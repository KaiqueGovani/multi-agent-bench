#!/usr/bin/env python3
"""Complementary paired statistics; never changes the frozen descriptive analysis."""
import argparse,json,csv,hashlib,itertools,statistics
from pathlib import Path
from datetime import datetime,UTC
import numpy as np
import scipy
from scipy.stats import rankdata,friedmanchisquare,wilcoxon,PermutationMethod
ARCHES=('centralized_orchestration','structured_workflow','decentralized_swarm')
DIMS=('intent_adherence','operational_correctness','safety','completeness','clarity')
METRICS=('end_to_end_latency_ms','total_tokens',*DIMS)
SEED=20261011;RESAMPLES=99999;BOOTSTRAPS=20000
def write_csv(path,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def paired_data(rows,metric):
 values={};excluded=[]
 for cid in sorted({r['scenario_id'] for r in rows}):
  triples=[]
  for arch in ARCHES:
   rr=[r for r in rows if r['scenario_id']==cid and r['architecture']==arch]
   vals=[(r['evaluation']['quality'][metric] if r.get('evaluation') else None) if metric in DIMS else r.get(metric) for r in rr]
   if len(vals)!=5 or any(v is None for v in vals) or not all(r['success'] for r in rr):break
   triples.append(statistics.median(vals))
  if len(triples)==3:values[cid]=triples
  else:excluded.append(cid)
 return np.asarray(list(values.values()),dtype=float),list(values),excluded
def friedman_permutation(data,observed,seed):
 ranks=rankdata(data,axis=1);n,k=ranks.shape
 correction=1-sum(sum(v**3-v for v in np.unique(row,return_counts=True)[1]) for row in ranks)/(n*(k**3-k))
 perms=np.asarray(list(itertools.permutations(range(k))))
 rng=np.random.default_rng(seed);extreme=0;done=0
 while done<RESAMPLES:
  batch=min(2048,RESAMPLES-done)
  chosen=perms[rng.integers(0,len(perms),size=(batch,n))]
  sums=np.take_along_axis(np.broadcast_to(ranks,(batch,n,k)),chosen,axis=2).sum(axis=1)
  stats=(12/(n*k*(k+1))*(sums*sums).sum(axis=1)-3*n*(k+1))/correction
  extreme+=int(np.count_nonzero(stats>=observed-1e-10));done+=batch
 return (extreme+1)/(RESAMPLES+1)
def holm(ps):
 result=np.empty(len(ps));maximum=0
 for step,index in enumerate(np.argsort(ps)):
  maximum=max(maximum,(len(ps)-step)*ps[index]);result[index]=min(1,maximum)
 return result
def analyze(folder,out):
 rows=[json.loads(s) for s in (folder/'aggregated-evaluations.jsonl').read_text().splitlines()]
 assert len(rows)==600
 out.mkdir(parents=True,exist_ok=True);global_rows=[];pair_rows=[];coverage={}
 for metric_index,metric in enumerate(METRICS):
  values,ids,excluded=paired_data(rows,metric);coverage[metric]={'included_scenarios':ids,'excluded_incomplete_scenarios':excluded}
  n=len(values);within_equal=n>0 and np.all(values==values[:,[0]])
  if not n:global_rows.append({'metric':metric,'paired_scenarios':0,'status':'no_complete_pairs'});continue
  if within_equal:
   statistic=0.;p=1.;pperm=1.;status='all_architectures_equal_within_every_complete_scenario; no identifiable rank contrast'
  else:
   test=friedmanchisquare(*values.T);statistic=float(test.statistic);p=float(test.pvalue);pperm=friedman_permutation(values,statistic,SEED+metric_index);status='calculated'
  global_rows.append({'metric':metric,'planned_scenarios':40,'paired_scenarios':n,'excluded_incomplete_scenarios':40-n,'friedman_statistic':statistic,'friedman_p_chi_square':p,'friedman_p_permutation_sensitivity':pperm,'kendall_W':statistic/(n*2),'posthoc_triggered':p<.05,'status':status})
  local=[]
  # Preserve the documented global Friedman trigger; permutation is sensitivity.
  if p<.05:
   for pair_index,(a,b) in enumerate(itertools.combinations(range(3),2)):
    difference=np.round(values[:,b]-values[:,a],9)
    nz=difference[difference!=0];seed=SEED+100*metric_index+pair_index
    if not len(nz):stat=0.;pw=1.;method='all_zero_differences; no rank contrast'
    else:
     exact=len(np.unique(np.abs(nz)))==len(nz) and len(nz)<=50
     method='exact_without_ties_or_zeros' if exact else 'sign_permutation_99999_resamples_or_exhaustive_if_smaller'
     result=wilcoxon(nz,zero_method='wilcox',alternative='two-sided',method='exact' if exact else PermutationMethod(n_resamples=RESAMPLES,batch=4096,rng=np.random.default_rng(seed)))
     stat=float(result.statistic);pw=float(result.pvalue)
    ranked=rankdata(np.abs(nz));positive=float(ranked[nz>0].sum());negative=float(ranked[nz<0].sum())
    effect=(positive-negative)/(positive+negative) if len(nz) else 0.
    rng=np.random.default_rng(seed+10000);boots=np.median(difference[rng.integers(0,n,size=(BOOTSTRAPS,n))],axis=1)
    low,high=np.quantile(boots,[.025,.975])
    local.append({'metric':metric,'architecture_a':ARCHES[a],'architecture_b':ARCHES[b],'orientation':'b_minus_a','paired_scenarios':n,'nonzero_pairs':len(nz),'zero_pairs':n-len(nz),'wilcoxon_statistic':stat,'p_unadjusted':pw,'method':method,'rank_biserial_b_minus_a':effect,'median_paired_difference':float(np.median(difference)),'median_difference_bootstrap_95_low':float(low),'median_difference_bootstrap_95_high':float(high)})
   for row,adjusted in zip(local,holm([r['p_unadjusted'] for r in local])):row.update(p_holm_within_metric=float(adjusted),significant_within_metric=bool(adjusted<.05))
   pair_rows+=local
 write_csv(out/'friedman-global.csv',global_rows);write_csv(out/'wilcoxon-holm-pairs.csv',pair_rows)
 provenance={'version':'complementary-paired-analysis-v1','implemented_after_generation':True,'interpretation':'Complementary and exploratory; exact operational choices recorded after collection; does not amend frozen primary labels or readiness gates. Broad Friedman/Wilcoxon/Holm procedure was already requested by the author.','metrics':list(METRICS),'unit':'complete scenario triple: median of five fully observed repetitions per architecture; no imputation','alpha':.05,'multiplicity':'Holm across the three pairs within each metric; no family correction across the seven global metrics; no global confirmatory winner claim','friedman':'tie-corrected chi-square p used for documented post-hoc trigger; Monte Carlo within-scenario label permutation reported separately because only three conditions','permutation_resamples':RESAMPLES,'wilcoxon':'two-sided; remove zero differences; exact only without absolute-rank ties, otherwise sign permutation; differences rounded to 1e-9 original metric units','effects':'Kendall W global; matched rank-biserial correlation oriented b-a','bootstrap':'20000 paired resamples of scenarios, percentile 95% interval for median difference; conditional and exploratory; selected sample is not a random population sample','seed':SEED,'dependencies':{'numpy':np.__version__,'scipy':scipy.__version__},'source_sha256':sha(Path(__file__)),'input_sha256':sha(folder/'aggregated-evaluations.jsonl'),'source_protocol_sha256':sha(Path(__file__).resolve().parents[1]/'experiments/pilots-v4/reference-experimental-protocol.md'),'coverage':coverage,'generated_at':datetime.now(UTC).isoformat(),'binary_outcomes_inferential_tests_performed':False,'original_primary_labels_changed':False}
 (out/'paired-statistics-provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
 def table(rr,keys):return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+''.join('| '+' | '.join(f'{r[k]:.6g}' if isinstance(r.get(k),float) else str(r.get(k,'')) for k in keys)+' |\n' for r in rr)
 report='# Análise pareada complementar\n\nO procedimento geral Friedman, seguido de Wilcoxon e Holm, já constava da solicitação autoral e do protocolo documental. A implementação, o tratamento de empates/ausências e a lista operacional de sete métricas foram registrados **após a coleta**; estes resultados são complementares e exploratórios. Não modificam rótulos, gabaritos, código congelado ou gates de prontidão. Não apresentar como plano confirmatório integralmente pré-registrado.\n\n'
 report+='Cada observação é uma mediana de cinco repetições por cenário/arquitetura. Só entram trios de arquiteturas com cinco valores observados em cada condição. Exclusões são explícitas em paired-statistics-provenance.json. As 600 execuções não são 600 amostras independentes. Casos de conteúdo qualitativo dependem do juiz técnico; não representam validação clínica.\n\n'
 report+=table(global_rows,['metric','paired_scenarios','friedman_statistic','friedman_p_chi_square','friedman_p_permutation_sensitivity','kendall_W','posthoc_triggered','status'])
 report+='\nA aproximação qui-quadrado do Friedman recebe uma análise de sensibilidade por permutação de rótulos dentro de cada cenário, devido às três condições. Empates são corrigidos; contraste totalmente constante é explicitamente identificado, com estatística 0 e p=1 por convenção, sem evidência de equivalência. [Documentação oficial do Friedman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html).\n\n'
 report+=table(pair_rows,['metric','architecture_a','architecture_b','paired_scenarios','nonzero_pairs','p_unadjusted','p_holm_within_metric','rank_biserial_b_minus_a','median_paired_difference','median_difference_bootstrap_95_low','median_difference_bootstrap_95_high'])
 report+='\nWilcoxon bilateral é aplicado às três comparações somente quando o Friedman qui-quadrado é menor que 0,05; Holm corrige esses três p-valores dentro da métrica. Não há correção conjunta entre as sete métricas globais. Zeros são retirados, empates usam permutação de sinais e diferenças são arredondadas a 1e-9 antes dos ranks. [Documentação oficial do Wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html).\n\n'
 report+='Efeitos e diferenças têm orientação arquitetura B menos A: maior latência/token representa mais consumo/tempo; maior nota representa pontuação maior sob a rubrica. Kendall W resume o contraste global; correlação bisserial de ranks resume o contraste pareado entre diferenças não nulas. Intervalos de 95% são percentis de 20.000 reamostragens pareadas de cenários, condicionais à amostra intencional; não garantem cobertura para todos os atendimentos. O Wilcoxon pressupõe simetria das diferenças sob a hipótese nula. Falha em rejeitar não prova equivalência. Sucesso binário, pass^1/pass^5 e encaminhamento permanecem descritivos, sem novo teste binário escolhido após observar resultados.\n'
 (out/'ANALISE_PAREADA_COMPLEMENTAR.md').write_text(report)
 print(json.dumps({'global_metrics':len(global_rows),'posthoc_pairs':len(pair_rows),'primary_labels_changed':False}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();analyze(args.input,args.output)
