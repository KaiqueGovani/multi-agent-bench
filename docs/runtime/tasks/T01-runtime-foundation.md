# T01 Runtime Foundation

- Scope: create `apps/agent-runtime`, configuration, healthcheck, callback bootstrap, Strands-ready Bedrock model configuration, and async `POST /runs`.
- Contracts touched: runtime dispatch request/response, runtime env defaults.
- Validation command: `uvicorn app.main:app --reload --app-dir apps/agent-runtime`
- Expected pass criteria: `GET /health` returns `ok` and `POST /runs` accepts a no-op or deterministic run.
- Known limitations: live Bedrock execution requires `ENABLE_LIVE_LLM=true` and `AWS_BEARER_TOKEN_BEDROCK`.
- Artifact: [bootstrap-report.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T01/bootstrap-report.json)
