# Research & Product Direction — 2026-06-01

Companion to [06-improvement-audit.md](./06-improvement-audit.md). That file lists engineering cleanups; this one is about what the project should *be about*. Two angles: scientist (what does the thesis prove?) and product (what does someone using the demo actually take away?).

Context: this is a TCC POC whose **research goal is comparing coordination architectures** for pharmacy customer service. Today the system runs the three architectures and surfaces mechanics. The next step is making sure those runs answer the thesis question convincingly and that the demo tells a story.

---

## Scientist mindset

### 1. Define "better" up front — pick outcome dimensions, then measure

The dashboard surfaces *mechanics* (latency, events, tokens, handoffs). Useful, but they don't answer the thesis question. Pick 4–5 *outcome* dimensions and instrument all of them before running more benchmarks:

- **Correctness** — did the response cite the right SKU / FAQ entry?
- **Safety** — did it escalate / refuse when it should have? (Clinical, dosing, pediatric, off-label.)
- **Calibration** — when the system says "tenho certeza", is it actually right?
- **Cost-efficiency** — $/conversation on the Pareto frontier with quality.
- **Robustness** — slight rephrasing → same answer? Adversarial survival rate?

The LLM-as-judge plan in [04-llm-as-judge.md](./04-llm-as-judge.md) should grade *each* dimension separately, not collapse to a single "overall quality" score.

### 2. Run statistically, not anecdotally

A defense committee will ask. For each (scenario × architecture) cell:
- N ≥ 30 runs.
- Report **median + IQR + p95** (LLM latency is right-skewed; means lie).
- Bootstrap CIs or sign-test for any claim like "centralizada é mais rápida".
- Same scenarios, prompts, and model across architectures — if the model differs per arch, two variables are conflated.
- Save raw runs as frozen Parquet/CSV in the repo so the thesis is reproducible.

### 3. Ablations are where the thesis gets interesting

A boring thesis says "swarm 9.5s, centralizada 6.2s, centralizada wins." A strong one explains *why* and *when each is preferred*:

- Remove the supervisor in centralizada → does routing collapse? (Is the supervisor adding value or just dispatching?)
- Force serial handoffs in swarm → does parallelism explain the cost?
- Swap Haiku → Sonnet → does the architecture gap close? (If yes, model capability dominates over architecture choice — that's a finding.)
- **Single-agent baseline** — one prompt, all tools, no orchestration. Are 3 specialists actually beating a generalist? If not, that's the most interesting result in the thesis.

The strongest story is usually a **Pareto map** — e.g. "swarm dominates on multimodal + ambiguous, workflow wins on simple stock, centralizada wins on clinical" — not a single winner.

### 4. Failure taxonomy, not just success rates

Most papers report only win rate; the richer story is *how each architecture fails*. Build a multi-label classifier into the LLM judge:

- wrong-tool
- hallucinated-SKU
- hallucinated-dosage
- over-escalated
- under-escalated (most dangerous)
- didn't-converge / hit max handoffs

Plot failure mode × architecture. That becomes a key thesis figure and shapes the recommendation section.

### 5. Out-of-distribution stress tests

Curate ~20 adversarial scenarios on top of the happy path:
- prompt injection
- multilingual
- contradictions / corrections mid-conversation
- multi-turn refinements
- pediatric + dosing combinations
- ambiguous SKU references ("aquele genérico do antibiótico")

The happy path doesn't differentiate the three architectures — OOD does. The most cited results in multi-agent literature come from stress conditions, not nominal ones.

---

## Product mindset

### 6. Pick an audience for each surface

Visão Geral today is a researcher's instrument. For a defense / pharmacy stakeholder demo, add a complementary surface that tells a story:

- **Scenario gallery** — curated canonical questions (estoque simples, clínica ambígua, anexo + estoque, prompt injection). Click → all three architectures run → side-by-side verdict.
- **Per-scenario verdict card** — "Centralizada acertou ✓ · Swarm alucinou ✗ · Workflow escalou desnecessariamente ⚠" with one-sentence reasoning.
- **Decision narrative** — translate the agent flow into prose: "O Supervisor classificou como consulta de estoque, delegou ao agente Estoque que consultou o catálogo." Far more compelling for non-technical viewers than "1 tool · 2 resp" badges.

### 7. Show cost in R$ / $, not tokens

Tokens are an engineering unit. For deployment decisions, **$/conversation** is the unit. Project to "per 1k atendimentos/mês". Two columns in the leaderboard: per-conversation and projected monthly.

### 8. Calibration is publishable *and* a product angle

Ask the LLM to self-report confidence (1–5) on every response. Two payoffs:
- **In chat:** display confidence as a trust signal.
- **In dashboard:** plot calibration curves (predicted vs. actual correctness).

"This architecture knows when it doesn't know" is both a thesis result and a deployment differentiator.

### 9. Escalation is the product moment

Pharmacy = high stakes. Today `humanReviewRequired` is a flag. Promote it to a first-class UI element with a stated reason ("escalando porque envolve dosagem pediátrica"). Then compare across architectures: which over-escalates? Which under-escalates? That ratio is what a pharmacy ops manager actually cares about — and "under-escalation" is the most dangerous failure mode in this domain.

### 10. Replace radar mechanics with an outcome leaderboard

The radar chart shows volume; what people want is rank by outcome:

| Cenário | Vencedor | Por quê |
|---|---|---|
| Estoque simples | Workflow | mais rápido, resposta idêntica |
| Clínica ambígua | Centralizada | escalou corretamente |
| Anexo + estoque | Swarm | specialists colaboraram |
| Prompt injection | Centralizada | recusou |

This is the table that lands in the thesis and on the defense slide.

---

## Suggested order

If only one scientist + one product item gets done:

1. **#1 (multi-dim outcome metrics)** — without this, every comparison is unfounded.
2. **#6 (scenario gallery + verdict view)** — without this, the demo looks like an instrument, not a result.

Together they reframe the project from "we built three architectures and they ran" to **"we measured what matters and here's when to use each"** — which is the actual thesis contribution.

After that, in order of impact:
- **#4 (failure taxonomy)** — turns the LLM judge into a tool that produces thesis figures.
- **#9 (escalation as product moment)** — biggest stakeholder-facing differentiator.
- **#3 (ablations)** — makes the conclusion section rigorous, especially the single-agent baseline.
- **#2 (statistical rigor)** — needed before any public claim, but lower risk if N is small in early iterations.
- **#5 (OOD stress tests)** — curate after the happy path is stable.
- **#7, #8, #10** — UI polish that follows once the data is there.

---

## What to *avoid*

- **Don't claim "X is better"** without showing the scenario, N, and CI.
- **Don't compare architectures using different models or prompts.** That's the thesis equivalent of confounded variables.
- **Don't optimize the engineering** (06-improvement-audit.md) before knowing which architecture stays. Some of the cleanups become moot if a finding kills an architecture.
- **Don't add a fourth architecture** unless there's a hypothesis it tests. More variants ≠ stronger thesis.
