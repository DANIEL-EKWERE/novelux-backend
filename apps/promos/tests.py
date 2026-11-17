from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.stories.models import Story
from .models import InAppPromo, PromoView

User = get_user_model()
MEM = {'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
       'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')


@override_settings(STORAGES=MEM)
class PromoTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.se = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.se2 = User.objects.create_user(email='se2@x.com', username='se2', password='x', role='se')
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x')
        self.story = Story.objects.create(author=self.author, title='The Spare Luna', slug='spare-luna',
                                          status='ongoing')
        self.c = APIClient()

    def create(self, user, **data):
        self.c.force_authenticate(user)
        payload = {'story_id': self.story.pk, 'kind': 'popup', 'tagline': 'Moon Goddess granted me the King', **data}
        return self.c.post('/api/promos/manage/', payload, format='multipart')

    def test_only_editors_and_admins_manage(self):
        self.assertEqual(self.create(self.reader).status_code, 403)
        self.assertEqual(self.create(self.author).status_code, 403)
        self.assertEqual(self.create(self.se).status_code, 201)

    def test_splash_needs_a_poster(self):
        r = self.create(self.se, kind='splash')
        self.assertEqual(r.status_code, 400)
        self.assertIn('poster', r.data['detail'])
        r = self.create(self.se, kind='splash', image=SimpleUploadedFile('p.png', PNG, 'image/png'))
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data['image'])

    def test_shown_once_per_reader_one_at_a_time(self):
        first = self.create(self.se, priority=5).data['id']
        second = self.create(self.se).data['id']
        c = APIClient()
        c.force_authenticate(self.reader)
        p = c.get('/api/promos/next/').data['promo']
        self.assertEqual(p['id'], first)                          # highest priority first, one at a time
        self.assertEqual(p['story']['slug'], 'spare-luna')
        c.post(f'/api/promos/{first}/seen/')
        self.assertEqual(c.get('/api/promos/next/').data['promo']['id'], second)
        c.post(f'/api/promos/{second}/seen/')
        c.post(f'/api/promos/{second}/click/')
        self.assertIsNone(c.get('/api/promos/next/').data['promo'])   # each shown once
        self.assertTrue(PromoView.objects.get(promo_id=second, user=self.reader).clicked_at)
        p2 = InAppPromo.objects.get(pk=second)
        self.assertEqual((p2.impressions, p2.clicks), (1, 1))

    def test_guests_use_the_device_seen_list(self):
        first = self.create(self.se).data['id']
        guest = APIClient()
        self.assertEqual(guest.get('/api/promos/next/').data['promo']['id'], first)
        self.assertIsNone(guest.get(f'/api/promos/next/?seen={first}').data['promo'])

    def test_schedule_pause_and_drafts(self):
        pid = self.create(self.se, starts_at=(timezone.now() + timedelta(days=1)).isoformat()).data['id']
        guest = APIClient()
        self.assertIsNone(guest.get('/api/promos/next/').data['promo'])          # not started
        InAppPromo.objects.filter(pk=pid).update(starts_at=timezone.now() - timedelta(minutes=1))
        self.assertIsNotNone(guest.get('/api/promos/next/').data['promo'])
        self.c.force_authenticate(self.se)
        self.c.patch(f'/api/promos/manage/{pid}/', {'is_active': False}, format='json')
        self.assertIsNone(guest.get('/api/promos/next/').data['promo'])          # paused
        InAppPromo.objects.filter(pk=pid).update(is_active=True)
        Story.objects.filter(pk=self.story.pk).update(status='draft')
        self.assertIsNone(guest.get('/api/promos/next/').data['promo'])          # book unpublished

    def test_senior_editors_edit_only_their_own(self):
        pid = self.create(self.se).data['id']
        self.c.force_authenticate(self.se2)
        self.assertEqual(self.c.patch(f'/api/promos/manage/{pid}/', {'tagline': 'x'}, format='json').status_code, 403)
        ce = User.objects.create_user(email='ce@x.com', username='ce', password='x', role='ce')
        self.c.force_authenticate(ce)
        self.assertEqual(self.c.patch(f'/api/promos/manage/{pid}/', {'tagline': 'Better hook'},
                                      format='json').data['tagline'], 'Better hook')

    def test_dashboard_page(self):
        self.client.force_login(self.se)
        from unittest import mock
        with mock.patch('novelux_web.views._user_from_request', return_value=self.se):
            r = self.client.get('/promotions/')
        self.assertEqual(r.status_code, 200)
        with mock.patch('novelux_web.views._user_from_request', return_value=self.reader):
            r = self.client.get('/promotions/')
        self.assertEqual(r.status_code, 302)
