# -*- coding: utf-8 -*-

from django.urls import path
from django.conf.urls import include
from . import views


urlpatterns = [
    path('api/', views.index),
    path('api/docs/', views.index),
    path('api/<str:app_label>/<str:model_name>/', views.obj_view),
    path('api/<str:app_label>/<str:model_name>/<str:x>/', views.obj_view),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.obj_view),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.obj_view),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.obj_view),

    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
