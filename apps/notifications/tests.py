from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.stories.models import Bookmark, Story
from .models import Notification
from . import services

User = get_user_model()


@mock.patch('apps.notifications.services.notify_all')
@mock.patch('apps.notifications.services.send_to_tokens')
class BookSignedLiveTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author',
                                               first_name='Amaka', last_name='Obi')
        self.fan    = User.objects.create_user(email='f@x.com', username='fan', password='x')
        self.story  = Story.objects.create(
            author=self.author, title='Moonbound', slug='moonbound', description='x',
            synopsis='Khadia was born under a red moon. ' * 10)
        Bookmark.objects.create(user=self.fan, story=self.story)

    def test_shows_book_not_author(self, send_to_tokens, notify_all):
        services.on_book_signed_live(self.story)

        note = Notification.objects.get(recipient=self.fan)
        self.assertEqual(note.title, '📖 Moonbound')
        self.assertTrue(note.message.startswith('Khadia was born under a red moon.'))
        self.assertTrue(note.message.endswith('…'))
        self.assertLessEqual(len(note.message), 151)

        broadcast = notify_all.call_args.kwargs
        self.assertEqual(broadcast['title'], '📖 Moonbound')
        self.assertEqual(broadcast['body'], note.message)
        self.assertEqual(broadcast['exclude_user_ids'], [self.fan.pk])
        for text in (note.title, note.message, broadcast['title'], broadcast['body']):
            self.assertNotIn('Amaka', text)
            self.assertNotIn('programme', text)

    def test_cover_attached_when_present(self, send_to_tokens, notify_all):
        with mock.patch.object(services, '_story_cover_url', return_value='https://cdn.test/cover.png'):
            services.on_book_signed_live(self.story)
        self.assertEqual(notify_all.call_args.kwargs['image_url'], 'https://cdn.test/cover.png')
        self.assertEqual(Notification.objects.get(recipient=self.fan).data['image'], 'https://cdn.test/cover.png')

    def test_no_cover_no_synopsis(self, send_to_tokens, notify_all):
        self.story.synopsis = ''
        self.story.description = ''
        services.on_book_signed_live(self.story)
        kwargs = notify_all.call_args.kwargs
        self.assertEqual((kwargs['image_url'], kwargs['body']), ('', 'A new story is now live on HuxNovel.'))


class ContinueReadingReminderTests(TestCase):
    """The "continue reading" push ~30 minutes after a reader stops mid-book."""

    def setUp(self):
        from datetime import datetime, timezone as dt_tz
        from apps.chapters.models import Chapter
        from apps.users.models import FCMDevice
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x', first_name='Ada')
        FCMDevice.objects.create(user=self.reader, token='tok', platform='Android', device_model='', app_version='')
        self.story = Story.objects.create(author=self.author, title='Moonbound', slug='moonbound', status='ongoing')
        self.ch = [Chapter.objects.create(story=self.story, title=f'Ch {n}', chapter_number=n, is_published=True)
                   for n in (1, 2, 3)]
        # 15:00 in Lagos — outside quiet hours
        self.noon = datetime(2026, 11, 17, 14, 0, tzinfo=dt_tz.utc)

    def read(self, chapter, at):
        from .reading_reminders import record_reading
        with mock.patch('django.utils.timezone.now', return_value=at):
            record_reading(self.reader, chapter)

    def run_at(self, at):
        from .reading_reminders import send_due
        with mock.patch('apps.notifications.services.notify_user') as push:
            out = send_due(now=at)
        return out, push

    def test_sent_once_after_30_minutes_to_the_next_chapter(self):
        from datetime import timedelta
        self.read(self.ch[0], self.noon)
        _, push = self.run_at(self.noon + timedelta(minutes=20))
        push.assert_not_called()                                   # too early
        out, push = self.run_at(self.noon + timedelta(minutes=31))
        self.assertIn('1 continue-reading', out)
        _, title, body = push.call_args[0]
        self.assertIn('Moonbound', title)
        self.assertIn('Chapter 2', body)
        self.assertEqual(push.call_args[1]['data'],
                         {'screen': 'story', 'slug': 'moonbound', 'chapter_number': 2, 'action': 'continue'})
        _, push = self.run_at(self.noon + timedelta(minutes=40))
        push.assert_not_called()                                   # only once per stop

    def test_reading_again_cancels_and_counts_as_came_back(self):
        from datetime import timedelta
        from .models import ReadingReminder
        self.read(self.ch[0], self.noon)
        self.read(self.ch[1], self.noon + timedelta(minutes=25))   # still reading
        _, push = self.run_at(self.noon + timedelta(minutes=35))
        push.assert_not_called()
        self.run_at(self.noon + timedelta(minutes=56))             # reminder for ch.2 stop
        self.read(self.ch[2], self.noon + timedelta(hours=2))      # came back
        self.assertEqual(ReadingReminder.objects.get().returned_count, 1)

    def test_one_a_day_finished_books_and_quiet_hours(self):
        from datetime import timedelta
        self.read(self.ch[0], self.noon)
        self.run_at(self.noon + timedelta(minutes=31))
        self.read(self.ch[1], self.noon + timedelta(hours=2))
        _, push = self.run_at(self.noon + timedelta(hours=3))
        push.assert_not_called()                                   # already reminded today
        # Caught up on the last chapter: nothing to remind about
        self.read(self.ch[2], self.noon + timedelta(days=2))
        _, push = self.run_at(self.noon + timedelta(days=2, minutes=31))
        push.assert_not_called()
        # Stopped at 22:30 Lagos time → waits for the morning
        late = self.noon + timedelta(days=4, hours=7, minutes=30)   # 21:30 UTC = 22:30 Lagos
        self.read(self.ch[0], late)
        _, push = self.run_at(late + timedelta(minutes=31))
        push.assert_not_called()
        _, push = self.run_at(late + timedelta(hours=9, minutes=40))  # ~08:10 Lagos
        push.assert_called_once()

    def test_opening_a_chapter_records_it(self):
        from rest_framework.test import APIClient
        from .models import ReadingReminder
        c = APIClient()
        c.force_authenticate(self.reader)
        r = c.get('/api/chapters/moonbound/chapters/2/')
        self.assertEqual(r.status_code, 200, getattr(r, 'data', r))
        self.assertEqual(ReadingReminder.objects.get(user=self.reader).chapter_number, 2)


class EngagementPushTests(TestCase):
    """Check-in / tasks / ad rewards / VIP pushes at the reader's local hour."""

    def setUp(self):
        from datetime import datetime, timezone as dt_tz
        from apps.analytics.models import PageVisit
        from apps.users.models import FCMDevice
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x')
        FCMDevice.objects.create(user=self.reader, token='tok-ada', platform='Android', device_model='', app_version='')
        v = PageVisit.objects.create(user=self.reader, path='/api/stories/', country_code='NG')
        self.day = datetime(2026, 11, 17, tzinfo=dt_tz.utc)
        PageVisit.objects.filter(pk=v.pk).update(created_at=self.day - timedelta(days=1))

    def at_lagos(self, hour, days=0):
        return self.day + timedelta(days=days, hours=hour - 1)     # Lagos = UTC+1

    def run_at(self, when):
        from .engagement import send_due
        with mock.patch('apps.notifications.fcm.send_to_tokens') as push:
            out = send_due(now=when)
        return out, push

    def test_checkin_streak_reminder_at_7pm(self):
        from apps.coins.models import CheckinStreak
        CheckinStreak.objects.create(user=self.reader, current_streak=4,
                                     last_checkin=self.day.date() - timedelta(days=1))
        _, push = self.run_at(self.at_lagos(18))
        push.assert_not_called()                                    # not 7pm yet
        out, push = self.run_at(self.at_lagos(19))
        self.assertIn('checkin: 1', out)
        tokens, title, body, data = push.call_args[0]
        self.assertEqual(tokens, ['tok-ada'])
        self.assertIn('4', title + body)                            # the streak
        self.assertEqual(data, {'screen': 'rewards', 'section': 'checkin'})
        _, push = self.run_at(self.at_lagos(19) + timedelta(minutes=15))
        push.assert_not_called()                                    # one a day

    def test_no_checkin_reminder_after_checking_in(self):
        from apps.coins.models import CheckinStreak
        CheckinStreak.objects.create(user=self.reader, current_streak=2, last_checkin=self.day.date())
        _, push = self.run_at(self.at_lagos(19))
        push.assert_not_called()

    def test_tasks_then_ad_rewards_at_noon(self):
        from apps.coins.models import AdRewardTask, Task, UserTask
        t = Task.objects.create(title='Follow us', description='x', reward_coins=20)
        AdRewardTask.objects.create(ads_required=3, reward_coins=15)
        out, push = self.run_at(self.at_lagos(12))
        self.assertIn('tasks: 1', out)
        self.assertEqual(push.call_args[0][3], {'screen': 'rewards', 'section': 'tasks'})
        self.assertIn('20', push.call_args[0][2])
        # Task done → next rewards push (3 days later) is about ad rewards
        UserTask.objects.create(user=self.reader, task=t, status=UserTask.STATUS_CLAIMED,
                                claimed_at=self.day)
        _, push = self.run_at(self.at_lagos(12, days=1))
        push.assert_not_called()                                    # every 3 days
        out, push = self.run_at(self.at_lagos(12, days=3))
        self.assertIn('ads: 1', out)
        self.assertEqual(push.call_args[0][3], {'screen': 'rewards', 'section': 'ad_rewards'})

    def test_vip_push_weekly_and_never_to_vips(self):
        out, push = self.run_at(self.at_lagos(20))
        self.assertIn('vip: 1', out)
        self.assertEqual(push.call_args[0][3], {'screen': 'vip'})
        _, push = self.run_at(self.at_lagos(20, days=2))
        push.assert_not_called()                                    # weekly
        User.objects.filter(pk=self.reader.pk).update(is_vip=True)
        _, push = self.run_at(self.at_lagos(20, days=8))
        push.assert_not_called()

    def test_inactive_readers_are_left_alone(self):
        _, push = self.run_at(self.at_lagos(20, days=30))
        push.assert_not_called()
