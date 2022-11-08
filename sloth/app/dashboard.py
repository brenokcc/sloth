from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from sloth.app.templatetags.tags import mobile
from sloth.exceptions import ReadyResponseException
from sloth.utils import pretty
from.actions import ExecuteQuery, ExecuteScript


DASHBOARDS = []


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
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], tools=[]
        )
        self.extra = {}
        self.defined_apps = {}
        self.enabled_apps = set()
        if self.request.user.is_authenticated:
            self.load(request)

    def header(self, logo=None, title=None, text=None, shadow=True):
        self.extra['header'] = dict(logo=logo, title=title, text=text, shadow=shadow)

    def footer(self, title=None, text=None, version=None):
        self.extra['footer'] = dict(title=title, text=text, version=version)

    def to_item(self, model, count=True):
        return

    def _load(self, key, items, app=None, count=False):
        allways = 'floating', 'navigation', 'settings', 'actions', 'menu', 'links', 'tools', 'search'
        for cls in items:
            add_item = True
            if app:
                self.enabled_apps.add(app)
                add_item = self.request.session.get('app_name') == app
            if add_item:
                if hasattr(cls, 'check_fake_permission'):
                    if cls.check_fake_permission(request=self.request):
                        metadata = cls.get_metadata()
                        self.data[key].append(dict(
                            url='/app/action/{}/'.format(metadata['key']), modal=metadata['modal'],
                            label=metadata['name'], icon=metadata['icon'], app=app
                        ))
                else:
                    if self.request.user.is_superuser or cls.objects.all().has_permission(self.request.user):
                        if key in allways or self.request.path == '/app/':
                            url = cls.get_list_url('/app')
                            for item in self.data[key]:
                                add_item = add_item and not item['url'] == url
                            if add_item:
                                self.data[key].append(
                                    dict(
                                        url=url,
                                        label=cls.metaclass().verbose_name_plural,
                                        count=cls.objects.all().apply_role_lookups(self.request.user).count() if count else None,
                                        icon=getattr(cls.metaclass(), 'icon', None),
                                        app=app
                                    )
                                )

    def _item(self, key, url, label, icon, count=None, app=None):
        self.data[key].append(
            dict(url=url, label=label, count=count, icon=icon, app=app)
        )

    def info(self, *items, app=None):
        self._load('info', items, app=app)

    def warning(self, *items, app=None):
        self._load('warning', items, app=app)

    def search(self, *items, app=None):
        self._load('search', items, app=app)

    def menu(self, *items, app=None):
        if mobile(self.request):
            self._load('search', items, app=app)
        else:
            self._load('menu', items, app=app)

    def links(self, *items, app=None):
        self._load('links', items, app=app)

    def add_link(self, url, label, app=None):
        self._item(self, 'links', url, label, app=app)

    def shortcuts(self, *items, app=None):
        self._load('shortcuts', items, app=app)

    def add_shortcut(self, url, label, icon, app=None):
        self._item(self, 'shortcut', url, label, icon, app=app)

    def actions(self, *items, app=None):
        if mobile(self.request):
            self._load('search', items, app=app)
        else:
            self._load('actions', items, app=app)

    def add_action(self, url, label, icon, app=None):
        if mobile(self.request):
            self._item(self, 'search', url, label, icon, app=app)
        else:
            self._item(self, 'actions', url, label, icon, app=app)

    def add_app(self, label, icon, hide=False):
        url = '/app/?toggle-application={}'.format(label)
        self.defined_apps[label] = dict(label=label, icon=icon, hide=hide, url=url, enabled=False)

    def cards(self, *items, app=None):
        self._load('cards', items, app=app, count=True)

    def floating(self, *items, app=None):
        self._load('floating', items, app=app)

    def tools(self, *items, app=None):
        self._load('tools', items, app=app)

    def navigation(self, *items, app=None):
        if mobile(self.request):
            self._load('floating', items, app=app)
        else:
            self._load('navigation', items, app=app)

    def add_navigation(self, url, label, icon, app=None):
        if mobile(self.request):
            self._item('floating', url, label, icon, app=app)
        else:
            self._item('navigation', url, label, icon, app=app)

    def settings(self, *items, app=None):
        self._load('settings', items, app=app)

    def append(self, data, aside=False, grid=1):
        if self.request.path == '/app/':
            if aside and hasattr(data, 'compact'):
                data.compact()
            if self.request.path == '/app/':
                html = str(data.contextualize(self.request))
                if aside:
                    self.data['right'].append(html)
                else:
                    self.data['center'].append((grid, html))

    def extend(self, template, aside=False, grid=1, **data):
        if self.request.path == '/app/':
            html = mark_safe(render_to_string(template, data, request=self.request))
            if aside:
                self.data['right'].append(html)
            else:
                self.data['center'].append((grid, html))

    def load(self, request):
        pass


class AppDashboard(Dashboard):
    def load(self, request):
        self.tools(ExecuteQuery, ExecuteScript)


class Dashboards:

    def __init__(self, request):

        self.request = request
        self.data = dict(
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], tools=[]
        )
        self.extra = dict(header={}, footer={})
        self.apps = {}
        self.data['navigation'].append(
            dict(url='/app/', label='Principal', icon='house', app=None)
        )
        for cls in DASHBOARDS:
            dashboard = cls(request)
            for key in dashboard.data:
                self.data[key].extend(dashboard.data[key])
            self.apps.update(dashboard.defined_apps)
            if dashboard.extra:
                self.extra.update(dashboard.extra)

        if self.request.user.is_superuser:
            self.superuser_search(self.data['search'])

        for name in dashboard.enabled_apps:
            self.apps[name]['enabled'] = True
        if 'toggle-application' in request.GET:
            for name in self.apps:
                if name == request.GET['toggle-application']:
                    if request.session.get('app_name') == name:
                        del request.session['app_name']
                        del request.session['app_icon']
                    else:
                        request.session['app_name'] = name
                        request.session['app_icon'] = self.apps[name]['icon']
                    request.session.save()
                    break
            raise ReadyResponseException(HttpResponseRedirect('/app/'))

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
                    item = dict(label=pretty(str(model_verbose_name_plural)), description=None, url=url, icon=icon, subitems=[], app=None)
                    items.append(item)
        return items

    def __str__(self):
        return mark_safe(render_to_string('app/dashboard/dashboards.html', dict(data=self.data), request=self.request))



