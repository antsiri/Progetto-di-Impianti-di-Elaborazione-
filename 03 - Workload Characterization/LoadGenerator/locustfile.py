"""
 * author Antonio Sirignano
 * created on 02-10-2026-18h-38m
 * github: https://github.com/antsiri
 * copyright 2026

Locust load test definition for the real workload.

Each simulated user requests a static resource chosen from three size
categories (low / mid / high) with weights 50 / 35 / 15.
Run with: ``locust -f locustfile.py --host http://<server>``.
"""

import random

from locust import HttpUser, task, constant_throughput

# Resources available on the web server, grouped by size
LOW_RES = ["/small1.xls", "/small2.dc", "/small3.jpg"]                # < 500 KB
MID_RES = ["/medium1.mp3", "/medium2.pdf", "/medium3.mov"]          # 700 KB -- 5 MB
HIGH_RES = ["/large1.zip", "/large2.mp4", "/large3.jpg"]            # 5 MB -- 10 MB


class WebServerUser(HttpUser):
    """Simulated user that repeatedly downloads weighted random resources."""

    wait_time = constant_throughput(21.6)                           #21.6 requests per second

    @task
    def request_resources(self):
        """Pick a size category (weighted), then a resource in it, and GET it."""
        # Weighted category choice: 50% small, 35% medium, 15% large
        category = random.choices([LOW_RES, MID_RES, HIGH_RES], weights=[50, 35, 15])[0]
        url = random.choice(category)

        #print(f"--> URL GENERATO: '{url}'")

        # name=url groups the Locust statistics by resource
        self.client.get(url, name=url)

