LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Recife'

USE_I18N = True

USE_L10N = True

USE_TZ = False

OAUTH2_PROVIDER_APPLICATION_MODEL = 'dms2.Application'

OAUTH2_PROVIDER = {
    'SCOPES_BACKEND_CLASS': 'dms2.backends.Scopes'
}
