# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string

from ..core import views
from ..actions import Action, LoginForm, PasswordForm

from ..utils.icons import bootstrap
from ..exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from . import dashboard


def view(func):
    def decorate(request, *args, **kwargs):
        try:
            # import time; time.sleep(0.5)
            if views.is_authenticated(request):
                response = func(request, *args, **kwargs)
                response["X-Frame-Options"] = "SAMEORIGIN"
                return response
            else:
                return HttpResponseRedirect('/app/login/')
        except ReadyResponseException as e:
            return e.response
        except JsonReadyResponseException as e:
            return JsonResponse(e.data)
        except HtmlJsonReadyResponseException as e:
            messages = render_to_string('app/messages.html', request=request)
            return HttpResponse(messages + e.html)
        except PermissionDenied:
            return HttpResponseForbidden()
        except BaseException as e:
            raise e

    return decorate


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


def icons(request):
    return render(request, ['app/icons.html'], dict(bootstrap=bootstrap.ICONS))


def logo(request):
    return HttpResponseRedirect(settings.LOGO)


def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/app/')
    form = LoginForm(request=request)
    if form.is_valid():
        form.submit()
        return HttpResponseRedirect('/app/')
    return render(request, ['app/login.html'], dict(form=form, settings=settings))


def password(request):
    form = PasswordForm(request=request)
    if form.is_valid():
        form.submit()
        return HttpResponseRedirect('..')
    return render(request, ['app/default.html'], dict(form=form, settings=settings))


def logout(request):
    request.session.clear()
    request.session.save()
    auth.logout(request)
    return HttpResponseRedirect('/')


def index(request):
    return HttpResponseRedirect('/app/')


@view
def app(request):
    request.COOKIES.get('width')
    return render(
        request, [getattr(settings, 'INDEX_TEMPLATE', 'app/index.html')],
        dict(settings=settings, dashboard=dashboard.Dashboards(request))
    )


@view
def dispatcher(request, app_label, model_name, x=None, y=None, z=None, w=None):
    context = dict(settings=settings, dashboard=dashboard.Dashboards(request))
    data = views.dispatcher(request, app_label, model_name, x=None if x == 'all' else x, y=y, z=z, w=w)
    if isinstance(data, Action):
        context.update(form=data)
        if data.response:
            html = data.response.get('html')
            if html:
                return HttpResponse(data.response['html'])
            return HttpResponse(data.response['url'])
    else:
        context.update(data=data)
    return render(request, ['app/default.html'], context)
