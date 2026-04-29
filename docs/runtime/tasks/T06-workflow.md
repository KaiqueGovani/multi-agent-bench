# T06 Structured Workflow

- Scope: staged workflow path with explicit classify, evidence, multimodal, review, and synthesis phases.
- Contracts touched: workflow stage payloads and projection snapshots.
- Validation command: `python scripts/run_fixture_scenarios.py --scenario product-image --scenario document-pdf`
- Expected pass criteria: stages appear in order and optional multimodal stage activates only when attachments exist.
- Known limitations: parallel branch support is intentionally narrow in this POC iteration.
- Artifact: [workflow-dag-report.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T06/workflow-dag-report.json)
