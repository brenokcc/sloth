from django.apps import apps
import traceback
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import modelform_factory
from django.http import JsonResponse
from ..forms import ModelForm


def try_except(func):
    def decorate(*args, **kwargs):
        try:
            return JsonResponse(func(*args, **kwargs))
        except BaseException as e:
            traceback.print_exc()
            return JsonResponse(dict(error=str(e)))
    return decorate


def actionform_factory(app_label, action):
    config = apps.get_app_config(app_label)
    forms = __import__(
        '{}.forms'.format(config.module.__package__),
        fromlist=config.module.__package__.split()
    )
    for name in dir(forms):
        if name.lower() == action:
            return getattr(forms, name)
    return None


@csrf_exempt
@try_except
def add_view(request, app_label, model_name):
    model = apps.get_model(app_label, model_name)
    form_cls = modelform_factory(model, form=ModelForm, exclude=())
    form = form_cls(data=request.POST or None, request=request)
    if form.is_valid():
        obj = form.save()
        return obj.serialize()
    return form.serialize()


@csrf_exempt
@try_except
def edit_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = modelform_factory(model, form=ModelForm, exclude=())
    form = form_cls(data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.is_valid():
        obj = form.process()
        return obj.serialize()
    return form.serialize()


@csrf_exempt
@try_except
def delete_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = modelform_factory(model, form=ModelForm, fields=())
    form = form_cls(data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.is_valid():
        form.instance.delete()
        return {}
    return form.serialize()


@csrf_exempt
@try_except
def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    qs = model.objects.all()
    if method:
        attr = getattr(qs, method)
        if pks:
            form_cls = actionform_factory(app_label, action)
            instances = attr().filter(pk__in=pks.split('-'))
            data = request.POST if not form_cls.base_fields else request.POST or None
            form = form_cls(data=data, instances=instances)
            if form.is_valid():
                form.process()
            return {}
        else:
            return attr().serialize()
    else:
        return qs.serialize()


@csrf_exempt
@try_except
def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    obj = model.objects.get(pk=pk)
    if method:
        if pks:
            if pks.split('-')[0].isdigit():  # queryset action
                attr = getattr(obj, method)
                form_cls = actionform_factory(app_label, action)
                instances = attr().filter(pk__in=pks.split('-'))
                data = request.POST if not form_cls.base_fields else request.POST or None
                form = form_cls(data=data, instances=instances)
                if form.is_valid():
                    form.process()
                return {}
            else:  # pks is obj action
                form_cls = actionform_factory(app_label, pks)
                data = request.POST if not form_cls.base_fields else request.POST or None
                form = form_cls(data=data, instance=obj)
                if form.is_valid():
                    form.process()
                return {}
        else:
            return obj.serialize(method)
    else:
        return obj.serialize()
