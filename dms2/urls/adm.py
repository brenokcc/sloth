# -*- coding: utf-8 -*-

from django.urls import path

from ..views import adm


urlpatterns = [
    path('', adm.index),
    path('icons/', adm.icons),
    path('login/<str:username>/', adm.login),

    path('<str:app_label>/<str:model_name>/', adm.list_view),
    path('<str:app_label>/<str:model_name>/add/', adm.add_view),
    path('<str:app_label>/<str:model_name>/Add/', adm.add_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/edit/', adm.edit_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/delete/', adm.delete_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/<str:action>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<str:pk>/', adm.obj_view),
    path('<str:app_label>/<str:model_name>/<str:method>/<str:pks>/<str:action>/', adm.list_view),
    path('<str:app_label>/<str:model_name>/<str:pk>/<str:method>/', adm.obj_view),
]
