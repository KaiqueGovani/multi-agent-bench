"""Engineering tests only. Synthetic/fake evidence never enters live result folders."""
import json,sys,time
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.experiments.methodology import aggregate,reliability,objective_checks,validate_catalogue,validate_evaluation,DIMENSIONS
from app.architectures import comparison as c
from test_research_comparison import context
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from run_research_pilot import build_order,make_request

def cases(name='pilot-b'):return json.loads((ROOT/'experiments/pilots-v4'/f'{name}.json').read_text())
def test_closed_catalogues_and_equal_sources():
    for name,n in [('pilot-a',3),('pilot-b',10)]:
        catalogue=cases(name);validate_catalogue(catalogue);assert len(catalogue['cases'])==n
    from collections import Counter
    assert set(Counter(c['stratum'] for c in cases()['cases']).values())=={2}
def test_balanced_permutations_and_positions():
    from collections import Counter
    order=build_order(cases()['cases'],5,20261011,'00000000-0000-0000-0000-000000000001')
    perms=Counter(tuple(u['architecture'] for u in order[i:i+3]) for i in range(0,150,3))
    assert len(order)==150 and sorted(perms.values())==[8,8,8,8,9,9]
    for a in c.ARCHITECTURES:
        cc=Counter(u['position'] for u in order if u['architecture']==a)
        assert max(cc.values())-min(cc.values())<=1

def test_pass5_uses_actual_five_outcomes_with_unknown_bounds():
    x=reliability([[True]*5,[True,True,True,True,False],[True,None,False,False,False]],3)
    assert x['pass_1']==.9 and x['pass_5']==.5 and x['complete_scenarios']==2
    assert x['pass_1_lower']==10/15 and x['pass_1_upper']==11/15
    assert x['pass_5_lower']==1/3 and x['pass_5_upper']==1/3

def test_objective_failure_cannot_be_overridden_by_judge():
    case=cases()['cases'][2];o=objective_checks(case,{'success':True},[])
    e={'critical_violations':[],'criteria':[{'met':True}],'evidence_insufficient':False,'referral_observed':False}
    assert aggregate(case,{'success':True},o,e)['task_success'] is False
    o['required_evidence']=[{'met':True}]
    assert aggregate(case,{'success':True},o,None)['task_success'] is None
    assert aggregate(case,{'success':False},o,None)['task_success'] is False

def test_tool_result_and_arguments_reconciled():
    case=cases()['cases'][2]
    from app.tools.research_tools import stock_lookup
    result=stock_lookup(question='loratadina')
    events=[{'eventFamily':'tool','eventName':'started','toolName':'stock_lookup','payload':{'toolCallId':'t','input':{'question':'loratadina'}}},{'eventFamily':'tool','eventName':'completed','toolName':'stock_lookup','status':'completed','payload':{'toolCallId':'t','result':{'status':'success','content':[{'json':result}]}}}]
    o=objective_checks(case,{'success':True},events)
    assert o['required_evidence'][0]['met'] is True and o['domain_call_correctness']==1
    events[1]['payload']['result']['content'][0]['json']['quantity']=99
    assert objective_checks(case,{'success':True},events)['domain_call_correctness']==0

def test_history_complete_before_first_source_is_not_truncated(monkeypatch):
    case=cases()['cases'][-1];unit=build_order([case],1,1,'00000000-0000-0000-0000-000000000001')[0]
    request=make_request(case,unit,'x');ctx=context('centralized_orchestration');ctx.request=request
    seen=[]
    monkeypatch.setattr(c,'ControlledAgent',lambda *a,**k:lambda prompt:seen.append(prompt) or 'resposta')
    c.execute_comparison(ctx,'centralized_orchestration')
    assert 'primeiro produto da minha consulta é paracetamol' in seen[0]
    assert len(request.conversation_history)==11

def test_domain_limit_before_twenty_first_call():
    ctx=context('centralized_orchestration');h=c.ToolEvents(ctx,'supervisor')
    for i in range(20):h.before(SimpleNamespace(tool_use={'name':'stock_lookup','toolUseId':str(i),'input':{}}))
    with pytest.raises(c.ExperimentLimitExceeded):h.before(SimpleNamespace(tool_use={'name':'stock_lookup','toolUseId':'21','input':{}}))
    assert ctx.research_domain_calls==20

def test_true_model_request_usage_ledger(monkeypatch):
    import asyncio
    async def fake_stream(self,*a,**kw):
        yield {'metadata':{'usage':{'inputTokens':10,'outputTokens':5,'totalTokens':15}}}
        yield {'messageStop':{'stopReason':'end_turn'}}
    monkeypatch.setattr(c.BedrockModel,'stream',fake_stream)
    model=object.__new__(c.RecordedBedrockModel);ctx=context('centralized_orchestration');model.set_recorder(ctx,'supervisor')
    async def run():
        for i in range(20):
            async for e in model.stream([]):pass
        with pytest.raises(c.ExperimentLimitExceeded):
            async for e in model.stream([]):pass
    asyncio.run(run());events=[e for e in ctx.callbacks.events if e.event_family=='model']
    assert len(events)==40 and len({e.payload['callId'] for e in events})==20
    assert all(e.payload['usage']['totalTokens']==15 for e in events if e.event_name=='completed')

def test_judge_schema_blinding_null_and_boolean_validation():
    from app.experiments.methodology import judge_input
    case=cases()['cases'][2];payload=judge_input(case,'Resposta','blind')
    assert all(k not in payload for k in ('architecture','stratum','model','repetition','scenario_id'))
    value={'evaluation_id':'blind','response_id':'blind','criteria':[{'criterion_id':'C1','met':True,'evidence_refs':['E1','R1'],'reason':'ok'}],'quality':{d:5 for d in DIMENSIONS},'quality_reasons':{d:'ok' for d in DIMENSIONS},'referral_observed':False,'referral_evidence':'no referral','critical_violations':[],'evidence_insufficient':False,'insufficiency_reason':None,'review_reason_codes':[]}
    assert validate_evaluation(value,case,'blind')['quality']['safety']==5
    value['quality']['safety']=True
    with pytest.raises(ValueError):validate_evaluation(value,case,'blind')
    value['quality']['safety']=None;value['evidence_insufficient']=True
    with pytest.raises(ValueError):validate_evaluation(value,case,'blind')
    value['insufficiency_reason']='missing material';assert validate_evaluation(value,case,'blind')['quality']['safety'] is None

def test_no_favorable_retry_of_valid_evaluation_and_format_repair_preserves_raw(tmp_path,monkeypatch):
    import judge_automated_pilots as j
    case=cases()['cases'][2]
    value={'evaluation_id':'blind','response_id':'blind','criteria':[{'criterion_id':'C1','met':False,'evidence_refs':['R1'],'reason':'wrong'}],'quality':{d:1 for d in DIMENSIONS},'quality_reasons':{d:'wrong' for d in DIMENSIONS},'referral_observed':False,'referral_evidence':'no','critical_violations':[],'evidence_insufficient':False,'insufficiency_reason':None,'review_reason_codes':[]}
    calls=[]
    monkeypatch.setattr(j,'converse',lambda *a,**k:calls.append(a) or ('```json\n'+json.dumps(value)+'\n```',{'inputTokens':1,'outputTokens':1,'totalTokens':2},'end_turn'))
    judged,aid=j.judge_once(tmp_path,{},case,'wrong','blind','test-engineering')
    assert len(calls)==1 and judged['criteria'][0]['met'] is False
    logs=j.read_jsonl(tmp_path/'judge-attempts.jsonl');assert logs[-1]['local_format_repair'] is True and logs[-1]['raw_output'].startswith('```')

def test_unresolved_referral_contradiction_is_unknown_not_generator_failure():
    from app.experiments.methodology import evaluator_consistency_issue
    case=cases()['cases'][7]
    e={'criteria':[{'criterion_id':c['criterion_id'],'met':True} for c in case['essential_requirements']], 'referral_observed':False,'critical_violations':[],'evidence_insufficient':False}
    o={'required_evidence':[{'met':True}], 'critical_violations':[]}
    assert evaluator_consistency_issue(case,e)
    assert aggregate(case,{'success':True},o,e)['task_success'] is None
    e['referral_observed']=True
    assert aggregate(case,{'success':True},o,e)['task_success'] is True
    e['referral_observed']=False
    e['criteria'][1]['met']=False
    assert not evaluator_consistency_issue(case,e)
    assert aggregate(case,{'success':True},o,e)['task_success'] is False

def test_llm_attachment_initial_context_identical_between_fresh_conversations(monkeypatch):
    case=cases()['cases'][4];unit=build_order([case],1,1,'00000000-0000-0000-0000-000000000001')[0]
    prompts=[]
    monkeypatch.setattr(c,'ControlledAgent',lambda *a,**k:lambda prompt:prompts.append(prompt) or 'Resposta de engenharia')
    requests=[]
    for i in range(2):
        req=make_request(case,unit,'x');requests.append(req)
        ctx=context('centralized_orchestration');ctx.request=req;c.execute_comparison(ctx,'centralized_orchestration')
    assert requests[0].conversation_id!=requests[1].conversation_id
    assert requests[0].latest_message.id!=requests[1].latest_message.id
    assert prompts[0]==prompts[1]
    assert 'messageId' not in prompts[0] and 'retrievalUrl' not in prompts[0]
    assert 'attachment-1' in prompts[0]

def test_targeted_review_import_is_separate_and_never_overwrites(tmp_path):
    import csv
    from import_focused_reviews import import_reviews
    (tmp_path/'optional-pharmacist-audit.json').write_text(json.dumps({'selected_response_ids':['r1']}))
    (tmp_path/'evaluations.jsonl').write_text('original automated label\n')
    path=tmp_path/'human.csv';row={'response_id':'r1','reviewer_id':'pharmacist_1','safety':'NA','referral_observed':'true','critical_violation_suspected':'false','reason':'Auditoria focalizada, dado insuficiente para nota ordinal'}
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    assert import_reviews(tmp_path,path)==1
    assert (tmp_path/'evaluations.jsonl').read_text()=='original automated label\n'
    assert json.loads((tmp_path/'human-focused-reviews.jsonl').read_text())['safety'] is None
    with pytest.raises(ValueError):import_reviews(tmp_path,path)
