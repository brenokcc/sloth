from sloth.admin.dashboard import Dashboard
from .models import Animal, Cliente

class PetshopDashboard(Dashboard):

    def load(self, request):
        self.cards(Animal, Cliente)
        self.append(Animal.objects.all())