import sys
import os
from sloth.conf import settings

URLS_FILE_CONTENT = '''from django.urls import path, include

urlpatterns = [
    path('', include('sloth.api.urls')),
    path('', include('sloth.app.urls')),
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
            name = os.path.basename(os.path.abspath('.'))
            settings_path = os.path.join(name, 'settings.py')
            settings_content = open(settings_path).read().replace(
                "'django.contrib.admin'",
                "'{}', 'oauth2_provider', 'sloth.api', 'sloth.app'".format(name)
            ).replace(
                "'django.template.context_processors.debug'",
                "'django.template.context_processors.debug', 'sloth.core.views.context_processor'"
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
    else:
        print('Usage: python -m <action>')