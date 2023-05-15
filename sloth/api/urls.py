# -*- coding: utf-8 -*-

from django.urls import path, re_path
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.apps import apps
from . import views


urlpatterns = [
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/', views.docs),
    path('api/docs/', views.docs),
]

for model_name in apps.get_app_config('api').models.keys():
    urlpatterns.append(path('api/{}/'.format(model_name), views.api_model_dispatcher))
    urlpatterns.append(re_path(r'^api/{}/(?P<path>.*)/$'.format(model_name), views.api_model_dispatcher))
    urlpatterns.append(re_path(r'^meta/{}/(?P<path>.*)/$'.format(model_name), views.api_model_dispatcher))

urlpatterns.append(re_path(r'^api/(?P<path>.*)/$', views.api_dispatcher))
urlpatterns.append(re_path(r'^meta/(?P<path>.*)/$', views.api_dispatcher))

urlpatterns.extend(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))


urlpatterns.extend([
    path('', views.index),
    path('app/', views.index),
    path('app/manifest/', views.manifest),
    path('icon', views.icon),
    path('favicon.ico', views.favicon),
    re_path(r'^apple-touch.*', views.icon),
    re_path(r'^app/(?P<path>.*)/$', views.app),
])
