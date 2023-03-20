# -*- coding: utf-8 -*-
from django.urls import path, re_path
from . import views


urlpatterns = [
    path('', views.index),
    path('app/', views.index),
    path('app/manifest/', views.manifest),
    path('app/icons/', views.icons),
    path('app/login/', views.login),
    path('app/login/<str:provider_name>/', views.oauth_login),
    path('app/roles/', views.roles),
    path('app/roles/<str:activate>/', views.roles),
    path('app/logout/', views.logout),
    path('app/queryset/', views.queryset),
    path('app/push_subscription/', views.push_subscription),
    re_path(r'^app/(?P<path>.*)/$', views.dispatcher),
    path('icon', views.icon),
    path('favicon.ico', views.favicon),
    re_path(r'^apple-touch.*', views.icon),
]
