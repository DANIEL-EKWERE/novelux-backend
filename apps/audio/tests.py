from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import AmbientSound, AmbientSoundCategory

User = get_user_model()


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AmbientSoundTests(TestCase):
    def sound(self, cat, title, **kw):
        return AmbientSound.objects.create(
            category=cat, title=title, audio=SimpleUploadedFile(f'{title}.mp3', b'ID3', 'audio/mpeg'), **kw)

    def test_library_lists_active_categories_and_sounds(self):
        rain = AmbientSoundCategory.objects.create(name='Rain', icon='🌧️', order=1)
        cafe = AmbientSoundCategory.objects.create(name='Café', order=0)
        AmbientSoundCategory.objects.create(name='Empty')                 # no sounds → hidden
        hidden = AmbientSoundCategory.objects.create(name='Hidden', is_active=False)
        self.sound(rain, 'Light rain', order=2)
        self.sound(rain, 'Storm', order=1)
        self.sound(rain, 'Off', is_active=False)
        self.sound(cafe, 'Chatter')
        self.sound(hidden, 'Nope')

        res = APIClient().get('/api/audio/ambient/')
        self.assertEqual(res.status_code, 200)
        cats = res.data['categories']
        self.assertEqual([c['name'] for c in cats], ['Café', 'Rain'])
        self.assertEqual([s['title'] for s in cats[1]['sounds']], ['Storm', 'Light rain'])
        self.assertTrue(cats[1]['sounds'][0]['url'])

    def test_play_counter(self):
        s = self.sound(AmbientSoundCategory.objects.create(name='Fire'), 'Fireplace')
        APIClient().post(f'/api/audio/ambient/{s.pk}/play/')
        s.refresh_from_db()
        self.assertEqual(s.plays, 1)

    def test_admin_upload_into_category(self):
        from django.urls import reverse
        admin = User.objects.create_superuser(email='admin@x.com', username='admin', password='x')
        self.client.force_login(admin)
        url = reverse('admin:audio_ambientsoundcategory_add')
        res = self.client.post(url, {
            'name': 'Nature', 'icon': '🌲', 'order': 0, 'is_active': 'on',
            'sounds-TOTAL_FORMS': 1, 'sounds-INITIAL_FORMS': 0,
            'sounds-0-title': 'Forest', 'sounds-0-order': 0, 'sounds-0-is_active': 'on',
            'sounds-0-duration_secs': 0,
            'sounds-0-audio': SimpleUploadedFile('forest.mp3', b'ID3', 'audio/mpeg'),
        }, secure=True)
        self.assertEqual(res.status_code, 302, getattr(res, 'context', None) and res.context.get('errors'))
        self.assertEqual(AmbientSound.objects.get().title, 'Forest')

    def test_rejects_non_audio_files(self):
        from django.core.exceptions import ValidationError
        s = AmbientSound(category=AmbientSoundCategory.objects.create(name='X'), title='Bad',
                         audio=SimpleUploadedFile('bad.exe', b'MZ'))
        with self.assertRaises(ValidationError):
            s.full_clean()
