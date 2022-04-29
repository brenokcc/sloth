from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

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
                print('{} dashboard initilized!'.format(module))
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
            info=[], warning=[], menu=[], shortcuts=[], cards=[],
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
                        url=model.get_list_url('/adm'),
                        label=model.metaclass().verbose_name_plural,
                        count=model.objects.all().apply_role_lookups(self.request.user).count(),
                        icon=getattr(model.metaclass(), 'icon', 'app')
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
        if self.request.path == '/adm/':
            self.data['right' if aside else 'center'].append(
                str(data.contextualize(self.request))
            )

    def extend(self, data, template, aside=False):
        html = mark_safe(render_to_string(template, data, request=self.request))
        self.data['right' if aside else 'center'].append(html)

    def load(self, request):
        pass


class Dashboards:

    def __init__(self, request):
        self.request = request
        self.data = dict(
            info=[], warning=[], menu=[], shortcuts=[], cards=[],
            floating=[], navigation=[], settings=[], center=[], right=[]
        )
        self.data['navigation'].append(
            dict(url='/adm/', label='Principal', icon='house')
        )
        initilize()
        for cls in DASHBOARDS:
            dashboard = cls(request)
            for key in dashboard.data:
                self.data[key].extend(dashboard.data[key])

    def __str__(self):
        return mark_safe(render_to_string('adm/dashboard/dashboards.html', dict(data=self.data), request=self.request))



