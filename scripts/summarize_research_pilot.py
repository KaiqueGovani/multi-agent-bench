#!/usr/bin/env python3
"""Descriptive pilot report; no inference or clinical-validity claims."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median
from run_research_pilot import write_csv
from app.architectures.comparison import ARCHITECTURES
from app.experiments.judge import DIMENSIONS


def fmt(values):
    values = [v for v in values if v is not None]
    return f"{median(values):.1f}" if values else "não medido"


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder",type=Path); args=parser.parse_args()
    folder=args.folder.resolve(); manifest=json.loads((folder/"manifest.json").read_text())
    records=[json.loads((folder/u["unit_id"]/"result.json").read_text()) for u in manifest["order"] if (folder/u["unit_id"]/"result.json").exists()]
    # Failed runs may still have complete, measured SDK usage in their events.
    # Derive it explicitly rather than assigning zero or discarding consumed tokens.
    for record in records:
        event_path = folder / record["unit_id"] / "events.jsonl"
        events = [json.loads(line) for line in event_path.read_text().splitlines()] if event_path.exists() else []
        starts = [e for e in events if e["eventFamily"] == "agent" and e["eventName"] == "started"]
        ends = [e for e in events if e["eventFamily"] == "agent" and e["eventName"] == "completed"]
        complete = bool(starts) and len(starts) == len(ends) and all(e["payload"].get("totalTokens") is not None for e in ends)
        record["usage_source"] = "measured-complete-agent-events" if complete else "incomplete-or-unavailable"
        for field, payload_key in (("input_tokens","inputTokens"),("output_tokens","outputTokens"),("total_tokens","totalTokens")):
            known = [e["payload"][payload_key] for e in ends if e["payload"].get(payload_key) is not None]
            record["observed_partial_" + field] = sum(known) if known else None
            record[field] = sum(e["payload"][payload_key] for e in ends) if complete and all(e["payload"].get(payload_key) is not None for e in ends) else None
    write_csv(folder / "analysis-runs.csv", records)
    evaluations=[json.loads(line) for line in (folder/"evaluations.jsonl").read_text().splitlines()] if (folder/"evaluations.jsonl").exists() else []
    mapping=json.loads((folder/"blind-mapping.json").read_text()) if (folder/"blind-mapping.json").exists() else {}
    by_attempt={r["attempt_id"]:r for r in records}
    judge={mapping[e["evaluation_id"]]:e for e in evaluations if e["reviewer_id"]=="llm_judge"}
    flattened=[]
    for e in evaluations:
        r=by_attempt[mapping[e["evaluation_id"]]]
        flattened.append({"evaluation_id":e["evaluation_id"],"reviewer_id":e["reviewer_id"],"attempt_id":r["attempt_id"],"scenario_id":r["scenario_id"],"architecture":r["architecture"],**e["scores"],"referral_adequacy":e["referral_adequacy"],"critical_error":e["critical_error"]})
    write_csv(folder/"quality-scores.csv",flattened,["evaluation_id","reviewer_id","attempt_id","scenario_id","architecture",*DIMENSIONS,"referral_adequacy","critical_error"])
    lines=[f"# Resultado do piloto — {manifest['configuration']['protocol']}", "", "**Piloto de engenharia, com critérios provisórios e sem validação farmacêutica.** Não é resultado definitivo do TCC nem demonstração de segurança clínica.", "",f"Planejamento: {len(manifest['cases'])} casos; {len(set(u['architecture'] for u in manifest['order']))} condições arquiteturais; {len(manifest['order'])} unidades. Tentativas registradas: {len(records)}; concluídas: {sum(bool(r.get('success')) for r in records)}; falhas: {sum(not r.get('success') for r in records)}.","", "Execução direta do núcleo, sem API/banco. Sete casos reconstruídos de prefixos liberados e três controles sintéticos; fontes da POC controlada. Uma repetição por condição/caso. As verificações anteriores estão em pastas distintas e não integram esta amostra.","",f"Modelo: `{manifest['configuration']['model_id']}`; região: `{manifest['configuration']['region']}`; temperatura: {manifest['configuration']['temperature']}; máximo por resposta: {manifest['configuration']['max_tokens']} tokens. SDK: {manifest['sdk_version']}. O manifesto registra parâmetros, ordem e hashes do código efetivo.","", "## Coleta técnica", "", "Medianas descritivas de execuções concluídas. Tempos do núcleo incluem instrumentação local. Invocações a agentes e requisições ao modelo são contagens diferentes. No protocolo v3, o swarm tem plano inicial validado e executado pelo controlador, seguido de delegação entre especialistas e síntese: é iniciação coordenada com colaboração entre pares, não descentralização integral. Não houve fallback para mock nesta coleta.","", "| Arquitetura | Concluídas / planejadas | Falhas | Duração mediana (ms) | Tokens medianos | Invocações de agente | Requisições ao modelo | Ferramentas de domínio | Handoffs |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arch in ARCHITECTURES:
        allrows=[r for r in records if r["architecture"]==arch]; rows=[r for r in allrows if r.get("success")]
        planned=sum(u["architecture"]==arch for u in manifest["order"])
        vals=[fmt([r.get(k) for r in rows]) for k in ("latency_ms","total_tokens","agent_invocations","model_requests","domain_tool_calls","handoff_count")]
        lines.append(f"| {arch} | {len(rows)} / {planned} | {sum(not r.get('success') for r in allrows)} | " + " | ".join(vals)+" |")
    lines += ["", "Consumo de tentativas falhas também deve ser contabilizado: analysis-runs.csv deriva uso de eventos quando todas as invocações terminaram com medição completa; uso parcial é guardado em colunas próprias e não confundido com total. O arquivo de tentativas original é preservado.", "", "## Qualidade pelo juiz automático", "",f"Avaliações válidas do juiz: {len(judge)}. Notas de 1 a 5 mantidas separadas; a tabela mostra medianas, sem índice agregado. As referências foram elaboradas pelos autores.","", "| Arquitetura | n avaliado | Correção | Completude | Clareza | Contexto | Segurança | Erros críticos sinalizados |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arch in ARCHITECTURES:
        values=[e for attempt,e in judge.items() if by_attempt[attempt]["architecture"]==arch]
        lines.append(f"| {arch} | {len(values)} | "+" | ".join(fmt([e["scores"][d] for e in values]) for d in DIMENSIONS)+f" | {sum(e['critical_error'] for e in values) if values else 'não avaliado'} |")
    if (folder/"judge-config.json").exists():
        cfg=json.loads((folder/"judge-config.json").read_text()); lines += ["",f"Juiz: `{cfg['model_id']}`; rubrica `{cfg['rubric_version']}`. Modelo igual ao avaliado: {'sim' if cfg['same_model_as_runtime'] else 'não'}. A preferência pelo próprio modelo e a calibração pendente são limitações desta avaliação."]
    if judge:
        flags = [(by_attempt[a], e) for a, e in judge.items() if e["critical_error"]]
        if all(e["scores"]["safety"] == 5 for e in judge.values()):
            lines += ["", "Todas as respostas receberam segurança 5 pelo juiz. Há efeito teto nessa dimensão; o piloto não permite distinguir segurança entre condições, nem concluir ausência de risco clínico."]
        if flags:
            lines += ["", "### Rótulos críticos que exigem calibração", "", "As marcações abaixo são interpretações do juiz, não pareceres farmacêuticos. Criticidade operacional e risco clínico precisam de definições separadas na rubrica definitiva; as notas originais foram preservadas."]
            for record, evaluation in flags:
                lines += ["", f"- {record['scenario_id']} / {record['architecture']}: segurança {evaluation['scores']['safety']}; correção {evaluation['scores']['correctness']}; completude {evaluation['scores']['completeness']}.", "", "Justificativa registrada pelo juiz: " + evaluation["critical_error_reason"]]
    lines += ["", "## Casos e sinais para revisão", "", "| Caso | Arquitetura | Status | Segurança pelo juiz | Encaminhamento pelo juiz | Erro crítico pelo juiz |", "|---|---|---|---:|---|---|"]
    for r in records:
        e=judge.get(r["attempt_id"])
        lines.append(f"| {r['scenario_id']} | {r['architecture']} | {r['status']} | {e['scores']['safety'] if e else 'não avaliado'} | {e['referral_adequacy'] if e else 'não avaliado'} | {e['critical_error'] if e else 'não avaliado'} |")
    lines += ["", "## O que este piloto permite concluir", "", "Verificar se as três condições executam chamadas reais, preservam respostas e permitem medir consumo, duração, chamadas, ferramentas e transferências. Identificar falhas de instrumentos e respostas a revisar. Comparações numéricas são descritivas: dez casos intencionais e uma repetição não sustentam superioridade geral de arquitetura.", "", "A flag de encaminhamento vem da mesma regra de entrada nas três condições; sua concordância com os rótulos provisórios não mede superioridade arquitetural. O juiz avalia o cumprimento no texto separadamente. Anexos são apenas metadados, sem avaliação de OCR/visão. Não há preços, pedidos ou estoque reais. Avaliação profissional efetivamente realizada: nenhuma.","", "## Próxima validação", "", "Os dois farmacêuticos devem revisar os casos/rubrica/encaminhamento e avaliar independentemente as mesmas respostas cegas. Preservar notas anteriores a consenso. O formulário e a importação já estão preparados; métricas de concordância só têm significado quando houver pares avaliados. Depois revisar instrumentos, validar integração API/banco, ampliar os cenários e congelar o protocolo definitivo.", "", "Arquivos locais: manifest.json, execution-order.csv, runs.csv, eventos por tentativa, respostas integrais, avaliações separadas, quality-scores.csv e formulário farmacêutico. As chaves não integram esses arquivos."]
    path=folder/"resultado_piloto.md";path.write_text("\n".join(lines)+"\n");print(path)

if __name__=="__main__":main()
