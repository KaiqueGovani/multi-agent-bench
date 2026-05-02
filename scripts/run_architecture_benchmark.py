"""Architecture benchmark runner for Multi-Agent Bench.

Runs YAML scenarios across architectures, collects RunMetrics, and generates
a comparative markdown report with aggregations and mermaid charts.

Usage:
    python scripts/run_architecture_benchmark.py --help
    python scripts/run_architecture_benchmark.py --architectures cent,work,swarm --iterations 1
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

# Ensure tests/e2e-quality is importable
ROOT = Path(__file__).resolve().parents[1]
E2E_DIR = ROOT / "tests" / "e2e-quality"
sys.path.insert(0, str(E2E_DIR))

from api_client import E2EClient  # noqa: E402
from benchmark_client import BenchmarkClient, RunMetrics  # noqa: E402
from _loader import load_yaml_scenarios  # noqa: E402

ARCH_ALIASES = {
    "cent": "centralized_orchestration",
    "work": "structured_workflow",
    "swarm": "decentralized_swarm",
}
VALID_ARCHS = set(ARCH_ALIASES.values())

# Short display names for report tables
ARCH_SHORT = {
    "centralized_orchestration": "centralized",
    "structured_workflow": "workflow",
    "decentralized_swarm": "swarm",
}


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run architecture benchmark for multi-agent-bench",
    )
    p.add_argument(
        "--architectures",
        default="cent,work,swarm",
        help="Comma-separated architecture modes or aliases (cent, work, swarm). Default: cent,work,swarm",
    )
    p.add_argument(
        "--scenarios",
        default=None,
        help="Comma-separated scenario case IDs. Default: all from YAML.",
    )
    p.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Repetitions per (scenario, architecture). Default: 1",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Enable live mode defaults (longer timeout, 1 req/s throttle).",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Default: var/reports/benchmark/<timestamp>",
    )
    p.add_argument(
        "--api-base",
        default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL. Default: env API_BASE_URL or http://127.0.0.1:8000",
    )
    p.add_argument(
        "--api-key",
        default=os.getenv("API_KEY", "poc-dev-key-2026"),
        help="API key. Default: env API_KEY or poc-dev-key-2026",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Per-run timeout seconds. Default: 60 (120 in --live)",
    )
    p.add_argument(
        "--scenarios-dir",
        default=str(E2E_DIR / "scenarios"),
        help="YAML scenarios directory. Default: tests/e2e-quality/scenarios",
    )
    return p.parse_args(argv)


def resolve_architectures(raw: str) -> list[str]:
    """Resolve comma-separated aliases/names into valid architecture modes."""
    resolved = []
    for token in raw.split(","):
        token = token.strip()
        arch = ARCH_ALIASES.get(token, token)
        if arch not in VALID_ARCHS:
            print(
                f"Error: '{token}' is not a valid architecture. "
                f"Valid: {', '.join(sorted(VALID_ARCHS))} (aliases: {', '.join(sorted(ARCH_ALIASES))})",
                file=sys.stderr,
            )
            sys.exit(1)
        resolved.append(arch)
    return resolved


def git_short_sha() -> str:
    """Return short git SHA, or '?' on failure."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "?"


def percentile(sorted_values: list[float], p: float) -> float:
    """Simple percentile on a pre-sorted list. Returns single value if n < 2."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_values[0]
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def aggregate(metrics: list[RunMetrics]) -> dict:
    """Compute aggregations over a list of RunMetrics."""
    count = len(metrics)
    if count == 0:
        return {"count": 0, "success_count": 0, "success_rate": "N/A"}

    success_count = sum(1 for m in metrics if m.success)
    success_rate = success_count / count

    ok = [m for m in metrics if m.success]
    if not ok:
        return {
            "count": count,
            "success_count": 0,
            "success_rate": 0.0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "avg_input_tokens": 0.0,
            "avg_output_tokens": 0.0,
            "avg_total_tokens": 0.0,
            "stddev_total_tokens": 0.0,
            "avg_tool_calls": 0.0,
            "avg_tool_errors": 0.0,
            "avg_loops": 0.0,
            "avg_handoffs": 0.0,
            "review_rate": 0.0,
        }

    latencies = sorted(m.latency_ms for m in ok)
    total_tokens_list = [m.total_tokens for m in ok]
    n = len(ok)

    return {
        "count": count,
        "success_count": success_count,
        "success_rate": success_rate,
        "latency_p50": percentile(latencies, 0.50),
        "latency_p95": percentile(latencies, 0.95),
        "avg_input_tokens": statistics.mean(m.input_tokens for m in ok),
        "avg_output_tokens": statistics.mean(m.output_tokens for m in ok),
        "avg_total_tokens": statistics.mean(total_tokens_list),
        "stddev_total_tokens": statistics.stdev(total_tokens_list) if n >= 2 else 0.0,
        "avg_tool_calls": statistics.mean(m.tool_call_count for m in ok),
        "avg_tool_errors": statistics.mean(m.tool_error_count for m in ok),
        "avg_loops": statistics.mean(m.loop_count for m in ok),
        "avg_handoffs": statistics.mean(m.handoff_count for m in ok),
        "review_rate": sum(1 for m in ok if m.review_required) / count,
    }


def _fmt_lat(v: float) -> str:
    return f"{v:,.0f} ms"


def _fmt_pct(v) -> str:
    if isinstance(v, str):
        return v
    return f"{round(v * 100)}%"


def _fmt_avg(v: float) -> str:
    return f"{v:.1f}"


def build_report_md(metrics: list[RunMetrics], meta: dict) -> str:
    """Generate the full markdown report."""
    lines: list[str] = []

    # -- Header -----------------------------------------------------------
    lines.append("# Benchmark Report — Multi-Agent Bench")
    lines.append("")
    lines.append("| Meta | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Data | {meta['timestamp']} |")
    lines.append(f"| Commit | `{meta['commit']}` |")
    lines.append(f"| Modo | {meta['mode_label']} |")
    lines.append(f"| Arquiteturas | {meta['arch_count']} |")
    lines.append(f"| Cenários | {meta['scenario_count']} |")
    lines.append(f"| Iterações | {meta['iterations']} |")
    lines.append(f"| Total de execuções | {meta['total_runs']} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # -- Per-architecture aggregation -------------------------------------
    archs = meta["architectures"]
    arch_aggs = {}
    for arch in archs:
        arch_metrics = [m for m in metrics if m.architecture_mode == arch]
        arch_aggs[arch] = aggregate(arch_metrics)

    # -- Resumo por Arquitetura -------------------------------------------
    lines.append("## Resumo por Arquitetura")
    lines.append("")
    lines.append("| Arquitetura | p50 Latência | p95 Latência | Avg Tokens | Avg Tool Calls | Avg Handoffs | Review Rate | Success Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for arch in archs:
        a = arch_aggs[arch]
        lines.append(
            f"| {arch} | {_fmt_lat(a['latency_p50'])} | {_fmt_lat(a['latency_p95'])} "
            f"| {_fmt_avg(a['avg_total_tokens'])} | {_fmt_avg(a['avg_tool_calls'])} "
            f"| {_fmt_avg(a['avg_handoffs'])} | {_fmt_pct(a['review_rate'])} "
            f"| {_fmt_pct(a['success_rate'])} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # -- Detalhamento por Cenário -----------------------------------------
    lines.append("## Detalhamento por Cenário")
    lines.append("")
    scenario_ids = list(dict.fromkeys(m.scenario_id for m in metrics))
    for sid in scenario_ids:
        lines.append(f"### {sid}")
        lines.append("")
        header_archs = " | ".join(ARCH_SHORT.get(a, a) for a in archs)
        lines.append(f"| Métrica | {header_archs} |")
        lines.append(f"|---|{'---:|' * len(archs)}")

        sc_aggs = {}
        for arch in archs:
            sc_metrics = [m for m in metrics if m.architecture_mode == arch and m.scenario_id == sid]
            sc_aggs[arch] = aggregate(sc_metrics)

        rows = [
            ("p50 Latência (ms)", lambda a: _fmt_lat(a["latency_p50"])),
            ("Avg Input Tokens", lambda a: _fmt_avg(a["avg_input_tokens"])),
            ("Avg Output Tokens", lambda a: _fmt_avg(a["avg_output_tokens"])),
            ("Avg Tool Calls", lambda a: _fmt_avg(a["avg_tool_calls"])),
            ("Avg Tool Errors", lambda a: _fmt_avg(a["avg_tool_errors"])),
            ("Avg Handoffs", lambda a: _fmt_avg(a["avg_handoffs"])),
            ("Review Rate", lambda a: _fmt_pct(a["review_rate"])),
            ("Success Rate", lambda a: _fmt_pct(a["success_rate"])),
        ]
        for label, fn in rows:
            vals = " | ".join(fn(sc_aggs[a]) for a in archs)
            lines.append(f"| {label} | {vals} |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # -- Observações Automáticas ------------------------------------------
    lines.append("## Observações Automáticas")
    lines.append("")
    lines.extend(_build_observations(archs, arch_aggs))
    lines.append("")
    lines.append("---")
    lines.append("")

    # -- Gráfico Latência ------------------------------------------------
    lines.append("## Gráfico — Latência p50 por Arquitetura (ms)")
    lines.append("")
    x_labels = ", ".join(f'"{ARCH_SHORT.get(a, a)}"' for a in archs)
    lat_vals = ", ".join(str(round(arch_aggs[a]["latency_p50"])) for a in archs)
    y_max = max((arch_aggs[a]["latency_p50"] for a in archs), default=100)
    y_ceil = round(y_max * 1.3) if y_max > 0 else 100
    lines.append("```mermaid")
    lines.append("xychart-beta")
    lines.append('    title "Latência p50 por Arquitetura (ms)"')
    lines.append(f"    x-axis [{x_labels}]")
    lines.append(f'    y-axis "Latência (ms)" 0 --> {y_ceil}')
    lines.append(f"    bar [{lat_vals}]")
    lines.append("```")
    lines.append("")

    # -- Gráfico Tool Calls -----------------------------------------------
    lines.append("## Gráfico — Tool Calls Médio por Arquitetura")
    lines.append("")
    tc_vals = ", ".join(f"{arch_aggs[a]['avg_tool_calls']:.1f}" for a in archs)
    tc_max = max((arch_aggs[a]["avg_tool_calls"] for a in archs), default=1)
    tc_ceil = round(tc_max * 1.3) if tc_max > 0 else 10
    lines.append("```mermaid")
    lines.append("xychart-beta")
    lines.append('    title "Tool Calls Médio por Arquitetura"')
    lines.append(f"    x-axis [{x_labels}]")
    lines.append(f'    y-axis "Tool Calls" 0 --> {tc_ceil}')
    lines.append(f"    bar [{tc_vals}]")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _build_observations(archs: list[str], aggs: dict[str, dict]) -> list[str]:
    """Generate 3-5 auto-observation bullets in PT-BR."""
    obs: list[str] = []
    valid = [a for a in archs if aggs[a]["count"] > 0 and aggs[a]["success_count"] > 0]
    if not valid:
        obs.append("- ⚠️ Nenhuma execução bem-sucedida para gerar observações.")
        return obs

    # 🏎️ Fastest by p50
    by_lat = sorted(valid, key=lambda a: aggs[a]["latency_p50"])
    fastest, slowest = by_lat[0], by_lat[-1]
    if len(valid) > 1 and aggs[slowest]["latency_p50"] > 0:
        ratio = aggs[slowest]["latency_p50"] / aggs[fastest]["latency_p50"]
        obs.append(
            f"- 🏎️ **{fastest}** teve a menor latência p50 "
            f"({_fmt_lat(aggs[fastest]['latency_p50'])}) — "
            f"{ratio:.1f}x mais rápido que {slowest}"
        )
    else:
        obs.append(
            f"- 🏎️ **{fastest}** teve a menor latência p50 "
            f"({_fmt_lat(aggs[fastest]['latency_p50'])})"
        )

    # 🔧 Most tool calls
    by_tc = sorted(valid, key=lambda a: aggs[a]["avg_tool_calls"])
    most_tc, least_tc = by_tc[-1], by_tc[0]
    if len(valid) > 1 and aggs[least_tc]["avg_tool_calls"] > 0:
        ratio = aggs[most_tc]["avg_tool_calls"] / aggs[least_tc]["avg_tool_calls"]
        obs.append(
            f"- 🔧 **{most_tc}** usou {ratio:.1f}x mais tool calls que "
            f"{least_tc} em média ({_fmt_avg(aggs[most_tc]['avg_tool_calls'])} vs "
            f"{_fmt_avg(aggs[least_tc]['avg_tool_calls'])})"
        )
    else:
        obs.append(
            f"- 🔧 **{most_tc}** usou mais tool calls em média "
            f"({_fmt_avg(aggs[most_tc]['avg_tool_calls'])})"
        )

    # 🔀 Handoffs
    by_ho = sorted(valid, key=lambda a: aggs[a]["avg_handoffs"])
    if aggs[by_ho[-1]]["avg_handoffs"] > 0:
        most_ho = by_ho[-1]
        obs.append(
            f"- 🔀 **{most_ho}** realizou {_fmt_avg(aggs[most_ho]['avg_handoffs'])} "
            f"handoffs em média; {by_ho[0]} não realizou nenhum"
            if aggs[by_ho[0]]["avg_handoffs"] == 0
            else f"- 🔀 **{most_ho}** realizou mais handoffs em média "
            f"({_fmt_avg(aggs[most_ho]['avg_handoffs'])})"
        )
    else:
        obs.append("- 🔀 Nenhuma arquitetura realizou handoffs")

    # 🔴 Lowest success rate or highest review rate
    by_sr = sorted(valid, key=lambda a: aggs[a]["success_rate"])
    lowest_sr = by_sr[0]
    by_rr = sorted(valid, key=lambda a: aggs[a]["review_rate"], reverse=True)
    highest_rr = by_rr[0]
    if isinstance(aggs[lowest_sr]["success_rate"], float) and aggs[lowest_sr]["success_rate"] < 1.0:
        obs.append(
            f"- 🔴 **{lowest_sr}** teve a menor taxa de sucesso "
            f"({_fmt_pct(aggs[lowest_sr]['success_rate'])})"
            + (
                f" e a maior taxa de review ({_fmt_pct(aggs[highest_rr]['review_rate'])})"
                if aggs[highest_rr]["review_rate"] > 0
                else ""
            )
        )
    elif aggs[highest_rr]["review_rate"] > 0:
        obs.append(
            f"- 🔴 **{highest_rr}** teve a maior taxa de review "
            f"({_fmt_pct(aggs[highest_rr]['review_rate'])})"
        )

    # 📊 Middle architecture
    if len(valid) >= 3:
        mid = by_lat[1]
        obs.append(f"- 📊 **{mid}** ficou no meio-termo em todas as métricas")

    return obs


def write_csv(metrics: list[RunMetrics], path: Path) -> None:
    """Write RunMetrics list to CSV."""
    fieldnames = [f.name for f in fields(RunMetrics)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in metrics:
            writer.writerow(m.to_json_dict())


def main(argv=None) -> int:
    args = parse_args(argv)

    # Resolve architectures
    architectures = resolve_architectures(args.architectures)

    # Timeout defaults
    if args.timeout is None:
        args.timeout = 120.0 if args.live else 60.0

    # Live mode warning
    if args.live and not os.getenv("ENABLE_LIVE_LLM"):
        print(
            "⚠️  --live ativado mas ENABLE_LIVE_LLM não está definido no shell atual. "
            "Certifique-se de que o agent-runtime foi iniciado com ENABLE_LIVE_LLM=true.",
            file=sys.stderr,
        )

    # Output dir
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = ROOT / "var" / "reports" / "benchmark" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load scenarios
    scenarios_dir = Path(args.scenarios_dir)
    selected_ids = [s.strip() for s in args.scenarios.split(",")] if args.scenarios else None
    items = load_yaml_scenarios(
        scenarios_dir,
        selected_ids=selected_ids,
        architectures_override=architectures,
    )
    if not items:
        print("Error: nenhum cenário encontrado após filtragem.", file=sys.stderr)
        return 1

    total_runs = len(items) * args.iterations
    scenario_ids = list(dict.fromkeys(case["id"] for _, case, _ in items))

    print(
        f"Benchmark: {len(architectures)} arquiteturas × {len(scenario_ids)} cenários × "
        f"{args.iterations} iterações = {total_runs} execuções",
        file=sys.stderr,
    )

    # Execute
    all_metrics: list[RunMetrics] = []
    log_lines: list[str] = []
    idx = 0

    with E2EClient(args.api_base, args.api_key, timeout=args.timeout) as client:
        bench = BenchmarkClient(client)
        for iteration in range(args.iterations):
            for test_id, case, arch in items:
                idx += 1
                t0 = time.monotonic()
                m = bench.run_and_collect(
                    case=case,
                    architecture=arch,
                    iteration=iteration,
                    timeout=args.timeout,
                )
                elapsed = (time.monotonic() - t0) * 1000
                all_metrics.append(m)

                status = "ok" if m.success else f"FAIL: {m.error}"
                line = (
                    f"[{idx}/{total_runs}] architecture={arch} "
                    f"scenario={m.scenario_id} iter={iteration} … "
                    f"{status} {elapsed:.0f}ms"
                )
                print(line, file=sys.stderr)
                log_lines.append(line)

                # Throttle in live mode (not after last run)
                if args.live and idx < total_runs:
                    time.sleep(1.0)

    # Write artifacts
    # Derive runtime mode from the first successful run's model_provider field
    first_ok = next((m for m in all_metrics if m.success and m.model_provider), None)
    if first_ok is None:
        mode_label = "❓ Unknown"
    elif first_ok.model_provider == "mock":
        mode_label = "🟢 Mock"
    else:
        mode_label = f"🔴 Live ({first_ok.model_provider}/{first_ok.model_name})"

    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": git_short_sha(),
        "live": args.live,
        "mode_label": mode_label,
        "architectures": architectures,
        "arch_count": len(architectures),
        "scenario_count": len(scenario_ids),
        "iterations": args.iterations,
        "total_runs": total_runs,
    }

    report_md = build_report_md(all_metrics, meta)
    (output_dir / "report.md").write_text(report_md, encoding="utf-8")

    runs_json = json.dumps(
        [m.to_json_dict() for m in all_metrics], indent=2, ensure_ascii=False,
    )
    (output_dir / "runs.json").write_text(runs_json, encoding="utf-8")

    write_csv(all_metrics, output_dir / "runs.csv")

    (output_dir / "benchmark.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(f"\n✅ Relatório gerado em: {output_dir}", file=sys.stderr)

    all_ok = all(m.success for m in all_metrics)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
