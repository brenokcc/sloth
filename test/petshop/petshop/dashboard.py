from sloth.app.dashboard import Dashboard
from .models import Animal, Cliente, Doenca, Tratamento

class PetshopDashboard(Dashboard):

    def load(self, request):
        self.shortcuts(Animal, Cliente, Tratamento)
        self.cards(Animal, Cliente)
        self.navigation(Animal, Cliente)
        self.floating(Animal, Cliente)
        self.settings(Animal, Cliente)
        self.append(Animal.objects.all().ignore('foto').accordion())
        self.append(Doenca.objects.contagiosas())
        self.append(Doenca.objects.get_total_por_contagiosiade(), aside=True)
        self.append(Animal.objects.get_qtd_por_tipo().verbose_name('Animais por Tipo').bar_chart(), aside=True)
