# T05 Centralized Orchestration

- Scope: centralized runtime path with supervisor-led routing, specialist invocation, review gate, and final synthesis.
- Contracts touched: run execution events for node, tool, handoff, review, and response families.
- Validation command: `python scripts/run_fixture_scenarios.py --scenario faq-question --scenario stock-availability`
- Expected pass criteria: routes and specialist evidence match the controlled scenarios.
- Known limitations: routing remains deterministic for comparability.
- Artifact: [supervisor-run-report.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T05/supervisor-run-report.json)
