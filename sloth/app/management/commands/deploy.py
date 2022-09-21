import socket
import sys
import os
import pwd
import grp
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from gunicorn.app.wsgiapp import run

NGINX_USER = 'breno' if os.path.exists('/Users/breno') else 'www-data'

NGINX_CONF = '''
server {
 listen              80;
 server_name         %s;
 location /media { alias %s/media;}
 location /static { alias %s/static;}
 location / {proxy_pass http://127.0.0.1:%s;}
}
'''

class Command(BaseCommand):

    def handle(self, *args, **options):
        uid = pwd.getpwnam(NGINX_USER).pw_uid
        gid = grp.getgrnam("nogroup").gr_gid
        for root, dirs, files in os.walk(settings.BASE_DIR,):
            for momo in dirs:
                os.chown(os.path.join(root, momo), uid, gid)
            for momo in files:
                os.chown(os.path.join(root, momo), uid, gid)
        app = os.path.basename(settings.BASE_DIR)
        call_command('migrate')
        call_command('collectstatic', clear=True, verbosity=0, interactive=False)
        s = socket.socket();
        s.bind(('', 0));
        port = s.getsockname()[1]
        s.close()
        if os.path.exists('/etc/nginx'):
            server_name = ' '.join([url.split('//')[-1] for url in settings.CSRF_TRUSTED_ORIGINS])
            nginx_conf = NGINX_CONF % (server_name, settings.BASE_DIR, settings.BASE_DIR, port)
            print(nginx_conf)
            with open('/etc/nginx/conf.d/{}.conf'.format(app), 'w') as nginx_file:
                nginx_file.write(nginx_conf)
            os.system('nginx -s reload')
        address = '0.0.0.0:{}'.format(port)
        cmd = 'gunicorn -b {} {}.wsgi:application -w 1 -t 360 -u {} -p {}/gunicorn.pid --daemon'.format(
            address, app, NGINX_USER, settings.BASE_DIR)
        print(cmd)
        print('http://{}'.format(address))
        sys.argv = cmd.split()
        sys.exit(run())
