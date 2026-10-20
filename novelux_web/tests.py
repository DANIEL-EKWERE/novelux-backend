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
