from functools import lru_cache
from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.template.loader import render_to_string

from sloth.actions import Action, ACTIONS
from sloth.core.valueset import ValueSet
from sloth.core.queryset import QuerySet
from sloth.utils import to_snake_case, to_camel_case, getattrr

FILTER_FIELD_TYPES = 'BooleanField', 'NullBooleanField', 'ForeignKey', 'ForeignKeyPlus', 'DateField', 'DateFieldPlus'
SEARCH_FIELD_TYPES = 'CharField', 'CharFieldPlus', 'TextField'


class ModelMixin(object):

    ### ROLE CREATION ###

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

    ### PERMISSIONS ###

    def role_lookups(self, *names, **scopes):
        from sloth import RoleLookup
        return RoleLookup(self).role_lookups(*names, **scopes)

    def has_permission(self, user):
        return user.is_superuser

    def has_view_permission(self, user):
        return user.is_superuser or self.has_permission(user) or self.is_autouser(user)

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or user.is_superuser or attr(user)

    def has_view_attr_permission(self, user, name):
        has_permission = False
        if user.is_superuser or self.has_permission(user):
            has_permission = True
        if self.is_view_attr(name) and self.has_view_permission(user):
            has_permission = True
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr(user) if attr else has_permission

    def is_view_attr(self, name):
        if not hasattr(self.__class__, '__view__'):
            attr_names = []

            def append_attr_names(valueset):
                names = list(valueset.metadata['names'].keys())
                names.extend(valueset.metadata['append'])
                names.extend(valueset.metadata['attach'])
                # if all names starts with "get_" it is certainly a fieldset list or fieldset group
                # if all([attr_name.startswith('get_') for attr_name in names]):
                if valueset.has_children():
                    for attr_name in names:
                        attr_names.append(attr_name)
                        if hasattr(self, attr_name):
                            attr = getattr(self, attr_name)()
                            if isinstance(attr, ValueSet):
                                append_attr_names(attr)
            append_attr_names(self.view())
            setattr(self.__class__, '__view__', attr_names)
        return name in getattr(self.__class__, '__view__')

    def has_add_permission(self, user):
        return user.is_superuser or self.has_permission(user) or (hasattr(self, 'autouser') and self.is_autouser(user))

    def has_edit_permission(self, user):
        return user.is_superuser or self.has_permission(user) or self.is_autouser(user)

    def has_delete_permission(self, user):
        return user.is_superuser or self.has_permission(user) or self.is_autouser(user)

    def is_autouser(self, user):
        return getattr(self, 'autouser', None) == user

    ### VISUALIZATION ###

    def value_set(self, *names):
        return ValueSet(self, names)

    def view(self, *names):
        names = names or [field.name for field in self.metaclass().fields]
        return self.value_set(*names)

    def serialize(self, wrap=True):
        return self.view().serialize(wrap=wrap)

    def get_select_display(self):
        select_fields = getattr(type(self).metaclass(), 'select_fields', None)
        if select_fields:
            values = []
            for attr_name in select_fields:
                values.append(getattr(self, attr_name))
            return render_to_string('inputs/select.html', dict(obj=self, values=values))
        return None

    ### ROLE CREATION ###

    def get_role_tuples(self, ignore_active_condition=False):
        model = type(self)
        tuples = set()
        for role in self.__roles__:
            if ignore_active_condition or role['active'] is None or getattrr(self, role['active'])[1]:
                lookups = list()
                lookups.append(role['username'])
                if role['email']:
                    lookups.append(role['email'])
                lookups.extend(role['scopes'].values())
                if role['name'].islower():
                    lookups.append(role['name'])
                values = model.objects.filter(pk=self.pk).values(*set(lookups))
                for value in values:
                    username = value[role['username']]
                    email = value[role['email']] if role['email'] else None
                    if username:
                        scope_name = value[role['name']] if role['name'].islower() else role['name']
                        if not role['scopes']:
                            tuples.add((username, email, scope_name, None, None, None))
                        for scope_key, lookup in role['scopes'].items():
                            scope_type = model if lookup in ('pk', 'id', 'self') else model.get_field(lookup).related_model
                            scope_value = value[lookup]
                            tuples.add((username, email, scope_name, scope_type, scope_key, scope_value))
                    # else:
                    #     raise ValidationError('O "login" do usuário ({}) deve ser informado.'.format(role['username'].upper().replace('__', '->')))
        # print('----- {} -----'.format(self))
        # for x in tuples: print(x)
        # print('\n\n')
        return tuples

    def sync_roles(self, role_tuples):
        from django.contrib.auth.models import User
        role = apps.get_model('api', 'Role')
        role_tuples2 = self.get_role_tuples()
        for username, email, scope_name, scope_type, scope_key, scope_value in role_tuples2:
            if username:
                user_id = User.objects.filter(username=username).values_list('id', flat=True).first()
                if user_id is None:
                    user = User.objects.create(username=username)
                    if email:
                        user.email = email
                    default_password = settings.DEFAULT_PASSWORD(user)
                    user.set_password(default_password)
                    user.save()
                    user_id = user.id
                role.objects.get_or_create(
                    user_id=user_id, name=scope_name,
                    scope_type='{}.{}'.format(
                        scope_type.metaclass().app_label, scope_type.metaclass().model_name
                    ) if scope_type else None,
                    scope_key=scope_key, scope_value=scope_value
                )
        deleted_role_tuples = role_tuples - role_tuples2
        # print('DELETED: ', deleted_role_tuples)
        for username, email, scope_name, scope_type, scope_key, scope_value in deleted_role_tuples:
            if scope_type:
                scope_type = '{}.{}'.format(scope_type.metaclass().app_label, scope_type.metaclass().model_name)
                role.objects.filter(
                    user__username=username, name=scope_name, scope_type=scope_type, scope_key=scope_key, scope_value=scope_value
                ).delete()

    @classmethod
    def get_list_url(cls, prefix='', subset='all'):
        url = '{}/dashboard/{}/{}/'.format(prefix, cls.metaclass().app_label, cls.metaclass().model_name)
        if subset != 'all':
            url = '{}{}/'.format(url, subset)
        return url

    @classmethod
    def add_form_cls(cls):
        form_cls = cls.action_form_cls('{}{}'.format('Cadastrar', cls.__name__))
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
                    return user.is_superuser or self.instance.has_add_permission(user) or self.instance.has_permission(user)
            return Add

        class Add(form_cls):
            class Meta(form_cls.Meta):
                verbose_name = getattr(
                    form_cls.Meta, 'verbose_name', 'Cadastrar {}'.format(cls.metaclass().verbose_name)
                )
                icon = getattr(form_cls.Meta, 'icon', 'plus')
                style = getattr(form_cls.Meta, 'style', 'success')
                submit_label = getattr(form_cls.Meta, 'submit_label', 'Cadastrar')

            def has_permission(self, user):
                return user.is_superuser or form_cls.has_permission(self, user) or self.instance.has_add_permission(user) or self.instance.has_permission(user)
        return Add

    @classmethod
    def edit_form_cls(cls):
        form_cls = cls.action_form_cls('Editar{}'.format(cls.__name__))
        if form_cls is None:
            class Edit(Action):
                class Meta:
                    model = cls
                    verbose_name = 'Editar {}'.format(cls.metaclass().verbose_name)
                    submit_label = 'Editar'
                    icon = 'pencil'
                    style = 'primary'
                    if hasattr(cls.metaclass(), 'edit_fieldsets'):
                        fieldsets = cls.metaclass().edit_fieldsets
                    elif hasattr(cls.metaclass(), 'fieldsets'):
                        fieldsets = cls.metaclass().fieldsets

                def has_permission(self, user):
                    return user.is_superuser or self.instance.has_edit_permission(user) or self.instance.has_permission(user)
            return Edit

        class Edit(form_cls):
            class Meta(form_cls.Meta):
                icon = 'pencil'
                submit_label = 'Editar'
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

            def submit(self):
                self.instance.delete()
                self.message('Exclusão realizada com sucesso.')
                self.redirect('..')

            def has_permission(self, user):
                return user.is_superuser or self.instance.has_delete_permission(user) or self.instance.has_permission(user)

        return Delete

    @classmethod
    def relation_form_cls(cls, related_field):
        _related_field = related_field

        class Add(Action):
            class Meta:
                icon = 'plus'
                modal = True
                model = cls.get_field(_related_field).model
                style = 'primary'
                related_field = _related_field
                verbose_name = 'Adicionar {}'.format(cls.get_field(_related_field).model.metaclass().verbose_name)
                fieldsets = getattr(cls.get_field(_related_field).model.metaclass(), 'fieldsets', None)

            def has_permission(self, user):
                return user.is_superuser or self.instantiator.has_edit_permission(user) or self.instantiator.has_permission(user)

        return Add

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
            return ACTIONS.get(action)

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
    def default_list_fields(cls):
        list_display = getattr(cls.metaclass(), 'list_display', None)
        return list_display or [field.name for field in cls.metaclass().fields[0:10] if field.name != 'id' and '_ptr' not in field.name]

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
        metaclass = cls.metaclass()
        search_fields = getattr(metaclass, 'search_fields', ())
        for field in metaclass.fields:
            cls_name = type(field).__name__
            if cls_name in SEARCH_FIELD_TYPES or field.name in search_fields:
                search.append(field.name)

        return search

    @classmethod
    def get_attr_metadata(cls, lookup):
        field = cls.get_field(lookup)
        if field:
            return str(getattr(field, 'verbose_name', lookup)), True, None, None
        attr = getattr(cls, lookup)
        template = getattr(attr, '__template__', None)
        metadata = getattr(attr, '__metadata__', None)
        if template:
            if not template.endswith('.html'):
                template = '{}.html'.format(template)
            if not template.startswith('.html'):
                template = 'renderers/{}'.format(template)
        return getattr(attr, '__verbose_name__', lookup), False, template, metadata

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

    def get_allowed_attrs(self, recursive=True):
        return self.view().get_allowed_attrs()

    @classmethod
    def get_api_info(cls):
        instance = cls(pk=0)
        instance.init_one_to_one_fields()
        app_label = cls.metaclass().app_label
        if app_label == 'api':
            url = '/api/dashboard/{}/'.format(cls.metaclass().model_name)
        else:
            url = '/api/dashboard/{}/{}/'.format(app_label, cls.metaclass().model_name)
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
        info.update(instance.view().get_api_info(url))
        return info

    @classmethod
    def metaclass(cls):
        return getattr(cls, '_meta')

    def contextualize(self, request):
        return self.view().contextualize(request)

    def attr(self, name, source=False):
        valueset = self.value_set(name).attr(name)
        if source:
            valueset = valueset.source(name)
        return valueset
