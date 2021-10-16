from django.apps import apps
from django.http import JsonResponse


def load_form(app_label, action):
    config = apps.get_app_config(app_label)
    forms = __import__(
        '{}.forms'.format(config.module.__package__),
        fromlist=config.module.__package__.split()
    )
    for name in dir(forms):
        if name.lower() == action:
            return getattr(forms, name)
    return None


def api_list(request, app_label, model_name, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    qs = model.objects.all()
    if method:
        attr = getattr(qs, method)
        if pks:
            print(attr().filter(pk__in=pks.split('-')), load_form(app_label, action))
            response = {}
        else:
            response = attr().serialize()
    else:
        response = qs.serialize()
    return JsonResponse(response)


def api_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    obj = model.objects.get(pk=pk)
    if method:
        if pks:
            if pks.split('-')[0].isdigit():  # queryset action
                attr = getattr(obj, method)
                print(attr().filter(pk__in=pks.split('-')), load_form(app_label, action))
            else:  # pks is obj action
                print(obj, load_form(app_label, pks))
            response = {}
        else:
            response = obj.serialize(method)
    else:
        response = obj.serialize()
    return JsonResponse(response)
