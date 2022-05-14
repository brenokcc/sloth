from functools import lru_cache

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

    def ordered_app_config_items(self):
        configs = dict(api=None)
        for app_label, app_config in apps.app_configs.items():
            if app_label not in ('contenttypes', 'sessions', 'messages', 'staticfiles', 'oauth2_provider', 'auth'):
                configs[app_label] = app_config
        return configs.items()

    def load(self):
        ordered_app_config_items = self.ordered_app_config_items()
        for app_label, app_config in ordered_app_config_items:
            api_models = []
            for model in app_config.get_models():
                model_name = model.metaclass().model_name
                verbose_name = model.metaclass().verbose_name
                api_models.append((model_name, verbose_name))
            if api_models:
                self.apps[app_label] = api_models

        selected_app_label = self.request.GET.get('app', 'api')
        selected_model_name = self.request.GET.get('model', self.apps[selected_app_label][0][0])
        for app_label, app_config in ordered_app_config_items:
            if selected_app_label == app_label:
                for model in app_config.get_models():
                    model_name = model.metaclass().model_name
                    if selected_model_name == model_name:
                        self['paths'].update(model.get_api_paths(self.request))
                self['tags'].append(dict(name=app_label))
