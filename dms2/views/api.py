# -*- coding: utf-8 -*-

import traceback

from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from .. import views


def api_view(func):
    def decorate(request, *args, **kwargs):
        try:
            if views.is_authenticated(request):
                data = func(request, *args, **kwargs)
                return JsonResponse(data.serialize(wrap=False, verbose=False), safe=False)
            else:
                return JsonResponse(
                    dict(type='message', text='Usuário não autenticado', style='warning'), status=403
                )
        except PermissionDenied:
            return JsonResponse(
                dict(type='message', text='Usuário não autorizado', style='warning'), status=401
            )
        except BaseException as e:
            traceback.print_exc()
            return JsonResponse(
                dict(type='message', text=str(e), style='error'), status=500
            )

    return decorate


@csrf_exempt
@api_view
def add_view(request, app_label, model_name):
    return views.add_view(request, app_label, model_name)


@csrf_exempt
@api_view
def edit_view(request, app_label, model_name, pk):
    return views.edit_view(request, app_label, model_name, pk)


@csrf_exempt
@api_view
def delete_view(request, app_label, model_name, pk):
    return views.delete_view(request, app_label, model_name, pk)


@csrf_exempt
@api_view
def list_view(request, app_label, model_name, method=None, pks=None, action=None):
    return views.list_view(request, app_label, model_name, method=method, pks=pks, action=action)


@csrf_exempt
@api_view
def obj_view(request, app_label, model_name, pk, method=None, pks=None, action=None):
    return views.obj_view(request, app_label, model_name, pk, method=method, pks=pks, action=action)
