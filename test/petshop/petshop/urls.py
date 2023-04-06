from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
]
