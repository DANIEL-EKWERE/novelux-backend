from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.stories.models import Story
from .models import Chapter

User = get_user_model()


class LockFromChapterTests(TestCase):
    """A story's "lock from chapter N" must hold for every chapter, including
    ones added or saved after the lock was set (authors reported a mix of
    locked and free chapters inside the locked range)."""

    def setUp(self):
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.story = Story.objects.create(author=self.author, title='Tale', slug='tale', lock_from_chapter=3)

    def add(self, n, **extra):
        return Chapter.objects.create(story=self.story, title=f'Ch {n}', chapter_number=n, **extra)

    def locks(self):
        return dict(Chapter.objects.filter(story=self.story).values_list('chapter_number', 'is_locked'))

    def test_chapters_added_after_the_lock_follow_it(self):
        for n in range(1, 7):
            self.add(n)
        self.assertEqual(self.locks(), {1: False, 2: False, 3: True, 4: True, 5: True, 6: True})

    def test_app_switch_cannot_unlock_a_chapter_in_the_locked_range(self):
        ch = self.add(4, is_locked=False)          # the app's lock switch was off
        self.assertTrue(ch.is_locked)
        ch.is_locked = False
        ch.save()
        ch.refresh_from_db()
        self.assertTrue(ch.is_locked)

    def test_partial_saves_still_apply_the_rule(self):
        ch = self.add(5)
        Chapter.objects.filter(pk=ch.pk).update(is_locked=False)   # stale data
        ch.refresh_from_db()
        ch.title = 'Renamed'
        ch.save(update_fields=['title'])
        ch.refresh_from_db()
        self.assertTrue(ch.is_locked)

    def test_no_lock_setting_keeps_manual_locks(self):
        free = Story.objects.create(author=self.author, title='Free', slug='free')
        ch = Chapter.objects.create(story=free, title='One', chapter_number=1, is_locked=True)
        ch.refresh_from_db()
        self.assertTrue(ch.is_locked)

    def test_repair_migration_fixes_existing_books(self):
        import importlib
        from django.apps import apps as django_apps
        for n in range(1, 6):
            self.add(n)
        Chapter.objects.filter(story=self.story, chapter_number__in=[4, 5]).update(is_locked=False)
        migration = importlib.import_module('apps.chapters.migrations.0012_reapply_story_locks')
        migration.reapply_locks(django_apps, None)
        self.assertEqual(self.locks(), {1: False, 2: False, 3: True, 4: True, 5: True})


class AdminBulkActionTests(TestCase):
    """Shortcuts in the admin "Action" dropdown, run through the real changelist."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@x.com', username='admin', password='x')
        self.client.force_login(self.admin)
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.story = Story.objects.create(author=self.author, title='Tale', slug='tale')
        self.chapters = [Chapter.objects.create(story=self.story, title=f'Ch {n}', chapter_number=n)
                         for n in range(1, 5)]

    def act(self, model_url, action, ids):
        from django.urls import reverse
        app, model = model_url.split('/')
        url = reverse(f'admin:{app}_{model}_changelist')   # admin lives at a custom path
        return self.client.post(url, {'action': action, '_selected_action': ids},
                                secure=True, follow=True)

    def test_chapter_lock_and_publish(self):
        ids = [c.pk for c in self.chapters[2:]]
        self.act('chapters/chapter', 'lock_chapters', ids)
        self.act('chapters/chapter', 'publish_chapters', ids)
        rows = dict(Chapter.objects.values_list('chapter_number', 'is_locked'))
        self.assertEqual(rows, {1: False, 2: False, 3: True, 4: True})
        self.assertEqual(Chapter.objects.filter(is_published=True, status=Chapter.STATUS_PUBLISHED).count(), 2)
        self.act('chapters/chapter', 'unpublish_chapters', ids)
        self.assertEqual(Chapter.objects.filter(is_published=True).count(), 0)

    def test_story_lock_all_then_unlock_all(self):
        self.act('stories/story', 'lock_all_chapters', [self.story.pk])
        self.assertEqual(Chapter.objects.filter(is_locked=True).count(), 4)
        self.story.refresh_from_db()
        self.assertEqual(self.story.lock_from_chapter, 1)
        self.act('stories/story', 'unlock_all_chapters', [self.story.pk])
        self.assertEqual(Chapter.objects.filter(is_locked=True).count(), 0)

    def test_story_status_and_explicit(self):
        self.act('stories/story', 'mark_completed', [self.story.pk])
        self.act('stories/story', 'mark_explicit', [self.story.pk])
        self.story.refresh_from_db()
        self.assertEqual((self.story.status, self.story.is_completed, self.story.is_explicit),
                         ('completed', True, True))

    def test_ban_user(self):
        self.act('users/user', 'ban_users', [self.author.pk])
        self.author.refresh_from_db()
        self.assertTrue(self.author.is_banned)


class BookDownloadTests(TestCase):
    """VIPs download free; others buy the unbought locked chapters with
    purchased coins at 10% off, which also unlocks them online."""

    def setUp(self):
        from rest_framework.test import APIClient
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='reader', password='x')
        self.story = Story.objects.create(author=self.author, title='Tale', slug='tale', lock_from_chapter=3)
        for n in range(1, 6):     # chapters 3-5 locked at 20 coins → 18 each after discount
            Chapter.objects.create(story=self.story, title=f'Ch {n}', chapter_number=n,
                                   coin_cost=20, is_published=True)
        self.client = APIClient()
        self.client.force_authenticate(self.reader)
        self.url = '/api/chapters/tale/chapters/download/'

    def test_quote_is_unbought_locked_chapters_less_ten_percent(self):
        from .models import ChapterUnlock
        ChapterUnlock.objects.create(user=self.reader, chapter=Chapter.objects.get(chapter_number=3), coins_spent=20)
        res = self.client.get(self.url)
        self.assertEqual((res.data['price'], res.data['full_price'], res.data['chapters_to_buy'],
                          res.data['discount_pct']), (36, 40, 2, 10))

    def test_buying_uses_purchased_coins_only(self):
        self.reader.coin_balance, self.reader.bonus_balance = 10, 500
        self.reader.save()
        res = self.client.post(self.url, {'method': 'buy'})
        self.assertEqual(res.status_code, 402)
        self.reader.refresh_from_db()
        self.assertEqual((self.reader.coin_balance, self.reader.bonus_balance), (10, 500))

    def test_buying_unlocks_chapters_and_holds_author_share(self):
        from .models import ChapterUnlock, ChapterUnlockEarning
        self.reader.coin_balance = 100
        self.reader.save()
        res = self.client.post(self.url, {'method': 'buy', 'price': 54})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data['coins_spent'], len(res.data['chapters'])), (54, 5))
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.coin_balance, 46)
        self.assertEqual(ChapterUnlock.objects.filter(user=self.reader).count(), 3)
        earnings = ChapterUnlockEarning.objects.filter(author=self.author)
        self.assertEqual([e.status for e in earnings], ['held'] * 3)
        self.assertEqual(sum(e.coins for e in earnings), 3 * int(18 * 0.20))
        # Second download is free — everything is owned now
        self.assertEqual(self.client.post(self.url).data['coins_spent'], 0)

    def test_old_app_is_never_charged(self):
        self.reader.coin_balance = 100
        self.reader.save()
        for method in ('ad', 'coins'):
            res = self.client.post(self.url, {'method': method})
            self.assertEqual(res.status_code, 409)
            self.assertTrue(res.data['update_required'])
        self.assertEqual(self.client.post(self.url, {'method': 'buy', 'price': 99}).status_code, 409)
        self.reader.refresh_from_db()
        self.assertEqual(self.reader.coin_balance, 100)

    def test_vip_downloads_free_and_reads_are_recorded(self):
        from .models import VipChapterRead
        self.reader.is_vip = True
        self.reader.save()
        res = self.client.post(self.url)
        self.assertEqual((res.status_code, res.data['coins_spent']), (200, 0))
        self.assertEqual(VipChapterRead.objects.filter(user=self.reader).count(), 3)

    def test_exclusive_books_are_vip_only(self):
        Story.objects.filter(pk=self.story.pk).update(is_exclusive=True)
        self.reader.coin_balance = 100
        self.reader.save()
        self.assertEqual(self.client.post(self.url, {'method': 'buy'}).status_code, 403)


class VipPayoutTests(TestCase):
    """Monthly pool per VIP reader: authors get the value of chapters read, up
    to what the reader's subscription covers; any excess is recorded, not paid."""

    def setUp(self):
        from datetime import date, datetime
        from django.utils import timezone
        from apps.coins.models import Purchase, SubscriptionPlan
        self.month = date(2026, 9, 1)
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.story = Story.objects.create(author=self.author, title='Tale', slug='tale', lock_from_chapter=1)
        self.chapters = [Chapter.objects.create(story=self.story, title=f'Ch {n}', chapter_number=n,
                                                coin_cost=50, is_published=True) for n in range(1, 11)]
        self.plan = SubscriptionPlan.objects.create(plan_id='month', label='Month', price_usd=10,
                                                    coins_per_month=0, duration_days=30)
        self.paid_at = timezone.make_aware(datetime(2026, 9, 1))
        self.Purchase = Purchase

    def vip(self, name, usd):
        u = User.objects.create_user(email=f'{name}@x.com', username=name, password='x')
        p = self.Purchase.objects.create(user=u, purchase_type='subscription', subscription_plan=self.plan,
                                         amount_paid_usd=usd, status='completed')
        self.Purchase.objects.filter(pk=p.pk).update(completed_at=self.paid_at)
        return u

    def read(self, user, chapters):
        from .models import VipChapterRead
        for c in chapters:
            VipChapterRead.objects.create(user=user, chapter=c, author=self.author,
                                          coin_cost=c.coin_cost, month=self.month)

    def test_light_reader_pays_value_and_records_excess(self):
        from .vip_payouts import run_vip_payout
        u = self.vip('light', 10)             # pool: 10 × 30/30 days in Sept × 0.85 × 0.20 = $1.70
        self.read(u, self.chapters[:2])       # value: 2 × 50 × 0.20 / 100 = $0.20
        run = run_vip_payout(self.month)
        [e] = run.earnings.all()
        self.assertEqual((e.coins, e.reads, e.status), (20, 2, 'held'))
        self.assertEqual(str(run.excess_ignored_usd), '1.50')
        self.assertEqual((run.readers_with_excess, run.readers_scaled_down), (1, 0))

    def test_heavy_reader_is_scaled_to_their_pool(self):
        from .vip_payouts import run_vip_payout
        u = self.vip('heavy', 1)              # pool: $0.17
        self.read(u, self.chapters)           # value: $1.00
        run = run_vip_payout(self.month)
        self.assertEqual(run.earnings.get().coins, 17)
        self.assertEqual((run.readers_scaled_down, str(run.excess_ignored_usd)), (1, '0.00'))

    def test_month_runs_once_and_release_pays_author(self):
        from .vip_payouts import run_vip_payout
        self.read(self.vip('v', 10), self.chapters[:2])
        run = run_vip_payout(self.month)
        self.assertIsNone(run_vip_payout(self.month))
        e = run.earnings.get()
        self.assertTrue(e.release())
        self.assertFalse(e.release())
        self.author.refresh_from_db()
        self.assertEqual(self.author.coin_balance, 20)

    def test_record_vip_read_skips_bought_and_own_chapters(self):
        from .models import ChapterUnlock, VipChapterRead, record_vip_read
        reader = User.objects.create_user(email='r@x.com', username='r', password='x', is_vip=True)
        ChapterUnlock.objects.create(user=reader, chapter=self.chapters[0], coins_spent=50)
        for c in self.chapters[:3]:
            record_vip_read(reader, c)
            record_vip_read(reader, c)        # same month counts once
            record_vip_read(self.author, c)   # author reading their own book
        self.assertEqual(VipChapterRead.objects.count(), 2)


class ChapterHtmlCleanTests(TestCase):
    """Author-centre content (typed <div> lines, Google Docs/Word pastes) is
    saved as the same plain paragraphs bulk upload produces."""

    def clean(self, html):
        from .html_clean import clean_chapter_html
        out = clean_chapter_html(html)
        self.assertEqual(clean_chapter_html(out), out)    # idempotent
        return out

    def test_typed_div_lines_become_paragraphs(self):
        self.assertEqual(self.clean('<div>One.&nbsp;</div><div><br></div><div>Two <b>bold</b>.</div>'),
                         '<p>One.</p><p>Two <strong>bold</strong>.</p>')

    def test_google_docs_paste_loses_styles_keeps_formatting(self):
        html = ('<b style="font-weight:normal;" id="docs-internal-guid-1"><p dir="ltr" style="line-height:1.38">'
                '<span style="font-size:11pt;font-family:Arial;color:rgb(0,0,0);white-space:pre-wrap;">Plain</span></p>'
                '<br><p dir="ltr"><span style="font-weight:700">Bold</span> and '
                '<span style="font-style:italic">italic</span></p></b>')
        self.assertEqual(self.clean(html), '<p>Plain</p><p><strong>Bold</strong> and <em>italic</em></p>')

    def test_bulk_upload_html_is_unchanged(self):
        html = '<h1>Chapter 1</h1><p>He came <strong>home</strong> &amp; slept.</p><ul><li>one</li></ul>'
        self.assertEqual(self.clean(html), html)

    def test_line_breaks_and_formatting_across_paragraphs(self):
        self.assertEqual(self.clean('<b>A<br>B<br><br>C</b>'),
                         '<p><strong>A<br>B</strong></p><p><strong>C</strong></p>')

    def test_plain_text(self):
        self.assertEqual(self.clean('It&rsquo;s one\n\nTwo'), '<p>It’s one</p><p>Two</p>')

    def test_saving_a_chapter_cleans_it(self):
        author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        story = Story.objects.create(author=author, title='Tale', slug='tale')
        ch = Chapter.objects.create(story=story, title='One', chapter_number=1,
                                    content='<div style="color:#000">Hi</div><div><br></div><div>there</div>')
        ch.refresh_from_db()
        self.assertEqual(ch.content, '<p>Hi</p><p>there</p>')


class ChapterListPageSizeTests(TestCase):
    """The app loads the whole chapter list with ?page_size= — the story
    details page showed only 10 chapters when this was ignored."""

    def test_page_size_param(self):
        from rest_framework.test import APIClient
        author = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        story = Story.objects.create(author=author, title='Tale', slug='tale')
        for n in range(1, 26):
            Chapter.objects.create(story=story, title=f'Ch {n}', chapter_number=n, is_published=True)
        client = APIClient()
        full = client.get('/api/chapters/tale/chapters/?page=1&page_size=500').data
        self.assertEqual((full['count'], len(full['results'])), (25, 25))
        self.assertEqual(len(client.get('/api/chapters/tale/chapters/').data['results']), 10)
