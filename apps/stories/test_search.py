from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Story, Tag

User = get_user_model()


class RankedSearchTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='a@x.com', username='inkqueen', password='x')
        other = User.objects.create_user(email='b@x.com', username='someone', password='x')
        mk = lambda title, desc='', who=other, views=0, status='ongoing': Story.objects.create(
            author=who, title=title, slug=title.lower().replace(' ', '-').replace("'", ''),
            description=desc, total_views=views, status=status)
        self.exact   = mk("The Alpha's Bride")
        self.prefix  = mk("The Alpha's Bride Returns", views=999)
        self.words   = mk("Bride of the Cold Alpha")
        self.blurb   = mk('Moonlight', desc="She became the alpha's bride overnight.")
        self.noise   = mk('Unrelated', desc='The alpha wolf and a bride were mentioned separately.')
        self.by_auth = mk('Crimson Vow', who=self.author)
        self.tagged  = mk('Pack Law')
        self.tagged.tags.add(Tag.objects.create(name='Werewolf', slug='werewolf'))
        self.draft   = mk("The Alpha's Bride Draft", status='draft')

    def search(self, q, **extra):
        res = APIClient().get('/api/stories/', {'search': q, **extra})
        self.assertEqual(res.status_code, 200, res.data)
        data = res.data['results'] if isinstance(res.data, dict) else res.data
        return [s['title'] for s in data]

    def test_exact_title_first_then_prefix_then_words_then_synopsis(self):
        self.assertEqual(self.search("the alpha's bride"), [
            "The Alpha's Bride", "The Alpha's Bride Returns", 'Moonlight',
        ])

    def test_scattered_words_only_match_titles_not_synopses(self):
        titles = self.search('alpha bride')
        # Every title holding both words ties, then the most-read leads
        self.assertEqual(titles[0], "The Alpha's Bride Returns")
        self.assertEqual(set(titles), {
            "The Alpha's Bride", "The Alpha's Bride Returns", 'Bride of the Cold Alpha',
        })

    def test_author_and_tag_and_code(self):
        self.assertEqual(self.search('inkqueen'), ['Crimson Vow'])
        self.assertEqual(self.search('werewolf'), ['Pack Law'])
        self.assertEqual(self.search(self.tagged.book_code), ['Pack Law'])

    def test_short_query_ignores_synopsis(self):
        self.assertNotIn('Unrelated', self.search('the'))
