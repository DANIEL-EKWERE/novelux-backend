import json
import os
from pathlib import Path
from decouple import config
from datetime import timedelta

import dj_database_url

import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
#ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')
ALLOWED_HOSTS = [
    'novelux-backend.onrender.com',
    'localhost',
    '127.0.0.1',
    'novelux.onrender.com'
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'django_filters',
    'drf_spectacular',
    'storages',
    'ckeditor',
    'anymail',
]

LOCAL_APPS = [
    'apps.users',
    'apps.stories',
    'apps.chapters',
    'apps.coins',
    'apps.audio',
    'apps.comments',
    'apps.tips',
    'apps.branching',
    'apps.notifications',
    'apps.reviews',
    'apps.editorial',      # Editorial hierarchy — AE / SE / CE
    'novelux_web',

]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.postgresql',
         'NAME': 'postgres',#'novelux_backend',#config('DB_NAME', default='novelplatform'),
         'USER': 'postgres',#config('DB_USER', default='postgres'),
         'PASSWORD': 'MKPOIKANA1dt',#config('DB_PASSWORD', default='password'),
         'HOST': 'database-1.cdcs8iswifke.eu-north-1.rds.amazonaws.com',#config('DB_HOST', default='localhost'),
         'PORT': '5432'#config('DB_PORT', default='5432'),
     }
 }


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# DATABASES = {
#     'default': dj_database_url.parse("postgresql://novelux_db_user:o1efbmKLxGZ6w0KvVw42fSGNlJOTN5pR@dpg-d6sq2895pdvs73e0dfs0-a.oregon-postgres.render.com/novelux_db")
# }

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# firebase messgging config


SITE_URL = config('SITE_URL', default='')

# cred_path = os.path.join(BASE_DIR, 'novelux-credentials.json')

# cred = credentials.Certificate(cred_path)
# firebase_admin.initialize_app(cred)
# json.loads(os.getenv('FIREBASE_CONFIG'))
# FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'novelux-1a13a-firebase-adminsdk-fbsvc-efebcdc03d.json')
FIREBASE_CREDENTIALS_PATH = json.loads(os.getenv('FIREBASE_CONFIG'))

GOOGLE_ANDROID_CLIENT_ID = '302060725266-si3i60jiots71onc2o075ta6c63gnkfu.apps.googleusercontent.com'
GOOGLE_IOS_CLIENT_ID = '302060725266-8r9c6525a9c810f75geigek68a5339u6.apps.googleusercontent.com'
GOOGLE_WEB_CLIENT_ID = '302060725266-8lm05k7jgm0dlbl1p2ht5hkfifdg1cq8.apps.googleusercontent.com'


# FIREBASE_CREDENTIALS_PATH = json.loads(os.getenv('FIREBASE_CONFIG'))

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = 'eu-north-1'  # Your RDS region

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

GOOGLE_CLIENT_IDS = [
    os.environ.get('GOOGLE_ANDROID_CLIENT_ID'),
    os.environ.get('GOOGLE_WEB_CLIENT_ID'),
    os.environ.get('GOOGLE_IOS_CLIENT_ID'),
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATIC_ROOT = os.path.join(BASE_DIR,'static')
'''
this shouldn't be here

# STATICFILES_DIRS = [
#    os.path.join(BASE_DIR, 'static')
# ]
STATIC_ROOT = os.path.join(BASE_DIR,'static')

'''

STATICFILES_DIRS = [BASE_DIR/ 'static']


'''
this shouldn't be here
'''

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SITE_ID = 1

# ── REST Framework ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# ── JWT ──────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(weeks=50),
    'REFRESH_TOKEN_LIFETIME': timedelta(weeks=300),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ─────────────────────────────────────────────────────────────────────
"""
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='https://novelux-backend.onrender.com').split(',')
CORS_ALLOW_CREDENTIALS = True
"""
CORS_ALLOWED_ORIGINS = [
    "https://novelux-backend.onrender.com",
    "https://novelux.onrender.com",
]

CORS_ALLOW_CREDENTIALS = True


# ── Allauth / Social Auth ────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
        }
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'APP': {
            'client_id': config('FACEBOOK_APP_ID', default=''),
            'secret': config('FACEBOOK_APP_SECRET', default=''),
        }
    }
}

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'novel-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'novel-refresh-token',
    'REGISTER_SERIALIZER': 'apps.users.serializers.RegisterSerializer',
}

# ── Redis & Celery ───────────────────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': REDIS_URL,
#         'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
#     }
# }


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

#CELERY_BROKER_URL = REDIS_URL

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = DEBUG        # In DEBUG mode, tasks run synchronously (no Redis needed)
CELERY_TASK_EAGER_PROPAGATES = DEBUG 


# CELERY_RESULT_BACKEND = REDIS_URL
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'

# ── AWS S3 Storage ───────────────────────────────────────────────────────────
USE_S3 = config('USE_S3', default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ── Stripe ───────────────────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# ── Coin System ──────────────────────────────────────────────────────────────
COIN_PACKAGES = [
    {'id': 'coins_100',  'coins': 100,  'price_usd': 0.99,  'label': '100 Coins'},
    {'id': 'coins_500',  'coins': 500,  'price_usd': 3.99,  'label': '500 Coins'},
    {'id': 'coins_1200', 'coins': 1200, 'price_usd': 8.99,  'label': '1200 Coins'},
    {'id': 'coins_2500', 'coins': 2500, 'price_usd': 14.99, 'label': '2500 Coins'},
    {'id': 'coins_5000', 'coins': 5000, 'price_usd': 24.99, 'label': '5000 Coins'},
]

SUBSCRIPTION_PLANS = [
    {'id': 'vip_monthly', 'label': 'VIP Monthly', 'price_usd': 9.99,  'coins_per_month': 1000, 'discount_pct': 20},
    {'id': 'vip_yearly',  'label': 'VIP Yearly',  'price_usd': 89.99, 'coins_per_month': 1200, 'discount_pct': 30},
]

AUTHOR_REVENUE_SHARE = 0.50   # 50%
TIP_AUTHOR_SHARE     = 0.85   # 85% of tip goes to author

# ── API Docs ─────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Novel Platform API',
    'DESCRIPTION': 'Backend API for a GoodNovel-style web fiction platform',
    'VERSION': '1.0.0',
}

# ── Email ────────────────────────────────────────────────────────────────────
# EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
# EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
# EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@novelplatform.com')


# RESEND_API_KEY = config('RESEND_API_KEY', default='')
 
# if RESEND_API_KEY:
#     EMAIL_BACKEND  = 'anymail.backends.resend.EmailBackend'
#     ANYMAIL = {
#         'RESEND_API_KEY': RESEND_API_KEY,
#     }
# else:
#     EMAIL_BACKEND = config(
#         'EMAIL_BACKEND',
#         default='django.core.mail.backends.console.EmailBackend'
#     )
 
# DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Novelux <onboarding@resend.dev>')
 
# EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST          = 'smtp-relay.brevo.com'
# EMAIL_PORT          = 587
# EMAIL_USE_TLS       = True
# EMAIL_HOST_USER     = 'ab9630001@smtp-brevo.com'
# EMAIL_HOST_PASSWORD = config('BREVO_SMTP_PASSWORD', default='')
 
# DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='novelux<ekweredaniel8@gmail.com>')
 

import os
# ... (rest of your existing settings like BASE_DIR, SECRET_KEY, etc.) ...

# ==============================================================================
# EMAIL CONFIGURATION (BREVO VIA ANYMAIL API)
# ==============================================================================

# Tell Django to route all mail functions through Anymail's Brevo module
EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"

ANYMAIL = {
    "BREVO_API_KEY": config("BREVO_API_KEY", default=""),
}

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="novelux <ekweredaniel8@gmail.com>")

# Optional: Set a reply-to configuration if your business logic demands it
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# # Add these lines anywhere in settings.py
# ACCOUNT_EMAIL_VERIFICATION = 'none'
# ACCOUNT_EMAIL_REQUIRED = False


LOGIN_URL = '/login/'   # was '/api/auth/login/'
