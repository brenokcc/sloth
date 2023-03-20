# -*- coding: utf-8 -*-

from django.urls import path, re_path
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.apps import apps
from . import views


urlpatterns = [
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/', views.index),
    path('api/docs/', views.index),
]

for model_name in apps.get_app_config('api').models.keys():
    urlpatterns.append(path('api/{}/'.format(model_name), views.api_model_dispatcher))
    urlpatterns.append(re_path(r'^api/{}/(?P<path>.*)/$'.format(model_name), views.api_model_dispatcher))
    urlpatterns.append(re_path(r'^meta/{}/(?P<path>.*)/$'.format(model_name), views.api_model_dispatcher))

urlpatterns.append(re_path(r'^api/(?P<path>.*)/$', views.dispatcher))
urlpatterns.append(re_path(r'^meta/(?P<path>.*)/$', views.dispatcher))

urlpatterns.extend(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
