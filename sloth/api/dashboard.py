from sloth.app.dashboard import Dashboard
from .models import *
from .actions import ChangePassword, Activate2FAuthentication, Deactivate2FAuthentication


class ApiDashboard(Dashboard):

    def load(self, request):
        self.settings(ChangePassword, Activate2FAuthentication, Deactivate2FAuthentication)
