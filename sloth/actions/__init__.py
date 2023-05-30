# -*- coding: utf-8 -*-
import datetime
import math
import re
import traceback
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache

from django.apps import apps
from django.contrib import messages
from django.db import transaction
from django.forms.models import ModelFormMetaclass
from django.forms import *
from .fields import *
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify

from . import inputs
from .fields import *
from ..core.queryset import QuerySet
from sloth.api.exceptions import JsonReadyResponseException, ReadyResponseException, HtmlReadyResponseException
from ..utils import to_api_params, to_snake_case
from ..utils.formatter import format_value
from ..utils.http import FileResponse

ACTIONS = {}
EXPOSE = []


class PermissionChecker:

    def __init__(self, request, instance=None, instantiator=None, metaclass=None):
        self.request = request
        self.instance = instance
        self.instantiator = instantiator
        self.metaclass = metaclass

    def has_permission(self, user):
        return self and user


class ActionDefaultMetaClass:
    modal = True


class ActionMetaclass(ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):
        if 'Meta' in attrs:
            if hasattr(attrs['Meta'], 'model'):
                if isinstance(attrs['Meta'].model, str):
                    attrs['Meta'].model = apps.get_model(attrs['Meta'].model)
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
        else:
            bases += forms.Form,
            attrs['Meta'] = ActionDefaultMetaClass
        cls = super().__new__(mcs, name, bases, attrs)
        ACTIONS[name] = cls
        ACTIONS[to_snake_case(name)] = cls
        if 'ActionView' in [k.__name__ for k in bases]:
            EXPOSE.append(to_snake_case(name))
        return cls


class DecimalField(forms.DecimalField):
    def clean(self, value):
        if value:
            value = value.replace('.', '').replace(',', '.')
        value = super().clean(value)
        return value


class TextField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=forms.Textarea())
        super().__init__(*args, **kwargs)


class BooleanChoiceField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs.update(widget=forms.Select(), choices=[['', ''], [1, 'Sim'], [0, 'Não']])
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if value == '':
            if self.required:
                raise ValidationError('Selecione uma opção')
            return None
        return bool(int(value))


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
        self.queryset = kwargs.pop('queryset', None)
        self.instances = kwargs.pop('instances', None)
        self.metaclass = getattr(self, 'Meta')

        self.show_form = True
        self.can_be_closed = False
        self.can_be_reloaded = False
        self.content = dict(top=[], left=[], center=[], right=[], bottom=[], info=[], alert=[], danger=[])
        self.on_change_data = dict(show=[], hide=[], set=[], show_fieldset=[], hide_fieldset=[])

        if forms.ModelForm in self.__class__.__bases__:
            self.instance = kwargs.get('instance', None)
        else:
            self.instance = kwargs.pop('instance', None)

        if self.instance is None and self.instances is not None and self.instances.exists():
            self.instance = self.instances.first()

        if self.has_url_posted_data():
            for k in self.request.GET:
                if k.startswith('post__'):
                    if 'data' not in kwargs:
                        kwargs['data'] = {}
                    kwargs['data'][k.split('__')[-1]] = self.request.GET[k]

        if 'data' not in kwargs:
            if self.get_api_name() in self.request.GET or self.get_api_name() in self.request.POST or self.request.path.startswith('/api/'):
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
        if self.instance is not None and hasattr(self.instance, 'autouser') and not self.instance.autouser_id:
            self.instance.autouser = self.request.user
            if 'autouser' in self.fields:
                del self.fields['autouser']

        for name in self.fields:
            if name != 'data':
                setattr(self, name, self.initial.get(name, None))
        self.asynchronous = getattr(self.metaclass, 'asynchronous', None) and self.request.GET.get('synchronous') is None

        related_field_name = getattr(self.metaclass, 'related_field', None)
        if related_field_name:
            setattr(self.instance, related_field_name, self.instantiator)
            if related_field_name in self.fields:
                del self.fields[related_field_name]

        for field_name in self.fields:
            field = self.fields[field_name]
            if hasattr(field, 'queryset'):
                if getattr(field, 'username_lookup', None):
                    pks = list(field.queryset.filter(**{field.username_lookup: self.request.user}).values_list('pk', flat=True)[0:2])
                    if len(pks) == 1:
                        field.queryset = field.queryset.model.objects.filter(pk=pks[0])
                        field.initial = pks[0]
                        self.initial[field_name] = field.initial
                        # field.widget = forms.HiddenInput()
                        field.widget.attrs['class'] = '{} disabled'.format(field.widget.attrs.get('class', ''))
                        field.widget.attrs['readonly'] = 'readonly'
                else:
                    field.queryset = field.queryset.contextualize(self.request).apply_role_lookups(self.request.user)

        self.response = {}
        self.fieldsets = {}
        self.one_to_one = {}
        self.one_to_many = {}

        confirmation = self.requires_confirmation()
        if confirmation:
            help_text = confirmation if isinstance(confirmation, str) else ''
            self.fields['confirmation'] = forms.BooleanField(
                label='', initial='on', required=False, help_text=help_text,
                widget=forms.HiddenInput()
            )

    def render(self, template_name, **context):
        return HttpResponse(render_to_string([template_name], context, request=self.request))

    def get_verbose_name(self):
        return self.get_metadata().get('name')

    def get_image(self):
        return self.get_metadata().get('image')

    def has_url_posted_data(self):
        return 'post__{}'.format(self.get_api_name()) in self.request.GET

    def closable(self, flag=True):
        self.can_be_closed = flag

    def reloadable(self, flag=True):
        self.can_be_reloaded = flag

    def info(self, text):
        if text:
            self.content['info'].append(text)

    def alert(self, text):
        if text:
            self.content['alert'].append(text)

    def danger(self, text):
        if text:
            self.content['danger'].append(text)

    def parameters(self):
        data = {}
        for token in self.request.path.split('/'):
            if '=' in token:
                k, v = token.split('=')
                data[k] = int(v) if v.isdigit() else v
        return data

    def parameter(self, name, default=None):
        return self.parameters().get(name, default)

    def objects(self, model_name):
        return apps.get_model(model_name).objects.contextualize(self.request)

    def clear(self):
        self.show_form = False
        for k, v in self.content.items():
            if k != 'bottom':
                v.clear()

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
        related_field = getattr(self.instance, 'related_field', None) if self.instance is not None else None
        if related_field and related_field in self.fields:
            del self.fields[related_field]
        fieldsets = getattr(self.metaclass, 'fieldsets', None)
        if fieldsets is None:
            fieldsets = {}
            if self.fields:
                field_names = [
                    name for name in self.fields.keys() if (
                            name not in self.get_one_to_one_field_names()
                            and name not in self.get_one_to_many_field_names()
                            and name not in ('confirmation', related_field)
                    )
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
        if hasattr(self.instance, '__roles__'):
            with transaction.atomic():
                self._save()
        else:
            self._save()

    def _save(self, *args, **kwargs):

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
            for i in range(0, 10):
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

    def get_allowed_attrs(self, recursive=True):
        return []

    @classmethod
    def get_api_name(cls):
        return to_snake_case(cls.__name__)

    @classmethod
    @lru_cache
    def get_metadata(cls, path=None, target=None):
        metaclass = getattr(cls, 'Meta', None)
        if metaclass:
            target = target
            name = getattr(metaclass, 'verbose_name', re.sub("([a-z])([A-Z])", "\g<1> \g<2>", cls.__name__))
            submit = getattr(metaclass, 'submit_label', name)
            icon = getattr(metaclass, 'icon', None)
            ajax = getattr(metaclass, 'ajax', True)
            modal = getattr(metaclass, 'modal', True)
            style = getattr(metaclass, 'style', 'primary')
            method = getattr(metaclass, 'method', 'post')
            auto_reload = getattr(metaclass, 'auto_reload', None)
            image = getattr(metaclass, 'image', None)
        else:
            name, submit, icon, ajax, modal, style, method, auto_reload, image = (
                'Enviar', 'Enviar', None, True, 'modal', 'primary', 'get', None, None
            )
        if path:
            path, *params = path.split('?')
            if target in ('queryset', 'instance'):
                path = '{}{{id}}/{}/'.format(path, cls.get_api_name())
            else:
                path = '{}{}/'.format(path, cls.get_api_name())
            if params:
                path = '{}?{}'.format(path, params[0])
        metadata = dict(
            type='form', key=cls.get_api_name(), name=name, submit=submit, target=target,
            method=method, icon=icon, style=style, ajax=ajax, path=path, modal=modal,
            auto_reload=auto_reload, image=image
        )
        return metadata

    def get_method(self):
        return getattr(self.metaclass, 'method', 'post') if hasattr(self, 'Meta') else 'post'

    def get_instances(self):
        if self.instances is not None:
            return self.instances
        elif self.queryset is not None:
            return self.queryset
        elif self.instance:
            return type(self.instance).objects.filter(pk=self.instance.pk)
        return []

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
            return has_permission
            ### return cls.check_permission(checker, request.user) if has_permission is None else has_permission
        return True

    def __str__(self):
        return self.html()

    def get_alternative_links(self):
        return []

    def html(self):

        for name, field in self.fields.items():
            classes = field.widget.attrs.get('class', '').split()
            if isinstance(field.widget, forms.CheckboxInput):
                classes.append('form-check-input')
            elif isinstance(field.widget, forms.widgets.Input):
                classes.append('form-control')

            if isinstance(field, forms.DateField):
                field.widget = RegionalDateWidget()
                classes.append('date-input')
                if name in self.initial and self.initial[name] and isinstance(self.initial[name], str) and '/' in self.initial[name]:
                    self.initial[name] = datetime.datetime.strptime(self.initial[name], '%d/%m/%Y').strftime('%Y-%m-%m')

            if isinstance(field, forms.DateTimeField):
                field.widget = RegionalDateTimeWidget()
                classes.append('date-time-input')
                if name in self.initial and self.initial[name] and isinstance(self.initial[name], str) and '/' in self.initial[name]:
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

            if hasattr(field, 'picker'):
                grouper = field.picker if isinstance(field.picker, str) else None
                if isinstance(field, forms.ModelMultipleChoiceField):
                    field.widget = inputs.MultiplePickInput(field.queryset, grouper=grouper)
                else:
                    field.widget = inputs.PickInput(field.queryset, grouper=grouper)

            if getattr(field, 'addable', False):
                has_permission = field.queryset.model().has_add_permission(self.request.user)
                has_permission = has_permission or field.queryset.model().has_permission(self.request.user)
                help_text = '<div>{}</div>'.format(field.help_text) if field.help_text else ''
                link = '<a style="text-decoration:none" class="popup" href="/app/{}/{}/add/">Adicionar</a>'.format(
                    field.queryset.model.metaclass().app_label, field.queryset.model.metaclass().model_name
                )
                help_text = '<div style="float:right">{}</div>'.format(link) + help_text
                if has_permission:
                    field.help_text = help_text

            field.widget.attrs['class'] = ' '.join(classes)
        return mark_safe(
            render_to_string(
                ['dashboard/form.html'], dict(
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

    def check_ouput(self, output, submit=False):
        from ..core.valueset import ValueSet
        position = 'bottom' if submit else 'center'
        if type(output) == dict:
            template_name = 'actions/{}.html'.format(self.get_api_name())
            self.content[position].append(render_to_string([template_name], output, request=self.request))
        elif type(output) == str and output[-5:].split('.')[-1] in FileResponse.CONTENT_TYPES.keys():
            raise ReadyResponseException(FileResponse(output))
        elif type(output) in (str, int, float, Decimal, datetime.date):
            raise ReadyResponseException(HttpResponse(str(output)))
        elif isinstance(output, HttpResponse):
            raise ReadyResponseException(output)
        elif isinstance(output, ValueSet) or isinstance(output, QuerySet):
            if submit:
                path = '{}{}/'.format(self.request.path, 'submit') if self.request.POST else None
            else:
                path = '{}{}/'.format(self.request.path, 'view')
            self.content[position].append(output.contextualize(self.request).html(path=path))
        elif output is not None:
            raise Exception()

        if self.request.path.startswith('/app/') and self.response and submit:
            js = '<script>{}</script>'
            display_messages = True
            url = self.response.get('url')
            if self.response.get('dispose'):
                js = js.format('fade{}({});'.format(self.get_metadata().get('key'), self.response.get('dispose')))
            elif url == '.':
                if 'modal' in self.request.GET:
                    js = js.format('$(document).popup("{}");'.format(self.request.path))
                else:
                    js = js.format('$(document).refresh([]);'.format(self.get_metadata().get('key')))
            elif url == '..':
                display_messages = 'modal' in self.request.GET
                js = js.format('$(document).back().refresh([]);')
            elif url:
                display_messages = False
                js = js.format('$(document).redirect("{}");'.format(self.response['url']))
            html = render_to_string('dashboard/messages.html', request=self.request) if display_messages else ''
            raise ReadyResponseException(HttpResponse('<!---->{}{}<!---->'.format(js, html)))

        if self.request.path.startswith('/app/') and self.response and not submit:
            stack = self.request.session.get('stack', [])
            url = self.response.get('url')
            if url in ('.', '..') and len(stack) > 1:
                url = stack[-2]
            raise ReadyResponseException(HttpResponseRedirect(url))

        return output

    def is_valid(self):
        if self.asynchronous:
            return False
        self.check_ouput(self.view())
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
            if value == 'unknown':
                value = None
            getattr(self, 'on_{}_change'.format(field_name))(value)
            raise JsonReadyResponseException(self.on_change_data)
        return super().is_valid()

    def choices(self, field_name, q=None):
        field = self.fields[field_name]
        if self.__class__.__name__ in ('Add', 'Edit'):
            attr = getattr(self.instance, 'get_{}_queryset'.format(field_name), None)
            if attr:
                for name in self.fields:
                    if isinstance(self.fields[name], MultipleChoiceField):
                        value = self.request.GET.getlist(name)
                    if isinstance(self.fields[name], ModelMultipleChoiceField):
                        value = self.request.GET.getlist(name)
                    else:
                        value = self.request.GET.get(name)
                        if value:
                            setattr(self.instance, name, self.fields[name].clean(value))
        else:
            attr = getattr(self, 'get_{}_queryset'.format(field_name), None)
        self.data.update(self.request.GET)
        qs = field.queryset if attr is None else attr(field.queryset)

        total = qs.count()
        qs = qs.search(q=q) if q else qs
        items = [dict(id=value.id, text=str(value), html=value.get_select_display()) for value in qs[0:25]]
        return dict(total=total, page=1, pages=math.ceil((1.0 * total) / 25), q=q, items=items )

    def dispose(self, milleseconds=2000):
        self.response.update(dispose=milleseconds)

    def reload(self):
        return self.redirect('.')

    def message(self, text='Ação realizada com sucesso.', style='success', milleseconds=60000):
        level = dict(success=messages.SUCCESS, warning=messages.WARNING, info=messages.INFO)[style]
        if self.request.path.startswith('/app/'):
            messages.add_message(self.request, level, text)
        else:
            self.response.update(message=dict(text=text, style=style, milleseconds=milleseconds))

    def redirect(self, url=None):
        if url is None:
            url = '..' if getattr(self, 'fields', None) or self.is_modal() else '.'
        self.response.update(type='redirect', url=url)
        if not self.get_metadata()['ajax']:
            raise ReadyResponseException(HttpResponseRedirect(url))

    def run(self, *tasks):
        for task in tasks:
            task.start(self.request)
        if len(tasks) > 1:
            self.redirect()
        else:
            self.redirect('/app/api/task/{}/'.format(task.task_id))

    def submit(self):
        if self.instances:
            for instance in self.instances:
                self.instance = instance
                if self.has_permission(self.request.user):
                    self._post_clean()
                    self.save()
        else:
            self.save()
        self.message()
        self.redirect()

    def process(self):
        try:
            return self.check_ouput(self.submit(), True)
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

    def send_mail(self, to, subject, content, from_email=None):
        from sloth.api.models import Email
        Email.objects.send(to, subject, content, from_email)


class ActionView(Action):
    pass
