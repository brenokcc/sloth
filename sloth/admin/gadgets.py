# -*- coding: utf-8 -*-
from uuid import uuid1

from django.apps import apps
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

INITIALIZE = True
GADGETS = {}


def initilize():
    global INITIALIZE
    if INITIALIZE:
        INITIALIZE = False
        for app_label in settings.INSTALLED_APPS:
            module = '{}.{}'.format(app_label, 'views')
            try:
                __import__(module, fromlist=app_label.split('.'))
                # print('{} initilized!'.format(module))
            except ImportError:
                # print(app_label, module, 'ERROR')
                pass


class GadgetType(type):

    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        if not cls.__module__.startswith('sloth'):
            GADGETS[getattr(cls, 'name', cls.__name__.lower())] = cls
        return cls


class Gadget(metaclass=GadgetType):
    template = None

    def __init__(self, request):
        super().__init__()
        self.request = request

    def render(self, **kwargs):
        template_name = '{}.html'.format(self.__class__.__name__.lower())
        context = kwargs or {}
        context.update(uuid=uuid1().hex, self=self)
        return mark_safe(render_to_string([self.template or template_name], context, request=self.request))


class Cards(Gadget):
    template = 'adm/gadgets/cards.html'

    def render(self):
        items = []
        for model in apps.get_models():
            if model.can_list(self.request.user):
                if hasattr(model.metaclass(), 'icon'):
                    items.append(dict(
                        url=model.get_list_url('/adm'),
                        label=model.metaclass().verbose_name_plural,
                        count=model.objects.count(),
                        icon=model.metaclass().icon
                    ))
        return super().render(items=items)
