# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path, re_path
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('', views.index),
    path('app/', views.app),
    path('app/manifest/', views.manifest),
    path('app/icons/', views.icons),
    path('app/login/', views.login),
    path('app/logout/', views.logout),
    path('app/password/', views.password),
    path('app/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('app/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),
    path('logo', views.logo),
    re_path(r'^apple-touch.*', views.logo),
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
) + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
