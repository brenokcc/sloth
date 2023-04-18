from weasyprint import HTML
import os, tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler

# curl -X POST http://localhost:8888 -d '<html><body><h1>:)</h1></body></html>' -o out.pdf


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200), self.end_headers()
        html = self.rfile.read(int(self.headers.get('Content-Length'))).decode()
        tmp = tempfile.NamedTemporaryFile(mode='w+b')
        HTML(string=html).write_pdf(tmp.name)
        print(html)
        self.wfile.write(tmp.read())

try:
    HTTPServer(('0.0.0.0', 8888), SimpleHTTPRequestHandler).serve_forever()
except KeyboardInterrupt:
    pass
