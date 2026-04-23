# POC Test Fixtures

Fixtures for repeatable POC demonstrations and smoke checks.

Each scenario in `scenarios/` describes:

- conversation payload metadata
- message text and optional attachments
- expected HTTP status
- expected mock route, actor, events, and review state
- image and PDF attachments used to validate multimodal input

Run all scenarios against a local API:

```powershell
python scripts/run_fixture_scenarios.py
```

Run one scenario:

```powershell
python scripts/run_fixture_scenarios.py --scenario stock-availability
```

The script expects the API at `http://127.0.0.1:8000` unless `--api-base` is provided.
