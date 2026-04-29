# T02 Runtime Contract

- Scope: enrich the `chat-api -> agent-runtime` payload with run, message, history, attachments, trace context, and callback config.
- Contracts touched: runtime dispatch payload, callback config, attachment descriptors.
- Validation command: `python scripts/run_e2e_validation.py`
- Expected pass criteria: message acceptance still works and external runtime dispatch remains backward compatible.
- Known limitations: callback signing is header-based, not HMAC.
- Artifact: [runtime-contract.json](/Users/kaiquemg/Repos/multi-agent-bench/var/reports/runtime/T02/runtime-contract.json)
