# -*- coding: utf-8 -*-
from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index),
    path('app/', views.index),
    path('app/manifest/', views.manifest),
    path('icon', views.icon),
    path('favicon.ico', views.favicon),
    re_path(r'^apple-touch.*', views.icon),
    re_path(r'^app/(?P<path>.*)/$', views.dashboard),
]
