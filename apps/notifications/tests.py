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
    """Daily retention pushes: up to 8 a day at the reader's local hours,
    each picked for them."""

    def setUp(self):
        from datetime import datetime, timezone as dt_tz
        from apps.analytics.models import PageVisit
        from apps.chapters.models import Chapter
        from apps.coins.models import ReadingHistory
        from apps.users.models import FCMDevice
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x')
        FCMDevice.objects.create(user=self.reader, token='tok-ada', platform='Android', device_model='', app_version='')
        self.day = datetime(2026, 11, 17, tzinfo=dt_tz.utc)            # a Tuesday
        v = PageVisit.objects.create(user=self.reader, path='/api/stories/', country_code='NG')
        PageVisit.objects.filter(pk=v.pk).update(created_at=self.day - timedelta(days=1))
        self.luna = Story.objects.create(author=self.author, title='Spare Luna', slug='luna', status='ongoing',
                                         total_chapters=3, total_views=900)
        self.other = Story.objects.create(author=self.author, title='Royal Mate', slug='royal', status='ongoing',
                                          total_chapters=2, total_views=500)
        for n in (1, 2, 3):
            Chapter.objects.create(story=self.luna, title=f'C{n}', chapter_number=n, is_published=True)
        ReadingHistory.objects.create(user=self.reader, story=self.luna, chapter_number=1)

    def lagos(self, hour, days=0, minute=5):
        return self.day + timedelta(days=days, hours=hour - 1, minutes=minute)     # Lagos = UTC+1

    def run_at(self, when):
        from .engagement import send_due
        with mock.patch('apps.notifications.fcm.send_personal', return_value=(1, 0, [])) as push:
            out = send_due(now=when)
        return out, push

    def sent(self, push):
        return push.call_args[0][0] if push.called else []

    def test_morning_push_and_once_per_slot(self):
        _, push = self.run_at(self.lagos(7))
        push.assert_not_called()                                   # before the first slot
        out, push = self.run_at(self.lagos(8))
        (tok, title, body, data, *_), = self.sent(push)
        self.assertEqual(tok, 'tok-ada')
        self.assertEqual(data['screen'], 'rewards')                # morning: check-in
        _, push = self.run_at(self.lagos(8, minute=25))
        push.assert_not_called()                                   # same slot: once

    def test_continue_reading_names_their_book(self):
        self.run_at(self.lagos(8))
        _, push = self.run_at(self.lagos(10))
        (tok, title, body, data, *_), = self.sent(push)
        self.assertIn('Spare Luna', title + body)
        self.assertIn('2', title + body)                           # the next chapter
        self.assertEqual(data, {'screen': 'story', 'slug': 'luna', 'chapter_number': 2, 'action': 'continue'})

    def test_eight_a_day_varied(self):
        from .models import EngagementPush
        User.objects.filter(pk=self.reader.pk).update(coin_balance=140)
        for h in (8, 10, 12, 14, 16, 18, 20, 21, 22):
            self.run_at(self.lagos(h))
        kinds = list(EngagementPush.objects.filter(user=self.reader).order_by('sent_at').values_list('kind', flat=True))
        self.assertEqual(len(kinds), 8)
        self.assertTrue(all(a != b for a, b in zip(kinds, kinds[1:])), kinds)     # never twice in a row
        self.assertIn('continue', kinds)
        self.assertIn('recommend', kinds)                          # Royal Mate — not read yet
        self.assertIn('coins', kinds)
        self.assertLessEqual(kinds.count('continue'), 2)

    def test_local_time_per_country(self):
        from apps.analytics.models import PageVisit
        PageVisit.objects.filter(user=self.reader).update(country_code='US')    # New York = UTC-5
        _, push = self.run_at(self.lagos(8))
        push.assert_not_called()                                   # 2am in New York
        _, push = self.run_at(self.day + timedelta(hours=13, minutes=5))   # 8am New York
        self.assertEqual(len(self.sent(push)), 1)

    def test_guests_get_book_pushes(self):
        from apps.users.models import FCMDevice
        FCMDevice.objects.create(user=None, token='tok-guest', platform='Android', device_model='', app_version='')
        _, push = self.run_at(self.lagos(10))
        guest = [m for m in self.sent(push) if m[0] == 'tok-guest']
        self.assertEqual(len(guest), 1)
        self.assertEqual(guest[0][3]['screen'], 'story')

    def test_inactive_readers_left_alone(self):
        from apps.analytics.models import PageVisit
        PageVisit.objects.filter(user=self.reader).update(created_at=self.day - timedelta(days=45))
        User.objects.filter(pk=self.reader.pk).update(date_joined=self.day - timedelta(days=90))
        _, push = self.run_at(self.lagos(8))
        push.assert_not_called()



class BookPushImageTests(TestCase):
    """Pushes that come from a book carry its cover."""

    def setUp(self):
        from django.core.files.base import ContentFile
        from apps.users.models import FCMDevice
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.fan = User.objects.create_user(email='f@x.com', username='fan', password='x')
        FCMDevice.objects.create(user=self.fan, token='tok-fan', platform='Android', device_model='', app_version='')
        self.story = Story.objects.create(author=self.author, title='Spare Luna', slug='luna', status='ongoing')
        self.story.cover_image.save('luna.png', ContentFile(b'img'), save=True)

    def test_new_chapter_push_has_the_cover(self):
        with mock.patch('apps.notifications.services.send_to_tokens') as push, \
                mock.patch('apps.notifications.services.notify_all') as everyone:
            services.on_new_chapter(self.story, 'Chapter 9')
        self.assertIn('luna', everyone.call_args.kwargs['image_url'])

    def test_followers_push_uses_the_current_api_with_cover(self):
        from apps.chapters.models import Chapter
        from apps.users.models import Follow
        from .tasks import notify_followers_new_chapter
        Follow.objects.create(follower=self.fan, following=self.author)
        ch = Chapter.objects.create(story=self.story, title='The Bite', chapter_number=4, is_published=True)
        with mock.patch('apps.notifications.fcm.send_to_tokens') as push:
            notify_followers_new_chapter(ch.pk)
        tokens, title, body, data, image = push.call_args[0]
        self.assertEqual(tokens, ['tok-fan'])
        self.assertIn('Spare Luna', title)
        self.assertEqual(data['slug'], 'luna')
        self.assertIn('luna', image)
