"""Threaded lab HTTP service with bounded, environment-controlled fault injection."""
import json
import math
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {"200": 0, "500": 0}
        self.buckets = {0.1: 0, 0.3: 0, 1.0: 0, 5.0: 0}
        self.total = 0
        self.duration = 0.0

    def observe(self, status, elapsed):
        with self.lock:
            self.counts[str(status)] += 1
            self.total += 1
            self.duration += elapsed
            for boundary in self.buckets:
                if elapsed <= boundary:
                    self.buckets[boundary] += 1

    def render(self):
        with self.lock:
            lines = ["# TYPE lab_requests_total counter"]
            lines += [f'lab_requests_total{{status="{s}"}} {n}' for s, n in self.counts.items()]
            lines += ["# TYPE lab_duration_seconds histogram"]
            lines += [f'lab_duration_seconds_bucket{{le="{b}"}} {n}' for b, n in self.buckets.items()]
            lines += [f'lab_duration_seconds_bucket{{le="+Inf"}} {self.total}',
                      f'lab_duration_seconds_sum {self.duration}',
                      f'lab_duration_seconds_count {self.total}']
            return "\n".join(lines) + "\n"

metrics = Metrics()

def config():
    rate = float(os.getenv("ERROR_RATE", "0"))
    delay = float(os.getenv("DELAY_MS", "0"))
    if not math.isfinite(rate) or not math.isfinite(delay) or not 0 <= rate <= 1 or not 0 <= delay <= 5000:
        raise ValueError("ERROR_RATE must be 0..1 and DELAY_MS 0..5000")
    return rate, delay

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/metrics":
            self.respond(200, metrics.render().encode(), "text/plain; version=0.0.4")
        elif path == "/healthz":
            self.respond(200, b'{"status":"ok"}')
        elif path == "/work":
            start = time.monotonic()
            rate, delay = self.server.fault_config
            time.sleep(delay / 1000)
            status = 500 if random.random() < rate else 200
            elapsed = time.monotonic() - start
            metrics.observe(status, elapsed)
            self.respond(status, json.dumps({"status": status, "duration_seconds": elapsed}).encode())
        else:
            self.respond(404, b'{"error":"not found"}')

    def respond(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(json.dumps({"request": fmt % args}), flush=True)

def make_server(address=("0.0.0.0", 8080)):
    server = ThreadingHTTPServer(address, Handler)
    server.fault_config = config()
    return server

if __name__ == "__main__":
    make_server().serve_forever()
