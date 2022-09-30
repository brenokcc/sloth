
# ALLOWED_HOSTS.append('*')
# MEDIA_ROOT = '{}/{}'.format(BASE_DIR, 'media')
# STATIC_ROOT = '{}/{}'.format(BASE_DIR, 'static')
# MEDIA_URL = '/media/'

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
	'NAME': 'Sloth',
	'ICON': '/static/images/icon.png',
	'FAVICON': '/static/images/icon.png',
	'VERSION': 1.0,
	'LOGIN': {
		'LOGO': '/static/images/logo.png',
		'TITLE': None,
		'TEXT': None,
		'IMAGE': '/static/images/login.jpeg',
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

# #SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# #CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1', 'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}}}