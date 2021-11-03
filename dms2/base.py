from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db.models import OneToOneField
from .forms import ModelForm, QuerySetForm
from .values import ValueSet
from .query import QuerySet

FILTER_FIELD_TYPES = 'BooleanField', 'NullBooleanField', 'ForeignKey', 'ForeignKeyPlus', 'DateField', 'DateFieldPlus'
SEARCH_FIELD_TYPES = 'CharField', 'CharFieldPlus', 'TextField'


class ModelMixin(object):

    def init_one_to_one_fields(self):
        for field in self.metaclass().fields:
            if isinstance(field, OneToOneField):
                if getattr(self, '{}_id'.format(field.name)) is None:
                    setattr(self, field.name, field.related_model())

    def get_one_to_one_field_names(self):
        names = []
        for field in self.metaclass().fields:
            if isinstance(field, OneToOneField):
                names.append(field.name)
        return names

    def has_view_permission(self, user):
        return self and user.is_superuser

    def has_attr_view_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    def has_add_permission(self, user):
        return self and user.is_superuser

    def has_edit_permission(self, user):
        return self and user.is_superuser

    def has_delete_permission(self, user):
        return self and user.is_superuser

    def values(self, *names):
        return ValueSet(self, names)

    def view(self):
        return self.values(*[field.name for field in self.metaclass().fields])

    def serialize(self, wrap=True, verbose=True):
        return self.view().serialize(wrap=wrap, verbose=verbose)

    def get_absolute_url(self, prefix=''):
        return '{}/{}/{}/{}/'.format(prefix, self.metaclass().app_label, self.metaclass().model_name, self.pk)

    def __str__(self):
        return '{} #{}'.format(self.metaclass().verbose_name, self.pk)

    def check_attr_access(self, attr_name, user):
        if attr_name.startswith('get_'):
            attr_name = 'can_{}'.format(attr_name)
        else:
            attr_name = 'can_view_{}'.format(attr_name)
        if hasattr(self, attr_name):
            return getattr(self, attr_name)(user)
        return user.is_superuser

    @classmethod
    def add_form_cls(cls):
        form_cls = cls.action_form_cls('{}Form'.format(cls.__name__))

        class Add(form_cls or ModelForm):
            class Meta:
                model = cls
                exclude = ()
                name = 'Cadastrar {}'.format(cls.metaclass().verbose_name)
                icon = 'plus'
                style = 'success'

            def process(self):
                self.save()
                self.notify('Cadastro realizado com sucesso')

            def has_permission(self):
                return self.instance.has_add_permission(self.request.user)

        return Add

    @classmethod
    def edit_form_cls(cls, inline=False):
        form_cls = cls.action_form_cls('{}Form'.format(cls.__name__))

        class Edit(QuerySetForm if inline else (form_cls or ModelForm)):
            class Meta:
                model = cls
                exclude = ()
                name = 'Editar {}'.format(cls.metaclass().verbose_name)
                icon = 'pencil'
                style = 'primary'

            def process(self):
                self.save()
                self.notify('Edição realizada com sucesso')

            def has_permission(self):
                return self.instance.has_edit_permission(self.request.user)

        return Edit

    @classmethod
    def delete_form_cls(cls, inline=False):

        class Delete(QuerySetForm if inline else ModelForm):
            class Meta:
                model = cls
                fields = ()
                name = 'Excluir {}'.format(cls.metaclass().verbose_name)
                icon = 'x'
                style = 'danger'

            def process(self):
                self.instance.delete()
                self.notify('Exclusão realizada com sucesso')

            def has_permission(self):
                return self.instance.has_delete_permission(self.request.user)

        return Delete

    @classmethod
    def action_form_cls(cls, action):
        if action.lower() == 'add':
            return cls.add_form_cls()
        elif action.lower() == 'edit':
            return cls.edit_form_cls()
        elif action.lower() == 'delete':
            return cls.delete_form_cls()
        elif action.lower() == 'edit-inline':
            return cls.edit_form_cls(inline=True)
        elif action.lower() == 'delete-inline':
            return cls.delete_form_cls(inline=True)
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
    def default_list_fields(cls):
        return [field.name for field in cls.metaclass().fields[0:5] if field.name != 'id']

    @classmethod
    def default_filter_fields(cls, exclude=None):
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
    def get_api_paths(cls):
        instance = cls()
        instance.init_one_to_one_fields()
        url = '/api/{}/{}/'.format(cls.metaclass().app_label, cls.metaclass().model_name)

        info = dict()
        info[url] = [('get', 'List', 'List objects', {'type': 'string'})]
        info['{}{{id}}/'.format(url)] = [
            ('get', 'View', 'View object', {'type': 'string'}),
            ('post', 'Add', 'Add object', {'type': 'string'}),
            ('put', 'Edit', 'Edit object', {'type': 'string'}),
        ]
        for name, attr in cls.__dict__.items():
            if hasattr(attr, 'decorated'):
                v = getattr(instance, name)()
                info['{}{{id}}/{}/'.format(url, name)] = [
                    ('get', attr.verbose_name, 'View {}'.format(attr.verbose_name), {'type': 'string'}),
                ]
                if isinstance(v, ValueSet):
                    for action in v.metadata['actions']:
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), {'type': 'string'}),
                        ]
                elif isinstance(v, QuerySet):
                    for action in v.metadata['actions']:
                        info['{}{{id}}/{}/{{ids}}/{}/'.format(url, name, action)] = [
                            ('post', action, 'Execute {}'.format(action), {'type': 'string'}),
                        ]

        paths = {}
        for url, data in info.items():
            paths[url] = {}
            for method, summary, description, schema in data:
                paths[url][method] = {
                    'summary': summary,
                    'description': description,
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
