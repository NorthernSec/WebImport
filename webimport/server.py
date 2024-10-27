import inspect
import os
import click

from http.server import HTTPServer, SimpleHTTPRequestHandler
import webimport.webimport

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/_hook':
            self.send_response(200)
            code = inspect.getsource(webimport)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(code.encode())
        else:
            super().do_GET()


@click.command()
@click.argument('directory',  required=True)
@click.option('-p', '--port', type=int, default=8080)
def run(directory, port):
    os.chdir(directory)  # Change to the specified directory
    httpd = HTTPServer(('', port), CustomHandler)
    print('Serving on port %s from directory "%s"...'%(port, directory))
    httpd.serve_forever()

if __name__ == "__main__":
    run()
