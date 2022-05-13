from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
    path('', include('sloth.app.urls')),
]
