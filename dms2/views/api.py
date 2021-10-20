# -*- coding: utf-8 -*-

import traceback
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .. import views
from ..api import OpenApi


class ApiResponse(JsonResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["Access-Control-Allow-Origin"] = "*"
        self["Access-Control-Allow-Headers"] = "*"
        self["X-Frame-Options"] = "SAMEORIGIN"


def endpoint(func):
    def decorate(request, *args, **kwargs):
        try:
            if views.is_authenticated(request):
                data = func(request, *args, **kwargs)
                return ApiResponse(data.serialize(wrap=False, verbose=False), safe=False)
            else:
                return ApiResponse(
                    dict(type='message', text='Usuário não autenticado', style='warning'), status=403
                )
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


def index(request):
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
def add_view(request, app_label, model_name):
    return views.add_view(request, app_label, model_name)


@csrf_exempt
@endpoint
def edit_view(request, app_label, model_name, pk):
    return views.edit_view(request, app_label, model_name, pk)


@csrf_exempt
@endpoint
def delete_view(request, app_label, model_name, pk):
    return views.delete_view(request, app_label, model_name, pk)


@csrf_exempt
@endpoint
def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    return views.list_view(request, app_label, model_name, method=method, pks=pks, action=action)


@csrf_exempt
@endpoint
def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    return views.obj_view(request, app_label, model_name, pk, method=method, pks=pks, action=action)
