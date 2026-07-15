"""
Global context available in every template:
  {{ SITE_NAME }}, {{ API_BASE }}, {{ CURRENT_YEAR }},
  {{ canonical_base }}, {{ canonical_url }}
"""
from datetime import datetime

from django.conf import settings


def site_globals(request):
    # One canonical host for SEO, regardless of which host (www / apex /
    # onrender) the request actually arrived on.
    canonical_base = settings.CANONICAL_BASE
    return {
        'SITE_NAME':     'Novelux',
        'SITE_TAGLINE':  'Millions of free novels. One quiet place to read them.',
        'API_BASE':      '/api',
        'CURRENT_YEAR':  datetime.now().year,
        'IS_AUTHOR':     getattr(request.user, 'is_author', False)
                         if request.user.is_authenticated else False,
        'canonical_base': canonical_base,
        'canonical_url':  canonical_base + request.path,
    }
