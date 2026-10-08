"""
 * author Antonio Sirignano
 * created on 07-10-2026-18h-11m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import os
import shutil
import threading

from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

from doe.Server.custom_handler import CustomHandler

class ServerManager:

    def __init__(self, host='127.0.0.1', port=8080, web_dir='./www_root'):
        self.host = host
        self.port = port
        self.web_dir = web_dir
        self.server = None
        self.thread = None

        self.page_sizes = {
            'Low': 20 * 1024,
            'Mid-Low': 184 * 1024,
            'Mid': 716 * 1024,
            'Mid-High': int(2.13 * 1024 * 1024),
            'High': int(5.07 * 1024 * 1024),
        }


    def setup_environment(self):
        if os.path.exists(self.web_dir):
            shutil.rmtree(self.web_dir)
        os.makedirs(self.web_dir)

        for label, size_bytes in self.page_sizes.items():
            file_path = os.path.join(self.web_dir, f'{label}.html')
            with open(file_path, 'wb') as f:
                f.write(b'0' * size_bytes)
        print(f'[ServerManager] Files created in {self.web_dir}.')

    def start_server(self):
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
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print('[ServerManager] Server stopped.')

            