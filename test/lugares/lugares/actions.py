from sloth import actions
from .models import Cidade
from . import tasks


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

class Contar(actions.ActionView):
    class Meta:
        verbose_name = 'Contar'
        modal = False
        style = 'primary'

    def view(self):
        return self.run(tasks.Contar())
