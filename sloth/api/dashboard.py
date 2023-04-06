from sloth.app.dashboard import Dashboard
from .models import *
from .actions import ChangePassword, Activate2FAuthentication, Deactivate2FAuthentication


class ApiDashboard(Dashboard):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools('ExecuteQuery', 'ExecuteScript')
