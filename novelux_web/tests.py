from types import SimpleNamespace

from django.test import TestCase, override_settings

from .sitemaps import StaticViewSitemap


class SitemapDomainTests(TestCase):
    @override_settings(SITE_URL='https://www.novelux.app')
    def test_static_sitemap_uses_configured_site_url_domain(self):
        urls = StaticViewSitemap().get_urls(site=SimpleNamespace(domain='example.com'))

        self.assertTrue(urls)
        self.assertTrue(any(url['location'] == 'https://www.novelux.app/' for url in urls))


@override_settings(CANONICAL_BASE='https://www.novelux.app',
                   ALLOWED_HOSTS=['www.novelux.app', 'novelux.app', 'testserver'])
class DeepLinkVerificationTests(TestCase):
    """/.well-known files for Android App Links and iOS Universal Links."""

    def test_assetlinks(self):
        res = self.client.get('/.well-known/assetlinks.json', secure=True, HTTP_HOST='www.novelux.app')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        target = res.json()[0]['target']
        self.assertEqual(target['package_name'], 'com.daniel.huxnovel')
        self.assertIn('0C:8C:7E:87:18:54:FC:D4:A5:69:87:63:54:F5:78:51:3F:50:34:E9:E7:BB:C4:5A:7A:A6:F3:E3:13:D9:C9:9F',
                      target['sha256_cert_fingerprints'])

    def test_apple_app_site_association(self):
        res = self.client.get('/.well-known/apple-app-site-association', secure=True, HTTP_HOST='www.novelux.app')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/json')
        detail = res.json()['applinks']['details'][0]
        self.assertEqual(detail['appIDs'], ['Q7MJNN6B4W.com.daniel.novelux.novelux'])
        self.assertIn({'/': '/explore/?*'}, detail['components'])

    def test_not_redirected_on_other_domains(self):
        # novelux.app normally 301s to www — but phones refuse redirected files
        res = self.client.get('/.well-known/assetlinks.json', secure=True, HTTP_HOST='novelux.app')
        self.assertEqual(res.status_code, 200)
        page = self.client.get('/explore/', secure=True, HTTP_HOST='novelux.app')
        self.assertEqual(page.status_code, 301)


class ReaderWelcomeTests(TestCase):
    """Readers who log in on the website land on /welcome/, not the author dashboard."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken
        U = get_user_model()
        self.tokens = {
            role: str(RefreshToken.for_user(
                U.objects.create_user(email=f'{role}@x.com', username=role, password='x', role=role,
                                      first_name=role.title())).access_token)
            for role in ('reader', 'author', 'se')
        }

    def _get(self, path, role=None):
        if role:
            self.client.cookies['nux_access'] = self.tokens[role]
        return self.client.get(path, secure=True)

    def test_reader_dashboard_goes_to_welcome(self):
        res = self._get('/dashboard/', 'reader')
        self.assertEqual((res.status_code, res['Location']), (302, '/welcome/'))

    def test_author_keeps_dashboard(self):
        self.assertEqual(self._get('/dashboard/', 'author').status_code, 200)

    def test_editor_goes_to_editorial_dashboard(self):
        self.assertEqual(self._get('/dashboard/', 'se')['Location'], '/editorial/se/')

    def test_welcome_shows_all_options(self):
        res = self._get('/welcome/', 'reader')
        self.assertEqual(res.status_code, 200)
        for text in ('Welcome, Reader', 'href="/explore/"', 'href="/become-author/"', 'href="/"',
                     'app-store-badge.svg', 'google-play-badge.png', '/download/apk/', 'Sign out'):
            self.assertContains(res, text)

    def test_welcome_requires_login(self):
        res = self._get('/welcome/')
        self.assertEqual(res['Location'], '/login/?next=/welcome/')


class DashboardRoutingTests(TestCase):
    """Everyone lands on their own dashboard — authors never on an editor's."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        self.author = U.objects.create_user(email='a@x.com', username='auth', password='pass12345', role='author')
        self.se = U.objects.create_user(email='s@x.com', username='sened', password='pass12345', role='se')
        self.ce = U.objects.create_user(email='c@x.com', username='ceed', password='pass12345', role='ce')
        self.reader = U.objects.create_user(email='r@x.com', username='rdr', password='pass12345')

    def login(self, email, nxt='/dashboard/'):
        import json
        res = self.client.post('/auth/login-web/', json.dumps({'email': email, 'password': 'pass12345', 'next': nxt}),
                               content_type='application/json', secure=True)
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()['next']

    def as_user(self, user):
        from rest_framework_simplejwt.tokens import AccessToken
        self.client.cookies['nux_access'] = str(AccessToken.for_user(user))

    def test_login_lands_on_own_dashboard(self):
        self.assertEqual(self.login('a@x.com'), '/dashboard/')
        self.assertEqual(self.login('s@x.com'), '/editorial/se/')
        self.assertEqual(self.login('c@x.com'), '/editorial/ce/')
        self.assertEqual(self.login('r@x.com'), '/welcome/')

    def test_next_never_sends_someone_to_a_page_they_cant_open(self):
        self.assertEqual(self.login('a@x.com', '/editorial/se/'), '/dashboard/')
        self.assertEqual(self.login('a@x.com', '/editorial/ce/'), '/dashboard/')
        self.assertEqual(self.login('a@x.com', '/master/'), '/dashboard/')
        self.assertEqual(self.login('s@x.com', '/dashboard/'), '/editorial/se/')
        self.assertEqual(self.login('a@x.com', 'https://evil.example/'), '/dashboard/')
        self.assertEqual(self.login('a@x.com', '//evil.example/'), '/dashboard/')
        # A normal page is still honoured
        self.assertEqual(self.login('a@x.com', '/explore/some-book/'), '/explore/some-book/')

    def test_wrong_dashboard_redirects_to_your_own(self):
        self.as_user(self.author)
        for url in ('/editorial/se/', '/editorial/ce/', '/editorial/', '/login/'):
            res = self.client.get(url, secure=True)
            self.assertRedirects(res, '/dashboard/', fetch_redirect_response=False, msg_prefix=url)
        self.as_user(self.se)
        self.assertRedirects(self.client.get('/dashboard/', secure=True), '/editorial/se/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/editorial/', secure=True), '/editorial/se/', fetch_redirect_response=False)

    def test_editorial_uses_the_current_role_not_the_token(self):
        from rest_framework_simplejwt.tokens import AccessToken
        tok = AccessToken.for_user(self.author)
        tok['role'] = 'se'                      # stale/forged role claim
        self.client.cookies['nux_access'] = str(tok)
        self.assertRedirects(self.client.get('/editorial/', secure=True), '/dashboard/', fetch_redirect_response=False)

    def test_dashboards_are_never_cached(self):
        self.as_user(self.se)
        res = self.client.get('/editorial/se/', secure=True)
        self.assertIn('no-store', res['Cache-Control'])

    def test_signup_cannot_create_editors_or_admins(self):
        import json
        from django.contrib.auth import get_user_model
        for i, role in enumerate(['se', 'ce', 'admin']):
            res = self.client.post('/auth/register-web/', json.dumps({
                'username': f'sneaky{i}', 'email': f'sneaky{i}@x.com', 'password1': 'pass12345', 'role': role,
            }), content_type='application/json', secure=True)
            self.assertEqual(res.status_code, 200, res.content)
            self.assertEqual(get_user_model().objects.get(username=f'sneaky{i}').role, 'reader')
        # Authors can still sign up as authors
        self.client.post('/auth/register-web/', json.dumps({
            'username': 'newauthor', 'email': 'na@x.com', 'password1': 'pass12345', 'role': 'author',
        }), content_type='application/json', secure=True)
        self.assertEqual(get_user_model().objects.get(username='newauthor').role, 'author')

    def test_app_signup_rejects_editor_roles(self):
        from apps.users.serializers import RegisterSerializer
        s = RegisterSerializer(data={'username': 'x1', 'email': 'x1@x.com', 'password1': 'Str0ng!pass9',
                                     'password2': 'Str0ng!pass9', 'role': 'ce', 'date_of_birth': '1995-01-01'})
        self.assertFalse(s.is_valid())
        self.assertIn('role', s.errors)


class DashboardRoutingTests(TestCase):
    """Everyone lands on their own dashboard — an author never ends up on an
    editor dashboard (or vice versa), whatever ?next= or old cookies say."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        self.author = U.objects.create_user(email='a@x.com', username='author', password='pass12345', role='author')
        self.se = U.objects.create_user(email='se@x.com', username='se', password='pass12345', role='se')
        self.reader = U.objects.create_user(email='r@x.com', username='reader', password='pass12345')

    def login_as(self, user):
        from rest_framework_simplejwt.tokens import AccessToken
        self.client.cookies['nux_access'] = str(AccessToken.for_user(user))

    def web_login(self, email, next_url=''):
        import json
        return self.client.post('/auth/login-web/', json.dumps({'email': email, 'password': 'pass12345', 'next': next_url}),
                                content_type='application/json', secure=True).json()

    def test_login_goes_to_own_dashboard_whatever_next_says(self):
        self.assertEqual(self.web_login('a@x.com', '/editorial/se/')['next'], '/dashboard/')
        self.assertEqual(self.web_login('a@x.com', '/editorial/ce/')['next'], '/dashboard/')
        self.assertEqual(self.web_login('a@x.com', '/master/')['next'], '/dashboard/')
        self.assertEqual(self.web_login('a@x.com', 'https://evil.example/x')['next'], '/dashboard/')
        self.assertEqual(self.web_login('se@x.com', '/dashboard/')['next'], '/editorial/se/')
        self.assertEqual(self.web_login('r@x.com')['next'], '/welcome/')
        # A safe page the account may open is still honoured
        self.assertEqual(self.web_login('a@x.com', '/explore/some-book/')['next'], '/explore/some-book/')

    def test_wrong_dashboard_sends_you_to_your_own(self):
        self.login_as(self.author)
        r = self.client.get('/editorial/se/', secure=True)
        self.assertEqual((r.status_code, r['Location']), (302, '/dashboard/'))
        self.assertEqual(self.client.get('/editorial/', secure=True)['Location'], '/dashboard/')
        self.assertEqual(self.client.get('/login/?next=/editorial/ce/', secure=True)['Location'], '/dashboard/')
        self.login_as(self.se)
        self.assertEqual(self.client.get('/dashboard/', secure=True)['Location'], '/editorial/se/')

    def test_role_changes_win_over_old_tokens(self):
        # Token minted while they were an SE; they're an author now
        self.login_as(self.se)
        self.se.role = 'author'
        self.se.save(update_fields=['role'])
        self.assertEqual(self.client.get('/editorial/', secure=True)['Location'], '/dashboard/')

    def test_dashboards_are_never_cached(self):
        self.login_as(self.author)
        r = self.client.get('/dashboard/', secure=True)
        self.assertIn('no-store', r['Cache-Control'])

    def test_signup_cannot_make_editors_or_admins(self):
        import json
        from django.contrib.auth import get_user_model
        for i, role in enumerate(['se', 'ce', 'admin']):
            self.client.post('/auth/register-web/', json.dumps({
                'username': f'sneaky{i}', 'email': f's{i}@x.com', 'password1': 'pass12345', 'role': role,
            }), content_type='application/json', secure=True)
            self.assertEqual(get_user_model().objects.get(username=f'sneaky{i}').role, 'reader')
        # App sign-up too
        from rest_framework.test import APIClient
        res = APIClient().post('/api/auth/dj/registration/', {
            'username': 'sneaky_app', 'email': 'sa@x.com', 'password1': 'Pass-word-123!', 'password2': 'Pass-word-123!',
            'role': 'ce', 'date_of_birth': '2000-01-01'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='sneaky_app', role='ce').exists())
