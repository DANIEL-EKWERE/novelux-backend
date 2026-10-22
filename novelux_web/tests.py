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
