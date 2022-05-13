from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from functools import lru_cache
from sloth.utils import pretty

INITIALIZE = True
DASHBOARDS = []


def initilize():
    global INITIALIZE
    if INITIALIZE:
        INITIALIZE = False
        for app_label in settings.INSTALLED_APPS:
            module = '{}.{}'.format(app_label, 'dashboard')
            try:
                __import__(module, fromlist=app_label.split('.'))
                # print('{} dashboard initilized!'.format(module))
            except ImportError:
                # print(app_label, module, 'ERROR')
                pass


class DashboardType(type):

    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        DASHBOARDS.append(cls)
        return cls


class Dashboard(metaclass=DashboardType):

    def __init__(self, request):
        self.request = request
        self.data = dict(
            info=[], warning=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[]
        )
        self.load(request)

    def to_item(self, model, count=True):
        return

    def _load(self, key, models):
        for model in models:
            if model().has_list_permission(self.request.user) or model().has_permission(self.request.user):
                self.data[key].append(
                    dict(
                        url=model.get_list_url('/app'),
                        label=model.metaclass().verbose_name_plural,
                        count=model.objects.all().apply_role_lookups(self.request.user).count(),
                        icon=getattr(model.metaclass(), 'icon', None)
                    )
                )

    def _item(self, key, url, label, icon, count=None):
        self.data[key].append(
            dict(url=url, label=label, count=count, icon=icon)
        )

    def info(self, *models):
        self._load('info', models)

    def warning(self, *models):
        self._load('warning', models)

    def menu(self, *models):
        self._load('menu', models)

    def links(self, *models):
        self._load('links', models)

    def add_link(self, url, label):
        self._item(self, 'links', url, label)

    def shortcuts(self, *models):
        self._load('shortcuts', models)

    def add_shortcut(self, url, label, icon):
        self._item(self, 'shortcut', url, label, icon)

    def cards(self, *models):
        self._load('cards', models)

    def floating(self, *models):
        self._load('floating', models)

    def navigation(self, *models):
        self._load('navigation', models)

    def add_navigation(self, url, label, icon):
        self._item('navigation', url, label, icon)

    def settings(self, *models):
        self._load('settings', models)

    def append(self, data, aside=False):
        if aside and hasattr(data, 'compact'):
            data.compact()
        if self.request.path == '/app/':
            self.data['right' if aside else 'center'].append(
                str(data.contextualize(self.request))
            )

    def extend(self, data, template, aside=False):
        if self.request.path == '/app/':
            html = mark_safe(render_to_string(template, data, request=self.request))
            self.data['right' if aside else 'center'].append(html)

    def load(self, request):
        pass


class Dashboards:

    def __init__(self, request):
        self.request = request
        self.data = dict(
            info=[], warning=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[]
        )
        self.data['navigation'].append(
            dict(url='/app/', label='Principal', icon='house')
        )
        if self.request.user.is_superuser:
            self.data['menu'].extend(self.superuser_menu())
        initilize()
        for cls in DASHBOARDS:
            dashboard = cls(request)
            for key in dashboard.data:
                self.data[key].extend(dashboard.data[key])

    @lru_cache
    def superuser_menu(self):
        from django.apps import apps
        from .. import PROXIED_MODELS
        items = []
        for model in apps.get_models():
            if model not in PROXIED_MODELS:
                app_label = model.metaclass().app_label
                model_name = model.metaclass().model_name
                model_verbose_name_plural = model.metaclass().verbose_name_plural
                icon = getattr(model.metaclass(), 'icon', None)
                url = '/app/{}/{}/'.format(app_label, model_name)
                item = dict(label=pretty(str(model_verbose_name_plural)), description=None, url=url, icon=icon, subitems=[])
                items.append(item)
        return items

    def __str__(self):
        return mark_safe(render_to_string('app/dashboard/dashboards.html', dict(data=self.data), request=self.request))



