# -*- coding: utf-8 -*-

from django.apps import apps
from django.urls import path
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/', views.index),
    path('api/docs/', views.index),
]

for model_name in apps.get_app_config('api').models.keys():
    urlpatterns.extend([
        path('api/{}/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/<str:w>/<str:k>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/<str:w>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/'.format(model_name), views.api_model_dispatcher),

        path('api/{}/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/<str:w>/<str:k>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/<str:w>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/<str:z>/'.format(model_name), views.api_model_dispatcher),
        path('api/{}/<str:x>/<str:y>/'.format(model_name), views.api_model_dispatcher),
    ])

urlpatterns.extend([
    path('api/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('api/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),

    path('meta/<str:app_label>/<str:model_name>/', views.dispatcher),
    path('meta/<str:app_label>/<str:model_name>/<str:x>/', views.dispatcher),
    path('meta/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/<str:w>/', views.dispatcher),
    path('meta/<str:app_label>/<str:model_name>/<str:x>/<str:y>/<str:z>/', views.dispatcher),
    path('meta/<str:app_label>/<str:model_name>/<str:x>/<str:y>/', views.dispatcher),
])

urlpatterns.extend(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))
urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
