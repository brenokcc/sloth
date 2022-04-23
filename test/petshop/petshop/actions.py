from sloth import actions
from .models import Tratamento

class IniciarTratamento(actions.Action):

    class Meta:
        model = Tratamento
        fields = 'doenca', 'data_inicio'
        parent = 'animal'
        verbose_name = 'Iniciar Tratamento'
        has_permission = 'Funcionário',
