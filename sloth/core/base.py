from django.apps import apps
from django.core.exceptions import FieldDoesNotExist

from sloth.forms import ModelForm
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

    def can_view(self, user):
        names = getattr(self.metaclass(), 'can_view', ()) + getattr(self.metaclass(), 'can_admin', ())
        return user.is_superuser or user.roles.filter(name__in=names)

    def can_view_attr(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    def can_add(self, user):
        names = getattr(self.metaclass(), 'can_add', ()) + getattr(self.metaclass(), 'can_admin', ())
        return user.is_superuser or user.roles.filter(name__in=names)

    def can_edit(self, user):
        names = getattr(self.metaclass(), 'can_edit', ()) + getattr(self.metaclass(), 'can_admin', ())
        return user.is_superuser or user.roles.filter(name__in=names)

    def can_delete(self, user):
        names = getattr(self.metaclass(), 'can_delete', ()) + getattr(self.metaclass(), 'can_admin', ())
        return user.is_superuser or user.roles.filter(name__in=names)

    @classmethod
    def can_list(cls, user):
        names = getattr(cls.metaclass(), 'can_list', ()) + getattr(cls.metaclass(), 'can_admin', ())
        return user.is_superuser or user.roles.filter(name__in=names)

    def values(self, *names):
        return ValueSet(self, names)

    def view(self):
        names = [field.name for field in self.metaclass().fields]
        return self.values(*names)

    def serialize(self, wrap=True, verbose=True):
        return self.view().serialize(wrap=wrap, verbose=verbose)

    @classmethod
    def get_list_url(cls, prefix=''):
        return '{}/{}/{}/'.format(prefix, cls.metaclass().app_label, cls.metaclass().model_name)

    def get_absolute_url(self, prefix=''):
        return '{}/{}/{}/{}/'.format(prefix, self.metaclass().app_label, self.metaclass().model_name, self.pk)

    def __str__(self):
        return '{} #{}'.format(self.metaclass().verbose_name, self.pk)

    def check_attr_access(self, attr_name, user):
        if attr_name.startswith('get_'):
            attr_name = 'can_{}'.format(attr_name)
        else:
            attr_name = 'can_view_{}'.format(attr_name)
        if not hasattr(self, attr_name) or getattr(self, attr_name)(user):
            return True
        return user.is_superuser

    @classmethod
    def add_form_cls(cls):
        cls_name = getattr(cls.metaclass(), 'add_form', None)
        if cls_name is None:
            cls_name = getattr(cls.metaclass(), 'form', None)
        form_cls = cls.action_form_cls(cls_name) if cls_name else None

        class Add(form_cls or ModelForm):
            class Meta:
                model = cls
                if form_cls and hasattr(form_cls.Meta, 'fields'):
                    fields = form_cls.Meta.fields
                else:
                    exclude = ()
                verbose_name = 'Cadastrar {}'.format(cls.metaclass().verbose_name)
                icon = 'plus'
                style = 'success'
                submit_label = 'Cadastrar'
                if form_cls and hasattr(form_cls.Meta, 'fieldsets'):
                    fieldsets = form_cls.Meta.fieldsets
                elif hasattr(cls.metaclass(), 'fieldsets'):
                    fieldsets = cls.metaclass().fieldsets

            def process(self):
                self.save()
                self.notify('Cadastro realizado com sucesso')

            def can_view(self, user):
                return self.instance.can_add(user)
        return Add

    @classmethod
    def edit_form_cls(cls):
        cls_name = getattr(cls.metaclass(), 'edit_form', None)
        if cls_name is None:
            cls_name = getattr(cls.metaclass(), 'form', None)
        form_cls = cls.action_form_cls(cls_name) if cls_name else None

        class Edit(form_cls or ModelForm):
            class Meta:
                model = cls
                exclude = ()
                verbose_name = 'Editar {}'.format(cls.metaclass().verbose_name)
                submit_label = 'Editar'
                icon = 'pencil'
                style = 'primary'
                if form_cls and hasattr(form_cls.Meta, 'fieldsets'):
                    fieldsets = form_cls.Meta.fieldsets
                elif hasattr(cls.metaclass(), 'fieldsets'):
                    fieldsets = cls.metaclass().fieldsets

            def process(self):
                self.save()
                self.notify('Edição realizada com sucesso')

            def can_view(self, user):
                return self.instance.can_edit(user)

        return Edit

    @classmethod
    def delete_form_cls(cls):

        class Delete(ModelForm):
            class Meta:
                model = cls
                fields = ()
                name = 'Excluir {}'.format(cls.metaclass().verbose_name)
                verbose_name = 'Excluir'
                icon = 'x'
                style = 'danger'
                submit_label = 'Excluir'

            def process(self):
                self.instance.delete()
                self.notify('Exclusão realizada com sucesso')

            def can_view(self, user):
                return self.instance.can_delete(user)

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
            forms = __import__(
                '{}.forms'.format(config.module.__package__),
                fromlist=config.module.__package__.split()
            )
            for name in dir(forms):
                if name.lower() == action.lower():
                    return getattr(forms, name)
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
            return str(field.verbose_name), True
        attr = getattr(cls, lookup)
        return getattr(attr, 'verbose_name', lookup), False

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
        lookups = list()
        tuples = set()
        for role in self._roles:
            lookups.append(role['username'])
            lookups.extend(role['scopes'].values())
        values = model.objects.filter(pk=self.pk).values(*set(lookups)).first()
        if values:
            for role in self._roles:
                username = values[role['username']]
                tuples.add((username, role['name'], None, None, None))
                for scope_key, lookup in role['scopes'].items():
                    scope_type = content_type.objects.get_for_model(
                        model if lookup == 'id' else model.get_field(lookup).related_model
                    )
                    scope_value = values[lookup]
                    tuples.add((username, role['name'], scope_type.id, scope_key, scope_value))
        return tuples

    def sync_roles(self, role_tuples):
        from django.contrib.auth.models import User
        user_id = None
        role = apps.get_model('api', 'Role')
        role_tuples2 = self.get_role_tuples()
        for username, name, scope_type, scope_key, scope_value in role_tuples2:
            if user_id is None:
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
        for user_id, name, scope_type, scope_key, scope_value in deleted_role_tuples:
            role.objects.filter(
                user_id=user_id, name=name, scope_type=scope_type, scope_key=scope_key, scope_value=scope_value
            ).delete()
