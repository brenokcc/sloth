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
                    attr = getattr(obj, y)
                    if z.split('-')[0].isdigit():  # queryset action
                        form_cls = model.action_form_cls(w)
                        instances = attr().filter(pk__in=z.split('-'))
                        form = form_cls(request=request, instantiator=obj, instances=instances)
                        if form.can_view(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    else:  # pks is instance action
                        form_cls = model.action_form_cls(z)
                        # if it is a relation action, do not set the instance attribute
                        if getattr(form_cls.Meta, 'relation', None):
                            form = form_cls(request=request, instantiator=obj)
                        else:
                            form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.can_view(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                else:
                    if y.lower() == 'edit':  # /base/estado/1/edit/
                        form_cls = model.edit_form_cls()
                        form = form_cls(request=request, instance=obj)
                        if form.can_view(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    if y.lower() == 'delete':  # /base/estado/1/delete/
                        form_cls = model.delete_form_cls()
                        form = form_cls(request=request, instance=obj)
                        if form.can_view(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    else:  # /base/estado/1/editar_sigla/
                        form_cls = model.action_form_cls(y)
                        if form_cls:  # instance action
                            form = form_cls(request=request, instance=obj)
                            if form.can_view(request.user):
                                if form.is_valid():
                                    form.process()
                                return form
                            raise PermissionDenied()
                        else:
                            # object subset
                            if obj.can_view_attr(request.user, y):
                                attr = getattr(obj, y)
                                output = attr().attr(x).contextualize(request)
                                return output
                        raise PermissionDenied()
            else:
                if obj.can_view(request.user):
                    return obj.view().contextualize(request)
                raise PermissionDenied()
        elif x.lower() == 'add':
            form_cls = model.add_form_cls()
            form = form_cls(request=request)
            if form.can_view(request.user):
                if form.is_valid():
                    form.process()
                return form
            raise PermissionDenied()
        else:
            attr = getattr(model.objects, x, None)
            if attr:
                if y:
                    if y.isdigit():  # view object in a subset
                        if z:
                            form_cls = model.action_form_cls(z)
                            instances = attr().filter(pk__in=y.split('-'))
                            form = form_cls(request=request, instances=instances)
                            if form.can_view(request.user):
                                if form.is_valid():
                                    result = form.process()
                                    if result is not None:
                                        return result
                                return form
                            raise PermissionDenied()
                        else:
                            obj = model.objects.get(pk=y)
                            if obj.can_view(request.user):
                                return obj.view().contextualize(request)
                            raise PermissionDenied()
                    else:  # execute action in a subset
                        form_cls = model.action_form_cls(z)
                        instances = attr().filter(pk__in=y.split('-'))
                        form = form_cls(request=request, instances=instances)
                        if form.can_view(request.user):
                            if form.is_valid():
                                result = form.process()
                                if result is not None:
                                    return result
                            return form
                        raise PermissionDenied()
                else:
                    return attr().attr(x).contextualize(request)
            else:
                if y:
                    form_cls = model.action_form_cls(y)
                    instances = model.objects.all().filter(pk__in=x.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.can_view(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
                else:
                    form_cls = model.action_form_cls(x)
                    form = form_cls(request=request)
                    if form.can_view(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
    else:  # /base/estado/
        return model.objects.all().contextualize(request).default_actions()
