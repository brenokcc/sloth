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


def obj_view(request, app_label, model_name, x=None, y=None, z=None, w=None):
    model = apps.get_model(app_label, model_name)
    # print(dict(x=x, y=y, z=z, w=w))
    if x:
        x = str(x)
        if x.isdigit():
            obj = model.objects.get(pk=x)
            if y:
                if z:
                    if z.split('-')[0].isdigit():  # queryset action
                        attr = getattr(obj, y)
                        form_cls = model.action_form_cls(w)
                        instances = attr().filter(pk__in=z.split('-'))
                        form = form_cls(request=request, instantiator=obj, instances=instances)
                        if form.has_permission():
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    else:  # pks is instance action
                        form_cls = model.action_form_cls(z)
                        form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.has_permission():
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                else:
                    if y.lower() == 'edit':  # /base/estado/1/edit/
                        form_cls = model.edit_form_cls()
                        form = form_cls(request=request, instance=obj)
                        if form.has_permission():
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    if y.lower() == 'delete':  # /base/estado/1/delete/
                        form_cls = model.delete_form_cls()
                        form = form_cls(request=request, instance=obj)
                        if form.has_permission():
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    else:  # /base/estado/1/editar_sigla/
                        form_cls = model.action_form_cls(y)
                        if form_cls:  # instance action
                            form = form_cls(request=request, instance=obj)
                            if form.has_permission():
                                if form.is_valid():
                                    form.process()
                                return form
                            raise PermissionDenied()
                        else:
                            # subset
                            if obj.has_attr_view_permission(request.user, y):
                                output = obj.values(y).contextualize(request)
                                return output
                        raise PermissionDenied()
            else:
                if obj.has_view_permission(request.user):
                    return obj.view().contextualize(request)
                raise PermissionDenied()
        elif x.lower() == 'add':
            form_cls = model.add_form_cls()
            form = form_cls(request=request)
            if form.has_permission():
                if form.is_valid():
                    form.process()
                return form
            raise PermissionDenied()
        else:
            attr = getattr(model.objects, x, None)
            if attr:
                if y:
                    form_cls = model.action_form_cls(z)
                    instances = attr().filter(pk__in=y.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.has_permission():
                        if form.is_valid():
                            result = form.process()
                            if result is not None:
                                return result
                        return form
                    raise PermissionDenied()
                else:
                    return attr().contextualize(request)
            else:
                if y:
                    form_cls = model.action_form_cls(y)
                    instances = model.objects.all().filter(pk__in=x.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.has_permission():
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
                else:
                    form_cls = model.action_form_cls(x)
                    form = form_cls(request=request)
                    if form.has_permission():
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
    else:  # /base/estado/
        return model.objects.all().contextualize(request).add_default_actions()
