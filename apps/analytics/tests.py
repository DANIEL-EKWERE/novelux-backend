from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import PageVisit

User = get_user_model()


class MasterDashboardTests(TestCase):
    """The owner's dashboard: admins only, and every section loads."""

    def setUp(self):
        from apps.chapters.models import Chapter, ChapterUnlock
        from apps.coins.models import Purchase, ReadingHistory
        from apps.editorial.models import AuthorEditorLink, ContractApplication
        from apps.stories.models import Story

        self.admin = User.objects.create_superuser(email='boss@x.com', username='boss', password='x')
        self.se = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='reader', password='x', coin_balance=40)
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        story = Story.objects.create(author=self.author, title='Tale', slug='tale', contract_status='signed')
        ch = Chapter.objects.create(story=story, title='One', chapter_number=1, is_published=True,
                                    reviewed_by_se=self.se, reviewed_at=timezone.now())
        ChapterUnlock.objects.create(user=self.reader, chapter=ch, coins_spent=20)
        ReadingHistory.objects.create(user=self.reader, story=story, chapter_number=1, chapter_title='One')
        Purchase.objects.create(user=self.reader, purchase_type='coin_pack', amount_paid_usd='4.99',
                                coins_granted=500, status='completed', completed_at=timezone.now())
        ContractApplication.objects.create(story=story, author=self.author, assigned_se=self.se,
                                           status='signed', signed_at=timezone.now())
        now = timezone.now()
        for user, path, mins in [(self.reader, '/api/chapters/tale/chapters/1/', 1),
                                 (self.reader, '/api/coins/checkin/', 90),
                                 (self.se, '/api/editorial/earnings/pending/', 3),
                                 (None, '/explore/tale/', 2)]:
            v = PageVisit.objects.create(user=user, path=path, ip_address='10.0.0.5', country='Nigeria',
                                         country_code='NG', city='Lagos', device_type='mobile', os='Android')
            PageVisit.objects.filter(pk=v.pk).update(created_at=now - timedelta(minutes=mins))
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_every_section_loads(self):
        for url in ['/api/master/overview/?days=30', '/api/master/realtime/', '/api/master/audience/?days=7',
                    '/api/master/users/', f'/api/master/users/{self.reader.pk}/', f'/api/master/users/{self.author.pk}/',
                    f'/api/master/users/{self.se.pk}/', '/api/master/team/', f'/api/master/team/{self.se.pk}/',
                    '/api/master/books/', '/api/master/revenue/']:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, (url, getattr(res, 'data', None)))

    def test_numbers(self):
        k = self.client.get('/api/master/overview/?days=30').data['kpis']
        self.assertEqual(k['online_now'], 2)            # reader + SE active in the last 5 minutes
        self.assertEqual(k['revenue_usd'], 4.99)
        self.assertEqual(k['chapter_reads'], 1)        # one chapter opened (from the request log)
        top = self.client.get('/api/master/overview/?days=30').data['top_books']
        self.assertEqual((top[0]['story__slug'], top[0]['reads'], top[0]['readers']), ('tale', 1, 1))
        rt = self.client.get('/api/master/realtime/').data
        self.assertEqual({u['username'] for u in rt['online']}, {'reader', 'se'})
        self.assertIn('Read chapter 1 of tale', [u['doing'] for u in rt['online']])

        users = self.client.get('/api/master/users/?status=online').data
        self.assertEqual({u['username'] for u in users['results']}, {'reader', 'se'})
        row = next(u for u in users['results'] if u['username'] == 'reader')
        self.assertEqual((row['country'], row['city'], row['spent_usd']), ('Nigeria', 'Lagos', 4.99))

        d = self.client.get(f'/api/master/users/{self.reader.pk}/').data
        self.assertTrue(d['status']['online'])
        self.assertEqual(d['reading']['unlocks'], 1)
        self.assertEqual(d['location']['places'][0]['city'], 'Lagos')

        team = self.client.get('/api/master/team/').data['editors']
        se = next(e for e in team if e['username'] == 'se')
        self.assertEqual((se['stats']['authors'], se['stats']['chapters_reviewed'], se['stats']['contracts_signed']), (1, 1, 1))
        member = self.client.get(f'/api/master/team/{self.se.pk}/').data
        self.assertEqual([a['username'] for a in member['authors']], ['author'])
        self.assertTrue(any('Contract signed' in x['what'] for x in member['log']))

    def test_replay(self):
        res = self.client.get(f'/api/master/users/{self.reader.pk}/replay/?live=1')
        self.assertEqual(res.status_code, 200, res.data)
        kinds = [x['type'] for x in res.data['screens']]
        self.assertIn('read', kinds)
        read = next(x for x in res.data['screens'] if x['type'] == 'read')
        self.assertEqual((read['story']['title'], read['chapter']['number']), ('Tale', 1))
        # Past sessions are listed and each can be replayed
        full = self.client.get(f'/api/master/users/{self.reader.pk}/replay/').data
        self.assertEqual(len(full['sessions']), 2)   # visits 90 minutes apart
        from urllib.parse import quote
        older = self.client.get(f"/api/master/users/{self.reader.pk}/replay/?start={quote(full['sessions'][1]['start'])}").data
        self.assertEqual([x['type'] for x in older['screens']], ['rewards'])
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get(f'/api/master/users/{self.reader.pk}/replay/').status_code, 403)

    def test_screen_grouping(self):
        from apps.analytics.master import _screen_of
        self.assertEqual(_screen_of('/api/stories/trending/')[0], 'home')
        self.assertEqual(_screen_of('/api/stories/tale/')[0], 'book')
        self.assertEqual(_screen_of('/api/chapters/tale/chapters/4/unlock/')[0], 'unlock')
        self.assertEqual(_screen_of('/api/coins/checkin/')[0], 'rewards')

    def test_search_and_filters(self):
        self.assertEqual([u['username'] for u in self.client.get('/api/master/users/?q=read').data['results']], ['reader'])
        self.assertEqual([u['username'] for u in self.client.get('/api/master/users/?status=paying').data['results']], ['reader'])
        dormant = {u['username'] for u in self.client.get('/api/master/users/?status=dormant').data['results']}
        self.assertEqual(dormant, {'boss', 'author'})

    def test_admins_only(self):
        for who in (self.reader, self.se, self.author):
            self.client.force_authenticate(who)
            self.assertEqual(self.client.get('/api/master/overview/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/master/users/').status_code, (401, 403))
        # role "admin" (not superuser) is allowed
        boss2 = User.objects.create_user(email='b2@x.com', username='boss2', password='x', role='admin')
        self.client.force_authenticate(boss2)
        self.assertEqual(self.client.get('/api/master/revenue/').status_code, 200)

    def test_web_page_is_gated(self):
        self.assertEqual(self.client.get('/master/').status_code, 302)  # no login cookie


class RateLimitTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_login_is_limited_per_ip_but_refresh_is_not(self):
        from unittest import mock
        c = APIClient()
        hdr = {'HTTP_X_FORWARDED_FOR': '203.0.113.7'}
        # Freeze the clock inside one window (fixed one-minute windows)
        self._clock = mock.patch('config.ratelimit.time.time', return_value=1_800_000_010)
        self._clock.start()
        self.addCleanup(self._clock.stop)
        codes = [c.post('/api/auth/token/', {'email': 'x@x.com', 'password': 'bad'}, format='json', **hdr).status_code
                 for _ in range(21)]
        self.assertNotIn(429, codes[:20])
        self.assertEqual(codes[20], 429)
        # Another network isn't affected
        self.assertNotEqual(c.post('/api/auth/token/', {'email': 'x@x.com', 'password': 'bad'}, format='json',
                                   HTTP_X_FORWARDED_FOR='198.51.100.9').status_code, 429)
        # Token refresh never counts as a login attempt
        self.assertNotEqual(c.post('/api/auth/token/refresh/', {'refresh': 'x'}, format='json', **hdr).status_code, 429)

    def test_api_throttle_is_per_account(self):
        from unittest import mock
        from rest_framework.settings import api_settings
        u = User.objects.create_user(email='t@x.com', username='t', password='x')
        c = APIClient()
        c.force_authenticate(u)
        rates = {'anon': '300/min', 'user': '3/min'}
        with mock.patch.object(api_settings, 'DEFAULT_THROTTLE_RATES', rates), \
             mock.patch('rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES', rates):
            codes = [c.get('/api/auth/me/').status_code for _ in range(4)]
        self.assertEqual(codes[:3], [200, 200, 200])
        self.assertEqual(codes[3], 429)

    def test_client_ip_behind_proxy(self):
        from django.test import RequestFactory
        from config.ratelimit import client_ip
        r = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='102.89.4.4, 10.0.0.1', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(client_ip(r), '102.89.4.4')


from django.test import override_settings  # noqa: E402


class CronTests(TestCase):
    """Scheduled jobs run through /api/cron/run/ when there's no Celery worker."""

    def test_switched_off_without_a_secret(self):
        with override_settings(CRON_SECRET=''):
            self.assertEqual(self.client.get('/api/cron/run/?key=anything').status_code, 503)

    @override_settings(CRON_SECRET='s3cret')
    def test_needs_the_secret(self):
        self.assertEqual(self.client.get('/api/cron/run/').status_code, 403)
        self.assertEqual(self.client.get('/api/cron/run/?key=wrong').status_code, 403)

    @override_settings(CRON_SECRET='s3cret')
    def test_runs_due_jobs_once(self):
        from apps.analytics.models import ScheduledJobRun
        res = self.client.get('/api/cron/run/?key=s3cret')
        self.assertEqual(res.status_code, 200, res.content)
        jobs = res.json()['jobs']
        self.assertEqual(set(jobs), {'expire_promotions', 'expire_bonus_coins', 'send_promotion_reminders', 'vip_payout',
                                     'social_scheduled_posts', 'social_insights'})
        self.assertTrue(all(v == 'ok' for v in jobs.values()), jobs)
        # Called again straight away: nothing is due
        again = self.client.get('/api/cron/run/', HTTP_X_CRON_KEY='s3cret').json()['jobs']
        self.assertEqual(set(again.values()), {'not due'})
        # An hour later the hourly jobs run again, the daily ones don't
        ScheduledJobRun.objects.update(last_started=timezone.now() - timedelta(minutes=58))
        later = self.client.get('/api/cron/run/?key=s3cret').json()['jobs']
        self.assertEqual(later['expire_bonus_coins'], 'ok')
        self.assertEqual(later['vip_payout'], 'not due')

    @override_settings(CRON_SECRET='s3cret')
    def test_one_failing_job_does_not_stop_the_rest(self):
        from unittest import mock
        with mock.patch('apps.coins.tasks.expire_bonus_coins.run', side_effect=RuntimeError('boom')):
            jobs = self.client.get('/api/cron/run/?key=s3cret').json()['jobs']
        self.assertTrue(jobs['expire_bonus_coins'].startswith('failed'))
        self.assertEqual(jobs['expire_promotions'], 'ok')

    def test_ping(self):
        self.assertEqual(self.client.get('/api/cron/ping/').json(), {'ok': True})


class InlineTaskTests(TestCase):
    def test_inline_mode_runs_tasks_in_a_thread(self):
        import threading
        from unittest import mock
        import config.celery as cc
        from apps.notifications.tasks import notify_followers_new_chapter
        started = []
        real_thread = threading.Thread

        class _Spy(real_thread):
            def start(self):
                started.append(self.name)
                # run synchronously so the test can check it
                self.run()

        with mock.patch.object(cc, 'CELERY_INLINE', True), mock.patch('config.celery.threading.Thread', _Spy), \
                mock.patch('django.db.connection.close'):
            self.assertIsNone(notify_followers_new_chapter.delay(999999))  # unknown chapter → task just returns
        self.assertEqual(started, ['task:apps.notifications.tasks.notify_followers_new_chapter'])
