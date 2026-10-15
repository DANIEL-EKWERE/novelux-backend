from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.editorial.models import StoryPromotion, SEPromotionRequest
from .models import Story, StoryDailyStats

User = get_user_model()


class MyPromotionsTests(TestCase):
    def setUp(self):
        self.se     = User.objects.create_user(email='se@x.com', username='se', password='x', role='se',
                                               first_name='Tola', last_name='A')
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.other  = User.objects.create_user(email='o@x.com', username='other', password='x', role='author')
        self.story  = Story.objects.create(author=self.author, title='Moon', slug='moon')
        self.theirs = Story.objects.create(author=self.other, title='Theirs', slug='theirs')
        now = timezone.now()
        self.live = StoryPromotion.objects.create(
            se=self.se, story=self.story, category='trending',
            starts_at=now - timedelta(days=2), expires_at=now + timedelta(days=5))
        StoryPromotion.objects.create(
            se=self.se, story=self.story, category='featured', status=StoryPromotion.STATUS_QUEUED,
            starts_at=now, expires_at=now + timedelta(days=7), queue_position=1)
        StoryPromotion.objects.create(
            se=self.se, story=self.theirs, category='trending',
            starts_at=now - timedelta(days=1), expires_at=now + timedelta(days=1))
        today = timezone.localdate()
        for days_ago, views in [(0, 50), (1, 40), (2, 30), (3, 10), (4, 10), (5, 10)]:
            StoryDailyStats.objects.create(story=self.story, date=today - timedelta(days=days_ago),
                                           views=views, unlocks=1)
        SEPromotionRequest.objects.create(se=self.se, story=self.story, tab='werewolf',
                                          section='picks-for-you', message='internal reasoning')
        self.client = APIClient()
        self.client.force_authenticate(self.author)

    def test_lists_only_my_promotions_with_details(self):
        res = self.client.get('/api/stories/my-promotions/')
        self.assertEqual(res.status_code, 200)
        titles = {p['story']['title'] for p in res.data['promotions']}
        self.assertEqual(titles, {'Moon'})
        live = next(p for p in res.data['promotions'] if p['state'] == 'live')
        self.assertEqual((live['section'], live['promoted_by'], live['days_left']), ('Trending Now', 'Tola A', 4))
        # 3 days measured: 120 views during vs 30 in the 3 days before → +300%
        self.assertEqual(live['performance']['during']['views'], 120)
        self.assertEqual(live['performance']['before']['views'], 30)
        self.assertEqual(live['performance']['views_change_pct'], 300)
        self.assertEqual(res.data['summary']['live'], 1)

    def test_queued_promotion_shows_position(self):
        res = self.client.get('/api/stories/my-promotions/')
        queued = next(p for p in res.data['promotions'] if p['state'] == 'queued')
        self.assertEqual((queued['queue_position'], queued['performance']), (1, None))

    def test_editor_notes_are_not_exposed(self):
        res = self.client.get('/api/stories/my-promotions/')
        self.assertEqual(len(res.data['requests']), 1)
        self.assertNotIn('internal reasoning', str(res.data))

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/stories/my-promotions/').status_code, (401, 403))
