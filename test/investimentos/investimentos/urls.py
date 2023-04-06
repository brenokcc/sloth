
from django.urls import path, include
from . import views

urlpatterns = [
    path('videos/', views.videos),
    path('', include('sloth.api.urls')),

]
