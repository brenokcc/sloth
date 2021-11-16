# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path
from django.conf.urls import include
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('', views.index),
    path('adm/', views.index),
    path('adm/icons/', views.icons),
    path('adm/login/', views.login),
    path('adm/logout/', views.logout),
    path('adm/<str:app_label>/<str:model_name>/', views.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/', views.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.obj_view),
    path('adm/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.obj_view),
] + static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
) + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
