# -*- coding: utf-8 -*-

import base64
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from oauth2_provider.oauth2_backends import get_oauthlib_core

from ..core.valueset import ValueSet
from ..core.valueset import QuerySet
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
    allowed_attrs = []
    extra_attrs = []
    instance = None
    instances = None
    instantiator = None
    tokens = path.split('/')
    token = tokens.pop(0)
    if token == 'dashboard':
        obj = Dashboards(request).main()
        if tokens:
            allowed_attrs = obj.view().get_allowed_attrs()
        else:
            obj = obj.view()
            allowed_attrs = obj.get_allowed_attrs()
        if not request.user.is_authenticated:
            raise PermissionDenied()
    elif token in settings.INSTALLED_APPS or token in ('api', 'auth'):
        app_label, model_name = token, tokens.pop(0)
        obj = apps.get_model(app_label, model_name).objects.view()
        if isinstance(obj, QuerySet):
            obj = obj.default_actions().expand().admin()
        allowed_attrs = obj.get_allowed_attrs()
        if not tokens and not obj.has_permission(request.user):
            raise PermissionDenied()
    else:
        raise PermissionDenied()
    for i, token in enumerate(tokens):
        allowed_attrs.append('ChangePassword')
        if  not request.user.is_authenticated and token not in allowed_attrs and token not in extra_attrs and not token.isdigit() and '-' not in token:
            print(token, type(obj).__name__, allowed_attrs, extra_attrs)
            raise PermissionDenied()
        if token.isdigit():
            extra_attrs = obj.metadata['actions'] + obj.metadata['inline_actions'] + ['view' if view['name'] == 'self' else view['name'] for view in obj.metadata['view']]
            obj = obj.contextualize(request).apply_role_lookups(request.user).filter(pk=token).first()
            if obj:
                instance = obj
                instances = None
            else:
                raise PermissionDenied()
        elif '-' in token:
            extra_attrs = obj.metadata['batch_actions']
            obj = obj.contextualize(request).apply_role_lookups(request.user).filter(pk__in=token.split('-'))
            instance = None
            instances = obj
        elif token in ACTIONS or token in ('add', 'edit', 'delete'):
            if token in ('edit', 'delete') and instance is None and instances is None:
                raise PermissionDenied()
            form_cls = obj.action_form_cls(token)
            # print(dict(action=form_cls, instantiator=instantiator, instance=instance, instances=instances))
            form = form_cls(request=request, instantiator=instantiator, instance=instance, instances=instances)
            if form.check_permission(request.user):
                if form.is_valid():
                    result = form.process()
                    if result is not None and form.has_url_posted_data():
                        obj = result
                    else:
                        obj = form
                else:
                    obj = form
            else:
                raise PermissionDenied()
        else:
            if i == len(tokens) - 1:  # last
                obj = obj.attr(token, source=not is_ajax(request))
            else:
                instance = None
                instances = None
                if isinstance(obj, ValueSet):
                    instantiator = obj.instance
                    obj = getattr(obj.instance, token)()
                else:
                    instantiator = obj
                    obj = getattr(obj, token)()
                if isinstance(obj, ValueSet):
                    instance = instantiator
        allowed_attrs = obj.get_allowed_attrs()
    return obj.contextualize(request).apply_role_lookups(request.user)
