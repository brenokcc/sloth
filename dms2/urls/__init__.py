from django.urls import path
from ..views import api_list, api_view

urlpatterns = [


    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/<str:action>/', api_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/', api_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/', api_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/', api_view),

    path('<str:app_label>/<str:model_name>/<str:method>/<str:pks>/<str:action>/', api_list),
    path('<str:app_label>/<str:model_name>/<str:method>/', api_list),
    path('<str:app_label>/<str:model_name>/', api_list),

]
