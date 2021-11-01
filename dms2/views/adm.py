# -*- coding: utf-8 -*-
import time

from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string

from .. import views
from ..forms import FormMixin, LoginForm
from ..utils.icons import bootstrap
from ..exceptions import ReadyResponseException, HtmlReadyResponseException


def view(func):
    def decorate(request, *args, **kwargs):
        try:
            time.sleep(0.5)
            if views.is_authenticated(request):
                response = func(request, *args, **kwargs)
                response["X-Frame-Options"] = "SAMEORIGIN"
                return response
            else:
                return HttpResponseForbidden()
        except ReadyResponseException as e:
            return JsonResponse(e.data)
        except HtmlReadyResponseException as e:
            messages = render_to_string('adm/messages.html', request=request)
            return HttpResponse(messages + e.html)
        except PermissionDenied:
            return HttpResponseForbidden()
        except BaseException as e:
            raise e

    return decorate


@view
def icons(request):
    return render(request, ['adm/icons.html'], dict(bootstrap=bootstrap.ICONS))


def login(request):
    form = LoginForm(request=request)
    if form.is_valid():
        form.process()
        return HttpResponseRedirect('/adm/')
    return render(request, ['adm/login.html'], dict(form=form))


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/adm/login/')


def index(request):
    request.COOKIES.get('width')
    if request.user.is_authenticated:
        return render(request, ['adm/index.html'], dict())
    return HttpResponseRedirect('/adm/login/')


@view
def obj_view(request, app_label, model_name, x=None, y=None, z=None, w=None):
    context = {}
    data = views.obj_view(request, app_label, model_name, x=x, y=y, z=z, w=w)
    # data.debug()
    if isinstance(data, FormMixin):
        context.update(form=data)
        if data.message:
            return HttpResponse('..')
    else:
        context.update(data=data)
    return render(request, ['adm/default.html'], context)
