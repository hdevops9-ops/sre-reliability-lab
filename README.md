# SRE Reliability Lab

A locally runnable instrumented HTTP API with Prometheus, a provisioned Grafana
dashboard, fault injection, and a practical incident runbook. No AWS bill.
Personal portfolio lab; no employer data or claims of production adoption.

## Start

Requires Docker Compose and Python 3.12+. Run in this repository:

```bash
docker compose up --build -d
python3 load.py --requests 600
```

Open Grafana at http://localhost:3000 (initial local credentials: admin/admin;
change them when prompted). The provisioned dashboard is **Platform API — Reliability Lab**.
Prometheus: http://localhost:9090. API: http://localhost:8080/healthz.
All host ports bind to loopback. Keep this lab on your own computer.

## Inject a failure and recover

```bash
ERROR_RATE=0.2 DELAY_MS=250 docker compose up -d --force-recreate app
python3 load.py --requests 600
# Inspect Grafana, Prometheus Alerts, and docker compose logs app.
ERROR_RATE=0 DELAY_MS=0 docker compose up -d --force-recreate app
python3 load.py --requests 600
```

For latency, repeat with `DELAY_MS=1500`. Wait for enough scrapes and traffic;
alerts use five-minute rate windows and a pending interval. Slow requests make
this sequential generator run longer. There is no public fault-toggle endpoint.

## SLO reasoning

A teaching target of 99.9% successful `/work` requests allows 0.1% errors.
The availability alert triggers above 14.4 × 0.001 = 1.44% errors with a traffic gate.
This demonstrates burn-rate arithmetic; it is not a production multi-window alert.
The latency histogram has coarse buckets, so p99 is an estimate. Health checks and
metrics scrapes are excluded from the user-request denominator. Idle traffic yields
no meaningful error ratio; a separate `up` alert detects scrape failure.

## Tests and limits

```bash
python3 -m unittest discover -s app -v
```

Tests cover HTTP success/failure, independent health, unknown routes, cumulative
histogram buckets, and invalid fault settings. Docker/Prometheus/Grafana execution
still needs a Docker host; unit tests alone do not prove the whole stack works.
Images are version-tagged rather than digest-pinned. The dashboard contains live
local data only after you start the stack; no screenshots or results are fabricated.
See [runbook](docs/runbook.md) and [decisions](docs/decisions.md).

## Cleanup

```bash
docker compose down --volumes --remove-orphans
```

## References

- https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- https://prometheus.io/docs/practices/histograms/
- https://sre.google/workbook/alerting-on-slos/
