"""
NoveluX Frontend — Django Integration Guide
============================================
This file shows exactly what to add/change in your Django project on Render.

STEP 1 — Copy the app into your project
-----------------------------------------
Copy the entire  novelux_web/  folder into your Django project root
(same level as manage.py and apps/).

Your project tree should look like:
  manage.py
  config/          ← your existing config folder
  apps/            ← your existing apps
  novelux_web/     ← NEW: copy this folder
  templates/       ← NEW: create this if it doesn't exist
    novelux/       ← copy all .html files here
  static/          ← NEW or existing
    novelux/       ← copy this folder
      images/
      css/
      js/


STEP 2 — settings.py changes
------------------------------
Add the following to your existing settings.py:
"""

SETTINGS_ADDITIONS = """
# ── Add novelux_web to INSTALLED_APPS ──────────────────────────────────────
INSTALLED_APPS = [
    # ... your existing apps ...
    'novelux_web',         # ← ADD THIS
]


# ── Templates: add the project-level templates/ dir ────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',   # ← ADD THIS LINE
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'novelux_web.context_processors.site_globals',  # ← ADD THIS
            ],
        },
    },
]


# ── Static files ────────────────────────────────────────────────────────────
import os
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'    # for collectstatic on Render
STATICFILES_DIRS = [
    BASE_DIR / 'static',   # ← your static/ folder with novelux/ inside
]


# ── APK path (optional — set when APK is ready) ─────────────────────────────
NOVELUX_APK_PATH = os.environ.get('NOVELUX_APK_PATH', '')


# ── Login redirect (for @login_required on dashboard) ────────────────────────
LOGIN_URL = '/api/auth/login/'    # or wherever your login page is
"""


STEP3 = """
STEP 3 — config/urls.py: include the novelux_web URLs
-------------------------------------------------------
Add this to your existing config/urls.py:

from django.urls import path, include

urlpatterns = [
    # ── Your existing API routes ──────────────────────────────────────
    path('api/auth/',           include('apps.users.urls')),
    path('api/stories/',        include('apps.stories.urls')),
    path('api/chapters/',       include('apps.chapters.urls')),
    path('api/coins/',          include('apps.coins.urls')),
    path('api/reading/',        include('apps.coins.reading_urls')),
    path('api/comments/',       include('apps.comments.urls')),
    path('api/tips/',           include('apps.tips.urls')),
    path('api/notifications/',  include('apps.notifications.urls')),
    path('admin/',              admin.site.urls),

    # ── Website pages (ADD THIS) ──────────────────────────────────────
    path('',                    include('novelux_web.urls')),
]
"""


STEP4 = """
STEP 4 — Collect static files
-------------------------------
Run these commands after deploying to Render:

    python manage.py collectstatic --noinput

Or add it to your Render build command:
    pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput


STEP 5 — Render environment variables
---------------------------------------
No new env vars are required. Optional:
    NOVELUX_APK_PATH=/path/to/novelux.apk   (when APK is ready)


STEP 6 — Author Dashboard API Authentication
----------------------------------------------
The author dashboard HTML calls the DRF API directly using fetch().
The JWT token needs to be available to the JavaScript.

The view injects {{ api_base }} into the template.
The JS in author_dashboard.html should read the token from localStorage
(same place the Flutter app stores it via the web login page), or from
a cookie set by the login view.

For the dashboard to work on the web:
1. The user logs in at /api/auth/login/ and receives an access token
2. Store it: localStorage.setItem('nux_access', token)
3. The dashboard JS reads it: const token = localStorage.getItem('nux_access')
4. All fetch() calls include: Authorization: Bearer ${token}


STEP 7 — File structure summary
---------------------------------
After setup your project should have:

  manage.py
  requirements.txt
  config/
    settings.py      ← modified (steps above)
    urls.py          ← modified (step 3)
  apps/
    users/
    stories/
    ...
  novelux_web/       ← NEW
    __init__.py
    apps.py
    views.py
    urls.py
    context_processors.py
  templates/         ← NEW
    novelux/
      index.html
      author_dashboard.html
      author_onboarding.html
      become_author.html
      faq.html
      privacy.html
      terms.html
      cookies.html
      content_guidelines.html
  static/            ← NEW
    novelux/
      images/
        logo.png
        lunas_betrayal.png
        sweet_chaos.png
        The_Ashborn_Crown.png
        ... (other cover images)
"""


print("Integration guide written.")

# =============================================================================
# AUTHENTICATION FIX — SUMMARY
# =============================================================================
AUTH_FIX = """
THE PROBLEM:
  The old dashboard used Django's @login_required which checks Django SESSION
  cookies. But NoveluX uses JWT tokens. These two systems don't know about
  each other, so /dashboard/ always redirected to /api/auth/login/.

THE FIX — 3-layer auth system:
  1. Login page at /login/  — user enters email+password
  2. JS POSTs to /auth/login-web/ — Django view hits the DRF JWT endpoint
  3. Access token stored as httpOnly cookie (nux_access) — NOT localStorage
  4. Dashboard view reads the cookie server-side and injects token into <meta>
  5. Dashboard JS reads token from meta tag for API calls
  6. If token expires, /auth/refresh-web/ silently refreshes it

GOOGLE SIGN-IN FIX:
  The Google button now calls the Google OAuth2 flow correctly:
  1. google.accounts.oauth2.initTokenClient() gets an access token
  2. We fetch /oauth2/v3/userinfo to get email/name/picture
  3. POST to /auth/google-web/ → Django → your existing /api/auth/google/ endpoint
  4. Access + refresh tokens stored in httpOnly cookies

NEW ROUTES:
  GET  /login/             — login page (replaces /api/auth/login/?next=...)
  GET  /register/          — registration page
  GET  /logout/            — clears cookies and redirects to /
  POST /auth/login-web/    — AJAX login handler
  POST /auth/register-web/ — AJAX register handler
  POST /auth/google-web/   — AJAX Google OAuth handler
  POST /auth/refresh-web/  — silent JWT refresh

SETTINGS.PY — add this:
  LOGIN_URL = '/login/'   ← was '/api/auth/login/'

GOOGLE_CLIENT_ID — add to Render environment variables:
  GOOGLE_WEB_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
  (Get from console.cloud.google.com → APIs → Credentials → Web client)

REQUIREMENTS — add to requirements.txt:
  requests>=2.28.0    ← used by Django views to call internal DRF endpoints
"""
