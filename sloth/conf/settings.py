
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
	'ICON': '/static/images/sloth.png',
	'FAVICON': None,
	'VERSION': 1.0,
	'LOGIN': {
		'LOGO': '/static/images/sloth.png',
		'TITLE': None,
		'TEXT': None,
		'IMAGE': None,
	},
	'HEADER': {
		'LOGO': '/static/images/sloth.png',
		'TITLE': None,
		'TEXT': None,
	},
	'FOOTER': {
		'TITLE': '© 2022 Slogth',
		'TEXT': 'Todos os direitos reservados',
		'LINKS': [],
	},
	'INCLUDE': {
		'CSS': [],
		'JS': [],
	},
	'ROLES':{
		'ALLOW_MULTIPLE': True
	}
}

# #SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# #CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1', 'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}}}