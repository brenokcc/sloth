# -*- coding: utf-8 -*-
from django.forms import *


class Form(Form):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class ModelForm(ModelForm):
    TARGET = 'class'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)

    def submit(self):
        return self.save()


class InstanceForm(ModelForm):
    TARGET = 'instance'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def submit(self):
        return self.save()


class QuerySetForm(InstanceForm):
    TARGET = 'queryset'

    def __init__(self, *args, **kwargs):
        if 'instances' in kwargs:
            self.instances = kwargs.pop('instances')
        super().__init__(*args, **kwargs)

    def submit(self):
        for instance in self.instances:
            self.instance = instance
            self._post_clean()
            super().save()
