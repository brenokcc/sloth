from django.apps import apps
from django.http import JsonResponse


def api_list(request, app_label, model_name, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    qs = model.objects.all()
    if method:
        attr = getattr(qs, method)
        if pks:
            pks = pks.split('-')
            print(attr().filter(pk__in=pks), attr.allow, action)
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
            pks = pks.split('-')
            if pks[0].isdigit():  # queryset action
                attr = getattr(obj, method)
                print(attr().filter(pk__in=pks), attr.allow, action)
            else:  # obj action
                attr = getattr(obj, method)
                print(obj)
            response = {}
        else:
            response = obj.serialize(method)
    else:
        response = obj.serialize()
    return JsonResponse(response)
