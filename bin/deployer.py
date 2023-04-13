#!/usr/bin/env python
import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        data = urllib.parse.parse_qs(self.path[2:])
        self.wfile.write('{}'.format(data).encode())
    def do_POST(self):
        output = ''
        self.send_response(200)
        self.end_headers()
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length'))).decode())
        print(data)
        output = os.popen('echo {}'.format(data)).read()
        print(output)
        with open('server.log', 'a') as file:
            file.write('{}\n\n'.format(output))
        self.wfile.write('{}'.format(output).encode())

httpd = HTTPServer(('127.0.0.1', 9999), SimpleHTTPRequestHandler)
httpd.serve_forever()
