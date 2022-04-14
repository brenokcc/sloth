# -*- coding: utf-8 -*-

from django.urls import path
from django.conf.urls import include
from . import views


urlpatterns = [
    path('api/', views.index),
    path('api/docs/', views.index),
    path('api/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),

    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
]
