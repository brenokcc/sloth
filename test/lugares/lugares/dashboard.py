from sloth.api.dashboard import Dashboard
from .models import *


class AppDashboard(Dashboard):

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
        self.footer(title='© 2022 Petshop', text='Todos os direitos reservados', version='1.0.0')
        self.links('lugares.pais', 'lugares.estado', 'lugares.cidade', 'lugares.pessoa')

    def view(self):
        return self.value_set()

