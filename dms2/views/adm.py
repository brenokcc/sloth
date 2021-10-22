# -*- coding: utf-8 -*-
import traceback

from django.apps import apps
from django.contrib import auth
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import render
from .. import views
from ..exceptions import ReadyResponseException, HtmlReadyResponseException


def view(func):
    def decorate(request, *args, **kwargs):
        try:
            if views.is_authenticated(request):
                return func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden()
        except ReadyResponseException as e:
            return JsonResponse(e.data)
        except HtmlReadyResponseException as e:
            return HttpResponse(e.html)
        except PermissionDenied:
            return HttpResponseForbidden()
        except BaseException as e:
            raise e

    return decorate


def login(request, username):
    if settings.DEBUG and request.get_host() == 'localhost:8000':
        user = apps.get_model(
            settings.AUTH_USER_MODEL
        ).objects.get(username=username)
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return index(request)


def index(request):
    return render(request, ['adm/index.html'], dict())


def add_view(request, app_label, model_name):
    form = views.add_view(request, app_label, model_name)
    return render(request, ['adm/add.html'], dict(form=form))


def edit_view(request, app_label, model_name, pk):
    form = views.edit_view(request, app_label, model_name, pk)
    print(form.serialize())
    if form.message:
        pass
    return render(request, ['adm/add.html'], dict(form=form))


def delete_view(request, app_label, model_name, pk):
    data = views.delete_view(request, app_label, model_name, pk)
    return render(request, ['adm/delete.html'], dict(data=data))


@view
def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    data = views.list_view(request, app_label, model_name, method=method, pks=pks, action=action)
    return render(request, ['adm/list.html'], dict(data=data))


def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    data = views.obj_view(request, app_label, model_name, pk, method=method, pks=pks, action=action)
    print(data.serialize())
    return render(request, ['adm/view.html'], dict(data=data))
