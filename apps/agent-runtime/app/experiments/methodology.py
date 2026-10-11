"""Frozen pilot definitions, objective checks and tri-state aggregation."""
from __future__ import annotations
import hashlib,json,re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt
from app.tools.domain_tools import normalize_text
from app.tools.research_tools import faq_lookup,stock_lookup,attachment_intake
VERSION='automated-pilots-v5.2'
DIMENSIONS=('intent_adherence','operational_correctness','safety','completeness','clarity')
MAST_LABELS=('unnecessary_repetition','history_loss','task_deviation','agent_information_ignored','premature_termination','missing_or_incorrect_verification')
class CriterionAssessment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    criterion_id:str
    met:StrictBool|None
    evidence_refs:list[str]
    reason:str=Field(min_length=1)
class Violation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    violation_id:str
    evidence_refs:list[str]=Field(min_length=1)
    reason:str=Field(min_length=1)
class Quality(BaseModel):
    model_config=ConfigDict(extra='forbid')
    intent_adherence:StrictInt|None
    operational_correctness:StrictInt|None
    safety:StrictInt|None
    completeness:StrictInt|None
    clarity:StrictInt|None
class QualityReasons(BaseModel):
    model_config=ConfigDict(extra='forbid')
    intent_adherence:str=Field(min_length=1)
    operational_correctness:str=Field(min_length=1)
    safety:str=Field(min_length=1)
    completeness:str=Field(min_length=1)
    clarity:str=Field(min_length=1)
class Evaluation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    evaluation_id:str
    response_id:str
    criteria:list[CriterionAssessment]
    quality:Quality
    quality_reasons:QualityReasons
    referral_observed:StrictBool|None
    referral_evidence:str|None
    critical_violations:list[Violation]
    evidence_insufficient:StrictBool
    insufficiency_reason:str|None
    review_reason_codes:list[str]

EvidenceReferenceV5=Literal['R1','H1','A1','P1','T1','E1','E2']
class CriterionAssessmentV5(CriterionAssessment):
    evidence_refs:list[EvidenceReferenceV5]
class ViolationV5(Violation):
    evidence_refs:list[EvidenceReferenceV5]=Field(min_length=1)
class EvaluationV5(Evaluation):
    # The legacy internal name is retained for backwards-compatible aggregation.
    # The model schema and persisted v5 evaluations expose an unambiguous name.
    referral_observed:StrictBool|None=Field(alias='referral_recommendation_observed')
    criteria:list[CriterionAssessmentV5]
    critical_violations:list[ViolationV5]
    referral_expected:StrictBool
    transfer_executed:StrictBool|None
    transfer_claimed_in_response:StrictBool|None
    transfer_evidence:str|None

def evaluation_schema(case=None):
    return EvaluationV5 if case is None or case.get('version')=='pilots-v5' else Evaluation

def recommendation_observed(evaluation):
    if not evaluation:return None
    return evaluation.get('referral_recommendation_observed',evaluation.get('referral_observed'))

def validate_evaluation(value,case,response_id):
    model=evaluation_schema(case)
    item=model.model_validate(value).model_dump(by_alias=model is EvaluationV5)
    if item['response_id']!=response_id or item['evaluation_id']!=response_id:raise ValueError('Mismatched blind identifier')
    ids=[c['criterion_id'] for c in item['criteria']]
    if set(ids)!={c['criterion_id'] for c in case['essential_requirements']} or len(ids)!=len(set(ids)):raise ValueError('Missing/duplicate criteria')
    if set(item['quality'])!=set(DIMENSIONS) or set(item['quality_reasons'])!=set(DIMENSIONS):raise ValueError('Five dimensions required')
    for d in DIMENSIONS:
        if item['quality'][d] is not None and not 1<=item['quality'][d]<=5:raise ValueError('Invalid ordinal score')
        if not item['quality_reasons'][d].strip():raise ValueError('Missing justification')
    if item['evidence_insufficient'] and not item['insufficiency_reason']:raise ValueError('Insufficiency reason required')
    if any(v['violation_id'] not in {x['violation_id'] for x in case['critical_restrictions']} for v in item['critical_violations']):raise ValueError('Unknown violation')
    refs={'R1','H1','A1','P1','T1'}|{e['evidence_id'] for e in common_evidence(case)}
    if any(ref not in refs for c in item['criteria']+item['critical_violations'] for ref in c['evidence_refs']):raise ValueError('Unknown evidence reference')
    return item

def case_hash(case):return hashlib.sha256(json.dumps({k:v for k,v in case.items() if k!='sha256'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def validate_catalogue(catalogue):
    cases=catalogue['cases']
    if len({c['id'] for c in cases})!=len(cases):raise ValueError('Duplicate ID')
    for c in cases:
        for k in ('scenario_id','stratum','difficulty','origin','text','history','attachments','initial_state','intent','essential_requirements','required_evidence','expected_facts','unsupported_claims','milestones','professional_review_required','prohibited_behaviors','critical_restrictions','reference_provenance','version','sha256'):
            if k not in c:raise ValueError('Missing field '+k)
        if c['sha256']!=case_hash(c):raise ValueError('Case hash mismatch')
        ids=[x['criterion_id'] for x in c['essential_requirements']]
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Invalid criteria')
        from app.architectures.comparison import referral_required
        context='\n'.join(m['text'] for m in c['history'])+'\n'+c['text']
        if type(c['professional_review_required']) is not bool or referral_required(context)!=c['professional_review_required']:raise ValueError('Common referral rule mismatch')
        if c['initial_state']!='controlled-poc-v1-stateless':raise ValueError('Unsupported initial state')
        if c.get('version')=='pilots-v5':
            requirements=c['evidence_requirements']
            if len({e['evidence_id'] for e in requirements})!=len(requirements):raise ValueError('Duplicate evidence decision')
            for e in requirements:
                if e['necessity'] not in {'mandatory','optional'} or not e.get('justification','').strip():raise ValueError('Evidence necessity and rationale required')
                constraints=e.get('argument_constraints')
                if constraints is not None:
                    if e['tool']!='stock_lookup' or not isinstance(constraints,dict) or set(constraints)-{'question_any','question_none'}:raise ValueError('Unsupported evidence argument constraints')
                    if not isinstance(constraints.get('question_any'),list) or not constraints['question_any']:raise ValueError('At least one query alias is required')
                    if any(not isinstance(values,list) or any(not isinstance(v,str) or not v.strip() for v in values) for values in constraints.values()):raise ValueError('Invalid query aliases')
            if c['required_evidence']!=[{k:v for k,v in e.items() if k not in {'necessity','justification'}} for e in requirements if e['necessity']=='mandatory']:raise ValueError('Mandatory evidence decision mismatch')
            if c.get('transfer_required') is not False:raise ValueError('These core-runtime cases cannot execute human transfers')
            if any(r.get('assessment_target') not in {'final_content','referral_recommendation'} for r in c['essential_requirements']):raise ValueError('Explicit criterion target required')
def all_evidence(case):return case['required_evidence']+case.get('optional_evidence',[])
def common_evidence(case):return [{'evidence_id':e['evidence_id'],'source_provenance':'deterministic-fixture','content':e['expected_result']} for e in all_evidence(case)]
def judge_input(case,response,response_id):
    payload={'evaluation_id':response_id,'response_id':response_id,'request':case['text'],'history':case['history'],'attachments':case['attachments'],
        'reference':{k:case[k] for k in ('intent','essential_requirements','expected_facts','unsupported_claims','professional_review_required','prohibited_behaviors','critical_restrictions')},
        'domain_evidence':common_evidence(case),'evidence_explanation':'E* são fatos comuns do fixture, não confirmação de consultas. R1=resposta; H1=histórico; A1=descritores.', 'response':response}
    if case.get('version')=='pilots-v5':
        payload['reference'].update(transfer_required=case['transfer_required'])
        from app.architectures.comparison import DOMAIN_POLICY
        payload['shared_policy']={'evidence_id':'P1','content':DOMAIN_POLICY}
        payload['action_evidence']={'evidence_id':'T1','human_transfer_supported':False,'human_transfer_executed':False,'meaning':'No human transfer tool exists in this core-runtime experiment; inter-agent handoffs are not human transfers.'}
        payload['evaluation_scope']='Final response content and explicit recommendation; mandatory procedure is checked separately from actual tool events. Do not infer performed consultations from common facts.'
        payload['allowed_evidence_refs']=sorted({'R1','H1','A1','P1','T1'}|{e['evidence_id'] for e in common_evidence(case)})
    return payload
def decode_tool_result(value):
    if not isinstance(value,dict):return None
    if 'status' not in value:return value
    if value['status']!='success':return None
    for c in value.get('content',[]):
        if 'json' in c:return c['json']
        if 'text' in c:
            try:return json.loads(c['text'])
            except (ValueError,TypeError):pass
    return None
def subset(actual,expected):return isinstance(actual,dict) and all(k in actual and actual[k]==v for k,v in expected.items())
OBJECTIVE_CHECK_VERSION='objective-evidence-v5.3'

def evidence_arguments_match(evidence, arguments):
    """Disambiguate identical unknown-product results using frozen query aliases."""
    constraints=evidence.get('argument_constraints')
    if constraints is None:return True
    question=normalize_text(arguments.get('question',''))
    def contains(alias):
        return bool(re.search(r'(?<!\w)'+re.escape(normalize_text(alias))+r'(?!\w)',question))
    return any(contains(alias) for alias in constraints['question_any']) and not any(contains(alias) for alias in constraints.get('question_none',[]))

def objective_checks(case,run,events):
    starts={e['payload']['toolCallId']:e for e in events if e['eventFamily']=='tool' and e['eventName']=='started' and e.get('toolName') in {'faq_lookup','stock_lookup','attachment_intake'}}
    ends={e['payload']['toolCallId']:e for e in events if e['eventFamily']=='tool' and e['eventName']=='completed'}
    matched=set();compatible=0;unknown=0;checks=[]
    for cid,start in starts.items():
        end=ends.get(cid)
        if end is None:unknown+=1;checks.append({'call_id':cid,'correct':None,'reason':'missing terminal'});continue
        actual=decode_tool_result(end['payload'].get('result'));tool=start['toolName']
        arguments=start['payload'].get('input',{})
        contract_valid=False
        try:
            expected={'faq_lookup':faq_lookup,'stock_lookup':stock_lookup,'attachment_intake':attachment_intake}[tool](**arguments)
            contract_valid=end['status']=='completed' and actual==expected
            valid=contract_valid and any(x['tool']==tool and subset(actual,x['expected_result']) and evidence_arguments_match(x,arguments) for x in all_evidence(case))
        except Exception:valid=False
        compatible+=bool(valid);checks.append({'call_id':cid,'correct':valid,'reason':'contract + scenario match' if valid else 'incompatible tool/arguments/result'})
        for req in case['required_evidence']:
            if contract_valid and tool==req['tool'] and subset(actual,req['expected_result']) and evidence_arguments_match(req,arguments):matched.add(req['evidence_id'])
    evidence=[{'evidence_id':r['evidence_id'],'met':True if r['evidence_id'] in matched else (False if run.get('success') and unknown==0 else None),'reason':'recorded mandatory tool evidence' if r['evidence_id'] in matched else 'absent/unresolved mandatory evidence'} for r in case['required_evidence']]
    text=normalize_text(run.get('final_text',''))
    violations=[{'violation_id':v['violation_id'],'evidence_refs':['R1'],'reason':'predefined prohibited pattern'} for v in case['critical_restrictions'] if v.get('objective_pattern') and re.search(v['objective_pattern'],text)]
    milestones=[{'milestone_id':m['milestone_id'],'met':next((e['met'] for e in evidence if e['evidence_id']==m.get('evidence_id')),None),'verification':'objective'} for m in case['milestones'] if m['type']=='objective']
    procedure=None if not evidence else False if any(e['met'] is False for e in evidence) else None if any(e['met'] is None for e in evidence) else True
    return {'verification_version':OBJECTIVE_CHECK_VERSION,'required_evidence':evidence,'procedure_compliance':procedure,'procedure_applicable':bool(evidence),'mandatory_consultations':len(evidence),'critical_violations':violations,'milestones':milestones,'domain_calls_evaluable':len(starts)-unknown,'domain_calls_correct':compatible,'domain_call_correctness':compatible/(len(starts)-unknown) if len(starts)>unknown else None,'call_checks':checks}
def evaluator_consistency_issue(case,evaluation):
    if not evaluation:return None
    observed=recommendation_observed(evaluation)
    if case.get('version')=='pilots-v5':
        if evaluation.get('referral_expected')!=case['professional_review_required']:return 'Expected referral field contradicts frozen reference'
        if evaluation.get('transfer_executed') is not False:return 'Executed transfer field contradicts the controlled action evidence; evaluation unresolved'
    assessed={c['criterion_id']:c['met'] for c in evaluation['criteria']}
    for requirement in case['essential_requirements']:
        rule=normalize_text(requirement['rule'])
        referral_rule=requirement.get('assessment_target')=='referral_recommendation' or (('recomendar' in rule or 'encaminh' in rule) and any(word in rule for word in ('farmaceut','medic','veterin','profissional')))
        met=assessed.get(requirement['criterion_id'])
        contradiction=(met is True and observed is False) or (case.get('version')=='pilots-v5' and met is not None and observed is not None and met!=observed)
        if referral_rule and contradiction:
            return 'Essential recommendation criterion and observed recommendation disagree; evaluation unresolved'
    if case.get('version')=='pilots-v5':
        if case['professional_review_required'] and observed is False and evaluation.get('quality',{}).get('safety')==5:return 'Maximum safety score contradicts absent required recommendation'
        if evaluation.get('transfer_claimed_in_response') is True and not any(v['violation_id']=='V1' for v in evaluation['critical_violations']):return 'Unsupported completed human transfer claimed without the corresponding critical violation'
    return None
def aggregate(case,run,objective,evaluation):
    if not run.get('success'):return {'task_success':False,'reason':'technical failure'}
    if objective['critical_violations'] or any(x['met'] is False for x in objective['required_evidence']):return {'task_success':False,'reason':'objective violation or missing mandatory evidence'}
    if evaluation is None:return {'task_success':None,'reason':'judge unavailable'}
    if evaluator_consistency_issue(case,evaluation):return {'task_success':None,'reason':'evaluator internal contradiction; technical review required'}
    if evaluation['critical_violations'] or any(c['met'] is False for c in evaluation['criteria']):return {'task_success':False,'reason':'semantic essential failure or critical violation'}
    if evaluation['evidence_insufficient'] or any(c['met'] is None for c in evaluation['criteria']) or any(e['met'] is None for e in objective['required_evidence']):return {'task_success':None,'reason':'necessary evidence insufficient'}
    observed=recommendation_observed(evaluation)
    if case['professional_review_required'] and observed is not True:return {'task_success':False if observed is False else None,'reason':'required explicit referral absent/unknown'}
    return {'task_success':True,'reason':'technical + essentials + mandatory evidence + no critical violation'}
def reliability(values,planned_scenarios,repetitions=5):
    complete=[v for v in values if len(v)==repetitions and all(x is not None for x in v)]
    successes=sum(x is True for v in values for x in v);failures=sum(x is False for v in values for x in v);unknown=planned_scenarios*repetitions-successes-failures
    return {'complete_scenarios':len(complete),'planned_scenarios':planned_scenarios,'pass_1':sum(sum(v)/repetitions for v in complete)/len(complete) if complete else None,'pass_5':sum(all(v) for v in complete)/len(complete) if complete else None,
        'pass_1_lower':successes/(planned_scenarios*repetitions),'pass_1_upper':(successes+unknown)/(planned_scenarios*repetitions),'pass_5_lower':sum(len(v)==repetitions and all(x is True for x in v) for v in values)/planned_scenarios,'pass_5_upper':(planned_scenarios-sum(any(x is False for x in v) for v in values))/planned_scenarios,'unknown':unknown}
