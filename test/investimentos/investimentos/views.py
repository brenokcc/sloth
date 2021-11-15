# -*- coding: utf-8 -*-
from .models import Demanda, Ciclo
from sloth.gadgets import Cards, Gadget


class Cartoes(Cards):
    class Meta:
        width = 50


class Ciclos(Gadget):

    class Meta:
        can_view = 'Administrador',

    def render(self):
        return Ciclo.objects.all().global_actions('add').contextualize(self.request)


class Totalizadores(Gadget):
    class Meta:
        width = 50
        can_view = 'Gestor',

    def __init__(self, request):
        super().__init__(request)
        qs = Demanda.objects.all().contextualize(request)
        if qs.exists():
            self.maximo = qs.first().ciclo.teto
            self.utilizado = sum([demanda.valor for demanda in qs if demanda.valor])
            self.disponivel = self.maximo - self.utilizado


class Demandas(Gadget):
    class Meta:
        can_view = 'Gestor',

    def render(self):
        return Demanda.objects.all().contextualize(self.request)


class DemandasPorInstituicao(Gadget):
    class Meta:
        width = 50

    def render(self):
        return Demanda.objects.contextualize(self.request).count('instituicao').chart('pie')


class DemandasPorInstituicaoClassificacao(Gadget):
    class Meta:
        width = 50

    def render(self):
        return Demanda.objects.contextualize(self.request).count('instituicao', 'classificacao').chart('column')


class ValorDemandadoPorInstituicao(Gadget):
    class Meta:
        width = 100

    def render(self):
        return Demanda.objects.contextualize(self.request).get_total_por_instituicao().chart('bar')
