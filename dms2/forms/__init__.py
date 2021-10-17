# -*- coding: utf-8 -*-
from django.forms import *


class FormMixin:

    def serialize(self):
        data = {}
        for field_name in self.fields:
            data[field_name] = self.data.get(field_name)
        return data

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
        self.related = kwargs.pop('related', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class ModelForm(ModelForm, FormMixin):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.related = kwargs.pop('related', None)
        super().__init__(*args, **kwargs)

    def process(self):
        return self.save()
    

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
