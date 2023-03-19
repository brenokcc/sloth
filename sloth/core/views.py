# -*- coding: utf-8 -*-

import base64
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from oauth2_provider.oauth2_backends import get_oauthlib_core

from ..app.dashboard import Dashboards
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
    form = form_cls(request=request)
    if form.check_permission(request.user):
        if form.is_valid():
            form.process()
        return form
    raise PermissionDenied()


def dispatcher(request, path):
    instance = None
    instances = None
    instantiator = None
    tokens = path.split('/')
    token = tokens.pop(0)
    if token == 'dashboard':
        dashboard = Dashboards(request).main()
        obj = dashboard if tokens else dashboard.view()
        if not request.user.is_authenticated:
            raise PermissionDenied()
    elif token in settings.INSTALLED_APPS or token == 'api':
        app_label, model_name = token, tokens.pop(0)
        if tokens:
            obj = apps.get_model(app_label, model_name).objects.get_queryset()
            if tokens[0].isdigit() or '-' in tokens[0]:
                obj = obj.all()
        else:
            obj = apps.get_model(app_label, model_name).objects.all().default_actions().collapsed(False).admin()
            if not obj.has_permission(request.user):
                raise PermissionDenied()
    else:
        raise PermissionDenied()
    for i, token in enumerate(tokens):
        if token.isdigit():
            obj = obj.contextualize(request).apply_role_lookups(request.user).get(pk=token)
            instance = obj
            instances = None
        elif '-' in token:
            obj = obj.contextualize(request).apply_role_lookups(request.user).filter(pk__in=token.split('-'))
            instance = None
            instances = obj
        elif token in ACTIONS:
            form_cls = obj.action_form_cls(token)
            # print(dict(action=form_cls, instantiator=instantiator, instance=instance, instances=instances))
            form = form_cls(request=request, instantiator=instantiator, instance=instance, instances=instances)
            if form.check_permission(request.user):
                if form.is_valid():
                    result = form.process()
                    if result is not None:
                        obj = result
                    else:
                        obj = form
                else:
                    obj = form
            else:
                raise PermissionDenied()
        else:
            if i == len(tokens) - 1:
                obj = obj.attr(token, source=not is_ajax(request))
            else:
                instance = None
                instances = None
                instantiator = obj
                obj = getattr(obj, token)()
    return obj.contextualize(request)
