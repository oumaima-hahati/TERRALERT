# TERRALERT — Wildfire Pipeline & System Reliability QA

## 1. Scope

Study area: 11 Tanger-Assilah administrative areas.

This QA evaluates the local automated forecast pipeline,
its output integrity, failure detection, execution logging,
scheduling configuration, and failure notification mechanism.

The implementation is a provisional research system.
It does not issue public warnings.

## 2. Automated pipeline

The pipeline contains five stages:

1. Download Open-Meteo hourly forecasts.
2. Prepare operational FWI meteorological inputs.
3. Calculate provisional wildfire FWI forecasts.
4. Generate wildfire forecast GIS layers.
5. Calculate 24h/72h rainfall and weather summaries.

## 3. Reliability results

| Validation category | Passed | Failed |
|---|---:|---:|
| Read-only pipeline reliability | 14 | 0 |
| Isolated pipeline failure simulation | 8 | 0 |
| Isolated notification failure simulation | 5 | 0 |
| Total | 27 | 0 |

Testing date: 2026-11-25.

### Successful execution

- Pipeline stages: 5/5 successful.
- FWI forecast records: 33.
- Wildfire GIS features: 33.
- Rainfall summary records: 22.
- SQLite GeoPackage integrity: OK.
- Public alerts: disabled.
- Model status: PROVISIONAL_RESEARCH.

### Controlled pipeline failure

A simulated downloader exit code of 23 was injected into
an isolated copy of the automation controller.

Verified:
- Controller exited with nonzero status.
- Execution status was FAILED.
- No stages were falsely marked completed.
- Error details were recorded.
- Execution log was created.
- No forecast datasets were generated.
- Public alerts remained disabled.
- Research-only model status was preserved.

### Failure notification simulation

An isolated FAILED execution report with error
SIMULATED_API_FAILURE was supplied to the real
notification script copied into a temporary directory.

Verified:
- Notification script exited successfully.
- Notification type was PIPELINE_FAILURE.
- Latest pipeline status was FAILED.
- Execution identifier was preserved.
- Original failure reason was preserved.
- Notification JSON was generated.

## 4. Scheduling

A user-level systemd timer is installed, enabled,
and active.

Configured execution time: 07:00 local system time.

The forecast service has an OnFailure dependency
on terralert-forecast-failure.service.

The configuration has been inspected; automatic
systemd invocation during a real service failure
has not been demonstrated by these isolated tests.

A scheduled run also requires the execution machine
to be available and the systemd user manager to run.

## 5. Scientific and operational limitations

- FWI forecasts are provisional research outputs.
- Historical comparison with FIRMS does not establish
  independent prospective forecast accuracy.
- Meteorological station validation remains pending.
- No external email/SMS notification was verified.
- No public emergency alerting is enabled.
- End-to-end frontend, backend, and PostGIS integration
  is outside the scope of this local QA.
- Passing 27 checks is not proof of production readiness.

## 6. Conclusion

RESULT: PASSED — LOCAL PIPELINE RELIABILITY QA.

All 27 executed checks passed.

Local failure handling and notification generation
were verified in isolated tests.

Further operational acceptance requires real systemd
failure-path verification, external notification tests
if implemented, and end-to-end platform validation.
