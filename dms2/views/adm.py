# -*- coding: utf-8 -*-

from django.apps import apps
from django.contrib import auth
from django.conf import settings
from django.shortcuts import render
from .. import views


def login(request, username):
    if settings.DEBUG and request.get_host() == 'localhost:8000':
        user = apps.get_model(
            settings.AUTH_USER_MODEL
        ).objects.get(username=username)
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return index(request)


def index(request):
    return render(request, ['index.html'], dict())


def add_view(request, app_label, model_name):
    data = views.add_view(request, app_label, model_name)
    return render(request, ['add.html'], dict(data=data))


def edit_view(request, app_label, model_name, pk):
    data = views.edit_view(request, app_label, model_name, pk)
    return render(request, ['edit.html'], dict(data=data))


def delete_view(request, app_label, model_name, pk):
    data = views.delete_view(request, app_label, model_name, pk)
    return render(request, ['delete.html'], dict(data=data))


def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    data = views.list_view(request, app_label, model_name, method=method, pks=pks, action=action)
    return render(request, ['list.html'], dict(data=data))


def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    data = views.obj_view(request, app_label, model_name, pk, method=method, pks=pks, action=action)
    return render(request, ['view.html'], dict(data=data))
