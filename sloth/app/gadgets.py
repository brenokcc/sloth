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

    def render(self):
        template_name = '{}.html'.format(self.__class__.__name__.lower())
        return mark_safe(render_to_string([self.template or template_name], dict(self=self), request=self.request))


class Cards(Gadget):
    template = 'app/gadgets/cards.html'

    def __init__(self, request):
        self.items = []
        super().__init__(request)
        for model in apps.get_models():
            if model().has_list_permission(request.user) or model().has_permission(request.user):
                if hasattr(model.metaclass(), 'icon'):
                    self.items.append(dict(
                        url=model.get_list_url('/app'),
                        label=model.metaclass().verbose_name_plural,
                        count=model.objects.all().apply_role_lookups(request.user).count(),
                        icon=model.metaclass().icon
                    ))
