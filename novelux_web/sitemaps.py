from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.blog.models import BlogPost
from apps.stories.models import Story


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'
    protocol   = 'https'

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


class StorySitemap(Sitemap):
    changefreq = 'weekly'
    priority   = 0.8
    protocol   = 'https'

    def items(self):
        return Story.objects.filter(
            status__in=['published', 'ongoing', 'completed'],
        ).order_by('-total_views')

    def location(self, obj):
        return reverse('novelux:story_preview', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(Sitemap):
    changefreq = 'weekly'
    priority   = 0.7
    protocol   = 'https'

    def items(self):
        return BlogPost.objects.filter(
            status=BlogPost.STATUS_PUBLISHED,
            audience=BlogPost.AUDIENCE_PUBLIC,
        ).order_by('-updated_at')

    def location(self, obj):
        return reverse('novelux:article_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at
