from sloth import actions
from .models import Loja

class AdicionarLoja(actions.Action):

    class Meta:
        model = Loja
        verbose_name = 'Adicionar Loja'
        parent = 'rede'

