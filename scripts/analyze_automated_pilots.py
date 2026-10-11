#!/usr/bin/env python3
"""Descriptive paired summaries; never treats repetitions as independent samples."""
from __future__ import annotations
import argparse,json,statistics,random,itertools
from collections import Counter
from pathlib import Path
from run_research_pilot import ROOT,dump,write_csv,sha
from judge_automated_pilots import read_jsonl
from app.experiments.methodology import objective_checks,aggregate,reliability,DIMENSIONS,MAST_LABELS,decode_tool_result,evaluator_consistency_issue,recommendation_observed,VERSION

def med(x):
    x=[v for v in x if v is not None];return statistics.median(x) if x else None
def quant(x,p):
    x=sorted(v for v in x if v is not None)
    if not x:return None
    pos=(len(x)-1)*p;a=int(pos);b=min(a+1,len(x)-1);return x[a]+(x[b]-x[a])*(pos-a)
def distribution(x):
    x=[v for v in x if v is not None]
    return {'n':len(x),'p50':med(x),'p25':quant(x,.25),'p75':quant(x,.75),'p95_exploratory':quant(x,.95),'min':min(x) if x else None,'max':max(x) if x else None}
def table(rows,keys):
    def cell(v):return 'null' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(keys)+' |\n|'+ '|'.join(['---']*len(keys))+'|\n'+''.join('| '+' | '.join(cell(r.get(k)) for k in keys)+' |\n' for r in rows)
def cohort_scope(manifest,runs):
    cases=manifest['cases'];definitive=manifest.get('cohort','').startswith('definitive-')
    return {'is_definitive':definitive,'real_conversation_cases':bool(cases) and all(c.get('origin')=='real-conversation-derived' for c in cases),
        'scenario_count':len(cases),'dataset_version':manifest.get('dataset_version',manifest.get('evaluation_plan',{}).get('version',VERSION)),
        'definitive_600_started':definitive and len(manifest['order'])==600 and bool(runs)}
def compare_recheck(case,run,objective,first,second,response_id):
    primary=aggregate(case,run,objective,first);repeat=aggregate(case,run,objective,second)
    paired=first is not None and second is not None
    critical_diff=({v['violation_id'] for v in first['critical_violations']}!={v['violation_id'] for v in second['critical_violations']}) if paired else None
    return {'response_id':response_id,'task_success_first':primary['task_success'],'task_success_second':repeat['task_success'],
        'classification_changed':primary['task_success']!=repeat['task_success'],'critical_disagreement':critical_diff,
        'critical_comparison_evaluable':paired,'objective_critical':bool(objective['critical_violations']),
        'primary_evaluation_available':first is not None,'repeat_evaluation_available':second is not None,
        'score_changes':{d:None if not paired or first['quality'][d] is None or second['quality'][d] is None else second['quality'][d]-first['quality'][d] for d in DIMENSIONS}}
def analyze(folder,calibration=None):
    manifest=json.loads((folder/'manifest.json').read_text());runs=read_jsonl(folder/'runs.jsonl');cases={c['id']:c for c in manifest['cases']};mapping=json.loads((folder/'blind-mapping.json').read_text());rid_by_attempt={v:k for k,v in mapping.items()}
    evals={r['response_id']:r['evaluation'] for r in read_jsonl(folder/'evaluations.jsonl')};rechecks={r['response_id']:r['evaluation'] for r in read_jsonl(folder/'reevaluations.jsonl')}
    scope=cohort_scope(manifest,runs)
    rows=[];queue=[];issues=[];diagnostics=[];changes=[];normalized_evidence=[];responses=[]
    for run in runs:
        path=folder/run['unit_id']/'events.jsonl';events=read_jsonl(path);case=cases[run['scenario_id']];rid=rid_by_attempt.get(run['attempt_id']);e=evals.get(rid);o=objective_checks(case,run,events);a=aggregate(case,run,o,e)
        for family,key in [('model','callId'),('tool','toolCallId'),('handoff','transferId')]:
            starts={x['payload'].get(key) for x in events if x['eventFamily']==family and x['eventName'] in {'started','requested'}}
            ends={x['payload'].get(key) for x in events if x['eventFamily']==family and x['eventName'] in {'completed','failed'}}
            if starts!=ends:issues.append({'attempt_id':run['attempt_id'],'reason':family+' unresolved IDs'})
            seq=[x.get('eventId') for x in events if x.get('eventId')]
            if len(seq)!=len(set(seq)):issues.append({'attempt_id':run['attempt_id'],'reason':'duplicate event ID'})
        calls=[x for x in events if x['eventFamily']=='model' and x['eventName']=='completed']
        if run.get('success'):
            if not run.get('token_measurement_complete'):issues.append({'attempt_id':run['attempt_id'],'reason':'missing successful-call token measurement'})
            if not any(x['eventFamily']=='response' and x['eventName']=='final' for x in events):issues.append({'attempt_id':run['attempt_id'],'reason':'missing terminal final event'})
            if calls and sum((x['payload'].get('usage') or {}).get('totalTokens',0) for x in calls)!=run.get('total_tokens'):issues.append({'attempt_id':run['attempt_id'],'reason':'token reconciliation'})
        hands=[x for x in events if x['eventFamily']=='handoff'];comms=[x for x in events if x['eventFamily']=='communication'];tools=[x for x in events if x['eventFamily']=='tool' and x['eventName']=='completed']
        milestones=o['milestones']+[{'milestone_id':'M-response','met':all(c['met'] is True for c in e['criteria']) if e and all(c['met'] is not None for c in e['criteria']) else None,'verification':'semantic'}]
        row={**run,'response_id':rid,**a,'objective_checks':o,'evaluation':e,'content_success':aggregate(case,run,{**o,'required_evidence':[]},e)['task_success'],'procedure_compliance':o['procedure_compliance'],'procedure_applicable':o['procedure_applicable'],'milestones':milestones,'milestone_fraction':sum(m['met'] is True for m in milestones)/len(milestones) if all(m['met'] is not None for m in milestones) else None,
             'handoffs_requested':sum(x['eventName']=='requested' for x in hands),'handoffs_completed':sum(x['eventName']=='completed' for x in hands),'handoffs_failed':sum(x['eventName']=='failed' for x in hands),'inter_agent_messages':len(comms),'inter_agent_characters':sum(x['payload'].get('characters',0) for x in comms),
             'domain_errors':sum(x['status']=='failed' and x['toolName'] in {'faq_lookup','stock_lookup','attachment_intake'} for x in tools),'coordination_errors':sum(x['status']=='failed' and x['toolName'] not in {'faq_lookup','stock_lookup','attachment_intake'} for x in tools), 'domain_call_correctness':o['domain_call_correctness']}
        row.update(expected_resolution_mode=case.get('expected_resolution_mode','legacy-unspecified'),
            workflow_stage_count=sum(x['eventFamily']=='agent' and x['eventName']=='started' for x in events) if run['architecture']=='structured_workflow' else None,
            swarm_sdk_cycles=run.get('model_requests') if run['architecture']=='decentralized_swarm' else None,
            inter_agent_explicit_messages=len(comms)+sum(x['eventName']=='requested' for x in hands),
            inter_agent_explicit_characters=sum(x['payload'].get('characters',0) for x in comms)+sum(x['payload'].get('messageCharacters',0) for x in hands if x['eventName']=='requested'),
            agent_input_characters=sum(x['payload'].get('inputCharacters',0) for x in events if x['eventFamily']=='agent' and x['eventName']=='started'))
        evidence_refs=[]
        for tool_event in tools:
            if tool_event.get('toolName') not in {'faq_lookup','stock_lookup','attachment_intake'}:continue
            content=decode_tool_result(tool_event['payload'].get('result'))
            if content is None:continue
            tool_id=tool_event['payload']['toolCallId'];evidence_refs.append(tool_id)
            normalized_evidence.append({'response_id':rid,'attempt_id':run['attempt_id'],'tool_call_id':tool_id,'tool_name':tool_event['toolName'],'result':content,'provenance':'deterministic-fixture-actually-consulted','architecture_and_actor_removed':True})
        if run.get('success'):responses.append({'response_id':rid,'attempt_id':run['attempt_id'],'response':run['final_text'],'evidence_refs':evidence_refs,'evidence_ledger':'normalized-domain-evidence.jsonl'})
        rows.append(row)
        def flag(role,reason,priority=2):queue.append({'response_id':rid,'attempt_id':run['attempt_id'],'scenario_id':case['id'],'architecture':run['architecture'],'reviewer_role':role,'reason':reason,'priority':priority,'human_review_performed':False})
        if not run.get('success'):flag('technical','technical failure',1)
        if e is None and run.get('success'):flag('technical','judge unavailable',1)
        if any(v['met'] is not True for v in o['required_evidence']):flag('technical','missing/unresolved mandatory evidence')
        if o['critical_violations']:flag('technical','objective critical violation',1)
        if e:
            if evaluator_consistency_issue(case,e):flag('technical','evaluator internal referral contradiction',1)
            if e['evidence_insufficient']:flag('technical','evidence insufficient',1)
            if e['critical_violations']:flag('pharmacist' if any(v['violation_id'] in {'V2','V4'} for v in e['critical_violations']) else 'technical','judge critical suspicion',1)
            if case['professional_review_required'] and recommendation_observed(e) is False and not evaluator_consistency_issue(case,e):flag('pharmacist','possible referral false negative',1)
            if any(x['met'] is False for x in o['required_evidence']) and all(c['met'] is True for c in e['criteria']):flag('technical','objective evidence failure with semantic criteria satisfied; review evidence requirement',1)
            if o['critical_violations'] and not e['critical_violations']:flag('technical','objective/judge critical conflict',1)
            for m in e['review_reason_codes']:flag('technical','judge review code: '+m)
        if rid in rechecks:
            change=compare_recheck(case,run,o,e,rechecks[rid],rid)
            changed=change['classification_changed'];critical_diff=change['critical_disagreement']
            changes.append(change)
            if changed or critical_diff:flag('technical','recheck disagreement',1)
        # Confirm omissions using closed milestones; repetition is only a candidate.
        if any(x['met'] is False for x in o['required_evidence']):diagnostics.append({'attempt_id':run['attempt_id'],'label':'missing_or_incorrect_verification','status':'objective-confirmed','evidence':'mandatory source milestone not met'})
        if run.get('success') and not e:diagnostics.append({'attempt_id':run['attempt_id'],'label':'premature_termination','status':'not_assessed','evidence':'judge unavailable, terminal alone does not establish task completion'})
        if e and any(c['criterion_id']=='C1' and c['met'] is False for c in e['criteria']):
            diagnostics.append({'attempt_id':run['attempt_id'],'label':'task_deviation','status':'candidate','evidence':'first essential criterion C1 not met; may instead be incomplete response'})
            if case['history']:
                diagnostics.append({'attempt_id':run['attempt_id'],'label':'history_loss','status':'candidate','evidence':'context-dependent essential C1 not met; history supplied; does not prove causal loss'})
        if e and comms and any(c['met'] is False for c in e['criteria']) and all(x['met'] is True for x in o['required_evidence']):
            diagnostics.append({'attempt_id':run['attempt_id'],'label':'agent_information_ignored','status':'candidate','evidence':'source evidence confirmed and specialist messages recorded, but essential criterion failed; inspect text before confirmation'})
        if run.get('success') and any(x['met'] is False for x in o['required_evidence']):
            diagnostics.append({'attempt_id':run['attempt_id'],'label':'premature_termination','status':'candidate','evidence':'final response emitted before mandatory evidence milestone was met'})
        if any(x['correct'] is False for x in o['call_checks']):
            diagnostics.append({'attempt_id':run['attempt_id'],'label':'missing_or_incorrect_verification','status':'objective-confirmed','evidence':'tool/arguments/result failed objective compatibility check'})
        seen=Counter(json.dumps(x['payload'].get('input',{}),sort_keys=True)+str(x.get('toolName')) for x in events if x['eventFamily']=='tool' and x['eventName']=='started')
        if any(n>1 for n in seen.values()):diagnostics.append({'attempt_id':run['attempt_id'],'label':'unnecessary_repetition','status':'candidate','evidence':'duplicate tool/argument signature; may be justified, needs technical review'})
    # Same planned schedule, no overlap; outer launch/finish evidence remains per attempt.
    if [r['unit_id'] for r in runs]!=[u['unit_id'] for u in manifest['order'][:len(runs)]]:issues.append({'reason':'planned order mismatch'})
    for name,want in manifest['code_hashes'].items():
        p=folder/'code-snapshot'/name
        if not p.exists() or sha(p.read_bytes())!=want:issues.append({'reason':'snapshot hash mismatch','file':name})
    planned=len(manifest['order']);reps=manifest.get('repetitions',5);arches=list(dict.fromkeys(u['architecture'] for u in manifest['order']));groups=[]
    continuous=['end_to_end_latency_ms','latency_ms','input_tokens','output_tokens','total_tokens','model_requests','agent_invocations','actual_agents','domain_tool_calls','coordination_tool_calls','handoffs_requested','handoffs_completed','handoffs_failed','inter_agent_messages','inter_agent_characters','milestone_fraction','domain_call_correctness','domain_errors','coordination_errors','workflow_stage_count','swarm_sdk_cycles','inter_agent_explicit_messages','inter_agent_explicit_characters','agent_input_characters']
    for case in cases.values():
        for arch in arches:
            rr=[r for r in rows if r['scenario_id']==case['id'] and r['architecture']==arch];known=[r['task_success'] for r in rr if r['task_success'] is not None];valid=[r for r in rr if r.get('success')]
            g={'scenario_id':case['id'],'stratum':case['stratum'],'difficulty':case['difficulty'],'expected_resolution_mode':case.get('expected_resolution_mode','legacy-unspecified'),'architecture':arch,'planned':reps,'executed':len(rr),'evaluable':len(known),'technical_successes':len(valid),'task_successes':sum(x is True for x in known),'task_success_rate':sum(known)/len(known) if known else None,'unknown':reps-len(known)}
            for k in continuous:g[k+'_median']=med([r.get(k) for r in valid])
            for d in DIMENSIONS:
                g[d+'_median']=med([r['evaluation']['quality'][d] for r in rr if r['evaluation']])
                g[d+'_evaluable']=sum(r['evaluation'] is not None and r['evaluation']['quality'][d] is not None for r in rr)
            for field in ('content_success','procedure_compliance'):
                applicable=[r for r in rr if field!='procedure_compliance' or r['procedure_applicable']]
                known=[r[field] for r in applicable if r[field] is not None]
                g[field+'_applicable']=len(applicable);g[field+'_evaluable']=len(known);g[field+'_successes']=sum(x is True for x in known);g[field+'_rate']=sum(known)/len(known) if known else None
            groups.append(g)
    summaries=[]
    for arch in arches:
        for stratum in ['all']+list(dict.fromkeys(c['stratum'] for c in cases.values())):
            cc=[c for c in cases.values() if stratum=='all' or c['stratum']==stratum];rr=[r for r in rows if r['architecture']==arch and r['scenario_id'] in {c['id'] for c in cc}];gg=[g for g in groups if g['architecture']==arch and g['scenario_id'] in {c['id'] for c in cc}]
            rel=reliability([[r['task_success'] for r in rr if r['scenario_id']==c['id']] for c in cc],len(cc),reps)
            if reps!=5:
                for key in ('complete_scenarios','pass_1','pass_5','pass_1_lower','pass_1_upper','pass_5_lower','pass_5_upper'):rel[key]=None
            s={'architecture':arch,'stratum':stratum,'planned':len(cc)*reps,'executed':len(rr),'technical_successes':sum(r.get('success',False) for r in rr),'task_successes':sum(r['task_success'] is True for r in rr),'evaluable':sum(r['task_success'] is not None for r in rr),**rel}
            for k in continuous:s[k+'_median_of_case_medians']=med([g[k+'_median'] for g in gg])
            for d in DIMENSIONS:
                s[d+'_median_of_case_medians']=med([g[d+'_median'] for g in gg])
                s[d+'_evaluable']=sum(g[d+'_evaluable'] for g in gg)
            for field in ('content_success','procedure_compliance'):
                for suffix in ('applicable','evaluable','successes'):s[field+'_'+suffix]=sum(g[field+'_'+suffix] for g in gg)
                s[field+'_rate_median_of_case_rates']=med([g[field+'_rate'] for g in gg])
            s['transfer_claimed_in_response_count']=sum(r['evaluation'] is not None and r['evaluation'].get('transfer_claimed_in_response') is True for r in rr)
            s['transfer_executed_by_judge_count']=sum(r['evaluation'] is not None and r['evaluation'].get('transfer_executed') is True for r in rr)
            counts=Counter()
            for r in rr:
                ev=r['evaluation'];expected=cases[r['scenario_id']]['professional_review_required'];observed=recommendation_observed(ev) if ev and not evaluator_consistency_issue(cases[r['scenario_id']],ev) else None
                counts['unknown' if observed is None else 'TP' if expected and observed else 'FN' if expected else 'FP' if observed else 'TN']+=1
            for k in ('TP','TN','FP','FN'):s['referral_'+k]=counts[k]
            s['referral_unknown']=counts['unknown'];s['referral_coverage']=sum(counts[k] for k in ('TP','TN','FP','FN'))/s['planned'];s['sensitivity']=counts['TP']/(counts['TP']+counts['FN']) if counts['TP']+counts['FN'] else None;s['specificity']=counts['TN']/(counts['TN']+counts['FP']) if counts['TN']+counts['FP'] else None;s['false_negative_rate']=counts['FN']/(counts['TP']+counts['FN']) if counts['TP']+counts['FN'] else None
            summaries.append(s)
    rng=random.Random(20261011);flags=[q for q in queue if q['reviewer_role']=='pharmacist'];selected=list(dict.fromkeys(q['response_id'] for q in sorted(flags,key=lambda q:q['priority']) if q['response_id']))[:24]
    # Cover architectures with approved sensitive responses, then fill randomly.
    candidates=[r for r in rows if r['response_id'] and cases[r['scenario_id']]['professional_review_required'] and r['task_success'] is True and r['response_id'] not in selected];rng.shuffle(candidates)
    for arch in arches:
        if not any(r['architecture']==arch and r['response_id'] in selected for r in rows):
            c=next((r for r in candidates if r['architecture']==arch),None)
            if c and len(selected)<24:selected.append(c['response_id'])
    for r in candidates:
        if len(selected)>=24:break
        if r['response_id'] not in selected:selected.append(r['response_id'])
    dump(folder/'optional-pharmacist-audit.json',{'budget':24,'selected_response_ids':selected,'flagged_responses_total':len({q['response_id'] for q in flags}),'flagged_responses_not_selected':len({q['response_id'] for q in flags}-set(selected)),'human_review_performed':False,'selection_bias':'targeted audit does not estimate representative error rate'})
    packets=[]
    for r in rows:
        if r['response_id'] in selected:
            c=cases[r['scenario_id']];packets.append({'response_id':r['response_id'],'request':c['text'],'history':c['history'],'attachments':c['attachments'],'reference':{k:c[k] for k in ('professional_review_required','expected_facts','critical_restrictions')},'response':r['final_text'],'domain_evidence':c['required_evidence']+c.get('optional_evidence',[]),'evidence_explanation':'Common reference facts, not proof of tool consultations. Actual evidence is in the separately preserved execution ledger.','review_scope':'security and referral only'})
    rng.shuffle(packets);dump(folder/'optional-pharmacist-packets.json',packets)
    write_csv(folder/'focused-pharmacist-template.csv',[{'response_id':rid,'reviewer_id':'','safety':'','referral_observed':'','critical_violation_suspected':'','reason':''} for rid in selected],['response_id','reviewer_id','safety','referral_observed','critical_violation_suspected','reason'])
    def export_jsonl(name,items):(folder/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in items))
    diag_summary=[]
    for arch in arches:
        for label in MAST_LABELS:
            eligible=[r for r in rows if r['architecture']==arch and (label!='agent_information_ignored' or r['inter_agent_messages']>0) and (label!='history_loss' or cases[r['scenario_id']]['history'])]
            found=[d for d in diagnostics if d['label']==label and d['attempt_id'] in {r['attempt_id'] for r in eligible}]
            confirmed=len({d['attempt_id'] for d in found if d['status']=='objective-confirmed'});candidate=len({d['attempt_id'] for d in found if d['status']=='candidate'})
            diag_summary.append({'architecture':arch,'label':label,'applicable_attempts':len(eligible),'objective_confirmed':confirmed,'candidate':candidate,'candidate_fraction':candidate/len(eligible) if eligible else None,'interpretation':'detectors incomplete; absence of flag does not establish absence of mechanism'})
    write_csv(folder/'failure-diagnostic-summary.csv',diag_summary)
    export_jsonl('normalized-domain-evidence.jsonl',normalized_evidence);export_jsonl('responses.jsonl',responses)
    snapshot=folder/'analysis-snapshot/scripts/analyze_automated_pilots.py';snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(Path(__file__).read_bytes())
    module_snapshot=folder/'analysis-snapshot/apps/agent-runtime/app/experiments/methodology.py';module_snapshot.parent.mkdir(parents=True,exist_ok=True);module_snapshot.write_bytes((ROOT/'apps/agent-runtime/app/experiments/methodology.py').read_bytes())
    export_jsonl('aggregated-evaluations.jsonl',rows);export_jsonl('failure-diagnostics.jsonl',diagnostics);write_csv(folder/'metrics.csv',groups);write_csv(folder/'architecture-stratum-metrics.csv',summaries);write_csv(folder/'review-queue.csv',queue,['response_id','attempt_id','scenario_id','architecture','reviewer_role','reason','priority','human_review_performed']);dump(folder/'recheck-analysis.json',{'planned':15 if reps==5 else 0,'evaluated':len(changes),'paired_evaluations':sum(c['critical_comparison_evaluable'] for c in changes),'success_classification_changes':sum(c['classification_changed'] for c in changes),'objective_critical_disagreements':sum(bool(c['critical_disagreement'] and c['objective_critical']) for c in changes),'changes':changes})
    if calibration and (folder/'judge-config.json').exists() and json.loads((folder/'judge-config.json').read_text())!=json.loads((calibration/'judge-config.json').read_text()):issues.append({'reason':'judge differs from calibrated configuration'})
    first_inputs={}
    for run in runs:
        evs=read_jsonl(folder/run['unit_id']/'events.jsonl')
        first=next((x for x in evs if x['eventFamily']=='agent' and x['eventName']=='started'),None)
        if first:first_inputs.setdefault(run['scenario_id'],set()).add(first['payload'].get('inputSha256'))
    equal_inputs=all(len(hashes)==1 and None not in hashes for hashes in first_inputs.values()) and len(first_inputs)==len(cases)
    if manifest['configuration']['protocol']=='architectural-comparison-v4.1' and not equal_inputs:issues.append({'reason':'initial agent input differs within a scenario'})
    dump(folder/'initial-input-equivalence.json',{'scope':'first agent user prompt, across architectures and repetitions; role system prompts remain architecture-specific','equal_within_all_scenarios':equal_inputs,'scenario_hashes':{k:sorted(v,key=str) for k,v in first_inputs.items()}})
    calibration_ok=bool(calibration and json.loads((calibration/'calibration-gate.json').read_text()).get('passed'))
    ready=len(runs)==planned and not issues and len(evals)==sum(r.get('success',False) for r in runs) and calibration_ok and (reps!=5 or (len(changes)==15 and all(c['critical_comparison_evaluable'] for c in changes) and sum(c['classification_changed'] for c in changes)<2 and not any(c['critical_disagreement'] and c['objective_critical'] for c in changes)))
    gates={'planned':planned,'attempts':len(runs),'successful':sum(r.get('success',False) for r in runs),'evaluated':len(evals),'integrity_issues':issues,'calibration_passed':calibration_ok,'core_engineering_ready':ready,'http_database_integration_performed':False,'human_review_performed':False,**scope,'cost_usd':None}
    gates['initial_inputs_equivalent']=equal_inputs
    gates['live_proven']=all(r.get('mode')=='live' and (not r.get('success') or r.get('model_requests',0)>0) for r in runs)
    gates['all_success_usage_complete']=all(r.get('token_measurement_complete') for r in runs if r.get('success'))
    gates['core_engineering_ready']=gates['core_engineering_ready'] and gates['live_proven'] and gates['all_success_usage_complete']
    ready=gates['core_engineering_ready']
    reference_notes=json.loads((folder/'reference-review-notes.json').read_text()) if (folder/'reference-review-notes.json').exists() else {}
    gates['reference_review_required']=any(x['status']=='technical-reference-review-required' for x in reference_notes.get('issues',[]))
    gates['evaluator_internal_contradictions']=sum(bool(evaluator_consistency_issue(cases[r['scenario_id']],r['evaluation'])) for r in rows)
    gates['collection_engineering_ready']=len(runs)==planned and not issues and gates['live_proven'] and gates['all_success_usage_complete']
    gates['core_engineering_ready']=ready and gates['evaluator_internal_contradictions']==0
    gates['cohort_type']=manifest.get('cohort_type','new-agent-collection')
    gates['recommend_full_matrix']=gates['core_engineering_ready'] and reps==5 and planned==150 and not gates['reference_review_required'] and gates['cohort_type']=='new-agent-collection'
    gates['definitive_collection_complete']=scope['is_definitive'] and len(runs)==planned and not issues
    gates['definitive_analysis_ready']=gates['definitive_collection_complete'] and gates['core_engineering_ready'] and not gates['reference_review_required']
    dump(folder/'readiness.json',gates)
    from app.experiments.methodology import OBJECTIVE_CHECK_VERSION
    dump(folder/'analysis-provenance.json',{'version':'descriptive-analysis-v5.2','objective_check_version':OBJECTIVE_CHECK_VERSION,'source_sha256':sha(Path(__file__).read_bytes()),'amendment':'Frozen v5 semantic instrument; v5.3 objective verification additionally requires authentic tool-contract results and frozen query aliases when generic unknown-product results are ambiguous. Final-content quality and objective procedure remain separate; missing primary/repeat evaluations remain unpaired and unknown. Historical results are not rewritten.'})
    costs={}
    for phase in ('primary','recheck','technical-calibration'):
        attempts=[r for r in read_jsonl(folder/'judge-attempts.jsonl') if r.get('event')=='completed' and r.get('phase')==phase];costs[phase]={'calls':len(attempts),'input_tokens':sum((r.get('usage') or {}).get('inputTokens',0) for r in attempts) if all(r.get('usage') for r in attempts) else None,'output_tokens':sum((r.get('usage') or {}).get('outputTokens',0) for r in attempts) if all(r.get('usage') for r in attempts) else None,'cost_usd':None}
    agent_tokens={k:sum(r[k] for r in runs) if runs and all(r.get(k) is not None for r in runs) else None for k in ('input_tokens','output_tokens','total_tokens')}
    historical=gates['cohort_type']!='new-agent-collection'
    dump(folder/'resource-consumption.json',{'agents':{k:0 for k in agent_tokens} if historical else agent_tokens,'historical_agent_tokens_reused':agent_tokens if historical else None,'judge':costs,'pricing':'unverified; USD unavailable','projection_600_tokens':{k:v*600/planned if v is not None and not historical else None for k,v in agent_tokens.items()},'projection_assumption':'Linear illustrative projection on a new live pilot composition, not a measured definitive cost; historical generator tokens are not billed again.'})
    order=manifest['order'];perms=Counter(tuple(u['architecture'] for u in order[i:i+len(arches)]) for i in range(0,len(order),len(arches)));positions={arch:Counter(u['position'] for u in order if u['architecture']==arch) for arch in arches};dump(folder/'randomization-check.json',{'permutations':{' / '.join(k):v for k,v in perms.items()},'positions':{k:dict(v) for k,v in positions.items()},'balanced_permutations':max(perms.values())-min(perms.values())<=1,'balanced_positions':all(max(v.values())-min(v.values())<=1 for v in positions.values())})
    durations={a:{'completed':distribution([r.get('end_to_end_latency_ms',r.get('latency_ms')) for r in runs if r['architecture']==a and r.get('success')]),'until_failure':distribution([r.get('end_to_end_latency_ms',r.get('latency_ms')) for r in runs if r['architecture']==a and not r.get('success')])} for a in arches};dump(folder/'latency-distributions.json',durations)
    report='# Resultados descritivos do lote — '+scope['dataset_version']+'\n\n'
    report+=f'{planned} unidades planejadas; {len(runs)} tentativas; {gates["successful"]} sucessos técnicos; {len(evals)} avaliações primárias válidas. {len(cases)} cenários, {reps} repetições por arquitetura; comparações pareadas por cenário.\n\n'
    if historical:report+='Este diretório reavalia respostas de execuções históricas sob referências/juiz novos. As tentativas e consumos do gerador são históricos; não houve nova coleta de agentes nem prova de entrada corrigida neste diretório.\n\n'
    report+=table([s for s in summaries if s['stratum']=='all'],['architecture','planned','executed','evaluable','technical_successes','task_successes','complete_scenarios','pass_1','pass_5','unknown'])
    report+='\n## Resumo por estrato\n\n'+table(summaries,['architecture','stratum','planned','evaluable','task_successes','pass_1','pass_5','referral_TP','referral_TN','referral_FP','referral_FN','referral_unknown','sensitivity','specificity'])
    report+='\n## Cinco dimensões, separadas\n\n'+table([s for s in summaries if s['stratum']=='all'],['architecture']+[d+'_median_of_case_medians' for d in DIMENSIONS])
    quality_distribution=[]
    criterion_distribution=[]
    for arch in arches:
        for case in cases.values():
            rr=[r for r in rows if r['architecture']==arch and r['scenario_id']==case['id']]
            for d in DIMENSIONS:
                counts=Counter(r['evaluation']['quality'][d] if r['evaluation'] else None for r in rr)
                quality_distribution.append({'architecture':arch,'scenario_id':case['id'],'stratum':case['stratum'],'dimension':d,'planned':reps,'unknown':counts[None],**{'score_'+str(i):counts[i] for i in range(1,6)}})
            for criterion in case['essential_requirements']:
                counts=Counter(next((c['met'] for c in r['evaluation']['criteria'] if c['criterion_id']==criterion['criterion_id']),None) if r['evaluation'] else None for r in rr)
                criterion_distribution.append({'architecture':arch,'scenario_id':case['id'],'criterion_id':criterion['criterion_id'],'rule':criterion['rule'],'assessment_target':criterion.get('assessment_target','legacy-unspecified'),'met':counts[True],'not_met':counts[False],'unknown':counts[None]})
    write_csv(folder/'quality-distributions.csv',quality_distribution);write_csv(folder/'criterion-distributions.csv',criterion_distribution)
    report+='\n## Conteúdo final e procedimento obrigatório, separados\n\n'+table([r for r in summaries if r['stratum']=='all'],['architecture','content_success_successes','content_success_evaluable','procedure_compliance_applicable','procedure_compliance_successes','procedure_compliance_evaluable'])+'\nA dimensão operational_correctness avalia conteúdo operacional final; procedure_compliance verifica consultas obrigatórias na trajetória. Procedimento sem consulta obrigatória é não aplicável. Distribuições 1–5 e critérios individuais estão em quality-distributions.csv e criterion-distributions.csv.\n'
    report+='\n## Comparações pareadas por cenário\n\n'+table(groups,['scenario_id','architecture','executed','evaluable','task_success_rate','end_to_end_latency_ms_median','total_tokens_median','model_requests_median','actual_agents_median','domain_tool_calls_median','coordination_tool_calls_median','handoffs_completed_median','milestone_fraction_median','domain_call_correctness_median'])
    report+='\n## Dispersão operacional\n\n'+json.dumps(durations,ensure_ascii=False,indent=2)+f'\n\np95 é exploratório; n está registrado. Falhas têm distribuição própria. A agregação principal usa medianas por cenário, não {planned} amostras independentes. Limites pass^1/pass^5 no conjunto planejado estão em architecture-stratum-metrics.csv; são limites descritivos, não intervalos de confiança.\n'
    report+='\n## Juiz, revisão e prontidão\n\n'+json.dumps(gates,ensure_ascii=False,indent=2)+'\n\n'+f'Reavaliações: {len(changes)}; mudanças de sucesso: {sum(c["classification_changed"] for c in changes)}. Primeira avaliação válida permanece principal. Review queue: {len(queue)} itens. Auditoria farmacêutica opcional: {len(selected)} respostas selecionadas; nenhuma revisão realizada.\n'
    origin=('Cenários derivados de conversas reais, com prefixos revisados para privacidade e gabaritos técnicos autorais; os clientes conhecidos já usados no desenvolvimento foram excluídos. Valores e operações históricos não comprovam fatos atuais. Sucesso mede cumprimento dos requisitos no ambiente controlado, incluindo declaração de limites ou esclarecimento; não comprova conclusão comercial real.' if scope['real_conversation_cases'] else 'Cenários sintéticos, gabaritos autorais apoiados por LLM. São variantes de capacidades conhecidas; excluir estes casos do conjunto definitivo.')
    report+='\n## Interpretação e limites\n\nInferência real Bedrock; ferramentas de domínio determinísticas simuladas. Centralizada é um supervisor com ferramentas; workflow usa agentes sequenciais; swarm tem iniciação coordenada e delegação sequencial. Sem paralelismo introduzido. Contexto estruturado integral, processos e memória novos por unidade. '+origin+' Sem validação farmacêutica. Anexos somente metadados, sem OCR/visão/transcrição. Conformidade automatizada com regras experimentais não constitui segurança clínica validada. Temperatura zero não implica repetições independentes. Sem testes inferenciais confirmatórios, vencedor ou custo monetário sem tarifa verificada. Falhas, desconhecidos e versões anteriores são preservados.\n'
    report+='\nDiagnóstico MAST adaptado: omissão de evidência obrigatória é objetiva; assinatura repetida de ferramenta é somente candidata, pois retry justificado/revisão/novo estado podem ser legítimos. Perda de histórico, desvio, informação de outro agente ignorada e encerramento prematuro exigem revisão observável, sem raciocínio interno ou causalidade inferida por similaridade. Diagnósticos de processo possuem cegamento limitado; não foram misturados com o juiz cego de qualidade.\n'
    decision=('Piloto A tecnicamente pronto para avançar ao B; não recomenda matriz definitiva com apenas nove unidades.' if reps!=5 and ready else 'núcleo pronto para decisão dos autores, sujeito ao escopo e à integração HTTP/banco ainda não demonstrada.' if gates['recommend_full_matrix'] else 'investigar gates/referências pendentes e realizar nova versão de piloto antes de recomendar matriz completa; ver readiness.json.')
    if scope['is_definitive']:
        decision='Lote definitivo tecnicamente completo para análise descritiva no escopo declarado.' if gates['definitive_analysis_ready'] else 'Lote definitivo com pendências de integridade, avaliação ou referência; consultar readiness.json antes de fechar os resultados.'
    report+='\nRecomendação: '+decision+'\n'
    report+='\n## Definições de processo e referências a revisar\n\nWorkflow_stage_count conta invocações iniciadas do router, especialistas e sintetizador. Swarm_sdk_cycles conta requisições reais ao modelo em seus agentes; não é equivalente a etapas do workflow. Inter_agent_messages legado conta saídas de especialistas registradas; inter_agent_explicit_messages soma essas saídas às solicitações explícitas de handoff. Seus caracteres somam texto das saídas e motivos de delegação; agent_input_characters inclui prompts com contexto compartilhado e é separado. Nenhuma contagem textual equivale a tokens faturados, nem representa atribuição completa de comunicação. Os esclarecimentos de exportação após a coleta são versionados em analysis-provenance.json, sem alterar os registros.\n'
    if (folder/'evaluator-consistency-notes.json').exists():report+='\nInconsistência do avaliador (rótulo bruto preservado, classificação derivada desconhecida, fila técnica):\n'+(folder/'evaluator-consistency-notes.json').read_text()+'\n'
    if reference_notes:report+='\nNotas de referência, preservando classificações primárias:\n'+json.dumps(reference_notes,ensure_ascii=False,indent=2)+'\n'
    (folder/'preliminary-results.md').write_text(report)
    if scope['is_definitive']:(folder/'descriptive-results.md').write_text(report)
    return gates
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--calibration',type=Path);a=p.parse_args();print(json.dumps(analyze(a.folder.resolve(),a.calibration),ensure_ascii=False))
