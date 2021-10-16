from django.urls import path
from ..views import list_view, obj_view, add_view, edit_view, delete_view

urlpatterns = [


    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/<str:action>/', obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/<str:pks>/', obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/edit/', edit_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/delete/', delete_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/<str:method>/', obj_view),
    path('<str:app_label>/<str:model_name>/<int:pk>/', obj_view),

    path('<str:app_label>/<str:model_name>/add/', add_view),
    path('<str:app_label>/<str:model_name>/<str:method>/<str:pks>/<str:action>/', list_view),
    path('<str:app_label>/<str:model_name>/<str:method>/', list_view),
    path('<str:app_label>/<str:model_name>/', list_view),

]
