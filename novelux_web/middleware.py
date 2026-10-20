"""
Canonical-host redirect: consolidates crawling onto a single host so search
engines never see the same page on www / apex / onrender as separate URLs.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostRedirectMiddleware:
    """301 alternate hosts to the canonical one (settings.SITE_URL).

    Only GET/HEAD requests are redirected — API calls and form POSTs from
    apps pinned to another host are never disturbed.
    """

    # Hosts that duplicate the canonical site and should be folded into it.
    REDIRECT_HOSTS = {'www.novelux.app', 'novelux.app'}

    def __init__(self, get_response):
        self.get_response = get_response
        parsed = urlparse(settings.CANONICAL_BASE)
        self.canonical_host = (parsed.netloc or '').split(':')[0].lower()
        self.canonical_base = settings.CANONICAL_BASE

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        if (
            self.canonical_host
            and request.method in ('GET', 'HEAD')
            and host in self.REDIRECT_HOSTS
            and host != self.canonical_host      # never loop
        ):
            return HttpResponsePermanentRedirect(
                self.canonical_base + request.get_full_path()
            )
        return self.get_response(request)


class FreshAccessCookieMiddleware:
    """Saves an access token minted mid-request (see views._user_from_request)
    as the nux_access cookie, so the browser has a valid one again and the
    page's API calls stop failing with 401."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        fresh = getattr(request, '_nux_fresh_access', None)
        if fresh and 'nux_access' not in response.cookies:
            import os
            response.set_cookie('nux_access', fresh, max_age=3600, httponly=True,
                                samesite='Lax', secure=os.environ.get('RENDER') == 'true')
        return response
