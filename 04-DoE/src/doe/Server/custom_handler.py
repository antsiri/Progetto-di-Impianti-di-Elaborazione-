"""
 * author Antonio Sirignano
 * created on 07-10-2026-18h-29m
 * github: https://github.com/antsiri
 * copyright 2026
"""

from http.server import SimpleHTTPRequestHandler

class CustomHandler(SimpleHTTPRequestHandler):
    def __init__(*args, **kwargs):
        super().__init__(*args, directory='./www_root', **kwargs)

    def log_message(self, format, *args):
        pass                        #Diabled for not slow down the I/O