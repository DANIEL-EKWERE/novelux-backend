from types import SimpleNamespace

from django.test import TestCase, override_settings

from .sitemaps import StaticViewSitemap


class SitemapDomainTests(TestCase):
    @override_settings(SITE_URL='https://www.novelux.app')
    def test_static_sitemap_uses_configured_site_url_domain(self):
        urls = StaticViewSitemap().get_urls(site=SimpleNamespace(domain='example.com'))

        self.assertTrue(urls)
        self.assertTrue(any(url['location'] == 'https://www.novelux.app/' for url in urls))
