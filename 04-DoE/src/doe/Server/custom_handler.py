"""
 * author Antonio Sirignano
 * created on 07-10-2026-18h-29m
 * github: https://github.com/antsiri
 * copyright 2026

Custom static-file HTTP request handler.
"""

from http.server import SimpleHTTPRequestHandler


class CustomHandler(SimpleHTTPRequestHandler):
    """
    ``SimpleHTTPRequestHandler`` that serves files from ``./www_root`` and
    does not log requests (console logging would slow down the I/O).
    """

    def __init__(*args, **kwargs):
        """Initialise the handler with ``./www_root`` as document root."""
        super().__init__(*args, directory='./www_root', **kwargs)

    def log_message(self, format, *args):
        """Override: suppress the per-request log line."""
        pass                        #Diabled for not slow down the I/O
