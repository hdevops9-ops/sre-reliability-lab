# Full-stack runtime validation

Tested commit: `f9daa962bddae7d0464b3f096d4a05364dca75d0`.

[Successful workflow](https://github.com/hdevops9-ops/sre-reliability-lab/actions/runs/42449587866) · artifact `monitoring-runtime-evidence` contains container logs, actual dashboard provisioning, alert snapshots, and runtime results.

Measured waits in this test: availability alert firing 66.04s; latency alert firing 106.07s; five-minute-window alert resolution 236.13s after recovery. These are observations from this test run, not guaranteed detection/recovery objectives.

The test checked real HTTP 500 responses, independent health, a measured 1.5-second injected request, healthy traffic recovery, and alert resolution. No Alertmanager or real paging integration was configured.
