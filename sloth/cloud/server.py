#!/usr/bin/env python
import os
import json
import urllib.parse
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 9999
WORKDIR = '/opt/cloud/'
DOMAIN_NAME = 'cloud.aplicativo.click'

if os.path.exists('/Users/breno/'):
    WORKDIR = '/Users/breno/cloud/'
    DOMAIN_NAME = 'local.aplicativo.click'

def execute(cmd):
    print(cmd)
    os.system(cmd)

def start():
    conf = 'server {server_name deploy.%s; location / { proxy_pass http://127.0.0.1:%s; }}' % (DOMAIN_NAME, PORT)
    execute("echo '{}' > /etc/nginx/conf.d/deploy.conf".format(conf))
    execute('nginx -s reload')

def stop():
    execute("rm -f /etc/nginx/conf.d/deploy.conf")
    execute('nginx -s reload')


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self._data = {}
        super().__init__(*args, **kwargs)

    def deploy(self):
        if os.path.exists(self._get_project_dir()):
            execute('git pull origin main')
        else:
            execute('git clone {} {}'.format(self.get_project_git_url(), self._get_project_dir()))
        execute('docker-compose -f {} up --build --detach'.format(self._get_file_path()))
        execute("echo '{}' > /etc/nginx/conf.d/{}.conf".format(self._get_nginx_project_conf(), self._get_project_name()))
        execute('nginx -s reload')
        return self.get_project_deploy_url()

    def undeploy(self):
        execute('docker exec nginx sh -c "rm /etc/nginx/conf.d/{}.conf"'.format(self._get_project_name()))
        execute('docker exec nginx nginx -s reload')
        execute('docker-compose -f {} down'.format(self._get_file_path()))
        return 'OK'

    def destroy(self):
        self.undeploy()
        execute('rm -rf {}'.format(self._get_project_dir()))
        return 'OK'

    def update(self):
        execute('cd {} && git pull origin main'.format(self._get_project_dir()))
        execute('docker restart {}'.format(self._get_container_name()))
        return 'OK'

    def _get_user(self):
        return self._data.get('user')

    def _get_project_name(self):
        return self._data.get('project_name')

    def _get_project_dir(self):
        return os.path.join(WORKDIR, self._get_project_name())

    def _get_container_name(self):
        return '{}-web-1'.format(self._data.get('project_name'))

    def _get_container_port(self):
        cmd = 'docker ps -a --no-trunc --filter name=^/%s$ --format "{{.Ports}}"' % self._get_container_name()
        return os.popen(cmd).read().split('->')[0].split(':')[-1].split('/')[0]

    def _get_file_path(self):
        return os.path.join(WORKDIR, self._get_project_name(), 'docker-compose.yml')

    def _get_nginx_project_conf(self):
        return 'server {server_name %s.%s; location / { proxy_pass http://127.0.0.1:%s; }}' % (
            self._get_project_name(), DOMAIN_NAME, self._get_container_port()
        )

    def get_project_deploy_url(self):
        return 'http://{}.{}/'.format(self._get_project_name(), DOMAIN_NAME)

    def get_project_git_url(self):
        return 'https://github.com/{}/{}.git'.format(self._get_user(), self._get_project_name())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        data = urllib.parse.parse_qs(self.path[2:])
        self.wfile.write('{}'.format(data).encode())

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length'))).decode())
        print(data)
        self._data.update(data)
        if data.get('action') == 'deploy':
            message = self.deploy()
        elif data.get('action') == 'update':
            message = self.update()
        elif data.get('action') == 'undeploy':
            message = self.undeploy()
        elif data.get('action') == 'destroy':
            message = self.destroy()
        else:
            message = 'unknown action'
        output = json.dumps(dict(message=message))
        print(output)
        with open(os.path.join(WORKDIR, 'server.log'), 'a') as file:
            file.write('<<< {}\n\n'.format(data))
            file.write('>>> {}\n\n'.format(output))
        self.wfile.write('{}'.format(output).encode())

signal.signal(signal.SIGTERM, stop)
httpd = HTTPServer(('127.0.0.1', PORT), SimpleHTTPRequestHandler)
try:
    start()
    print('Listening 127.0.0.1:{} ...'.format(PORT))
    httpd.serve_forever()
except KeyboardInterrupt:
    stop()
    print('Stopped!')



# curl -X POST http://localhost:9999 -d '{"action": "deploy", "project_name": "a1"}'
# curl -X POST http://localhost:9999 -d '{"action": "undeploy", "project_name": "a1"}'
