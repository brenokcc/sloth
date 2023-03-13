from sloth.app.dashboard import Dashboard


class PetshopDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.header(title='Petshop', shadow=True)
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.0')
        self.shortcuts('animal', 'cliente', 'tratamento')
        self.actions('animal', 'cliente')
        self.links('animal', 'cliente')
        self.cards('animal', 'cliente')
        self.navigation('animal', 'cliente')
        self.floating('animal', 'cliente')
        self.settings('animal', 'cliente')

    def get_animal_preferido(self):
        self.objects('animal').first().values('nome', 'tipo').image('foto')

    def get_tratamentos(self):
        return self.objects('tratamento').all().batch_actions('ExcluirTratamentos')

    def get_caes(self):
        return self.objects('animal').filter(tipo=1).ignore('foto').verbose_name('Cães').accordion().global_actions('FazerAlgumaCoisa2')

    def get_gatos(self):
        return self.objects('animal').filter(tipo=2).ignore('foto').verbose_name('Cães').accordion().global_actions('FazerAlgumaCoisa2')

    def get_estatistica(self):
        return self.objects('animal').get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart()

    def get_doencas(self):
        return self.objects('doenca').contagiosas()

    def get_mais_informacoes(self):
        return self.values('get_estatistica', 'get_doencas')

    def view(self):
        return self.values(
            'get_tratamentos',  # 'get_animal_preferido',
            'get_mais_informacoes', 'get_gatos'
        ).append(
            'get_caes', 'get_doencas'
        ).actions(
            'fazer_alguma_coisa', 'exibir_data_hora', inline=True
        )

