# -*- coding: utf-8 -*-

import base64

from django.apps import apps
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
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


def add_view(request, app_label, model_name):
    model = apps.get_model(app_label, model_name)
    form_cls = model.add_form_cls()
    form = form_cls(request=request)
    if form.has_add_permission(request.user):
        if form.is_valid():
            form.process()
        return form
    raise PermissionDenied()


def edit_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = model.edit_form_cls()
    form = form_cls(request=request, instance=model.objects.get(pk=pk))
    if form.has_edit_permission(request.user):
        if form.is_valid():
            form.process()
        return form
    raise PermissionDenied()


def delete_view(request, app_label, model_name, pk):
    model = apps.get_model(app_label, model_name)
    form_cls = model.delete_form_cls()
    form = form_cls(request=request, instance=model.objects.get(pk=pk))
    if form.has_delete_permission(request.user):
        if form.is_valid():
            form.process()
        return form
    raise PermissionDenied()


def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    model = apps.get_model(app_label, model_name)
    qs = model.objects.contextualize(request)
    if method:
        attr = getattr(qs, method, None)
        if attr:
            if pks:
                form_cls = model.action_form_cls(action)
                instances = attr().filter(pk__in=pks.split('-'))
                form = form_cls(request=request, instances=instances)
                if form.has_permission(request.user):
                    if form.is_valid():
                        result = form.process()
                        if result is not None:
                            return result
                    return form
                raise PermissionDenied()
            else:
                return attr()
        else:
            form_cls = model.action_form_cls(method)
            form = form_cls(request=request)
            if form.is_valid():
                result = form.process()
                if result is not None:
                    return result
            return form
    else:
        return qs.add_default_actions()


def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    pk = str(pk)
    model = apps.get_model(app_label, model_name)
    if pk.isdigit():
        obj = model.objects.get(pk=pk)
        if method:
            if pks:
                if pks.split('-')[0].isdigit():  # queryset action
                    attr = getattr(obj, method)
                    form_cls = model.action_form_cls(action)
                    instances = attr().filter(pk__in=pks.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.has_permission(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
                else:  # pks is instance action
                    form_cls = model.action_form_cls(pks)
                    form = form_cls(request=request, instance=obj)
                    if form.has_permission(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
            else:
                form_cls = model.action_form_cls(method)
                if form_cls:  # instance action
                    form = form_cls(request=request, instance=obj)
                    if form.has_permission(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
                else:
                    # subset
                    if obj.has_attr_view_permission(request.user, method):
                        output = obj.values(method).contextualize(request)
                        return output
                raise PermissionDenied()
        else:
            if obj.has_view_permission(request.user):
                return obj.view()
            raise PermissionDenied()
    else:
        if method:
            form_cls = model.action_form_cls(method)
            instances = model.objects.all().filter(pk__in=pk.split('-'))
            form = form_cls(request=request, instances=instances)
        else:
            form_cls = model.action_form_cls(pk)
            form = form_cls(request=request)

        if form.has_permission(request.user):
            if form.is_valid():
                form.process()
            return form
        raise PermissionDenied()
