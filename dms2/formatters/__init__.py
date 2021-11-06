from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

INITIALIZE = True
FORMATTERS = {}


def initilize():
    global INITIALIZE
    if INITIALIZE:
        INITIALIZE = False
        for app_label in settings.INSTALLED_APPS:
            module = '{}.{}'.format(app_label, 'formatters')
            try:
                __import__(module, fromlist=app_label.split('.'))
                print('{} initilized!'.format(module))
            except ImportError:
                # print(app_label, module, 'ERROR')
                pass


class FormatterType(type):

    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        FORMATTERS[getattr(cls, 'name') or cls.__name__.lower()] = cls
        return cls


class Formatter(metaclass=FormatterType):
    name = None
    template = None

    def __init__(self, value, instance=None):
        super().__init__()
        self.value = value
        self.instance = instance

    def render(self, **kwargs):
        context = dict(instance=self.instance, value=self.value, **kwargs)
        template_name = '{}.html'.format(self.__class__.__name__.lower())
        return mark_safe(render_to_string([self.template or template_name], context))

    def __str__(self):
        return self.render()


class Progress(Formatter):
    template = 'adm/formatters/progress.html'

    def render(self):
        return super().render()


class Image(Formatter):
    template = 'adm/formatters/image.html'

    def render(self):
        return super().render()
