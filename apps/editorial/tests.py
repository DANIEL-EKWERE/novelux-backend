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
        # Still kept out — sent to their own page instead of the CE dashboard
        self.assertEqual((res.status_code, res['Location']), (302, '/welcome/'))

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


class CEPhaseOneTests(TestCase):
    """Chief-editor fixes: real take-downs and bans, deleting announcements,
    transferring authors, deactivating editors, issue counts, cancelling
    contracts."""

    def setUp(self):
        from unittest import mock
        self.ce = User.objects.create_user(email='ce@x.com', username='chief', password='x', role='ce')
        self.se = User.objects.create_user(email='se@x.com', username='vora', password='x', role='se')
        self.se2 = User.objects.create_user(email='se2@x.com', username='kay', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.author2 = User.objects.create_user(email='b@x.com', username='bola', password='x', role='author')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        AuthorEditorLink.objects.create(author=self.author2, assigned_se=self.se)
        self.story = Story.objects.create(author=self.author, title='Copied Tale', slug='copied', status='ongoing')
        self.story2 = Story.objects.create(author=self.author, title='Second', slug='second', status='ongoing')
        self.ch = Chapter.objects.create(story=self.story, title='One', chapter_number=1, is_published=True)
        self.c = APIClient()
        self.c.force_authenticate(self.ce)
        self.push = mock.patch('apps.notifications.services.notify_user')
        self.push.start()
        self.addCleanup(self.push.stop)

    def public_slugs(self):
        r = APIClient().get('/api/stories/')
        rows = r.data['results'] if isinstance(r.data, dict) else r.data
        return {s['slug'] for s in rows}

    def notes(self, user):
        from apps.notifications.models import Notification
        return list(Notification.objects.filter(recipient=user).values_list('title', flat=True))

    def test_take_down_flag_hides_the_book_and_tells_the_author(self):
        from .models import ContentFlag
        flag = ContentFlag.objects.create(chapter=self.ch, flagged_by=self.se, flag_type='plagiarism', description='x')
        self.assertIn('copied', self.public_slugs())
        r = self.c.post(f'/api/editorial/ce/flags/{flag.pk}/resolve/', {'action': 'take_down', 'note': 'Copied'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertNotIn('copied', self.public_slugs())
        self.assertIn('second', self.public_slugs())                       # only that book
        self.assertEqual(APIClient().get('/api/stories/copied/').status_code, 404)
        self.assertIn('Your book was taken down', self.notes(self.author))
        flag.refresh_from_db()
        self.assertTrue(flag.resolved)

    def test_ban_from_reader_report_removes_all_books(self):
        from apps.stories.models import ContentReport
        rep = ContentReport.objects.create(story=self.story, reason='copyright', details='stolen')
        d = self.c.get('/api/editorial/ce/reader-reports/').data['results'][0]
        self.assertEqual(d['author'], 'amaka')
        r = self.c.post(f'/api/editorial/ce/reader-reports/{rep.pk}/action/', {'action': 'ban', 'note': 'Plagiarism'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.author.refresh_from_db()
        self.assertTrue(self.author.is_banned)
        self.assertFalse({'copied', 'second'} & self.public_slugs())
        self.assertIn('Your account has been banned', self.notes(self.author))
        self.assertEqual(self.c.get('/api/editorial/ce/reader-reports/').data['results'], [])

    def test_delete_announcement_removes_it_from_inboxes(self):
        from apps.notifications.models import Notification
        r = self.c.post('/api/editorial/ce/announcements/', {'title': 'Oops', 'body': 'Wrong text', 'target': 'authors'}, format='json')
        self.assertEqual(Notification.objects.filter(title='📢 Oops').count(), 2)
        r = self.c.delete(f'/api/editorial/ce/announcements/{r.data["id"]}/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(Notification.objects.filter(title='📢 Oops').count(), 0)
        self.assertEqual(self.c.get('/api/editorial/ce/announcements/').data['results'], [])

    def test_transfer_then_deactivate(self):
        r = self.c.post(f'/api/editorial/ce/editors/{self.se.pk}/active/', {'active': False}, format='json')
        self.assertEqual(r.status_code, 400)                                 # still has authors
        self.assertEqual(len(self.c.get(f'/api/editorial/ce/editors/{self.se.pk}/authors/').data['results']), 2)
        r = self.c.post('/api/editorial/ce/transfer-authors/', {'from_se': self.se.pk, 'to_se': self.se2.pk,
                                                                'author_ids': [self.author.pk]}, format='json')
        self.assertEqual(r.data['moved'], 1)
        self.assertEqual(AuthorEditorLink.objects.get(author=self.author).assigned_se, self.se2)
        self.assertIn('You have a new editor', self.notes(self.author))
        self.c.post('/api/editorial/ce/transfer-authors/', {'from_se': self.se.pk, 'to_se': self.se2.pk}, format='json')
        r = self.c.post(f'/api/editorial/ce/editors/{self.se.pk}/active/', {'active': False}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.se.refresh_from_db()
        self.assertFalse(self.se.is_active)
        # SEs can't use these
        self.c.force_authenticate(self.se2)
        self.assertEqual(self.c.post('/api/editorial/ce/transfer-authors/', {}, format='json').status_code, 403)

    def test_issue_counts_and_cancelling_an_se_contract(self):
        from .models import ContentFlag
        from apps.stories.models import ContentReport
        ContentFlag.objects.create(chapter=self.ch, flagged_by=self.se, flag_type='plagiarism', description='x')
        ContentReport.objects.create(story=self.story, reason='spam')
        Story.objects.filter(pk=self.story2.pk).update(contract_status='awaiting_signature')
        c = self.c.get('/api/editorial/ce/issue-counts/').data
        self.assertEqual((c['flags'], c['reader_reports'], c['reports'], c['awaiting_sign']), (1, 1, 2, 1))
        r = self.c.post('/api/editorial/ce-story-queue/second/reject/', {'action': 'send_back', 'reason': 'Weak'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.c.get('/api/editorial/ce/issue-counts/').data['awaiting_sign'], 0)
        self.assertTrue(any('sent back' in t for t in self.notes(self.se)))   # the SE is told


class CEPromotionCenterTests(TestCase):
    """Promotions in the CE dashboard: timelines on every spot + book insights."""

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        self.td, self.now = timedelta, timezone.now
        self.ce = User.objects.create_user(email='ce@x.com', username='chief', password='x', role='ce')
        self.se = User.objects.create_user(email='se@x.com', username='kay', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x')
        self.story = Story.objects.create(author=self.author, title='Spare Luna', slug='spare-luna', status='ongoing',
                                          total_views=500, total_likes=40, total_comments=10)
        for n in (1, 2, 3):
            Chapter.objects.create(story=self.story, title=f'C{n}', chapter_number=n, is_published=True)
        self.c = APIClient()
        self.c.force_authenticate(self.ce)

    def test_approving_a_request_pins_for_the_chosen_days_then_frees_the_spot(self):
        from .models import ExploreTabPin, SEPromotionRequest
        req = SEPromotionRequest.objects.create(se=self.se, story=self.story, tab='werewolf',
                                                section='fresh-reads', message='Hot book')
        r = self.c.post(f'/api/editorial/ce/promotion-requests/{req.pk}/review/', {'action': 'approved', 'days': 3}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        pin = ExploreTabPin.objects.get()
        self.assertAlmostEqual((pin.expires_at - self.now()).total_seconds(), 3 * 86400, delta=60)
        from apps.stories.views import ExploreTabView
        self.assertEqual(ExploreTabView()._pinned_ids('werewolf', 'fresh-reads'), [self.story.pk])
        ExploreTabPin.objects.update(expires_at=self.now() - self.td(minutes=1))
        self.assertEqual(ExploreTabView()._pinned_ids('werewolf', 'fresh-reads'), [])      # spot freed
        rows = self.c.get('/api/editorial/ce/promo-center/placements/?type=pins&state=ended').data['results']
        self.assertEqual(rows[0]['state'], 'ended')

    def test_ce_places_books_extends_and_ends(self):
        r = self.c.post('/api/editorial/ce/promo-center/slots/', {'story_id': self.story.pk, 'category': 'trending', 'days': 7}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        rows = self.c.get('/api/editorial/ce/promo-center/placements/?type=slots').data['results']
        self.assertEqual((rows[0]['spot_label'], rows[0]['state']), ('Trending Now', 'live'))
        pid = rows[0]['id']
        trending = APIClient().get('/api/stories/trending/')
        self.assertIn('spare-luna', str(trending.data))
        self.c.patch(f'/api/editorial/ce/promo-center/slots/{pid}/', {'end_now': True}, format='json')
        self.assertEqual(self.c.get('/api/editorial/ce/promo-center/placements/?type=slots').data['results'], [])
        self.c.patch(f'/api/editorial/ce/promo-center/slots/{pid}/', {'extend_days': 7}, format='json')
        self.assertEqual(self.c.get('/api/editorial/ce/promo-center/placements/?type=slots').data['results'][0]['state'], 'live')

    def test_banners_follow_their_dates(self):
        r = self.c.post('/api/editorial/ce/promo-center/banners/', {'title': 'Werewolf week', 'slug': 'spare-luna',
                         'starts_at': (self.now() + self.td(days=1)).isoformat(), 'days': 5}, format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        titles = lambda: [b['title'] for b in APIClient().get('/api/stories/banners/').data]
        self.assertNotIn('Werewolf week', titles())                                   # not started yet
        from apps.stories.models import PromoBanner
        PromoBanner.objects.update(starts_at=self.now() - self.td(hours=1))
        self.assertIn('Werewolf week', titles())

    def test_book_insights(self):
        from apps.coins.models import ReadingHistory
        ReadingHistory.objects.create(user=self.reader, story=self.story, chapter_number=3)
        ReadingHistory.objects.create(user=self.ce, story=self.story, chapter_number=1)
        d = self.c.get('/api/editorial/ce/promo-center/insights/spare-luna/').data
        self.assertEqual(d['reach']['readers'], 2)
        self.assertEqual(d['reading']['completion_pct'], 50.0)
        self.assertEqual([f['readers'] for f in d['reading']['funnel']], [2, 1])
        self.assertTrue(0 <= d['score'] <= 100)
        self.assertIn(d['verdict'], ('Strong', 'Good', 'Weak'))
        self.c.force_authenticate(self.se)
        self.assertEqual(self.c.get('/api/editorial/ce/promo-center/insights/spare-luna/').status_code, 403)


class CEInsightsTests(TestCase):
    """SE activity, revenue per SE, how readers unlock, contracts by type."""

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        self.td, self.now = timedelta, timezone.now
        self.ce = User.objects.create_user(email='ce@x.com', username='chief', password='x', role='ce')
        self.se = User.objects.create_user(email='se@x.com', username='kay', password='x', role='se')
        self.author = User.objects.create_user(email='a@x.com', username='amaka', password='x', role='author')
        self.reader = User.objects.create_user(email='r@x.com', username='ada', password='x')
        AuthorEditorLink.objects.create(author=self.author, assigned_se=self.se)
        self.story = Story.objects.create(author=self.author, title='Luna', slug='luna', status='ongoing')
        self.ch = [Chapter.objects.create(story=self.story, title=f'C{n}', chapter_number=n, is_published=True,
                                          is_locked=n > 1, coin_cost=20) for n in (1, 2, 3, 4)]
        self.c = APIClient()
        self.c.force_authenticate(self.ce)

    def test_unlock_records_bonus_vs_purchased_coins(self):
        from apps.chapters.models import ChapterUnlock
        User.objects.filter(pk=self.reader.pk).update(coin_balance=100, bonus_balance=0)
        from apps.users.models import BonusGrant
        self.reader.refresh_from_db()
        BonusGrant.objects.create(user=self.reader, amount=10, remaining=10, expires_at=self.now() + self.td(days=5))
        User.objects.filter(pk=self.reader.pk).update(bonus_balance=10)
        r = APIClient()
        r.force_authenticate(User.objects.get(pk=self.reader.pk))
        self.assertEqual(r.post('/api/chapters/luna/chapters/2/unlock/').status_code, 200)
        r.force_authenticate(User.objects.get(pk=self.reader.pk))
        r.post('/api/chapters/luna/chapters/3/unlock/')
        u2, u3 = ChapterUnlock.objects.order_by('chapter__chapter_number')
        self.assertEqual((u2.coins_spent, u2.bonus_spent), (20, 10))      # 10 bonus + 10 purchased
        self.assertEqual((u3.coins_spent, u3.bonus_spent), (20, 0))       # all purchased

        d = self.c.get('/api/editorial/ce/insights/unlocks/').data
        m = {x['key']: x['count'] for x in d['methods']}
        self.assertEqual((m['mixed'], m['paid']), (1, 1))
        self.assertEqual((d['coins']['paid'], d['coins']['bonus']), (30, 10))

        rev = self.c.get('/api/editorial/ce/insights/se-revenue/').data
        row = rev['by_se'][0]
        self.assertEqual((row['se'], row['unlocks'], row['reader_coins']), ('kay', 2, 40))
        self.assertEqual(row['top_authors'][0]['username'], 'amaka')
        self.assertEqual(rev['top_authors'][0]['se'], 'kay')

    def test_se_activity_time_and_actions(self):
        from apps.analytics.models import PageVisit
        base = self.now() - self.td(hours=3)
        for minutes in (0, 5, 12, 20, 90):          # 0→20 = one 20-min session; 90 = a lone 1-min burst
            v = PageVisit.objects.create(user=self.se, path='/api/editorial/x/')
            PageVisit.objects.filter(pk=v.pk).update(created_at=base + self.td(minutes=minutes))
        Chapter.objects.filter(pk=self.ch[1].pk).update(reviewed_by_se=self.se, reviewed_at=self.now())
        d = self.c.get('/api/editorial/ce/insights/se-activity/?days=7').data['results'][0]
        self.assertEqual(d['username'], 'kay')
        self.assertEqual(d['active_minutes'], 21)
        self.assertEqual(d['chapters_reviewed'], 1)
        self.assertEqual(d['authors'], 1)
        self.assertEqual(len(d['daily']), 7)

    def test_contracts_by_type(self):
        from .models import ContractApplication
        ContractApplication.objects.create(story=self.story, author=self.author, assigned_se=self.se,
                                           status='signed', contract_type='non_exclusive')
        s2 = Story.objects.create(author=self.author, title='B', slug='b')
        ContractApplication.objects.create(story=s2, author=self.author, status='contract_sent', contract_type='exclusive')
        d = self.c.get('/api/editorial/ce/insights/contracts/').data
        t = {x['key']: x for x in d['types']}
        self.assertEqual((t['non_exclusive']['signed'], t['exclusive']['contract_sent'], t['buyout']['total']), (1, 1, 0))
        self.assertEqual(d['signed_by_se'][0]['se'], 'kay')
        self.c.force_authenticate(self.se)
        self.assertEqual(self.c.get('/api/editorial/ce/insights/contracts/').status_code, 403)


class CEContactAndHomeTests(TestCase):
    def setUp(self):
        from unittest import mock
        from apps.users.models import AuthorKYC
        self.ce = User.objects.create_user(email='ce@x.com', username='chief', password='x', role='ce')
        self.author = User.objects.create_user(email='amaka@x.com', username='amaka', password='x', role='author',
                                               first_name='Amaka')
        self.kyc_phone = '08031234567'
        try:
            AuthorKYC.objects.create(user=self.author, full_name='Amaka Obi', phone=self.kyc_phone,
                                     contact_address='x', country='Nigeria')
        except Exception:
            self.kyc_phone = ''
        Story.objects.create(author=self.author, title='Moonlit Vows', slug='moonlit', status='ongoing')
        self.c = APIClient()
        self.c.force_authenticate(self.ce)
        p = mock.patch('apps.notifications.services.notify_user')
        p.start()
        self.addCleanup(p.stop)

    def test_directory_search_and_contact(self):
        from apps.notifications.models import Notification
        d = self.c.get('/api/editorial/ce/author-directory/?q=moonlit').data
        self.assertEqual(d['total'], 1)
        row = d['results'][0]
        self.assertEqual((row['email'], row['books']), ('amaka@x.com', 1))
        self.assertEqual(row['phone'], self.kyc_phone)
        url = f'/api/editorial/ce/authors/{self.author.pk}/contact/'
        self.assertEqual(self.c.post(url, {'channel': 'in_app', 'message': ''}, format='json').status_code, 400)
        r = self.c.post(url, {'channel': 'in_app', 'subject': 'Plagiarism', 'message': 'Please call me.'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        n = Notification.objects.get(recipient=self.author)
        self.assertIn('Chief Editor', n.title)
        self.c.post(url, {'channel': 'whatsapp'}, format='json')
        hist = self.c.get(url).data['results']
        self.assertEqual([h['channel'] for h in hist], ['WhatsApp', 'In-app message'])

    def test_home_summary(self):
        d = self.c.get('/api/editorial/ce/home-summary/').data
        self.assertEqual(d['live_books'], 1)
        self.assertIn('revenue_month_usd', d)
        se = User.objects.create_user(email='s@x.com', username='s', password='x', role='se')
        self.c.force_authenticate(se)
        self.assertEqual(self.c.get('/api/editorial/ce/home-summary/').status_code, 403)
