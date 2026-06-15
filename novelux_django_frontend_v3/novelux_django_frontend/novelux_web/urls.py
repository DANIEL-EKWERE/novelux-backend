from django.urls import path
from . import views

app_name = 'novelux'

urlpatterns = [
    # ── Public pages ──────────────────────────────────────────────────────────
    path('',                         views.index,               name='index'),
    path('become-author/',           views.become_author,       name='become_author'),
    path('faq/',                     views.faq,                 name='faq'),
    path('privacy/',                 views.privacy,             name='privacy'),
    path('terms/',                   views.terms,               name='terms'),
    path('cookies/',                 views.cookies_page,        name='cookies'),
    path('content-guidelines/',      views.content_guidelines,  name='content_guidelines'),

    # ── Auth pages ────────────────────────────────────────────────────────────
    path('login/',                   views.login_page,          name='login'),
    path('register/',                views.register_page,       name='register'),
    path('logout/',                  views.logout_view,         name='logout'),

    # ── Auth AJAX (called by JS, return JSON) ─────────────────────────────────
    path('auth/login-web/',          views.ajax_login,          name='ajax_login'),
    path('auth/register-web/',       views.ajax_register,       name='ajax_register'),
    path('auth/google-web/',         views.ajax_google_auth,    name='ajax_google'),
    path('auth/refresh-web/',        views.ajax_refresh_token,  name='ajax_refresh'),

    # ── Author area ───────────────────────────────────────────────────────────
    path('dashboard/',               views.author_dashboard,    name='dashboard'),
    path('author/onboarding/',       views.author_onboarding,   name='author_onboarding'),

    # ── APK download ──────────────────────────────────────────────────────────
    path('download/apk/',            views.download_apk,        name='download_apk'),

    # ── AJAX helpers ──────────────────────────────────────────────────────────
    path('book-request/',            views.book_request_web,    name='book_request'),
    path('newsletter/',              views.newsletter_signup,   name='newsletter'),
]
