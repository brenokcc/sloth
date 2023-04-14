#!/usr/bin/env python
import os
import json
import urllib.parse
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler

if os.path.exists('/Users/breno/'):
    DOMAIN_NAME = 'local.aplicativo.click'
    WORKDIR = '/Users/breno/Documents/Workspace/sloth/test'
else:
    DOMAIN_NAME = 'cloud.aplicativo.click'
    WORKDIR = '/opt/cloud/'

def execute(cmd):
    print(cmd)
    os.system(cmd)

def start_nginx():
    execute('docker network create sloth')
    execute('docker run --name nginx -d --rm -p 80:80 -v $(pwd):/etc/nginx/conf.d --network sloth nginx')

def stop_nginx():
    execute('docker stop nginx')
    execute('docker network rm sloth')


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self._data = {}
        super().__init__(*args, **kwargs)

    def deploy(self):
        execute('docker-compose -f {} up --build --detach'.format(self._get_file_path()))
        execute('docker network connect sloth {}'.format(self._get_container_name()))
        execute("""docker exec nginx sh -c "echo '{}' > /etc/nginx/conf.d/{}.conf";""".format(
            self._get_nginx_conf(), self._get_project_name()
        ))
        execute('docker exec nginx nginx -s reload')
        return 'OK'

    def undeploy(self):
        execute('docker network disconnect sloth {}'.format(self._get_container_name()))
        execute('docker exec nginx sh -c "rm /etc/nginx/conf.d/{}.conf"'.format(self._get_project_name()))
        execute('docker exec nginx nginx -s reload')
        execute('docker-compose -f {} down'.format(self._get_file_path()))
        return 'OK'

    def destroy(self):
        execute('')
        execute('')
        execute('')

    def update(self):
        execute('')
        execute('')
        execute('')

    def _get_project_name(self):
        return self._data.get('project_name')

    def _get_container_name(self):
        return '{}-web-1'.format(self._data.get('project_name'))

    def _get_file_path(self):
        return os.path.join(WORKDIR, self._get_project_name(), 'docker-compose.yml')

    def _get_nginx_conf(self):
        return 'server {server_name %s.%s; location / { proxy_pass http://%s:8000; }}' % (
            self._get_project_name(), DOMAIN_NAME, self._get_container_name()
        )

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
        elif data.get('action') == 'undeploy':
            message = self.undeploy()
        else:
            message = 'unknown action'
        output = json.dumps(dict(message=message))
        print(output)
        with open('server.log', 'a') as file:
            file.write('<<< {}\n\n'.format(data))
            file.write('>>> {}\n\n'.format(output))
        self.wfile.write('{}'.format(output).encode())

signal.signal(signal.SIGTERM, stop_nginx)
httpd = HTTPServer(('0.0.0.0', 9999), SimpleHTTPRequestHandler)
start_nginx()
try:
    httpd.serve_forever()
except:
    stop_nginx()

# curl -X POST http://localhost:9999 -d '{"action": "deploy", "project_name": "a1"}'
# curl -X POST http://localhost:9999 -d '{"action": "undeploy", "project_name": "a1"}'
