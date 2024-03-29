from sloth import meta
from datetime import date
from sloth.api.dashboard import Dashboard
from .models import *


class AppDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.styles('/static/css/sloth.css', '/static/css/coletasetec.css')
        self.scripts('/static/js/sloth.js', '/static/js/coletasetec.js')
        self.libraries(fontawesome=False, materialicons=False)
        self.web_push_notification(False)
        self.login(title='COLETA SETEC', mask=None, two_factor=False)
        self.navbar(title='COLETA SETEC', icon=None, favicon='/static/images/favicon.png')
        self.header(title='COLETA SETEC', shadow=True)
        self.settings_menu('change_password')
        self.tools_menu('show_icons')
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.7')

        self.footer(title='© 2023 MEC', text='Todos os direitos reservados', version='1.0.0')
        self.top_menu('investimentos.mensagem', 'investimentos.anexo', 'investimentos.categoria', 'investimentos.instituicao', 'investimentos.gestor', 'investimentos.ciclo')
        if self.request.user.roles.contains('Administrador'):
            self.top_menu('investimentos.duvida', 'investimentos.notificacao')
        self.add_action('/media/tutorial/tutorial.pdf', 'Tutorial', 'book-half')

    def view(self):
        return self.value_set('get_notificacoes', 'get_mensagem', 'get_anexos', 'get_minhas_solicitacoes', 'get_duvidas_nao_respondidas', 'get_duvidas')

    def get_anexos(self):
        return self.objects('investimentos.anexo').all()

    def has_get_minhas_solicitacoes_permission(self, user):
        return user.roles.contains('Gestor')

    @meta('Ciclos de Demandas')
    def get_minhas_solicitacoes(self):
        return self.objects('investimentos.solicitacao').all().display('get_periodo', 'get_limite_orcamentario', 'get_limite_demandas', 'is_finalizada').actions('view').timeline()

    def has_get_duvidas_permission(self, user):
        return user.roles.contains('Gestor')

    @meta('Dúvidas')
    def get_duvidas(self):
        return self.objects('investimentos.duvida').all().ignore('instituicao').actions('view')

    def has_get_duvidas_nao_respondidas_permission(self, user):
        return user.roles.contains('Administrador')

    @meta('Dúvidas Não Respondidas')
    def get_duvidas_nao_respondidas(self):
        return self.objects('investimentos.duvida').all().nao_respondidas().calendar('data_pergunta')

    @meta(renderer='mensagem')
    def get_mensagem(self):
        qs = self.objects('investimentos.mensagem').all()
        if self.request.user.roles.contains('Administrador'):
            qs = qs.filter(perfil='Administrador')
        else:
            qs = qs.filter(perfil='Gestor')
        return qs.first()

    @meta(renderer='notificacoes')
    def get_notificacoes(self):
        return list(self.objects('investimentos.notificacao').ativas().values_list('descricao', flat=True))
