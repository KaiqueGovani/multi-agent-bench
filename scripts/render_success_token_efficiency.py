"""Render a descriptive success/token figure from the public v4.4 cohort.

Uses generation tokens from every attempt, including unsuccessful tasks.
The original measurements and frozen reports are read only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research-data/results/architectural-comparison-v44"
STEM = "Sucesso_por_milhao_de_tokens"
ARCHITECTURES = (
    ("centralized_orchestration", "Centralizada", "#235E98"),
    ("structured_workflow", "Workflow", "#AE5B19"),
    ("decentralized_swarm", "Swarm", "#31745E"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def aggregate() -> list[dict]:
    units = read_csv(SOURCE / "units.csv")
    summaries = {row["architecture"]: row for row in read_csv(SOURCE / "architecture-summary.csv")}
    keys = [(row["architecture"], row["scenario_id"], row["repetition"]) for row in units]
    if len(units) != 600 or len(set(keys)) != 600:
        raise ValueError("Expected the 600 unique attempts of the frozen v4.4 cohort")
    rows = []
    for architecture, label, _ in ARCHITECTURES:
        group = [row for row in units if row["architecture"] == architecture]
        scenarios = {row["scenario_id"] for row in group}
        if len(group) != 200 or len(scenarios) != 40 or any(
            len([row for row in group if row["scenario_id"] == scenario]) != 5 for scenario in scenarios
        ):
            raise ValueError(f"Incomplete scenario/repetition coverage: {architecture}")
        if any(row["task_success"] not in {"True", "False"} or row["token_measurement_complete"] != "True" for row in group):
            raise ValueError("Unknown outcomes or incomplete token measurements require a separate analysis")
        if any(int(row["total_tokens"]) != int(row["input_tokens"]) + int(row["output_tokens"]) for row in group):
            raise ValueError("Generation input/output tokens do not reconcile")
        successes = sum(row["task_success"] == "True" for row in group)
        tokens = sum(int(row["total_tokens"]) for row in group)
        if tokens <= 0 or successes <= 0:
            raise ValueError("The denominator and observed success count must be positive")
        summary = summaries[architecture]
        if successes != int(summary["task_successes"]) or tokens != int(summary["total_tokens_total"]):
            raise ValueError(f"Attempt data and frozen summary disagree: {architecture}")
        success_rate = successes / len(group)
        if not math.isclose(success_rate, float(summary["observed_success_rate"]), abs_tol=1e-12):
            raise ValueError("Success rates do not reproduce Figure 12")
        estimated_usd = sum(float(row["estimated_generation_cost_usd"]) for row in group)
        rows.append({
            "architecture": architecture, "label": label, "attempts": len(group),
            "scenarios": len(scenarios), "task_successes": successes,
            "success_rate": success_rate, "generation_tokens_total": tokens,
            "mean_generation_tokens_per_attempt": tokens / len(group),
            "successes_per_million_generation_tokens": successes / tokens * 1_000_000,
            "generation_tokens_per_observed_success": tokens / successes,
            "frozen_estimated_generation_usd_per_success": estimated_usd / successes,
        })
    baseline = rows[0]
    for row in rows:
        row["efficiency_change_vs_centralized_pct"] = (
            row["successes_per_million_generation_tokens"] / baseline["successes_per_million_generation_tokens"] - 1
        ) * 100
    return rows


def pt(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")


def render(rows: list[dict], output: Path) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 13, "svg.fonttype": "path",
        "svg.hashsalt": "mab-v44-success-token-efficiency", "axes.axisbelow": True,
    })
    ink = "#21384A"
    figure = plt.figure(figsize=(11, 5.6), facecolor="white")
    axes = figure.add_axes((0.105, 0.33, 0.88, 0.52))
    values = [row["successes_per_million_generation_tokens"] for row in rows]
    bars = axes.bar(range(3), values, width=0.58, color=[entry[2] for entry in ARCHITECTURES])
    axes.set_ylim(0, 110)
    axes.set_xlim(-0.48, 2.48)
    axes.yaxis.set_major_locator(MultipleLocator(20))
    axes.set_ylabel("Sucessos / 1 milhão de tokens", fontsize=14, color=ink, labelpad=10)
    axes.set_xticks(range(3), [row["label"] for row in rows], fontsize=15)
    axes.tick_params(axis="both", labelsize=14, length=5, width=1.2)
    axes.grid(axis="y", color="#E0E5E8", linewidth=1.2)
    for spine in ["top", "right"]:
        axes.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        axes.spines[spine].set_linewidth(1.2)
    for bar, value in zip(bars, values):
        axes.text(bar.get_x() + bar.get_width() / 2, value + 1.6, pt(value),
                  ha="center", va="bottom", fontsize=20, fontweight="bold", color=ink,
                  bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
    figure.text(0.105, 0.965, "Eficiência de sucesso por consumo de tokens",
                ha="left", va="top", fontsize=18, fontweight="bold", color=ink)
    for index, row in enumerate(rows):
        x = figure.transFigure.inverted().transform(axes.transData.transform((index, 0)))[0]
        figure.text(x, 0.235, f"Sucesso: {pt(row['success_rate'] * 100)}%", ha="center", color=ink, fontsize=11)
        figure.text(x, 0.19, f"Média: {pt(row['mean_generation_tokens_per_attempt'], 0)} tokens/tentativa",
                    ha="center", color=ink, fontsize=10.5)
        change = row["efficiency_change_vs_centralized_pct"]
        relative = "Referência" if index == 0 else f"{'+' if change >= 0 else '−'}{pt(abs(change))}% em eficiência"
        figure.text(x, 0.145, relative, ha="center", color=ARCHITECTURES[index][2], fontsize=11, fontweight="bold")
    figure.text(0.105, 0.07,
                "Eficiência = sucessos ÷ tokens totais × 1.000.000. Inclui as 200 tentativas por arquitetura, com e sem sucesso.",
                ha="left", fontsize=8.7, color=ink)
    figure.text(0.105, 0.028,
                "Fonte: dados v4.4. Tokens de geração (entrada + saída), sem o julgador. Análise descritiva complementar.",
                ha="left", fontsize=8.7, color=ink)
    figure.savefig(output / f"{STEM}.png", dpi=300, facecolor="white")
    figure.savefig(output / f"{STEM}.svg", facecolor="white", metadata={"Date": None})
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "var/success-token-efficiency-v44")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = aggregate()
    render(rows, output)
    with (output / f"{STEM}.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "analysis": "post_hoc_descriptive", "source_cohort": "architectural-comparison-v4.4",
        "formula": "sum(task_success) / sum(total_tokens) * 1000000",
        "denominator": "generation input + output tokens, including unsuccessful task attempts",
        "judge_tokens_included": False, "monetary_cost": False,
        "inference": "No new significance test or clinical validation; observational descriptive comparison",
        "sources": [{"path": str((SOURCE / name).relative_to(ROOT)), "sha256": hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()}
                    for name in ["units.csv", "architecture-summary.csv"]],
        "rows": rows,
    }
    (output / f"{STEM}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    caption = (
        "Eficiência de sucesso por consumo de tokens nas três configurações. "
        "O indicador divide os sucessos observados pelo total de tokens de geração e normaliza para um milhão de tokens. "
        "A análise inclui todas as 200 tentativas por configuração, inclusive as sem sucesso, e soma tokens de entrada e saída; "
        "não inclui o julgador. Os valores foram recalculados das tentativas, sem usar as medianas do boxplot. "
        "Análise descritiva complementar dos resultados automáticos v4.4; revisão humana pendente. "
        "Tokens representam consumo computacional, não custo monetário.\nFonte: Elaborado pelos autores (2026).\n"
    )
    (output / f"{STEM}_legenda.txt").write_text(caption, encoding="utf-8")
    print(json.dumps({"output": str(output), "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
