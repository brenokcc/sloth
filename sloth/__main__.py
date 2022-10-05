import sys
import os
from sloth.conf import settings


URLS_FILE_CONTENT = '''from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
    path('', include('sloth.app.urls')),
]
'''

MODELS_FILE_CONTENT = '''from sloth.db import models, role, meta
'''

ACTIONS_FILE_CONTENT = '''from sloth import actions
'''

DASHBOARD_FILE_CONTENT = '''from sloth.app.dashboard import Dashboard
from .models import *

class AppDashboard(Dashboard):
    
    def load(self, request):
        self.header(logo='/static/images/logo.png', title=None, text='Take your time!', shadow=False)
        self.footer(title='© 2022 Sloth', text='Todos os direitos reservados', version='1.0.0')

'''

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'configure':
            name = os.path.basename(os.path.abspath('.'))
            settings_path = os.path.join(name, 'settings.py')
            settings_content = open(settings_path).read().replace(
                "'django.contrib.admin'",
                "'{}', 'oauth2_provider', 'sloth.api', 'sloth.app'".format(name)
            )
            settings_append = open(settings.__file__).read().replace('# ', '')
            with open(settings_path, 'w') as file:
                file.write('{}{}'.format(settings_content, settings_append))
            urls_path = os.path.join(name, 'urls.py')
            with open(urls_path, 'w') as file:
                file.write(URLS_FILE_CONTENT)
            models_path = os.path.join(name, 'models.py')
            with open(models_path, 'w') as file:
                file.write(MODELS_FILE_CONTENT)
            actions_path = os.path.join(name, 'actions.py')
            with open(actions_path, 'w') as file:
                file.write(ACTIONS_FILE_CONTENT)
            dashboard_path = os.path.join(name, 'dashboard.py')
            with open(dashboard_path, 'w') as file:
                file.write(DASHBOARD_FILE_CONTENT)
            os.system('python manage.py sync')
    else:
        print('Usage: python -m <action>')
