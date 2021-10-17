from django.apps import apps
import traceback

from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import modelform_factory
from django.http import JsonResponse
from ..forms import ModelForm
import base64
from django.contrib.auth import authenticate
from oauth2_provider.oauth2_backends import get_oauthlib_core


def is_authenticated(request):
    request.access_token = None
    if request.method != 'OPTIONS' and not request.user.is_authenticated:
        if 'Authorization' in request.headers:
            authorization = request.headers['Authorization']
            token = authorization.split(' ')[-1]
            if authorization.startswith('Basic '):
                username, password = base64.b64decode(token).decode().split(':')
                user = authenticate(request, username=username, password=password)
                if user:
                    request.user = user
                    return True
            elif authorization.startswith('Bearer '):
                valid, req = get_oauthlib_core().verify_request(request, scopes=[])
                if valid:
                    request.user = req.user
                    request.access_token = req.access_token
                    return True
            return False
        else:
            return False
    return True


def try_except(func):
    def decorate(request, *args, **kwargs):
        try:
            if is_authenticated(request):
                return JsonResponse(func(request, *args, **kwargs))
            else:
                return JsonResponse(dict(error='Usuário não autenticado'))
        except PermissionDenied:
            return JsonResponse(dict(error='Usuário não autorizado'))
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
    form = form_cls(request=request, data=request.POST or None)
    if form.has_add_permission(request.user):
        if form.is_valid():
            obj = form.save()
            return obj.serialize()
        return form.serialize()
    raise PermissionDenied()


@csrf_exempt
@try_except
def edit_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = modelform_factory(model, form=ModelForm, exclude=())
    form = form_cls(request=request, data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.has_edit_permission(request.user):
        if form.is_valid():
            obj = form.process()
            return obj.serialize()
        return form.serialize()
    raise PermissionDenied()


@csrf_exempt
@try_except
def delete_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = modelform_factory(model, form=ModelForm, fields=())
    form = form_cls(request=request, data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.has_delete_permission(request.user):
        if form.is_valid():
            form.instance.delete()
            return {}
        return form.serialize()
    raise PermissionDenied()


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
            form = form_cls(request=request, data=data, instances=instances)
            if form.has_permission(request.user):
                if form.is_valid():
                    form.process()
                return {}
            raise PermissionDenied()
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
                form = form_cls(request=request, data=data, instances=instances)
                if form.has_permission(request.user):
                    if form.is_valid():
                        form.process()
                    return {}
                raise PermissionDenied()
            else:  # pks is obj action
                form_cls = actionform_factory(app_label, pks)
                data = request.POST if not form_cls.base_fields else request.POST or None
                form = form_cls(request=request, data=data, instance=obj)
                if form.has_permission(request.user):
                    if form.is_valid():
                        form.process()
                    return {}
                raise PermissionDenied()
        else:
            if obj.has_attr_view_permission(request.user, method):
                return obj.serialize(method)
            raise PermissionDenied()
    else:
        if obj.has_view_permission(request.user):
            return obj.serialize()
        raise PermissionDenied()
