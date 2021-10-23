# -*- coding: utf-8 -*-

from django.middleware.csrf import get_token
from django.forms import *
from django.utils.safestring import mark_safe


class FormMixin:

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
    def get_metadata(cls, path=None):
        form_name = cls.__name__
        meta = getattr(cls, 'Meta', None)
        name = form_name
        target = 'model'
        icon = None
        style = 'primary'
        method = 'get'
        batch = False
        if meta:
            name = getattr(meta, 'name', form_name)
            icon = getattr(meta, 'icon', None)
            style = getattr(meta, 'style', 'primary')
            method = getattr(meta, 'method', 'post')
            batch = getattr(meta, 'batch', False)
        if path:
            if hasattr(cls, 'instances'):
                target = 'queryset' if batch else 'instance'
                path = '{}{{id}}/{}/'.format(path, form_name.lower())
            else:
                path = '{}{}/'.format(path, form_name.lower())
        metadata = dict(name=name, target=target)
        if getattr(meta, 'batch', False):
            metadata.update(batch=True)
        metadata.update(method=method, icon=icon, style=style, path=path)
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

    def __str__(self):
        html = list()
        csrf_token = get_token(self.request)
        html.append('<form action="" method="{}">'.format(self.get_method()))
        html.append('<input name="csrfmiddlewaretoken" type="hidden" value="{}"/>'.format(csrf_token))
        html.append(self.as_p())
        html.append('<input class="btn-success" type="submit" value="Submit">')
        html.append('</form>')
        return mark_safe(''.join(html))


class Form(FormMixin, Form):
    def __init__(self, *args, **kwargs):
        self.instance = None
        self.message = 'Ação realizada com sucesso'
        self.related = kwargs.pop('related', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class ModelForm(FormMixin, ModelForm):

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
