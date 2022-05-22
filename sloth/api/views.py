# -*- coding: utf-8 -*-

import traceback
from django.shortcuts import render
from django.http import QueryDict
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from ..core import views
from ..api import OpenApi
from ..exceptions import JsonReadyResponseException


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
                wrap = request.path.startswith('/meta')
                verbose = request.path.startswith('/meta')
                return ApiResponse(data.serialize(wrap=wrap, verbose=verbose), safe=False)
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
def dispatcher(request, app_label, model_name, x=None, y=None, z=None, w=None, k=None):
    if request.method == 'GET' and x == 'all':
        x = None
    if request.method == 'POST' and x is None and y is None:
        x = 'add'
    if request.method == 'PUT' and x is not None and y is None:
        request.POST = QueryDict(request.body)
        y = 'edit'
    if request.method == 'DELETE' and x is not None and y is None:
        request.POST = QueryDict('confirmation=1')
        y = 'delete'
    return views.dispatcher(request, app_label, model_name, x=x, y=y, z=z, w=w, k=k)


@csrf_exempt
def api_model_dispatcher(request, x=None, y=None, z=None, w=None, k=None):
    app_label = 'api'
    model_name = request.path.split('/')[2]
    return dispatcher(request, app_label, model_name, x=x, y=y, z=z, w=w, k=k)
