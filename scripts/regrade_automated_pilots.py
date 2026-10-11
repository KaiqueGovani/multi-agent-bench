#!/usr/bin/env python3
"""Prepare a separate v5 judge cohort from existing responses; never mutate source."""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
from run_research_pilot import ROOT,dump,sha,code_hashes
from judge_automated_pilots import read_jsonl,config
from app.experiments.methodology import validate_catalogue,objective_checks,aggregate

def prepare(source,reference,output,calibration):
    if output.exists() and any(output.iterdir()):raise ValueError('Use an empty new output folder')
    catalogue=json.loads(reference.read_text());validate_catalogue(catalogue)
    cases={c['id']:c for c in catalogue['cases']}
    original=json.loads((source/'manifest.json').read_text());runs=read_jsonl(source/'runs.jsonl')
    if len(runs)!=len(original['order']):raise ValueError('Source collection not complete')
    if set(cases)!={c['id'] for c in original['cases']}:raise ValueError('Reference case IDs differ')
    output.mkdir(parents=True,exist_ok=True)
    for name in ('runs.jsonl','runs.csv','attempts.jsonl','events.jsonl','calls.jsonl','responses.jsonl','blind-mapping.json','execution-order.csv'):
        shutil.copyfile(source/name,output/name)
    for run in runs:
        shutil.copytree(source/run['unit_id'],output/run['unit_id'])
    for name in ('code-snapshot','assets-snapshot'):
        shutil.copytree(source/name,output/name)
    cfg=config();manifest={**original,'cases':[cases[c['id']] for c in original['cases']],
        'cohort_type':'historical-responses-new-reference-and-judge',
        'source_collection':str(source),'source_manifest_sha256':sha((source/'manifest.json').read_bytes()),
        'original_cases_sha256':original['cases_sha256'],
        'cases_sha256':sha(json.dumps(list(cases.values()),sort_keys=True).encode()),
        'evaluation_plan':{'version':cfg['version'],'model_id':cfg['model_id'],'calibration_folder':str(calibration.resolve()),
            'configuration_sha256':sha(json.dumps(cfg,sort_keys=True,ensure_ascii=False).encode())},
        'evaluation_code_hashes':code_hashes(),'reference_review_sha256':sha(reference.read_bytes()),
        'meaning':'Original generator calls and inputs, v5 references/judge only. This is not a new agent pilot and does not validate stable attachment inputs.'}
    dump(output/'manifest.json',manifest)
    for name in manifest['evaluation_code_hashes']:
        dst=output/'evaluation-code-snapshot'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    for asset in reference.parent.glob('*'):
        if asset.is_file():
            dst=output/'evaluation-assets-snapshot'/asset.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(asset,dst)
    blind=json.loads((source/'blind-responses.json').read_text())
    for b in blind:b['input']=cases[b['input']['id']]
    dump(output/'blind-responses.json',blind)
    # Isolate the arithmetic effect of mandatory-source revision while retaining
    # the original semantic labels. This is a diagnostic, not a new LLM judgement.
    old_evaluations={r['response_id']:r['evaluation'] for r in read_jsonl(source/'evaluations.jsonl')}
    mapping=json.loads((source/'blind-mapping.json').read_text());rid_by_attempt={v:k for k,v in mapping.items()};rows=[]
    for run in runs:
        case=cases[run['scenario_id']];rid=rid_by_attempt.get(run['attempt_id'])
        objective=objective_checks(case,run,read_jsonl(source/run['unit_id']/'events.jsonl'))
        legacy_case={**case,'version':'pilots-v4'}
        rows.append({**run,'response_id':rid,**aggregate(legacy_case,run,objective,old_evaluations.get(rid)),
            'provenance':'derived diagnostic: revised mandatory evidence + original semantic labels; no new model call',
            'essential_label_comparability':'Semantic labels retained, not asserted to be valid under the clarified v5 rubric.'})
    (output/'reference-only-diagnostic.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    dump(output/'regrade-provenance.json',{'source':str(source),'source_primary_evaluations_sha256':sha((source/'evaluations.jsonl').read_bytes()),
        'source_aggregated_evaluations_sha256':sha((source/'aggregated-evaluations.jsonl').read_bytes()),'source_modified':False,'new_agent_executions':0,'new_judge_evaluations_planned':len(blind),
        'analysis_plan':'Compare original, evidence-only diagnostic, historical replies with full v5 judge, and new live replies with v5 judge. Temporal/generation variation prevents isolated causal attribution to inputs.'})
    return len(blind)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);p.add_argument('--calibration',type=Path,required=True);a=p.parse_args()
    print('Prepared:',prepare(a.source.resolve(),a.reference.resolve(),a.output.resolve(),a.calibration))
