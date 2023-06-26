from functools import lru_cache
from django.apps import apps


class OpenApi(dict):
    def __init__(self, request, *args, **kwargs):
        self.apps = {'': []}
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
                        'Token': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'},
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

        selected_app_label = self.request.GET.get('app', '')
        if selected_app_label:
            selected_model_name = self.request.GET.get('model', self.apps[selected_app_label][0][0])
            for app_label, app_config in ordered_app_config_items:
                if selected_app_label == app_label:
                    for model in app_config.get_models():
                        model_name = model.metaclass().model_name
                        if selected_model_name == model_name:
                            self.contribute(app_label, model.get_api_info())
                    self['tags'].append(dict(name=app_label))
        elif self.request.GET.get('app') == '' or not self.request.GET:
            from sloth.actions import ACTIONS
            from sloth.api.dashboard import Dashboards
            form_cls = ACTIONS['login']
            self.contribute('', {'/api/dashboard/login/': [('post', 'Login', 'Login', {'type': 'string'}, form_cls)]})
            self.contribute(selected_app_label, Dashboards(self.request).get_api_info())
            self.contribute('', {'/api/dashboard/logout/': [('get', 'Logout', 'Logout', {'type': 'string'}, None)]})

    def contribute(self, app_label, info):
        paths = {}
        for url, data in info.items():
            paths[url] = {}
            for method, summary, description, schema, form_cls in data:
                body = []
                params = []
                if '{id}' in url:
                    params.append(
                        {'description': 'Identificador', 'name': 'id', 'in': 'path', 'required': True,
                         'schema': dict(type='integer')}
                    )
                if '{ids}' in url:
                    params.append(
                        {'description': 'Identificadores', 'name': 'ids', 'in': 'path', 'required': True,
                         'schema': dict(type='string')}
                    )
                if form_cls:
                    form = form_cls(request=self.request)
                    form.load_fieldsets()
                    if form_cls.__name__ == 'FilterForm':
                        params.append(
                            {'description': 'Palavras-chaves', 'name': 'q', 'in': 'query', 'required': False,
                             'schema': dict(type='string')}
                        )
                        params.extend(form.get_api_params())
                    else:
                        body = form.get_api_params()
                paths[url][method] = {
                    'summary': summary,
                    'description': description,
                    'parameters': params,
                    'requestBody': {
                        'content': {
                            'application/{}'.format(x): {
                                'schema': {
                                    'type': 'object',
                                    'properties': {param['name']: {
                                        'description': param['description'],
                                        'type': param['schema']['type']
                                    } for param in body},
                                    'required': [param['name'] for param in body if param['required']]
                                }
                            } for x in ['x-www-form-urlencoded', 'json']
                        }
                    } if body else None,
                    'responses': {
                        '200': {'description': 'OK', 'content': {'application/json': {'schema': schema}}}
                    },
                    'tags': [app_label],
                    'security': [dict(OAuth2=[], BasicAuth=[], Token=[])]  # , BearerAuth=[], ApiKeyAuth=[]
                }
        self['paths'].update(paths)
