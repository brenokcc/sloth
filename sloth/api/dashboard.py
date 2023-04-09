import inspect
from django.apps import apps
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from .templatetags.tags import mobile
from sloth.api.exceptions import ReadyResponseException
from sloth.utils import pretty
from ..actions import Action, ACTIONS

DASHBOARDS = []


class DashboardType(type):

    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        DASHBOARDS.append(cls)
        return cls


class Dashboard(metaclass=DashboardType):

    def __init__(self, request):
        self.redirect_url = None
        self.redirect_message = None
        self.request = request
        self.data = dict(
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], tools=[], header={}, footer={}
        )
        self.defined_apps = {}
        self.enabled_apps = set()
        if self.request.user.is_authenticated:
            self.load(request)
        if self.request.path == '/app/dashboard/':
            valueset = self.view()
            if valueset:
                self.append(valueset)
                for data in valueset.get('append'):
                    self.append(data, aside=True)

    def view(self):
        return None

    def redirect(self, url, message=None):
        self.redirect_url = url
        self.redirect_message = message

    def header(self, logo=None, title=None, text=None, shadow=True):
        self.data['header'].update(logo=logo, title=title, text=text, shadow=shadow)

    def footer(self, title=None, text=None, version=None):
        self.data['footer'].update(title=title, text=text, version=version)

    def to_item(self, model, count=True):
        return

    def _load(self, key, items, modal=False, count=False, app=None):
        allways = 'floating', 'navigation', 'settings', 'actions', 'menu', 'links', 'tools', 'search'
        for cls in items:
            if '.' in cls:
                tokens = cls.split('.')
                cls = apps.get_model(*tokens[0:2])
                subset = 'all' if len(tokens) == 2 else tokens[-1]
            else:
                subset = None
                cls = ACTIONS[cls]
            add_item = True
            if app:
                self.enabled_apps.add(app)
                add_item = self.request.session.get('app_name') == app
            if add_item:
                if subset is None:
                    if cls.check_fake_permission(request=self.request):
                        metadata = cls.get_metadata()
                        self.data[key].append(dict(
                            url='/app/dashboard/{}/'.format(metadata['key']), modal=metadata['modal'] and modal,
                            label=metadata['name'], icon=metadata['icon'], app=app
                        ))
                else:
                    qs = getattr(cls.objects, subset)()
                    if self.request.user.is_superuser or qs.has_permission(self.request.user):
                        if key in allways or self.request.path == '/app/dashboard/':
                            label = cls.metaclass().verbose_name_plural
                            if subset and subset != 'all':
                                label = '{} {}'.format(label, qs.get_attr_metadata(subset)[0])
                            url = cls.get_list_url('/app', subset)
                            for item in self.data[key]:
                                add_item = add_item and not item['url'] == url
                            if add_item:
                                self.data[key].append(
                                    dict(
                                        url=url, label=label, modal=modal,
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

    def links(self, *items, modal=False, app=None):
        self._load('links', items, modal=modal, app=app)

    def add_link(self, url, label, app=None):
        self._item('links', url, label, app=app)

    def shortcuts(self, *items, app=None):
        self._load('shortcuts', items, app=app)

    def add_shortcut(self, url, label, icon, app=None):
        self._item('shortcut', url, label, icon, app=app)

    def actions(self, *items, app=None):
        if mobile(self.request):
            self._load('search', items, app=app)
        else:
            self._load('actions', items, app=app)

    def add_action(self, url, label, icon, app=None):
        if mobile(self.request):
            self._item('search', url, label, icon, app=app)
        else:
            self._item('actions', url, label, icon, app=app)

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

    def settings(self, *items, modal=False, app=None):
        self._load('settings', items, modal=modal, app=app)

    def append(self, data, aside=False, grid=1):
        if inspect.isclass(data) and issubclass(data, Action):
            action = data(request=self.request)
            action.is_valid()
            if aside:
                self.data['right'].append(action.html())
            else:
                self.data['center'].append((grid, action.html()))
        elif self.request.path == '/app/dashboard/':
            if aside and hasattr(data, 'compact'):
                data.compact()
            if self.request.path == '/app/dashboard/':
                html = str(data.contextualize(self.request))
                if aside:
                    self.data['right'].append(html)
                else:
                    self.data['center'].append((grid, html))

    def extend(self, template, aside=False, grid=1, **data):
        if self.request.path == '/app/dashboard/':
            html = mark_safe(render_to_string(template, data, request=self.request))
            if aside:
                self.data['right'].append(html)
            else:
                self.data['center'].append((grid, html))

    def load(self, request):
        pass

    def attr(self, name, source=False):
        valueset = self.value_set(name).attr(name)
        if source:
            valueset = valueset.source(name)
        return valueset

    def value_set(self, *names):
        from sloth.core.base import ValueSet
        return ValueSet(self, names)

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return attr is None or attr(user)

    @staticmethod
    def objects(model_name):
        return apps.get_model(model_name).objects

    @classmethod
    def get_attr_metadata(cls, lookup):
        attr = getattr(cls, lookup)
        template = getattr(attr, '__template__', None)
        metadata = getattr(attr, '__metadata__', None)
        if template:
            if not template.endswith('.html'):
                template = '{}.html'.format(template)
            if not template.startswith('.html'):
                template = 'renderers/{}'.format(template)
        return getattr(attr, '__verbose_name__', lookup), False, template, metadata

    @classmethod
    def action_form_cls(cls, action):
        return ACTIONS.get(action)


class Dashboards:

    def __init__(self, request):
        self.apps = {}
        self.dashboards = []
        self.request = request
        self.data = dict(
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[], tasks=[1, 2, 3],
            floating=[], navigation=[], settings=[], center=[], right=[], actions=[], tools=[], header={}, footer={}
        )
        self.data['navigation'].append(
            dict(url='/app/dashboard/', label='Principal', icon='house', app=None)
        )
        for cls in DASHBOARDS:
            dashboard = cls(request)
            if dashboard.redirect_url:
                raise ReadyResponseException(HttpResponseRedirect(dashboard.redirect_url))
            for k, v in dashboard.data.items():
                self.data[k].update(v) if k in ['header', 'footer'] else self.data[k].extend(v)
            self.apps.update(dashboard.defined_apps)
            for name in dashboard.enabled_apps:
                self.apps[name]['enabled'] = True
            self.dashboards.append(dashboard)

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
            raise ReadyResponseException(HttpResponseRedirect('/app/dashboard/'))

        if self.request.user.is_superuser:
            self.superuser()

    def main(self):
        for dashboard in self.dashboards:
            if dashboard.view.__func__ != Dashboard.view:
                return dashboard

    def superuser(self):
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
                for item in self.data['search']:
                    add_item = add_item and not item['url'] == url
                if add_item:
                    item = dict(label=pretty(str(model_verbose_name_plural)), description=None, url=url, icon=icon, subitems=[], app=None)
                    self.data['search'].append(item)
