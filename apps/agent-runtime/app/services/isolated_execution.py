"""Hard attempt deadline for live API requests, including nested SDK threads.

The direct benchmark transport already isolates each attempt in its own process.
The API uses this worker as well, so cancelling a future never leaves an inference
thread or nested specialist running in the application process.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

from app.architectures.base import ExecutionResult
from app.schemas.runtime import IngestRunExecutionEventRequest, RuntimeDispatchRequest


class RuntimeIsolationError(RuntimeError):
    """The worker could not be stopped with a verified process-group signal."""


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False))
    path.chmod(0o600)


def execute_isolated(executor):
    from app.architectures.comparison import ExperimentLimitExceeded
    root = Path(__file__).resolve().parents[2]
    deadline = executor.started_at + executor.settings.runtime_timeout_seconds
    with tempfile.TemporaryDirectory(prefix="mab-api-run-") as directory:
        folder = Path(directory)
        os.chmod(folder, 0o700)
        settings = asdict(executor.settings)
        # Provider credential is inherited through the environment, never serialized.
        settings["aws_bearer_token_bedrock"] = None
        _write(folder / "task.json", {"request":executor.request.model_dump(by_alias=True,mode="json"),
               "settings":settings,"trace_id":executor.trace_id})
        env = os.environ.copy()
        if executor.settings.aws_bearer_token_bedrock:
            env["AWS_BEARER_TOKEN_BEDROCK"] = executor.settings.aws_bearer_token_bedrock
        proc = subprocess.Popen([sys.executable,"-m","app.services.isolated_execution",str(folder)],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        timed_out = threading.Event()
        termination_lock = threading.Lock()
        termination_errors = []

        def stop_worker():
            # The deadline thread and main exception path must not signal/reap
            # the same process concurrently. Reaping can make its PID reusable.
            with termination_lock:
                if proc.poll() is not None:
                    return
                try:
                    os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:
                    # Benign only if the owned child really exited meanwhile.
                    if proc.poll() is None:
                        termination_errors.append(RuntimeIsolationError("Worker group disappeared while worker is still running"))
                except OSError as exc:
                    # Keep failures for the calling thread; never let a watchdog
                    # exception become an unobserved warning or success claim.
                    termination_errors.append(exc)
                else:
                    proc.wait()

        def stop_at_deadline():
            with termination_lock:
                running = proc.poll() is None
            if running:
                timed_out.set()
                stop_worker()

        def join_watchdog():
            watchdog.cancel()
            watchdog.join()

        # Callback persistence can block on HTTP; this independent watchdog still
        # stops inference at the global deadline while the parent relays events.
        watchdog = threading.Timer(max(0,deadline-time.perf_counter()),stop_at_deadline)
        watchdog.daemon = True
        watchdog.start()
        journal = folder / "events.jsonl"
        position, pending, observed = 0, "", []

        def relay():
            nonlocal position, pending
            if not journal.exists():
                return
            with journal.open() as stream:
                stream.seek(position)
                pending += stream.read()
                position = stream.tell()
            while "\n" in pending:
                line, pending = pending.split("\n",1)
                event = IngestRunExecutionEventRequest.model_validate_json(line)
                observed.append(event)
                executor.callbacks.emit_run_event(event)

        try:
            while proc.poll() is None:
                relay()
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    raise ExperimentLimitExceeded("Global attempt deadline exceeded")
                time.sleep(min(0.02,remaining))
            relay()
            if timed_out.is_set():
                raise ExperimentLimitExceeded("Global attempt deadline exceeded")
            result_path = folder / "result.json"
            if not result_path.exists():
                raise RuntimeError("Isolated runtime exited without a result")
            record = json.loads(result_path.read_text())
            if "error_type" in record:
                if record["error_type"] == "ExperimentLimitExceeded":
                    raise ExperimentLimitExceeded(record.get("message","Attempt limit exceeded"))
                raise RuntimeError("Isolated runtime failed: " + record["error_type"])
            return ExecutionResult(**record)
        except BaseException as exc:
            join_watchdog()
            stop_worker()
            if proc.poll() is None:
                # Best-effort local-child cleanup after an unsuccessful group
                # signal. Descendant termination remains explicitly unverified.
                proc.kill()
                proc.wait()
            relay()
            # Open physical requests remain unknown; never invent usage on cancellation.
            terminal = {(e.event_family,e.payload.get("callId") or e.payload.get("toolCallId"))
                for e in observed if e.event_name in {"completed","failed"}}
            from app.architectures.base import ExecutionContext
            ctx = ExecutionContext(executor.request,executor.callbacks,executor.settings,executor.started_at,executor.trace_id)
            for e in reversed(observed):
                call_id = e.payload.get("callId") or e.payload.get("toolCallId")
                if e.event_name == "started" and e.event_family in {"model","agent","tool"} and (e.event_family,call_id) not in terminal:
                    ctx.emit(e.event_family,"failed","failed",actor_name=e.actor_name,tool_name=e.tool_name,
                        payload={**e.payload,"errorType":type(exc).__name__,"interrupted":True,"usage":None})
            if isinstance(exc, ExperimentLimitExceeded):
                ctx.emit("limit","exceeded","failed",payload={"resource":"timeout","limit":executor.settings.runtime_timeout_seconds})
            if termination_errors:
                ctx.emit("run","failed","failed",payload={"reason":"process_group_termination_failed",
                    "errorTypes":[type(error).__name__ for error in termination_errors]})
                raise RuntimeIsolationError("Process-group termination failed; inspect descendant state") from termination_errors[0]
            raise
        finally:
            join_watchdog()
            if proc.poll() is None:
                stop_worker()
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            if termination_errors and sys.exc_info()[0] is None:
                raise RuntimeIsolationError("Process-group termination failed; inspect descendant state") from termination_errors[0]


def worker(folder):
    from app.core.config import Settings
    from app.services.execution import RuntimeExecutor
    task = json.loads((folder/"task.json").read_text())
    class Events:
        def emit_run_event(self,event):
            with (folder/"events.jsonl").open("a") as stream:
                stream.write(event.model_dump_json(by_alias=True)+"\n")
                stream.flush()
    try:
        result = RuntimeExecutor(RuntimeDispatchRequest.model_validate(task["request"]),
            settings=Settings(**task["settings"]),callbacks=Events()).execute()
        _write(folder/"result.json",asdict(result))
    except BaseException as exc:
        _write(folder/"result.json",{"error_type":type(exc).__name__,"message":str(exc) if type(exc).__name__=="ExperimentLimitExceeded" else "Runtime worker failed"})


if __name__ == "__main__":
    worker(Path(sys.argv[1]))
