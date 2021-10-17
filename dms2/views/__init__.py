# -*- coding: utf-8 -*-

import base64
import traceback

from django.apps import apps
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.oauth2_backends import get_oauthlib_core

from dms2.threading import tls


def is_authenticated(request):
    tls.wrap = False
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
                return JsonResponse(
                    dict(type='message', text='Usuário não autenticado', style='warning'), status=403
                )
        except PermissionDenied:
            return JsonResponse(
                dict(type='message', text='Usuário não autorizado', style='warning'), status=401
            )
        except BaseException as e:
            traceback.print_exc()
            return JsonResponse(
                dict(type='message', text=str(e), style='error'), status=500
            )

    return decorate


@csrf_exempt
@try_except
def add_view(request, app_label, model_name):
    model = apps.get_model(app_label, model_name)
    form_cls = model.add_form_cls()
    form = form_cls(request=request, data=request.POST or None)
    if form.has_add_permission(request.user):
        if form.is_valid():
            obj = form.save()
            return form.get_message(next=obj.get_absolute_url())
        return form.serialize()
    raise PermissionDenied()


@csrf_exempt
@try_except
def edit_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = model.edit_form_cls()
    form = form_cls(request=request, data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.has_edit_permission(request.user):
        if form.is_valid():
            obj = form.process()
            return form.get_message(next=obj.get_absolute_url())
        return form.serialize()
    raise PermissionDenied()


@csrf_exempt
@try_except
def delete_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = model.delete_form_cls()
    form = form_cls(request=request, data=request.POST or None, instance=model.objects.get(pk=pk))
    if form.has_delete_permission(request.user):
        if form.is_valid():
            form.instance.delete()
            return form.get_message()
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
            form_cls = model.action_form_cls(action)
            instances = attr().filter(pk__in=pks.split('-'))
            data = request.POST if not form_cls.base_fields else request.POST or None
            form = form_cls(request=request, data=data, instances=instances)
            if form.has_permission(request.user):
                if form.is_valid():
                    result = form.process()
                    if result is None:
                        return form.get_message()
                    return result.serialize()
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
                form_cls = model.action_form_cls(action)
                instances = attr().filter(pk__in=pks.split('-'))
                data = request.POST if not form_cls.base_fields else request.POST or None
                form = form_cls(request=request, data=data, instances=instances)
                if form.has_permission(request.user):
                    if form.is_valid():
                        result = form.process()
                        if result is None:
                            return form.get_message()
                        return result.serialize()
                    form.serialize()
                raise PermissionDenied()
            else:  # pks is obj action
                form_cls = model.action_form_cls(pks)
                data = request.POST if not form_cls.base_fields else request.POST or None
                form = form_cls(request=request, data=data, instance=obj)
                if form.has_permission(request.user):
                    if form.is_valid():
                        result = form.process()
                        if result is None:
                            return dict(message='Ação realizada com sucesso')
                        return result.serialize()
                    return form.serialize()
                raise PermissionDenied()
        else:
            if obj.has_attr_view_permission(request.user, method):
                return obj.serialize(method)
            raise PermissionDenied()
    else:
        if obj.has_view_permission(request.user):
            return obj.serialize()
        raise PermissionDenied()
