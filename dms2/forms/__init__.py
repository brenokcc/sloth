# -*- coding: utf-8 -*-
from copy import deepcopy
from functools import lru_cache
import math
from django.forms import *
from django.forms import fields
from django.forms import widgets
from django.forms import models
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.contrib import auth
from django.template.loader import render_to_string

from ..exceptions import JsonReadyResponseException
from ..utils import load_menu


class FormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.fake:
            self.one_to_one = {}
            self.one_to_many = {}
            self.fieldsets = self.load_fieldsets()
            self.parse_fieldsets()

    def load_fieldsets(self):
        # creates default fieldset if necessary
        fieldsets = getattr(self.Meta, 'fieldsets', None)
        if fieldsets is None:
            if self.instance:
                fieldsets = getattr(self.instance.metaclass(), 'fielsets', None)

        if fieldsets is None:
            fieldsets = {'Dados Gerais': list(self.fields.keys())}
        else:
            fieldsets = dict(fieldsets)

        # extract one-to-one and one-to-many fields
        if self.instance:
            for name in list(self.fields):
                if name in self.instance.get_one_to_one_field_names():
                    # remove one-to-one fields from the form
                    self.one_to_one[name] = self.fields.pop(name)
                if name in self.instance.get_one_to_many_field_names():
                    # remove one-to-many fields from the form
                    self.one_to_many[name] = self.fields.pop(name)

        # configure one-to-one fields
        for one_to_one_field_name, one_to_one_field in self.one_to_one.items():
            field_list = []
            form_cls = one_to_one_field.queryset.model.add_form_cls()
            initial = one_to_one_field.queryset.model.objects.filter(
                pk=getattr(self.instance, '{}_id'.format(one_to_one_field_name))
            ).values(
                *form_cls.base_fields.keys()
            ).first() or {}
            key = one_to_one_field_name.upper()
            self.fields[key] = fields.BooleanField(
                required=one_to_one_field.required, initial=bool(initial)
            )
            self.fields[key].widget.attrs['class'] = 'field-controller'
            for name, field in form_cls.base_fields.items():
                ont_to_one_key = '{}__{}'.format(one_to_one_field_name, name)
                field_list.append(ont_to_one_key)
                field.required = field.required and one_to_one_field.required or self.data.get(
                    one_to_one_field_name.upper()
                )
                field.widget.attrs['class'] = key
                self.fields[ont_to_one_key] = field
                self.initial[ont_to_one_key] = initial.get(name)

            # try to get field organization from form fieldsets if defined
            one_to_one_fieldsets = getattr(form_cls.Meta, 'fieldsets', None)
            if one_to_one_fieldsets is None:
                one_to_one_fieldsets = getattr(form_cls.Meta.model.metaclass(), 'fieldsets', None)
            if one_to_one_fieldsets is not None:
                field_list = []
                for fieldset in one_to_one_fieldsets.values():
                    for names in fieldset:
                        if isinstance(names, str):
                            field_list.append('{}__{}'.format(one_to_one_field_name, names))
                        else:
                            field_list.append(
                                ['{}__{}'.format(one_to_one_field_name, field_name) for field_name in names]
                            )
            field_list.append(one_to_one_field_name.upper())
            fieldsets[one_to_one_field.label] = field_list

        # configure one-to-many fields
        for one_to_many_field_name, one_to_many_field in self.one_to_many.items():
            field_list = []
            form_cls = one_to_many_field.queryset.model.add_form_cls()
            pks = []
            if self.instance.pk:
                pks.extend(getattr(self.instance, one_to_many_field_name).values_list('pk', flat=True))
            pks.extend(['' for _ in range(1, 3)])
            for i, pk in enumerate(pks):
                initial = one_to_many_field.queryset.model.objects.filter(
                    pk=pk
                ).values(
                    *form_cls.base_fields.keys()
                ).first() if pk else {}
                key = '{}--{}'.format(one_to_many_field_name.upper(), i)
                self.fields[key] = fields.CharField(
                    label='{} {}'.format(one_to_many_field.queryset.model.metaclass().verbose_name, i+1),
                    required=False, initial=pk, widget=fields.CheckboxInput()
                )
                self.fields[key].widget.attrs['class'] = 'field-controller'
                field_list.append(key)
                inline_field_list = []
                for name, field in form_cls.base_fields.items():
                    field = deepcopy(field)
                    one_to_many_key = '{}__{}__{}'.format(one_to_many_field_name, name, i)
                    inline_field_list.append(one_to_many_key)
                    field.required = False
                    field.widget.attrs['class'] = key
                    self.fields[one_to_many_key] = field
                    self.initial[one_to_many_key] = initial.get(name)

                field_list.append(inline_field_list)
            fieldsets[one_to_many_field.label] = field_list
        return fieldsets

    def parse_fieldsets(self):
        # configure ordinary fields
        for title, names in self.fieldsets.items():
            field_list = []
            for name in names:
                if isinstance(name, tuple) or isinstance(name, list):
                    for _name in name:
                        if _name in self.fields:
                            field_list.append(dict(name=_name, width=100//len(name)))
                else:
                    if name in self.fields:
                        field_list.append(dict(name=name, width=100))
            if field_list:
                self.fieldsets[title] = field_list

    def save(self, *args, **kwargs):
        # save one-to-one fields
        for name in self.one_to_one:
            instance = getattr(self.instance, name)
            if self.data.get(name.upper()):  # if checkbox is checked
                instance = instance or self.one_to_one[name].queryset.model()
                for field_name in self.fields:
                    if field_name.split('__')[0] == name:
                        setattr(instance, field_name.split('__')[1], self.cleaned_data[field_name])
                instance.save()
                setattr(self.instance, name, instance)
            else:  # if checkbox is NOT checked
                if instance:
                    instance.delete()
                setattr(self.instance, name, None)

        # save one-to-many fields
        for name in self.one_to_many:
            qs = getattr(self.instance, name)
            pks = list(qs.values_list('pk', flat=True))
            for i in range(0, 5):
                key = '{}--{}'.format(name.upper(), i)
                pk = self.data.get(key)
                if pk:  # if checkbox is checked
                    if pk == 'on':
                        instance = qs.model()
                    else:
                        pks.remove(int(pk))
                        instance = qs.get(pk=pk)
                    for field_name in self.fields:
                        if field_name.startswith('{}__'.format(name)) and field_name.endswith('__{}'.format(i)):
                            setattr(instance, field_name.split('__')[1], self.cleaned_data[field_name])
                    instance.save()
                    qs.add(instance)
            qs.filter(pk__in=pks).delete()
        super().save(*args, **kwargs)

    def serialize(self, wrap=False, verbose=False):
        if self.message:
            return self.message
        if wrap:
            data = dict(type='form')
            form_fields = {}
            for field_name in self.fields:
                field = self.fields[field_name]
                form_fields[field_name] = dict(
                    label=field.label,
                    name=field_name,
                    type=type(field).__name__.replace('Field', '').lower(),
                    required=field.required,
                    value=self.data.get(field_name)
                )
            data.update(self.get_metadata())
            data.update(fields=form_fields, errors=self.errors)
            return data
        return {}

    @classmethod
    @lru_cache
    def get_metadata(cls, path=None):
        form_name = cls.__name__
        meta = getattr(cls, 'Meta', None)
        if meta:
            target = 'model'
            name = getattr(meta, 'verbose_name', form_name)
            submit = getattr(meta, 'submit_label', 'Enviar')
            icon = getattr(meta, 'icon', None)
            ajax = getattr(meta, 'ajax', True)
            style = getattr(meta, 'style', 'primary')
            method = getattr(meta, 'method', 'post')
            batch = getattr(meta, 'batch', False)
        else:
            target = 'model'
            name = 'Enviar'
            submit = name
            icon = None
            ajax = True
            style = 'primary'
            method = 'get'
            batch = False
        if path:
            if hasattr(cls, 'instances'):
                target = 'queryset' if batch else 'instance'
                path = '{}{{id}}/{}/'.format(path, form_name)
            else:
                path = '{}{}/'.format(path, form_name)
        metadata = dict(type='form', key=form_name, name=name, submit=submit, target=target)
        if getattr(meta, 'batch', False):
            metadata.update(batch=True)
        metadata.update(method=method, icon=icon, style=style, ajax=ajax, path=path)
        return metadata

    def get_method(self):
        meta = getattr(self, 'Meta', None)
        return getattr(meta, 'method', 'post') if meta else 'post'

    def has_permission(self):
        return self.request.user.is_superuser

    def __str__(self):
        for name, field in self.fields.items():
            classes = field.widget.attrs.get('class', '').split()
            if isinstance(field.widget, widgets.TextInput):
                classes.append('form-control')
            elif isinstance(field.widget, widgets.PasswordInput):
                classes.append('form-control')
            elif isinstance(field.widget, widgets.NumberInput):
                classes.append('form-control')
            elif isinstance(field.widget, widgets.Select):
                classes.append('form-control')
            elif isinstance(field.widget, widgets.CheckboxInput):
                classes.append('form-check-input')

            if isinstance(field, DateField):
                classes.append('date-input')

            if isinstance(field, ModelChoiceField):
                initial = self.initial.get(name)
                pks = []
                if initial:
                    if isinstance(initial, int):
                        pks.append(initial)
                    else:
                        pks.extend([obj.pk for obj in initial])
                if self.data:
                    pks = [pk for pk in self.data.getlist(name) if pk]
                field.queryset = field.queryset.filter(pk__in=pks) if pks else field.queryset.none()
                field.widget.attrs['data-choices-url'] = '{}?choices={}'.format(
                    self.request.path, name
                )

            if getattr(field.widget, 'mask', None):
                classes.append('masked-input')
                field.widget.attrs['data-reverse'] = 'false'
                field.widget.attrs['data-mask'] = getattr(field.widget, 'mask')
            if getattr(field.widget, 'rmask', None):
                classes.append('masked-input')
                field.widget.attrs['data-reverse'] = 'true'
                field.widget.attrs['data-mask'] = getattr(field.widget, 'rmask')
            field.widget.attrs['class'] = ' '.join(classes)
        return mark_safe(
            render_to_string(
                ['adm/form.html'], dict(
                    self=self, fieldsets=self.fieldsets
                ),
                request=self.request
            )
        )

    def is_valid(self):
        if 'choices' in self.request.GET:
            raise JsonReadyResponseException(
                self.choices(self.request.GET['choices'], q=self.request.GET.get('term'))
            )
        return super().is_valid()

    def choices(self, field_name, q=None):
        field = self.fields[field_name]
        attr = getattr(self, 'get_{}_queryset'.format(field_name), None)
        self.data.update(self.request.GET)
        qs = field.queryset if attr is None else attr(field.queryset)
        total = qs.count()
        qs = qs.search(q=q) if q else qs
        items = [dict(id=value.id, text=str(value)) for value in qs[0:25]]

        return dict(
            total=total, page=1, pages=math.ceil((1.0 * total) / 25),
            q=q, items=items
        )

    def notify(self, text='Ação realizada com sucesso', style='sucess', **kwargs):
        messages.add_message(self.request, messages.INFO, text)
        self.message = dict(type='message', text=text, style=style, **kwargs)


class Form(FormMixin, Form):
    def __init__(self, *args, **kwargs):
        self.fake = kwargs.pop('fake', False)
        self.instance = kwargs.pop('instance', None)
        self.message = None
        self.instantiator = kwargs.pop('instantiator', None)
        self.request = kwargs.pop('request', None)
        if 'data' not in kwargs:
            if self.base_fields:
                data = self.request.POST or None
            else:
                data = self.request.POST
            kwargs['data'] = data
        if not self.fake:
            super().__init__(*args, **kwargs)

    def process(self):
        self.notify()


class ModelFormMetaclass(models.ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        if 'Meta' in attrs:
            if not hasattr(attrs['Meta'], 'fields') and not hasattr(attrs['Meta'], 'exclude'):
                form_fields = []
                fieldsets = getattr(attrs['Meta'], 'fieldsets', {})
                for tuples in fieldsets.values():
                    for names in tuples:
                        if isinstance(names, str):
                            form_fields.append(names)
                        else:
                            form_fields.extend(names)
                setattr(attrs['Meta'], 'fields', form_fields)

        return super().__new__(mcs, name, bases, attrs)


class ModelForm(FormMixin, ModelForm, metaclass=ModelFormMetaclass):

    def __init__(self, *args, **kwargs):
        self.fake = kwargs.pop('fake', False)
        self.instance = kwargs.get('instance', None)
        self.message = None
        self.request = kwargs.pop('request', None)
        self.instantiator = kwargs.pop('instantiator', None)
        if 'data' not in kwargs:
            if self.base_fields:
                data = self.request.POST or None
            else:
                data = self.request.POST
            kwargs['data'] = data
        if not self.fake:
            super().__init__(*args, **kwargs)

    def process(self):
        self.save()
        self.notify()


class QuerySetFormMixin:
    instances = []

    def __init__(self, *args, **kwargs):
        self.instances = kwargs.pop('instances', ())
        if self.instances:
            kwargs.update(instance=self.instances[0])
        super().__init__(*args, **kwargs)

    def process(self):
        if self.instances:
            for instance in self.instances:
                self.instance = instance
                self._post_clean()
                self.save()
        else:
            self.save()
        self.notify()


class QuerySetForm(QuerySetFormMixin, ModelForm):
    pass


class LoginForm(Form):
    username = CharField(label='Login')
    password = CharField(label='Senha', widget=widgets.PasswordInput())

    class Meta:
        name = None
        ajax = False
        submit = 'Acessar'

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        if self.cleaned_data:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            if username and password:
                self.user = auth.authenticate(
                    self.request, username=username, password=password
                )
                if self.user is None:
                    raise ValidationError('Login e senham não conferem.')
        return self.cleaned_data

    def process(self):
        if self.user:
            auth.login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')
            self.request.session['menu'] = load_menu(self.user)
            self.request.session.save()
