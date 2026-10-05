"""
 * author Antonio Sirignano
 * created on 02-10-2026-18h-38m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import random

from locust import HttpUser, task, constant_throughput

LOW_RES = ["/small1.xls", "/small2.dc", "/small3.jpg"]                # < 500 KB
MID_RES = ["/medium1.mp3", "/medium2.pdf", "/medium3.mov"]          # 700 KB -- 5 MB
HIGH_RES = ["/large1.zip", "/large2.mp4", "/large3.jpg"]            # 5 MB -- 10 MB

class WebServerUser(HttpUser):
    wait_time = constant_throughput(21.6)                           #21.6 requests per second

    @task
    def request_resources(self):
        category = random.choices([LOW_RES, MID_RES, HIGH_RES], weights=[50, 35, 15])[0]
        url = random.choice(category)

        #print(f"--> URL GENERATO: '{url}'")

        self.client.get(url, name=url)

