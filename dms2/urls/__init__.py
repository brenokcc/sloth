# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path
from django.conf.urls import include
from django.conf.urls.static import static
from ..views import adm, api


urlpatterns = [
    path('', adm.index),
    path('adm/', adm.index),
    path('adm/icons/', adm.icons),
    path('adm/login/', adm.login),
    path('adm/logout/', adm.logout),
    path('adm/<str:app_label>/<str:model_name>/', adm.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/', adm.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/<str:w>/', adm.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/', adm.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<int:x>/<str:y>/', adm.obj_view),

    path('api/', api.index),
    path('api/docs/', api.index),
    path('api/<str:app_label>/<str:model_name>/', api.obj_view),
    path('api/<str:app_label>/<str:model_name>/<str:x>/', api.obj_view),
    path('api/<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/<str:w>/', api.obj_view),
    path('api/<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/', api.obj_view),
    path('api/<str:app_label>/<str:model_name>/<int:x>/<str:y>/', api.obj_view),

    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
