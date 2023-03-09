from sloth.app.dashboard import Dashboard
from .models import Animal, Cliente, Doenca, Tratamento
from .actions import ExibirDataHora, FazerAlgumaCoisa, FazerAlgumaCoisa

class PetshopDashboard(Dashboard):

    def load(self, request):
        self.header(title='Petshop', shadow=True)
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.0')
        self.shortcuts(Animal, Cliente, Tratamento)
        self.cards(Animal, Cliente)
        self.navigation(Animal, Cliente)
        self.floating(Animal, Cliente)
        self.settings(Animal, Cliente)

    def _index(self, request):
        self.append(FazerAlgumaCoisa)
        self.append(ExibirDataHora, aside=True)
        self.append(Animal.objects.first().values('get_dados_gerais'))
        self.append(Tratamento.objects.all().batch_actions('ExcluirTratamentos'))
        self.append(Animal.objects.filter(tipo=1).ignore('foto').verbose_name('Cães').accordion().global_actions('FazerAlgumaCoisa2'))
        self.append(Doenca.objects.contagiosas())
        self.append(Doenca.objects.get_total_por_contagiosiade().verbose_name('Doenças por Contagiosidade'), aside=True)
        self.append(Animal.objects.get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart(), aside=True)

    def get_animal_preferido(self):
        return Animal.objects.first().values('nome', 'tipo').image('foto')

    def get_tratamentos(self):
        return Tratamento.objects.all().batch_actions('ExcluirTratamentos')

    def get_caes(self):
        return Animal.objects.filter(tipo=1).ignore('foto').verbose_name('Cães').accordion().global_actions('FazerAlgumaCoisa2')

    def get_estatistica(self):
        return Animal.objects.get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart()

    def get_doencas(self):
        return Doenca.objects.contagiosas()

    def get_mais_informacoes(self):
        return self.values('get_estatistica', 'get_doencas')

    def view(self):
        return self.values('get_animal_preferido', 'get_tratamentos', 'get_mais_informacoes')

    def right(self):
        return self.values('get_caes', 'get_doencas')

    def values(self, *names):
        from sloth.core.base import ValueSet
        return ValueSet(self, names)

    def has_attr_permission(self, user, name):
        attr = getattr(self, 'has_{}_permission'.format(name), None)
        return  attr is None or attr(user)

    def index(self, request):
        self.append(self.view())
        self.append(self.right(), aside=True)