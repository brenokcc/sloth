from sloth import actions
from .models import Cidade


class AdicionarCidade(actions.Action):
    class Meta:
        verbose_name = 'Adicionar Cidade'
        model = Cidade
        related_field = 'estado'


class FazerAlgumaCoisa(actions.Action):
    class Meta:
        verbose_name = 'Fazer Alguma Coisa'

    def submit(self):
        super().submit()