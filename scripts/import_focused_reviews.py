#!/usr/bin/env python3
"""Optional, targeted review import; never overwrites LLM labels or assumes consensus."""
from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
from datetime import datetime,UTC
from run_research_pilot import append,dump

def optional_bool(value):
    if value=='NA':return None
    if value not in {'true','false'}:raise ValueError('Use true, false or NA')
    return value=='true'
def import_reviews(folder,path):
    selected=set(json.loads((folder/'optional-pharmacist-audit.json').read_text())['selected_response_ids'])
    dest=folder/'human-focused-reviews.jsonl'
    previous=[json.loads(l) for l in dest.read_text().splitlines()] if dest.exists() else []
    seen={(r['response_id'],r['reviewer_id']) for r in previous};pending=[]
    with path.open(newline='') as f:
        for row in csv.DictReader(f):
            key=row['response_id'],row['reviewer_id']
            if key[0] not in selected or not re.fullmatch(r'[a-z0-9_-]{1,32}',key[1]) or key in seen:raise ValueError('Unknown response, non-pseudonymous or duplicate reviewer/response')
            if not row.get('reason','').strip():raise ValueError('Short reason required')
            score=None if row['safety']=='NA' else int(row['safety'])
            if score is not None and not 1<=score<=5:raise ValueError('Safety 1..5 or NA')
            pending.append({'response_id':key[0],'reviewer_id':key[1],'reviewer_role':'pharmacist','safety':score,'referral_observed':optional_bool(row['referral_observed']),
                'critical_violation_suspected':optional_bool(row['critical_violation_suspected']),'reason':row['reason'],'recorded_at':datetime.now(UTC).isoformat(),
                'provenance':'human-labels-provided-by-author','independent_evaluation_not_verified':True})
            seen.add(key)
    for row in pending:append(dest,row)
    all_rows=previous+pending
    dump(folder/'human-focused-review-summary.json',{'human_review_performed':bool(all_rows),'response_count':len({r['response_id'] for r in all_rows}),'reviewer_count':len({r['reviewer_id'] for r in all_rows}),
        'llm_labels_overwritten':False,'consensus_performed':False,'scope':'targeted audit; no representative error rate or general agreement estimate'})
    return len(pending)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('csv',type=Path);a=p.parse_args();print('Imported:',import_reviews(a.folder,a.csv))
