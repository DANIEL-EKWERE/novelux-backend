# # # from django.shortcuts import render
# # # from django.http import HttpResponse, JsonResponse
# # # from django.views.decorators.http import require_POST
# # # from django.contrib.auth.decorators import login_required
# # # import json


# # # # ── Public pages ──────────────────────────────────────────────────────────────

# # # def index(request):
# # #     """Landing page — serve stories from API for SEO."""
# # #     context = {}
# # #     try:
# # #         from apps.stories.models import Story
# # #         context['featured_stories'] = list(
# # #             Story.objects.filter(status='published')
# # #             .order_by('-total_views')[:8]
# # #             .values('slug', 'title', 'cover_image', 'average_rating', 'total_views')
# # #         )
# # #     except Exception:
# # #         context['featured_stories'] = []
# # #     return render(request, 'novelux/index.html', context)


# # # def become_author(request):
# # #     return render(request, 'novelux/become_author.html')


# # # def author_onboarding(request):
# # #     return render(request, 'novelux/author_onboarding.html')


# # # def faq(request):
# # #     return render(request, 'novelux/faq.html')


# # # def privacy(request):
# # #     return render(request, 'novelux/privacy.html')


# # # def terms(request):
# # #     return render(request, 'novelux/terms.html')


# # # def cookies(request):
# # #     return render(request, 'novelux/cookies.html')


# # # def content_guidelines(request):
# # #     return render(request, 'novelux/content_guidelines.html')


# # # # ── Author dashboard (requires login) ─────────────────────────────────────────

# # # @login_required(login_url='/api/auth/login/')
# # # def author_dashboard(request):
# # #     """
# # #     Author dashboard — passes author stats to template via context.
# # #     The dashboard HTML uses JS to call the DRF API for live data;
# # #     this view injects the auth token so the JS can use it.
# # #     """
# # #     context = {
# # #         'user': request.user,
# # #         # Pass JWT access token so dashboard JS can hit the DRF API
# # #         'api_base': '/api',
# # #     }
# # #     return render(request, 'novelux/author_dashboard.html', context)


# # # # ── APK download ───────────────────────────────────────────────────────────────

# # # def download_apk(request):
# # #     """
# # #     Redirect to the latest APK in storage, or serve a 404-style
# # #     page while the app is not yet published.
# # #     """
# # #     import os
# # #     from django.conf import settings

# # #     apk_path = getattr(settings, 'NOVELUX_APK_PATH', None)
# # #     if apk_path and os.path.exists(apk_path):
# # #         with open(apk_path, 'rb') as f:
# # #             response = HttpResponse(f.read(),
# # #                 content_type='application/vnd.android.package-archive')
# # #             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
# # #             return response

# # #     # APK not yet uploaded — redirect back to landing with a flash
# # #     from django.contrib import messages
# # #     from django.shortcuts import redirect
# # #     messages.info(request, 'APK coming soon — follow us for updates.')
# # #     return redirect('novelux:index')


# # # # ── Book request (from search "not found") ────────────────────────────────────

# # # @require_POST
# # # def book_request_web(request):
# # #     """Web form submission for 'Find the book' — mirrors the API endpoint."""
# # #     try:
# # #         data   = json.loads(request.body)
# # #         title  = data.get('title', '').strip()
# # #         author = data.get('author', '').strip()
# # #     except (json.JSONDecodeError, AttributeError):
# # #         title  = request.POST.get('title', '').strip()
# # #         author = request.POST.get('author', '').strip()

# # #     if not title:
# # #         return JsonResponse({'detail': 'title required'}, status=400)

# # #     try:
# # #         from apps.stories.models import BookRequest
# # #         BookRequest.objects.create(
# # #             title=title, author=author,
# # #             requested_by=request.user if request.user.is_authenticated else None,
# # #         )
# # #     except Exception:
# # #         pass  # graceful — don't crash the page

# # #     return JsonResponse({'detail': 'Request received. Thank you!'})


# # # # ── Newsletter / contact ───────────────────────────────────────────────────────

# # # @require_POST
# # # def newsletter_signup(request):
# # #     try:
# # #         data  = json.loads(request.body)
# # #         email = data.get('email', '').strip()
# # #     except Exception:
# # #         email = request.POST.get('email', '').strip()

# # #     if not email or '@' not in email:
# # #         return JsonResponse({'detail': 'valid email required'}, status=400)

# # #     # TODO: integrate with Mailchimp / SendGrid / etc.
# # #     return JsonResponse({'detail': 'Subscribed!'})


# # from django.shortcuts import render, redirect
# # from django.http import HttpResponse, JsonResponse
# # from django.views.decorators.http import require_POST, require_http_methods
# # from django.views.decorators.csrf import csrf_exempt
# # import json, os


# # # ══════════════════════════════════════════════════════════════════════════════
# # # HELPERS
# # # ══════════════════════════════════════════════════════════════════════════════

# # def _jwt_from_request(request):
# #     """Read JWT from the nux_access cookie (set after login)."""
# #     return request.COOKIES.get('nux_access', '')


# # def _is_authenticated(request):
# #     """Check if the request has a valid JWT cookie."""
# #     return bool(_jwt_from_request(request))


# # def _set_auth_cookies(response, access_token, refresh_token, username='', email='', role=''):
# #     """Set JWT cookies on the response — secure, httponly, samesite."""
# #     is_prod = os.environ.get('RENDER') == 'true'
# #     opts = dict(httponly=True, samesite='Lax', secure=is_prod)
# #     response.set_cookie('nux_access',   access_token,   max_age=3600,         **opts)
# #     response.set_cookie('nux_refresh',  refresh_token,  max_age=60*60*24*30,  **opts)
# #     response.set_cookie('nux_username', username,       max_age=60*60*24*30,
# #                         samesite='Lax', secure=is_prod)
# #     response.set_cookie('nux_email',    email,          max_age=60*60*24*30,
# #                         samesite='Lax', secure=is_prod)
# #     return response


# # def _clear_auth_cookies(response):
# #     for name in ('nux_access', 'nux_refresh', 'nux_username', 'nux_email'):
# #         response.delete_cookie(name)
# #     return response


# # # ══════════════════════════════════════════════════════════════════════════════
# # # PUBLIC PAGES
# # # ══════════════════════════════════════════════════════════════════════════════

# # def index(request):
# #     context = {
# #         'is_auth': _is_authenticated(request),
# #         'username': request.COOKIES.get('nux_username', ''),
# #     }
# #     return render(request, 'novelux/index.html', context)

# # def become_author(request):
# #     return render(request, 'novelux/become_author.html')

# # def faq(request):
# #     return render(request, 'novelux/faq.html')

# # def privacy(request):
# #     return render(request, 'novelux/privacy.html')

# # def terms(request):
# #     return render(request, 'novelux/terms.html')

# # def cookies_page(request):
# #     return render(request, 'novelux/cookies.html')

# # def content_guidelines(request):
# #     return render(request, 'novelux/content_guidelines.html')


# # # ══════════════════════════════════════════════════════════════════════════════
# # # AUTH PAGES  (login / register / logout)
# # # ══════════════════════════════════════════════════════════════════════════════

# # def login_page(request):
# #     """
# #     GET  → show login form
# #     The actual auth is done by the AJAX endpoint /auth/login-web/ below.
# #     """
# #     if _is_authenticated(request):
# #         return redirect('novelux:dashboard')

# #     next_url = request.GET.get('next', '/dashboard/')
# #     return render(request, 'novelux/login.html', {
# #         'next': next_url,
# #         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
# #     })


# # def register_page(request):
# #     """Sign-up page (readers only — authors go through onboarding)."""
# #     if _is_authenticated(request):
# #         return redirect('novelux:index')
# #     return render(request, 'novelux/register.html', {
# #         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
# #     })


# # def logout_view(request):
# #     response = redirect('novelux:index')
# #     _clear_auth_cookies(response)
# #     return response


# # # ══════════════════════════════════════════════════════════════════════════════
# # # AJAX AUTH ENDPOINTS  (called by JS fetch — return JSON)
# # # ══════════════════════════════════════════════════════════════════════════════

# # @csrf_exempt
# # @require_POST
# # def ajax_login(request):
# #     """
# #     POST /auth/login-web/
# #     Body: { email, password }
# #     Hits the DRF JWT endpoint, sets httpOnly cookies, returns { ok, next }.
# #     """
# #     import requests as http_requests

# #     try:
# #         body = json.loads(request.body)
# #     except Exception:
# #         return JsonResponse({'error': 'Invalid request body'}, status=400)

# #     email    = body.get('email', '').strip()
# #     password = body.get('password', '').strip()
# #     next_url = body.get('next', '/dashboard/')

# #     if not email or not password:
# #         return JsonResponse({'error': 'Email and password are required'}, status=400)

# #     # Hit the internal DRF login endpoint
# #     base_url = _get_api_base(request)
# #     try:
# #         # r = http_requests.post(
# #         #     f'{base_url}/api/auth/login/',
# #         #     json={'email': email, 'password': password},
# #         #     timeout=10
# #         # )
# #         r = http_requests.post(
# #         f'{base_url}/api/auth/token/',
# #         json={'email': email, 'password': password},
# #         timeout=10
# #         )
        
# #         data = r.json()
# #     except Exception as e:
# #         return JsonResponse({'error': f'Could not reach auth server: {e}'}, status=503)

# #     if r.status_code != 200 or 'access' not in data:
# #         err = data.get('detail') or data.get('error') or 'Invalid email or password'
# #         return JsonResponse({'error': err}, status=401)

# #     response = JsonResponse({'ok': True, 'next': next_url,
# #                              'username': data.get('username', '')})
# #     _set_auth_cookies(
# #         response,
# #         access_token=data['access'],
# #         refresh_token=data.get('refresh', ''),
# #         username=data.get('username', ''),
# #         email=email,
# #     )
# #     return response


# # @csrf_exempt
# # @require_POST
# # def ajax_register(request):
# #     """
# #     POST /auth/register-web/
# #     Body: { username, email, password, role? }
# #     """
# #     import requests as http_requests

# #     try:
# #         body = json.loads(request.body)
# #     except Exception:
# #         return JsonResponse({'error': 'Invalid request body'}, status=400)

# #     base_url = _get_api_base(request)
# #     try:
# #         r = http_requests.post(
# #             f'{base_url}/api/auth/register/',
# #             json={
# #                 'username': body.get('username', '').strip(),
# #                 'email':    body.get('email', '').strip(),
# #                 'password': body.get('password', '').strip(),
# #                 'role':     body.get('role', 'reader'),
# #             },
# #             timeout=10
# #         )
# #         data = r.json()
# #     except Exception as e:
# #         return JsonResponse({'error': f'Server error: {e}'}, status=503)

# #     if r.status_code not in (200, 201):
# #         # Extract first readable error message from DRF response
# #         err = _extract_drf_error(data)
# #         return JsonResponse({'error': err}, status=400)

# #     # Auto-login after register if tokens returned
# #     response = JsonResponse({'ok': True, 'username': data.get('username', '')})
# #     if 'access' in data:
# #         _set_auth_cookies(
# #             response,
# #             access_token=data['access'],
# #             refresh_token=data.get('refresh', ''),
# #             username=data.get('username', ''),
# #             email=body.get('email', ''),
# #         )
# #     return response


# # @csrf_exempt
# # @require_POST
# # def ajax_google_auth(request):
# #     """
# #     POST /auth/google-web/
# #     Body: { id_token, email, name, photo_url }
# #     Verifies with Django backend, sets cookies.
# #     """
# #     import requests as http_requests

# #     try:
# #         body = json.loads(request.body)
# #     except Exception:
# #         return JsonResponse({'error': 'Invalid request body'}, status=400)

# #     base_url = _get_api_base(request)
# #     try:
# #         r = http_requests.post(
# #             f'{base_url}/api/auth/google/',
# #             json={
# #                 'id_token':     body.get('id_token', ''),
# #                 'email':        body.get('email', ''),
# #                 'display_name': body.get('name', ''),
# #                 'photo_url':    body.get('photo_url', ''),
# #             },
# #             timeout=10
# #         )
# #         data = r.json()
# #     except Exception as e:
# #         return JsonResponse({'error': f'Server error: {e}'}, status=503)

# #     if r.status_code != 200 or 'access' not in data:
# #         err = data.get('detail') or data.get('error') or 'Google sign-in failed'
# #         return JsonResponse({'error': err}, status=401)

# #     response = JsonResponse({'ok': True, 'username': data.get('username', ''),
# #                              'is_new': data.get('is_new', False)})
# #     _set_auth_cookies(
# #         response,
# #         access_token=data['access'],
# #         refresh_token=data.get('refresh', ''),
# #         username=data.get('username', ''),
# #         email=data.get('email', body.get('email', '')),
# #     )
# #     return response


# # @csrf_exempt
# # @require_POST
# # def ajax_refresh_token(request):
# #     """
# #     POST /auth/refresh-web/
# #     Silently refresh the access token using the refresh cookie.
# #     """
# #     import requests as http_requests

# #     refresh_token = request.COOKIES.get('nux_refresh', '')
# #     if not refresh_token:
# #         return JsonResponse({'error': 'No refresh token'}, status=401)

# #     base_url = _get_api_base(request)
# #     try:
# #         r = http_requests.post(
# #             f'{base_url}/api/auth/token/refresh/',
# #             json={'refresh': refresh_token},
# #             timeout=10
# #         )
# #         data = r.json()
# #     except Exception as e:
# #         return JsonResponse({'error': str(e)}, status=503)

# #     if r.status_code != 200 or 'access' not in data:
# #         response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
# #         _clear_auth_cookies(response)
# #         return response

# #     response = JsonResponse({'ok': True})
# #     is_prod = os.environ.get('RENDER') == 'true'
# #     response.set_cookie('nux_access', data['access'], max_age=3600,
# #                         httponly=True, samesite='Lax', secure=is_prod)
# #     return response


# # # ══════════════════════════════════════════════════════════════════════════════
# # # AUTHOR DASHBOARD  (JWT-cookie-gated, NOT Django session)
# # # ══════════════════════════════════════════════════════════════════════════════

# # def author_dashboard(request):
# #     """
# #     Serve the dashboard if the user has a valid nux_access cookie.
# #     The cookie is httpOnly so JS can't read it — we inject the token
# #     into a <meta> tag so the page JS can pick it up for API calls.
# #     """
# #     if not _is_authenticated(request):
# #         return redirect(f'/login/?next=/dashboard/')

# #     return render(request, 'novelux/author_dashboard.html', {
# #         'access_token': _jwt_from_request(request),
# #         'username':     request.COOKIES.get('nux_username', 'Author'),
# #         'email':        request.COOKIES.get('nux_email', ''),
# #         'api_base':     '/api',
# #     })


# # def author_onboarding(request):
# #     """
# #     Multi-step author onboarding.
# #     If already logged in we pre-fill user info.
# #     """
# #     return render(request, 'novelux/author_onboarding.html', {
# #         'is_auth':      _is_authenticated(request),
# #         'username':     request.COOKIES.get('nux_username', ''),
# #         'email':        request.COOKIES.get('nux_email', ''),
# #         'access_token': _jwt_from_request(request),
# #         'api_base':     '/api',
# #         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
# #     })


# # # ══════════════════════════════════════════════════════════════════════════════
# # # APK DOWNLOAD
# # # ══════════════════════════════════════════════════════════════════════════════

# # def download_apk(request):
# #     apk_path = os.environ.get('NOVELUX_APK_PATH', '')
# #     if apk_path and os.path.exists(apk_path):
# #         with open(apk_path, 'rb') as f:
# #             response = HttpResponse(f.read(),
# #                 content_type='application/vnd.android.package-archive')
# #             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
# #             return response
# #     return JsonResponse({'detail': 'APK not yet available'}, status=404)


# # # ══════════════════════════════════════════════════════════════════════════════
# # # MISC AJAX
# # # ══════════════════════════════════════════════════════════════════════════════

# # @csrf_exempt
# # @require_POST
# # def book_request_web(request):
# #     try:
# #         data = json.loads(request.body)
# #     except Exception:
# #         data = {}
# #     title  = data.get('title', '').strip()
# #     author = data.get('author', '').strip()
# #     if not title:
# #         return JsonResponse({'error': 'title required'}, status=400)
# #     try:
# #         from apps.stories.models import BookRequest
# #         BookRequest.objects.create(title=title, author=author)
# #     except Exception:
# #         pass
# #     return JsonResponse({'detail': 'Request received!'})


# # @csrf_exempt
# # @require_POST
# # def newsletter_signup(request):
# #     try:
# #         data = json.loads(request.body)
# #         email = data.get('email', '').strip()
# #     except Exception:
# #         email = ''
# #     if not email or '@' not in email:
# #         return JsonResponse({'error': 'valid email required'}, status=400)
# #     return JsonResponse({'detail': 'Subscribed!'})


# # # ══════════════════════════════════════════════════════════════════════════════
# # # INTERNAL HELPERS
# # # ══════════════════════════════════════════════════════════════════════════════

# # def _get_api_base(request):
# #     """
# #     When calling Django's own DRF endpoints from a view we use localhost,
# #     not the public Render URL, to avoid the round-trip.
# #     On Render PORT is 10000 by default.
# #     """
# #     port = os.environ.get('PORT', '8000')
# #     return f'http://127.0.0.1:{port}'


# # def _extract_drf_error(data):
# #     """Pull the first readable error message from a DRF error dict."""
# #     if isinstance(data, str):
# #         return data
# #     if isinstance(data, dict):
# #         for key in ('detail', 'error', 'non_field_errors',
# #                     'email', 'username', 'password'):
# #             val = data.get(key)
# #             if val:
# #                 if isinstance(val, list):
# #                     return str(val[0])
# #                 return str(val)
# #         # Fallback — first value
# #         first = next(iter(data.values()), None)
# #         if first:
# #             return str(first[0] if isinstance(first, list) else first)
# #     return 'Something went wrong. Please try again.'


# from django.shortcuts import render, redirect
# from django.http import HttpResponse, JsonResponse
# from django.views.decorators.http import require_POST, require_http_methods
# from django.views.decorators.csrf import csrf_exempt
# import json, os
# from rest_framework.response import Response
# from apps.users.models import AuthorProfile


# # ══════════════════════════════════════════════════════════════════════════════
# # HELPERS
# # ══════════════════════════════════════════════════════════════════════════════

# def _jwt_from_request(request):
#     """Read JWT from the nux_access cookie (set after login)."""
#     return request.COOKIES.get('nux_access', '')


# def _is_authenticated(request):
#     """Check if the request has a valid JWT cookie."""
#     return bool(_jwt_from_request(request))


# def _set_auth_cookies(response, access_token, refresh_token, username='', email='', role=''):
#     """Set JWT cookies on the response — secure, httponly, samesite."""
#     is_prod = os.environ.get('RENDER') == 'true'
#     opts = dict(httponly=True, samesite='Lax', secure=is_prod)
#     response.set_cookie('nux_access',   access_token,   max_age=3600,         **opts)
#     response.set_cookie('nux_refresh',  refresh_token,  max_age=60*60*24*30,  **opts)
#     response.set_cookie('nux_username', username,       max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod)
#     response.set_cookie('nux_email',    email,          max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod)
#     # Role cookie (not httponly — JS reads it to gate dashboard navigation)
#     response.set_cookie('nux_role',     role,           max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod, httponly=False)
#     return response


# def _clear_auth_cookies(response):
#     for name in ('nux_access', 'nux_refresh', 'nux_username', 'nux_email', 'nux_role'):
#         response.delete_cookie(name)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # PUBLIC PAGES
# # ══════════════════════════════════════════════════════════════════════════════

# def index(request):
#     context = {
#         'is_auth': _is_authenticated(request),
#         'username': request.COOKIES.get('nux_username', ''),
#     }
#     return render(request, 'novelux/index.html', context)

# def become_author(request):
#     return render(request, 'novelux/become_author.html')

# def faq(request):
#     return render(request, 'novelux/faq.html')

# def privacy(request):
#     return render(request, 'novelux/privacy.html')

# def terms(request):
#     return render(request, 'novelux/terms.html')

# def cookies_page(request):
#     return render(request, 'novelux/cookies.html')

# def content_guidelines(request):
#     return render(request, 'novelux/content_guidelines.html')

# def copyright_policy(request):
#     return render(request, 'novelux/copyright_policy.html')


# # ══════════════════════════════════════════════════════════════════════════════
# # AUTH PAGES  (login / register / logout)
# # ══════════════════════════════════════════════════════════════════════════════

# def login_page(request):
#     """
#     GET  → show login form
#     The actual auth is done by the AJAX endpoint /auth/login-web/ below.
#     """
#     if _is_authenticated(request):
#         return redirect('novelux:dashboard')

#     next_url = request.GET.get('next', '/dashboard/')
#     return render(request, 'novelux/login.html', {
#         'next': next_url,
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# def register_page(request):
#     """Sign-up page (readers only — authors go through onboarding)."""
#     if _is_authenticated(request):
#         return redirect('novelux:index')
#     return render(request, 'novelux/register.html', {
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# def logout_view(request):
#     response = redirect('novelux:index')
#     _clear_auth_cookies(response)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # AJAX AUTH ENDPOINTS  (called by JS fetch — return JSON)
# # ══════════════════════════════════════════════════════════════════════════════
# """
# @csrf_exempt
# @require_POST
# def ajax_login(request):
    
#     POST /auth/login-web/
#     Body: { email, password }
#     Hits the DRF JWT endpoint, sets httpOnly cookies, returns { ok, next }.
    
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     email    = body.get('email', '').strip()
#     password = body.get('password', '').strip()
#     next_url = body.get('next', '/dashboard/')

#     if not email or not password:
#         return JsonResponse({'error': 'Email and password are required'}, status=400)

#     # Hit the internal DRF login endpoint
#     base_url = _get_api_base(request)
#     try:
#         # r = http_requests.post(
#         #     f'{base_url}/api/auth/login/',
#         #     json={'email': email, 'password': password},
#         #     timeout=10
#         # )
#         r = http_requests.post(
#         f'{base_url}/api/auth/token/',
#         json={'email': email, 'password': password},
#         timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Could not reach auth server: {e}'}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         err = data.get('detail') or data.get('error') or 'Invalid email or password'
#         return JsonResponse({'error': err}, status=401)

#     response = JsonResponse({'ok': True, 'next': next_url,
#                              'username': data.get('username', '')})
#     _set_auth_cookies(
#         response,
#         access_token=data['access'],
#         refresh_token=data.get('refresh', ''),
#         username=data.get('username', ''),
#         email=email,
#     )
#     return response

# """

# # ══════════════════════════════════════════════════════════════════════════════
# # MINIMAL FIX — only replace ajax_login and ajax_refresh_token
# # Leave ajax_register and ajax_google_auth exactly as they are.
# # ══════════════════════════════════════════════════════════════════════════════

# # Add these imports at the top of novelux_web/views.py if not already there:
# #   from django.contrib.auth import authenticate
# #   from rest_framework_simplejwt.tokens import RefreshToken


# @csrf_exempt
# @require_POST
# def ajax_login(request):
#     """
#     POST /auth/login-web/
#     Authenticates directly via Django — no internal HTTP call.
#     """
#     from django.contrib.auth import authenticate
#     from rest_framework_simplejwt.tokens import RefreshToken

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     email    = body.get('email', '').strip()
#     password = body.get('password', '').strip()
#     next_url = body.get('next', '/dashboard/')

#     if not email or not password:
#         return JsonResponse({'error': 'Email and password are required'}, status=400)

#     # Try authenticating with email as username first
#     user = authenticate(request, username=email, password=password)

#     # If that fails, look up the actual username by email
#     if user is None:
#         try:
#             from apps.users.models import User
#             u = User.objects.get(email__iexact=email)
#             user = authenticate(request, username=u.username, password=password)
#         except Exception:
#             user = None

#     if user is None or not user.is_active:
#         return JsonResponse({'error': 'Invalid email or password'}, status=401)

#     # Mint JWT tokens — embed role in payload for dashboard gating
#     from apps.editorial.models import AuthorEditorLink
#     refresh      = RefreshToken.for_user(user)
#     access_token = refresh.access_token
#     access_token['role']     = user.role
#     access_token['username'] = user.username

#     EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
#     if user.role in EDITOR_ROUTES:
#         next_url = EDITOR_ROUTES[user.role]
#     elif user.role == 'author' and next_url in ('', '/dashboard/', '/'):
#         next_url = '/dashboard/'

#     response = JsonResponse({
#         'ok': True, 'next': next_url,
#         'username': user.username, 'role': user.role,
#     })
#     _set_auth_cookies(
#         response,
#         access_token  = str(access_token),
#         refresh_token = str(refresh),
#         username      = user.username,
#         email         = user.email,
#         role          = user.role,
#     )
#     return response


# @csrf_exempt
# @require_POST
# def ajax_refresh_token(request):
#     """
#     POST /auth/refresh-web/
#     Refreshes access token directly via SimpleJWT — no internal HTTP call.
#     """
#     from rest_framework_simplejwt.tokens import RefreshToken
#     from rest_framework_simplejwt.exceptions import TokenError

#     refresh_token = request.COOKIES.get('nux_refresh', '')
#     if not refresh_token:
#         return JsonResponse({'error': 'No refresh token'}, status=401)

#     try:
#         refresh    = RefreshToken(refresh_token)
#         new_access = str(refresh.access_token)
#     except TokenError:
#         response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
#         _clear_auth_cookies(response)
#         return response

#     is_prod = os.environ.get('RENDER') == 'true'
#     response = JsonResponse({'ok': True})
#     response.set_cookie('nux_access', new_access, max_age=3600,
#                         httponly=True, samesite='Lax', secure=is_prod)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # Replace ajax_register in novelux_web/views.py
# # ══════════════════════════════════════════════════════════════════════════════

# @csrf_exempt
# @require_POST
# def ajax_register(request):
#     """
#     POST /auth/register-web/
#     Creates a user directly via Django ORM — no internal HTTP call.
#     """
#     from rest_framework_simplejwt.tokens import RefreshToken

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     username = body.get('username', '').strip()
#     email    = body.get('email', '').strip()
#     password = body.get('password1', '').strip()
#     role     = body.get('role', 'reader')

#     # ── Validate ──────────────────────────────────────────────────────────
#     if not username:
#         return JsonResponse({'error': 'Username is required'}, status=400)
#     if not email:
#         return JsonResponse({'error': 'Email is required'}, status=400)
#     if not password:
#         return JsonResponse({'error': 'Password is required'}, status=400)
#     if len(password) < 8:
#         return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)

#     # ── Check uniqueness ──────────────────────────────────────────────────
#     from apps.users.models import User

#     if User.objects.filter(username__iexact=username).exists():
#         return JsonResponse({'error': 'Username already taken'}, status=400)

#     if User.objects.filter(email__iexact=email).exists():
#         return JsonResponse({'error': 'An account with this email already exists'}, status=400)

#     # ── Create user ───────────────────────────────────────────────────────
#     try:
#         user = User.objects.create_user(
#             username = username,
#             email    = email,
#             password = password,
#         )
#         if hasattr(user, 'role') and role:
#             user.role = role
#             user.save(update_fields=['role'])
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=400)

#     # ── Auto-login: mint JWT tokens directly ──────────────────────────────
#     refresh = RefreshToken.for_user(user)
#     access  = str(refresh.access_token)

#     response = JsonResponse({'ok': True, 'username': user.username})
#     _set_auth_cookies(
#         response,
#         access_token  = access,
#         refresh_token = str(refresh),
#         username      = user.username,
#         email         = user.email,
#     )
#     return response

# """
# @csrf_exempt
# @require_POST
# def ajax_register(request):
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     base_url = _get_api_base(request)
#     from django.contrib.auth import get_user_model
#     User = get_user_model()
    
#     email = body.get('email', '').strip()  # ✅ fixed
#     user = User.objects.filter(email=email).first()
        
#     if user:
#         user.role = User.ROLE_AUTHOR
#         user.save()
#         AuthorProfile.objects.get_or_create(user=user)  # ✅ creates if missing
#         return JsonResponse({'detail': 'You are now an author!'}, status=200)
    
#     editor_code = body.get('editor_code', '').strip().upper()

#     # Pre-validate editor code before hitting the registration API
#     if editor_code:
#         from django.contrib.auth import get_user_model as _gum
#         _User = _gum()
#         if not _User.objects.filter(editor_code=editor_code, role='se').exists():
#             return JsonResponse(
#                 {'error': 'Invalid editor code. Double-check the code with your editor.'},
#                 status=400,
#             )

#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/dj/registration/',
#             json={
#                 'username':    body.get('username', 'N/A').strip(),
#                 'email':       body.get('email', 'N/A').strip(),
#                 'password1':   body.get('password1', 'N/A').strip(),
#                 'password2':   body.get('password2', 'N/A').strip(),
#                 'role':        body.get('role', 'reader'),
#                 'editor_code': editor_code,
#             },
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Server error: {e}'}, status=503)

#     if r.status_code not in (200, 201):
#         err = _extract_drf_error(data)
#         return JsonResponse({'error': err}, status=400)

#     # Determine redirect based on role
#     role = body.get('role', 'reader')
#     EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
#     next_url = EDITOR_ROUTES.get(role, '/dashboard/')

#     response = JsonResponse({
#         'ok':       True,
#         'username': data.get('username', ''),
#         'role':     role,
#         'next':     next_url,
#     })
#     if 'access' in data:
#         _set_auth_cookies(
#             response,
#             access_token=data['access'],
#             refresh_token=data.get('refresh', ''),
#             username=data.get('username', ''),
#             email=body.get('email', ''),
#             role=role,
#         )
#     return response
# """

# @csrf_exempt
# @require_POST
# def ajax_google_auth(request):
#     """
#     POST /auth/google-web/
#     Body: { id_token, email, name, photo_url }
#     Verifies with Django backend, sets cookies.
#     """
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     base_url = _get_api_base(request)
#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/google/',
#             json={
#                 'id_token':     body.get('id_token', ''),
#                 'email':        body.get('email', ''),
#                 'display_name': body.get('name', ''),
#                 'photo_url':    body.get('photo_url', ''),
#             },
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Server error: {e}'}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         err = data.get('detail') or data.get('error') or 'Google sign-in failed'
#         return JsonResponse({'error': err}, status=401)

#     # Decode role from JWT payload if available
#     _google_role = 'reader'
#     try:
#         from rest_framework_simplejwt.tokens import AccessToken as _AT
#         _google_role = _AT(data['access']).payload.get('role', 'reader')
#     except Exception:
#         pass
#     EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
#     _google_next  = EDITOR_ROUTES.get(_google_role, '/dashboard/')

#     response = JsonResponse({
#         'ok': True, 'username': data.get('username', ''),
#         'is_new': data.get('is_new', False),
#         'next': _google_next, 'role': _google_role,
#     })
#     _set_auth_cookies(
#         response,
#         access_token=data['access'],
#         refresh_token=data.get('refresh', ''),
#         username=data.get('username', ''),
#         email=data.get('email', body.get('email', '')),
#         role=_google_role,
#     )
#     return response

# """
# @csrf_exempt
# @require_POST
# def ajax_refresh_token(request):
    
#     POST /auth/refresh-web/
#     Silently refresh the access token using the refresh cookie.
    
#     import requests as http_requests

#     refresh_token = request.COOKIES.get('nux_refresh', '')
#     if not refresh_token:
#         return JsonResponse({'error': 'No refresh token'}, status=401)

#     base_url = _get_api_base(request)
#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/token/refresh/',
#             json={'refresh': refresh_token},
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
#         _clear_auth_cookies(response)
#         return response

#     # Re-decode role from the new access token
#     _refresh_role = request.COOKIES.get('nux_role', 'reader')
#     try:
#         from rest_framework_simplejwt.tokens import AccessToken as _AT2
#         _refresh_role = _AT2(data['access']).payload.get('role', _refresh_role)
#     except Exception:
#         pass
#     response = JsonResponse({'ok': True, 'role': _refresh_role})
#     is_prod = os.environ.get('RENDER') == 'true'
#     response.set_cookie('nux_access', data['access'], max_age=3600,
#                         httponly=True, samesite='Lax', secure=is_prod)
#     response.set_cookie('nux_role', _refresh_role, max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod, httponly=False)
#     return response

# """
# def author_dashboard(request):
#     """
#     Serve the dashboard if the user has a valid nux_access cookie.
#     Pulls real data from the DB and injects it into the template context
#     so the page renders correctly server-side without extra API round-trips.
#     """
#     if not _is_authenticated(request):
#         return redirect(f'/login/?next=/dashboard/')

#     # ── Resolve the author from the JWT stored in the cookie ─────────────────
#     from apps.users.models import User, AuthorProfile
#     from apps.stories.models import Story
#     from apps.chapters.models import Chapter
#     from apps.tips.models import Tip
#     from apps.coins.models import AuthorPayout
#     from django.db.models import Sum, Count, Q
#     from django.utils import timezone
#     import datetime, json

#     username = request.COOKIES.get('nux_username', '')
#     try:
#         user = User.objects.select_related('author_profile').get(username=username)
#     except User.DoesNotExist:
#         # Fall back gracefully — render with empty data
#         user = None

#     # ── Story queryset for this author ────────────────────────────────────────
#     stories_qs = (
#         Story.objects
#         .filter(author=user)
#         .prefetch_related('chapters')
#         .order_by('-created_at')
#         if user else Story.objects.none()
#     )

#     stories_list = list(
#         stories_qs.values(
#             'id', 'title', 'slug', 'status',
#             'total_views', 'total_chapters', 'word_count',
#             'total_tips', 'average_rating', 'total_ratings',
#             'total_comments', 'created_at',
#             'contract_status', 'contract_eligible',
#         )
#     )

#     # Human-friendly numbers for the template
#     def fmt(n):
#         if n >= 1_000_000:
#             return f'{n/1_000_000:.1f}M'
#         if n >= 1_000:
#             return f'{n/1_000:.1f}K'
#         return str(n)

#     for s in stories_list:
#         s['reads_fmt']    = fmt(s['total_views'])
#         s['words_fmt']    = f"{s['word_count']:,}"
#         s['badge_class']  = {
#             'published': 'badge-green',
#             'ongoing':   'badge-green',
#             'draft':     'badge-yellow',
#             'paused':    'badge-yellow',
#             'completed': 'badge-primary',
#         }.get(s['status'], 'badge-gray')
#         # Show "Apply for Contract" when threshold hit but not yet applied
#         s['can_apply_contract'] = (
#             s.get('contract_eligible', False) and
#             s.get('contract_status', 'none') == 'none'
#         )

#     # ── Aggregate stats ───────────────────────────────────────────────────────
#     totals = stories_qs.aggregate(
#         total_reads    = Sum('total_views'),
#         total_chapters = Sum('total_chapters'),
#         total_words    = Sum('word_count'),
#         total_comments = Sum('total_comments'),
#         story_count    = Count('id'),
#     )

#     total_reads    = totals['total_reads']    or 0
#     total_chapters = totals['total_chapters'] or 0
#     total_comments = totals['total_comments'] or 0
#     story_count    = totals['story_count']    or 0

#     published_count = stories_qs.filter(status__in=['published', 'ongoing', 'completed']).count()
#     draft_count     = stories_qs.filter(status__in=['draft', 'paused']).count()

#     # Follower count
#     followers_count = 0
#     if user:
#         try:
#             followers_count = user.followers.count()
#         except Exception:
#             pass

#     # ── Earnings / Author profile ─────────────────────────────────────────────
#     total_earnings   = 0.0
#     pending_payout   = 0.0
#     contract_type    = ''
#     is_verified      = False

#     if user:
#         try:
#             ap = user.author_profile
#             total_earnings = float(ap.total_earnings)
#             pending_payout = float(ap.pending_payout)
#             contract_type  = ap.contract_type
#             is_verified    = ap.is_verified
#         except Exception:
#             pass

#     # Tips received by this author
#     tips_received_coins = 0
#     if user:
#         try:
#             tips_received_coins = (
#                 Tip.objects.filter(recipient=user)
#                 .aggregate(total=Sum('coins_amount'))['total'] or 0
#             )
#         except Exception:
#             pass

#     # Payout history (latest 5)
#     payouts = []
#     if user:
#         try:
#             payouts = list(
#                 AuthorPayout.objects
#                 .filter(author=user)
#                 .order_by('-requested_at')[:5]
#                 .values('amount_usd', 'status', 'payout_method', 'requested_at')
#             )
#             for p in payouts:
#                 p['requested_at_fmt'] = p['requested_at'].strftime('%b %-d, %Y')
#                 p['badge_class'] = {
#                     'processed': 'badge-green',
#                     'pending':   'badge-yellow',
#                     'failed':    'badge-red',
#                 }.get(p['status'], 'badge-gray')
#         except Exception:
#             payouts = []

#     # ── Chapters for the most-read story (for the Chapters page) ─────────────
#     chapters_list = []
#     featured_story_title = ''
#     if stories_list:
#         top_story_id = max(stories_list, key=lambda s: s['total_views'])['id']
#         featured_story_title = next(s['title'] for s in stories_list if s['id'] == top_story_id)
#         chapters_list = list(
#             Chapter.objects
#             .filter(story_id=top_story_id)
#             .order_by('chapter_number')
#             .values('chapter_number', 'title', 'word_count', 'is_published', 'views', 'unlocks')
#         )
#         for ch in chapters_list:
#             ch['words_fmt'] = f"{ch['word_count']:,}"
#             ch['reads_fmt'] = fmt(ch['views'])
#             ch['status']    = 'published' if ch['is_published'] else 'draft'
#             ch['badge_class'] = 'badge-green' if ch['is_published'] else 'badge-yellow'

#     # ── Weekly reads chart (last 7 days, sum of views is denormalized,
#     #    so we approximate from ReadingHistory if available) ──────────────────
#     weekly_reads  = [0] * 7
#     weekly_labels = []
#     today = timezone.now().date()
#     for i in range(6, -1, -1):
#         d = today - datetime.timedelta(days=i)
#         weekly_labels.append(d.strftime('%a'))
#     # We don't have a daily_views table, so pass the placeholder zeros —
#     # the JS will render the chart; replace with real data if you add a DailyView model.

#     # ── Analytics: per-story table data ──────────────────────────────────────
#     analytics_rows = []
#     for s in stories_list[:10]:
#         analytics_rows.append({
#             'title':    s['title'],
#             'status':   s['status'],
#             'reads':    s['reads_fmt'],
#             'chapters': s['total_chapters'],
#             'rating':   float(s['average_rating']),
#             'comments': s['total_comments'],
#         })

#     # ── User profile data ─────────────────────────────────────────────────────
#     display_name = ''
#     bio          = ''
#     avatar   = ''
#     if user:
#         display_name = f"{user.first_name} {user.last_name}".strip() or user.username
#         bio          = user.bio
#         if user.avatar:
#             try:
#                 avatar = user.avatar.url
#             except Exception:
#                 pass

#     # ── Greeting ──────────────────────────────────────────────────────────────
#     hour = timezone.localtime(timezone.now()).hour
#     if hour < 12:
#         greeting_time = 'morning'
#     elif hour < 17:
#         greeting_time = 'afternoon'
#     else:
#         greeting_time = 'evening'

#     context = {
#         # Auth
#         'access_token':  _jwt_from_request(request),
#         'username':      username,
#         'email':         request.COOKIES.get('nux_email', ''),
#         'api_base':      '/api',

#         # Greeting
#         'greeting_time':  greeting_time,
#         'display_name':   display_name or username,

#         # Overview stats
#         'total_reads':     fmt(total_reads),
#         'followers_count': fmt(followers_count),
#         'story_count':     story_count,
#         'published_count': published_count,
#         'draft_count':     draft_count,
#         'total_chapters':  total_chapters,
#         'total_comments':  fmt(total_comments),
#         'tips_coins':      tips_received_coins,

#         # Stories
#         'stories':         stories_list,
#         'stories_json':    json.dumps(stories_list, default=str),

#         # Chapters (top story)
#         'chapters':              chapters_list,
#         'chapters_json':         json.dumps(chapters_list, default=str),
#         'featured_story_title':  featured_story_title,

#         # Earnings
#         'total_earnings':   f'{total_earnings:,.2f}',
#         'pending_payout':   f'{pending_payout:,.2f}',
#         'contract_type':    contract_type,
#         'is_verified':      is_verified,
#         'payouts':          payouts,

#         # Analytics
#         'analytics_rows':   analytics_rows,
#         'analytics_json':   json.dumps(analytics_rows),

#         # Chart data
#         'weekly_labels_json': json.dumps(weekly_labels),
#         'weekly_reads_json':  json.dumps(weekly_reads),

#         # Profile
#         'bio':        bio,
#         'avatar': avatar,
#     }

#     return render(request, 'novelux/author_dashboard.html', context)

# def author_onboarding(request):
#     """
#     Multi-step author onboarding.
#     If already logged in we pre-fill user info.
#     """
#     return render(request, 'novelux/author_onboarding.html', {
#         'is_auth':      _is_authenticated(request),
#         'username':     request.COOKIES.get('nux_username', ''),
#         'email':        request.COOKIES.get('nux_email', ''),
#         'access_token': _jwt_from_request(request),
#         'api_base':     '/api',
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# # ══════════════════════════════════════════════════════════════════════════════
# # APK DOWNLOAD
# # ══════════════════════════════════════════════════════════════════════════════

# # def download_apk(request):
# #     apk_path = os.environ.get('NOVELUX_APK_PATH', '')
# #     if apk_path and os.path.exists(apk_path):
# #         with open(apk_path, 'rb') as f:
# #             response = HttpResponse(f.read(),
# #                 content_type='application/vnd.android.package-archive')
# #             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
# #             return response
# #     return JsonResponse({'detail': 'APK not yet available'}, status=404)


# # ══════════════════════════════════════════════════════════════════════════════
# # MISC AJAX
# # ══════════════════════════════════════════════════════════════════════════════

# @csrf_exempt
# @require_POST
# def book_request_web(request):
#     try:
#         data = json.loads(request.body)
#     except Exception:
#         data = {}
#     title  = data.get('title', '').strip()
#     author = data.get('author', '').strip()
#     if not title:
#         return JsonResponse({'error': 'title required'}, status=400)
#     try:
#         from apps.stories.models import BookRequest
#         BookRequest.objects.create(title=title, author=author)
#     except Exception:
#         pass
#     return JsonResponse({'detail': 'Request received!'})


# @csrf_exempt
# @require_POST
# def newsletter_signup(request):
#     try:
#         data = json.loads(request.body)
#         email = data.get('email', '').strip()
#     except Exception:
#         email = ''
#     if not email or '@' not in email:
#         return JsonResponse({'error': 'valid email required'}, status=400)
#     return JsonResponse({'detail': 'Subscribed!'})


# # ══════════════════════════════════════════════════════════════════════════════
# # INTERNAL HELPERS
# # ══════════════════════════════════════════════════════════════════════════════

# def _get_api_base(request):
#     """
#     Returns the API base URL for use in dashboard templates (injected as
#     the nux-api meta tag so JS fetch calls can reach DRF endpoints).

#     Always returns a path-only '/api' so it works on any host — local dev,
#     Render, or any other deployment — without hardcoding a domain.
#     """
#     return '/api'


# def _extract_drf_error(data):
#     """Pull the first readable error message from a DRF error dict."""
#     if isinstance(data, str):
#         return data
#     if isinstance(data, dict):
#         for key in ('detail', 'error', 'non_field_errors',
#                     'email', 'username', 'password'):
#             val = data.get(key)
#             if val:
#                 if isinstance(val, list):
#                     return str(val[0])
#                 return str(val)
#         # Fallback — first value
#         first = next(iter(data.values()), None)
#         if first:
#             return str(first[0] if isinstance(first, list) else first)
#     return 'Something went wrong. Please try again.'


# def download_apk(request):
#     # \"\"\"
#     # GET  /download/apk/          → shows the download page
#     # GET  /download/apk/?dl=1     → streams the APK file directly
#     # \"\"\"
#     from novelux_web.models import APKRelease
#     from django.http import FileResponse, Http404
 
#     release = APKRelease.get_latest()
 
#     # Direct download triggered by ?dl=1 (the Download button hits this)
#     if request.GET.get('dl') == '1':
#         if not release or not release.apk_file:
#             raise Http404('APK not available yet.')
#         # Increment download counter
#         from django.db import models
#         APKRelease.objects.filter(pk=release.pk).update(
#             download_count=models.F('download_count') + 1
#         )
#         try:
#             response = FileResponse(
#                 release.apk_file.open('rb'),
#                 content_type='application/vnd.android.package-archive',
#                 as_attachment=True,
#                 filename=f'novelux-v{release.version_name}.apk',
#             )
#             return response
#         except Exception:
#             raise Http404('APK file could not be read.')
 
#     # Default: show the download landing page
#     return render(request, 'novelux/download.html', {'release': release})


# # ═══════════════════════════════════════════════════════════════════════════════
# #  EDITOR DASHBOARD VIEWS  (AE / SE / CE)
# # ═══════════════════════════════════════════════════════════════════════════════

# def _editor_required(roles):
#     """Inline decorator: redirect to login unless user has one of the given roles."""
#     from functools import wraps
#     def decorator(fn):
#         @wraps(fn)
#         def wrapper(request, *args, **kwargs):
#             if not _is_authenticated(request):
#                 return redirect(f'/login/?next={request.path}')
#             role = request.COOKIES.get('nux_role', '')
#             if role not in roles:
#                 # Try to get fresh role from access token payload
#                 from rest_framework_simplejwt.tokens import AccessToken as AT
#                 token_str = _jwt_from_request(request)
#                 try:
#                     tok   = AT(token_str)
#                     role  = tok.payload.get('role', '')
#                 except Exception:
#                     role  = ''
#             if role not in roles:
#                 return redirect('/login/?error=access_denied')
#             return fn(request, *args, **kwargs)
#         return wrapper
#     return decorator


# def _editorial_context(request):
#     """
#     Build the template context for all editor dashboards.
    
#     NOTE: The ChapterReview model has been removed. Editorial state now lives
#     directly on Chapter.status. This function returns a minimal context to prevent
#     import errors. The editor dashboards are transitioning to use the modern
#     editorial API (apps.editorial.views) instead of these legacy web views.
#     """
#     from django.contrib.auth import get_user_model
#     from django.utils import timezone

#     User    = get_user_model()
#     token   = _jwt_from_request(request)
#     api_url = _get_api_base(request)

#     # Resolve user from JWT
#     user = None
#     try:
#         from rest_framework_simplejwt.tokens import AccessToken as AT
#         tok     = AT(token)
#         user_id = tok.payload.get('user_id')
#         if user_id:
#             user = User.objects.get(pk=user_id)
#     except Exception:
#         pass

#     ctx = {
#         'api_url':     api_url,
#         'access_token': token,
#         'editor':      user,
#         'role':        user.role if user else '',
#     }

#     if user and user.role == 'se' and not user.editor_code:
#         user.generate_editor_code()

#     if not user:
#         return ctx

#     role = user.role

#     # TODO: Refactor these dashboard views to use the modern editorial API
#     # and the new Chapter-based workflow instead of the legacy ChapterReview model.
    
#     if role == 'se':
#         from django.contrib.auth import get_user_model as _gum
#         from django.db.models import Count as _Count
#         from apps.chapters.models import Chapter
#         from datetime import timedelta
#         from apps.stories.models import Story
#         from apps.editorial.models import ContractApplication

#         _User = _gum()

#         # Stories awaiting SE review (threshold hit, contract_status=under_review,
#         # and the ContractApplication is assigned to this SE)
#         review_stories = Story.objects.filter(
#             contract_status='under_review',
#             author__editor_link__assigned_se=user,
#         ).select_related('author').prefetch_related(
#             'chapters'
#         ).order_by('-updated_at')[:50]

#         # Annotate each story with its chapter list and contract application
#         for s in review_stories:
#             s.chapters_list = list(
#                 s.chapters.order_by('chapter_number')
#                 .values('id','chapter_number','title','status','word_count','created_at')
#             )
#             try:
#                 s.contract_app = s.contract_application
#             except ContractApplication.DoesNotExist:
#                 s.contract_app = None

#         # Stories already SE-approved (passed to CE)
#         approved_stories = Story.objects.filter(
#             contract_status__in=['contract_sent','signed'],
#             author__editor_link__assigned_se=user,
#         ).select_related('author').order_by('-updated_at')[:20]

#         one_week_ago = timezone.now() - timedelta(days=7)
#         cleared_this_week = ContractApplication.objects.filter(
#             assigned_se=user,
#             status__in=['se_approved','contract_sent','signed'],
#             se_reviewed_at__gte=one_week_ago,
#         ).count()

#         ctx.update({
#             'pending_count':       review_stories.count(),
#             'review_stories':      review_stories,
#             'approved_stories':    approved_stories,
#             'cleared_this_week':   cleared_this_week,
#             'policy_actions_month': 0,
#             'recent_se_decisions': approved_stories,
#             'flagged_items': [],
#             'supervisor_ce': (
#                 user.editorial_assignment.supervisor
#                 if hasattr(user, 'editorial_assignment') and
#                    user.editorial_assignment.supervisor else None
#             ),
#             'author_overview': _User.objects.filter(
#                 role='author',
#                 editor_link__assigned_se=user,
#             ).order_by('username')[:50],
#         })

#     elif role == 'ce':
#         from django.contrib.auth import get_user_model as _gum
#         from apps.editorial.models import EditorialPolicy, ContractApplication
#         from apps.stories.models import Story

#         _User = _gum()

#         se_qs = _User.objects.filter(
#             role='se', editorial_assignment__supervisor=user,
#         )

#         # Stories SE-approved and waiting for CE action (send contract)
#         pending_stories = Story.objects.filter(
#             contract_status='contract_sent',
#             author__editor_link__assigned_se__editorial_assignment__supervisor=user,
#         ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

#         # Fallback: also catch stories approved by any SE (no CE assignment yet)
#         if not pending_stories.exists():
#             pending_stories = Story.objects.filter(
#                 contract_status='contract_sent',
#             ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

#         for s in pending_stories:
#             s.chapters_list = list(
#                 s.chapters.order_by('chapter_number')
#                 .values('id', 'chapter_number', 'title', 'status', 'word_count', 'created_at')
#             )
#             try:
#                 s.contract_app = s.contract_application
#             except ContractApplication.DoesNotExist:
#                 s.contract_app = None

#         signed_stories = Story.objects.filter(
#             contract_status='signed',
#         ).select_related('author').order_by('-updated_at')[:20]

#         ctx.update({
#             'pending_stories':          pending_stories,
#             'pending_stories_count':    pending_stories.count(),
#             'signed_stories':           signed_stories,
#             'se_count':                 se_qs.count(),
#             'se_team':                  se_qs,
#             'pending_policies_count':   EditorialPolicy.objects.filter(status='under_review').count(),
#             'policies_pending':         EditorialPolicy.objects.filter(
#                 status='under_review',
#             ).select_related('proposed_by').order_by('-created_at'),
#             'active_policies':          EditorialPolicy.objects.filter(
#                 status='active',
#             ).select_related('proposed_by', 'approved_by').order_by('-published_at'),
#             'all_editors':              _User.objects.filter(role='se').order_by('username'),
#             'author_overview':          _User.objects.filter(role='author').order_by('username')[:100],
#             # legacy keys kept so other template sections don't crash
#             'ce_escalation_count':      pending_stories.count(),
#             'ce_escalations':           [],
#             'chapters_cleared_month':   0,
#             'content_removed_month':    0,
#             'se_decisions':             [],
#         })

#     return ctx



# @_editor_required(['se'])
# def se_dashboard(request):
#     ctx = _editorial_context(request)
#     return render(request, 'novelux/se_dashboard.html', ctx)


# @_editor_required(['ce'])
# def ce_dashboard(request):
#     ctx = _editorial_context(request)
#     return render(request, 'novelux/ce_dashboard.html', ctx)


# def editor_login_redirect(request):
#     """
#     After login, redirect editors to the correct dashboard based on their role.
#     Called when an editor visits /dashboard/ but their role is not 'author'.
#     """
#     from rest_framework_simplejwt.tokens import AccessToken as AT
#     token = _jwt_from_request(request)
#     role  = 'reader'
#     try:
#         tok  = AT(token)
#         role = tok.payload.get('role', 'reader')
#     except Exception:
#         pass

#     routes = {
#         'se': '/editorial/se/',
#         'ce': '/editorial/ce/',
#     }
#     return redirect(routes.get(role, '/'))


# # ═══════════════════════════════════════════════════════════════════════════════
# #  EDITOR ONBOARDING — INVITE ACCEPTANCE WEB VIEWS
# # ═══════════════════════════════════════════════════════════════════════════════

# def editor_invite_page(request, token):
#     """
#     GET  /editorial/invite/<token>/
#          Shows the onboarding registration form with role pre-filled.

#     POST /editorial/invite/<token>/
#          Creates the account, calls invite.accept(user), sets cookies,
#          redirects to the correct editor dashboard.
#     """
#     from apps.editorial.models import EditorInvite
#     from django.utils import timezone

#     ROLE_LABELS = {'se': 'Senior Editor'}

#     # Look up the invite
#     try:
#         invite = EditorInvite.objects.select_related(
#             'invited_by', 'supervisor',
#         ).get(token=token)
#     except EditorInvite.DoesNotExist:
#         return render(request, 'novelux/invite_invalid.html', {
#             'reason': 'This invite link does not exist.',
#         }, status=404)

#     if not invite.is_valid:
#         reason = (
#             'This invite has already been used.'
#             if invite.status == EditorInvite.STATUS_ACCEPTED
#             else 'This invite link has expired or been revoked.'
#         )
#         return render(request, 'novelux/invite_invalid.html', {
#             'reason': reason,
#             'invite': invite,
#         }, status=410)

#     ctx = {
#         'invite':      invite,
#         'role_label':  ROLE_LABELS.get(invite.role, invite.role.upper()),
#         'error':       None,
#     }

#     if request.method == 'GET':
#         return render(request, 'novelux/editor_onboarding.html', ctx)

#     # ── POST: create account ──────────────────────────────────────────────────
#     from django.contrib.auth import get_user_model
#     User = get_user_model()

#     username   = request.POST.get('username', '').strip()
#     password1  = request.POST.get('password1', '').strip()
#     password2  = request.POST.get('password2', '').strip()
#     first_name = request.POST.get('first_name', '').strip()
#     last_name  = request.POST.get('last_name', '').strip()

#     # Validation
#     errors = {}
#     if not username:
#         errors['username'] = 'Username is required.'
#     elif User.objects.filter(username=username).exists():
#         errors['username'] = 'That username is already taken.'
#     if len(password1) < 8:
#         errors['password1'] = 'Password must be at least 8 characters.'
#     if password1 != password2:
#         errors['password2'] = 'Passwords do not match.'

#     if errors:
#         ctx['errors'] = errors
#         ctx['form'] = {
#             'username':   username,
#             'first_name': first_name,
#             'last_name':  last_name,
#         }
#         return render(request, 'novelux/editor_onboarding.html', ctx)

#     # Create user
#     user = User.objects.create_user(
#         username   = username,
#         email      = invite.email,
#         password   = password1,
#         first_name = first_name,
#         last_name  = last_name,
#         role       = invite.role,       # pre-set the role
#     )

#     # Accept invite: creates EditorAssignment, generates editor_code for AEs
#     invite.accept(user)

#     # Mint JWT and set cookies — same flow as ajax_login
#     from rest_framework_simplejwt.tokens import RefreshToken
#     refresh      = RefreshToken.for_user(user)
#     access_token = refresh.access_token
#     access_token['role']     = user.role
#     access_token['username'] = user.username

#     EDITOR_ROUTES = {'ae': '/editorial/ae/', 'se': '/editorial/se/'}
#     next_url = EDITOR_ROUTES.get(user.role, '/editorial/')

#     response = redirect(next_url)
#     _set_auth_cookies(
#         response,
#         access_token  = str(access_token),
#         refresh_token = str(refresh),
#         username      = user.username,
#         email         = user.email,
#         role          = user.role,
#     )
#     return response




# def contract_sign_page(request, slug):
#     """
#     GET /my-books/<slug>/contract/
#     Renders the contract signing page for the author.
#     Accessible via dashboard or the email link.
#     """
#     if not _is_authenticated(request):
#         return redirect(f'/login/?next=/my-books/{slug}/contract/')

#     from apps.stories.models import Story
#     from apps.editorial.models import ContractApplication
#     from apps.users.models import User

#     username = request.COOKIES.get('nux_username', '')
#     try:
#         user = User.objects.select_related('author_profile').get(username=username)
#     except User.DoesNotExist:
#         return redirect(f'/login/?next=/my-books/{slug}/contract/')

#     try:
#         story = Story.objects.get(slug=slug, author=user)
#     except Story.DoesNotExist:
#         from django.http import Http404
#         raise Http404

#     try:
#         app = story.contract_application
#         contract_type       = app.contract_type or 'non_exclusive'
#         ce_note             = (app.se_note or '').split('\n\nCE note:')[-1].strip() if 'CE note:' in (app.se_note or '') else ''
#         already_signed      = app.status == ContractApplication.STATUS_SIGNED
#     except ContractApplication.DoesNotExist:
#         contract_type  = 'non_exclusive'
#         ce_note        = ''
#         already_signed = getattr(user, 'author_profile', None) and user.author_profile.has_contract

#     contract_type_label = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'

#     return render(request, 'novelux/contract_sign.html', {
#         'story':               story,
#         'contract_type':       contract_type,
#         'contract_type_label': contract_type_label,
#         'ce_note':             ce_note,
#         'already_signed':      already_signed,
#         'access_token':        _jwt_from_request(request),
#         'api_base':            '/api',
#     })

# @csrf_exempt
# def ce_invite_create_web(request):
#     """
#     POST /editorial/invite/create/
#     AJAX endpoint called from the CE dashboard invite modal.
#     Body: { email, role, supervisor_id, notes }
#     Returns JSON.
#     """
#     if not _is_authenticated(request):
#         return JsonResponse({'error': 'Authentication required.'}, status=401)

#     from apps.editorial.models import EditorInvite
#     from apps.editorial.tasks import send_editor_invite_email
#     from django.contrib.auth import get_user_model
#     from rest_framework_simplejwt.tokens import AccessToken as AT

#     # Verify CE role
#     token_str = _jwt_from_request(request)
#     try:
#         tok  = AT(token_str)
#         role = tok.payload.get('role', '')
#     except Exception:
#         role = ''

#     if role != 'ce':
#         return JsonResponse({'error': 'Only Chief Editors can create invites.'}, status=403)

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body.'}, status=400)

#     email         = body.get('email', '').strip().lower()
#     editor_role   = body.get('role', '').strip()
#     supervisor_id = body.get('supervisor_id')
#     notes         = body.get('notes', '').strip()

#     if not email:
#         return JsonResponse({'error': 'Email is required.'}, status=400)
#     if editor_role not in ('se',):
#         return JsonResponse({'error': "Role must be 'se'."}, status=400)

#     User = get_user_model()

#     # Get the CE user from JWT
#     try:
#         ce_user = User.objects.get(pk=tok.payload.get('user_id'))
#     except User.DoesNotExist:
#         return JsonResponse({'error': 'CE account not found.'}, status=404)

#     # Resolve supervisor
#     supervisor = None
#     if supervisor_id:
#         try:
#             supervisor = User.objects.get(pk=supervisor_id, role__in=('se', 'ce'))
#         except User.DoesNotExist:
#             return JsonResponse({'error': 'Supervisor not found.'}, status=404)

#     # Check for existing pending invite to this email
#     existing = EditorInvite.objects.filter(
#         email=email, status='pending',
#     ).first()
#     if existing:
#         return JsonResponse({
#             'error': f'A pending invite already exists for {email}. Revoke it first or resend it.',
#         }, status=400)

#     invite = EditorInvite.create_invite(
#         email      = email,
#         role       = editor_role,
#         invited_by = ce_user,
#         supervisor = supervisor,
#         notes      = notes,
#     )

#     try:
#         send_editor_invite_email(invite, request)
#         email_sent = True
#     except Exception as e:
#         email_sent = False

#     return JsonResponse({
#         'ok':          True,
#         'invite_id':   invite.id,
#         'email_sent':  email_sent,
#         'expires_at':  invite.expires_at.isoformat(),
#         'message':     f'Invite {"sent to" if email_sent else "created for"} {email}.',
#     })


# # from django.shortcuts import render
# # from django.http import HttpResponse, JsonResponse
# # from django.views.decorators.http import require_POST
# # from django.contrib.auth.decorators import login_required
# # import json


# # # ── Public pages ──────────────────────────────────────────────────────────────

# # def index(request):
# #     """Landing page — serve stories from API for SEO."""
# #     context = {}
# #     try:
# #         from apps.stories.models import Story
# #         context['featured_stories'] = list(
# #             Story.objects.filter(status='published')
# #             .order_by('-total_views')[:8]
# #             .values('slug', 'title', 'cover_image', 'average_rating', 'total_views')
# #         )
# #     except Exception:
# #         context['featured_stories'] = []
# #     return render(request, 'novelux/index.html', context)


# # def become_author(request):
# #     return render(request, 'novelux/become_author.html')


# # def author_onboarding(request):
# #     return render(request, 'novelux/author_onboarding.html')


# # def faq(request):
# #     return render(request, 'novelux/faq.html')


# # def privacy(request):
# #     return render(request, 'novelux/privacy.html')


# # def terms(request):
# #     return render(request, 'novelux/terms.html')


# # def cookies(request):
# #     return render(request, 'novelux/cookies.html')


# # def content_guidelines(request):
# #     return render(request, 'novelux/content_guidelines.html')


# # # ── Author dashboard (requires login) ─────────────────────────────────────────

# # @login_required(login_url='/api/auth/login/')
# # def author_dashboard(request):
# #     """
# #     Author dashboard — passes author stats to template via context.
# #     The dashboard HTML uses JS to call the DRF API for live data;
# #     this view injects the auth token so the JS can use it.
# #     """
# #     context = {
# #         'user': request.user,
# #         # Pass JWT access token so dashboard JS can hit the DRF API
# #         'api_base': '/api',
# #     }
# #     return render(request, 'novelux/author_dashboard.html', context)


# # # ── APK download ───────────────────────────────────────────────────────────────

# # def download_apk(request):
# #     """
# #     Redirect to the latest APK in storage, or serve a 404-style
# #     page while the app is not yet published.
# #     """
# #     import os
# #     from django.conf import settings

# #     apk_path = getattr(settings, 'NOVELUX_APK_PATH', None)
# #     if apk_path and os.path.exists(apk_path):
# #         with open(apk_path, 'rb') as f:
# #             response = HttpResponse(f.read(),
# #                 content_type='application/vnd.android.package-archive')
# #             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
# #             return response

# #     # APK not yet uploaded — redirect back to landing with a flash
# #     from django.contrib import messages
# #     from django.shortcuts import redirect
# #     messages.info(request, 'APK coming soon — follow us for updates.')
# #     return redirect('novelux:index')


# # # ── Book request (from search "not found") ────────────────────────────────────

# # @require_POST
# # def book_request_web(request):
# #     """Web form submission for 'Find the book' — mirrors the API endpoint."""
# #     try:
# #         data   = json.loads(request.body)
# #         title  = data.get('title', '').strip()
# #         author = data.get('author', '').strip()
# #     except (json.JSONDecodeError, AttributeError):
# #         title  = request.POST.get('title', '').strip()
# #         author = request.POST.get('author', '').strip()

# #     if not title:
# #         return JsonResponse({'detail': 'title required'}, status=400)

# #     try:
# #         from apps.stories.models import BookRequest
# #         BookRequest.objects.create(
# #             title=title, author=author,
# #             requested_by=request.user if request.user.is_authenticated else None,
# #         )
# #     except Exception:
# #         pass  # graceful — don't crash the page

# #     return JsonResponse({'detail': 'Request received. Thank you!'})


# # # ── Newsletter / contact ───────────────────────────────────────────────────────

# # @require_POST
# # def newsletter_signup(request):
# #     try:
# #         data  = json.loads(request.body)
# #         email = data.get('email', '').strip()
# #     except Exception:
# #         email = request.POST.get('email', '').strip()

# #     if not email or '@' not in email:
# #         return JsonResponse({'detail': 'valid email required'}, status=400)

# #     # TODO: integrate with Mailchimp / SendGrid / etc.
# #     return JsonResponse({'detail': 'Subscribed!'})


# from django.shortcuts import render, redirect
# from django.http import HttpResponse, JsonResponse
# from django.views.decorators.http import require_POST, require_http_methods
# from django.views.decorators.csrf import csrf_exempt
# import json, os


# # ══════════════════════════════════════════════════════════════════════════════
# # HELPERS
# # ══════════════════════════════════════════════════════════════════════════════

# def _jwt_from_request(request):
#     """Read JWT from the nux_access cookie (set after login)."""
#     return request.COOKIES.get('nux_access', '')


# def _is_authenticated(request):
#     """Check if the request has a valid JWT cookie."""
#     return bool(_jwt_from_request(request))


# def _set_auth_cookies(response, access_token, refresh_token, username='', email='', role=''):
#     """Set JWT cookies on the response — secure, httponly, samesite."""
#     is_prod = os.environ.get('RENDER') == 'true'
#     opts = dict(httponly=True, samesite='Lax', secure=is_prod)
#     response.set_cookie('nux_access',   access_token,   max_age=3600,         **opts)
#     response.set_cookie('nux_refresh',  refresh_token,  max_age=60*60*24*30,  **opts)
#     response.set_cookie('nux_username', username,       max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod)
#     response.set_cookie('nux_email',    email,          max_age=60*60*24*30,
#                         samesite='Lax', secure=is_prod)
#     return response


# def _clear_auth_cookies(response):
#     for name in ('nux_access', 'nux_refresh', 'nux_username', 'nux_email'):
#         response.delete_cookie(name)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # PUBLIC PAGES
# # ══════════════════════════════════════════════════════════════════════════════

# def index(request):
#     context = {
#         'is_auth': _is_authenticated(request),
#         'username': request.COOKIES.get('nux_username', ''),
#     }
#     return render(request, 'novelux/index.html', context)

# def become_author(request):
#     return render(request, 'novelux/become_author.html')

# def faq(request):
#     return render(request, 'novelux/faq.html')

# def privacy(request):
#     return render(request, 'novelux/privacy.html')

# def terms(request):
#     return render(request, 'novelux/terms.html')

# def cookies_page(request):
#     return render(request, 'novelux/cookies.html')

# def content_guidelines(request):
#     return render(request, 'novelux/content_guidelines.html')


# # ══════════════════════════════════════════════════════════════════════════════
# # AUTH PAGES  (login / register / logout)
# # ══════════════════════════════════════════════════════════════════════════════

# def login_page(request):
#     """
#     GET  → show login form
#     The actual auth is done by the AJAX endpoint /auth/login-web/ below.
#     """
#     if _is_authenticated(request):
#         return redirect('novelux:dashboard')

#     next_url = request.GET.get('next', '/dashboard/')
#     return render(request, 'novelux/login.html', {
#         'next': next_url,
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# def register_page(request):
#     """Sign-up page (readers only — authors go through onboarding)."""
#     if _is_authenticated(request):
#         return redirect('novelux:index')
#     return render(request, 'novelux/register.html', {
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# def logout_view(request):
#     response = redirect('novelux:index')
#     _clear_auth_cookies(response)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # AJAX AUTH ENDPOINTS  (called by JS fetch — return JSON)
# # ══════════════════════════════════════════════════════════════════════════════

# @csrf_exempt
# @require_POST
# def ajax_login(request):
#     """
#     POST /auth/login-web/
#     Body: { email, password }
#     Hits the DRF JWT endpoint, sets httpOnly cookies, returns { ok, next }.
#     """
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     email    = body.get('email', '').strip()
#     password = body.get('password', '').strip()
#     next_url = body.get('next', '/dashboard/')

#     if not email or not password:
#         return JsonResponse({'error': 'Email and password are required'}, status=400)

#     # Hit the internal DRF login endpoint
#     base_url = _get_api_base(request)
#     try:
#         # r = http_requests.post(
#         #     f'{base_url}/api/auth/login/',
#         #     json={'email': email, 'password': password},
#         #     timeout=10
#         # )
#         r = http_requests.post(
#         f'{base_url}/api/auth/token/',
#         json={'email': email, 'password': password},
#         timeout=10
#         )
        
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Could not reach auth server: {e}'}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         err = data.get('detail') or data.get('error') or 'Invalid email or password'
#         return JsonResponse({'error': err}, status=401)

#     response = JsonResponse({'ok': True, 'next': next_url,
#                              'username': data.get('username', '')})
#     _set_auth_cookies(
#         response,
#         access_token=data['access'],
#         refresh_token=data.get('refresh', ''),
#         username=data.get('username', ''),
#         email=email,
#     )
#     return response


# @csrf_exempt
# @require_POST
# def ajax_register(request):
#     """
#     POST /auth/register-web/
#     Body: { username, email, password, role? }
#     """
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     base_url = _get_api_base(request)
#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/register/',
#             json={
#                 'username': body.get('username', '').strip(),
#                 'email':    body.get('email', '').strip(),
#                 'password': body.get('password', '').strip(),
#                 'role':     body.get('role', 'reader'),
#             },
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Server error: {e}'}, status=503)

#     if r.status_code not in (200, 201):
#         # Extract first readable error message from DRF response
#         err = _extract_drf_error(data)
#         return JsonResponse({'error': err}, status=400)

#     # Auto-login after register if tokens returned
#     response = JsonResponse({'ok': True, 'username': data.get('username', '')})
#     if 'access' in data:
#         _set_auth_cookies(
#             response,
#             access_token=data['access'],
#             refresh_token=data.get('refresh', ''),
#             username=data.get('username', ''),
#             email=body.get('email', ''),
#         )
#     return response


# @csrf_exempt
# @require_POST
# def ajax_google_auth(request):
#     """
#     POST /auth/google-web/
#     Body: { id_token, email, name, photo_url }
#     Verifies with Django backend, sets cookies.
#     """
#     import requests as http_requests

#     try:
#         body = json.loads(request.body)
#     except Exception:
#         return JsonResponse({'error': 'Invalid request body'}, status=400)

#     base_url = _get_api_base(request)
#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/google/',
#             json={
#                 'id_token':     body.get('id_token', ''),
#                 'email':        body.get('email', ''),
#                 'display_name': body.get('name', ''),
#                 'photo_url':    body.get('photo_url', ''),
#             },
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': f'Server error: {e}'}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         err = data.get('detail') or data.get('error') or 'Google sign-in failed'
#         return JsonResponse({'error': err}, status=401)

#     response = JsonResponse({'ok': True, 'username': data.get('username', ''),
#                              'is_new': data.get('is_new', False)})
#     _set_auth_cookies(
#         response,
#         access_token=data['access'],
#         refresh_token=data.get('refresh', ''),
#         username=data.get('username', ''),
#         email=data.get('email', body.get('email', '')),
#     )
#     return response


# @csrf_exempt
# @require_POST
# def ajax_refresh_token(request):
#     """
#     POST /auth/refresh-web/
#     Silently refresh the access token using the refresh cookie.
#     """
#     import requests as http_requests

#     refresh_token = request.COOKIES.get('nux_refresh', '')
#     if not refresh_token:
#         return JsonResponse({'error': 'No refresh token'}, status=401)

#     base_url = _get_api_base(request)
#     try:
#         r = http_requests.post(
#             f'{base_url}/api/auth/token/refresh/',
#             json={'refresh': refresh_token},
#             timeout=10
#         )
#         data = r.json()
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=503)

#     if r.status_code != 200 or 'access' not in data:
#         response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
#         _clear_auth_cookies(response)
#         return response

#     response = JsonResponse({'ok': True})
#     is_prod = os.environ.get('RENDER') == 'true'
#     response.set_cookie('nux_access', data['access'], max_age=3600,
#                         httponly=True, samesite='Lax', secure=is_prod)
#     return response


# # ══════════════════════════════════════════════════════════════════════════════
# # AUTHOR DASHBOARD  (JWT-cookie-gated, NOT Django session)
# # ══════════════════════════════════════════════════════════════════════════════

# def author_dashboard(request):
#     """
#     Serve the dashboard if the user has a valid nux_access cookie.
#     The cookie is httpOnly so JS can't read it — we inject the token
#     into a <meta> tag so the page JS can pick it up for API calls.
#     """
#     if not _is_authenticated(request):
#         return redirect(f'/login/?next=/dashboard/')

#     return render(request, 'novelux/author_dashboard.html', {
#         'access_token': _jwt_from_request(request),
#         'username':     request.COOKIES.get('nux_username', 'Author'),
#         'email':        request.COOKIES.get('nux_email', ''),
#         'api_base':     '/api',
#     })


# def author_onboarding(request):
#     """
#     Multi-step author onboarding.
#     If already logged in we pre-fill user info.
#     """
#     return render(request, 'novelux/author_onboarding.html', {
#         'is_auth':      _is_authenticated(request),
#         'username':     request.COOKIES.get('nux_username', ''),
#         'email':        request.COOKIES.get('nux_email', ''),
#         'access_token': _jwt_from_request(request),
#         'api_base':     '/api',
#         'GOOGLE_CLIENT_ID': os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
#     })


# # ══════════════════════════════════════════════════════════════════════════════
# # APK DOWNLOAD
# # ══════════════════════════════════════════════════════════════════════════════

# def download_apk(request):
#     apk_path = os.environ.get('NOVELUX_APK_PATH', '')
#     if apk_path and os.path.exists(apk_path):
#         with open(apk_path, 'rb') as f:
#             response = HttpResponse(f.read(),
#                 content_type='application/vnd.android.package-archive')
#             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
#             return response
#     return JsonResponse({'detail': 'APK not yet available'}, status=404)


# # ══════════════════════════════════════════════════════════════════════════════
# # MISC AJAX
# # ══════════════════════════════════════════════════════════════════════════════

# @csrf_exempt
# @require_POST
# def book_request_web(request):
#     try:
#         data = json.loads(request.body)
#     except Exception:
#         data = {}
#     title  = data.get('title', '').strip()
#     author = data.get('author', '').strip()
#     if not title:
#         return JsonResponse({'error': 'title required'}, status=400)
#     try:
#         from apps.stories.models import BookRequest
#         BookRequest.objects.create(title=title, author=author)
#     except Exception:
#         pass
#     return JsonResponse({'detail': 'Request received!'})


# @csrf_exempt
# @require_POST
# def newsletter_signup(request):
#     try:
#         data = json.loads(request.body)
#         email = data.get('email', '').strip()
#     except Exception:
#         email = ''
#     if not email or '@' not in email:
#         return JsonResponse({'error': 'valid email required'}, status=400)
#     return JsonResponse({'detail': 'Subscribed!'})


# # ══════════════════════════════════════════════════════════════════════════════
# # INTERNAL HELPERS
# # ══════════════════════════════════════════════════════════════════════════════

# def _get_api_base(request):
#     """
#     When calling Django's own DRF endpoints from a view we use localhost,
#     not the public Render URL, to avoid the round-trip.
#     On Render PORT is 10000 by default.
#     """
#     port = os.environ.get('PORT', '8000')
#     return f'http://127.0.0.1:{port}'


# def _extract_drf_error(data):
#     """Pull the first readable error message from a DRF error dict."""
#     if isinstance(data, str):
#         return data
#     if isinstance(data, dict):
#         for key in ('detail', 'error', 'non_field_errors',
#                     'email', 'username', 'password'):
#             val = data.get(key)
#             if val:
#                 if isinstance(val, list):
#                     return str(val[0])
#                 return str(val)
#         # Fallback — first value
#         first = next(iter(data.values()), None)
#         if first:
#             return str(first[0] if isinstance(first, list) else first)
#     return 'Something went wrong. Please try again.'


from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json, os
from rest_framework.response import Response
from apps.users.models import AuthorProfile


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _jwt_from_request(request):
    """Read JWT from the nux_access cookie (set after login)."""
    return request.COOKIES.get('nux_access', '')


def _is_authenticated(request):
    """Check if the request has a valid JWT cookie."""
    return bool(_jwt_from_request(request))


def _set_auth_cookies(response, access_token, refresh_token, username='', email='', role=''):
    """Set JWT cookies on the response — secure, httponly, samesite."""
    is_prod = os.environ.get('RENDER') == 'true'
    opts = dict(httponly=True, samesite='Lax', secure=is_prod)
    response.set_cookie('nux_access',   access_token,   max_age=3600,         **opts)
    response.set_cookie('nux_refresh',  refresh_token,  max_age=60*60*24*30,  **opts)
    response.set_cookie('nux_username', username,       max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod)
    response.set_cookie('nux_email',    email,          max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod)
    # Role cookie (not httponly — JS reads it to gate dashboard navigation)
    response.set_cookie('nux_role',     role,           max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod, httponly=False)
    return response


def _clear_auth_cookies(response):
    for name in ('nux_access', 'nux_refresh', 'nux_username', 'nux_email', 'nux_role'):
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

def copyright_policy(request):
    return render(request, 'novelux/copyright_policy.html')


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

    from django.conf import settings as _s
    next_url = request.GET.get('next', '/dashboard/')
    return render(request, 'novelux/login.html', {
        'next': next_url,
        'GOOGLE_CLIENT_ID': getattr(_s, 'GOOGLE_WEB_CLIENT_ID', '') or os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
    })


def register_page(request):
    """Sign-up page — also handles author onboarding via SE editor code."""
    if _is_authenticated(request):
        return redirect('novelux:index')
    from django.conf import settings as _s
    editor_code = request.GET.get('editor_code', '').strip().upper()
    return render(request, 'novelux/register.html', {
        'GOOGLE_CLIENT_ID': getattr(_s, 'GOOGLE_WEB_CLIENT_ID', '') or os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
        'editor_code': editor_code,
    })


def logout_view(request):
    response = redirect('novelux:index')
    _clear_auth_cookies(response)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# AJAX AUTH ENDPOINTS  (called by JS fetch — return JSON)
# ══════════════════════════════════════════════════════════════════════════════
"""
@csrf_exempt
@require_POST
def ajax_login(request):
    
    POST /auth/login-web/
    Body: { email, password }
    Hits the DRF JWT endpoint, sets httpOnly cookies, returns { ok, next }.
    
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

"""

# ══════════════════════════════════════════════════════════════════════════════
# MINIMAL FIX — only replace ajax_login and ajax_refresh_token
# Leave ajax_register and ajax_google_auth exactly as they are.
# ══════════════════════════════════════════════════════════════════════════════

# Add these imports at the top of novelux_web/views.py if not already there:
#   from django.contrib.auth import authenticate
#   from rest_framework_simplejwt.tokens import RefreshToken


@csrf_exempt
@require_POST
def ajax_login(request):
    """
    POST /auth/login-web/
    Authenticates directly via Django — no internal HTTP call.
    """
    from django.contrib.auth import authenticate
    from rest_framework_simplejwt.tokens import RefreshToken

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    email    = body.get('email', '').strip()
    password = body.get('password', '').strip()
    next_url = body.get('next', '/dashboard/')

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required'}, status=400)

    # Try authenticating with email as username first
    user = authenticate(request, username=email, password=password)

    # If that fails, look up the actual username by email
    if user is None:
        try:
            from apps.users.models import User
            u = User.objects.get(email__iexact=email)
            user = authenticate(request, username=u.username, password=password)
        except Exception:
            user = None

    if user is None or not user.is_active:
        return JsonResponse({'error': 'Invalid email or password'}, status=401)

    # Mint JWT tokens — embed role in payload for dashboard gating
    from apps.editorial.models import AuthorEditorLink
    refresh      = RefreshToken.for_user(user)
    access_token = refresh.access_token
    access_token['role']     = user.role
    access_token['username'] = user.username

    EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
    if user.role in EDITOR_ROUTES:
        next_url = EDITOR_ROUTES[user.role]
    elif user.role == 'author' and next_url in ('', '/dashboard/', '/'):
        next_url = '/dashboard/'

    response = JsonResponse({
        'ok': True, 'next': next_url,
        'username': user.username, 'role': user.role,
    })
    _set_auth_cookies(
        response,
        access_token  = str(access_token),
        refresh_token = str(refresh),
        username      = user.username,
        email         = user.email,
        role          = user.role,
    )
    return response


@csrf_exempt
@require_POST
def ajax_refresh_token(request):
    """
    POST /auth/refresh-web/
    Refreshes access token directly via SimpleJWT — no internal HTTP call.
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.exceptions import TokenError

    refresh_token = request.COOKIES.get('nux_refresh', '')
    if not refresh_token:
        return JsonResponse({'error': 'No refresh token'}, status=401)

    try:
        refresh    = RefreshToken(refresh_token)
        new_access = str(refresh.access_token)
    except TokenError:
        response = JsonResponse({'error': 'Session expired, please log in again'}, status=401)
        _clear_auth_cookies(response)
        return response

    is_prod = os.environ.get('RENDER') == 'true'
    response = JsonResponse({'ok': True})
    response.set_cookie('nux_access', new_access, max_age=3600,
                        httponly=True, samesite='Lax', secure=is_prod)
    return response


# ══════════════════════════════════════════════════════════════════════════════
# Replace ajax_register in novelux_web/views.py
# ══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_POST
def ajax_register(request):
    """
    POST /auth/register-web/
    Creates a user directly via Django ORM — no internal HTTP call.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    username    = body.get('username', '').strip()
    email       = body.get('email', '').strip()
    password    = body.get('password1', '').strip()
    role        = body.get('role', 'reader')
    editor_code = body.get('editor_code', '').strip().upper()

    # ── Validate ──────────────────────────────────────────────────────────
    if not username:
        return JsonResponse({'error': 'Username is required'}, status=400)
    if not email:
        return JsonResponse({'error': 'Email is required'}, status=400)
    if not password:
        return JsonResponse({'error': 'Password is required'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)

    # ── Check uniqueness ──────────────────────────────────────────────────
    from apps.users.models import User

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'error': 'Username already taken'}, status=400)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'An account with this email already exists'}, status=400)

    # Pre-validate editor code before creating the account
    if editor_code:
        if not User.objects.filter(editor_code=editor_code, role='se').exists():
            return JsonResponse(
                {'error': 'Invalid editor code. Double-check the code with your editor.'},
                status=400,
            )

    # ── Create user ───────────────────────────────────────────────────────
    try:
        user = User.objects.create_user(
            username = username,
            email    = email,
            password = password,
        )
        if hasattr(user, 'role') and role:
            user.role = role
            user.save(update_fields=['role'])
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # ── Link to SE if an editor code was provided ─────────────────────────
    if editor_code and user.role == 'author':
        from apps.editorial.models import AuthorEditorLink
        AuthorEditorLink.link_by_code(user, editor_code)

    # ── Auto-login: mint JWT tokens directly ──────────────────────────────
    refresh = RefreshToken.for_user(user)
    access  = str(refresh.access_token)

    if user.role == 'author':
        next_url = '/author/kyc/'
    else:
        next_url = '/'
    response = JsonResponse({'ok': True, 'username': user.username, 'next': next_url})
    _set_auth_cookies(
        response,
        access_token  = access,
        refresh_token = str(refresh),
        username      = user.username,
        email         = user.email,
    )
    return response

"""
@csrf_exempt
@require_POST
def ajax_register(request):
    import requests as http_requests

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    base_url = _get_api_base(request)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    email = body.get('email', '').strip()  # ✅ fixed
    user = User.objects.filter(email=email).first()
        
    if user:
        user.role = User.ROLE_AUTHOR
        user.save()
        AuthorProfile.objects.get_or_create(user=user)  # ✅ creates if missing
        return JsonResponse({'detail': 'You are now an author!'}, status=200)
    
    editor_code = body.get('editor_code', '').strip().upper()

    # Pre-validate editor code before hitting the registration API
    if editor_code:
        from django.contrib.auth import get_user_model as _gum
        _User = _gum()
        if not _User.objects.filter(editor_code=editor_code, role='se').exists():
            return JsonResponse(
                {'error': 'Invalid editor code. Double-check the code with your editor.'},
                status=400,
            )

    try:
        r = http_requests.post(
            f'{base_url}/api/auth/dj/registration/',
            json={
                'username':    body.get('username', 'N/A').strip(),
                'email':       body.get('email', 'N/A').strip(),
                'password1':   body.get('password1', 'N/A').strip(),
                'password2':   body.get('password2', 'N/A').strip(),
                'role':        body.get('role', 'reader'),
                'editor_code': editor_code,
            },
            timeout=10
        )
        data = r.json()
    except Exception as e:
        return JsonResponse({'error': f'Server error: {e}'}, status=503)

    if r.status_code not in (200, 201):
        err = _extract_drf_error(data)
        return JsonResponse({'error': err}, status=400)

    # Determine redirect based on role
    role = body.get('role', 'reader')
    EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
    next_url = EDITOR_ROUTES.get(role, '/dashboard/')

    response = JsonResponse({
        'ok':       True,
        'username': data.get('username', ''),
        'role':     role,
        'next':     next_url,
    })
    if 'access' in data:
        _set_auth_cookies(
            response,
            access_token=data['access'],
            refresh_token=data.get('refresh', ''),
            username=data.get('username', ''),
            email=body.get('email', ''),
            role=role,
        )
    return response
"""

@csrf_exempt
@require_POST
def ajax_google_auth(request):
    """
    POST /auth/google-web/
    Body: { id_token, access_token, email, name, photo_url }
    Verifies with Google directly — no internal HTTP round-trip.
    """
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    id_token_str = body.get('id_token', '').strip()
    access_token = body.get('access_token', '').strip()
    email        = body.get('email', '').strip().lower()
    name         = body.get('name', '') or body.get('display_name', '')
    photo_url    = body.get('photo_url', '')

    if not id_token_str and not access_token:
        return JsonResponse({'error': 'Google token is required'}, status=400)

    # Verify with Google
    if id_token_str:
        try:
            from google.oauth2 import id_token as _gid
            from google.auth.transport import requests as _greq
            idinfo = _gid.verify_oauth2_token(id_token_str, _greq.Request(), audience=None)
        except ValueError as e:
            return JsonResponse({'error': f'Invalid Google token: {e}'}, status=401)
    else:
        import requests as _req
        try:
            r = _req.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5,
            )
            if r.status_code != 200:
                return JsonResponse({'error': 'Invalid Google access token'}, status=401)
            idinfo = r.json()
        except Exception as e:
            return JsonResponse({'error': f'Google verification failed: {e}'}, status=503)

    google_email = (idinfo.get('email') or email).lower()
    google_name  = idinfo.get('name') or name
    google_photo = idinfo.get('picture') or photo_url

    if not google_email:
        return JsonResponse({'error': 'Could not determine email from Google account'}, status=400)

    from django.contrib.auth import get_user_model as _gum
    from rest_framework_simplejwt.tokens import RefreshToken

    _User = _gum()

    def _make_uname(display, addr):
        base = (display or addr.split('@')[0]).lower().replace(' ', '_')[:20]
        uname = base
        i = 1
        while _User.objects.filter(username=uname).exists():
            uname = f'{base}_{i}'
            i += 1
        return uname

    user, created = _User.objects.get_or_create(
        email=google_email,
        defaults={
            'username':   _make_uname(google_name, google_email),
            'first_name': google_name.split()[0] if google_name else '',
            'last_name':  ' '.join(google_name.split()[1:]) if google_name else '',
        }
    )
    if created:
        user.set_unusable_password()
        user.save()
        if hasattr(user, 'avatar') and google_photo:
            user.avatar = google_photo
            user.save(update_fields=['avatar'])

    refresh    = RefreshToken.for_user(user)
    access_tok = refresh.access_token
    role       = getattr(user, 'role', 'reader') or 'reader'
    access_tok['role']     = role
    access_tok['username'] = user.username

    EDITOR_ROUTES = {'se': '/editorial/se/', 'ce': '/editorial/ce/'}
    next_url = EDITOR_ROUTES.get(role, '/dashboard/')

    response = JsonResponse({
        'ok':      True,
        'username': user.username,
        'is_new':  created,
        'next':    next_url,
        'role':    role,
    })
    _set_auth_cookies(
        response,
        access_token  = str(access_tok),
        refresh_token = str(refresh),
        username      = user.username,
        email         = user.email,
        role          = role,
    )
    return response

"""
@csrf_exempt
@require_POST
def ajax_refresh_token(request):
    
    POST /auth/refresh-web/
    Silently refresh the access token using the refresh cookie.
    
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

    # Re-decode role from the new access token
    _refresh_role = request.COOKIES.get('nux_role', 'reader')
    try:
        from rest_framework_simplejwt.tokens import AccessToken as _AT2
        _refresh_role = _AT2(data['access']).payload.get('role', _refresh_role)
    except Exception:
        pass
    response = JsonResponse({'ok': True, 'role': _refresh_role})
    is_prod = os.environ.get('RENDER') == 'true'
    response.set_cookie('nux_access', data['access'], max_age=3600,
                        httponly=True, samesite='Lax', secure=is_prod)
    response.set_cookie('nux_role', _refresh_role, max_age=60*60*24*30,
                        samesite='Lax', secure=is_prod, httponly=False)
    return response

"""
def author_dashboard(request):
    """
    Serve the dashboard if the user has a valid nux_access cookie.
    Pulls real data from the DB and injects it into the template context
    so the page renders correctly server-side without extra API round-trips.
    """
    if not _is_authenticated(request):
        return redirect(f'/login/?next=/dashboard/')

    # ── Resolve the author from the JWT stored in the cookie ─────────────────
    from apps.users.models import User, AuthorProfile, AuthorKYC
    from apps.stories.models import Story
    from apps.chapters.models import Chapter
    from apps.tips.models import Tip
    from apps.coins.models import AuthorPayout
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    import datetime, json

    username = request.COOKIES.get('nux_username', '')
    try:
        user = User.objects.select_related('author_profile').get(username=username)
    except User.DoesNotExist:
        # Fall back gracefully — render with empty data
        user = None

    # ── Story queryset for this author ────────────────────────────────────────
    stories_qs = (
        Story.objects
        .filter(author=user)
        .prefetch_related('chapters')
        .order_by('-created_at')
        if user else Story.objects.none()
    )

    stories_list = list(
        stories_qs.values(
            'id', 'title', 'slug', 'status',
            'total_views', 'total_chapters', 'word_count',
            'total_tips', 'average_rating', 'total_ratings',
            'total_comments', 'created_at',
            'contract_status', 'contract_eligible',
        )
    )

    # Attach SE/CE editorial note for rejected stories
    from apps.editorial.models import ContractApplication
    story_ids = [s['id'] for s in stories_list]
    notes_map = {
        ca['story_id']: ca['se_note']
        for ca in ContractApplication.objects.filter(
            story_id__in=story_ids,
            status=ContractApplication.STATUS_REJECTED,
        ).values('story_id', 'se_note')
    }
    for s in stories_list:
        s['editorial_note'] = notes_map.get(s['id'], '') or ''

    # Human-friendly numbers for the template
    def fmt(n):
        if n >= 1_000_000:
            return f'{n/1_000_000:.1f}M'
        if n >= 1_000:
            return f'{n/1_000:.1f}K'
        return str(n)

    for s in stories_list:
        s['reads_fmt']    = fmt(s['total_views'])
        s['words_fmt']    = f"{s['word_count']:,}"
        s['badge_class']  = {
            'published': 'badge-green',
            'ongoing':   'badge-green',
            'draft':     'badge-yellow',
            'paused':    'badge-yellow',
            'completed': 'badge-primary',
        }.get(s['status'], 'badge-gray')
        # Show "Apply for Contract" when threshold hit but not yet applied
        s['can_apply_contract'] = (
            s.get('contract_eligible', False) and
            s.get('contract_status', 'none') == 'none'
        )

    # ── Aggregate stats ───────────────────────────────────────────────────────
    totals = stories_qs.aggregate(
        total_reads    = Sum('total_views'),
        total_chapters = Sum('total_chapters'),
        total_words    = Sum('word_count'),
        total_comments = Sum('total_comments'),
        story_count    = Count('id'),
    )

    total_reads    = totals['total_reads']    or 0
    total_chapters = totals['total_chapters'] or 0
    total_comments = totals['total_comments'] or 0
    story_count    = totals['story_count']    or 0

    published_count = stories_qs.filter(status__in=['published', 'ongoing', 'completed']).count()
    draft_count     = stories_qs.filter(status__in=['draft', 'paused']).count()

    # Follower count
    followers_count = 0
    if user:
        try:
            followers_count = user.followers.count()
        except Exception:
            pass

    # ── Earnings / Author profile ─────────────────────────────────────────────
    total_earnings   = 0.0
    pending_payout   = 0.0
    contract_type    = ''
    is_verified      = False

    if user:
        try:
            ap = user.author_profile
            total_earnings = float(ap.total_earnings)
            pending_payout = float(ap.pending_payout)
            contract_type  = ap.contract_type
            is_verified    = ap.is_verified
        except Exception:
            pass

    # Tips received by this author
    tips_received_coins = 0
    if user:
        try:
            tips_received_coins = (
                Tip.objects.filter(recipient=user)
                .aggregate(total=Sum('coins_amount'))['total'] or 0
            )
        except Exception:
            pass

    # Payout history (latest 5)
    payouts = []
    if user:
        try:
            payouts = list(
                AuthorPayout.objects
                .filter(author=user)
                .order_by('-requested_at')[:5]
                .values('amount_usd', 'status', 'payout_method', 'requested_at')
            )
            for p in payouts:
                p['requested_at_fmt'] = p['requested_at'].strftime('%b %-d, %Y')
                p['badge_class'] = {
                    'processed': 'badge-green',
                    'pending':   'badge-yellow',
                    'failed':    'badge-red',
                }.get(p['status'], 'badge-gray')
        except Exception:
            payouts = []

    # ── Chapters for the most-read story (for the Chapters page) ─────────────
    chapters_list = []
    featured_story_title = ''
    if stories_list:
        top_story_id = max(stories_list, key=lambda s: s['total_views'])['id']
        featured_story_title = next(s['title'] for s in stories_list if s['id'] == top_story_id)
        chapters_list = list(
            Chapter.objects
            .filter(story_id=top_story_id)
            .order_by('chapter_number')
            .values('chapter_number', 'title', 'word_count', 'is_published', 'views', 'unlocks')
        )
        for ch in chapters_list:
            ch['words_fmt'] = f"{ch['word_count']:,}"
            ch['reads_fmt'] = fmt(ch['views'])
            ch['status']    = 'published' if ch['is_published'] else 'draft'
            ch['badge_class'] = 'badge-green' if ch['is_published'] else 'badge-yellow'

    # ── Weekly reads chart (last 7 days, sum of views is denormalized,
    #    so we approximate from ReadingHistory if available) ──────────────────
    weekly_reads  = [0] * 7
    weekly_labels = []
    today = timezone.now().date()
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        weekly_labels.append(d.strftime('%a'))
    # We don't have a daily_views table, so pass the placeholder zeros —
    # the JS will render the chart; replace with real data if you add a DailyView model.

    # ── Analytics: per-story table data ──────────────────────────────────────
    analytics_rows = []
    for s in stories_list[:10]:
        analytics_rows.append({
            'title':    s['title'],
            'status':   s['status'],
            'reads':    s['reads_fmt'],
            'chapters': s['total_chapters'],
            'rating':   float(s['average_rating']),
            'comments': s['total_comments'],
        })

    # ── User profile data ─────────────────────────────────────────────────────
    display_name = ''
    bio          = ''
    avatar   = ''
    if user:
        display_name = f"{user.first_name} {user.last_name}".strip() or user.username
        bio          = user.bio
        if user.avatar:
            try:
                avatar = user.avatar.url
            except Exception:
                pass

    # ── Greeting ──────────────────────────────────────────────────────────────
    hour = timezone.localtime(timezone.now()).hour
    if hour < 12:
        greeting_time = 'morning'
    elif hour < 17:
        greeting_time = 'afternoon'
    else:
        greeting_time = 'evening'

    # ── KYC (single query) ────────────────────────────────────────────────────
    _kyc = AuthorKYC.objects.filter(user=user).first() if user else None

    context = {
        # Auth
        'access_token':  _jwt_from_request(request),
        'username':      username,
        'email':         request.COOKIES.get('nux_email', ''),
        'api_base':      '/api',

        # Greeting
        'greeting_time':  greeting_time,
        'display_name':   display_name or username,

        # Overview stats
        'total_reads':     fmt(total_reads),
        'followers_count': fmt(followers_count),
        'story_count':     story_count,
        'published_count': published_count,
        'draft_count':     draft_count,
        'total_chapters':  total_chapters,
        'total_comments':  fmt(total_comments),
        'tips_coins':      tips_received_coins,

        # Stories
        'stories':         stories_list,
        'stories_json':    json.dumps(stories_list, default=str),

        # Chapters (top story)
        'chapters':              chapters_list,
        'chapters_json':         json.dumps(chapters_list, default=str),
        'featured_story_title':  featured_story_title,

        # Earnings
        'total_earnings':   f'{total_earnings:,.2f}',
        'pending_payout':   f'{pending_payout:,.2f}',
        'contract_type':    contract_type,
        'is_verified':      is_verified,
        'payouts':          payouts,

        # Analytics
        'analytics_rows':   analytics_rows,
        'analytics_json':   json.dumps(analytics_rows),

        # Chart data
        'weekly_labels_json': json.dumps(weekly_labels),
        'weekly_reads_json':  json.dumps(weekly_reads),

        # Profile
        'bio':        bio,
        'avatar': avatar,

        # KYC (single query reused for both keys)
        'kyc': _kyc,
        'kyc_status': _kyc.status if _kyc else None,
    }

    return render(request, 'novelux/author_dashboard.html', context)

def author_onboarding(request):
    """
    Multi-step author onboarding.
    If already logged in we pre-fill user info.
    """
    from django.conf import settings as _s
    return render(request, 'novelux/author_onboarding.html', {
        'is_auth':      _is_authenticated(request),
        'username':     request.COOKIES.get('nux_username', ''),
        'email':        request.COOKIES.get('nux_email', ''),
        'access_token': _jwt_from_request(request),
        'api_base':     '/api',
        'GOOGLE_CLIENT_ID': getattr(_s, 'GOOGLE_WEB_CLIENT_ID', '') or os.environ.get('GOOGLE_WEB_CLIENT_ID', ''),
    })


# ══════════════════════════════════════════════════════════════════════════════
# APK DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

# def download_apk(request):
#     apk_path = os.environ.get('NOVELUX_APK_PATH', '')
#     if apk_path and os.path.exists(apk_path):
#         with open(apk_path, 'rb') as f:
#             response = HttpResponse(f.read(),
#                 content_type='application/vnd.android.package-archive')
#             response['Content-Disposition'] = 'attachment; filename="novelux.apk"'
#             return response
#     return JsonResponse({'detail': 'APK not yet available'}, status=404)


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
    Returns the API base URL for use in dashboard templates (injected as
    the nux-api meta tag so JS fetch calls can reach DRF endpoints).

    Always returns a path-only '/api' so it works on any host — local dev,
    Render, or any other deployment — without hardcoding a domain.
    """
    return '/api'


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


def download_apk(request):
    # \"\"\"
    # GET  /download/apk/          → shows the download page
    # GET  /download/apk/?dl=1     → streams the APK file directly
    # \"\"\"
    from novelux_web.models import APKRelease
    from django.http import FileResponse, Http404
 
    release = APKRelease.get_latest()
 
    # Direct download triggered by ?dl=1 (the Download button hits this)
    if request.GET.get('dl') == '1':
        if not release or not release.apk_file:
            raise Http404('APK not available yet.')
        # Increment download counter
        from django.db import models
        APKRelease.objects.filter(pk=release.pk).update(
            download_count=models.F('download_count') + 1
        )
        try:
            response = FileResponse(
                release.apk_file.open('rb'),
                content_type='application/vnd.android.package-archive',
                as_attachment=True,
                filename=f'novelux-v{release.version_name}.apk',
            )
            return response
        except Exception:
            raise Http404('APK file could not be read.')
 
    # Default: show the download landing page
    return render(request, 'novelux/download.html', {'release': release})


# ═══════════════════════════════════════════════════════════════════════════════
#  EDITOR DASHBOARD VIEWS  (AE / SE / CE)
# ═══════════════════════════════════════════════════════════════════════════════

def _editor_required(roles):
    """Inline decorator: redirect to login unless user has one of the given roles."""
    from functools import wraps
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not _is_authenticated(request):
                return redirect(f'/login/?next={request.path}')
            role = request.COOKIES.get('nux_role', '')
            if role not in roles:
                # Try to get fresh role from access token payload
                from rest_framework_simplejwt.tokens import AccessToken as AT
                token_str = _jwt_from_request(request)
                try:
                    tok   = AT(token_str)
                    role  = tok.payload.get('role', '')
                except Exception:
                    role  = ''
            if role not in roles:
                return redirect('/login/?error=access_denied')
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator


def _editorial_context(request):
    """
    Build the template context for all editor dashboards.
    
    NOTE: The ChapterReview model has been removed. Editorial state now lives
    directly on Chapter.status. This function returns a minimal context to prevent
    import errors. The editor dashboards are transitioning to use the modern
    editorial API (apps.editorial.views) instead of these legacy web views.
    """
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    User    = get_user_model()
    token   = _jwt_from_request(request)
    api_url = _get_api_base(request)

    # Resolve user from JWT
    user = None
    try:
        from rest_framework_simplejwt.tokens import AccessToken as AT
        tok     = AT(token)
        user_id = tok.payload.get('user_id')
        if user_id:
            user = User.objects.get(pk=user_id)
    except Exception:
        pass

    ctx = {
        'api_url':     api_url,
        'access_token': token,
        'editor':      user,
        'role':        user.role if user else '',
    }

    if user and user.role == 'se' and not user.editor_code:
        user.generate_editor_code()

    if not user:
        return ctx

    role = user.role

    # TODO: Refactor these dashboard views to use the modern editorial API
    # and the new Chapter-based workflow instead of the legacy ChapterReview model.
    
    if role == 'se':
        from django.contrib.auth import get_user_model as _gum
        from django.db.models import Count as _Count
        from apps.chapters.models import Chapter
        from datetime import timedelta
        from apps.stories.models import Story
        from apps.editorial.models import ContractApplication

        _User = _gum()

        # Stories awaiting SE review (threshold hit, contract_status=under_review,
        # and the ContractApplication is assigned to this SE)
        review_stories = Story.objects.filter(
            contract_status='under_review',
            author__editor_link__assigned_se=user,
        ).select_related('author').prefetch_related(
            'chapters'
        ).order_by('-updated_at')[:50]

        # Annotate each story with its chapter list, contract application and KYC
        from apps.users.models import AuthorKYC as _AuthorKYC
        for s in review_stories:
            s.chapters_list = list(
                s.chapters.order_by('chapter_number')
                .values('id','chapter_number','title','status','word_count','created_at')
            )
            try:
                s.contract_app = s.contract_application
            except ContractApplication.DoesNotExist:
                s.contract_app = None
            try:
                s.author_kyc = _AuthorKYC.objects.get(user=s.author)
            except _AuthorKYC.DoesNotExist:
                s.author_kyc = None

        # Stories already SE-approved (passed to CE) — includes awaiting_signature
        approved_stories = Story.objects.filter(
            contract_status__in=['contract_sent', 'awaiting_signature', 'signed'],
            author__editor_link__assigned_se=user,
        ).select_related('author').prefetch_related('contract_application').order_by('-updated_at')[:20]

        # Stories CE-rejected (contract_status reverts to 'none', so query via ContractApplication)
        ce_rejected_apps = ContractApplication.objects.filter(
            assigned_se=user,
            status=ContractApplication.STATUS_REJECTED,
        ).select_related('story', 'story__author').order_by('-rejected_at')[:20]

        one_week_ago = timezone.now() - timedelta(days=7)
        cleared_this_week = ContractApplication.objects.filter(
            assigned_se=user,
            status__in=['se_approved','contract_sent','signed'],
            se_reviewed_at__gte=one_week_ago,
        ).count()

        ctx.update({
            'pending_count':       review_stories.count(),
            'review_stories':      review_stories,
            'approved_stories':    approved_stories,
            'ce_rejected_apps':    ce_rejected_apps,
            'cleared_this_week':   cleared_this_week,
            'policy_actions_month': 0,
            'recent_se_decisions': approved_stories,
            'flagged_items': [],
            'supervisor_ce': (
                user.editorial_assignment.supervisor
                if hasattr(user, 'editorial_assignment') and
                   user.editorial_assignment.supervisor else None
            ),
            'author_overview': _User.objects.filter(
                role='author',
                editor_link__assigned_se=user,
            ).order_by('username')[:50],
        })

    elif role == 'ce':
        from django.contrib.auth import get_user_model as _gum
        from apps.editorial.models import EditorialPolicy, ContractApplication
        from apps.stories.models import Story

        _User = _gum()

        se_qs = _User.objects.filter(
            role='se', editorial_assignment__supervisor=user,
        )
        # Fall back to all SEs on the platform (covers invites sent before
        # the supervisor-auto-assign fix)
        if not se_qs.exists():
            se_qs = _User.objects.filter(role='se')

        # Stories SE-approved and waiting for CE action (send contract)
        pending_stories = Story.objects.filter(
            contract_status='contract_sent',
            author__editor_link__assigned_se__editorial_assignment__supervisor=user,
        ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        # Fallback: also catch stories approved by any SE (no CE assignment yet)
        if not pending_stories.exists():
            pending_stories = Story.objects.filter(
                contract_status='contract_sent',
            ).select_related('author').prefetch_related('chapters').order_by('-updated_at')

        from apps.users.models import AuthorKYC as _AuthorKYC
        for s in pending_stories:
            s.chapters_list = list(
                s.chapters.order_by('chapter_number')
                .values('id', 'chapter_number', 'title', 'status', 'word_count', 'created_at')
            )
            try:
                s.contract_app = s.contract_application
            except ContractApplication.DoesNotExist:
                s.contract_app = None
            try:
                s.author_kyc = _AuthorKYC.objects.get(user=s.author)
            except _AuthorKYC.DoesNotExist:
                s.author_kyc = None

        signed_stories = Story.objects.filter(
            contract_status='signed',
        ).select_related('author').order_by('-updated_at')[:20]

        # Stories in awaiting_signature state — CE has sent contract, waiting for author
        awaiting_sign_stories = Story.objects.filter(
            contract_status='awaiting_signature',
        ).select_related('author').prefetch_related('contract_application').order_by('-updated_at')[:50]
        for s in awaiting_sign_stories:
            try:
                s.contract_app = s.contract_application
            except ContractApplication.DoesNotExist:
                s.contract_app = None

        # Authors with no SE assignment — CE can assign them
        unassigned_authors = _User.objects.filter(
            role='author',
        ).exclude(editor_link__isnull=False).order_by('username')[:100]

        # KYC submissions
        from apps.users.models import AuthorKYC
        kyc_pending = AuthorKYC.objects.filter(
            status=AuthorKYC.STATUS_PENDING,
        ).select_related('user').order_by('submitted_at')
        kyc_all = AuthorKYC.objects.select_related('user').order_by('-submitted_at')[:100]
        kyc_pending_count = kyc_pending.count()

        # Dynamic stats
        from django.db.models import Sum as _Sum
        approved_books_qs = Story.objects.filter(contract_status='signed')
        approved_books_count = approved_books_qs.count()
        approved_books_chapters = approved_books_qs.aggregate(
            total=_Sum('total_chapters')
        )['total'] or 0
        awaiting_sign_count = Story.objects.filter(contract_status='awaiting_signature').count()

        ctx.update({
            'pending_stories':          pending_stories,
            'pending_stories_count':    pending_stories.count(),
            'signed_stories':           signed_stories,
            'awaiting_sign_stories':    awaiting_sign_stories,
            'awaiting_sign_count':      awaiting_sign_count,
            'unassigned_authors':       unassigned_authors,
            'kyc_pending':              kyc_pending,
            'kyc_all':                  kyc_all,
            'kyc_pending_count':        kyc_pending_count,
            'my_ses':                   se_qs,
            'se_count':                 se_qs.count(),
            'se_team':                  se_qs,
            'approved_books_count':     approved_books_count,
            'approved_books_chapters':  approved_books_chapters,
            'pending_policies_count':   EditorialPolicy.objects.filter(status='under_review').count(),
            'policies_pending':         EditorialPolicy.objects.filter(
                status='under_review',
            ).select_related('proposed_by').order_by('-created_at'),
            'active_policies':          EditorialPolicy.objects.filter(
                status='active',
            ).select_related('proposed_by', 'approved_by').order_by('-published_at'),
            'all_editors':              _User.objects.filter(role='se').order_by('username'),
            'author_overview':          _User.objects.filter(role='author').order_by('username')[:100],
            # legacy keys kept so other template sections don't crash
            'ce_escalation_count':      pending_stories.count(),
            'ce_escalations':           [],
            'chapters_cleared_month':   0,
            'content_removed_month':    0,
            'se_decisions':             [],
        })

    return ctx



@_editor_required(['se'])
def se_dashboard(request):
    ctx = _editorial_context(request)
    return render(request, 'novelux/se_dashboard.html', ctx)


@_editor_required(['ce'])
def ce_dashboard(request):
    ctx = _editorial_context(request)
    return render(request, 'novelux/ce_dashboard.html', ctx)


def editor_login_redirect(request):
    """
    After login, redirect editors to the correct dashboard based on their role.
    Called when an editor visits /dashboard/ but their role is not 'author'.
    """
    from rest_framework_simplejwt.tokens import AccessToken as AT
    token = _jwt_from_request(request)
    role  = 'reader'
    try:
        tok  = AT(token)
        role = tok.payload.get('role', 'reader')
    except Exception:
        pass

    routes = {
        'se': '/editorial/se/',
        'ce': '/editorial/ce/',
    }
    return redirect(routes.get(role, '/'))


# ═══════════════════════════════════════════════════════════════════════════════
#  EDITOR ONBOARDING — INVITE ACCEPTANCE WEB VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def editor_invite_page(request, token):
    """
    GET  /editorial/invite/<token>/
         Shows the onboarding registration form with role pre-filled.

    POST /editorial/invite/<token>/
         Creates the account, calls invite.accept(user), sets cookies,
         redirects to the correct editor dashboard.
    """
    from apps.editorial.models import EditorInvite
    from django.utils import timezone

    ROLE_LABELS = {'se': 'Senior Editor'}

    # Look up the invite
    try:
        invite = EditorInvite.objects.select_related(
            'invited_by', 'supervisor',
        ).get(token=token)
    except EditorInvite.DoesNotExist:
        return render(request, 'novelux/invite_invalid.html', {
            'reason': 'This invite link does not exist.',
        }, status=404)

    if not invite.is_valid:
        reason = (
            'This invite has already been used.'
            if invite.status == EditorInvite.STATUS_ACCEPTED
            else 'This invite link has expired or been revoked.'
        )
        return render(request, 'novelux/invite_invalid.html', {
            'reason': reason,
            'invite': invite,
        }, status=410)

    ctx = {
        'invite':      invite,
        'role_label':  ROLE_LABELS.get(invite.role, invite.role.upper()),
        'error':       None,
    }

    if request.method == 'GET':
        return render(request, 'novelux/editor_onboarding.html', ctx)

    # ── POST: create account ──────────────────────────────────────────────────
    from django.contrib.auth import get_user_model
    User = get_user_model()

    username   = request.POST.get('username', '').strip()
    password1  = request.POST.get('password1', '').strip()
    password2  = request.POST.get('password2', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name  = request.POST.get('last_name', '').strip()

    # Validation
    errors = {}
    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'That username is already taken.'
    if len(password1) < 8:
        errors['password1'] = 'Password must be at least 8 characters.'
    if password1 != password2:
        errors['password2'] = 'Passwords do not match.'

    if errors:
        ctx['errors'] = errors
        ctx['form'] = {
            'username':   username,
            'first_name': first_name,
            'last_name':  last_name,
        }
        return render(request, 'novelux/editor_onboarding.html', ctx)

    # Create user
    user = User.objects.create_user(
        username   = username,
        email      = invite.email,
        password   = password1,
        first_name = first_name,
        last_name  = last_name,
        role       = invite.role,       # pre-set the role
    )

    # Accept invite: creates EditorAssignment, generates editor_code for AEs
    invite.accept(user)

    # Mint JWT and set cookies — same flow as ajax_login
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh      = RefreshToken.for_user(user)
    access_token = refresh.access_token
    access_token['role']     = user.role
    access_token['username'] = user.username

    EDITOR_ROUTES = {'ae': '/editorial/ae/', 'se': '/editorial/se/'}
    next_url = EDITOR_ROUTES.get(user.role, '/editorial/')

    response = redirect(next_url)
    _set_auth_cookies(
        response,
        access_token  = str(access_token),
        refresh_token = str(refresh),
        username      = user.username,
        email         = user.email,
        role          = user.role,
    )
    return response




def contract_sign_page(request, slug):
    """
    GET /my-books/<slug>/contract/
    Renders the contract signing page for the author.
    Accessible via dashboard or the email link.
    """
    if not _is_authenticated(request):
        return redirect(f'/login/?next=/my-books/{slug}/contract/')

    from apps.stories.models import Story
    from apps.editorial.models import ContractApplication
    from apps.users.models import User

    username = request.COOKIES.get('nux_username', '')
    try:
        user = User.objects.select_related('author_profile').get(username=username)
    except User.DoesNotExist:
        return redirect(f'/login/?next=/my-books/{slug}/contract/')

    try:
        story = Story.objects.get(slug=slug, author=user)
    except Story.DoesNotExist:
        from django.http import Http404
        raise Http404

    try:
        app = story.contract_application
        contract_type       = app.contract_type or 'non_exclusive'
        ce_note             = (app.se_note or '').split('\n\nCE note:')[-1].strip() if 'CE note:' in (app.se_note or '') else ''
        already_signed      = app.status == ContractApplication.STATUS_SIGNED
    except ContractApplication.DoesNotExist:
        contract_type  = 'non_exclusive'
        ce_note        = ''
        already_signed = getattr(user, 'author_profile', None) and user.author_profile.has_contract

    # Guard: only show the signing form once CE has actually sent the contract.
    # 'contract_sent' = SE approved / CE not yet acted — too early.
    contract_ready = (
        story.contract_status == 'awaiting_signature'
        or already_signed
        or story.contract_status == 'signed'
    )

    contract_type_label = 'Exclusive' if contract_type == 'exclusive' else 'Non-Exclusive'

    return render(request, 'novelux/contract_sign.html', {
        'story':               story,
        'contract_type':       contract_type,
        'contract_type_label': contract_type_label,
        'ce_note':             ce_note,
        'already_signed':      already_signed,
        'contract_ready':      contract_ready,
        'access_token':        _jwt_from_request(request),
        'api_base':            '/api',
    })

@csrf_exempt
def ce_invite_create_web(request):
    """
    POST /editorial/invite/create/
    AJAX endpoint called from the CE dashboard invite modal.
    Body: { email, role, supervisor_id, notes }
    Returns JSON.
    """
    if not _is_authenticated(request):
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    from apps.editorial.models import EditorInvite
    from apps.editorial.tasks import send_editor_invite_email
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.tokens import AccessToken as AT

    # Verify CE role
    token_str = _jwt_from_request(request)
    try:
        tok  = AT(token_str)
        role = tok.payload.get('role', '')
    except Exception:
        role = ''

    if role != 'ce':
        return JsonResponse({'error': 'Only Chief Editors can create invites.'}, status=403)

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body.'}, status=400)

    email         = body.get('email', '').strip().lower()
    editor_role   = body.get('role', '').strip()
    supervisor_id = body.get('supervisor_id')
    notes         = body.get('notes', '').strip()

    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)
    if editor_role not in ('se',):
        return JsonResponse({'error': "Role must be 'se'."}, status=400)

    User = get_user_model()

    # Get the CE user from JWT
    try:
        ce_user = User.objects.get(pk=tok.payload.get('user_id'))
    except User.DoesNotExist:
        return JsonResponse({'error': 'CE account not found.'}, status=404)

    # Resolve supervisor
    supervisor = None
    if supervisor_id:
        try:
            supervisor = User.objects.get(pk=supervisor_id, role__in=('se', 'ce'))
        except User.DoesNotExist:
            return JsonResponse({'error': 'Supervisor not found.'}, status=404)

    # SE reports directly to the CE who invited them
    if editor_role == 'se' and not supervisor:
        supervisor = ce_user

    # Check for existing pending invite to this email
    existing = EditorInvite.objects.filter(
        email=email, status='pending',
    ).first()
    if existing:
        return JsonResponse({
            'error': f'A pending invite already exists for {email}. Revoke it first or resend it.',
        }, status=400)

    invite = EditorInvite.create_invite(
        email      = email,
        role       = editor_role,
        invited_by = ce_user,
        supervisor = supervisor,
        notes      = notes,
    )

    # Fire email in a background thread so the response returns immediately.
    # This prevents 502s on Render caused by synchronous SMTP blocking the worker.
    import threading

    # Capture values needed by the thread (request object is not thread-safe to pass directly)
    _invite_id  = invite.id
    _scheme     = 'https' if request.is_secure() else 'http'
    _host       = request.get_host()

    def _send_invite_email_async():
        import logging
        _log = logging.getLogger(__name__)
        try:
            from apps.editorial.models import EditorInvite as _EI
            _inv = _EI.objects.get(pk=_invite_id)

            # Reconstruct a minimal request-like object the task needs
            class _FakeRequest:
                def is_secure(self):      return _scheme == 'https'
                def get_host(self):       return _host

            send_editor_invite_email(_inv, _FakeRequest())
            _log.info('Invite email sent to %s (invite %s)', _inv.email, _invite_id)
        except Exception as _e:
            _log.error('Invite email failed for invite %s: %s', _invite_id, _e)

    t = threading.Thread(target=_send_invite_email_async, daemon=True)
    t.start()

    return JsonResponse({
        'ok':         True,
        'invite_id':  invite.id,
        'email_sent': True,   # optimistic — email is queued in background thread
        'expires_at': invite.expires_at.isoformat(),
        'message':    f'Invite created for {email}. Email is being sent.',
    })


# ══════════════════════════════════════════════════════════════════════════════
# FORGOT / RESET PASSWORD
# ══════════════════════════════════════════════════════════════════════════════

def forgot_password_page(request):
    """GET /forgot-password/ — show the "enter your email" form."""
    if _is_authenticated(request):
        return redirect('novelux:dashboard')
    return render(request, 'novelux/forgot_password.html')


def reset_password_page(request, uidb64, token):
    """GET /reset-password/<uidb64>/<token>/ — show the set-new-password form."""
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    from apps.users.models import User

    valid = False
    try:
        uid  = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
        valid = default_token_generator.check_token(user, token)
    except Exception:
        pass

    return render(request, 'novelux/reset_password.html', {
        'valid':   valid,
        'uidb64':  uidb64,
        'token':   token,
    })


@csrf_exempt
@require_POST
def ajax_forgot_password(request):
    """
    POST /auth/forgot-password/
    Body: { email }
    Sends a password-reset email. Always returns 200 to avoid user enumeration.
    """
    import threading
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.contrib.auth.tokens import default_token_generator
    from django.core.mail import send_mail
    from apps.users.models import User

    try:
        body  = json.loads(request.body)
        email = body.get('email', '').strip().lower()
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    if not email or '@' not in email:
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

    def _send():
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return  # Silent — don't reveal whether the email exists

        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        scheme = 'https' if os.environ.get('RENDER') == 'true' else request.scheme
        host   = request.get_host()
        reset_url = f'{scheme}://{host}/reset-password/{uid}/{token}/'

        subject = 'Reset your Novelux password'
        message = (
            f'Hi {user.username},\n\n'
            f'We received a request to reset the password for your Novelux account.\n\n'
            f'Click the link below to set a new password (valid for 1 hour):\n\n'
            f'{reset_url}\n\n'
            f'If you did not request this, you can safely ignore this email.\n\n'
            f'— The Novelux Team'
        )
        html_message = f"""
<div style="font-family:'Geist',system-ui,sans-serif;max-width:480px;margin:0 auto;padding:40px 24px;background:#fff;color:#181818;">
  <div style="margin-bottom:28px;">
    <span style="font-size:14px;font-weight:700;letter-spacing:.04em;">Novelux</span>
  </div>
  <h1 style="font-size:20px;font-weight:600;letter-spacing:-.02em;margin:0 0 8px;">Reset your password</h1>
  <p style="font-size:14px;color:#666;line-height:1.6;margin:0 0 24px;">
    Hi {user.username},<br><br>
    We received a request to reset the password for your Novelux account.
    Click the button below — the link is valid for <strong>1 hour</strong>.
  </p>
  <a href="{reset_url}"
     style="display:inline-block;padding:12px 24px;background:hsl(14 62% 38%);color:#fff;
            font-size:14px;font-weight:600;text-decoration:none;">
    Reset Password
  </a>
  <p style="font-size:12px;color:#999;margin-top:24px;line-height:1.6;">
    If the button doesn't work, copy and paste this URL into your browser:<br>
    <a href="{reset_url}" style="color:hsl(14 62% 38%);word-break:break-all;">{reset_url}</a>
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:28px 0;">
  <p style="font-size:11px;color:#aaa;">If you didn't request a password reset, you can safely ignore this email.</p>
</div>"""

        try:
            send_mail(subject, message,
                      from_email=None,  # uses DEFAULT_FROM_EMAIL
                      recipient_list=[user.email],
                      html_message=html_message,
                      fail_silently=False)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error('Password reset email failed for %s: %s', email, e)

    threading.Thread(target=_send, daemon=True).start()
    return JsonResponse({'ok': True, 'message': 'If an account with that email exists, a reset link has been sent.'})


@csrf_exempt
@require_POST
def ajax_reset_password(request):
    """
    POST /auth/reset-password/
    Body: { uidb64, token, password1, password2 }
    Validates token and sets the new password.
    """
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.tokens import default_token_generator
    from apps.users.models import User

    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid request body'}, status=400)

    uidb64    = body.get('uidb64', '').strip()
    token     = body.get('token', '').strip()
    password1 = body.get('password1', '')
    password2 = body.get('password2', '')

    if not uidb64 or not token:
        return JsonResponse({'error': 'Invalid reset link.'}, status=400)
    if not password1:
        return JsonResponse({'error': 'Password is required.'}, status=400)
    if len(password1) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters.'}, status=400)
    if password1 != password2:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)

    try:
        uid  = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except Exception:
        return JsonResponse({'error': 'Invalid reset link.'}, status=400)

    if not default_token_generator.check_token(user, token):
        return JsonResponse({'error': 'This reset link has expired or already been used. Please request a new one.'}, status=400)

    user.set_password(password1)
    user.save(update_fields=['password'])

    return JsonResponse({'ok': True, 'message': 'Password updated successfully. You can now sign in.'})


# ══════════════════════════════════════════════════════════════════════════════
# AUTHOR KYC
# ══════════════════════════════════════════════════════════════════════════════

def author_kyc_page(request):
    """GET /author/kyc/ — KYC form; must be logged in as author."""
    if not _is_authenticated(request):
        return redirect('/login/?next=/author/kyc/')

    from apps.users.models import AuthorKYC
    token = _jwt_from_request(request)
    # Check if already submitted
    existing = None
    try:
        from apps.users.models import User
        from rest_framework_simplejwt.tokens import AccessToken
        payload = AccessToken(token)
        user_id = payload['user_id']
        existing = AuthorKYC.objects.filter(user_id=user_id).first()
    except Exception:
        pass

    countries = [
        'Nigeria','Ghana','Kenya','South Africa','Egypt','Ethiopia','Tanzania',
        'Uganda','Senegal','Cameroon','United States','United Kingdom','Canada',
        'Australia','India','Philippines','Indonesia','Brazil','Mexico',
        'Germany','France','Italy','Spain','Netherlands','Poland','Turkey',
        'Saudi Arabia','UAE','Pakistan','Bangladesh','Other',
    ]
    return render(request, 'novelux/author_kyc.html', {
        'existing':  existing,
        'username':  request.COOKIES.get('nux_username', ''),
        'email':     request.COOKIES.get('nux_email', ''),
        'countries': countries,
    })


@csrf_exempt
@require_POST
def ajax_kyc_submit(request):
    """
    POST /author/kyc/submit/
    Accepts multipart/form-data. Saves AuthorKYC and redirects author to dashboard.
    """
    if not _is_authenticated(request):
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    from apps.users.models import User, AuthorKYC
    from rest_framework_simplejwt.tokens import AccessToken

    try:
        token = _jwt_from_request(request)
        payload = AccessToken(token)
        user = User.objects.get(pk=payload['user_id'])
    except Exception:
        return JsonResponse({'error': 'Invalid session. Please log in again.'}, status=401)

    # Don't allow re-submission once approved
    existing = AuthorKYC.objects.filter(user=user).first()
    if existing and existing.status == 'approved':
        return JsonResponse({'ok': True, 'next': '/dashboard/'})

    data = request.POST
    files = request.FILES

    # ── Validate required personal fields ────────────────────────────────
    required = ['full_name', 'phone', 'contact_address', 'country', 'id_type', 'id_number']
    for field in required:
        if not data.get(field, '').strip():
            return JsonResponse({'error': f'{field.replace("_", " ").title()} is required.'}, status=400)

    if not existing and 'id_document' not in files:
        return JsonResponse({'error': 'ID document photo is required.'}, status=400)

    # ── Validate payment ──────────────────────────────────────────────────
    payment_method = data.get('payment_method', 'bank_account')
    if payment_method == 'bank_account':
        for f in ['account_holder', 'bank_name', 'account_number', 'swift_code', 'bank_country']:
            if not data.get(f, '').strip():
                return JsonResponse({'error': f'{f.replace("_", " ").title()} is required for bank accounts.'}, status=400)
    elif payment_method == 'paypal':
        if not data.get('paypal_email', '').strip():
            return JsonResponse({'error': 'PayPal email is required.'}, status=400)

    # ── Save ──────────────────────────────────────────────────────────────
    kyc = existing or AuthorKYC(user=user)
    kyc.full_name       = data.get('full_name', '').strip()
    kyc.phone           = data.get('phone', '').strip()
    kyc.contact_address = data.get('contact_address', '').strip()
    kyc.country         = data.get('country', '').strip()
    kyc.id_type         = data.get('id_type', 'national_id')
    kyc.id_number       = data.get('id_number', '').strip()
    kyc.payment_method  = payment_method
    kyc.account_holder  = data.get('account_holder', '').strip()
    kyc.bank_name       = data.get('bank_name', '').strip()
    kyc.account_number  = data.get('account_number', '').strip()
    kyc.swift_code      = data.get('swift_code', '').strip()
    kyc.bank_country    = data.get('bank_country', '').strip()
    kyc.paypal_email    = data.get('paypal_email', '').strip()
    if 'id_document' in files:
        kyc.id_document = files['id_document']
    # Reset to pending if resubmitting after rejection
    if existing and existing.status == 'rejected':
        kyc.status = 'pending'
    kyc.save()

    return JsonResponse({'ok': True, 'next': '/dashboard/'})