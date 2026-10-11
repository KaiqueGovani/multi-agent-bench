#!/usr/bin/env python3
"""Uniform nonsemantic format revision of preserved outputs; no model calls."""
from pathlib import Path
import json,shutil,argparse
from judge_automated_pilots import config,frozen_config,read_jsonl,normalize_json_format
from app.experiments.methodology import validate_evaluation,judge_input
from run_research_pilot import ROOT,dump,append,sha
def process(source,target,cal):
    cfg=config()
    if not json.loads((cal/'calibration-gate.json').read_text())['passed']:raise ValueError('Calibration not approved')
    if json.loads((cal/'judge-config.json').read_text())!=cfg:raise ValueError('Calibration configuration differs')
    if target.exists():raise ValueError('Use an empty new normalization cohort')
    oldcfg=json.loads((source/'judge-config.json').read_text())
    differences={k for k in cfg.keys()|oldcfg.keys() if cfg.get(k)!=oldcfg.get(k)}
    if differences-{'version','local_format_repair'}:raise ValueError('Inference controls changed: '+str(differences))
    # All inferential controls, prompt, schema and source facts remain identical.
    accepted={phase:{r['response_id']:r for r in read_jsonl(source/name)} for phase,name in [('primary','evaluations.jsonl'),('recheck','reevaluations.jsonl')]}
    journals=read_jsonl(source/'judge-attempts.jsonl');by_attempt={r['attempt_id']:r for r in journals if r.get('event')=='completed'}
    blind={r['evaluation_id']:r for r in json.loads((source/'blind-responses.json').read_text())}
    shutil.copytree(source,target)
    for name in ['judge-config.json','judge-source-provenance.json','judge-code-snapshot','evaluations.jsonl','reevaluations.jsonl','evaluation-failures.jsonl']:
        path=target/name
        if path.exists():path.rename(target/('source-'+name))
    frozen_config(target,cfg)
    m=json.loads((target/'manifest.json').read_text());m['original_evaluation_plan']=m.get('evaluation_plan');m['evaluation_plan']={'model_id':cfg['model_id'],'temperature':cfg['temperature'],'max_tokens':cfg['max_tokens'],'version':cfg['version'],'calibration_folder':str(cal),'configuration_sha256':sha(json.dumps(cfg,sort_keys=True,ensure_ascii=False).encode())};m['evaluation_reprocessing']={'source_folder':str(source),'source_manifest_sha256':sha((source/'manifest.json').read_bytes()),'source_inference_configuration':oldcfg['version'],'format_configuration':cfg['version'],'new_agent_calls':0,'new_primary_judge_calls':0,'scope':'Uniform deterministic format pass on preserved outputs; existing valid labels must remain exactly equal.'};dump(target/'manifest.json',m)
    ledger=[];recovered=0;unchanged=0
    for phase,name in [('primary','evaluations.jsonl'),('recheck','reevaluations.jsonl')]:
        ids=list(blind) if phase=='primary' else json.loads((source/'recheck-selection.json').read_text())['response_ids'] if (source/'recheck-selection.json').exists() else []
        for rid in ids:
            old=accepted[phase].get(rid)
            candidates=[by_attempt[old['attempt_id']]] if old else [r for r in journals if r.get('event')=='completed' and r['phase']==phase and r['response_id']==rid]
            value=None;aid=None;operations=[];errors=[]
            for attempt in candidates:
                try:
                    decoded,operations=normalize_json_format(attempt['raw_output']);value=validate_evaluation(decoded,blind[rid]['input'],rid);aid=attempt['attempt_id'];break
                except (ValueError,TypeError) as e:errors.append(type(e).__name__+': '+str(e))
            stored=source/'judge-inputs'/phase/(rid+'.json')
            if stored.exists() and json.loads(stored.read_text())!=judge_input(blind[rid]['input'],blind[rid]['response'],rid):raise ValueError('Frozen judge input changed: '+rid)
            if old:
                if value!=old['evaluation']:raise ValueError('Previously valid decisions changed: '+rid)
                unchanged+=1
            elif value is not None:recovered+=1
            if value is None:append(target/'evaluation-failures.jsonl',{'response_id':rid,'phase':phase,'normalization_errors':errors,'new_inference_calls':0})
            else:append(target/name,{'response_id':rid,'attempt_id':aid,'configuration_version':cfg['version'],'inference_configuration_version':oldcfg['version'],'format_reprocessing':True,'evaluation':value,'human_review_performed':False})
            ledger.append({'response_id':rid,'phase':phase,'physical_attempt_id':aid,'source_valid_evaluation':old is not None,'normalized_valid':value is not None,'existing_valid_decisions_unchanged':value==old['evaluation'] if old else None,'operations':operations,'new_inference_calls':0})
    dump(target/'format-normalization-ledger.json',ledger)
    dump(target/'format-normalization-summary.json',{'source_folder':str(source),'configuration_changes':sorted(differences),'existing_valid_evaluations_unchanged':unchanged,'schema_failures_recovered':recovered,'unresolved':sum(not r['normalized_valid'] for r in ledger),'new_agent_calls':0,'new_judge_calls':0,'raw_journal_sha256_unchanged':sha((source/'judge-attempts.jsonl').read_bytes())==sha((target/'judge-attempts.jsonl').read_bytes()),'method':'Only strip wrappers and remove an exactly duplicated review_reason_codes field from quality_reasons when the authoritative root field exists and is equal. No relocation, conflicted deletion or semantic changes.'})
    print(target.name,'unchanged',unchanged,'recovered',recovered,flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('target',type=Path);parser.add_argument('--calibration',type=Path,required=True);args=parser.parse_args()
    process(args.source.resolve(),args.target.resolve(),args.calibration.resolve())
