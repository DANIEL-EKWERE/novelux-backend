from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.editorial.models import AuthorEditorLink, SEPromotionRequest
from apps.stories.models import Story
from .models import Placement, PromotionTask, Shelf

User = get_user_model()


class PromotionTeamTests(TestCase):
    def setUp(self):
        self.promo = User.objects.create_user(email='p@x.com', username='tola', password='x', role='promo')
        self.se = User.objects.create_user(email='se@x.com', username='kay', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        self.books = [Story.objects.create(author=self.author, title=f'Book {i}', slug=f'book-{i}', status='ongoing',
                                           total_views=1000 - i * 10, total_chapters=5) for i in range(6)]
        self.c = APIClient()
        self.c.force_authenticate(self.promo)
        Shelf.ensure_defaults()
        self.trending = Shelf.objects.get(key='trending')
        p = mock.patch('apps.notifications.services.notify_user')
        p.start()
        self.addCleanup(p.stop)

    def trending_slugs(self):
        r = APIClient().get('/api/stories/trending/')
        rows = r.data['results'] if isinstance(r.data, dict) else r.data
        return [s['slug'] for s in rows]

    def test_only_the_team_and_admins(self):
        for u, code in ((self.se, 403), (self.author, 403)):
            self.c.force_authenticate(u)
            self.assertEqual(self.c.get('/api/promotion/shelves/').status_code, code)

    def test_scheduled_sets_switch_by_themselves(self):
        now = timezone.now()
        b = self.books
        # Today: books 5 and 4 first. Tomorrow: book 3 takes slot 1.
        r = self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [b[5].pk, b[4].pk],
                        'starts_at': (now - timedelta(minutes=1)).isoformat(), 'days': 1, 'label': 'Mon'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [b[3].pk],
                    'starts_at': (now + timedelta(days=1)).isoformat(), 'days': 1, 'label': 'Tue'}, format='json')
        self.assertEqual(self.trending_slugs()[:3], ['book-5', 'book-4', 'book-0'])   # then the usual order
        with mock.patch('django.utils.timezone.now', return_value=now + timedelta(days=1, minutes=1)):
            self.assertEqual(self.trending_slugs()[0], 'book-3')
        cal = self.c.get(f'/api/promotion/calendar/?start={timezone.localdate()}&days=3').data
        self.assertTrue(any(p['book']['slug'] == 'book-3' for d in cal['days'] for p in d['placements']))

    def test_too_many_books_and_clash_warnings(self):
        self.trending.capacity = 2
        self.trending.save()
        r = self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [b.pk for b in self.books[:3]]}, format='json')
        self.assertEqual(r.status_code, 400)
        self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [self.books[0].pk], 'days': 3}, format='json')
        r = self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [self.books[1].pk],
                        'days': 3, 'replace': False}, format='json')
        self.assertTrue(r.data['warnings'])                       # slot 1 double-booked

    def test_daily_rotation(self):
        days = [[self.books[0].pk, self.books[1].pk], [self.books[2].pk, self.books[3].pk], [self.books[4].pk]]
        r = self.c.post('/api/promotion/rotation/', {'shelf_id': self.trending.pk, 'start_date': str(timezone.localdate()),
                        'switch_time': '00:00', 'tz_offset_minutes': 0, 'days': days}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Placement.objects.count(), 5)
        p = Placement.objects.get(story=self.books[2])
        self.assertEqual((p.ends_at - p.starts_at), timedelta(days=1))
        self.assertEqual(p.position, 1)

    def test_pause_end_and_active_list(self):
        self.c.post('/api/promotion/schedule/', {'shelf_id': self.trending.pk, 'books': [self.books[5].pk], 'days': 2}, format='json')
        pid = Placement.objects.get().pk
        self.assertEqual(len(self.c.get('/api/promotion/placements/?status=active').data['results']), 1)
        self.c.patch(f'/api/promotion/placements/{pid}/', {'paused': True}, format='json')
        self.assertNotEqual(self.trending_slugs()[0], 'book-5')
        self.assertEqual(len(self.c.get('/api/promotion/placements/?status=paused').data['results']), 1)
        self.c.patch(f'/api/promotion/placements/{pid}/', {'paused': False}, format='json')
        self.assertEqual(self.trending_slugs()[0], 'book-5')
        self.c.patch(f'/api/promotion/placements/{pid}/', {'end_now': True}, format='json')
        self.assertNotEqual(self.trending_slugs()[0], 'book-5')
        self.assertTrue(self.c.get('/api/promotion/history/').data['results'])

    def test_se_request_approved_by_team_and_forwarded(self):
        req = SEPromotionRequest.objects.create(se=self.se, story=self.books[5], tab='werewolf', section='fresh-reads',
                                                message='Readers love it')
        rows = self.c.get('/api/promotion/requests/').data['results']
        self.assertEqual((rows[0]['reason'], rows[0]['se']), ('Readers love it', 'kay'))
        r = self.c.post(f'/api/promotion/requests/{req.pk}/review/', {'action': 'approve', 'shelf_id': self.trending.pk,
                        'days': 7}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.trending_slugs()[0], 'book-5')
        se = APIClient()
        se.force_authenticate(self.se)
        mine = se.get('/api/editorial/promotion-requests/').data['results'][0]
        self.assertEqual((mine['stage'], mine['shelf'], mine['reviewer_role']), ('promoted', 'Trending Books', 'Promotion team'))
        r = se.post(f'/api/editorial/promotion-requests/{req.pk}/forward/', {'message': 'Well done!'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        from apps.notifications.models import Notification
        self.assertTrue(Notification.objects.filter(recipient=self.author, title__icontains='promoted').exists())

    def test_rejection_needs_feedback_and_shows_to_se(self):
        req = SEPromotionRequest.objects.create(se=self.se, story=self.books[1], tab='werewolf', section='fresh-reads', message='x')
        self.assertEqual(self.c.post(f'/api/promotion/requests/{req.pk}/review/', {'action': 'reject'}, format='json').status_code, 400)
        self.c.post(f'/api/promotion/requests/{req.pk}/review/', {'action': 'reject', 'feedback': 'Too few chapters'}, format='json')
        se = APIClient()
        se.force_authenticate(self.se)
        mine = se.get('/api/editorial/promotion-requests/').data['results'][0]
        self.assertEqual((mine['status'], mine['ce_note']), ('rejected', 'Too few chapters'))

    def test_explore_section_shelf(self):
        sh = Shelf.objects.get(key='explore:werewolf:fresh-reads')
        self.c.post('/api/promotion/schedule/', {'shelf_id': sh.pk, 'books': [self.books[2].pk]}, format='json')
        from apps.stories.views import ExploreTabView
        self.assertEqual(ExploreTabView()._pinned_ids('werewolf', 'fresh-reads')[0], self.books[2].pk)

    def test_role_routing_and_dashboard(self):
        from novelux_web.views import _home_for
        self.assertEqual(_home_for(self.promo), '/promotion/')
        with mock.patch('novelux_web.views._user_from_request', return_value=self.promo):
            r = self.client.get('/promotion/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Daily rotation', r.content)
        with mock.patch('novelux_web.views._user_from_request', return_value=self.se):
            self.assertEqual(self.client.get('/promotion/').status_code, 302)
        from apps.social.service import can_post
        self.assertTrue(can_post(self.promo))


class PromotionTasksAndAnalyticsTests(TestCase):
    def setUp(self):
        from apps.chapters.models import Chapter
        self.Chapter = Chapter
        self.promo = User.objects.create_user(email='p@x.com', username='tola', password='x', role='promo')
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.other = User.objects.create_user(email='o@x.com', username='bola', password='x', role='author')
        self.book = Story.objects.create(author=self.author, title='Spare Luna', slug='spare-luna', status='ongoing',
                                         total_views=900, total_chapters=3)
        self.c = APIClient()
        self.c.force_authenticate(self.promo)
        p = mock.patch('apps.notifications.services.notify_user')
        p.start()
        self.addCleanup(p.stop)

    def offer(self, **kw):
        body = {'story_id': self.book.pk, 'title': 'Trending week', 'message': 'Congrats!', 'reward': '7 days on Trending',
                'chapters_per_day': 2, 'duration_days': 3, **kw}
        return self.c.post('/api/promotion/tasks/', body, format='json')

    def test_offer_accept_and_progress(self):
        from apps.notifications.models import Notification
        r = self.offer()
        self.assertEqual(r.status_code, 201, r.data)
        tid = r.data['task']['id']
        self.assertTrue(Notification.objects.filter(recipient=self.author, title__icontains='Promotion offer').exists())
        a = APIClient()
        a.force_authenticate(self.other)                       # someone else's offer: invisible
        self.assertEqual(a.get('/api/promotion/my-tasks/').data['results'], [])
        self.assertEqual(a.post(f'/api/promotion/my-tasks/{tid}/respond/', {'accept': True}, format='json').status_code, 404)
        a.force_authenticate(self.author)
        self.assertEqual(len(a.get('/api/promotion/my-tasks/').data['results']), 1)
        r = a.post(f'/api/promotion/my-tasks/{tid}/respond/', {'accept': True}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        # Two chapters on day 1 → day 1 met
        for n in (1, 2):
            self.Chapter.objects.create(story=self.book, title=f'C{n}', chapter_number=n, status='published', is_published=True)
        t = PromotionTask.objects.get(pk=tid)
        p = t.progress()
        self.assertEqual((p['uploaded'], p['days'][0]['state'], p['on_track']), (2, 'met', True))
        # Day 2 passes with nothing → missed
        with mock.patch('django.utils.timezone.now', return_value=t.accepted_at + timedelta(days=2, hours=1)):
            t.refresh_status()
        self.assertEqual(PromotionTask.objects.get(pk=tid).status, 'missed')
        # The team can still decide
        self.c.patch(f'/api/promotion/tasks/{tid}/', {'status': 'qualified'}, format='json')
        self.assertTrue(Notification.objects.filter(recipient=self.author, title__icontains='qualified').exists())

    def test_decline_and_required_fields(self):
        self.assertEqual(self.offer(reward='').status_code, 400)
        tid = self.offer().data['task']['id']
        a = APIClient()
        a.force_authenticate(self.author)
        a.post(f'/api/promotion/my-tasks/{tid}/respond/', {'accept': False, 'reason': 'Exams this week'}, format='json')
        t = PromotionTask.objects.get(pk=tid)
        self.assertEqual((t.status, t.decline_reason), ('declined', 'Exams this week'))
        self.assertEqual(a.post(f'/api/promotion/my-tasks/{tid}/respond/', {'accept': True}, format='json').status_code, 400)

    def test_search_is_logged_and_analytics(self):
        from apps.stories.models import StoryDailyStats
        from .models import SearchLog
        APIClient().get('/api/stories/?search=Spare Luna')
        self.assertEqual(SearchLog.objects.get().query, 'spare luna')
        today = timezone.localdate()
        for i in range(14):                                     # growing: 10/day last week, 2/day before
            StoryDailyStats.objects.create(story=self.book, date=today - timedelta(days=i), views=10 if i < 7 else 2)
        self.Chapter.objects.create(story=self.book, title='C1', chapter_number=1, status='published', is_published=True)
        d = self.c.get('/api/promotion/analytics/movers/?days=7').data
        self.assertEqual(d['rising'][0]['slug'], 'spare-luna')
        self.assertEqual(d['rising'][0]['growth'], 400.0)
        self.assertEqual(d['candidates'][0]['slug'], 'spare-luna')
        self.assertEqual(d['top_searches'][0]['query'], 'spare luna')
        t = self.c.get(f'/api/promotion/analytics/books/{self.book.pk}/?days=30').data
        self.assertEqual((t['totals']['week'], t['totals']['week_growth']), (70, 400.0))
        self.assertEqual(len(t['series']), 30)

    def test_promotion_results_lift(self):
        from apps.stories.models import StoryDailyStats
        today = timezone.localdate()
        for i in range(8):
            StoryDailyStats.objects.create(story=self.book, date=today - timedelta(days=i), views=30 if i < 4 else 10)
        Shelf.ensure_defaults()
        sh = Shelf.objects.get(key='featured')
        Placement.objects.create(shelf=sh, story=self.book, starts_at=timezone.now() - timedelta(days=3, hours=1),
                                 ends_at=timezone.now() + timedelta(days=1))
        d = self.c.get('/api/promotion/analytics/promotions/').data
        self.assertEqual(d['placements'][0]['during']['views'], 120)
        self.assertEqual(d['placements'][0]['lift'], 200.0)
        self.assertEqual(d['by_shelf'][0]['shelf'], 'Featured Books')
        a = APIClient()
        a.force_authenticate(self.author)
        mine = a.get('/api/stories/my-promotions/').data
        self.assertTrue(any(p['section'] == 'Featured Books' and p['state'] == 'live' for p in mine['promotions']))
