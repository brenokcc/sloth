# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path, re_path
from django.conf.urls import include
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('', views.index),
    path('adm/', views.index),
    path('adm/icons/', views.icons),
    path('adm/login/', views.login),
    path('adm/logout/', views.logout),
    path('adm/password/', views.password),
    path('adm/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),
    re_path(r'^apple-touch.*', views.logo),
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
) + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
