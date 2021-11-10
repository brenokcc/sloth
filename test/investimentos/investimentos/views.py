from django.shortcuts import render
from django.conf import settings
from .models import Demanda, Ciclo


def index(request):
    qs = None
    valores = {}
    if request.user.roles.filter(name='Gestor').exists():
        qs = Demanda.objects.all().contextualize(request)
        if qs.exists():
            demanda = qs.first()
            valores['maximo'] = demanda.ciclo.teto
            valores['utilizado'] = sum([demanda.valor for demanda in qs if demanda.valor])
            valores['disponivel'] = valores['maximo'] - valores['utilizado']
    elif request.user.roles.filter(name='Administrador').exists():
        qs = Ciclo.objects.all().global_actions('add').contextualize(request)
    return render(request, 'index.html', dict(qs=qs, settings=settings, valores=valores))

