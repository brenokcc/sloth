# -*- coding: utf-8 -*-

from django.urls import path

from ..views import adm


urlpatterns = [
    path('', adm.index),
    path('icons/', adm.icons),
    path('login/<str:username>/', adm.login),

    path('<str:app_label>/<str:model_name>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<str:x>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/<str:w>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/', adm.obj_view),
]
