# -*- coding: utf-8 -*-
from django.urls import path, re_path
from . import views


urlpatterns = [
    path('', views.index),
    path('app/', views.app),
    path('app/manifest/', views.manifest),
    path('app/icons/', views.icons),
    path('app/login/', views.login),
    path('app/login/<str:provider_name>/', views.oauth_login),
    path('app/roles/', views.roles),
    path('app/roles/<str:activate>/', views.roles),
    path('app/logout/', views.logout),
    path('app/push_subscription/', views.push_subscription),
    path('app/action/<str:name>/', views.action),
    path('app/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/<str:k>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),
    path('icon', views.icon),
    path('favicon.ico', views.favicon),
    re_path(r'^apple-touch.*', views.icon),
]
