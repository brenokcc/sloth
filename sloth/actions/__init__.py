# -*- coding: utf-8 -*-
import math
import re
import traceback
from decimal import Decimal
from copy import deepcopy
from functools import lru_cache
from django.contrib import auth
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from . import inputs
from django import forms
from django.forms.models import ModelFormMetaclass, ModelMultipleChoiceField
from ..exceptions import JsonReadyResponseException, ReadyResponseException
from ..utils import to_api_params, to_camel_case, to_snake_case
from django.forms.fields import *
from django.forms.widgets import *
from .fields import *
from django.core.exceptions import ValidationError
from ..utils.formatter import format_value

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


class Action(metaclass=ActionMetaclass):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.instantiator = kwargs.pop('instantiator', None)
        self.instances = kwargs.pop('instances', ())
        self.metaclass = getattr(self, 'Meta')
        self.output_data = None
        self.on_change_data = {'show': [], 'hide': [], 'set': [], 'show_fieldset': [], 'hide_fieldset': []}

        if forms.ModelForm in self.__class__.__bases__:
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

        form_name = type(self).__name__
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

        super().__init__(*args, **kwargs)

        for field_name in self.fields:
            field = self.fields[field_name]
            if False and hasattr(field, 'queryset') and field.queryset.metadata['lookups']: # TODO
                field.queryset = field.queryset.apply_role_lookups(self.request.user)
                if field.queryset.count() == 1:
                    field.initial = field.queryset.first().id
                    field.widget = forms.HiddenInput()
            if hasattr(field, 'queryset') and getattr(field, 'auto_user', False) and not self.request.user.is_superuser:
                scope_type = '{}.{}'.format(
                    field.queryset.model.metaclass().app_label, field.queryset.model.metaclass().model_name
                )
                pks = self.request.user.roles.filter(scope_type=scope_type).values_list('scope_value', flat=True)
                field.queryset = field.queryset.model.objects.filter(pk__in=pks)
                if len(pks) == 1:
                    field.initial = pks.first()
                    field.widget = forms.HiddenInput()
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

    def get_instructions(self):
        return None

    def get_reload_areas(self):
        reload = getattr(self.metaclass, 'reload', 'self')
        if isinstance(reload, tuple):
            return ','.join(reload)
        return reload or ''

    def is_modal(self):
        return getattr(self.metaclass, 'modal', True) if hasattr(self, 'Meta') else True

    def has_permission(self, user):
        return user.is_superuser

    def check_permission(self, user):
        return user.is_superuser or self.has_permission(user)

    @classmethod
    def check_fake_permission(cls, request, instance=None, instantiator=None):
        if request and not request.user.is_superuser:
            checker = PermissionChecker(request, instance, instantiator, getattr(cls, 'Meta', None))
            has_permission = cls.has_permission(checker, request.user)
            return cls.check_permission(checker, request.user) if has_permission is None else has_permission
        return True

    def __str__(self):
        return self.html()

    def html(self):
        if self.response:
            if 'html' in self.response:
                return self.response['html']
            else:
                js = '<script>{}</script>'
                if self.response['url'] == '.':
                    display_messages = True
                    js = js.format('$(document).reload();')
                elif self.response['url'] == '..':
                    display_messages = 'modal' in self.request.GET
                    js = js.format('$(document).back();')
                else:
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

            if isinstance(field, forms.DateTimeField):
                classes.append('date-time-input')

            if isinstance(field, forms.DateField):
                classes.append('date-input')

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
                field.widget.attrs['data-choices-url'] = '{}?action_choices={}'.format(
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

    def redirect(self, url=None, message=None, style='success'):
        if url is None:
            url = '..' if self.fields or self.is_modal() else '.'
            # if url == '..' and not self.get_refresh():
            #     url = '.'
        self.response.update(type='redirect', url=url)
        if message is None:
            message = getattr(self.metaclass, 'message', None)
        if message and self.request.path.startswith('/app/'):
            messages.add_message(self.request, messages.SUCCESS, message)
            self.response.update(message=message, style=style)

    def run(self, *tasks, message=None):
        for task in tasks:
            task.start(self.request)
        if len(tasks) > 1:
            self.redirect(message=message or 'Tarefas iniciadas com sucesso')
        elif message:
            self.redirect(message=message)
        else:
            self.redirect('/app/api/task/{}/'.format(task.task_id), message=message)

    def display(self, data, template='app/default.html'):
        if isinstance(data, dict):
            ctx = data
        else:
            ctx = dict(form=self, data=data.contextualize(self.request).html())
        self.response.update(
            html=render_to_string([template], ctx, request=self.request)
        )

    def submit(self):
        if self.instances:
            for instance in self.instances:
                self.instance = instance
                self._post_clean()
                self.save()
        else:
            self.save()
        self.redirect(message='Ação realizada com sucesso.')

    def process(self):
        try:
            response = self.submit()
            if isinstance(response, HttpResponse):
                raise ReadyResponseException(response)
        except forms.ValidationError as e:
            if self.request.path.startswith('/app/'):
                message = 'Corrija os erros indicados no formulário'
                messages.add_message(self.request, messages.WARNING, message)
            self.add_error(None, e.message)
        except BaseException as e:
            if isinstance(e, ReadyResponseException):
                raise e
            traceback.print_exc()
            if self.request.path.startswith('/app/'):
                message = 'Ocorreu um erro no servidor: {}'.format(e)
                messages.add_message(self.request, messages.WARNING, message)
            self.add_error(None, message)

    def display(self):
        return None

    def output(self, data, template=None):
        if template:
            self.output_data = render_to_string(template, data, request=self.request)
        else:
            self.output_data = data

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

    def values(self, *names):
        from sloth.core.base import ValueSet
        return ValueSet(self, names)