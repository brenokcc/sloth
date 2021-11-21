# -*- coding: utf-8 -*-
from decimal import Decimal
from .models import Ciclo, Demanda, Pergunta
from sloth.admin.gadgets import Cards, Gadget


class Instrucoes(Gadget):

    def render(self):
        return super().render(
            is_gestor=self.request.user.roles.filter(name='Gestor').exists()
        )


class Cartoes(Cards):
    pass


class CiclosAbertos(Gadget):
    class Meta:
        can_view = 'Gestor',

    def render(self):
        ciclos = []
        for ciclo in Ciclo.objects.abertos():
            demandas = ciclo.demanda_set.all().contextualize(self.request)
            utilizado = Decimal(sum([demanda.valor for demanda in demandas if demanda.valor]))
            ciclos.append(
                dict(
                    id=ciclo.id, descricao=ciclo.descricao, maximo=ciclo.teto,
                    utilizado=utilizado, disponivel=ciclo.teto - utilizado,
                    inicio=ciclo.inicio, fim=ciclo.fim, limites=ciclo.limites.all()
                )
            )
        return super().render(ciclos=ciclos)


class DemandasPorInstituicao(Gadget):

    def render(self):
        return Demanda.objects.contextualize(self.request).count('instituicao').chart('bar')


class DemandasPorInstituicaoClassificacao(Gadget):

    def render(self):
        return Pergunta.objects.contextualize(self.request).count('categoria', 'tipo_resposta').chart('column')

