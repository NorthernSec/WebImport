#!/usr/bin/env python3
"""WebImport-Server.

This library provides a simple http.server for webimport, and made available through
 webimport-server.
It provides access to python libraries from the specified directory, for use by the
 remote device.
It also adds a /_hook endpoint that provides the webimport code, so that it can be
 easily obtained remotely.

Classes:
    CustomHandler: Custom handler for the built-in http.server

Methods:
    run(directory, port): Run the server from within a specified directory, on a
                           specified port.
"""
import inspect
import os
import click

from http.server import HTTPServer, SimpleHTTPRequestHandler
from webimport import webimport

class CustomHandler(SimpleHTTPRequestHandler):
    """Custom handler for the built-in http.server.

    Methods:
        do_GET(): Override the default GET method to add the /_hook endpoint.
    """
    def do_GET(self):
        """Overridden GET method with the addition of the /_hook endpoint."""
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
    """Run the webserver.

    Args:
        directory (str): The directory to server. This should be your package directory.
        port      (int): The port you want to serve on. Default: 8080.
    """
    os.chdir(directory)  # Change to the specified directory
    httpd = HTTPServer(('', port), CustomHandler)
    print('Serving on port %s from directory "%s"...'%(port, directory))
    httpd.serve_forever()

if __name__ == "__main__":
    run()
