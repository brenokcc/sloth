# -*- coding: utf-8 -*-

from django.urls import path

from ..views import api

urlpatterns = [
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/<str:action>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/edit/', api.edit_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/delete/', api.delete_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/', api.obj_view),

    path('<str:app_label>/<str:model_name>/add/', api.add_view),
    path('<str:app_label>/<str:model_name>/<str:method>/<str:pks>/<str:action>/', api.list_view),
    path('<str:app_label>/<str:model_name>/<str:method>/', api.list_view),
    path('<str:app_label>/<str:model_name>/', api.list_view),
]
