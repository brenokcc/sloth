# -*- coding: utf-8 -*-
import math
import re
import zlib
import pickle
import base64
import datetime
from django.core import signing
import traceback
from decimal import Decimal
from copy import deepcopy
from functools import lru_cache
from django.contrib import auth
from django.contrib import messages
from django.conf import settings
from django.apps import apps
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from . import inputs
from django import forms
from django.forms.models import ModelFormMetaclass, ModelMultipleChoiceField

from ..exceptions import JsonReadyResponseException, ReadyResponseException, HtmlReadyResponseException
from ..utils import to_api_params, to_camel_case, to_snake_case
from django.forms.fields import *
from django.forms.widgets import *
from .fields import *
from django.core.exceptions import ValidationError
from ..utils.formatter import format_value
from ..core.queryset import QuerySet
from ..utils.http import FileResponse

ACTIONS = {}


class PermissionChecker:

    def __init__(self, request, instance=None, instantiator=None, metaclass=None):
        self.request = request
        self.instance = instance
        self.instantiator = instantiator
        self.metaclass = metaclass

    def has_permission(self, user):
        pass


class ActionMetaclass(ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        if 'Meta' in attrs:
            if hasattr(attrs['Meta'], 'model'):
                bases += forms.ModelForm,
            else:
                bases += forms.Form,
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
        cls = super().__new__(mcs, name, bases, attrs)
        ACTIONS[name] = cls
        ACTIONS[name.lower()] = cls
        ACTIONS[to_snake_case(name)] = cls
        return cls


class RegionalDateWidget(DateInput):
    input_type = 'date'

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, datetime.date):
            value = value.isoformat()
        attrs = attrs or {}
        attrs.update({'autocomplete': 'off'})
        html = super().render(name, value, attrs)
        return mark_safe(html)


class RegionalDateTimeWidget(DateTimeInput):
    input_type = 'datetime-local'

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, datetime.datetime):
            value = value.isoformat().split('.')[0]
        attrs = attrs or {}
        attrs.update({'step': '1'})
        html = super().render(name, value, attrs)
        return mark_safe(html)


class Action(metaclass=ActionMetaclass):

    def __init__(self, *args, **kwargs):
        self.path = None
        self.request = kwargs.pop('request', None)
        self.instantiator = kwargs.pop('instantiator', None)
        self.instances = kwargs.pop('instances', None)
        self.metaclass = getattr(self, 'Meta')

        self.show_form = True
        self.can_be_closed = False
        self.can_be_reloaded = False
        self.content = dict(top=[], left=[], center=[], right=[], bottom=[], info=[], alert=[])
        self.on_change_data = dict(show=[], hide=[], set=[], show_fieldset=[], hide_fieldset=[])

        if forms.ModelForm in self.__class__.__bases__:
            self.instance = kwargs.get('instance', None)
        else:
            self.instance = kwargs.pop('instance', None)

        # print(dict(actions=type(self), instantiator=self.instantiator, instance=self.instance, instances=self.instances))

        # if forms.ModelForm in self.__class__.__bases__:
        #     self.instance = kwargs.get('instance', None)
        #     if self.instances:
        #         kwargs.update(instance=self.instances[0])
        # else:
        #     self.instance = kwargs.pop('instance', None)
        #     if self.instance is None:
        #         if self.instances:
        #             self.instance = self.instances[0]
        #     else:
        #         if self.instances == ():
        #             self.instances = self.instance,
        # if 'instances' in self.request.GET:
        #     self.instances = QuerySet.loads(self.request.GET['instances'])

        form_name = type(self).__name__
        if 'post__{}'.format(form_name) in self.request.GET:
            for k in self.request.GET:
                if k.startswith('post__'):
                    if 'data' not in kwargs:
                        kwargs['data'] = {}
                    kwargs['data'][k.split('__')[-1]] = self.request.GET[k]

        if 'data' not in kwargs:
            if form_name in self.request.GET or form_name in self.request.POST or self.request.path.startswith('/api/'):
                # if self.base_fields or self.requires_confirmation():
                if self.request.method == 'GET' or self.requires_confirmation():
                    if self.get_method() == 'get':
                        data = self.request.GET or None
                    else:
                        data = self.request.POST or None
                else:
                    data = self.request.POST
                kwargs['data'] = data
                kwargs['files'] = self.request.FILES or None
            else:
                kwargs['data'] = None
        # if kwargs['data'] and form_name in kwargs['data']:
        #     self.loads(kwargs['data'][form_name])

        super().__init__(*args, **kwargs)
        self.asynchronous = getattr(self.metaclass, 'asynchronous', None) and self.request.GET.get('synchronous') is None

        related_field_name = getattr(self.metaclass, 'related_field', None)
        if related_field_name:
            setattr(self.instance, related_field_name, self.instantiator)
            if related_field_name in self.fields:
                del self.fields[related_field_name]

        for field_name in self.fields:
            field = self.fields[field_name]
            if hasattr(field, 'queryset'):
                if not self.request.user.is_superuser and getattr(field, 'username_lookup', None):
                    pks = list(field.queryset.filter(**{field.username_lookup: self.request.user}).values_list('pk', flat=True)[0:2])
                    if len(pks) == 1:
                        field.queryset = field.queryset.model.objects.filter(pk=pks[0])
                        field.initial = pks[0]
                        field.widget = forms.HiddenInput()
                else:
                    field.queryset = field.queryset.contextualize(self.request).apply_role_lookups(self.request.user)
            if hasattr(field, 'picker'):
                grouper = field.picker if isinstance(field.picker, str) else None
                if isinstance(field, forms.ModelMultipleChoiceField):
                    field.widget = inputs.MultiplePickInput(field.queryset, grouper=grouper)
                else:
                    field.widget = inputs.PickInput(field.queryset, grouper=grouper)

        self.response = {}
        self.fieldsets = {}
        self.one_to_one = {}
        self.one_to_many = {}

        confirmation = self.requires_confirmation()
        if confirmation:
            help_text = confirmation if isinstance(confirmation, str) else ''
            self.fields['confirmation'] = forms.BooleanField(
                label='', initial='on', required=False, help_text=help_text,
                widget=forms.TextInput(attrs={'style': 'display:none'})
            )

    def closable(self, flag=True):
        self.can_be_closed = flag

    def reloadable(self, flag=True):
        self.can_be_reloaded = flag

    def info(self, text):
        self.content['info'].append(text)

    def alert(self, text):
        self.content['alert'].append(text)

    def parameters(self, index):
        values = None
        for token in self.request.path.split('/'):
            if values is not None:
                values.append((token))
            if token.lower() == type(self).__name__.lower():
                values = []
        return values[index] if values and len(values)>index else None

    def objects(self, model_name):
        return apps.get_model(model_name).objects.contextualize(self.request)

    def clear(self):
        self.show_form = False
        for k, v in self.content.items():
            if k != 'bottom':
                v.clear()

    def download(self, file_path):
        raise ReadyResponseException(FileResponse(file_path))

    def view(self):
        return None

    def append(self, item, position='center'):
        if hasattr(item, 'contextualize'):
            item.contextualize(self.request)
        self.content[position].append(item.html())

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

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

        pop = []
        for name, names in fieldsets.items():
            if len(names) == 1 and (names[0] in self.one_to_one.keys() or names[0] in self.one_to_many.keys()):
                pop.append(name)
        for name in pop:
            del fieldsets[name]

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
            self.fields[key] = forms.BooleanField(
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
            pks.extend(['' for _ in range(len(pks) + 1, one_to_many_field.max + 1)])
            for i, pk in enumerate(pks):
                initial = one_to_many_field.queryset.model.objects.filter(
                    pk=pk
                ).values(
                    *form_cls.base_fields.keys()
                ).first() if pk else {}
                key = '{}--{}'.format(one_to_many_field_name.upper(), i)
                required = i < one_to_many_field.min
                self.fields[key] = forms.CharField(
                    label='{} {}'.format(one_to_many_field.queryset.model.metaclass().verbose_name, i + 1),
                    required=required, initial=(pk or 'on') if required else pk, widget=forms.CheckboxInput()
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
                            if not isinstance(self.fields[_name].widget, forms.HiddenInput):
                                field_list.append(dict(name=_name, width=100 // len(name)))
                else:
                    if name in self.fields:
                        if not isinstance(self.fields[name].widget, forms.HiddenInput):
                            field_list.append(dict(name=name, width=100))
            if field_list:
                self.fieldsets[title] = field_list

    def get_api_params(self):
        return to_api_params(self.fields.items())

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

    def serialize(self, wrap=False):
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
            if hasattr(self, 'get_verbose_name'):
                data['name'] = hasattr(self, 'get_verbose_name')
            data.update(fields=form_fields, errors=self.errors)
            return data
        else:
            data = dict(type='form', errors=self.errors)
            return data

    @lru_cache()
    def get_on_change_fields(self):
        on_change = []
        for attr_name in dir(self):
            if attr_name.startswith('on_') and attr_name.endswith('_change'):
                field_name = attr_name[3:-7]
                on_change.append(field_name)
        return on_change

    def get_allowed_attrs(self):
        return []

    @classmethod
    @lru_cache
    def get_metadata(cls, path=None, target=None):
        form_name = cls.__name__
        metaclass = getattr(cls, 'Meta', None)
        if metaclass:
            target = target
            name = getattr(metaclass, 'verbose_name', re.sub("([a-z])([A-Z])", "\g<1> \g<2>", form_name))
            submit = getattr(metaclass, 'submit_label', name)
            icon = getattr(metaclass, 'icon', None)
            ajax = getattr(metaclass, 'ajax', True)
            modal = getattr(metaclass, 'modal', True)
            style = getattr(metaclass, 'style', 'primary')
            method = getattr(metaclass, 'method', 'post')
            auto_reload = getattr(metaclass, 'auto_reload', None)
        else:
            name, submit, icon, ajax, modal, style, method, auto_reload = (
                'Enviar', 'Enviar', None, True, 'modal', 'primary', 'get', None
            )
        if path:
            path, *params = path.split('?')
            if target in ('queryset', 'instance'):
                path = '{}{{id}}/{}/'.format(path, to_snake_case(form_name))
            else:
                path = '{}{}/'.format(path, to_snake_case(form_name))
            if params:
                path = '{}?{}'.format(path, params[0])
        metadata = dict(
            type='form', key=form_name, name=name, submit=submit, target=target,
            method=method, icon=icon, style=style, ajax=ajax, path=path, modal=modal, auto_reload=auto_reload
        )
        return metadata

    def get_method(self):
        return getattr(self.metaclass, 'method', 'post') if hasattr(self, 'Meta') else 'post'

    def get_instructions(self):
        return None

    def is_modal(self):
        return getattr(self.metaclass, 'modal', True) if hasattr(self, 'Meta') else True

    def has_permission(self, user):
        return user.is_superuser

    def check_permission(self, user):
        return user.is_superuser or self.has_permission(user)

    @classmethod
    def check_fake_permission(cls, request, instance=None, instantiator=None):
        if request:  # and not request.user.is_superuser
            checker = PermissionChecker(request, instance, instantiator, getattr(cls, 'Meta', None))
            has_permission = cls.has_permission(checker, request.user)
            return cls.check_permission(checker, request.user) if has_permission is None else has_permission
        return True

    def __str__(self):
        return self.html()

    def html(self):
        if self.response:
            js = '<script>{}</script>'
            display_messages = True
            if self.response.get('dispose'):
                js = js.format('fade{}({});'.format(self.get_metadata().get('key'), self.response.get('dispose')))
            elif self.response.get('url') == '.':
                if 'modal' in self.request.GET:
                    js = js.format('$(document).popup("{}");'.format(self.request.path))
                else:
                    js = js.format('$(document).refresh([]);'.format(self.get_metadata().get('key')))
            elif self.response.get('url') == '..':
                display_messages = 'modal' in self.request.GET
                js = js.format('$(document).back().refresh([]);')
            elif self.response.get('url'):
                display_messages = False
                js = js.format('$(document).redirect("{}");'.format(self.response['url']))
            html = render_to_string('app/messages.html', request=self.request) if display_messages else ''
            return '<!---->{}{}<!---->'.format(js, html)

        for name, field in self.fields.items():
            classes = field.widget.attrs.get('class', '').split()
            if isinstance(field.widget, forms.CheckboxInput):
                classes.append('form-check-input')
            elif isinstance(field.widget, forms.widgets.Input):
                classes.append('form-control')

            if isinstance(field, forms.DateField):
                field.widget = RegionalDateWidget()
                classes.append('date-input')
                if self.initial[name] and isinstance(self.initial[name], str) and '/' in self.initial[name]:
                    self.initial[name] = datetime.datetime.strptime(self.initial[name], '%d/%m/%Y').strftime('%Y-%m-%m')

            if isinstance(field, forms.DateTimeField):
                field.widget = RegionalDateTimeWidget()
                classes.append('date-time-input')
                if self.initial[name] and isinstance(self.initial[name], str) and '/' in self.initial[name]:
                    self.initial[name] = datetime.datetime.strptime(self.initial[name], '%d/%m/%Y').strftime('%Y-%m-%m %H:%M')

            if isinstance(field, forms.DecimalField):
                field.widget.input_type = 'text'
                field.widget.rmask = getattr(field.widget, 'rmask', '#.##0,00')
                if name in self.initial and self.initial[name] is not None:
                    self.initial[name] =  Decimal('%.2f' % self.initial[name])

            if isinstance(field, forms.ImageField):
                classes.append('image-input')

            if isinstance(field, forms.ModelChoiceField) and isinstance(field.widget, Select):
                initial = self.initial.get(name)
                pks = []
                if initial:
                    if isinstance(initial, int):
                        pks.append(initial)
                    else:
                        pks.extend([obj.pk for obj in initial])
                if self.data:
                    pks = [pk for pk in self.data.getlist(name) if pk]
                if getattr(field, 'picker', None) is None:
                    field.queryset = field.queryset.filter(pk__in=pks) if pks else field.queryset.none()
                field.widget.attrs['data-choices-url'] = '{}{}action_choices={}'.format(
                    self.get_full_path(), '&' if '?' in self.get_full_path() else '?', name
                )

            if getattr(field.widget, 'mask', None):
                classes.append('masked-input')
                field.widget.attrs['data-reverse'] = 'false'
                field.widget.attrs['data-mask'] = getattr(field.widget, 'mask')
            if getattr(field.widget, 'rmask', None):
                classes.append('masked-input')
                field.widget.attrs['data-reverse'] = 'true'
                field.widget.attrs['data-mask'] = getattr(field.widget, 'rmask')
            if getattr(field.widget, 'formatted', False):
                classes.append('html-input')

            field.widget.attrs['class'] = ' '.join(classes)
        return mark_safe(
            render_to_string(
                ['app/form.html'], dict(
                    self=self, fieldsets=self.fieldsets
                ),
                request=self.request
            )
        )

    def show(self, *names):
        for name in names:
            if name.islower():
                if name in self.on_change_data['hide']:
                    self.on_change_data['hide'].remove(name)
                if name not in self.on_change_data['show']:
                    self.on_change_data['show'].append(name)
            else:
                name = slugify(name)
                if name in self.on_change_data['hide_fieldset']:
                    self.on_change_data['hide_fieldset'].remove(name)
                if name not in self.on_change_data['show_fieldset']:
                    self.on_change_data['show_fieldset'].append(name)

    def hide(self, *names):
        for name in names:
            if name.islower():
                if name in self.on_change_data['show']:
                    self.on_change_data['show'].remove(name)
                if name not in self.on_change_data['hide']:
                    self.on_change_data['hide'].append(name)
            else:
                name = slugify(name)
                if name in self.on_change_data['show_fieldset']:
                    self.on_change_data['show_fieldset'].remove(name)
                if name not in self.on_change_data['hide_fieldset']:
                    self.on_change_data['hide_fieldset'].append(name)

    def set(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(v, 'pk'):
                value = v.pk
                text = str(v)
            else:
                value = format_value(v)
                text = None
            self.on_change_data['set'].append(dict(name=k, value=value, text=text))

    def is_valid(self):
        from ..core.valueset import ValueSet
        if self.asynchronous:
            return False
        valueset = self.view()
        if type(valueset) == dict:
            template = '{}.html'.format(type(self).__name__)
            self.content['center'].append(render_to_string([template], valueset, request=self.request))
        elif type(valueset) == ValueSet:
            self.content['center'].append(valueset.contextualize(self.request).html())
        for field in self.fields.values():
            if isinstance(field, forms.DecimalField):
                field.clean = lambda value: value.replace('.', '').replace(',','.')
        self.load_fieldsets()
        if 'action_choices' in self.request.GET:
            raise JsonReadyResponseException(
                self.choices(self.request.GET['action_choices'], q=self.request.GET.get('term'))
            )
        if 'on_change_field' in self.request.POST:
            for data in self.on_change_data.values():
                data.clear()
            field_name = self.request.POST['on_change_field']
            value = self.request.POST.get('on_change_value')
            if value == 'true':
                value = True
            if value == 'false':
                value = False
            getattr(self, 'on_{}_change'.format(field_name))(value)
            raise JsonReadyResponseException(self.on_change_data)
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

    def dispose(self, milleseconds=2000):
        self.response.update(dispose=milleseconds)

    def reload(self):
        return self.redirect('.')

    def message(self, text, style='success', milleseconds=60000):
        if self.request.path.startswith('/app/'):
            messages.add_message(self.request, messages.SUCCESS, text)
        else:
            self.response.update(message=dict(text=text, style=style, milleseconds=milleseconds))

    def redirect(self, url=None):
        if url is None:
            url = '..' if getattr(self, 'fields', None) or self.is_modal() else '.'
        self.response.update(type='redirect', url=url)
        if not self.get_metadata()['ajax']:
            raise ReadyResponseException(HttpResponseRedirect(url))

    def run(self, *tasks, message=None):
        for task in tasks:
            task.start(self.request)
        if len(tasks) > 1:
            self.redirect(message=message or 'Tarefas iniciadas com sucesso')
        elif message:
            self.redirect(message=message)
        else:
            self.redirect('/app/api/task/{}/'.format(task.task_id), message=message)

    def submit(self):
        if self.instances:
            for instance in self.instances:
                self.instance = instance
                self._post_clean()
                self.save()
        else:
            self.save()
        self.message('Ação realizada com sucesso.')
        self.redirect()

    def process(self):
        try:
            from ..core.valueset import ValueSet
            response = self.submit()
            if isinstance(response, HttpResponse):
                raise ReadyResponseException(response)
            if isinstance(response, ValueSet):
                self.content['bottom'].append(response.contextualize(self.request).html())
        except forms.ValidationError as e:
            if self.request.path.startswith('/app/'):
                message = 'Corrija os erros indicados no formulário'
                messages.add_message(self.request, messages.WARNING, message)
            self.add_error(None, e.message)
        except BaseException as e:
            if isinstance(e, ReadyResponseException):
                raise e
            if isinstance(e, JsonReadyResponseException):
                raise e
            if isinstance(e, HtmlReadyResponseException):
                raise e
            traceback.print_exc()
            if self.request.path.startswith('/app/'):
                message = 'Ocorreu um erro no servidor: {}'.format(e)
                messages.add_message(self.request, messages.WARNING, message)
            self.add_error(None, message)

    @classmethod
    def get_attr_metadata(cls, lookup):
        attr = getattr(cls, lookup)
        template = getattr(attr, '__template__', None)
        metadata = getattr(attr, '__metadata__', None)
        if template:
            if not template.endswith('.html'):
                template = '{}.html'.format(template)
            if not template.startswith('.html'):
                template = 'renderers/{}'.format(template)
        return getattr(attr, '__verbose_name__', lookup), False, template, metadata

    def value_set(self, *names):
        from sloth.core.base import ValueSet
        return ValueSet(self, names)

    @classmethod
    @lru_cache
    def action_form_cls(cls, action):
        return ACTIONS.get(action)

    def should_display_buttons(self):
        return self.fields or self.submit.__func__ != Action.submit

    # def dumps(self):
    #     state = dict(instantiator=None, instance=None, instances=None)
    #     if self.instantiator:
    #         state['instantiator'] = '{}.{}'.format(
    #             self.instantiator.metaclass().app_label,
    #             self.instantiator.metaclass().model_name,
    #         ), self.instantiator.id
    #     if self.instance:
    #         state['instance'] = '{}.{}'.format(
    #             self.instance.metaclass().app_label,
    #             self.instance.metaclass().model_name,
    #         ), self.instance.id
    #     if self.instances:
    #         state['instances'] = self.instances.dumps()
    #     from pprint import pprint;pprint(state)
    #     return signing.dumps(base64.b64encode(zlib.compress(pickle.dumps(state))).decode())
    #
    # def loads(self, s):
    #     state = pickle.loads(zlib.decompress(base64.b64decode(signing.loads(s).encode())))
    #     if state['instantiator'] and state['instantiator'][1]:
    #         self.instantiator = apps.get_model(state['instantiator'][0]).objects.get(pk=state['instantiator'][1])
    #     if state['instance'] and state['instance'][1]:
    #         self.instance = apps.get_model(state['instance'][0]).objects.get(pk=state['instance'][1])
    #     if state['instances']:
    #         self.instances = QuerySet.loads(state['instances'])

    def get_full_path(self):
        return self.path or self.request.get_full_path()

    def contextualize(self, request):
        return self

    def apply_role_lookups(self, user):
        return self
