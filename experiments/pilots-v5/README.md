# Piloto B revisado e comparação v5.0

Aplicar AMENDMENT.md. pilot-b.json tem dez cenários com gabaritos revisados; evidence-decisions.json justifica todas as fontes. evaluation-rubric.md separa conteúdo final e procedimento; calibration.json contém 20 fixtures técnicas. Lotes e credenciais privados permanecem ignorados pelo Git. Os casos não são a amostra definitiva nem transcrições reais.

Executar na raiz do repositório, com credencial Bedrock válida em apps/agent-runtime/.env, sem sincronizar dependências durante a coleta. Diretórios novos são obrigatórios; snapshots de v4 preservados. Se a calibração v5.0 falhar, investigar, versionar e recalibrar antes de coletar agentes. Não reaplicar avaliação válida por resultado ruim.

```sh
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/connectivity --connectivity
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/calibration-v5.1 --calibrate
apps/agent-runtime/.venv/bin/python scripts/regrade_automated_pilots.py var/reports/automated-pilots-v4/pilot-b experiments/pilots-v5/pilot-b.json var/reports/automated-pilots-v5/historical-regrade --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/historical-regrade --judge --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v5/historical-regrade --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/run_research_pilot.py --cases experiments/pilots-v5/pilot-b.json --output var/reports/automated-pilots-v5/pilot-b --repetitions 5 --max-tokens 2048 --calibration var/reports/automated-pilots-v5/calibration-v5.1 --continue-after-failure
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/pilot-b --judge --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/pilot-b --recheck --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v5/pilot-b --calibration var/reports/automated-pilots-v5/calibration-v5.1
apps/agent-runtime/.venv/bin/python scripts/compare_automated_pilots.py var/reports/automated-pilots-v4/pilot-b var/reports/automated-pilots-v5/historical-regrade var/reports/automated-pilots-v5/pilot-b var/reports/automated-pilots-v5/comparison
```

Runner aceita --plan-only e --resume. Plano é congelado com o hash de configuração esperada do juiz; coleta live exige calibração positiva dessa mesma configuração. Retomada recusa deriva de código/SDK e não repete unidades terminais. Sem calibração ou acesso aos modelos, preservar o estado preparado sem declarar execução. Locks e resolução de processos interrompidos continuam obrigatórios. Regrade histórico não é nova coleta nem prova de entrada corrigida; os respectivos consumos dos agentes não são somados novamente como consumo da nova rodada.

metrics.csv e architecture-stratum-metrics.csv têm denominadores e cobertura; quality-distributions.csv e criterion-distributions.csv apresentam notas e requisitos individuais. Conteúdo final, procedimento, tarefa, consumo, encaminhamento e diagnósticos são separados. initial-input-equivalence.json registra igualdade de prompts iniciais dentro de cada caso. judge-inputs preserva pacotes normalizados por resposta/fase; arquivos com valores desconhecidos não são preenchidos com zero. Snapshots/manifestos e fontes v4 permanecem preservados.

Auditoria farmacêutica opcional: pacotes e template focalizado até 24 respostas, priorizando flags e cobrindo arquiteturas. Se dois profissionais avaliarem, usar IDs pseudônimos distintos e importar com scripts/import_focused_reviews.py; não usar template amplo legado. Rótulos individuais ficam separados dos LLM. Sem revisão, human_review_performed=false; sem consenso ou taxa representativa inventados.

A decisão sobre 600 depende do relatório deste piloto. Não executar a matriz apenas porque a coleta terminou. Fontes simuladas, indicação textual de encaminhamento e ausência de HTTP/banco/OCR devem permanecer explícitas no TCC.

## Iteração de calibração v5.1

A tentativa v5.0 foi preservada e recusada pelo gate (14/20 fixtures aprovadas). Antes de coletar agentes, v5.1 restringe IDs de evidência no schema e explicita a independência dos critérios: disponibilidade correta não se torna falsa por quantidade errada; incerteza não equivale a fato oposto; recomendação presente não desaparece por outra alegação operacional indevida. Gabaritos das 20 fixtures permanecem iguais. Nova calibração integral, sem repetir avaliação válida da versão anterior por nota desfavorável. Rubrica de conteúdo e datasets v5.0 permanecem os mesmos; a configuração do juiz efetiva é v5.1.
