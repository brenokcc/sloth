import inspect

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from sloth.app.templatetags.tags import mobile
from sloth.db import models
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
            except ImportError as e:
                if not e.name.endswith('dashboard'):
                    raise e


class DashboardType(type):

    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        DASHBOARDS.append(cls)
        return cls


class Dashboard(metaclass=DashboardType):

    def __init__(self, request):
        self.request = request
        self.data = dict(
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], grids=[]
        )
        if self.request.user.is_authenticated:
            self.load(request)

    def to_item(self, model, count=True):
        return

    def _load(self, key, models):
        allways = 'floating', 'navigation', 'settings', 'actions', 'menu', 'links'
        for model in models:
            if model().has_list_permission(self.request.user) or model().has_permission(self.request.user):
                if key in allways or self.request.path == '/app/':
                    url = model.get_list_url('/app')
                    add_item = True
                    for item in self.data[key]:
                        add_item = add_item and not item['url'] == url
                    if add_item:
                        self.data[key].append(
                            dict(
                                url=url,
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

    def search(self, *models):
        self._load('search', models)

    def menu(self, *models):
        if mobile(self.request):
            self._load('search', models)
        else:
            self._load('menu', models)

    def links(self, *models):
        self._load('links', models)

    def add_link(self, url, label):
        self._item(self, 'links', url, label)

    def shortcuts(self, *models):
        self._load('shortcuts', models)

    def add_shortcut(self, url, label, icon):
        self._item(self, 'shortcut', url, label, icon)

    def actions(self, *models):
        if mobile(self.request):
            self._load('search', models)
        else:
            self._load('actions', models)

    def add_action(self, url, label, icon):
        if mobile(self.request):
            self._item(self, 'search', url, label, icon)
        else:
            self._item(self, 'actions', url, label, icon)

    def cards(self, *models):
        self._load('cards', models)

    def grids(self, *grids):
        for grid in grids:
            self.add_grid(grid)

    def add_grid(self, grid, template=None, size=1):
        key = 'grids'
        if isinstance(grid, (list, tuple)):
            html = mark_safe(render_to_string(grid[1], grid[0], request=self.request))
            self.data[key].append(
                dict(
                    html=html,
                    size=size,
                )
            )
        elif isinstance(grid, dict):
            html = mark_safe(render_to_string(template, grid, request=self.request))
            self.data[key].append(
                dict(
                    html=html,
                    size=size,
                )
            )
        elif inspect.isclass(grid) and issubclass(grid, models.Model):
            model = grid
            if model().has_list_permission(self.request.user) or model().has_permission(self.request.user):
                if self.request.path == '/app/':
                    url = model.get_list_url('/app')
                    add_item = True
                    # for item in self.data[key]:
                    #     add_item = add_item and not item.get('url') == url
                    if add_item:
                        self.data[key].append(
                            dict(
                                url=url,
                                label=model.metaclass().verbose_name_plural,
                                count=model.objects.all().apply_role_lookups(self.request.user).count(),
                                icon=getattr(model.metaclass(), 'icon', None),
                                size=size,
                            )
                        )
        elif isinstance(grid, models.QuerySet):
            if self.request.path == '/app/':
                self.data[key].append(
                    dict(
                        html=str(grid.contextualize(self.request)),
                        size=size,
                    )
                )

    def floating(self, *models):
        self._load('floating', models)

    def navigation(self, *models):
        if mobile(self.request):
            self._load('floating', models)
        else:
            self._load('navigation', models)

    def add_navigation(self, url, label, icon):
        if mobile(self.request):
            self._item('floating', url, label, icon)
        else:
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

    def get_qtd_grid(self):
        return 3

    def get_grid_size(self):
        qtd_grid = self.get_qtd_grid()
        return 12//qtd_grid


class Dashboards:

    def __init__(self, request):
        self.request = request
        self.data = dict(
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], grids=[]
        )
        self.data['navigation'].append(
            dict(url='/app/', label='Principal', icon='house')
        )
        initilize()
        for cls in DASHBOARDS:
            dashboard = cls(request)
            self.grid_size = dashboard.get_grid_size()
            for key in dashboard.data:
                self.data[key].extend(dashboard.data[key])
        if self.request.user.is_superuser:
            self.superuser_search(self.data['search'])

    def superuser_search(self, items):
        from django.apps import apps
        from .. import PROXIED_MODELS
        for model in apps.get_models():
            if model not in PROXIED_MODELS:
                app_label = model.metaclass().app_label
                model_name = model.metaclass().model_name
                model_verbose_name_plural = model.metaclass().verbose_name_plural
                icon = getattr(model.metaclass(), 'icon', None)
                url = '/app/{}/{}/'.format(app_label, model_name)
                add_item = True
                for item in items:
                    add_item = add_item and not item['url'] == url
                if add_item:
                    item = dict(label=pretty(str(model_verbose_name_plural)), description=None, url=url, icon=icon, subitems=[])
                    items.append(item)
        return items

    def __str__(self):
        return mark_safe(render_to_string('app/dashboard/dashboards.html', dict(data=self.data, grid_size=self.grid_size), request=self.request))



