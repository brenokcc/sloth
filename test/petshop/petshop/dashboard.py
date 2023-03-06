from sloth.app.dashboard import Dashboard
from .models import Animal, Cliente, Doenca, Tratamento
from .actions import ExibirDataHora, FazerAlgumaCoisa

class PetshopDashboard(Dashboard):

    def load(self, request):
        self.header(title='Petshop', shadow=True)
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.0')
        self.shortcuts(Animal, Cliente, Tratamento)
        self.cards(Animal, Cliente)
        self.navigation(Animal, Cliente)
        self.floating(Animal, Cliente)
        self.settings(Animal, Cliente)

    def index(self, request):
        self.append(FazerAlgumaCoisa)
        self.append(ExibirDataHora, aside=True)
        self.append(Animal.objects.all().ignore('foto').accordion())
        self.append(Doenca.objects.contagiosas())
        self.append(Doenca.objects.get_total_por_contagiosiade().verbose_name('Doenças por Contagiosidade'), aside=True)
        self.append(Animal.objects.get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart(), aside=True)