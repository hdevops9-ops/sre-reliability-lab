# SLO Burn Rate and Telemetry Coverage

A repeatable on-call exercise for a checkout API. The evaluator reads one-minute request counts and computes request-based availability and error-budget burn. Run with Python 3.10+ and no dependencies:

```sh
cd slo-burn-rate
python evaluate.py --scenario healthy
python evaluate.py --scenario incident
python evaluate.py --scenario telemetry-gap
```

| Scenario | Expected decision |
| --- | --- |
| Healthy | Continue monitoring |
| Incident | Page the on-call engineer |
| Telemetry gap | Investigate missing metrics |
| No traffic | Report insufficient traffic |

The example objective is 99.9% availability. Burn rate is the observed failed-request fraction divided by 0.001, the allowed fraction. The page condition requires at least 14.4× burn in both the last five minutes and last hour. The thresholds are explicit so teams can adapt them to their own SLO policy.

A missing minute blocks the health decision. A complete window with zero requests is classified separately. The script reports missing minutes and evaluated request counts so an operator can check the basis for each result.

For a page, verify user impact and correlate the rise in failures with deployments or downstream health. For a telemetry gap, check the scrape target, collector and ingestion path, then cross-check with a synthetic probe. The fixtures are synthetic. The evaluator demonstrates one paging rule and does not measure monthly SLA compliance or connect to a live metrics backend.

Run `python -m unittest -v` to verify the fixtures and the distinction between missing metrics and zero traffic.

## Replay telemetry from CSV

Export one row per minute with the header `minute,requests,errors`. Use consecutive integer minute IDs or Unix epoch minutes. Include a row with zero counts for a measured idle minute and omit a row for a missing observation.

```sh
python evaluate.py --csv checkout.csv --end-minute 60
```

The end is exclusive. This example evaluates minutes 0–59 for the hour and 55–59 for the short window. Supply the expected end even when the newest observations are missing, so a stale export cannot shift the evaluation window backwards. Duplicate minutes and invalid counts fail with an input error.
