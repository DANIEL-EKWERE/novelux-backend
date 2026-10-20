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
