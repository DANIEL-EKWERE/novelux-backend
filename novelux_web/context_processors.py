"""
Global context available in every template:
  {{ SITE_NAME }}, {{ API_BASE }}, {{ CURRENT_YEAR }}
"""
from datetime import datetime

def site_globals(request):
    return {
        'SITE_NAME':     'Novelux',
        'SITE_TAGLINE':  'Millions of free novels. One quiet place to read them.',
        'API_BASE':      '/api',
        'CURRENT_YEAR':  datetime.now().year,
        'IS_AUTHOR':     getattr(request.user, 'is_author', False)
                         if request.user.is_authenticated else False,
    }
