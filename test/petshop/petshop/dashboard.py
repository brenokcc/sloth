from sloth.admin.dashboard import Dashboard
from .models import Animal, Cliente

class PetshopDashboard(Dashboard):

    def load(self, request):
        self.shortcuts(Animal, Cliente)
        self.cards(Animal, Cliente)
        self.navigation(Animal, Cliente)
        self.floating(Animal, Cliente)
        self.settings(Animal, Cliente)
        self.append(Animal.objects.all())