
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
LOGO = '/static/images/sloth.png'
INDEX_TEMPLATE = 'adm/index.html'
LOGIN_IMAGE = '/static/images/sloth.png'
LOGIN_BACKGROUND = None
NAME = 'Admin'
DESCRIPTION = None
CSS = []
JS = []
