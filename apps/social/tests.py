from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import SocialAccount, SocialPost, SocialSettings
from . import publishers

User = get_user_model()
MEM = {'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
       'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}


class FakeNet:
    """Stands in for a network: records what was posted."""
    fields = [('chat_id', 'Chat', False), ('bot_token', 'Token', True)]
    sent = []
    fail = False

    @classmethod
    def verify(cls, acc):
        return 'Channel: Test'

    @classmethod
    def publish(cls, acc, ctx):
        if cls.fail:
            raise publishers.PublishError('Network said no')
        cls.sent.append((acc.name, ctx.text_with_link(), len(ctx.images), bool(ctx.video)))
        return '42', 'https://t.me/test/42'


def _sync_publish(post_id):
    from .service import publish_post
    publish_post(post_id)


@override_settings(STORAGES=MEM)
@mock.patch('apps.social.views.publish_in_background', _sync_publish)
class SocialDashboardTests(TestCase):
    def setUp(self):
        FakeNet.sent, FakeNet.fail = [], False
        self.p = mock.patch.dict(publishers.PUBLISHERS, {'telegram': FakeNet, 'x': FakeNet})
        self.p.start()
        self.addCleanup(self.p.stop)
        self.boss = User.objects.create_superuser(email='b@x.com', username='boss', password='x')
        self.se = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.c = APIClient()

    def as_(self, u):
        self.c.force_authenticate(u)
        return self.c

    def connect(self, platform='telegram', name='HuxNovel Telegram'):
        r = self.as_(self.boss).post('/api/social/accounts/', {
            'platform': platform, 'name': name, 'values': {'chat_id': '@huxnovel', 'bot_token': 'SECRET-123'}},
            format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data['id']

    def test_who_can_do_what(self):
        self.assertEqual(self.as_(self.author).get('/api/social/overview/').status_code, 403)
        ov = self.as_(self.se).get('/api/social/overview/').data
        self.assertFalse(ov['can_manage'])
        self.assertEqual(self.as_(self.se).post('/api/social/accounts/', {'platform': 'telegram'},
                                                format='json').status_code, 403)
        self.assertEqual(self.as_(self.se).patch('/api/social/settings/', {'require_approval': True},
                                                 format='json').status_code, 403)

    def test_secrets_are_encrypted_and_never_returned(self):
        aid = self.connect()
        acc = SocialAccount.objects.get(pk=aid)
        self.assertNotIn('SECRET-123', acc._secrets)
        self.assertEqual(acc.secrets['bot_token'], 'SECRET-123')
        data = self.as_(self.boss).get('/api/social/overview/').data['accounts'][0]
        self.assertNotIn('SECRET-123', str(data))
        self.assertEqual(data['secrets_set'], ['bot_token'])
        self.assertNotIn('SECRET-123', str(self.as_(self.se).get('/api/social/overview/').data))
        # Editing without a token keeps the saved one
        self.as_(self.boss).patch(f'/api/social/accounts/{aid}/', {'values': {'chat_id': '@new'}}, format='json')
        acc.refresh_from_db()
        self.assertEqual((acc.config['chat_id'], acc.secrets['bot_token']), ('@new', 'SECRET-123'))
        test = self.as_(self.boss).post(f'/api/social/accounts/{aid}/test/').data
        self.assertTrue(test['ok'])

    def test_post_goes_out_directly_by_default(self):
        aid = self.connect()
        img = SimpleUploadedFile('a.png', b'\x89PNG....', content_type='image/png')
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'New book out!', 'link': 'https://huxnovel.com/x',
                                                          'account_ids': [aid], 'files': [img], 'action': 'publish'})
        self.assertEqual(r.status_code, 201, r.data)
        post = SocialPost.objects.get()
        self.assertEqual(post.status, 'published')
        self.assertEqual(FakeNet.sent, [('HuxNovel Telegram', 'New book out!\n\nhttps://huxnovel.com/x', 1, False)])
        self.assertEqual(post.targets.get().url, 'https://t.me/test/42')

    def test_approval_setting(self):
        aid = self.connect()
        self.as_(self.boss).patch('/api/social/settings/', {'require_approval': True}, format='json')
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'Hi', 'account_ids': [aid]})
        self.assertEqual(r.data['status'], 'pending_approval')
        self.assertEqual(FakeNet.sent, [])
        # Admins' own posts still go straight out
        self.assertEqual(self.as_(self.boss).post('/api/social/posts/', {'text': 'Boss', 'account_ids': [aid]})
                         .data['status'], 'published')
        done = self.as_(self.boss).post(f"/api/social/posts/{r.data['id']}/approve/", {}, format='json').data
        self.assertEqual(done['status'], 'published')
        self.assertEqual(len(FakeNet.sent), 2)

    def test_failure_then_retry(self):
        aid, aid2 = self.connect(), self.connect('x', 'HuxNovel X')
        FakeNet.fail = True
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'Hi', 'account_ids': [aid, aid2]})
        post = SocialPost.objects.get(pk=r.data['id'])
        self.assertEqual(post.status, 'failed')
        self.assertIn('Network said no', post.targets.first().error)
        FakeNet.fail = False
        self.assertEqual(self.as_(self.se).post(f'/api/social/posts/{post.pk}/retry/', {}, format='json')
                         .data['status'], 'published')

    def test_text_too_long_for_x(self):
        aid = self.connect('x', 'HuxNovel X')
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'a' * 300, 'account_ids': [aid]})
        self.assertEqual(r.status_code, 400)
        self.assertIn('HuxNovel X', r.data['detail'])
        # A shorter version just for X is fine
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'a' * 300, 'account_ids': [aid],
                                                          'overrides': '{"%d": "short"}' % aid})
        self.assertEqual(r.data['status'], 'published')

    def test_scheduled_posts_go_out_on_time(self):
        from .service import publish_due
        aid = self.connect()
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = self.as_(self.se).post('/api/social/posts/', {'text': 'Later', 'account_ids': [aid],
                                                          'action': 'schedule', 'scheduled_at': when})
        self.assertEqual(r.data['status'], 'scheduled')
        publish_due()
        self.assertEqual(FakeNet.sent, [])
        SocialPost.objects.update(scheduled_at=timezone.now() - timedelta(minutes=1))
        publish_due()
        self.assertEqual(SocialPost.objects.get().status, 'published')

    def test_roles_setting(self):
        self.as_(self.boss).patch('/api/social/settings/', {'poster_roles': ['author']}, format='json')
        self.assertEqual(self.as_(self.se).get('/api/social/overview/').status_code, 403)
        self.assertEqual(self.as_(self.author).get('/api/social/overview/').status_code, 200)


class PublisherRequestTests(TestCase):
    """What actually gets sent to the networks (HTTP mocked)."""

    def acc(self, platform, config, secrets):
        a = SocialAccount(platform=platform, name='T', config=config)
        a.secrets = secrets
        return a

    def test_telegram_text_and_photo(self):
        acc = self.acc('telegram', {'chat_id': '@hux'}, {'bot_token': 'TOK'})
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {'ok': True, 'result': {'message_id': 7, 'chat': {'username': 'hux'}}}
        with mock.patch('apps.social.publishers.requests.post', return_value=ok) as post:
            ext, url = publishers.Telegram.publish(acc, publishers.PostContext('Hello', link='https://h.com'))
            self.assertEqual((ext, url), ('7', 'https://t.me/hux/7'))
            self.assertIn('/botTOK/sendMessage', post.call_args.args[0])
            self.assertEqual(post.call_args.kwargs['json']['text'], 'Hello\n\nhttps://h.com')
            img = publishers.Media('https://cdn/x.jpg', lambda: b'x')
            publishers.Telegram.publish(acc, publishers.PostContext('Pic', images=[img]))
            self.assertIn('/sendPhoto', post.call_args.args[0])
            self.assertEqual(post.call_args.kwargs['json']['photo'], 'https://cdn/x.jpg')

    def test_facebook_text_post(self):
        acc = self.acc('facebook', {'page_id': '123'}, {'page_token': 'PT'})
        ok = mock.Mock(status_code=200)
        ok.json.return_value = {'id': '123_456'}
        with mock.patch('apps.social.publishers.requests.post', return_value=ok) as post:
            ext, url = publishers.Facebook.publish(acc, publishers.PostContext('Hi', link='https://h.com'))
        self.assertEqual(ext, '123_456')
        self.assertTrue(post.call_args.args[0].endswith('/123/feed'))
        self.assertEqual(post.call_args.kwargs['data']['link'], 'https://h.com')

    def test_instagram_needs_media_and_errors_are_readable(self):
        acc = self.acc('instagram', {'ig_user_id': '9'}, {'access_token': 'T'})
        with self.assertRaises(publishers.PublishError) as e:
            publishers.Instagram.publish(acc, publishers.PostContext('No picture'))
        self.assertIn('needs an image', str(e.exception))
        bad = mock.Mock(status_code=400)
        bad.json.return_value = {'error': {'message': 'Invalid OAuth access token'}}
        with mock.patch('apps.social.publishers.requests.get', return_value=bad):
            with self.assertRaises(publishers.PublishError) as e:
                publishers.Instagram.verify(acc)
        self.assertIn('Invalid OAuth access token', str(e.exception))

    def test_linkedin_escapes_reserved_characters(self):
        self.assertEqual(publishers._li_escape('Hi (new) #book @me'), 'Hi \\(new\\) \\#book \\@me')
