# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import auth, messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string

from .templatetags.tags import is_ajax
from ..core import views
from ..actions import Action, LoginForm, PasswordForm

from ..utils.icons import bootstrap
from ..exceptions import JsonReadyResponseException, HtmlJsonReadyResponseException, ReadyResponseException
from . import dashboard


def view(func):
    def decorate(request, *args, **kwargs):
        try:
            # import time; time.sleep(0.5)
            response = func(request, *args, **kwargs)
            response["X-Frame-Options"] = "SAMEORIGIN"
            return response
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


def context(request, **kwargs):
    kwargs.update(settings=settings)
    if request.user.is_authenticated:
        if request.path.startswith('/app/') and not is_ajax(request):
            if 'stack' not in request.session:
                request.session['stack'] = []
            if request.path == '/app/':
                request.session['stack'].clear()
                request.session['stack'].append(request.path)
                request.session.save()
            elif request.path in request.session['stack']:
                index = request.session['stack'].index(request.path)
                request.session['stack'] = request.session['stack'][0:index + 1]
            else:
                request.session['stack'].append(request.path)
            referrer = request.session['stack'][-2] if len(request.session['stack']) > 1 else None
            return dict(referrer=referrer, **kwargs)
    return kwargs


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
        if request.user.is_superuser or settings.SLOTH['ROLES']['ALLOW_MULTIPLE']:
            return HttpResponseRedirect('/app/')
        else:
            if request.user.roles.filter(active=True).count() == 1:
                return HttpResponseRedirect('/app/')
            else:
                request.user.roles.update(active=False)
                return HttpResponseRedirect('/app/roles/')
    return render(request, ['app/login.html'], context(request, form=form))


def password(request):
    form = PasswordForm(request=request)
    if form.is_valid():
        form.submit()
        return HttpResponseRedirect('..')
    return render(request, ['app/default.html'], context(request, form=form))


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
    if request.user.is_authenticated:
        return render(
            request, [getattr(settings, 'INDEX_TEMPLATE', 'app/index.html')],
            context(request, dashboard=dashboard.Dashboards(request))
        )
    return HttpResponseRedirect('/app/login/')

@view
def roles(request, activate=None):
    if activate:
        request.user.roles.update(active=False)
        roles = request.user.roles.filter(pk__in=activate.split('-'))
        updated = roles.update(active=True)
        if updated == 1:
            message = 'Perfil "{}" ativado com sucesso.'.format(roles.first().name)
        else:
            message = 'Perfis "{}" ativos com sucesso'.format(', '.join([role.name for role in roles]))
        messages.success(request, message)
        return HttpResponseRedirect('/app/')
    return render(request, ['app/roles.html'], context(request))


@view
def dispatcher(request, app_label, model_name, x=None, y=None, z=None, w=None):
    ctx = context(request, dashboard=dashboard.Dashboards(request))
    data = views.dispatcher(request, app_label, model_name, x=None if x == 'all' else x, y=y, z=z, w=w)
    if isinstance(data, Action):
        ctx.update(form=data)
        if data.response:
            html = data.response.get('html')
            if html:
                return HttpResponse(data.response['html'])
            return HttpResponse(data.response['url'])
    else:
        ctx.update(data=data)
    return render(request, ['app/default.html'], ctx)
