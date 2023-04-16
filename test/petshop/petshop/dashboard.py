from sloth import meta
from sloth.api.dashboard import Dashboard


class PetshopDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.styles('/static/css/sloth.css')
        self.scripts('/static/js/sloth.js')
        self.libraries(fontawesome=False, materialicons=False)
        self.web_push_notification(False)
        self.login(logo='/static/images/logo.png', title=None, mask=None, two_factor=False, actions=['signup', 'reset_password'])
        self.navbar(title='Petshop', icon='/static/images/icon.png', favicon='/static/images/icon.png')
        self.header(title='Petshop', shadow=True)
        self.settings_menu('change_password')
        self.tools_menu('show_icons')
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.7')

        self.shortcuts('petshop.animal', 'petshop.cliente', 'petshop.tratamento')
        self.action_bar('petshop.animal', 'petshop.cliente', 'teste')
        self.top_menu('petshop.animal', 'petshop.cliente', 'fazer_alguma_coisa_2', 'exibir_data_hora')
        self.top_menu('fazer_alguma_coisa', modal=True)
        self.cards('petshop.animal', 'petshop.cliente', 'petshop.doenca.contagiosas')
        self.navigation('petshop.animal', 'petshop.cliente')
        self.floating('petshop.animal', 'petshop.cliente')
        self.settings_menu('petshop.animal', 'petshop.cliente')

    def get_animal_preferido(self):
        animal = self.objects('petshop.animal').first()
        return animal.value_set('nome', 'tipo').image('foto') if animal else None

    def get_tratamentos(self):
        return self.objects('petshop.tratamento').all().batch_actions('ExcluirTratamentos')

    def get_caes(self):
        return self.objects('petshop.animal').filter(tipo=1).ignore('foto').verbose_name('Cães').accordion().global_actions('fazer_alguma_coisa_2')

    def get_gatos(self):
        return self.objects('petshop.animal').filter(tipo=2).ignore('foto').verbose_name('Cães').accordion().global_actions('fazer_alguma_coisa_2')

    def get_estatistica(self):
        return self.objects('petshop.animal').get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart()

    def get_doencas(self):
        return self.objects('petshop.doenca').contagiosas().expand()

    def get_mais_informacoes(self):
        return self.value_set('get_estatistica', 'get_doencas')

    def view(self):
        return self.value_set(
            'get_tratamentos', 'get_animal_preferido',
            'get_mais_informacoes', 'get_gatos', 'get_estatisticas_basicas'
        ).append(
            'get_caes', 'get_doencas'
        ).actions(
            'fazer_alguma_coisa_2', 'exibir_data_hora'
        ).inline_actions('exibir_permissoes')

    def get_total_animais_por_tipo(self):
        return self.objects('petshop.animal').get_qtd_por_tipo()

    def get_total_doencas_por_contagiosidade(self):
        return self.objects('petshop.doenca').get_total_por_contagiosiade()

    @meta('Estatísticas Básicas')
    def get_estatisticas_basicas(self):
        return self.value_set('get_total_animais_por_tipo', 'get_total_doencas_por_contagiosidade').split()

