"""
Django settings for investimentos project.

Generated by 'django-admin startproject' using Django 4.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-kuzmojummvu2jsk8nz#g12okyaty3qk409*$_z!#)f0un3xiqd'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'investimentos', 'oauth2_provider', 'sloth.api', 'sloth.app',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'investimentos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'investimentos.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ALLOWED_HOSTS.append('*')
MEDIA_ROOT = '{}/{}'.format(BASE_DIR, 'media')
STATIC_ROOT = '{}/{}'.format(BASE_DIR, 'static')
MEDIA_URL = '/media/'

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

SLOTH = {
	'NAME': 'COLETA SETEC',
	'ICON': None,
	'FAVICON': '/static/images/icon.png',
	'VERSION': 1.0,
	'LOGIN': {
		'LOGO': None,
		'TITLE': 'COLETA SETEC',
		'TEXT': None,
		'IMAGE': None,
		'USERNAME_MASK': None
	},
	'INCLUDE': {
		'CSS': [],
		'JS': [],
	},
	'ROLES':{
		'ALLOW_MULTIPLE': True
	},
    'OAUTH_LOGIN': {
        'APP': {
            'TEXT': 'Acessar com APP',
            'LOGO': None,
            'REDIRECT_URI': 'http://localhost:8000/app/login/APP/',
            'CLIENTE_ID': None,
            'CLIENT_SECRET': None,
            'AUTHORIZE_URL': None,
            'ACCESS_TOKEN_URL': None,
            'USER_DATA_URL': None,
			'USER_AUTO_CREATE': False,
			'USER_DATA':{
				'USERNAME': 'username',
				'EMAIL': 'email',
				'FIRST_NAME': None,
				'LAST_NAME': None
			}
        }
    },
	'2FA': False,
	'LIST_PER_PAGE': 20,
	'DEFAULT_PASSWORD': lambda user=None: '123',
	'FORCE_PASSWORD_DEFINITION': False,
	'ICONS': ['fontawesome', 'materialicons']
}

#SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
#CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1', 'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}}}