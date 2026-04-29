# T10 Dashboard Comparison

- Scope: extend dashboard metrics with tool distribution and latency percentiles, keeping `chat-api` as the aggregation layer.
- Contracts touched: dashboard response payload and web dashboard rendering.
- Validation command: `python scripts/run_e2e_validation.py`
- Expected pass criteria: dashboard payload contains architecture/model/scenario/tool slices and latency summary values.
- Known limitations: percentiles are computed from transactional run summaries only.
- Artifact: [comparison-summary.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T10/comparison-summary.json)
