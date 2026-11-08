"""Exercise the real Compose stack through HTTP, Prometheus, and Grafana."""
import base64
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

out = Path("evidence"); out.mkdir(exist_ok=True)
results = []
stop = threading.Event()

def get(url, auth=False):
    headers = {}
    if auth: headers["Authorization"] = "Basic " + base64.b64encode(b"admin:admin").decode()
    with urlopen(Request(url, headers=headers), timeout=8) as response:
        return json.loads(response.read())

def wait(label, predicate, timeout=120):
    start = time.monotonic()
    error = None
    while time.monotonic() - start < timeout:
        try:
            value = predicate()
            if value:
                results.append({"check": label, "elapsed_seconds": round(time.monotonic()-start, 2), "observed": value})
                return value
        except (HTTPError, URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e: error = str(e)
        time.sleep(2)
    raise AssertionError(f"{label} timed out: {error}")

def query(expr):
    data = get("http://127.0.0.1:9090/api/v1/query?" + urlencode({"query": expr}))
    assert data["status"] == "success", data
    return data["data"]["result"]

def traffic():
    while not stop.is_set():
        try:
            with urlopen("http://127.0.0.1:8080/work", timeout=8) as response: response.read()
        except (HTTPError, URLError, TimeoutError, ConnectionError): pass
        stop.wait(.03)

def fault(rate, delay):
    env = dict(os.environ, ERROR_RATE=str(rate), DELAY_MS=str(delay))
    subprocess.run(["docker", "compose", "up", "-d", "--force-recreate", "app"], env=env, check=True)
    wait("app process healthy", lambda: get("http://127.0.0.1:8080/healthz")["status"] == "ok")

try:
    wait("Prometheus ready", lambda: get("http://127.0.0.1:9090/api/v1/status/buildinfo")["status"] == "success")
    wait("Grafana healthy", lambda: get("http://127.0.0.1:3000/api/health")["database"] == "ok")
    dashboard = wait("provisioned Grafana dashboard", lambda: get("http://127.0.0.1:3000/api/dashboards/uid/platform-lab", True))
    assert len(dashboard["dashboard"]["panels"]) == 3
    (out/"grafana-dashboard.json").write_text(json.dumps(dashboard, indent=2))
    thread = threading.Thread(target=traffic, daemon=True); thread.start()
    wait("Prometheus scrapes real API", lambda: any(float(x["value"][1]) == 1 for x in query('up{job="platform-api"}')))
    wait("healthy request rate", lambda: any(float(x["value"][1]) > 1 for x in query('sum(rate(lab_requests_total{status="200"}[30s]))')))
    fault(1, 0)
    wait("all user requests fail", lambda: get("http://127.0.0.1:8080/healthz")["status"] == "ok")
    try:
        get("http://127.0.0.1:8080/work")
        raise AssertionError("expected injected 500")
    except HTTPError as e:
        assert e.code == 500; e.close()
    wait("availability alert fires", lambda: any(a["labels"]["alertname"] == "LabAvailabilityBurn" and a["state"] == "firing" for a in get("http://127.0.0.1:9090/api/v1/alerts")["data"]["alerts"]), 240)
    (out/"alerts-during-failure.json").write_text(json.dumps(get("http://127.0.0.1:9090/api/v1/alerts"), indent=2))
    fault(0, 1500)
    wait("measured slow request", lambda: get("http://127.0.0.1:8080/work")["duration_seconds"] >= 1.4)
    wait("latency alert fires", lambda: any(a["labels"]["alertname"] == "LabLatencyHigh" and a["state"] == "firing" for a in get("http://127.0.0.1:9090/api/v1/alerts")["data"]["alerts"]), 180)
    fault(0, 0)
    wait("user requests recover", lambda: get("http://127.0.0.1:8080/work")["status"] == 200)
    wait("short window error ratio recovers", lambda: any(float(x["value"][1]) == 0 for x in query('sum(rate(lab_requests_total{status="500"}[30s])) / sum(rate(lab_requests_total[30s]))')), 90)
    wait("five minute alerts resolve", lambda: not any(a["state"] == "firing" and a["labels"]["alertname"] in ("LabAvailabilityBurn", "LabLatencyHigh") for a in get("http://127.0.0.1:9090/api/v1/alerts")["data"]["alerts"]), 420)
    (out/"alerts-after-recovery.json").write_text(json.dumps(get("http://127.0.0.1:9090/api/v1/alerts"), indent=2))
finally:
    stop.set()
    (out/"runtime-results.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
