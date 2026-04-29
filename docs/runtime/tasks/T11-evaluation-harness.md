# T11 Evaluation Harness

- Scope: run the same fixture set across the three architectures and emit machine-readable plus Markdown benchmark outputs.
- Contracts touched: scenario metadata propagation and comparative reporting.
- Validation command: `python scripts/run_architecture_benchmark.py`
- Expected pass criteria: one report bundle contains results for all configured architectures and scenarios.
- Known limitations: results depend on the runtime mode configured in the API and runtime services.
- Artifact: [final-benchmark-report.md](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T11/final-benchmark-report.md)
