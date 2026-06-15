from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json, os


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _jwt_from_request(request):
    """Read JWT from the nux_access cookie (set after login)."""
    return request.COOKIES.get('nux_access', '')


def _is_authenticated(request):
    """Check if the request has a valid JWT cookie."""
    return bool(_jwt_from_request(request))


def _set_auth_cookies(response, access_token, refresh_token, username='', email=''):
    """Set JWT cookies on the response — secure, httponly, samesite."""
    is_prod = os.environ.get('RENDER') == 'true'
    opts = dict(httponly=True, samesite='Lax', secure=is_prod)
    response.set_cookie('nux_access',   access_token,   max_age=3600,         **opts)
    response.set_cookie('nux_refresh',  refresh_token,  max_age=60*60*24*30,  **opts)
    response.set_cookie('nux_username', username,       max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod)
    response.set_cookie('nux_email',    email,          max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod)
    return response


def _clear_auth_cookies(response):
    for name in ('nux_access', 'nux_refresh', 'nux_username', 'nux_email'):
        response.delete_cookie(name)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC PAGES
# ══════════════════════════════════════════════════════════════════════════════

def index(request):
    context = {
        'is_auth': _is_authenticated(request),
        'username': request.COOKIES.get('nux_username', ''),
    }
    return render(request, 'novelux/index.html', context)

def become_author(request):
    return render(request, 'novelux/become_author.html')

def faq(request):
    return render(request, 'novelux/faq.html')

def privacy(request):
    return render(request, 'novelux/privacy.html')

def terms(request):
    return render(request, 'novelux/terms.html')

def cookies_page(request):
    return render(request, 'novelux/cookies.html')

def content_guidelines(request):
    return render(request, 'novelux/content_guidelines.html')


# ══════════════════════════════════════════════════════════════════════════════
# AUTH PAGES  (login / register / logout)
# ══════════════════════════════════════════════════════════════════════════════

def login_page(request):
    """
    GET  → show login form
    The actual auth is done by the AJAX endpoint /auth/login-web/ below.
    """
    if _is_authenticated(request):
        return redirect('novelux:dashboard')

    next_url = request.GET.get('next', '/dashboard/')
    return render(request, 'novelux/login.html', {
        'next': next_url,
        'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
    })


def register_page(request):
    """Sign-up page (readers only — authors go through onboarding)."""
    if _is_authenticated(request):
        return redirect('novelux:index')
    return render(request, 'novelux/register.html', {
        'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
    })


def logout_view(request):
    response = redirect('novelux:index')
    _clear_auth_cookies(response)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# AJAX AUTH ENDPOINTS  (called by JS fetch — return JSON)
# ══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def ajax_login(request):
    """
    POST /auth/login-web/
    Body: { email, password }
    Hits the DRF JWT endpoint, sets httpOnly cookies, returns { ok, next }.
    """
    import requests as http_requests

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    email    = body.get('email', '').strip()
    password = body.get('password', '').strip()
    next_url = body.get('next', '/dashboard/')

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required'}, status=400)

    # Hit the internal DRF login endpoint
    base_url = _get_api_base(request)
    try:
        # r = http_requests.post(
        #     f'{base_url}/api/auth/login/',
        #     json={'email': email, 'password': password},
        #     timeout=10
        # )
        r = http_requests.post(
        f'{base_url}/api/auth/token/',
        json={'email': email, 'password': password},
        timeout=10
        )
        data = r.json()
    except Exception as e:
        return JsonResponse({'error': f'Could not reach auth server: {e}'}, status=503)

    if r.status_code != 200 or 'access' not in data:
        err = data.get('detail') or data.get('error') or 'Invalid email or password'
        return JsonResponse({'error': err}, status=401)

    response = JsonResponse({'ok': True, 'next': next_url,
                             'username': data.get('username', '')})
    _set_auth_cookies(
        response,
        access_token=data['access'],
        refresh_token=data.get('refresh', ''),
        username=data.get('username', ''),
        email=email,
    )
    return response


@csrf_exempt
@require_POST
def ajax_register(request):
    """
    POST /auth/register-web/
    Body: { username, email, password, role? }
    """
    import requests as http_requests

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    base_url = _get_api_base(request)
    try:
        r = http_requests.post(
            f'{base_url}/api/auth/register/',
            json={
                'username': body.get('username', '').strip(),
                'email':    body.get('email', '').strip(),
                'password': body.get('password', '').strip(),
                'role':     body.get('role', 'reader'),
            },
            timeout=10
        )
        data = r.json()
    except Exception as e:
        return JsonResponse({'error': f'Server error: {e}'}, status=503)

    if r.status_code not in (200, 201):
        # Extract first readable error message from DRF response
        err = _extract_drf_error(data)
        return JsonResponse({'error': err}, status=400)

    # Auto-login after register if tokens returned
    response = JsonResponse({'ok': True, 'username': data.get('username', '')})
    if 'access' in data:
        _set_auth_cookies(
            response,
            access_token=data['access'],
            refresh_token=data.get('refresh', ''),
            username=data.get('username', ''),
            email=body.get('email', ''),
        )
    return response


@csrf_exempt
@require_POST
def ajax_google_auth(request):
    """
    POST /auth/google-web/
    Body: { id_token, email, name, photo_url }
    Verifies with Django backend, sets cookies.
    """
    import requests as http_requests

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    base_url = _get_api_base(request)
    try:
        r = http_requests.post(
            f'{base_url}/api/auth/google/',
            json={
                'id_token':     body.get('id_token', ''),
                'email':        body.get('email', ''),
                'display_name': body.get('name', ''),
                'photo_url':    body.get('photo_url', ''),
            },
            timeout=10
        )
        data = r.json()
    except Exception as e:
        return JsonResponse({'error': f'Server error: {e}'}, status=503)

    if r.status_code != 200 or 'access' not in data:
        err = data.get('detail') or data.get('error') or 'Google sign-in failed'
        return JsonResponse({'error': err}, status=401)

    response = JsonResponse({'ok': True, 'username': data.get('username', ''),
                             'is_new': data.get('is_new', False)})
    _set_auth_cookies(
        response,
        access_token=data['access'],
        refresh_token=data.get('refresh', ''),
        username=data.get('username', ''),
        email=data.get('email', body.get('email', '')),
    )
    return response


@csrf_exempt
@require_POST
def ajax_refresh_token(request):
    """
    POST /auth/refresh-web/
    Silently refresh the access token using the refresh cookie.
    """
    import requests as http_requests

    refresh_token = request.COOKIES.get('nux_refresh', '')
    if not refresh_token:
        return JsonResponse({'error': 'No refresh token'}, status=401)

    base_url = _get_api_base(request)
    try:
        r = http_requests.post(
            f'{base_url}/api/auth/token/refresh/',
            json={'refresh': refresh_token},
            timeout=10
        )
        data = r.json()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=503)

    if r.status_code != 200 or 'access' not in data:
        response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
        _clear_auth_cookies(response)
        return response

    response = JsonResponse({'ok': True})
    is_prod = os.environ.get('RENDER') == 'true'
    response.set_cookie('nux_access', data['access'], max_age=3600,
                        httponly=True, samesite='Lax', secure=is_prod)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# AUTHOR DASHBOARD  (JWT-cookie-gated, NOT Django session)
# ══════════════════════════════════════════════════════════════════════════════

def author_dashboard(request):
    """
    Serve the dashboard if the user has a valid nux_access cookie.
    The cookie is httpOnly so JS can't read it — we inject the token
    into a <meta> tag so the page JS can pick it up for API calls.
    """
    if not _is_authenticated(request):
        return redirect(f'/login/?next=/dashboard/')

    return render(request, 'novelux/author_dashboard.html', {
        'access_token': _jwt_from_request(request),
        'username':     request.COOKIES.get('nux_username', 'Author'),
        'email':        request.COOKIES.get('nux_email', ''),
        'api_base':     '/api',
    })


def author_onboarding(request):
    """
    Multi-step author onboarding.
    If already logged in we pre-fill user info.
    """
    return render(request, 'novelux/author_onboarding.html', {
        'is_auth':      _is_authenticated(request),
        'username':     request.COOKIES.get('nux_username', ''),
        'email':        request.COOKIES.get('nux_email', ''),
        'access_token': _jwt_from_request(request),
        'api_base':     '/api',
        'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
    })


# ══════════════════════════════════════════════════════════════════════════════
# APK DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def download_apk(request):
    apk_path = os.environ.get('NOVELUX_APK_PATH', '')
    if apk_path and os.path.exists(apk_path):
        with open(apk_path, 'rb') as f:
            response = HttpResponse(f.read(),
                content_type='application/vnd.android.package-archive')
            response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
            return response
    return JsonResponse({'detail': 'APK not yet available'}, status=404)


# ══════════════════════════════════════════════════════════════════════════════
# MISC AJAX
# ══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def book_request_web(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = {}
    title  = data.get('title', '').strip()
    author = data.get('author', '').strip()
    if not title:
        return JsonResponse({'error': 'title required'}, status=400)
    try:
        from apps.stories.models import BookRequest
        BookRequest.objects.create(title=title, author=author)
    except Exception:
        pass
    return JsonResponse({'detail': 'Request received!'})


@csrf_exempt
@require_POST
def newsletter_signup(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
    except Exception:
        email = ''
    if not email or '@' not in email:
        return JsonResponse({'error': 'valid email required'}, status=400)
    return JsonResponse({'detail': 'Subscribed!'})


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_api_base(request):
    """
    When calling Django's own DRF endpoints from a view we use localhost,
    not the public Render URL, to avoid the round-trip.
    On Render PORT is 10000 by default.
    """
    port = os.environ.get('PORT', '8000')
    return f'http://127.0.0.1:{port}'


def _extract_drf_error(data):
    """Pull the first readable error message from a DRF error dict."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ('detail', 'error', 'non_field_errors',
                    'email', 'username', 'password'):
            val = data.get(key)
            if val:
                if isinstance(val, list):
                    return str(val[0])
                return str(val)
        # Fallback — first value
        first = next(iter(data.values()), None)
        if first:
            return str(first[0] if isinstance(first, list) else first)
    return 'Something went wrong. Please try again.'
