#!/usr/bin/env python3
"""Export only quantitative benchmark tables and public provenance, never transcripts.

Requires completed frozen analysis. This downstream export does not modify the
reference, primary labels, source runs or evaluator. Input directory is restricted.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,statistics
from pathlib import Path
from collections import Counter

ARCHES=('centralized_orchestration','structured_workflow','decentralized_swarm')
NAMES=dict(zip(ARCHES,('Centralizada','Workflow','Swarm')))
DIMS=('intent_adherence','operational_correctness','safety','completeness','clarity')
MODES={
 'capability_limit':'Limitação', 'request_information':'Esclarecimento',
 'controlled_fact':'Fato controlado','controlled_fact_and_limit':'Fato e limitação',
 'professional_referral':'Encaminhamento',
 'professional_referral_and_limit':'Encaminhamento e limitação',
 'professional_referral_and_information':'Encaminhamento e esclarecimento'}
def load(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
def med(xs):
 xs=[x for x in xs if x is not None]
 return statistics.median(xs) if xs else None
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rows):
 if not rows:return
 keys=sorted(set().union(*(r.keys() for r in rows)))
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x):return 'NA' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
def table(rows,columns):
 return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+''.join('| '+' | '.join(num(r.get(k)) for k in columns)+' |\n' for r in rows)
def main():
 a=argparse.ArgumentParser();a.add_argument('input',type=Path);a.add_argument('output',type=Path);args=a.parse_args()
 p=args.input.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 manifest=load(p/'manifest.json');gate=load(p/'readiness.json');rs=lines(p/'aggregated-evaluations.jsonl')
 if gate['attempts']!=600 or len(rs)!=600:raise ValueError('Only a complete 600-unit collection may be exported')
 if not gate['definitive_collection_complete']:raise ValueError('Collection integrity gate is not complete')
 transition=load(p/'parallel-judging/transition.json')
 if not transition.get('original_primary_prefix_preserved') or not transition.get('primary_response_ids_unique'):raise ValueError('Parallel consolidation integrity is unverified')
 dispatch={k:transition[k] for k in ('created_at','requested_workers','sequential_terminal_responses','remaining_responses','generator_order_changed','model_rubric_gold_changed','transition_completed_at','boundary_had_no_request','partition','merged_at','parallel_valid','parallel_unknown','original_primary_prefix_preserved','primary_response_ids_unique','raw_worker_journals_preserved','journal_merge_order')}
 dump(out/'judge-dispatch-amendment.json',dispatch)
 # Explicit table whitelist. Criterion text and review reasons are restricted.
 for name in ('metrics.csv','architecture-stratum-metrics.csv','quality-distributions.csv','failure-diagnostic-summary.csv'):
  (out/name).write_bytes((p/name).read_bytes())
 crit=list(csv.DictReader((p/'criterion-distributions.csv').open()))
 csvwrite(out/'criterion-counts.csv',[{k:r[k] for k in ('architecture','scenario_id','criterion_id','assessment_target','met','not_met','unknown')} for r in crit])
 for name in ('readiness.json','latency-distributions.json','randomization-check.json','analysis-provenance.json','recheck-analysis.json','initial-input-equivalence.json'):
  dump(out/name,load(p/name))
 # Execution order identifies experimental cases/units only, never original chats.
 (out/'execution-order.csv').write_bytes((p/'execution-order.csv').read_bytes())
 safe_cases=[{k:c[k] for k in ('id','stratum','difficulty','expected_resolution_mode','professional_review_required','sha256')} for c in manifest['cases']]
 dump(out/'provenance.json',{'export_version':'quantitative-export-v1','export_script_sha256':h(Path(__file__)),'plan':'matrix40-v1-final','manifest_sha256':h(p/'manifest.json'),
  'dataset_version':manifest['dataset_version'],'cohort':manifest['cohort'],'created_at':manifest['created_at'],
  'source_commit_base':manifest['commit'],'code_hashes':manifest['code_hashes'],'asset_hashes':{Path(k).name:v for k,v in manifest['asset_hashes'].items()},
  'dependencies':manifest['dependency_versions'],'configuration':manifest['configuration'],
  'evaluation_plan':{k:v for k,v in manifest['evaluation_plan'].items() if k!='calibration_folder'},
  'cases':safe_cases,'original_chats_or_reverse_maps_published':False,'primary_labels_changed':False,'human_review_performed':False})
 # Read frozen per-case numeric medians; repetitions are nested in scenarios.
 groups=[]
 for row in csv.DictReader((p/'metrics.csv').open()):
  groups.append({k:(None if v=='' else float(v) if k.endswith('_median') else v) for k,v in row.items()})
 summaries=[]
 for arch in ARCHES:
  rr=[r for r in rs if r['architecture']==arch];gg=[g for g in groups if g['architecture']==arch]
  base={'architecture':arch,'planned':200,'technical_successes':sum(r.get('success',False) for r in rr),'task_successes':sum(r['task_success'] is True for r in rr),'task_failures':sum(r['task_success'] is False for r in rr),'task_unknown':sum(r['task_success'] is None for r in rr),
   'content_successes':sum(r['content_success'] is True for r in rr),'content_evaluable':sum(r['content_success'] is not None for r in rr),
   'procedure_applicable':sum(r['procedure_applicable'] for r in rr),'procedure_successes':sum(r['procedure_applicable'] and r['procedure_compliance'] is True for r in rr),'procedure_evaluable':sum(r['procedure_applicable'] and r['procedure_compliance'] is not None for r in rr)}
  for k in ('end_to_end_latency_ms','total_tokens','model_requests','actual_agents','domain_tool_calls','coordination_tool_calls'):
   base[k+'_median_of_case_medians']=med([g[k+'_median'] for g in gg])
  base['known_task_success_rate']=base['task_successes']/(200-base['task_unknown']) if base['task_unknown']<200 else None
  summaries.append(base)
 modes=[]
 for mode in sorted({r['expected_resolution_mode'] for r in rs}):
  for arch in ARCHES:
   rr=[r for r in rs if r['architecture']==arch and r['expected_resolution_mode']==mode]
   gg=[g for g in groups if g['architecture']==arch and g['expected_resolution_mode']==mode]
   bycase={cid:[r['task_success'] for r in rr if r['scenario_id']==cid] for cid in sorted({r['scenario_id'] for r in rr})}
   complete=[v for v in bycase.values() if len(v)==5 and all(x is not None for x in v)]
   modes.append({'architecture':arch,'expected_resolution_mode':mode,'scenario_count':len(bycase),'planned':len(bycase)*5,'executed':len(rr),
    'task_successes':sum(r['task_success'] is True for r in rr),'task_failures':sum(r['task_success'] is False for r in rr),'task_unknown':sum(r['task_success'] is None for r in rr),
    'complete_scenarios':len(complete),'pass_1_complete':sum(sum(v)/5 for v in complete)/len(complete) if complete else None,'pass_5_complete':sum(all(v) for v in complete)/len(complete) if complete else None,
    'latency_ms_median_of_case_medians':med([g['end_to_end_latency_ms_median'] for g in gg]),'tokens_median_of_case_medians':med([g['total_tokens_median'] for g in gg])})
 csvwrite(out/'architecture-summary.csv',summaries);csvwrite(out/'resolution-mode-summary.csv',modes)
 csvwrite(out/'assessment-coverage.csv',[{'architecture':a,'planned':200,'primary_schema_valid':sum(r['evaluation'] is not None for r in rs if r['architecture']==a),'primary_evaluation_missing':sum(r['evaluation'] is None for r in rs if r['architecture']==a),'task_unknown':sum(r['task_success'] is None for r in rs if r['architecture']==a)} for a in ARCHES])
 quality=[];criticals=[]
 for arch in ARCHES:
  rr=[r for r in rs if r['architecture']==arch]
  for d in DIMS:
   c=Counter(r['evaluation']['quality'][d] if r['evaluation'] else None for r in rr)
   quality.append({'architecture':arch,'dimension':d,'planned':200,'unknown':c[None],**{'score_'+str(i):c[i] for i in range(1,6)}})
  for source in ('objective_checks','evaluation'):
   for vid in ('V1','V2','V3','V4'):
    applicable=[r for r in rr if r[source] is not None]
    criticals.append({'architecture':arch,'source':source,'violation_id':vid,'assessed':len(applicable),'flagged_responses':sum(any(v['violation_id']==vid for v in r[source]['critical_violations']) for r in applicable)})
 csvwrite(out/'quality-summary.csv',quality);csvwrite(out/'critical-violation-counts.csv',criticals)
 paired=[]
 for arch in ARCHES[1:]:
  for k in ('end_to_end_latency_ms','total_tokens','model_requests'):
   pairs=[]
   for cid in {g['scenario_id'] for g in groups}:
    c=next(g for g in groups if g['scenario_id']==cid and g['architecture']==ARCHES[0]);v=next(g for g in groups if g['scenario_id']==cid and g['architecture']==arch)
    x=c[k+'_median'];y=v[k+'_median']
    if x is not None and y is not None:pairs.append((y-x,y/x if x else None))
   paired.append({'architecture_vs_centralized':arch,'metric':k,'paired_scenarios':len(pairs),'median_paired_difference':med([v[0] for v in pairs]),'median_paired_ratio':med([v[1] for v in pairs])})
 csvwrite(out/'paired-comparisons.csv',paired)
 # Physical inference attempts and observed usage, with coverage. The frozen
 # analyzer's pilot projection is preserved privately but is unnecessary here.
 agent_events=[e for r in rs for e in lines(p/r['unit_id']/'events.jsonl') if e['eventFamily']=='model']
 started=[e for e in agent_events if e['eventName']=='started']
 completed=[e for e in agent_events if e['eventName']=='completed']
 measured=[e for e in completed if isinstance(e['payload'].get('usage'),dict) and all(e['payload']['usage'].get(k) is not None for k in ('inputTokens','outputTokens','totalTokens'))]
 agent_cost={'requests_started':len(started),'requests_completed':len(completed),'requests_failed':sum(e['eventName']=='failed' for e in agent_events),'requests_with_usage':len(measured),'cost_usd':None,
  **{'known_measured_'+k:sum(e['payload']['usage'][v] for e in measured) for k,v in [('input_tokens','inputTokens'),('output_tokens','outputTokens'),('total_tokens','totalTokens')]}}
 attempts=lines(p/'judge-attempts.jsonl');judge_phases={}
 for phase in ('primary','recheck'):
  aa=[x for x in attempts if x.get('phase')==phase];cc=[x for x in aa if x.get('event')=='completed'];mm=[x for x in cc if x.get('usage') and all(x['usage'].get(k) is not None for k in ('inputTokens','outputTokens','totalTokens'))]
  judge_phases[phase]={'requests_started':sum(x['event']=='started' for x in aa),'requests_completed':len(cc),'requests_failed':sum(x['event']=='failed' for x in aa),'requests_with_usage':len(mm),'format_repair_requests':sum(x['event']=='started' and x.get('format_repair',0)>0 for x in aa),'cost_usd':None,
   **{'known_measured_'+k:sum(x['usage'][v] for x in mm) for k,v in [('input_tokens','inputTokens'),('output_tokens','outputTokens'),('total_tokens','totalTokens')]}}
 connectivity_path=p.parent/'connectivity-final/connectivity-summary.json'
 checks=load(connectivity_path)['checks'] if connectivity_path.exists() else []
 measured_checks=[x for x in checks if x.get('usage')]
 judge={'export_version':'measured-resource-export-v1','agents':agent_cost,'judge':judge_phases,
  'connectivity':{'requests':len(checks),'requests_with_usage':len(measured_checks),**{'known_measured_'+k:sum(x['usage'].get(v,0) for x in measured_checks) for k,v in [('input_tokens','inputTokens'),('output_tokens','outputTokens'),('total_tokens','totalTokens')]}},
  'technical_calibration_new_requests':0,'technical_calibration_reused_fixtures':20,'pricing':'Unverified; monetary cost unavailable. Known measured tokens are provider usage, not a guarantee of the final bill. Missing usage is not zero.'}
 dump(out/'resource-consumption.json',judge)
 re=load(p/'recheck-analysis.json')
 result={'plan':'matrix40-v1-final','generated':600,'technical_successes':gate['successful'],'primary_valid':gate['evaluated'],'task_successes':sum(r['task_success'] is True for r in rs),'task_failures':sum(r['task_success'] is False for r in rs),'task_unknown':sum(r['task_success'] is None for r in rs),'architectures':summaries,'readiness':gate,'recheck':re,'resources':judge}
 dump(out/'results-summary.json',result)
 report='# Metodologia e resultados — 40 cenários reais\n\n'
 report+=f'Plano congelado **matrix40-v1-final**: 600/600 unidades executadas; {gate["successful"]} términos técnicos bem-sucedidos; {gate["evaluated"]} avaliações primárias válidas. Sucesso no gabarito: **{result["task_successes"]}**; falha: **{result["task_failures"]}**; desconhecido: **{result["task_unknown"]}**. O relatório preserva as avaliações primárias.\n\n'
 if gate['evaluated']<gate['successful']:
  report+=f'As 600 respostas foram processadas pelo julgador; {gate["successful"]-gate["evaluated"]} não obtiveram avaliação primária válida sob as regras congeladas. Os campos dependentes do juiz permanecem ausentes e não são substituídos por zero ou por rechecagens. Uma tarefa ainda pode ser classificada como falha por evidência obrigatória ausente, independentemente da indisponibilidade do juiz. A cobertura do juiz e os desconhecidos de tarefa são, portanto, contagens diferentes.\n\n'
 if not gate['definitive_analysis_ready']:
  report+='O gate estrito de prontidão integral da análise **não foi aprovado**. A coleta completa e as estatísticas observadas são preservadas, com as pendências de cobertura/coerência/rechecagem detalhadas em readiness.json. Não apresentar este lote como avaliação integralmente validada, nem modificar julgamentos ou gabaritos para converter o gate em aprovação.\n\n'
 report+='## Desenho e escopo\n\n40 cenários derivados de conversas reais, oito por estrato e dificuldade 15/15/10, comparados em três arquiteturas com cinco repetições. São 40 casos pareados; as 600 unidades não são 600 casos independentes. Modelos, parâmetros, regras, fontes e contexto inicial são comuns, com papéis e circulação de contexto determinados pela arquitetura. O protocolo completo está em [experiments/real-conversations-v1/README.md](../../../experiments/real-conversations-v1/README.md).\n\n'
 report+='A seleção é intencional na partição test, com 40 grupos conhecidos distintos e sem sobreposição conhecida com os sete grupos de desenvolvimento. Prefixos disponíveis antes do corte foram revisados, sem mensagens futuras. Mídias só fornecem metadados. O catálogo e FAQ são simulados; operações comerciais e transferência humana não estão integradas.\n\n'
 report+='A geração das 600 unidades ocorreu sequencialmente na ordem congelada. Após sua conclusão, por solicitação do autor, as '+str(dispatch['remaining_responses'])+' avaliações restantes foram distribuídas entre quatro processos; as '+str(dispatch['sequential_terminal_responses'])+' anteriores foram preservadas. A transição não cancelou chamadas em andamento. Cada resposta teve um único proprietário, com a mesma função, modelo, parâmetros, rubrica e referência calibrados. Essa emenda de despacho do juiz não modifica as latências dos agentes. Registros consolidados e por processo representam as mesmas chamadas físicas; o consumo usa somente o registro consolidado.\n\n'
 report+='Em 25 casos a resolução principal prevista é limitação/esclarecimento; sete incluem fatos controlados e oito encaminhamento. O cumprimento do gabarito não comprova compra, entrega ou resultado clínico. Gabaritos e dificuldades são técnicos, sem anotação farmacêutica. O detector já fornece a indicação provisória: a medida é conformidade, não identificação clínica autônoma.\n\n'
 report+='## Resultados por arquitetura\n\n'+table(summaries,['architecture','planned','technical_successes','task_successes','task_failures','task_unknown','known_task_success_rate','end_to_end_latency_ms_median_of_case_medians','total_tokens_median_of_case_medians'])
 report+='\nLatência em milissegundos: mediana das 40 medianas por cenário, incluindo inicialização do processo/runtime e arquivos. Não inclui HTTP/banco de produção. Consumo usa tokens registrados pelo provedor; texto de comunicação não equivale a tokens faturados. Falhas técnicas têm distribuição própria.\n\n'
 report+='## Conteúdo e procedimento\n\n'+table(summaries,['architecture','content_successes','content_evaluable','procedure_applicable','procedure_successes','procedure_evaluable'])
 report+='\nHá 20 fontes obrigatórias em 19 cenários, além de 33 opcionais. Procedimento sem consulta obrigatória é não aplicável. A nota de correção operacional trata o conteúdo final; o verificador v5.3 avalia consulta, argumentos e integridade do retorno. São medidas distintas e não devem ser somadas como falhas independentes.\n\n'
 strata=list(csv.DictReader((p/'architecture-stratum-metrics.csv').open()))
 report+='## Confiabilidade das cinco repetições\n\n'+table([r for r in strata if r['stratum']=='all'],['architecture','complete_scenarios','pass_1','pass_5','pass_1_lower','pass_1_upper','pass_5_lower','pass_5_upper','unknown'])
 report+='\npass^1 é a média da proporção de sucessos nas cinco repetições por cenário completamente avaliável. pass^5 é a proporção desses cenários com as cinco respostas aprovadas. Limites inferior/superior abrangem desconhecidos no conjunto planejado; são limites descritivos, não intervalos de confiança.\n\n'
 report+='## Modo previsto de resolução\n\n'+table(modes,['architecture','expected_resolution_mode','scenario_count','task_successes','task_failures','task_unknown','pass_1_complete','pass_5_complete'])
 report+='\nEsses rótulos descrevem o objetivo previsto no gabarito, não uma categorização automática da resposta observada. O pequeno número de casos em alguns modos limita comparações.\n\n'
 report+='## Qualidade e encaminhamento\n\n'+table(quality,['architecture','dimension','score_1','score_2','score_3','score_4','score_5','unknown'])
 report+='\n'+table([r for r in strata if r['stratum']=='all'],['architecture','referral_TP','referral_TN','referral_FP','referral_FN','referral_unknown','transfer_claimed_in_response_count','transfer_executed_by_judge_count'])
 report+='\nOs rótulos de encaminhamento comparam recomendação explícita ao gabarito técnico. FP não estabelece inadequação clínica; indicação e validação clínica não foram avaliadas. Alegar contato humano não prova execução. A segurança de 1–5 é julgamento automatizado sob a rubrica, não segurança clínica validada.\n\n'
 report+='## Comparações pareadas de consumo e latência\n\n'+table(paired,['architecture_vs_centralized','metric','paired_scenarios','median_paired_difference','median_paired_ratio'])
 report+='\nDiferenças e razões são calculadas primeiro para cada cenário e depois resumidas. Razão de medianas globais e mediana das razões pareadas são estimativas distintas. A comparação é descritiva, sem testes confirmatórios ou conclusão geral de superioridade.\n\n'
 report+='## Auditoria, consumo e limitações\n\n'+f'Calibração técnica: 20 fixtures previamente aprovadas, sem alteração da configuração. Rechecagem fixa: {re["evaluated"]}/15 avaliações; {re["paired_evaluations"]} pares completos; {re["success_classification_changes"]} mudanças de classificação. A primeira avaliação válida permanece principal. A auditoria é limitada, sem estimativa de acurácia clínica.\n\n'
 report+='```json\n'+json.dumps(gate,ensure_ascii=False,indent=2)+'\n```\n\n'
 report+='Consumo por fase, separado de resultados históricos e calibração já realizada:\n\n```json\n'+json.dumps(judge,ensure_ascii=False,indent=2)+'\n```\n\n'
 report+='Não foram realizadas avaliações farmacêuticas. Dois revisores podem avaliar independentemente o mesmo subconjunto focalizado em pacotes cegos; avaliações, desacordos e concordância devem ser apresentados separadamente e só após recebimento dos pareceres reais. Geração por processos/arquivos, amostragem intencional, fontes simuladas, ausência de leitura multimodal e gabaritos técnicos delimitam a generalização. O piloto anterior permanece lote próprio.\n\n'
 report+='Os arquivos públicos são quantitativos, sem respostas, históricos ou mapas reversíveis. O ZIP de contexto privado dos autores conserva entradas revisadas, gabaritos, registros individuais e snapshots, excluindo chaves, base original, mídias e mapa cliente–cenário. Detalhes de diagnóstico de processo representam indicadores candidatos quando não confirmados objetivamente; não demonstram causalidade ou raciocínio interno.\n'
 report+='\n## Figuras para a escrita\n\nAs versões SVG e PNG com 300 dpi estão em figures/. As figuras usam as tabelas deste relatório e não introduzem inferência estatística adicional.\n\n'
 report+='A aplicação complementar de Friedman, Wilcoxon e Holm, incluindo cobertura, efeitos e intervalos exploratórios, consta de [ANALISE_PAREADA_COMPLEMENTAR.md](ANALISE_PAREADA_COMPLEMENTAR.md). Os detalhes operacionais dessa análise foram registrados após a coleta; ela não altera rótulos nem gates congelados e não constitui um plano confirmatório integralmente pré-registrado.\n\n'
 for stem,title in [('01_sucesso_tarefa','Cumprimento do gabarito'),('02_conteudo_procedimento','Conteúdo e procedimento'),('03_latencia_tokens','Latência e tokens por cenário'),('04_qualidade','Distribuições de qualidade'),('05_estratos','Sucesso por estrato')]:
  report+='!['+title+'](figures/'+stem+'.png)\n\n'
 (out/'RELATORIO_METODOLOGIA_RESULTADOS.md').write_text(report)
 (out/'README.md').write_text('# Resultados públicos — matrix40-v1-final\n\nLeia `RELATORIO_METODOLOGIA_RESULTADOS.md` e `results-summary.json`. As tabelas contêm indicadores quantitativos do lote, sem conversas individuais. A reprodução exata depende do pacote restrito dos autores e das dependências congeladas em `provenance.json`.\n\n`metrics.csv`: 120 grupos cenário × arquitetura. `architecture-stratum-metrics.csv`: arquitetura × estrato e total. `resolution-mode-summary.csv`: modo previsto × arquitetura. `quality-summary.csv`: distribuições 1–5, sem nota global. `paired-comparisons.csv`: diferenças e razões das medianas por cenário. `criterion-counts.csv`: critérios sem enunciados. `critical-violation-counts.csv`: sinalizações separadas por fonte, com possível sobreposição. `readiness.json` e `recheck-analysis.json`: integridade e auditoria.\n\n`human_review_performed=false`: nenhum julgamento farmacêutico ou validação clínica. Custos monetários não verificados permanecem indisponíveis.\n')
 dump(out/'PUBLIC_FILES_MANIFEST.json',{'files':{q.name:{'bytes':q.stat().st_size,'sha256':h(q)} for q in sorted(out.iterdir()) if q.is_file() and q.name!='PUBLIC_FILES_MANIFEST.json'},'conversations_published':False})
 print(json.dumps({k:v for k,v in result.items() if k in ('generated','technical_successes','primary_valid','task_successes','task_failures','task_unknown')}))
if __name__=='__main__':main()
