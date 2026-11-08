# Lab availability / latency runbook

1. Establish impact: inspect request rate, error ratio, p99, and target availability.
2. Compare `/healthz` with `/work`. A healthy process can still fail user requests.
3. Correlate the start with configuration changes: inspect `ERROR_RATE` and `DELAY_MS`.
4. Reproduce with bounded local traffic and check structured logs (`docker compose logs app`).
5. Mitigate the lab fault: `ERROR_RATE=0 DELAY_MS=0 docker compose up -d --force-recreate app`.
6. Continue traffic and observe the five-minute query windows recover. A restart
   resets counters; `rate()` accounts for counter resets but old samples remain in the window.
7. Record impact, hypothesis, evidence, mitigation, and a prevention action.

No notifications are sent. Alertmanager integration is deliberately not configured.
This is a single-window demonstration, not a complete production burn-rate policy.
Production needs multi-window alerts, service-specific traffic gates, paging routing,
maintenance handling, and an explicit policy for missing data.
