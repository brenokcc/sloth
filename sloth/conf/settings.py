import os
# ALLOWED_HOSTS.append('*')
# MEDIA_ROOT = '{}/{}'.format(BASE_DIR, 'media')
# STATIC_ROOT = '{}/{}'.format(BASE_DIR, 'static')
# MEDIA_URL = '/media/'

CLOUD_PROVIDER_API_URL = os.environ.get('CLOUD_PROVIDER_API_URL', 'https://deploy.cloud.aplicativo.click')
CLOUD_PROVIDER_API_TOKEN = os.environ.get('CLOUD_PROVIDER_API_TOKEN', '0123456789')

CSRF_TRUSTED_ORIGINS = [
    'http://*.local.aplicativo.click',
    'https://*.cloud.aplicativo.click',
]
ADMINS = [('admin', 'admin@mydomain.com')]

USER_ROLE_NAME = 'Usuário'
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Recife'
USE_I18N = True
USE_L10N = True
USE_TZ = False
DECIMAL_SEPARATOR = ','
USE_THOUSAND_SEPARATOR = True
OAUTH2_PROVIDER_APPLICATION_MODEL = 'api.application'
OAUTH2_PROVIDER = {
    'SCOPES_BACKEND_CLASS': 'sloth.api.backends.Scopes'
}

DEFAULT_FROM_EMAIL = 'noreply@mydomain.com'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mydomain.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'noreply@mydomain.com>'
EMAIL_HOST_PASSWORD = '*****'
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_PASSWORD = lambda user: '123'
FORCE_PASSWORD_DEFINITION = False
OAUTH2_AUTHENTICATORS = {
    'APP': {
        'TEXT': 'Acessar com App',
        'LOGO': None,
        'REDIRECT_URI': 'http://localhost:8000/app/login/',
        'CLIENTE_ID': None,
        'CLIENT_SECRET': None,
        'AUTHORIZE_URL': None,
        'ACCESS_TOKEN_URL': None,
        'USER_DATA_URL': None,
        'USER_AUTO_CREATE': False,
        'USER_DATA': {
            'USERNAME': 'username',
            'EMAIL': 'email',
            'FIRST_NAME': None,
            'LAST_NAME': None
        }
    }
}

if os.environ.get('REDIS_HOST'):
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://{}:{}/1".format(REDIS_HOST, REDIS_PORT),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASSWORD
            }
        }
    }

if os.environ.get('POSTGRES_HOST'):
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
    DATABASES['default']['NAME'] = os.environ.get('DATABASE_NAME', 'database')
    DATABASES['default']['USER'] = os.environ.get('DATABASE_USER', 'postgres')
    DATABASES['default']['PASSWORD'] = os.environ.get('DATABASE_PASSWORD', 'password')
    DATABASES['default']['HOST'] = os.environ.get('DATABASE_HOST', 'postgres')
    DATABASES['default']['PORT'] = os.environ.get('DATABASE_PORT', '5432')


try:
    from .local_settings import *
except ImportError as e:
    print('[WARNING] Could not import local_settings.py: {}'.format(e))
