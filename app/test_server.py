import os
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen
from server import Metrics, config, make_server

class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(("127.0.0.1", 0))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_success_and_metrics(self):
        self.server.fault_config = (0, 0)
        with urlopen(self.url + "/work", timeout=2) as response:
            self.assertEqual(response.status, 200)
        with urlopen(self.url + "/metrics", timeout=2) as response:
            self.assertIn(b'lab_requests_total{status="200"}', response.read())

    def test_failure_does_not_break_health(self):
        self.server.fault_config = (1, 0)
        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.url + "/work", timeout=2)
        self.assertEqual(ctx.exception.code, 500)
        ctx.exception.close()
        with urlopen(self.url + "/healthz", timeout=2) as response:
            self.assertEqual(response.status, 200)

    def test_unknown_route(self):
        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.url + "/unknown", timeout=2)
        self.assertEqual(ctx.exception.code, 404)
        ctx.exception.close()

    def test_cumulative_histogram(self):
        m = Metrics()
        m.observe(200, .2)
        m.observe(500, 2)
        self.assertEqual(list(m.buckets.values()), [0, 1, 1, 2])
        self.assertIn('lab_duration_seconds_bucket{le="+Inf"} 2', m.render())

    def test_invalid_fault_settings(self):
        for env in [{"ERROR_RATE": "1.1"}, {"DELAY_MS": "-1"}, {"DELAY_MS": "nan"}]:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError): config()

if __name__ == "__main__": unittest.main()
