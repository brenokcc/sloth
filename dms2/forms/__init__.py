# -*- coding: utf-8 -*-

from django.forms import *


class FormMixin:

    def serialize(self):
        if self.message:
            return self.message
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

    @classmethod
    def get_metadata(cls, path=None):
        metadata = {}
        form_name = cls.__name__
        meta = getattr(cls, 'Meta', None)
        if meta:
            name = getattr(meta, 'name', form_name)
            icon = getattr(meta, 'icon', None)
            style = getattr(meta, 'style', 'primary')
            method = getattr(meta, 'method', 'post')
            metadata.update(name=name, icon=icon, style=style, method=method)
            if getattr(meta, 'batch', False):
                metadata.update(batch=True)
        else:
            metadata.update(name=form_name, icon=None, style='primary', method='get')
        if path:
            if hasattr(cls, 'instances'):
                target = 'queryset'
                path = '{}{{id}}/{}/'.format(path, form_name.lower())
            else:
                target = 'model'
                path = '{}{}/'.format(path, form_name.lower())
            metadata.update(target=target, path=path)
        return metadata

    def get_method(self):
        meta = getattr(self, 'Meta', None)
        return getattr(meta, 'method', 'post') if meta else 'post'

    def has_permission(self, user):
        return self and user.is_superuser

    def has_add_permission(self, user):
        return self.instance and self.instance.has_add_permission(user)

    def has_edit_permission(self, user):
        return self.instance and self.instance.has_edit_permission(user)

    def has_delete_permission(self, user):
        return self.instance and self.instance.has_add_permission(user)


class Form(Form, FormMixin):
    def __init__(self, *args, **kwargs):
        self.instance = None
        self.message = 'Ação realizada com sucesso'
        self.related = kwargs.pop('related', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class ModelForm(ModelForm, FormMixin):

    def __init__(self, *args, **kwargs):
        self.message = None
        self.request = kwargs.pop('request', None)
        self.related = kwargs.pop('related', None)
        super().__init__(*args, **kwargs)

    def process(self):
        return self.save()

    def notify(self, text='Ação realizada com sucesso', style='sucess', **kwargs):
        self.message = dict(type='message', text=text, style=style, **kwargs)


class QuerySetForm(ModelForm):
    instances = []

    def __init__(self, *args, **kwargs):
        self.instances = kwargs.pop('instances')
        super().__init__(*args, **kwargs)

    def process(self):
        for instance in self.instances:
            self.instance = instance
            self._post_clean()
            self.save()
