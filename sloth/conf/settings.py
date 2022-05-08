
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
	}
}