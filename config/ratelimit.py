"""Rate limiting.

Two layers:
  * DRF throttles (REST_FRAMEWORK settings) for the whole API — generous,
    per signed-in account or per IP for guests.
  * AuthRateLimitMiddleware — tight per-IP limits on login, sign-up and
    password-reset routes (app API and website), against password guessing
    and sign-up spam.

Limits are generous on purpose: many mobile users in Nigeria/Ghana share one
carrier IP (CGNAT), so a tight per-IP limit would block real people.

Counters live in Django's cache (LocMemCache today, so per server process;
switch CACHES to Redis to share them across processes/instances).
"""
import time

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def client_ip(request):
    """The visitor's IP behind Render's proxy (not the proxy's own address)."""
    try:
        from ipware import get_client_ip
        ip, _ = get_client_ip(request)
        if ip:
            return ip
    except Exception:
        pass
    fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (fwd.split(',')[0].strip() if fwd else '') or request.META.get('REMOTE_ADDR', '') or 'unknown'


class _RealIP:
    def get_ident(self, request):
        return client_ip(request)


class AnonBurstThrottle(_RealIP, AnonRateThrottle):
    scope = 'anon'


class UserBurstThrottle(_RealIP, UserRateThrottle):
    scope = 'user'


# (path, method, requests, window seconds, label)
AUTH_LIMITS = [
    # Logging in (app + website + social)
    ('/api/auth/token/',            'POST', 20, 60,   'login'),
    ('/api/auth/social/',           'POST', 20, 60,   'login'),
    ('/api/auth/google/',           'POST', 20, 60,   'login'),
    ('/api/auth/apple/',            'POST', 20, 60,   'login'),
    ('/api/auth/dj/login/',         'POST', 20, 60,   'login'),
    ('/auth/login-web/',            'POST', 20, 60,   'login'),
    ('/auth/google-web/',           'POST', 20, 60,   'login'),
    # Creating accounts
    ('/api/auth/dj/registration/',  'POST', 30, 3600, 'signup'),
    ('/auth/register-web/',         'POST', 30, 3600, 'signup'),
    # Password reset e-mails
    ('/api/auth/dj/password/reset/', 'POST', 10, 3600, 'reset'),
    ('/auth/forgot-password/',      'POST', 10, 3600, 'reset'),
    ('/auth/reset-password/',       'POST', 20, 3600, 'reset'),
]

_MESSAGES = {
    'login':  'Too many sign-in attempts. Please wait a minute and try again.',
    'signup': 'Too many new accounts from this network. Please try again later.',
    'reset':  'Too many password reset requests. Please try again later.',
}


def hit(key, limit, window):
    """Count one request in a fixed window. Returns seconds to wait when the
    limit is exceeded, else 0."""
    now = int(time.time())
    bucket = now // window
    k = f'rl:{key}:{bucket}'
    if cache.add(k, 1, timeout=window + 5):
        count = 1
    else:
        try:
            count = cache.incr(k)
        except ValueError:  # expired between add and incr
            cache.set(k, 1, timeout=window + 5)
            count = 1
    if count > limit:
        return (bucket + 1) * window - now
    return 0


class AuthRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        for prefix, method, limit, window, label in AUTH_LIMITS:
            # Exact paths (so /api/auth/token/refresh/ isn't counted as a
            # login); sign-up also covers its sub-paths.
            matched = path == prefix or (label == 'signup' and path.startswith(prefix))
            if request.method == method and matched:
                wait = hit(f'{label}:{client_ip(request)}', limit, window)
                if wait:
                    resp = JsonResponse({'detail': _MESSAGES[label], 'retry_after': wait}, status=429)
                    resp['Retry-After'] = str(wait)
                    return resp
                break
        return self.get_response(request)
