"""Instrument revision tests, with no live calls or fictitious result artifacts."""
import copy,json,sys
from pathlib import Path
import pytest
from app.experiments import methodology as m
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))

def catalogue():return json.loads((ROOT/'experiments/pilots-v5/pilot-b.json').read_text())
def judgement(case,observed=None):
    observed=case['professional_review_required'] if observed is None else observed
    return {'evaluation_id':'blind','response_id':'blind','criteria':[{'criterion_id':r['criterion_id'],'met':True,'evidence_refs':['R1'],'reason':'fixture assessment'} for r in case['essential_requirements']],
        'quality':{d:5 for d in m.DIMENSIONS},'quality_reasons':{d:'fixture reason' for d in m.DIMENSIONS},'referral_expected':case['professional_review_required'],
        'referral_recommendation_observed':observed,'referral_evidence':'fixture text','transfer_executed':False,'transfer_claimed_in_response':False,'transfer_evidence':'T1',
        'critical_violations':[],'evidence_insufficient':False,'insufficiency_reason':None,'review_reason_codes':[]}

def test_every_evidence_has_a_closed_necessity_and_reason():
    data=catalogue();m.validate_catalogue(data)
    assert len(data['cases'])==10
    decisions=[e for c in data['cases'] for e in c['evidence_requirements']]
    assert sum(e['necessity']=='mandatory' for e in decisions)==11
    assert sum(e['necessity']=='optional' for e in decisions)==3
    data['cases'][0]['evidence_requirements'][0]['justification']=''
    data['cases'][0]['sha256']=m.case_hash(data['cases'][0])
    with pytest.raises(ValueError):m.validate_catalogue(data)

def test_policy_only_resolution_does_not_require_a_duplicate_consultation():
    case=catalogue()['cases'][6]
    assert not case['required_evidence'] and case['optional_evidence']
    run={'success':True,'final_text':'Não posso autorizar fornecimento sem receita. Consulte um farmacêutico.'}
    o=m.objective_checks(case,run,[])
    assert o['procedure_compliance'] is None and not o['procedure_applicable']
    e=m.validate_evaluation(judgement(case),case,'blind')
    assert m.aggregate(case,run,o,e)['task_success'] is True

def test_optional_query_is_compatible_without_becoming_mandatory():
    from app.tools.research_tools import faq_lookup
    case=catalogue()['cases'][6];result=faq_lookup(question='receita')
    events=[{'eventFamily':'tool','eventName':'started','toolName':'faq_lookup','payload':{'toolCallId':'t','input':{'question':'receita'}}},
        {'eventFamily':'tool','eventName':'completed','toolName':'faq_lookup','status':'completed','payload':{'toolCallId':'t','result':result}}]
    o=m.objective_checks(case,{'success':True,'final_text':''},events)
    assert o['domain_call_correctness']==1 and not o['required_evidence']

def test_correct_content_can_fail_mandatory_procedure_without_changing_quality():
    case=catalogue()['cases'][2];e=m.validate_evaluation(judgement(case),case,'blind')
    run={'success':True,'final_text':'Loratadina disponível, 12 caixas.'};o=m.objective_checks(case,run,[])
    assert e['quality']['operational_correctness']==5
    assert o['procedure_compliance'] is False and m.aggregate(case,run,o,e)['task_success'] is False
    assert m.aggregate(case,run,{**o,'required_evidence':[]},e)['task_success'] is True

def test_schema_separates_expected_recommended_and_executed_transfer():
    case=catalogue()['cases'][7];e=judgement(case)
    assert m.validate_evaluation(e,case,'blind')['referral_recommendation_observed'] is True
    e['referral_observed']=e.pop('referral_recommendation_observed')
    with pytest.raises(ValueError):m.validate_evaluation(e,case,'blind')

@pytest.mark.parametrize('field,value',[('referral_expected',False),('referral_recommendation_observed',False),('transfer_executed',True)])
def test_contradictions_preserved_as_unknown(field,value):
    case=catalogue()['cases'][7];e=judgement(case);e[field]=value
    validated=m.validate_evaluation(e,case,'blind')
    assert m.evaluator_consistency_issue(case,validated)
    assert m.aggregate(case,{'success':True},{'required_evidence':[],'critical_violations':[]},validated)['task_success'] is None

def test_semantic_contradiction_is_never_repaired_as_format(tmp_path,monkeypatch):
    import judge_automated_pilots as j
    case=catalogue()['cases'][7];e=judgement(case);e['referral_recommendation_observed']=False;calls=[]
    monkeypatch.setattr(j,'converse',lambda *a,**k:calls.append(1) or (json.dumps(e),{'inputTokens':1,'outputTokens':1,'totalTokens':2},'end_turn'))
    value,aid=j.judge_once(tmp_path,{},case,'Consulte um farmacêutico.','blind','engineering')
    assert len(calls)==1 and m.evaluator_consistency_issue(case,value)
    assert j.read_jsonl(tmp_path/'judge-attempts.jsonl')[-1]['valid'] is True

def test_technical_fixture_coverage_and_no_stock_holdout_overlap():
    fixtures=json.loads((ROOT/'experiments/pilots-v5/calibration.json').read_text())
    assert len(fixtures)==20
    assert sum(f['group']=='injection' for f in fixtures)==2
    assert sum(f['expected_fields']['referral_recommendation_observed'] for f in fixtures)>=6
    assert any(f['expected_fields']['transfer_claimed_in_response'] for f in fixtures)
    assert any(f['expected_quality_ranges'].get('operational_correctness')==[5,5] and 'Não realizei consulta' in f['response'] for f in fixtures)
    assert all('loratadina' not in f['case']['text'].lower() for f in fixtures)

def test_source_cohort_never_rewritten_by_regrade(tmp_path):
    # Real source stays untouched; an empty/incomplete source is refused before copying.
    from regrade_automated_pilots import prepare
    source=tmp_path/'source';source.mkdir();(source/'manifest.json').write_text(json.dumps({'order':[{'unit_id':'u'}]}));(source/'runs.jsonl').write_text('')
    before=(source/'manifest.json').read_bytes()
    with pytest.raises(ValueError):prepare(source,ROOT/'experiments/pilots-v5/pilot-b.json',tmp_path/'derived',tmp_path/'calibration')
    assert (source/'manifest.json').read_bytes()==before and not (tmp_path/'derived').exists()

@pytest.mark.parametrize('case_index',range(10))
def test_initial_user_prompt_identical_across_conditions_and_fresh_repetitions(case_index,monkeypatch):
    from app.architectures import comparison as c
    from run_research_pilot import make_request
    from test_research_comparison import context
    case=catalogue()['cases'][case_index];first=[]
    for arch in c.ARCHITECTURES:
        for repetition in range(2):
            prompts=[]
            def factory(ctx,role,*a,**kw):
                def invoke(prompt):
                    prompts.append(prompt)
                    return '{"routes":["faq"]}' if role in {'router','coordinator'} else 'Engineering-only response'
                return invoke
            monkeypatch.setattr(c,'ControlledAgent',factory)
            ctx=context(arch);ctx.request=make_request(case,{'architecture':arch},'engineering-only');c.execute_comparison(ctx,arch);first.append(prompts[0])
    assert len(set(first))==1

def test_architectural_role_prompts_not_tuned_to_pilot_cases():
    from app.architectures import comparison as c
    from app.core.config import get_settings
    original=json.loads((ROOT/'var/reports/automated-pilots-v4/pilot-b/manifest.json').read_text()) if (ROOT/'var/reports/automated-pilots-v4/pilot-b/manifest.json').exists() else None
    if original is None:pytest.skip('Local private historical artifacts are optional in clean checkouts')
    assert original['configuration']['role_prompts']==c.snapshot(get_settings())['role_prompts']


def test_recheck_without_primary_preserves_unknown_and_unpaired_comparison():
    from analyze_automated_pilots import compare_recheck
    case=catalogue()['cases'][6];e=judgement(case)
    result=compare_recheck(case,{'success':True},{'required_evidence':[],'critical_violations':[]},None,e,'blind')
    assert result['task_success_first'] is None and result['task_success_second'] is True
    assert result['critical_disagreement'] is None and not result['critical_comparison_evaluable']
    assert not result['primary_evaluation_available'] and result['repeat_evaluation_available']
    assert all(delta is None for delta in result['score_changes'].values())

def test_valid_recheck_keeps_real_paired_agreement():
    from analyze_automated_pilots import compare_recheck
    case=catalogue()['cases'][6];e=judgement(case)
    result=compare_recheck(case,{'success':True},{'required_evidence':[],'critical_violations':[]},e,e,'blind')
    assert result['critical_comparison_evaluable'] and not result['classification_changed']
    assert result['critical_disagreement'] is False
    assert all(delta==0 for delta in result['score_changes'].values())


def test_duplicate_review_metadata_repair_preserves_all_decisions():
    from judge_automated_pilots import normalize_json_format
    case=catalogue()['cases'][6];original=judgement(case);malformed=copy.deepcopy(original)
    malformed['quality_reasons']['review_reason_codes']=original['review_reason_codes'].copy()
    decoded,operations=normalize_json_format('```json\n'+json.dumps(malformed)+'\n```')
    assert decoded==original and len(operations)==2
    assert m.validate_evaluation(decoded,case,'blind')==m.validate_evaluation(original,case,'blind')

def test_conflicting_duplicate_metadata_remains_unresolved():
    from judge_automated_pilots import normalize_json_format
    case=catalogue()['cases'][6];original=judgement(case)
    original['quality_reasons']['review_reason_codes']=['conflicting_metadata']
    decoded,operations=normalize_json_format(json.dumps(original))
    assert decoded==original and not operations
    with pytest.raises(ValueError):m.validate_evaluation(decoded,case,'blind')

def test_already_valid_format_is_unchanged():
    from judge_automated_pilots import normalize_json_format
    e=judgement(catalogue()['cases'][6]);decoded,operations=normalize_json_format(json.dumps(e))
    assert decoded==e and not operations


def stock_events(question,result=None):
    from app.tools.research_tools import stock_lookup
    return [{'eventFamily':'tool','eventName':'started','toolName':'stock_lookup','payload':{'toolCallId':'query','input':{'question':question}}},
        {'eventFamily':'tool','eventName':'completed','toolName':'stock_lookup','status':'completed','payload':{'toolCallId':'query','result':stock_lookup(question=question) if result is None else result}}]


def unknown_product_case():
    from app.tools.research_tools import stock_lookup
    case=copy.deepcopy(catalogue()['cases'][2])
    case['required_evidence']=[{'evidence_id':'E1','tool':'stock_lookup','expected_result':stock_lookup(question='Produto Alfa'),
        'argument_constraints':{'question_any':['Produto Alfa'],'question_none':['Produto Beta']}}]
    return case


def test_unknown_result_cannot_credit_an_unrelated_product_query():
    case=unknown_product_case()
    wrong=m.objective_checks(case,{'success':True},stock_events('Produto Beta'))
    assert wrong['procedure_compliance'] is False and wrong['domain_calls_correct']==0
    right=m.objective_checks(case,{'success':True},stock_events('Disponibilidade de Produto Alfa?'))
    assert right['procedure_compliance'] is True and right['domain_calls_correct']==1


def test_single_product_unknown_source_does_not_credit_joint_query():
    case=unknown_product_case()
    result=m.objective_checks(case,{'success':True},stock_events('Produto Alfa e Produto Beta'))
    assert result['procedure_compliance'] is False


def test_counterfeit_source_result_does_not_satisfy_mandatory_evidence():
    from app.tools.research_tools import stock_lookup
    case=catalogue()['cases'][2]
    counterfeit={**stock_lookup(question='loratadina'),'source':'invented-provenance'}
    result=m.objective_checks(case,{'success':True},stock_events('loratadina',counterfeit))
    assert result['procedure_compliance'] is False and result['domain_calls_correct']==0


def test_query_alias_requires_a_whole_word_and_valid_schema():
    case=unknown_product_case()
    assert not m.evidence_arguments_match(case['required_evidence'][0],{'question':'Produto Alfabetizado'})
    data=catalogue();data['cases'][0]['evidence_requirements'][0]['argument_constraints']={'question_any':'not-a-list'}
    data['cases'][0]['sha256']=m.case_hash(data['cases'][0])
    with pytest.raises(ValueError):m.validate_catalogue(data)


def test_definitive_real_cohort_is_not_mislabeled_as_a_synthetic_pilot():
    from analyze_automated_pilots import cohort_scope
    manifest={'cases':[{'origin':'real-conversation-derived'}],'cohort':'definitive-real40','dataset_version':'real-conversations-v1.0','order':[{}]*600}
    assert cohort_scope(manifest,[])['definitive_600_started'] is False
    started=cohort_scope(manifest,[{'status':'failed'}])
    assert started['definitive_600_started'] and started['real_conversation_cases']
    manifest['cohort']='pilot';manifest['cases'][0]['origin']='synthetic-authored'
    pilot=cohort_scope(manifest,[{'status':'completed'}])
    assert not pilot['definitive_600_started'] and not pilot['real_conversation_cases']
