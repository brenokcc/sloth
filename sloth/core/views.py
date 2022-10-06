# -*- coding: utf-8 -*-

import base64
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from oauth2_provider.oauth2_backends import get_oauthlib_core

from ..actions import ACTIONS
from ..app.templatetags.tags import is_ajax
from .. import initilize


initilize()


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


def action(request, name):
    form_cls = ACTIONS[name]
    form = form_cls(request=request, instances=(), instantiator=None)
    if form.check_permission(request.user):
        if form.is_valid():
            form.process()
        return form
    raise PermissionDenied()


def dispatcher(request, app_label, model_name, x=None, y=None, z=None, w=None, k=None):
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        raise PermissionDenied()
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
                                        form.process()
                                    return form
                                raise PermissionDenied()
                            elif w.lower() == 'delete':  # /base/estado/1/get_cidades/1/delete/
                                form_cls = model.delete_form_cls()
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        form.process()
                                    return form
                                raise PermissionDenied()
                            elif hasattr(obj, w):  # /base/estado/1/get_cidades/1/get_dados_gerais/
                                instance = qs.contextualize(request).first()
                                if request.user.is_superuser or instance.has_view_attr_permission(request.user, w) or instance.has_permission(request.user):
                                    return instance.display(w).contextualize(request)
                                raise PermissionDenied()
                            else:  # /base/estado/1/get_cidades/1/alterar_nome/
                                form_cls = model.action_form_cls(w)
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        form.process()
                                    return form
                                raise PermissionDenied()
                        else:  # /base/estado/1/get_cidades/1/
                            qs = attr()
                            instance = qs.contextualize(request).get(pk=z)
                            if request.user.is_superuser or instance.has_view_permission(request.user) or instance.has_permission(request.user):
                                return instance.view().contextualize(request)
                            raise PermissionDenied()
                            # form_cls = model.action_form_cls(z)
                            # instances = attr().filter(pk__in=z.split('-'))
                            # form = form_cls(request=request, instantiator=obj, instances=instances)
                            # if form.check_permission(request.user):
                            #     if form.is_valid():
                            #         form.process()
                            #     return form
                            # raise PermissionDenied()
                    else:
                        if w:  # /base/estado/1/get_cidades/sem_prefeito/1/
                            qs = getattr(attr(), z)()
                            instance = qs.contextualize(request).get(pk=w)
                            if k:  # /base/estado/1/get_cidades/sem_prefeito/1/DefinirPrefeito/
                                form_cls = model.action_form_cls(k)
                                form = form_cls(request=request, instances=qs, instantiator=obj)
                                if form.check_permission(request.user):
                                    if form.is_valid():
                                        form.process()
                                    return form
                                raise PermissionDenied()
                            else:
                                if request.user.is_superuser or instance.has_view_permission(request.user) or instance.has_permission(request.user):
                                    return instance.display('self').contextualize(request)
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
                                    form.process()
                                return form
                            raise PermissionDenied()
                else:
                    if y.lower() == 'edit':  # /base/estado/1/edit/
                        form_cls = model.edit_form_cls()
                        form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.check_permission(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    if y.lower() == 'delete':  # /base/estado/1/delete/
                        form_cls = model.delete_form_cls()
                        form = form_cls(request=request, instance=obj, instantiator=obj)
                        if form.check_permission(request.user):
                            if form.is_valid():
                                form.process()
                            return form
                        raise PermissionDenied()
                    else:  # /base/estado/1/editar_sigla/
                        form_cls = model.action_form_cls(y)
                        if form_cls:  # instance action
                            form = form_cls(request=request, instance=obj, instantiator=obj)
                            if form.check_permission(request.user):
                                if form.is_valid():
                                    form.process()
                                return form
                            raise PermissionDenied()
                        else:  # /base/servidor/3/get_ferias/
                            if obj.has_view_attr_permission(request.user, y):
                                attr = obj.values(y)
                                output = attr.attr(y).contextualize(request)
                                if not is_ajax(request):
                                    output = output.source(obj)
                                return output
                        raise PermissionDenied()
            else:
                if request.user.is_superuser or obj.has_view_permission(request.user) or obj.has_permission(request.user):
                    return obj.view().contextualize(request)
                raise PermissionDenied()
        elif x.lower() == 'add':  # /base/estado/add/
            form_cls = model.add_form_cls()
            form = form_cls(request=request)
            if form.check_permission(request.user):
                if form.is_valid():
                    form.process()
                return form
            raise PermissionDenied()
        else:
            attr = getattr(model.objects, x, None)
            if attr:
                if model.objects.has_attr_permission(request.user, x):
                    if y:
                        if y.isdigit():  # view object in a subset
                            if z:  # /base/cidade/potiguares/1/get_dados_gerais/
                                obj = attr().contextualize(request).get(pk=y)
                                if hasattr(obj, z):
                                    if request.user.is_superuser or obj.has_view_attr_permission(request.user, z) or obj.has_permission(request.user):
                                        return obj.display(z).contextualize(request)
                                    raise PermissionDenied()
                                else:  # /base/cidade/potiguares/1/corrigir_nome/
                                    form_cls = model.action_form_cls(z)
                                    instances = attr().filter(pk__in=y.split('-'))
                                    form = form_cls(request=request, instances=instances)
                                    if form.check_permission(request.user):
                                        if form.is_valid():
                                            result = form.process()
                                            if result is not None:
                                                return result
                                        return form
                                    raise PermissionDenied()
                            else:  # /base/cidade/potiguares/1/
                                obj = model.objects.get(pk=y)
                                if request.user.is_superuser or obj.has_view_permission(request.user) or obj.has_permission(request.user):
                                    return obj.view().contextualize(request)
                                raise PermissionDenied()
                        else:  # /base/cidade/potiguares/notificar_populacao/
                            form_cls = model.action_form_cls(z)
                            instances = attr().filter(pk__in=y.split('-'))
                            form = form_cls(request=request, instances=instances)
                            if form.check_permission(request.user):
                                if form.is_valid():
                                    result = form.process()
                                    if result is not None:
                                        return result
                                return form
                            raise PermissionDenied()
                    else: # /base/cidade/potiguares/
                        output = attr().attr(x).contextualize(request)
                        if not is_ajax(request):
                            output = output.source(model.objects)
                        return output
                raise PermissionDenied()
            else:
                if y: # /base/cidade/fazer_alguma_coisa/1-2-3/
                    form_cls = model.action_form_cls(y)
                    instances = model.objects.all().filter(pk__in=x.split('-'))
                    form = form_cls(request=request, instances=instances)
                    if form.check_permission(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
                else: # /base/cidade/fazer_alguma_coisa/
                    form_cls = model.action_form_cls(x)
                    form = form_cls(request=request)
                    if form.check_permission(request.user):
                        if form.is_valid():
                            form.process()
                        return form
                    raise PermissionDenied()
    else:  # /base/estado/
        subset = request.GET.get('subset', 'all')
        if model.objects.has_attr_permission(request.user, subset):
            obj = getattr(model.objects, subset)().contextualize(request)
            if hasattr(obj, 'model'):
                obj = obj.default_actions().collapsed(False).is_admin()
            return obj
        raise PermissionDenied()
