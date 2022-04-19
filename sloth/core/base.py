from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string

from sloth.actions import Action
from sloth.core.values import ValueSet
from sloth.core.query import QuerySet

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

    def has_view_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('view', 'admin'))

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    def has_add_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('add', 'admin'))

    def has_edit_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('edit', 'admin'))

    def has_delete_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('delete', 'admin'))

    def has_list_permission(self, user):
        return user.is_superuser or user.roles.contains(*self.get_permission_roles('list', 'admin'))

    def values(self, *names):
        return ValueSet(self, names)

    def view(self):
        names = [field.name for field in self.metaclass().fields]
        return self.values(*names)

    def show(self, *names):
        if 'self' in names:
            return self.view()
        return self.values(*names)

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
            return render_to_string('adm/select.html', dict(obj=self, values=values))
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
                    return self.instance.has_add_permission(user)

            return Add
        return form_cls

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
                        return self.instance.has_edit_permission(user)

                return Edit
        return form_cls

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

            def save(self):
                self.instance.delete()

            def has_permission(self, user):
                return self.instance.has_delete_permission(user)

        return Delete

    @classmethod
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
                    if name.lower() == action.lower():
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
    def get_attr_verbose_name(cls, lookup):
        field = cls.get_field(lookup)
        if field:
            return str(getattr(field, 'verbose_name', lookup)), True
        attr = getattr(cls, lookup)
        return getattr(attr, '__verbose_name__', lookup), False

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
        url = '/api/{}/{}/'.format(cls.metaclass().app_label, cls.metaclass().model_name)

        info = dict()
        # info[url] = [('get', 'List', 'List objects', {'type': 'string'}, None)]
        info['{}{{id}}/'.format(url)] = [
            ('get', 'View', 'View object', instance.view().get_api_schema(), None),
            # ('post', 'Add', 'Add object', {'type': 'string'}, cls.add_form_cls()),
            # ('put', 'Edit', 'Edit object', {'type': 'string'}, None),
        ]
        for name, attr in cls.__dict__.items():
            if hasattr(attr, 'decorated'):
                try:
                    v = getattr(instance, name)()
                except BaseException as e:
                    continue
                info['{}{{id}}/{}/'.format(url, name)] = [
                    ('get', attr.verbose_name, 'View {}'.format(attr.verbose_name), {'type': 'string'}, None),
                ]
                if isinstance(v, ValueSet):
                    for action in v.metadata['actions']:
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), v.get_api_schema(), None),
                        ]
                elif isinstance(v, QuerySet):
                    for action in v.metadata['actions']:
                        forms_cls = cls.action_form_cls(action)
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), {'type': 'string'}, forms_cls),
                        ]

        paths = {}
        for url, data in info.items():
            paths[url] = {}
            for method, summary, description, schema, form_cls in data:
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
                    params.extend(form.get_api_params())
                paths[url][method] = {
                    'summary': summary,
                    'description': description,
                    'parameters': params,
                    'responses': {
                        '200': {'description': 'OK', 'content': {'application/json': {'schema': schema}}}
                    },
                    'tags': [cls.metaclass().app_label],
                    'security': [dict(OAuth2=[], BasicAuth=[])]  # , BearerAuth=[], ApiKeyAuth=[]
                }
        return paths

    @classmethod
    def metaclass(cls):
        return getattr(cls, '_meta')

    def get_role_tuples(self):
        content_type = apps.get_model('contenttypes', 'ContentType')
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
                        scope_type = content_type.objects.get_for_model(
                            model if lookup == 'id' else model.get_field(lookup).related_model
                        )
                        scope_value = value[lookup]
                        tuples.add((value[role['username']], role['name'], scope_type.id, scope_key, scope_value))
        return tuples

    def sync_roles(self, role_tuples):
        from django.contrib.auth.models import User
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
                if user_id is None:
                    user = User.objects.create(username=username)
                    user.set_password('123')
                    user.save()
                    user_id = user.id
                role.objects.get_or_create(
                    user_id=user_id, name=name, scope_type_id=scope_type, scope_key=scope_key, scope_value=scope_value
                )
        deleted_role_tuples = role_tuples - role_tuples2
        # print('DELETED: ', deleted_role_tuples)
        for username, name, scope_type, scope_key, scope_value in deleted_role_tuples:
            role.objects.filter(
                user__username=username, name=name, scope_type=scope_type, scope_key=scope_key, scope_value=scope_value
            ).delete()
