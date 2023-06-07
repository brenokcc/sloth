import inspect
from django.apps import apps
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from .templatetags.tags import mobile
from sloth.api.exceptions import ReadyResponseException
from sloth.utils import pretty
from ..actions import Action, ACTIONS
from ..core.valueset import ValueSet
from ..core.queryset import QuerySet

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
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[], plus=[], navbar={},
            floating=[], navigation=[], settings=[], top=[], center=[], right=[], bottom=[], actions=[], tools=[], header={}, footer={},
            styles=[], scripts=[]
        )
        self.defined_apps = {}
        self.enabled_apps = set()
        if self.request.user.is_authenticated:
            self.load(request)
        if self.request.path == '/app/dashboard/':
            obj = self.view()
            if obj:
                if isinstance(obj, ValueSet):
                    self.append(obj)
                    for data in obj.get('append'):
                        self.append(data, aside=True)
                elif isinstance(obj, QuerySet):
                    self.append(obj)

    def view(self):
        return None

    def redirect(self, url, message=None):
        self.redirect_url = url
        self.redirect_message = message

    def navbar(self, title=None, icon=None, favicon=None):
        cache.set('title', title)
        cache.set('icon', icon)
        cache.set('favicon', favicon)
        self.data['navbar'].update(title=title, icon=icon, favicon=favicon)

    def login(self, logo=None, title=None, mask=None, two_factor=False, actions=()):
        cache.set('login', dict(logo=logo, title=title, mask=mask, actions=actions))
        if two_factor:
            self.settings_menu('activate_2f_authentication', 'deactivate_2f_authentication')

    def styles(self, *urls):
        self.data['styles'].extend(urls)

    def scripts(self, *urls):
        self.data['scripts'].extend(urls)

    def libraries(self, fontawesome=False, materialicons=False):
        if fontawesome:
            cache.set('fontawesome', True)
            self.scripts('/static/icons/fontawesome/fontawesome.min.js')
            self.styles('/static/icons/fontawesome/fontawesome.min.css')
        if materialicons:
            cache.set('materialicons', True)
            self.styles('/static/icons/materialicons/materialicons.css')

    def web_push_notification(self, activate=False):
        if activate:
            self.scripts('/static/js/wpn.min.js')

    def header(self, logo=None, title=None, text=None, shadow=True):
        self.data['header'].update(logo=logo, title=title, text=text, shadow=shadow)

    def footer(self, title=None, text=None, version=None):
        self.data['footer'].update(title=title, text=text, version=version)

    def to_item(self, model, count=True):
        return

    def _load(self, key, items, modal=False, count=False, app=None):
        new_item = None
        allways = 'floating', 'navigation', 'settings', 'actions', 'menu', 'links', 'tools', 'search', 'plus'
        for cls in items:
            if '.' in cls:
                modal = False if key in ('tools', 'settings') else modal
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
                        url = '/app/dashboard/{}/'.format(metadata['key'])
                        self.data[key].append(dict(
                            url=url, modal=metadata['modal'] and modal,
                            label=metadata['name'], icon=metadata['icon'], app=app
                        ))
                else:
                    qs = getattr(cls.objects, subset)()
                    if key == 'plus':
                        has_perm = self.request.user.is_superuser or qs.model().has_add_permission(self.request.user)
                    else:
                        has_perm = self.request.user.is_superuser or qs.has_permission(self.request.user)
                    if has_perm:
                        if key in allways or self.request.path == '/app/dashboard/':
                            label = cls.metaclass().verbose_name if key == 'plus' else cls.metaclass().verbose_name_plural
                            if subset and subset != 'all':
                                label = '{} {}'.format(label, qs.get_attr_metadata(subset)[0])
                            url = cls.get_list_url('/app', subset)
                            if key == 'plus':
                                url = '{}{}/'.format(url, 'add')
                            for item in self.data[key]:
                                add_item = add_item and not item['url'] == url
                            if add_item:
                                new_item = dict(
                                    url=url, label=label, modal=modal or key == 'plus',
                                    count=cls.objects.all().apply_role_lookups(self.request.user).count() if count else None,
                                    icon=getattr(cls.metaclass(), 'icon', None),
                                    app=app
                                )
                                self.data[key].append(new_item)
        return new_item

    def _item(self, key, url, label, icon, count=None, app=None):
        self.data[key].append(
            dict(url=url, label=label, count=count, icon=icon, app=app)
        )

    def info(self, *items, app=None):
        self._load('info', items, app=app)

    def warning(self, *items, app=None):
        self._load('warning', items, app=app)

    def search_menu(self, *items, app=None):
        self._load('search', items, app=app)

    def menu(self, *items, app=None, hierarchy=None, icon=None):
        item = self._load('menu', items, app=app)
        if item:
            item.update(hierarchy=hierarchy, menu_icon=icon)

    def session_lookup(self, **kwargs):
        # del self.request.session['session_lookups']
        for key, qs in kwargs.items():
            if 'session_lookups' not in self.request.session:
                self.request.session['session_lookups'] = {}
                self.request.session.save()
            if key not in self.request.session['session_lookups'] :
                self.request.session['session_lookups'][key] = dict(
                    choices=[[obj.pk, str(obj)] for obj in qs],
                    value=None,
                    label=qs.model.metaclass().verbose_name
                )
                self.request.session.save()

    def top_menu(self, *items, modal=False, app=None):
        self._load('links', items, modal=modal, app=app)

    def add_link(self, url, label, app=None):
        self._item('links', url, label, app=app)

    def shortcuts(self, *items, app=None):
        self._load('shortcuts', items, app=app)

    def add_shortcut(self, url, label, icon, app=None):
        self._item('shortcut', url, label, icon, app=app)

    def action_bar(self, *items, app=None):
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

    def tools_menu(self, *items, modal=True, app=None):
        self._load('tools', items, modal=modal, app=app)

    def plus_menu(self, *items, modal=True, app=None):
        self._load('plus', items, modal=modal, app=app)

    def navigation(self, *items, app=None):
        if mobile(self.request):
            self._load('navigation', items, app=app)
        else:
            self._load('floating', items, app=app)

    def add_navigation(self, url, label, icon, app=None):
        if mobile(self.request):
            self._item('navigation', url, label, icon, app=app)
        else:
            self._item('floating', url, label, icon, app=app)

    def settings_menu(self, *items, modal=True, app=None):
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

    def objects(self, model_name):
        qs = apps.get_model(model_name).objects
        qs.request = self.request
        return qs.apply_role_lookups(self.request.user, self.request.session)

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
            info=[], warning=[], search=[], menu=[], links=[], shortcuts=[], cards=[], tasks=[], plus=[], navbar={},
            floating=[], navigation=[], settings=[], top=[], center=[], right=[], bottom=[], actions=[], tools=[], header={}, footer={},
            styles=[], scripts=[]
        )
        self.data['navigation'].append(
            dict(url='/app/dashboard/', label='Principal', icon='house', app=None)
        )
        for cls in DASHBOARDS:
            dashboard = cls(request)
            if dashboard.redirect_url:
                raise ReadyResponseException(HttpResponseRedirect(dashboard.redirect_url))
            for k, v in dashboard.data.items():
                self.data[k].update(v) if isinstance(v, dict) else self.data[k].extend(v)
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

        if self.request.path.startswith('/app/'):
            self.data['menu'] = self.create_menu(render=True)
        else:
            self.data['menu'] = self.create_menu(render=False)

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

    def create_menu(self, render=True):
        icons = {}
        default_icon = 'record2'
        def create_submenu(hierarchy, item, level=0):
            tokens = item['hierarchy'].split('::')
            if len(tokens) == 1:
                if level == 0:
                    icons[tokens[0]] = item['menu_icon'] or item['icon'] or default_icon
                if tokens[0] not in hierarchy:
                    hierarchy[tokens[0]] = {}
                hierarchy[tokens[0]][item['label']] = item
            else:
                if level == 0:
                    icons[tokens[0]] = item['menu_icon'] or default_icon
                if tokens[0] in hierarchy:
                    submenu = hierarchy[tokens[0]]
                else:
                    submenu = {}
                    hierarchy[tokens[0]] = submenu
                item['hierarchy'] = '::'.join(tokens[1:])
                create_submenu(submenu, item, level+1)

        menu = {}
        for item in self.data['menu']:
            if item['hierarchy']:
                create_submenu(menu, item)
            else:
                menu[item['label']] = item
                icons[item['label']] = item['icon'] or 'record-circle'

        if not render:
            return dict(icons=icons, items=menu)

        html = []
        def append_html(label, item, level=0, hierarchy=None):
            ident = '\t' * level
            nbsp = '&nbsp;' * level * 3
            html.append('{}<li>'.format(ident))
            icon = '<i class="bi bi-{} menu-item-icon"></i> '.format(icons[label]) if level == 0 else ''
            if 'url' in item:
                html.append('{}\t<a class="menu-subitem" data-hierarchy="({})" href="{}">{}{}{}</a>'.format(ident, ', '.join([f"'{text}'" for text in hierarchy]), item['url'], icon, nbsp, item['label']))
            else:
                html.append('{}\t<a class="menu-item" href="javascript:">{}{}{}<i class="bi bi-chevron-down chevron"></i></a>'.format(ident, icon, nbsp, label))
                html.append('{}<ul>'.format(ident))
                for sublabel, subitem in item.items():
                    hierarchy.insert(0, sublabel)
                    append_html(sublabel, subitem, level+1, hierarchy)
                html.append('{}</ul>'.format(ident))
            html.append('{}</li>'.format(ident))
        for label, item in menu.items():
            append_html(label, item, 0, [label])
        return mark_safe('\n'.join(html))

    def serialize(self, data):
        for k, v in data.items():
            pass # print(k, v)
        for k, v in data.get('append', {}).items():
            self.data[k].append(v)
        return self.data