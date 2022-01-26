# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render
from .models import Ciclo, Mensagem, Gestor, Notificacao
from sloth.admin.gadgets import Cards, Gadget


class Instrucoes(Gadget):

    def __init__(self, request):
        super().__init__(request)
        self.mensagem = None
        if request.user.roles.filter(name='Gestor').exists():
            self.gestor = Gestor.objects.filter(user=request.user).first()
            self.mensagem = Mensagem.objects.filter(perfil='Gestor').exclude(notificados=request.user).first()
        else:
            self.mensagem = Mensagem.objects.filter(perfil='Administrador').exclude(notificados=request.user).first()
        self.notificacoes = Notificacao.objects.filter(
            inicio__gte=date.today()
        ).exclude(fim__lt=date.today())
        if self.mensagem and 'ocultar' in request.GET:
            self.mensagem.notificados.add(request.user)
            self.mensagem = None


class Cartoes(Cards):
    pass


class CiclosAbertos(Gadget):
    class Meta:
        can_view = 'Gestor',

    def __init__(self, request):
        super().__init__(request)
        self.ciclos = []
        gestor = Gestor.objects.filter(user=request.user).first()
        instituicao = gestor and gestor.instituicao or None
        for ciclo in Ciclo.objects.abertos().filter(instituicoes=instituicao):
            demandas = ciclo.demanda_set.exclude(classificacao__contabilizar=False).all().contextualize(request)
            utilizado = Decimal(sum([demanda.valor for demanda in demandas if demanda.valor]))
            self.ciclos.append(
                dict(
                    id=ciclo.id, descricao=ciclo.descricao, maximo=ciclo.teto,
                    utilizado=utilizado, disponivel=ciclo.teto - utilizado,
                    inicio=ciclo.inicio, fim=ciclo.fim, limites=ciclo.limites.all(),
                    obs=ciclo.limites.filter(classificacao__contabilizar=False).exists()
                )
            )


def videos(request):
    return render(request, ['videos.html'], dict(settings=settings))
