from sloth import meta
from sloth.app.dashboard import Dashboard
from .models import *


class AppDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.header(logo='/static/images/logo.png', title='COLETA SETEC', text=None, shadow=True)
        self.footer(title='© 2023 MEC', text='Todos os direitos reservados', version='1.0.0')
        self.links('investimentos.anexo', 'investimentos.categoria', 'investimentos.instituicao', 'investimentos.gestor', 'investimentos.ciclo')

    def view(self):
        return self.value_set('get_anexos', 'get_minhas_solicitacoes')

    def get_anexos(self):
        return self.objects('investimentos.anexo').all()

    def has_get_minhas_solicitacoes_permission(self, user):
        return user.roles.contains('Gestor')

    @meta('Histórico de Solicitações')
    def get_minhas_solicitacoes(self):
        return self.objects('investimentos.solicitacao').all().ignore('instituicao').actions('view')

