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
    path('copyright-policy/',        views.copyright_policy,    name='copyright_policy'),

    # ── Auth pages ────────────────────────────────────────────────────────────
    path('login/',                                views.login_page,            name='login'),
    path('register/',                             views.register_page,         name='register'),
    path('logout/',                               views.logout_view,           name='logout'),
    path('forgot-password/',                      views.forgot_password_page,  name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password_page, name='reset_password'),

    # ── Auth AJAX (called by JS, returns JSON) ────────────────────────────────
    path('auth/login-web/',          views.ajax_login,              name='ajax_login'),
    path('auth/register-web/',       views.ajax_register,           name='ajax_register'),
    path('auth/google-web/',         views.ajax_google_auth,        name='ajax_google'),
    path('auth/refresh-web/',        views.ajax_refresh_token,      name='ajax_refresh'),
    path('auth/forgot-password/',    views.ajax_forgot_password,    name='ajax_forgot_password'),
    path('auth/reset-password/',     views.ajax_reset_password,     name='ajax_reset_password'),

    # ── Author dashboard ──────────────────────────────────────────────────────
    path('dashboard/',               views.author_dashboard,    name='dashboard'),
    path('author/onboarding/',       views.author_onboarding,   name='author_onboarding'),

    # ── Editor dashboards (role-gated: ae / se / ce) ──────────────────────────
    path('editorial/',               views.editor_login_redirect, name='editorial_redirect'),
    path('editorial/se/',            views.se_dashboard,          name='se_dashboard'),
    path('editorial/ce/',            views.ce_dashboard,          name='ce_dashboard'),

    # ── Editor onboarding invites ────────────────────────────────────────────
    path('editorial/invite/create/',              views.ce_invite_create_web,  name='invite_create'),
    path('editorial/invite/<str:token>/',         views.editor_invite_page,    name='invite_accept'),

    # ── APK download ──────────────────────────────────────────────────────────
    path('download/apk/',            views.download_apk,        name='download_apk'),

    # ── AJAX helpers ──────────────────────────────────────────────────────────
    path('book-request/',            views.book_request_web,    name='book_request'),
    path('my-books/<slug:slug>/contract/', views.contract_sign_page, name='contract_sign'),
    path('newsletter/',              views.newsletter_signup,   name='newsletter'),

    # ── KYC ───────────────────────────────────────────────────────────────────
    path('author/kyc/',              views.author_kyc_page,     name='author_kyc'),
    path('author/kyc/submit/',       views.ajax_kyc_submit,     name='ajax_kyc_submit'),
]