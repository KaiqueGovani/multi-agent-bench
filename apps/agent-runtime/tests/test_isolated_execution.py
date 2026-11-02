"""Actual process-boundary checks, independent of provider credentials."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from app.architectures.comparison import ExperimentLimitExceeded
from app.core.config import Settings
from app.services.execution import RuntimeExecutor
from app.services import isolated_execution as isolated
from test_research_comparison import Events
from test_runtime_service import build_request


def test_worker_round_trip_relays_events_and_result():
    events=Events()
    executor=RuntimeExecutor(build_request(),settings=Settings(enable_live_llm=False,runtime_timeout_seconds=10),callbacks=events)
    result=isolated.execute_isolated(executor)
    assert result.final_text.startswith("[modo mock]")
    assert any(e.event_family=="response" and e.event_name=="final" for e in events.events)


@pytest.mark.parametrize("cancel",[False,True,"signal_failure"])
def test_global_deadline_kills_worker_and_descendant_and_closes_open_events(monkeypatch,tmp_path,cancel):
    events=Events(); launched=[]; real_popen=subprocess.Popen
    if cancel is True:
        original_emit=events.emit_run_event
        def emit(event):
            original_emit(event)
            if event.event_family == "model" and event.event_name == "started":raise KeyboardInterrupt()
        events.emit_run_event=emit
    executor=RuntimeExecutor(build_request(),settings=Settings(enable_live_llm=True,runtime_timeout_seconds=0.5),callbacks=events)
    def popen(args,**kwargs):
        folder=Path(args[-1])
        # This fixture emulates a blocked provider worker and its nested process.
        script='''import json,os,subprocess,sys,time
from pathlib import Path
folder=Path(sys.argv[1]); output=Path(sys.argv[2])
task=json.loads((folder/'task.json').read_text()); request=task['request']
assert task['settings']['aws_bearer_token_bedrock'] is None
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
output.write_text(str(child.pid))
event={'runId':request['runId'],'conversationId':request['conversationId'],'messageId':request['messageId'],'correlationId':request['correlationId'],'eventFamily':'model','eventName':'started','status':'running','actorName':'faq','source':'ai_service','externalEventId':'controlled-open-call','payload':{'callId':'open-model','agentInvocationId':'nested-agent'}}
(folder/'events.jsonl').write_text(json.dumps(event)+'\\n')
time.sleep(30)
'''
        proc=real_popen([sys.executable,"-c",script,str(folder),str(tmp_path/"descendant.pid")],**kwargs)
        launched.append(proc);return proc
    monkeypatch.setattr(isolated.subprocess,"Popen",popen)
    if cancel == "signal_failure":
        real_killpg=os.killpg
        attempts=[]
        def killpg(pid,sig):
            attempts.append(pid)
            if len(attempts)==1:raise PermissionError("controlled signal rejection")
            return real_killpg(pid,sig)
        monkeypatch.setattr(isolated.os,"killpg",killpg)
    started=time.perf_counter()
    expected=isolated.RuntimeIsolationError if cancel == "signal_failure" else KeyboardInterrupt if cancel is True else ExperimentLimitExceeded
    with pytest.raises(expected):isolated.execute_isolated(executor)
    assert time.perf_counter()-started<2
    assert launched[0].poll() is not None
    descendant=int((tmp_path/"descendant.pid").read_text())
    status=subprocess.run(["ps","-o","stat=","-p",str(descendant)],capture_output=True,text=True).stdout.strip()
    assert not status or status.startswith("Z")  # terminated; may await OS reaping
    terminal=next(e for e in events.events if e.event_family=="model" and e.event_name=="failed")
    assert terminal.payload["callId"]=="open-model" and terminal.payload["usage"] is None
    assert terminal.payload["interrupted"]

    if cancel == "signal_failure":
        assert any(e.event_family == "run" and e.payload.get("reason") == "process_group_termination_failed" for e in events.events)
