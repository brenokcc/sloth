# -*- coding: utf-8 -*-

import base64
from django.conf import settings
from django.apps import apps
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from oauth2_provider.oauth2_backends import get_oauthlib_core

from ..app.templatetags.tags import is_ajax


def context_processor(request):
    if request.user.is_authenticated and ('menu' not in request.session or settings.DEBUG):
        if request.path.startswith('/app/') and not is_ajax(request):
            if 'stack' not in request.session:
                request.session['stack'] = []
            if request.path == '/app/':
                request.session['stack'].clear()
                request.session['stack'].append(request.path)
            elif request.path in request.session['stack']:
                index = request.session['stack'].index(request.path)
                request.session['stack'] = request.session['stack'][0:index+1]
            else:
                request.session['stack'].append(request.path)
            referrer =  request.session['stack'][-2] if len(request.session['stack']) > 1 else None
            return dict(referrer=referrer)
    return {}


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


def dispatcher(request, app_label, model_name, x=None, y=None, z=None, w=None):
    model = apps.get_model(app_label, model_name)
    if x:
        x = str(x)
        if x.isdigit():
            obj = model.objects.get(pk=x)
            if y:
                if z:
                    attr = getattr(obj, y)
                    if z.split('-')[0].isdigit():  # queryset action
                        if w:
                            qs = attr().filter(pk__in=z.split('-'))
                            model = qs.model
                            if w.lower() == 'edit':  # /base/estado/1/get_cidades/1/edit/
                                form_cls = model.edit_form_cls()
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    for ignore in qs.metadata['ignore']:
                                        if ignore in form.fields:
                                            del form.fields[ignore]
                                    if form.is_valid():
                                        form.submit()
                                    return form
                                raise PermissionDenied()
                            elif w.lower() == 'delete':  # /base/estado/1/get_cidades/1/delete/
                                form_cls = model.delete_form_cls()
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        form.submit()
                                    return form
                                raise PermissionDenied()
                            else:  # /base/estado/1/get_cidades/1/alterar_nome/
                                form_cls = model.action_form_cls(w)
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        form.submit()
                                    return form
                                raise PermissionDenied()
                        else:  # /base/estado/1/get_cidades/1/
                            qs = attr()
                            instance = qs.contextualize(request).get(pk=z)
                            if instance.has_view_permission(request.user) or instance.has_permission(request.user):
                                return instance.show(qs.metadata['view']).contextualize(request)
                            raise PermissionDenied()
                            # form_cls = model.action_form_cls(z)
                            # instances = attr().filter(pk__in=z.split('-'))
                            # form = form_cls(request=request, instantiator=obj, instances=instances)
                            # if form.check_permission(request.user):
                            #     if form.is_valid():
                            #         form.submit()
                            #     return form
                            # raise PermissionDenied()
                    else:
                        if w:  # /base/estado/1/get_cidades/sem_prefeito/1/
                            qs = getattr(attr(), z)()
                            instance = qs.contextualize(request).get(pk=w)
                            if instance.has_view_permission(request.user) or instance.has_permission(request.user):
                                return instance.show(*qs.metadata['view']).contextualize(request)
                            raise PermissionDenied()
                        else:  # base/servidor/3/get_ferias/CadastrarFerias/ or base/servidor/3/InformarEndereco/
                            relation = attr()
                            form_cls = model.action_form_cls(z)
                            if hasattr(relation, 'all'):  # if it is a queryset
                                form = form_cls(request=request, instantiator=obj)
                            else:  # it is a valueset
                                form = form_cls(request=request, instance=obj, instantiator=obj)
                            related_field_name = getattr(form_cls.Meta, 'related_field', None)
                            if related_field_name:
                                setattr(form.instance, related_field_name, obj)
                                if related_field_name in form.fields:
                                    del form.fields[related_field_name]
                            if form.check_permission(request.user):
                                if form.is_valid():
                                    form.submit()
                                return form
                            raise PermissionDenied()
                else:
                    if y.lower() == 'edit':  # /base/estado/1/edit/
                        form_cls = model.edit_form_cls()
                        form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.check_permission(request.user):
                            if form.is_valid():
                                form.submit()
                            return form
                        raise PermissionDenied()
                    if y.lower() == 'delete':  # /base/estado/1/delete/
                        form_cls = model.delete_form_cls()
                        form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.check_permission(request.user):
                            if form.is_valid():
                                form.submit()
                            return form
                        raise PermissionDenied()
                    else:  # /base/estado/1/editar_sigla/
                        form_cls = model.action_form_cls(y)
                        if form_cls:  # instance action
                            form = form_cls(request=request, instance=obj, instantiator=obj)
                            if form.check_permission(request.user):
                                if form.is_valid():
                                    form.submit()
                                return form
                            raise PermissionDenied()
                        else:
                            # object subset or attr
                            if obj.has_fieldset_permission(request.user, y):
                                attr = getattr(obj, y)
                                output = attr().attr(y).contextualize(request)
                                if not is_ajax(request):
                                    output = output.source(obj)
                                return output
                        raise PermissionDenied()
            else:
                if obj.has_view_permission(request.user) or obj.has_permission(request.user):
                    return obj.view().contextualize(request)
                raise PermissionDenied()
        elif x.lower() == 'add':
            form_cls = model.add_form_cls()
            form = form_cls(request=request)
            if form.check_permission(request.user):
                if form.is_valid():
                    form.submit()
                return form
            raise PermissionDenied()
        else:
            attr = getattr(model.objects, x, None)
            if attr:
                if model.objects.has_attr_permission(request.user, x):
                    if y:
                        if y.isdigit():  # view object in a subset
                            if z:
                                form_cls = model.action_form_cls(z)
                                instances = attr().filter(pk__in=y.split('-'))
                                form = form_cls(request=request, instances=instances)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        result = form.submit()
                                        if result is not None:
                                            return result
                                    return form
                                raise PermissionDenied()
                            else:
                                obj = model.objects.get(pk=y)
                                if obj.has_view_permission(request.user) or obj.has_permission(request.user):
                                    return obj.view().contextualize(request)
                                raise PermissionDenied()
                        else:  # execute action in a subset
                            form_cls = model.action_form_cls(z)
                            instances = attr().filter(pk__in=y.split('-'))
                            form = form_cls(request=request, instances=instances)
                            if form.check_permission(request.user):
                                if form.is_valid():
                                    result = form.submit()
                                    if result is not None:
                                        return result
                                return form
                            raise PermissionDenied()
                    else:
                        output = attr().attr(x).contextualize(request)
                        if not is_ajax(request):
                            output = output.source(model.objects)
                        return output
                raise PermissionDenied()
            else:
                if y:
                    form_cls = model.action_form_cls(y)
                    instances = model.objects.all().filter(pk__in=x.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.check_permission(request.user):
                        if form.is_valid():
                            form.submit()
                        return form
                    raise PermissionDenied()
                else:
                    form_cls = model.action_form_cls(x)
                    form = form_cls(request=request)
                    if form.check_permission(request.user):
                        if form.is_valid():
                            form.submit()
                        return form
                    raise PermissionDenied()
    else:  # /base/estado/
        if model().has_list_permission(request.user) or model().has_permission(request.user):
            qs = model.objects.all() if request.GET.get('subset', 'all') == 'all' else model.objects
            return qs.contextualize(request).default_actions().collapsed(False).is_admin()
        raise PermissionDenied()