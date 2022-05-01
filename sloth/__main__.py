import sys
import os

URLS_FILE_CONTENT = '''from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
    path('', include('sloth.admin.urls')),
]
'''

MODELS_FILE_CONTENT = '''from sloth.db import models
from sloth.decorators import role
'''

ACTIONS_FILE_CONTENT = '''from sloth import actions
'''

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'configure':
            root_dir = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir))
            settings_path = os.path.join(os.path.join(root_dir, 'conf'), 'settings.py')
            with open(settings_path) as file:
                settings = file.read()
            project_dir_name = os.path.basename(os.path.abspath('.'))
            settings_path = os.path.join(project_dir_name, 'settings.py')
            settings = "\nMEDIA_URL = '/media/'{}".format(settings)
            settings = "\nSTATIC_ROOT = os.path.join(BASE_DIR, 'static'){}".format(settings)
            settings = "\nMEDIA_ROOT = os.path.join(BASE_DIR, 'media'){}".format(settings)
            with open(settings_path) as file:
                settings = '{}\n{}'.format(file.read(), settings)
                settings = "import os\n{}".format(settings)
            settings = settings.replace(
                'APPS = [', "APPS = [\n    '{}',\n    'oauth2_provider',\n    'sloth.api',\n    'sloth.admin',".format(
                    project_dir_name
                )
            )
            settings = settings.replace(
                "processors.messages',",
                "processors.messages',\n                'sloth.views.context_processor'"
            )
            settings = settings.replace("\n    'django.contrib.admin',", "")
            with open(settings_path, 'w') as file:
                file.write(settings)
            urls_path = os.path.join(project_dir_name, 'urls.py')
            with open(urls_path, 'w') as file:
                file.write(URLS_FILE_CONTENT)

            models_path = os.path.join(project_dir_name, 'models.py')
            with open(models_path, 'w') as file:
                file.write(MODELS_FILE_CONTENT)

            actions_path = os.path.join(project_dir_name, 'actions.py')
            with open(actions_path, 'w') as file:
                file.write(ACTIONS_FILE_CONTENT)

    else:
        print('Usage: python -m <action>')