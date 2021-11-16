
from django.urls import path, include

urlpatterns = [
    # path('adm/', index),
    path('', include('sloth.api.urls')),
    path('', include('sloth.admin.urls')),
]
