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
        self.data = dict(cards=[], append=[])
        self.load(request)

    def cards(self, *models):
        for model in models:
            if model().has_list_permission(self.request.user) or model().has_permission(self.request.user):
                self.data['cards'].append(dict(
                    url=model.get_list_url('/adm'),
                    label=model.metaclass().verbose_name_plural,
                    count=model.objects.all().apply_role_lookups(self.request.user).count(),
                    icon=getattr(model.metaclass(), 'icon', 'app')
                ))

    def append(self, data):
        self.data['append'].append(str(data.contextualize(self.request)))

    def load(self, request):
        pass


class Dashboards:

    def __init__(self, request):
        self.request = request
        self.data = dict(cards=[], append=[])
        initilize()
        for cls in DASHBOARDS:
            dashboard = cls(request)
            self.data['cards'].extend(dashboard.data['cards'])
            self.data['append'].extend(dashboard.data['append'])


    def __str__(self):
        return mark_safe(render_to_string('adm/dashboard/dashboards.html', dict(data=self.data), request=self.request))



