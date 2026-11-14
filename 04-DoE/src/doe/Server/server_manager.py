"""
 * author Antonio Sirignano
 * created on 07-10-2026-18h-11m
 * github: https://github.com/antsiri
 * copyright 2026

Management of the local HTTP server used as system under test.
"""

import os
import shutil
import threading

from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

from doe.Server.custom_handler import CustomHandler


class ServerManager:
    """
    Creates the test pages and runs a static HTTP server in a background thread.

    Attributes:
        host (str): listening address.
        port (int): listening port.
        web_dir (str): document root.
        server (HTTPServer | None): running server instance.
        thread (threading.Thread | None): thread executing ``serve_forever``.
        page_sizes (dict[str, int]): size in bytes of each test page.
    """

    def __init__(self, host='127.0.0.1', port=8080, web_dir='./www_root'):
        """
        Args:
            host (str): listening address.
            port (int): listening port.
            web_dir (str): folder that will contain the test pages.
        """
        self.host = host
        self.port = port
        self.web_dir = web_dir
        self.server = None
        self.thread = None

        # Size of each PageType level (factor levels of the DoE)
        self.page_sizes = {
            'Low': 20 * 1024,
            'Mid-Low': 184 * 1024,
            'Mid': 716 * 1024,
            'Mid-High': int(2.13 * 1024 * 1024),
            'High': int(5.07 * 1024 * 1024),
        }


    def setup_environment(self):
        """
        Recreate ``web_dir`` from scratch and write one ``<label>.html`` file
        of the configured size for each page type.
        """
        # Start from an empty document root
        if os.path.exists(self.web_dir):
            shutil.rmtree(self.web_dir)
        os.makedirs(self.web_dir)

        for label, size_bytes in self.page_sizes.items():
            file_path = os.path.join(self.web_dir, f'{label}.html')
            with open(file_path, 'wb') as f:
                f.write(b'0' * size_bytes)
        print(f'[ServerManager] Files created in {self.web_dir}.')

    def start_server(self):
        """Start the HTTP server in a daemon thread (non-blocking)."""
        # partial() binds the document root to the handler class
        handler = partial(SimpleHTTPRequestHandler, directory=self.web_dir)

        self.server = HTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        print(
            f'[ServerManager] Server active on http://{self.host}:{self.port} ...'
        )

    def stop_server(self):
        """Stop the server loop and release the listening socket."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print('[ServerManager] Server stopped.')
