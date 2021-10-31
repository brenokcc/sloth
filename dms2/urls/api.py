# -*- coding: utf-8 -*-

from django.urls import path

from ..views import api

urlpatterns = [
    path('', api.index),
    path('docs/', api.index),

    path('<str:app_label>/<str:model_name>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<str:x>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/<str:w>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/<str:z>/', api.obj_view),
    path('<str:app_label>/<str:model_name>/<int:x>/<str:y>/', api.obj_view),
]
