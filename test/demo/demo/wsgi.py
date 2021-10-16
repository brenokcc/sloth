import os
import sys

from django.core.wsgi import get_wsgi_application

sys.path.append('/Users/breno/Documents/Workspace/dms2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
__import__('dms2')

application = get_wsgi_application()
