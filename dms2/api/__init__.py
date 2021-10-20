from django.apps import apps


class OpenApi(dict):
    def __init__(self, request, *args, **kwargs):
        self.apps = {}
        self.scopes = []
        self.request = request
        super().__init__(*args, **kwargs)

        self.update({
            'openapi': '3.0.0',
            'servers': [
                {'url': 'http://localhost:8000', 'description': 'Desenvolvimento'}
            ],
            'components':
                {
                    'securitySchemes': {
                        'BasicAuth': {'type': 'http', 'scheme': 'basic'},
                        'OAuth2': {
                            'type': 'oauth2', 'flows': {
                                'authorizationCode': {
                                    'authorizationUrl': '/o/authorize/', 'tokenUrl': '/o/token/', 'scopes': []
                                },
                                'password': {
                                    'tokenUrl': '/o/token/', 'scopes': []
                                },
                                'clientCredentials': {'tokenUrl': '/o/token/', 'scopes': []}
                            }
                        }
                    }
                },
            'tags': [],
            'paths': {}
        })
        self.load()

    def load(self):
        for app_label, app_config in apps.app_configs.items():
            if app_label in ('contenttypes', 'sessions', 'messages', 'staticfiles', 'oauth2_provider'):
                continue
            if self.request.GET.get('app') and self.request.GET['app'] != app_label:
                continue
            api_models = []
            for model in app_config.get_models():
                model_name = model._meta.model_name
                verbose_name = model._meta.verbose_name
                if self.request.GET.get('model') and self.request.GET['model'] != model_name:
                    continue
                api_models.append((model_name, verbose_name))
                url = '/api/{}/{}'.format(app_label, model_name)
                self['paths'][url] = {
                    'get': {
                        'summary': 'Returns a list of users.',
                        'description': 'Optional extended description in CommonMark or HTML.',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {'type': 'array', 'items': {'type': 'string'}}
                                    }
                                }
                            }
                        },
                        'tags': [app_label],
                        'security': [dict(OAuth2=[], BasicAuth=[])]  # , BearerAuth=[], ApiKeyAuth=[]
                    }
                }
            if api_models:
                self['tags'].append(dict(name=app_label))
                self.apps[app_label] = api_models
