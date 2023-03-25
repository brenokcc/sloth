from sloth.app.dashboard import Dashboard
from .models import *


class AppDashboard(Dashboard):

    def __init__(self, request):
        super().__init__(request)
        self.header(logo='/static/images/logo.png', title=None, text='Take your time!', shadow=False)
        self.footer(title='© 2022 Sloth', text='Todos os direitos reservados', version='1.0.0')
        self.links('lugares.pais', 'lugares.estado', 'lugares.cidade', 'lugares.pessoa')

    def view(self):
        return self.values()

