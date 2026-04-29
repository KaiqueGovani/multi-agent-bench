# T03 Event Pipeline

- Scope: persist rich execution events and projections by `run`, derive public `ProcessingEvent`s from runtime callbacks, and expose run execution routes.
- Contracts touched: `POST /integrations/ai/run-events`, `GET /runs/{run_id}/execution`, execution SSE stream.
- Validation command: `python scripts/run_e2e_validation.py`
- Expected pass criteria: ingested runtime events persist, replay in order, and materialize public events.
- Known limitations: projection reducer is intentionally lightweight and optimized for the POC.
- Artifact: [projection-snapshot.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T03/projection-snapshot.json)
