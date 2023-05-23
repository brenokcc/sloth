# -*- coding: utf-8 -*-
import json
import base64
import traceback
from datetime import datetime

from django.views import static

from sloth import threadlocals
from django.core.cache import cache
from django.http import QueryDict
from django.apps import apps
from oauth2_provider.oauth2_backends import get_oauthlib_core
from ..core.valueset import ValueSet
from ..utils.http import ApiResponse
from django.contrib.auth import authenticate
from ..api import OpenApi
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from ..actions import Action, ACTIONS, EXPOSE
from .templatetags.tags import is_ajax
from ..core.queryset import QuerySet
from sloth.api.exceptions import JsonReadyResponseException, HtmlReadyResponseException, ReadyResponseException
from .dashboard import Dashboards, Dashboard
from .. import initialize


initialize()


def logger(func):
    def decorate(request, *args, **kwargs):
        threadlocals.transaction = dict(
            user=request.user.username, operation=None, time=datetime.now().strftime('%d/%m/%Y %H:%M'), path=request.path, diff=[]
        )
        response = func(request, *args, **kwargs)
        if threadlocals.transaction['diff']:
            print(json.dumps(threadlocals.transaction, ensure_ascii=False))
        return response
    return decorate


def media(request, path):
    return static.serve(request, path, document_root=settings.MEDIA_ROOT)


@logger
def app(request, path):
    if request.user.is_authenticated and settings.FORCE_PASSWORD_DEFINITION:
        default_password = settings.DEFAULT_PASSWORD(request.user)
        if request.user.check_password(default_password):
            messages.warning(request, 'Altere sua senha padrão')
            return HttpResponseRedirect('/app/dashboard/change_password/')
    try:
        ctx = dict(dashboard=Dashboards(request))
        if request.user.is_authenticated and request.path.startswith('/app/') and not is_ajax(request):
            if 'stack' not in request.session:
                request.session['stack'] = []
            if request.path == '/app/dashboard/':
                request.session['stack'].clear()
                request.session['stack'].append(request.path)
            elif request.path in request.session['stack']:
                i = request.session['stack'].index(request.path)
                request.session['stack'] = request.session['stack'][0:i + 1]
            else:
                request.session['stack'].append(request.path)
            request.session.save()
            referrer = request.session['stack'][-2] if len(request.session['stack']) > 1 else None
            ctx.update(referrer=referrer)
        data = dispatcher(request, path)
        if isinstance(data, Action):
            ctx.update(form=data)
            if data.response:
                return HttpResponse(data.html())
        else:
            ctx.update(data=data)
        response = render(request, ['dashboard/default.html'], ctx)
        response["X-Frame-Options"] = "SAMEORIGIN"
        return response
    except ReadyResponseException as error:
        return error.response
    except JsonReadyResponseException as error:
        return JsonResponse(error.data)
    except HtmlReadyResponseException as error:
        app_messages = render_to_string('dashboard/messages.html', request=request)
        return HttpResponse(app_messages + error.html)
    except PermissionDenied:
        return HttpResponseForbidden()
    except BaseException as error:
        raise error


def manifest(request):
    return JsonResponse(
        {
            "name": cache.get('title', 'Sloth'),
            "short_name": cache.get('title', 'Sloth'),
            "lang": settings.LANGUAGE_CODE,
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "icons": [{
                "src": cache.get('icon', '/static/images/icon.png'),
                "sizes": "192x192",
                "type": "image/png"
            }]
        },
        headers={'Cache-Control': 'public, max-age=31557600'}
    )


def icon(request):
    return HttpResponseRedirect(cache.get('icon', '/static/images/icon.png'))


def favicon(request):
    return HttpResponseRedirect(cache.get('favicon', '/static/images/icon.png'))


def index(request):
    return HttpResponseRedirect('/app/dashboard/' if request.user.is_authenticated else '/app/dashboard/login/')


def endpoint(func):
    def decorate(request, *args, **kwargs):
        try:
            if is_authenticated(request):
                data = func(request, *args, **kwargs)
                wrap = request.path.startswith('/meta')
                serialized = data.serialize(wrap=wrap)
                if request.path == '/meta/dashboard/':
                    dashboard = Dashboards(request)
                    serialized = dashboard.serialize(serialized)
                # from pprint import pprint; pprint(serialized)
                return ApiResponse(serialized, safe=False)
            else:
                return ApiResponse(
                    dict(type='message', text='Usuário não autenticado', style='warning'), status=403
                )
        except JsonReadyResponseException as e:
            return ApiResponse(e.data, safe=False)
        except PermissionDenied:
            return ApiResponse(
                dict(type='message', text='Usuário não autorizado', style='warning'), status=401
            )
        except BaseException as e:
            traceback.print_exc()
            return ApiResponse(
                dict(type='message', text=str(e), style='error'), status=500
            )

    return decorate


def docs(request):
    if request.path.startswith('/api/docs/'):
        api = OpenApi(request)
        if 'filters' in request.GET:
            return ApiResponse(
                dict(apps=api.apps, scopes=api.scopes)
            )
        else:
            return ApiResponse(api)
    return render(request, ['api/index.html'], dict())


@csrf_exempt
@endpoint
def api_dispatcher(request, path):
    if request.method == 'GET':
        pass
    if request.method == 'POST':
        pass
    if request.method == 'PUT':
        request.POST = QueryDict(request.body)
    if request.method == 'DELETE':
        request.POST = QueryDict('confirmation=1')
    return dispatcher(request, path)


@csrf_exempt
def api_model_dispatcher(request, path=None):
    if path:
        return api_dispatcher(request, 'api/{}/{}'.format(request.path.split('/')[2], path))
    return api_dispatcher(request, 'api/{}'.format(request.path.split('/')[2]))


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


def dispatcher(request, path):
    allowed_attrs = []
    extra_attrs = []
    instance = None
    instances = None
    instantiator = None
    queryset = None
    tokens = [token for token in path.split('/') if '=' not in token]
    token = tokens.pop(0)
    if token == 'dashboard':
        obj = Dashboards(request).main()
        if tokens:
            allowed_attrs = obj.view().get_allowed_attrs()
        else:
            obj = obj.view()
            allowed_attrs = obj.get_allowed_attrs()
            if not request.user.is_authenticated: raise PermissionDenied()
    elif token in settings.INSTALLED_APPS or token in ('api', 'auth'):
        app_label, model_name = token, tokens.pop(0)
        obj = apps.get_model(app_label, model_name).objects.view()
        if isinstance(obj, QuerySet):
            queryset = obj
            obj = obj.default_actions().expand().admin()
        allowed_attrs = obj.get_allowed_attrs()
        if not tokens and not obj.has_permission(request.user):
            raise PermissionDenied()
    else:
        raise PermissionDenied()
    for i, token in enumerate(tokens):
        if i == 0:
            allowed_attrs.extend(EXPOSE)
        if not request.user.is_authenticated and token not in allowed_attrs and token not in extra_attrs and not token.isdigit() and '-' not in token:
            # print(token, type(obj).__name__, allowed_attrs, extra_attrs)
            raise PermissionDenied()
        if token.isdigit():
            if isinstance(obj, Dashboard):
                obj = obj.view()
            extra_attrs = obj.metadata['actions'] + obj.metadata['inline_actions'] + ['view' if view['name'] == 'self' else view['name'] for view in obj.metadata['view']]
            obj = obj.contextualize(request).apply_role_lookups(request.user).filter(pk=token).first()
            if obj:
                instance = obj
                instances = None
            else:
                raise PermissionDenied()
        elif '-' in token:
            if isinstance(obj, Dashboard):
                obj = obj.view()
            extra_attrs = obj.metadata['batch_actions']
            obj = obj.contextualize(request).apply_role_lookups(request.user).filter(pk__in=token.split('-'))
            instance = None
            instances = obj
            queryset = obj
        elif token in ACTIONS or token in ('add', 'edit', 'delete'):
            if token in ('edit', 'delete') and instance is None and instances is None:
                raise PermissionDenied()
            if token == 'add' and isinstance(obj, QuerySet) and obj.metadata['related_field']:
                form_cls = obj.model.relation_form_cls(obj.metadata['related_field'])
            else:
                form_cls = obj.action_form_cls(token)
            # print(token, dict(action=form_cls, instantiator=instantiator, instance=instance, instances=instances, queryset=queryset))
            form = form_cls(
                request=request, instantiator=instantiator, instance=instance, instances=instances, queryset=queryset
            )
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
                queryset = None
                if isinstance(obj, ValueSet):
                    instantiator = obj.instance
                    obj = getattr(obj.instance, token)()
                else:
                    instantiator = obj
                    obj = getattr(obj, token)()
                if isinstance(obj, ValueSet):
                    instance = obj.instance
                if isinstance(obj, QuerySet):
                    queryset = obj
                    if 'global_action' in request.GET:
                        queryset = obj.process_request(request, uuid=token).apply_role_lookups(request.user)
        allowed_attrs = obj.get_allowed_attrs()
    obj = obj.contextualize(request).apply_role_lookups(request.user)
    if request.path.startswith('/api/') and isinstance(obj, QuerySet):
        obj = obj.process_request(request)
    return obj
