# -*- coding: utf-8 -*-
import json
import requests
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib import auth, messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from ..actions import Action
from .templatetags.tags import is_ajax
from ..api.models import PushNotification, AuthCode
from ..api.actions import Login
from ..core import views
from ..core.queryset import QuerySet
from ..utils.icons import bootstrap, materialicons, fontawesome
from ..exceptions import JsonReadyResponseException, HtmlReadyResponseException, ReadyResponseException
from .dashboard import Dashboards


def dashboard(request, path):
    if request.user.is_authenticated and settings.SLOTH.get('FORCE_PASSWORD_DEFINITION') == True and settings.SLOTH.get('DEFAULT_PASSWORD'):
        default_password = settings.SLOTH['DEFAULT_PASSWORD'](request.user)
        if request.user.check_password(default_password):
            messages.warning(request, 'Altere sua senha padrão')
            return HttpResponseRedirect('/app/dashboard/change_password/')
    try:
        ctx = dict(dashboard=Dashboards(request), settings=settings)
        if request.user.is_authenticated and request.path.startswith('/app/') and not is_ajax(request):
            if 'stack' not in request.session:
                request.session['stack'] = []
            if request.path == '/app/dashboard/':
                request.session['stack'].clear()
                request.session['stack'].append(request.path)
            elif request.path in request.session['stack']:
                index = request.session['stack'].index(request.path)
                request.session['stack'] = request.session['stack'][0:index + 1]
            else:
                request.session['stack'].append(request.path)
            request.session.save()
            referrer = request.session['stack'][-2] if len(request.session['stack']) > 1 else None
            ctx.update(referrer=referrer)
        data = views.dispatcher(request, path)
        if isinstance(data, Action):
            ctx.update(form=data)
            if data.response:
                return HttpResponse(data.html())
        else:
            ctx.update(data=data)
        response = render(request, ['app/default.html'], ctx)
        response["X-Frame-Options"] = "SAMEORIGIN"
        return response
    except ReadyResponseException as error:
        return error.response
    except JsonReadyResponseException as error:
        return JsonResponse(error.data)
    except HtmlReadyResponseException as error:
        app_messages = render_to_string('app/messages.html', request=request)
        return HttpResponse(app_messages + error.html)
    except PermissionDenied:
        return HttpResponseForbidden()
    except BaseException as error:
        raise error


def manifest(request):
    return JsonResponse(
        {
            "name": settings.SLOTH['NAME'],
            "short_name": settings.SLOTH['NAME'],
            "lang": settings.LANGUAGE_CODE,
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "icons": [{
                "src": settings.SLOTH['ICON'],
                "sizes": "192x192",
                "type": "image/png"
            }]
        },
        headers={'Cache-Control': 'public, max-age=31557600'}
    )


def icon(request):
    return HttpResponseRedirect(settings.SLOTH['ICON'] or '/static/images/icon.png')


def favicon(request):
    return HttpResponseRedirect(settings.SLOTH['FAVICON'] or '/static/images/icon.png')


def index(request):
    return HttpResponseRedirect('/app/dashboard/' if request.user.is_authenticated else '/app/dashboard/login/')
