from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.urls import reverse
from apps.blog.models import BlogPost
from apps.stories.models import Story


class BaseSitemap(Sitemap):
    protocol = 'https'

    def get_domain(self, site=None):
        configured_domain = getattr(settings, 'SITE_DOMAIN', '').strip()
        configured_site_url = getattr(settings, 'SITE_URL', '').strip()

        candidates = []
        if configured_domain:
            candidates.append(configured_domain)
        if configured_site_url:
            candidates.append(configured_site_url)

        for candidate in candidates:
            parsed = urlparse(candidate if '://' in candidate else f'https://{candidate}')
            host = parsed.netloc or parsed.path.rstrip('/')
            if not host:
                continue

            if host in {'example.com', 'localhost', '127.0.0.1', '0.0.0.0'}:
                continue

            if host.endswith('.onrender.com') or host.endswith('.render.com'):
                continue

            return host

        if site is None:
            site = Site.objects.get_current()

        host = getattr(site, 'domain', '').strip()
        if host and host not in {'example.com', 'localhost', '127.0.0.1', '0.0.0.0'} and not host.endswith('.onrender.com'):
            return host

        return 'www.novelux.app'

    def get_urls(self, page=1, site=None, protocol=None):
        protocol = self.get_protocol(protocol)
        domain = self.get_domain(site)
        return self._urls(page, protocol, domain)


class StaticViewSitemap(BaseSitemap):
    changefreq = 'weekly'


    pages = [
        ('novelux:index',              1.0, 'daily'),
        ('novelux:explore',            0.9, 'daily'),
        ('novelux:articles',           0.8, 'daily'),
        ('novelux:become_author',      0.7, 'weekly'),
        ('novelux:faq',                0.5, 'monthly'),
        ('novelux:download_apk',       0.6, 'weekly'),
        ('novelux:privacy',            0.3, 'yearly'),
        ('novelux:terms',              0.3, 'yearly'),
        ('novelux:cookies',            0.3, 'yearly'),
        ('novelux:content_guidelines', 0.4, 'monthly'),
        ('novelux:copyright_policy',   0.3, 'yearly'),
    ]

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class StorySitemap(BaseSitemap):
    changefreq = 'weekly'
    priority   = 0.8

    def items(self):
        from apps.stories.views import exclude_explicit
        return exclude_explicit(Story.objects.filter(
            status__in=['published', 'ongoing', 'completed'],
        )).order_by('-total_views')

    def location(self, obj):
        return reverse('novelux:story_preview', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(BaseSitemap):
    changefreq = 'weekly'
    priority   = 0.7

    def items(self):
        return BlogPost.objects.filter(
            status=BlogPost.STATUS_PUBLISHED,
            audience=BlogPost.AUDIENCE_PUBLIC,
        ).order_by('-updated_at')

    def location(self, obj):
        return reverse('novelux:article_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at
