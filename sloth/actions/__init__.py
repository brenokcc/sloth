# -*- coding: utf-8 -*-
import math
import os
import re
from copy import deepcopy
from functools import lru_cache

from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.forms import *
from django.forms import fields
from django.forms import models
from django.forms import widgets
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from ..exceptions import JsonReadyResponseException


class PermissionChecker:

    def __init__(self, request, instance=None, instantiator=None, metaclass=None):
        self.request = request
        self.instance = instance
        self.instantiator = instantiator
        self.metaclass = metaclass

    def has_permission(self, user):
        pass


class ActionMetaclass(models.ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        if 'Meta' in attrs:
            if hasattr(attrs['Meta'], 'model'):
                bases += ModelForm,
            else:
                bases += Form,
            if not hasattr(attrs['Meta'], 'fields') and not hasattr(attrs['Meta'], 'exclude'):
                form_fields = []
                fieldsets = getattr(attrs['Meta'], 'fieldsets', {})
                if fieldsets:
                    for tuples in fieldsets.values():
                        for names in tuples:
                            if isinstance(names, str):
                                form_fields.append(names)
                            else:
                                form_fields.extend(names)
                    setattr(attrs['Meta'], 'fields', form_fields)
                else:
                    setattr(attrs['Meta'], 'exclude', ())
        elif name != 'Action':
            raise NotImplementedError('class {} must have a Meta class.'.format(name))
        return super().__new__(mcs, name, bases, attrs)


class Action(metaclass=ActionMetaclass):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.instantiator = kwargs.pop('instantiator', None)
        self.instances = kwargs.pop('instances', ())
        self.metaclass = getattr(self, 'Meta')

        if ModelForm in self.__class__.__bases__:
            self.instance = kwargs.get('instance', None)
            if self.instances:
                kwargs.update(instance=self.instances[0])
        else:
            self.instance = kwargs.pop('instance', None)
            if self.instance is None:
                if self.instances:
                    self.instance = self.instances[0]
            else:
                if self.instances == ():
                    self.instances = self.instance,

        if 'data' not in kwargs:
            if self.base_fields or self.requires_confirmation():
                data = self.request.POST or None
            else:
                data = self.request.POST
            kwargs['data'] = data
            kwargs['files'] = self.request.FILES or None

        super().__init__(*args, **kwargs)

        self.response = {}
        self.fieldsets = {}
        self.one_to_one = {}
        self.one_to_many = {}

        if self.requires_confirmation():
            self.fields['confirmation'] = BooleanField(
                label='', initial='on', required=False, widget=TextInput(attrs={'style': 'display:none'})
            )

    def requires_confirmation(self):
        return getattr(self.metaclass, 'confirmation', False)

    @lru_cache
    def get_one_to_one_field_names(self):
        return self.instance.get_one_to_one_field_names() if self.instance else ()

    @lru_cache
    def get_one_to_many_field_names(self):
        return self.instance.get_one_to_many_field_names() if self.instance else ()

    def get_fieldsets(self):
        fieldsets = getattr(self.metaclass, 'fieldsets', None)
        if fieldsets is None:
            fieldsets = {}
            if self.fields:
                field_names = [
                    name for name in self.fields.keys()
                    if name not in self.get_one_to_one_field_names()
                       and name not in self.get_one_to_many_field_names()
                ]
                if field_names:
                    fieldsets[None] = field_names
        else:
            fieldsets = dict(fieldsets)
        return fieldsets

    def load_fieldsets(self):
        fieldsets = self.get_fieldsets()

        # extract one-to-one and one-to-many fields
        if self.instance:
            for name in list(self.fields):
                if name in self.get_one_to_one_field_names():
                    # remove one-to-one fields from the form
                    self.one_to_one[name] = self.fields.pop(name)
                if name in self.get_one_to_many_field_names():
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
                required=one_to_one_field.required, initial=bool(initial) or one_to_one_field.required
            )
            self.fields[key].widget.attrs['class'] = 'field-controller'
            if one_to_one_field.required:
                self.fields[key].widget.attrs['class'] += ' d-none'
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
            pks.extend(['' for _ in range(len(pks)+1, one_to_many_field.max+1)])
            for i, pk in enumerate(pks):
                initial = one_to_many_field.queryset.model.objects.filter(
                    pk=pk
                ).values(
                    *form_cls.base_fields.keys()
                ).first() if pk else {}
                key = '{}--{}'.format(one_to_many_field_name.upper(), i)
                required = i < one_to_many_field.min
                self.fields[key] = fields.CharField(
                    label='{} {}'.format(one_to_many_field.queryset.model.metaclass().verbose_name, i+1),
                    required=required, initial=(pk or 'on') if required else pk, widget=fields.CheckboxInput()
                )
                self.fields[key].widget.attrs['class'] = 'field-controller'
                if required:
                    self.fields[key].widget.attrs['class'] += ' d-none'
                field_list.append(key)
                inline_field_list = []
                for name, field in form_cls.base_fields.items():
                    field = deepcopy(field)
                    one_to_many_key = '{}__{}__{}'.format(one_to_many_field_name, name, i)
                    inline_field_list.append(one_to_many_key)
                    field.required = field.required and required or False
                    field.widget.attrs['class'] = key
                    self.fields[one_to_many_key] = field
                    self.initial[one_to_many_key] = initial.get(name)

                field_list.append(inline_field_list)
            fieldsets[one_to_many_field.label] = field_list
        self.fieldsets = fieldsets
        self.parse_fieldsets()

    def parse_fieldsets(self):
        # configure ordinary fields
        for title, names in self.fieldsets.items():
            field_list = []
            for name in names:
                if isinstance(name, tuple) or isinstance(name, list):
                    for _name in name:
                        if _name in self.fields:
                            if not isinstance(self.fields[_name].widget, widgets.HiddenInput):
                                field_list.append(dict(name=_name, width=100//len(name)))
                else:
                    if name in self.fields:
                        if not isinstance(self.fields[name].widget, widgets.HiddenInput):
                            field_list.append(dict(name=name, width=100))
            if field_list:
                self.fieldsets[title] = field_list

    def get_api_params(self):
        params = []
        for name, field in self.fields.items():
            param_type = 'string'
            param_format = None
            if isinstance(field, BooleanField) or name.isupper():  # controller field
                param_type = 'boolean'
            elif isinstance(field, DateTimeField):
                param_format = 'date-time'
            elif isinstance(field, DateField):
                param_format = 'date'
            elif isinstance(field, IntegerField) or isinstance(field, ModelChoiceField):
                param_type = 'integer'
                param_format = 'int32'
            params.append(
                {'description': field.label, 'name': name, 'in': 'query', 'required': False,
                 'schema': dict(type=param_type, format=param_format)}
            )
        return params

    def save(self, *args, **kwargs):
        if hasattr(self.instance, 'pre_save'):
            self.instance.pre_save()

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

        # save
        if hasattr(super(), 'save'):
            super().save(*args, **kwargs)

        # save one-to-many fields
        for name in self.one_to_many:
            qs = getattr(self.instance, name)
            pks = list(qs.values_list('pk', flat=True))
            for i in range(0, 6):
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

        if hasattr(self.instance, 'post_save'):
            self.instance.post_save()

    def serialize(self, wrap=False, verbose=False):
        if self.response:
            return self.response
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
    def get_metadata(cls, path=None, inline=False, batch=False):
        form_name = cls.__name__
        metaclass = getattr(cls, 'Meta', None)
        if metaclass:
            target = 'model'
            name = getattr(metaclass, 'verbose_name', re.sub("([a-z])([A-Z])", "\g<1> \g<2>", form_name))
            submit = getattr(metaclass, 'submit_label', name)
            icon = getattr(metaclass, 'icon', None)
            ajax = getattr(metaclass, 'ajax', True)
            modal = getattr(metaclass, 'modal', True)
            style = getattr(metaclass, 'style', 'primary')
            method = getattr(metaclass, 'method', 'post')
        else:
            target, name, submit, icon, ajax, modal, style, method = (
                'model', 'Enviar', 'Enviar', None, True, 'modal', 'primary', 'get'
            )
        if path:
            if inline or batch:
                target = 'queryset' if batch else 'instance'
                path = '{}{{id}}/{}/'.format(path, form_name)
            else:
                path = '{}{}/'.format(path, form_name)
        metadata = dict(
            type='form', key=form_name, name=name, submit=submit, target=target,
            method=method, icon=icon, style=style, ajax=ajax, path=path, modal=modal
        )
        return metadata

    def get_method(self):
        return getattr(self.metaclass, 'method', 'post') if hasattr(self, 'Meta') else 'post'

    def is_modal(self):
        return getattr(self.metaclass, 'modal', True) if hasattr(self, 'Meta') else True

    def has_permission(self, user):
        pass

    def check_permission(self, user):
        has_permission = self.has_permission(user)
        if has_permission is None:
            return user.is_superuser or user.roles.contains(*getattr(self.metaclass, 'has_permission', ()))
        return has_permission

    @classmethod
    def check_fake_permission(cls, request, instance=None, instantiator=None):
        checker = PermissionChecker(request, instance=instance, instantiator=instantiator, metaclass=getattr(cls, 'Meta', None))
        has_permission = cls.has_permission(checker, request.user)
        if has_permission is None:
            return cls.check_permission(checker, request.user)
        return has_permission

    def __str__(self):
        for name, field in self.fields.items():
            classes = field.widget.attrs.get('class', '').split()
            if isinstance(field.widget, widgets.CheckboxInput):
                classes.append('form-check-input')
            elif isinstance(field.widget, widgets.Input):
                classes.append('form-control')

            if isinstance(field, DateField):
                classes.append('date-input')

            if isinstance(field, DecimalField):
                field.localize = True
                field.widget.is_localized = True
                field.widget.input_type = 'text'
                field.widget.rmask = '#.##0,00'

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
        self.load_fieldsets()
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
        items = [dict(id=value.id, text=str(value), html=value.get_select_display()) for value in qs[0:25]]
        return dict(
            total=total, page=1, pages=math.ceil((1.0 * total) / 25),
            q=q, items=items
        )

    def redirect(self, url=None, message=None, style='sucess'):
        if url is None:
            url = '..' if self.fields or self.is_modal() else '.'
        self.response.update(type='redirect', url=url)
        if message is None:
            message = getattr(self.metaclass, 'message', None)
        if message:
            messages.add_message(self.request, messages.INFO, message)
            self.response.update(message=message, style=style)

    def display(self, data=None, **kwargs):
        self.response.update(
            html=render_to_string(['{}.html'.format(self.__class__.__name__)], data or kwargs, request=self.request)
        )

    def download(self, file_path_or_bytes, file_name=None):
        download_dir_path = os.path.join(settings.MEDIA_ROOT, 'download')
        os.makedirs(download_dir_path, exist_ok=True)
        if type(file_path_or_bytes) == bytes:
            file_path = os.path.join(download_dir_path, file_name)
            with open(file_path, 'w+b') as file:
                file.write(file_path_or_bytes)
        else:
            if file_name is None:
                file_name = file_path_or_bytes.split('/')[-1]
            file_path = os.path.join(download_dir_path, file_name)
            os.symlink(file_path_or_bytes, file_path)
            print(file_path_or_bytes, file_path)
        self.response.update(type='redirect', url='/media/download/{}'.format(file_name))

    def submit(self):
        if self.instances:
            for instance in self.instances:
                self.instance = instance
                self._post_clean()
                self.save()
        else:
            self.save()
        self.redirect(message='Ação realizada com sucesso.')


class LoginForm(Action):
    username = CharField(label='Login')
    password = CharField(label='Senha', widget=widgets.PasswordInput())

    class Meta:
        verbose_name = None
        ajax = False
        submit_label = 'Acessar'
        fieldsets = {
            None: ('username', 'password')
        }

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
                    raise ValidationError('Login e senha não conferem.')
        return self.cleaned_data

    def submit(self):
        if self.user:
            auth.login(self.request, self.user, backend='django.contrib.auth.backends.ModelBackend')


class PasswordForm(Action):
    password = CharField(label='Senha', widget=widgets.PasswordInput())
    password2 = CharField(label='Confirmação', widget=widgets.PasswordInput())

    class Meta:
        verbose_name = 'Alterar Senha'

    def clean(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password != password2:
            raise forms.ValidationError('Senhas não conferem.')
        return self.cleaned_data

    def submit(self):
        self.request.user.set_password(self.cleaned_data.get('password'))
        self.request.user.save()
        auth.login(self.request, self.request.user, backend='django.contrib.auth.backends.ModelBackend')
        self.redirect(message='Senha alterada com sucesso.')
