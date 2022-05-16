from functools import lru_cache
import types
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string

from sloth.actions import Action
from sloth.core.valueset import ValueSet
from sloth.core.queryset import QuerySet
from sloth.utils import to_snake_case, to_camel_case

FILTER_FIELD_TYPES = 'BooleanField', 'NullBooleanField', 'ForeignKey', 'ForeignKeyPlus', 'DateField', 'DateFieldPlus'
SEARCH_FIELD_TYPES = 'CharField', 'CharFieldPlus', 'TextField'


class ModelMixin(object):

    def init_one_to_one_fields(self):
        for field in self.metaclass().fields:
            if getattr(field, 'one_to_one', False):
                if getattr(self, '{}_id'.format(field.name)) is None:
                    setattr(self, field.name, field.related_model())

    def get_one_to_one_field_names(self):
        names = []
        for field in self.metaclass().fields:
            if getattr(field, 'one_to_one', False):
                names.append(field.name)
        return names

    def get_one_to_many_field_names(self):
        names = []
        for field in self.metaclass().many_to_many:
            if getattr(field, 'one_to_many', False):
                names.append(field.name)
        return names

    @classmethod
    def get_permission_roles(cls, *names):
        roles = []
        if hasattr(cls, 'Permission'):
            for name in names:
                value = getattr(cls.Permission, name, ())
                if value and not isinstance(value, tuple):
                    raise RuntimeError(
                        'The value for "{}" in the Permission class for "{}" must be a tuple'.format(name, cls.__name__)
                    )
                roles.extend(value)
        return roles

    def has_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('admin'))

    def has_view_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('view')) or self.has_permission(user)

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return  attr is None or user.is_superuser or attr(user)

    def has_fieldset_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        if attr:
            return attr(user)
        return self.is_view_fieldset(name) and (self.has_permission(user) or self.has_view_permission(user))

    def is_view_fieldset(self, name):
        if not hasattr(self.__class__, '__view__'):
            attr_names = []
            def append_attr_names(valueset):
                names = list(valueset.metadata['names'].keys())
                names.extend(valueset.metadata['append'])
                names.extend(valueset.metadata['attach'])
                # if all names starts with "get_" it is certainly a fieldset list or fieldset group
                if all([attr_name.startswith('get_') for attr_name in names]):
                    for attr_name in names:
                        attr_names.append(attr_name)
                        attr = getattr(self, attr_name)()
                        if isinstance(attr, ValueSet):
                            append_attr_names(attr)
            append_attr_names(self.view())
            setattr(self.__class__, '__view__', attr_names)
        return name in getattr(self.__class__, '__view__')

    def has_add_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('add')) or self.has_permission(user)

    def has_edit_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('edit')) or self.has_permission(user)

    def has_delete_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('delete')) or self.has_permission(user)

    def has_list_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('list')) or self.has_permission(user)

    def values(self, *names):
        return ValueSet(self, names)

    def view(self):
        names = [field.name for field in self.metaclass().fields]
        return self.values(*names)

    def show(self, name):
        if isinstance(name, str):
            return self.values(name)
        return self.view()

    def serialize(self, wrap=True, verbose=True):
        return self.view().serialize(wrap=wrap, verbose=verbose)

    @classmethod
    def get_list_url(cls, prefix=''):
        return '{}/{}/{}/'.format(prefix, cls.metaclass().app_label, cls.metaclass().model_name)

    def get_absolute_url(self, prefix=''):
        return '{}/{}/{}/{}/'.format(prefix, self.metaclass().app_label, self.metaclass().model_name, self.pk)

    def get_select_display(self):
        select_fields = getattr(type(self).metaclass(), 'select_fields', None)
        if select_fields:
            values = []
            for attr_name in select_fields:
                values.append(getattr(self, attr_name))
            return render_to_string('app/select.html', dict(obj=self, values=values))
        return None

    def __str__(self):
        return '{} #{}'.format(self.metaclass().verbose_name, self.pk)

    @classmethod
    def add_form_cls(cls):
        form_cls = cls.action_form_cls('Add{}'.format(cls.__name__))
        if form_cls is None:
            class Add(Action):
                class Meta:
                    model = cls
                    verbose_name = 'Cadastrar {}'.format(cls.metaclass().verbose_name)
                    icon = 'plus'
                    style = 'success'
                    submit_label = 'Cadastrar'
                    if hasattr(cls.metaclass(), 'fieldsets'):
                        fieldsets = cls.metaclass().fieldsets

                def has_permission(self, user):
                    return self.instance.has_add_permission(user) or self.instance.has_permission(user)
            return Add

        class Add(form_cls):
            class Meta(form_cls.Meta):
                verbose_name = getattr(
                    form_cls.Meta, 'verbose_name', 'Cadastrar {}'.format(cls.metaclass().verbose_name)
                )
        return Add

    @classmethod
    def edit_form_cls(cls):
        form_cls = cls.action_form_cls('Edit{}'.format(cls.__name__))
        if form_cls is None:
            form_cls = cls.action_form_cls('Add{}'.format(cls.__name__))
            if form_cls is None:
                class Edit(Action):
                    class Meta:
                        model = cls
                        verbose_name = 'Editar {}'.format(cls.metaclass().verbose_name)
                        submit_label = 'Editar'
                        icon = 'pencil'
                        style = 'primary'
                        if hasattr(cls.metaclass(), 'fieldsets'):
                            fieldsets = cls.metaclass().fieldsets

                    def has_permission(self, user):
                        return self.instance.has_edit_permission(user) or self.instance.has_permission(user)
                return Edit

        class Edit(form_cls):
            class Meta(form_cls.Meta):
                verbose_name = getattr(
                    form_cls.Meta, 'verbose_name', 'Editar {}'.format(cls.metaclass().verbose_name)
                )
        return Edit

    @classmethod
    def delete_form_cls(cls):

        class Delete(Action):
            class Meta:
                model = cls
                fields = ()
                verbose_name = 'Excluir {}'.format(cls.metaclass().verbose_name)
                icon = 'x'
                style = 'danger'
                submit_label = 'Excluir'
                confirmation = True

            def save(self):
                self.instance.delete()

            def has_permission(self, user):
                return self.instance.has_delete_permission(user) or self.instance.has_permission(user)

        return Delete

    @classmethod
    @lru_cache
    def action_form_cls(cls, action):
        if action.lower() == 'add':
            return cls.add_form_cls()
        elif action.lower() == 'edit':
            return cls.edit_form_cls()
        elif action.lower() == 'delete':
            return cls.delete_form_cls()
        else:
            config = apps.get_app_config(cls.metaclass().app_label)
            try:
                forms = __import__(
                    '{}.actions'.format(config.module.__package__),
                    fromlist=config.module.__package__.split()
                )
                for name in dir(forms):
                    if name.lower() == to_camel_case(action).lower():
                        return getattr(forms, name)
            except ModuleNotFoundError:
                pass
            return None

    @classmethod
    def get_field(cls, lookup):
        model = cls
        attrs = lookup.split('__')
        while attrs:
            attr_name = attrs.pop(0)
            if attrs:  # go deeper
                field = model.metaclass().get_field(attr_name)
                model = field.related_model
            else:
                try:
                    return model.metaclass().get_field(attr_name)
                except FieldDoesNotExist:
                    pass
        return None

    @classmethod
    def default_list_per_page(cls):
        return getattr(cls.metaclass(), 'list_per_page', 10)

    @classmethod
    def default_list_fields(cls):
        list_display = getattr(cls.metaclass(), 'list_display', None)
        return list_display or [field.name for field in cls.metaclass().fields[0:5] if field.name != 'id']

    @classmethod
    def default_filter_fields(cls, exclude=None):
        filters = getattr(cls.metaclass(), 'list_filter', None)
        if filters is None:
            filters = []
            for field in cls.metaclass().fields:
                cls_name = type(field).__name__
                if cls_name in FILTER_FIELD_TYPES:
                    if field.name != exclude:
                        filters.append(field.name)
                elif field.choices:
                    if field.name != exclude:
                        filters.append(field.name)
        return filters

    @classmethod
    def default_search_fields(cls):
        search = []
        for field in cls.metaclass().fields:
            cls_name = type(field).__name__
            if cls_name in SEARCH_FIELD_TYPES:
                search.append(field.name)
        return search

    @classmethod
    def get_attr_metadata(cls, lookup):
        field = cls.get_field(lookup)
        if field:
            return str(getattr(field, 'verbose_name', lookup)), True, None
        attr = getattr(cls, lookup)
        template = getattr(attr, '__template__', None)
        if template and not template.endswith('.html'):
            template = '{}.html'.format(template)
        return getattr(attr, '__verbose_name__', lookup), False, template

    @classmethod
    def get_attr_api_type(cls, lookup):
        from django.db import models
        param_type = 'string'
        param_format = None
        field = cls.get_field(lookup)
        if field:
            if isinstance(field, models.BooleanField):  # controller field
                param_type = 'boolean'
            elif isinstance(field, models.DateTimeField):
                param_format = 'date-time'
            elif isinstance(field, models.DateField):
                param_format = 'date'
            elif isinstance(field, models.IntegerField) or isinstance(field, models.ForeignKey):
                param_type = 'integer'
                param_format = 'int32'
        return dict(type=param_type, format=param_format)

    @classmethod
    def get_api_paths(cls, request):
        instance = cls()
        instance.id = -1
        instance.init_one_to_one_fields()
        app_label = cls.metaclass().app_label
        if app_label == 'api':
            url = '/api/{}/'.format(cls.metaclass().model_name)
        else:
            url = '/api/{}/{}/'.format(app_label, cls.metaclass().model_name)
        info = dict()
        info[url] = [
            ('get', 'List', 'List objects', {'type': 'string'}, cls.objects.all().filter_form_cls()),
            ('post', 'Add', 'Add object', {'type': 'string'}, cls.add_form_cls())
        ]
        info['{}{{id}}/'.format(url)] = [
            ('get', 'View', 'View object', instance.view().get_api_schema(), None),
            ('put', 'Edit', 'Edit object', {'type': 'string'}, cls.edit_form_cls()),
            ('delete', 'Delete', 'Delete object', {'type': 'string'}, None),
        ]

        def find_endpoints(valueset):
            for name in valueset.metadata['names']:
                try:
                    attr = getattr(instance, name)
                except BaseException:
                    continue
                if isinstance(attr, types.MethodType):
                    v = attr()
                    info['{}{{id}}/{}/'.format(url, name)] = [
                        ('get', name, 'View {}'.format(name), {'type': 'string'}, None),
                    ]
                    if isinstance(v, ValueSet):
                        for action in v.metadata['actions']:
                            forms_cls = cls.action_form_cls(action)
                            info['{}{{id}}/{}/{}/'.format(url, name, to_snake_case(action))] = [
                                ('post', action, 'Execute {}'.format(action), v.get_api_schema(), forms_cls),
                            ]
                        if v.has_children():
                            find_endpoints(v)
                    elif isinstance(v, QuerySet):
                        for action in v.metadata['global_actions']:
                            forms_cls = cls.action_form_cls(action)
                            info['{}{{id}}/{}/{}/'.format(url, name, to_snake_case(action))] = [
                                ('post', action, 'Execute {}'.format(action), {'type': 'string'}, forms_cls),
                            ]
                        for action in v.metadata['actions']:
                            forms_cls = cls.action_form_cls(action)
                            info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, to_snake_case(action))] = [
                                ('post', action, 'Execute {}'.format(action), {'type': 'string'}, forms_cls),
                            ]
                        for action in v.metadata['batch_actions']:
                            forms_cls = cls.action_form_cls(action)
                            info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, to_snake_case(action))] = [
                                ('post', action, 'Execute {}'.format(action), {'type': 'string'}, forms_cls),
                            ]

        find_endpoints(cls().view())

        paths = {}
        for url, data in info.items():
            paths[url] = {}
            for method, summary, description, schema, form_cls in data:
                body = []
                params = []
                if '{id}' in url:
                    params.append(
                        {'description': 'Identificador', 'name': 'id', 'in': 'path', 'required': True, 'schema': dict(type='integer')}
                    )
                if '{ids}' in url:
                    params.append(
                        {'description': 'Identificadores', 'name': 'ids', 'in': 'path', 'required': True, 'schema': dict(type='string')}
                    )
                if form_cls:
                    form = form_cls(request=request)
                    form.load_fieldsets()
                    if form_cls.__name__ == 'FilterForm':
                        params.extend(form.get_api_params())
                    else:
                        body = form.get_api_params()
                paths[url][method] = {
                    'summary': summary,
                    'description': description,
                    'parameters': params,
                    'requestBody': {
                        'content': {
                            'application/x-www-form-urlencoded': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {param['name']: {
                                        'description': param['description'],
                                        'type': param['schema']['type']
                                    } for param in body},
                                    'required': [param['name'] for param in body if param['required']]
                                }
                            }
                        }
                    } if body else None,
                    'responses': {
                        '200': {'description': 'OK', 'content': {'application/json': {'schema': schema}}}
                    },
                    'tags': [app_label],
                    'security': [dict(OAuth2=[], BasicAuth=[])]  # , BearerAuth=[], ApiKeyAuth=[]
                }
        return paths

    @classmethod
    def metaclass(cls):
        return getattr(cls, '_meta')

    def get_role_tuples(self):
        model = type(self)
        tuples = set()
        for role in self.__roles__:
            lookups = list()
            lookups.append(role['username'])
            if model.__name__.lower() not in role['scopes']:
                role['scopes'][model.__name__.lower()] = 'id'
            lookups.extend(role['scopes'].values())
            values = model.objects.filter(pk=self.pk).values(*set(lookups))
            for value in values:
                if value[role['username']]:
                    for scope_key, lookup in role['scopes'].items():
                        scope_type = model if lookup in ('id', 'pk') else model.get_field(lookup).related_model
                        scope_value = value[lookup]
                        tuples.add((value[role['username']], role['name'], scope_type, scope_key, scope_value))
        return tuples

    def sync_roles(self, role_tuples):
        from django.contrib.auth.models import User
        user_id = None
        role = apps.get_model('api', 'Role')
        role_tuples2 = self.get_role_tuples()
        # for x in role_tuples: print(x)
        # print('\n')
        # for x in role_tuples2: print(x)
        # print('\n\n')
        added_role_tuples = role_tuples2 - role_tuples
        # print('ADDED: ', added_role_tuples)
        for username, name, scope_type, scope_key, scope_value in role_tuples2:
            if scope_value:
                user_id = User.objects.filter(username=username).values_list('id', flat=True).first()
                scope_type = '{}.{}'.format(scope_type.metaclass().app_label, scope_type.metaclass().model_name)
                if user_id is None:
                    user = User.objects.create(username=username)
                    user.set_password('123')
                    user.save()
                    user_id = user.id
                role.objects.get_or_create(
                    user_id=user_id, name=name,
                    scope_type=scope_type,
                    scope_key=scope_key, scope_value=scope_value
                )
        deleted_role_tuples = role_tuples - role_tuples2
        # print('DELETED: ', deleted_role_tuples)
        for username, name, scope_type, scope_key, scope_value in deleted_role_tuples:
            if user_id is None:
                user_id = User.objects.filter(username=username).values_list('id', flat=True).first()
            scope_type = '{}.{}'.format(scope_type.metaclass().app_label, scope_type.metaclass().model_name)
            role.objects.filter(
                user_id=user_id, name=name, scope_type=scope_type, scope_key=scope_key, scope_value=scope_value
            ).delete()
