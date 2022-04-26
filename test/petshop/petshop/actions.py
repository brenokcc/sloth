from sloth import actions
from .models import Tratamento, Procedimento

class IniciarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'doenca', 'data_inicio'
        related_field = 'animal'
        has_permission = 'Funcionário',
        refresh = 'get_dados_gerais',

class ExcluirTratamento(actions.Action):

    class Meta:
        style = 'danger'
        confirmation = True
        has_permission = 'Funcionário',
        refresh = 'get_dados_gerais',

    def submit(self):
        self.instance.delete()
        super().submit()


class RegistrarProcedimento(actions.Action):

    class Meta:
        model = Procedimento
        related_field = 'tratamento'
        has_permission = 'Funcionário',
        refresh = 'get_eficacia',

    def has_permission(self, user):
        return self.instantiator.eficaz is None


class FinalizarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'data_fim', 'eficaz',
        has_permission = 'Funcionário',
        style = 'success'
        refresh = 'get_procedimentos',

    def has_permission(self, user):
        return self.instance.procedimento_set.exists() and self.instance.eficaz is None