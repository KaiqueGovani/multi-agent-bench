#!/usr/bin/env python3
"""Version-aware descriptive comparison, preserving source cohorts and unknowns."""
from __future__ import annotations
import argparse,json,statistics
from pathlib import Path
from collections import Counter
from run_research_pilot import dump,write_csv,sha
from judge_automated_pilots import read_jsonl
from app.experiments.methodology import reliability,DIMENSIONS

def compare(old,regrade,new,output):
    output.mkdir(parents=True,exist_ok=True)
    datasets={'v4-original':read_jsonl(old/'aggregated-evaluations.jsonl'),
              'v4-evidence-only-diagnostic':read_jsonl(regrade/'reference-only-diagnostic.jsonl'),
              'v4-responses-v5-full-instrument':read_jsonl(regrade/'aggregated-evaluations.jsonl'),
              'v5-new-live-pilot':read_jsonl(new/'aggregated-evaluations.jsonl')}
    if any(len(rows)!=150 for rows in datasets.values()):raise ValueError('All four comparison stages must contain the complete planned 150 attempts')
    keys=[(r['scenario_id'],r['architecture'],r['repetition']) for r in datasets['v4-original']]
    stages={name:{(r['scenario_id'],r['architecture'],r['repetition']):r for r in rows} for name,rows in datasets.items()}
    if any(set(rows)!=set(keys) for rows in stages.values()):raise ValueError('Unpaired scenario/architecture/repetition keys')
    summaries=[];paired=[]
    for name,rows in datasets.items():
        for arch in dict.fromkeys(r['architecture'] for r in rows):
            rr=[r for r in rows if r['architecture']==arch];cases=list(dict.fromkeys(r['scenario_id'] for r in rr))
            rel=reliability([[r['task_success'] for r in rr if r['scenario_id']==c] for c in cases],len(cases))
            summaries.append({'stage':name,'architecture':arch,'planned':50,'technical_successes':sum(r['success'] for r in rr),'task_successes':sum(r['task_success'] is True for r in rr),'task_failures':sum(r['task_success'] is False for r in rr),**rel})
            for case in cases:
                cc=[r for r in rr if r['scenario_id']==case];known=[r['task_success'] for r in cc if r['task_success'] is not None]
                row={'stage':name,'scenario_id':case,'architecture':arch,'task_successes':sum(x is True for x in known),'known':len(known),'unknown':5-len(known),'task_success_rate':sum(known)/len(known) if known else None}
                if name!='v4-evidence-only-diagnostic':
                    for metric in ('end_to_end_latency_ms','total_tokens','model_requests'):
                        values=[r.get(metric) for r in cc if r['success'] and r.get(metric) is not None];row[metric+'_median']=statistics.median(values) if values else None
                    for d in DIMENSIONS:
                        values=[r['evaluation']['quality'][d] for r in cc if r.get('evaluation') and r['evaluation']['quality'][d] is not None];row[d+'_median']=statistics.median(values) if values else None
                paired.append(row)
    transitions=[]
    names=list(datasets)
    for left,right in zip(names,names[1:]):
        counts=Counter();changed=[]
        for key in keys:
            a,b=stages[left][key]['task_success'],stages[right][key]['task_success'];counts[str(a)+' -> '+str(b)]+=1
            if a!=b:changed.append({'scenario_id':key[0],'architecture':key[1],'repetition':key[2],'before':a,'after':b})
        transitions.append({'before_stage':left,'after_stage':right,'counts':dict(counts),'changed_classifications':changed,
            'interpretation':'diagnostic source-rule arithmetic' if right==names[1] else 'revised judge and clarified criterion/rubric on same replies' if right==names[2] else 'new input version plus ordinary temporal/generation variability; not isolated causal input effect'})
    write_csv(output/'stage-metrics.csv',summaries);write_csv(output/'paired-scenario-metrics.csv',paired);dump(output/'classification-transitions.json',transitions)
    old_m=json.loads((old/'manifest.json').read_text());new_m=json.loads((new/'manifest.json').read_text())
    unchanged=old_m['configuration']['role_prompts']==new_m['configuration']['role_prompts']
    dump(output/'comparison-provenance.json',{'source_folders':{k:str(p) for k,p in [('old',old),('regrade',regrade),('new',new)]},'architecture_role_prompts_unchanged':unchanged,
        'source_hashes':{str(p/'aggregated-evaluations.jsonl'):sha((p/'aggregated-evaluations.jsonl').read_bytes()) for p in (old,regrade,new)},
        'quality_comparability':'Operational correctness definition clarified in v5; no claim that ordinal changes measure architecture-only improvement.',
        'no_inferential_tests':True,'human_review_performed':False})
    lines=['# Comparação dos lotes v4 e v5\n','Quatro etapas preservam os resultados anteriores e distinguem revisão de exigências, novo instrumento semântico e novas execuções. O diagnóstico de evidências mantém rótulos semânticos antigos e não substitui uma reavaliação completa.\n',
        '| Etapa | Arquitetura | Técnicos | Sucessos | Falhas | Desconhecidos | pass^1 | pass^5 | Cobertura de cenários |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summaries:
        fmt=lambda v:'NA' if v is None else f'{v:.3f}'
        lines.append(f"| {r['stage']} | {r['architecture']} | {r['technical_successes']}/50 | {r['task_successes']} | {r['task_failures']} | {r['unknown']} | {fmt(r['pass_1'])} | {fmt(r['pass_5'])} | {r['complete_scenarios']}/10 |")
    lines+=['\nPrompts arquiteturais preservados: '+str(unchanged)+'. Não foram ajustados para acertar os dez casos.',
        '\nDistribuições e critérios por cenário ficam nos relatórios dos lotes e nos CSVs pareados. Gabarito e rubrica mudaram: não interpretar diferenças como superioridade geral ou melhora exclusivamente arquitetural. A diferença entre respostas antigas e novas não isola causalmente descritores de anexos de variação temporal ou de geração.',
        '\nO novo piloto continua descritivo, com ferramentas controladas, indicação textual provisória de encaminhamento e execução por processos/arquivos, sem HTTP/banco ao vivo. Revisão farmacêutica permanece opcional e não realizada. A matriz de 600 não foi iniciada.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n')
    return summaries
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('regrade',type=Path);p.add_argument('new',type=Path);p.add_argument('output',type=Path);a=p.parse_args();compare(a.old,a.regrade,a.new,a.output);print('Comparison exported')
