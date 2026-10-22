from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.chapters.models import Chapter, ChapterUnlockEarning
from apps.stories.models import Story
from apps.tips.models import Tip
from apps.users.models import AuthorProfile
from .models import AuthorEditorLink

User = get_user_model()


class SEAuthorAndEarningsTests(TestCase):
    def setUp(self):
        self.se       = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.other_se = User.objects.create_user(email='se2@x.com', username='se2', password='x', role='se')
        self.author   = User.objects.create_user(email='a@x.com', username='author', password='x', role='author')
        self.stranger = User.objects.create_user(email='b@x.com', username='stranger', password='x', role='author')
        self.reader   = User.objects.create_user(email='r@x.com', username='reader', password='x')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        AuthorEditorLink.objects.create(author=self.stranger, assigned_se=self.other_se)
        self.profile = AuthorProfile.objects.create(user=self.author, pen_name='Pen')

        self.story   = Story.objects.create(author=self.author, title='Tale', slug='tale')
        chapter      = Chapter.objects.create(story=self.story, title='One', chapter_number=1)
        self.unlock  = ChapterUnlockEarning.objects.create(
            author=self.author, chapter=chapter, coins=4, coins_spent=20)
        self.tip     = Tip.objects.create(
            sender=self.reader, recipient=self.author, story=self.story,
            coins_amount=100, gift_label='Coffee', author_coins_earned=25)

        self.client = APIClient()
        self.client.force_authenticate(self.se)

    # ── author details ───────────────────────────────────────────────────────

    def test_author_detail_lists_books(self):
        res = self.client.get(f'/api/editorial/authors/{self.author.pk}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['pen_name'], 'Pen')
        self.assertEqual([b['title'] for b in res.data['books']], ['Tale'])
        self.assertEqual(res.data['books'][0]['chapters_total'], 1)

    def test_se_cannot_see_another_se_author(self):
        res = self.client.get(f'/api/editorial/authors/{self.stranger.pk}/')
        self.assertEqual(res.status_code, 404)

    def test_se_edits_only_allowed_fields(self):
        res = self.client.patch(f'/api/editorial/authors/{self.author.pk}/', {
            'first_name': 'Ada', 'pen_name': 'New Pen', 'bio': 'Hi',
            'email': 'hacked@x.com', 'role': 'ce',
        }, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.author.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual((self.author.first_name, self.author.bio, self.profile.pen_name),
                         ('Ada', 'Hi', 'New Pen'))
        self.assertEqual((self.author.email, self.author.role), ('a@x.com', 'author'))

    # ── earnings approval ────────────────────────────────────────────────────

    def test_pending_earnings_breakdown(self):
        res = self.client.get('/api/editorial/earnings/pending/')
        self.assertEqual(res.status_code, 200, res.data)
        [entry] = res.data['authors']
        self.assertEqual((entry['author_id'], entry['count'], entry['coins']), (self.author.pk, 2, 29))
        self.assertEqual({i['type'] for i in entry['items']}, {'unlock', 'tip'})

    def test_approve_one_item(self):
        res = self.client.post('/api/editorial/earnings/review/', {
            'action': 'approve', 'author_id': self.author.pk,
            'items': [{'type': 'tip', 'id': self.tip.pk}],
        }, format='json')
        self.assertEqual(res.data['processed'], 1)
        self.author.refresh_from_db(); self.tip.refresh_from_db(); self.unlock.refresh_from_db()
        self.assertEqual(self.author.coin_balance, 25)
        self.assertEqual(self.tip.earning_status, Tip.EARNING_RELEASED)
        self.assertEqual(self.unlock.status, ChapterUnlockEarning.STATUS_HELD)

    def test_approve_all_pays_once(self):
        for _ in range(2):
            self.client.post('/api/editorial/earnings/review/', {'action': 'approve'}, format='json')
        self.author.refresh_from_db()
        self.assertEqual(self.author.coin_balance, 29)
        self.assertEqual(self.client.get('/api/editorial/earnings/pending/').data['authors'], [])

    def test_approve_all_skips_other_se_authors(self):
        Tip.objects.create(sender=self.reader, recipient=self.stranger, story=self.story,
                           coins_amount=100, gift_label='Coffee', author_coins_earned=25)
        self.client.post('/api/editorial/earnings/review/', {'action': 'approve'}, format='json')
        self.stranger.refresh_from_db()
        self.assertEqual(self.stranger.coin_balance, 0)

    def test_reject_never_pays(self):
        self.client.post('/api/editorial/earnings/review/', {'action': 'reject'}, format='json')
        self.client.post('/api/editorial/earnings/review/', {'action': 'approve'}, format='json')
        self.author.refresh_from_db()
        self.assertEqual(self.author.coin_balance, 0)

    def test_readers_cannot_use_endpoints(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get('/api/editorial/earnings/pending/').status_code, 403)


class ContractTemplateAndSendTests(TestCase):
    def setUp(self):
        from apps.notifications.models import Notification  # noqa: F401  (app must be installed)
        self.ce       = User.objects.create_user(email='ce@x.com', username='ce', password='x', role='ce')
        self.se       = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.other_se = User.objects.create_user(email='se2@x.com', username='se2', password='x', role='se')
        self.author   = User.objects.create_user(email='a@x.com', username='author', password='x',
                                                 role='author', first_name='Ada', last_name='Obi')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        AuthorProfile.objects.create(user=self.author, pen_name='Ada Rose')
        self.story = Story.objects.create(author=self.author, title='Moon <Tale>', slug='moon-tale',
                                          contract_status='contract_sent')
        self.client = APIClient()
        self.client.force_authenticate(self.se)

    def test_default_template_is_seeded(self):
        res = self.client.get('/api/editorial/contract-templates/')
        names = [t['name'] for t in res.data['templates']]
        self.assertIn('Standard contract', names)

    def test_template_html_is_sanitised(self):
        res = self.client.post('/api/editorial/contract-templates/', {
            'name': 'Mine', 'body': '<p onclick="x()">Hi {book_title}</p><script>alert(1)</script>',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertNotIn('script', res.data['body'])
        self.assertNotIn('onclick', res.data['body'])

    def test_se_sends_contract_with_template(self):
        from apps.editorial.models import ContractApplication, ContractTemplate
        from apps.notifications.models import Notification
        t = ContractTemplate.objects.create(name='Excl', created_by=self.se,
                                            body='<p>{pen_name} / {book_title}</p><p>{licence_clause}</p>')
        res = self.client.post('/api/editorial/stories/moon-tale/send-contract/', {
            'template_id': t.pk, 'contract_type': 'exclusive', 'note': 'Welcome!'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.story.refresh_from_db()
        app = ContractApplication.objects.get(story=self.story)
        self.assertEqual((self.story.contract_status, app.template, app.contract_type),
                         ('awaiting_signature', t, 'exclusive'))
        self.assertIn('Ada Rose / Moon &lt;Tale&gt;', app.contract_body)   # escaped
        self.assertIn('<strong>exclusive</strong>', app.contract_body)
        self.assertTrue(Notification.objects.filter(recipient=self.ce, title='Contract sent by SE').exists())

        # Editing the template later doesn't change the contract already sent
        t.body = '<p>Changed</p>'; t.save()
        app.refresh_from_db()
        self.assertIn('Ada Rose', app.contract_body)

    def test_ce_sends_for_any_author_without_self_notification(self):
        from apps.notifications.models import Notification
        self.client.force_authenticate(self.ce)
        res = self.client.post('/api/editorial/stories/moon-tale/send-contract/', {}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.story.refresh_from_db()
        self.assertEqual(self.story.contract_status, 'awaiting_signature')
        self.assertFalse(Notification.objects.filter(recipient=self.ce, title='Contract sent by SE').exists())

    def test_se_cannot_send_for_another_se_author(self):
        self.client.force_authenticate(self.other_se)
        res = self.client.post('/api/editorial/stories/moon-tale/send-contract/', {}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_preview_matches_template(self):
        res = self.client.post('/api/editorial/contracts/preview/', {
            'story_slug': 'moon-tale', 'body': '<p>{author_name} — {contract_type}</p>',
            'contract_type': 'non_exclusive'}, format='json')
        self.assertEqual(res.data['html'], '<p>Ada Obi — Non-Exclusive</p>')

    def test_only_creator_or_ce_can_edit(self):
        from apps.editorial.models import ContractTemplate
        t = ContractTemplate.objects.create(name='Mine', body='<p>x</p>', created_by=self.se)
        self.client.force_authenticate(self.other_se)
        res = self.client.patch(f'/api/editorial/contract-templates/{t.pk}/', {'name': 'Hijack'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.client.force_authenticate(self.ce)
        res = self.client.patch(f'/api/editorial/contract-templates/{t.pk}/', {'name': 'Fixed'}, format='json')
        self.assertEqual(res.status_code, 200)

    def test_author_sign_page_shows_frozen_text(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.client.post('/api/editorial/stories/moon-tale/send-contract/', {}, format='json')
        web = self.client_class()
        web.cookies['nux_access'] = str(RefreshToken.for_user(self.author).access_token)
        web.cookies['nux_username'] = self.author.username
        html = web.get('/my-books/moon-tale/contract/', secure=True).content.decode()
        self.assertIn('writing as <strong>Ada Rose</strong>', html)


class WebCookieAuthTests(TestCase):
    """Web pages must identify users from verified tokens, never from the
    plain nux_username / nux_role cookies (which anyone can set)."""

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        self.ce     = User.objects.create_user(email='ce@x.com', username='ce', password='x', role='ce')
        self.author = User.objects.create_user(email='a@x.com', username='victim', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='mallory', password='x')
        Story.objects.create(author=self.author, title='Secret', slug='secret', contract_status='awaiting_signature')
        self.reader_access = str(RefreshToken.for_user(self.reader).access_token)
        self.author_refresh = str(RefreshToken.for_user(self.author))

    def _get(self, path, **cookies):
        c = self.client_class()
        for k, v in cookies.items():
            c.cookies[k] = v
        return c.get(path, secure=True)

    def test_forged_role_cookie_cannot_open_ce_dashboard(self):
        res = self._get('/editorial/ce/', nux_access='not-a-real-token', nux_role='ce')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login/', res['Location'])

    def test_real_user_with_forged_role_is_denied(self):
        res = self._get('/editorial/ce/', nux_access=self.reader_access, nux_role='ce')
        self.assertIn('access_denied', res['Location'])

    def test_username_cookie_cannot_impersonate_author(self):
        res = self._get('/my-books/secret/contract/', nux_access=self.reader_access, nux_username='victim')
        self.assertEqual(res.status_code, 404)   # mallory has no story "secret"
        res = self._get('/my-books/secret/contract/', nux_access='junk', nux_username='victim')
        self.assertEqual(res.status_code, 302)

    def test_author_dashboard_ignores_username_cookie(self):
        res = self._get('/dashboard/', nux_access=self.reader_access, nux_username='victim')
        self.assertNotContains(res, 'Secret', status_code=res.status_code)

    def test_expired_access_cookie_is_renewed(self):
        # Access cookie gone (1h max_age) but session valid: the page gets a
        # fresh token and the cookie is set again — no reload/refresh needed.
        res = self._get('/my-books/secret/contract/', nux_refresh=self.author_refresh)
        self.assertEqual(res.status_code, 200)
        self.assertIn('nux_access', res.cookies)
        fresh = res.cookies['nux_access'].value
        self.assertTrue(fresh)
        self.assertContains(res, f'content="{fresh}"')

    def test_valid_access_cookie_is_not_reissued(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        access = str(RefreshToken.for_user(self.author).access_token)
        res = self._get('/my-books/secret/contract/', nux_access=access)
        self.assertNotIn('nux_access', res.cookies)

    def test_valid_refresh_token_still_identifies_user(self):
        # Access token expired/missing, refresh token valid → page still loads
        res = self._get('/my-books/secret/contract/', nux_refresh=self.author_refresh)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Secret')


class EarningReaderFraudTests(TestCase):
    """Each held earning names the reader whose money it is, with warning
    flags, and the SE can open that reader's full profile."""

    def setUp(self):
        from apps.chapters.models import ChapterUnlock
        from apps.users.models import UserDevice
        self.se     = User.objects.create_user(email='se@x.com', username='se', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='author', password='x',
                                               role='author', registration_ip='10.0.0.1')
        self.other  = User.objects.create_user(email='o@x.com', username='other', password='x', role='author')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        # A sock puppet: same IP and phone as the author, never bought coins
        self.reader = User.objects.create_user(email='r@x.com', username='puppet', password='x',
                                               registration_ip='10.0.0.1', coin_balance=80, bonus_balance=12)
        UserDevice.objects.create(user=self.author, device_id='PHONE-1', platform='android')
        UserDevice.objects.create(user=self.reader, device_id='PHONE-1', platform='android')

        self.story = Story.objects.create(author=self.author, title='Tale', slug='tale')
        chapter = Chapter.objects.create(story=self.story, title='One', chapter_number=1)
        unlock = ChapterUnlock.objects.create(user=self.reader, chapter=chapter, coins_spent=300)
        self.earning = ChapterUnlockEarning.objects.create(
            author=self.author, chapter=chapter, unlock=unlock, coins=60, coins_spent=300)

        self.client = APIClient()
        self.client.force_authenticate(self.se)

    def test_items_name_the_reader_with_flags(self):
        [entry] = self.client.get('/api/editorial/earnings/pending/').data['authors']
        [item] = entry['items']
        self.assertEqual(item['reader']['username'], 'puppet')
        self.assertTrue({'same_ip_author', 'same_device_author', 'new_account', 'no_purchases'}
                        <= set(item['reader']['flags']))
        self.assertEqual(entry['flagged'], 1)

    def test_reader_detail(self):
        res = self.client.get(f'/api/editorial/earnings/reader/{self.reader.pk}/?author_id={self.author.pk}')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual((res.data['wallet']['coin_balance'], res.data['wallet']['bonus_balance']), (80, 12))
        self.assertIn('one_author', res.data['flags'])
        self.assertEqual([a['username'] for a in res.data['same_ip_accounts']], ['author'])
        self.assertEqual(res.data['devices'][0]['other_accounts'][0]['username'], 'author')
        self.assertEqual(res.data['history_with_author'][0]['status'], 'held')

    def test_se_only_sees_readers_who_paid_their_authors(self):
        stranger = User.objects.create_user(email='s@x.com', username='s', password='x')
        self.assertEqual(self.client.get(f'/api/editorial/earnings/reader/{stranger.pk}/').status_code, 404)

    def test_vip_earnings_are_in_the_queue(self):
        from datetime import date
        from apps.chapters.models import VipPayoutRun, VipEarning
        run = VipPayoutRun.objects.create(month=date(2026, 9, 1))
        vip = VipEarning.objects.create(run=run, author=self.author, reads=3, usd='0.30', coins=30)
        [entry] = self.client.get('/api/editorial/earnings/pending/').data['authors']
        self.assertIn('vip', {i['type'] for i in entry['items']})
        res = self.client.post('/api/editorial/earnings/review/', {
            'action': 'approve', 'items': [{'type': 'vip', 'id': vip.pk}]}, format='json')
        self.assertEqual(res.data['processed'], 1)
        self.author.refresh_from_db()
        self.assertEqual(self.author.coin_balance, 30)
