# -*- coding: utf-8 -*-
from django.forms import *


class SerializableFormMixin:

    def serialize(self):
        data = {}
        for field_name in self.fields:
            data[field_name] = self.data.get(field_name)
        return data


class Form(Form, SerializableFormMixin):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class ModelForm(ModelForm, SerializableFormMixin):

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
