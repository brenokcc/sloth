from django.shortcuts import render
from django.conf import settings
from .models import Demanda, Ciclo


def index(request):
    qs = None
    if request.user.roles.filter(name='Gestor').exists():
        qs = Demanda.objects.all().contextualize(request)
    elif request.user.roles.filter(name='Administrador').exists():
        qs = Ciclo.objects.all().global_actions('add').contextualize(request)
    return render(request, 'index.html', dict(qs=qs, settings=settings))

