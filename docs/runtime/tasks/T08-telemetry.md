# T08 Telemetry

- Scope: runtime logging, trace ID propagation, and OTEL bootstrap hooks for Strands-compatible observability.
- Contracts touched: trace propagation fields, run summaries, runtime environment configuration.
- Validation command: `python scripts/run_e2e_validation.py`
- Expected pass criteria: `run_id` and `trace_id` remain visible across API, runtime callbacks, and UI.
- Known limitations: OTEL export is optional and environment-driven.
- Artifact: [otel-validation.md](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T08/otel-validation.md)
