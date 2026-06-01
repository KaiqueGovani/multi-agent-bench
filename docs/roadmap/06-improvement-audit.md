# Improvement Audit — 2026-06-01

Snapshot of improvement opportunities across the codebase, ordered by ROI. Captured for follow-up — no actions taken from this document.

Context: this is a TCC POC whose research goal is **comparing coordination architectures**. Anything that doesn't directly serve that goal should stay simple.

---

## High impact — tackle first

### 1. Deduplicate Pydantic schemas across the two services

`apps/api/app/schemas/` and `apps/agent-runtime/app/schemas/` define the same models twice with slight drift (`OperationalMetadata`, `RunExperimentMetadata`, dispatch payloads, etc.).

- Move shared models to a new `packages/python-contracts` package, install in both services.
- Generate the TS contracts in `packages/contracts/` from the Pydantic models (e.g. `datamodel-code-generator`) so there's one source of truth across all three apps.

### 2. Split `RunExecutionService._upsert_projection`

`apps/api/app/services/run_execution.py:222-341` — 120 lines mixing actor state machine, metric aggregation, and architecture-view rebuilding.

- Extract `_sync_actor_state`, `_accumulate_metrics`, `_rebuild_architecture_view`.
- This is the hottest path during live runs and the hardest to unit-test today (currently exercised only via integration tests that need a real DB).

### 3. Extract event-family → public-event mapping

`apps/api/app/services/run_execution.py:509-557` (`_derive_public_event`) is a hardcoded 11-entry table inside the persistence service.

- Move to a small `EventTranslator` with a typed registry.
- Adding a new family today requires touching both the runtime and the API; the registry pattern lets architectures add events without cross-cutting changes.

### 4. Surface dispatch failures to the UI

`apps/api/app/services/processing_dispatcher.py:56-63` plus the `urlopen` callbacks have bare `try/except` blocks that log and swallow.

- When the agent runtime dies mid-flight, the UI shows a stalled run forever.
- Emit a `DISPATCH_FAILED` event so the chat UI can render "agent runtime unreachable".
- Add at least one retry with exponential backoff. Distinguish `HTTPError` vs `URLError`.
- This is the only stability bug in the list — the rest are polish.

---

## Medium impact

### 5. Break up `architecture-flow.tsx` (922 lines)

`apps/web/src/components/runtime/architecture-flow.tsx` owns: the agent node component, hover popover, event timeline, edge styling, SVG marker defs, and three full architecture layouts (centralized, workflow, swarm).

- Extract `agent-node.tsx`, `event-timeline-popover.tsx`, `flow-layouts.ts`.
- Future architecture variants become drop-in additions. Hover logic gets isolated and unit-testable.

### 6. Move the mock runtime out of production code

`apps/api/app/runtime/mock/` still ships alongside the live dispatcher and is selected via the `RUNTIME_MODE` env var. The real runtime now exists; the mock has clearly outgrown its role.

- Move to `packages/test-fixtures/` or behind a `--mock-mode` CLI flag.
- Today the API races two execution paths over a single env switch; the frontend can't even tell which one is running.

### 7. Lift duplication out of architecture executors

`apps/agent-runtime/app/architectures/`:

- `_detect_review_required_in_text` is imported across centralized & swarm.
- `create_agent` builds BedrockModel + Strands Agent in three nearly-identical ways across centralized, workflow, swarm.
- Mock execution mirrors live execution patterns inside each file.

Lift these into `base.py` utilities. ~50 LOC saved per architecture, and **adding a new architecture is the whole point of this thesis**.

### 8. `useConversation` is the frontend twin of `_upsert_projection`

`apps/web/src/hooks/use-conversation.ts` (562 lines) handles SSE subscription, polling, streaming message lifecycle, and refresh logic in one hook.

- Polling block at lines 288-304 fires fixed-interval refreshes (500ms / 1s / 2s / 3s) regardless of whether the data already arrived via SSE. Replace with a single "poll until `conversation.status === completed`, stop early, exponential backoff" loop.
- SSE error recovery (line 442) wipes all streaming messages on every transient disconnect — should retry first.
- Splitting into `useConversationState`, `useConversationEvents`, `useConversationRefresh` reduces cognitive load and unlocks unit tests.

---

## Lower priority

### 9. Type safety on event payloads

`event.payload` is `Record<string, unknown>` / `JsonObject` everywhere, narrowed by ad-hoc string checks at use site.

- Define a `ProcessingEventPayload` discriminated union keyed on `eventFamily` / `eventName`.
- TypeScript narrows the payload shape automatically; removes a class of "what's in this object" bugs.

### 10. SSE resilience has no tests

`apps/api` events router + `apps/web/src/lib/sse/events.ts` implement heartbeats, `Last-Event-ID` replay, and queue exhaustion handling — none of it is tested.

- Add Playwright tests that close the EventSource mid-stream and verify recovery.
- Add an API-level test for replay-from-`last_event_id` and heartbeat cadence.

### 11. Two more large UI components worth a pass

- `architecture-comparison-overview.tsx` (698 lines)
- `run-execution-panel.tsx`

Not urgent, but approaching god-component size. Watch for the same patterns that made `architecture-flow.tsx` grow: rendering + data shaping + UI state in one file.

---

## Suggested order

1. **#4** — only item that actively affects users today.
2. **#2 + #3 together** — `run_execution.py` cleanup + event translator. Unlocks unit testability and makes everything downstream safer.
3. **#1** — schema dedup. Highest long-term leverage but biggest blast radius; do it after the `run_execution` split.
4. The rest as time permits, prioritizing whatever the next architecture experiment touches.

---

## Other observations worth keeping in mind

- **Test pyramid is inverted.** API has 17 mostly-integration tests; runtime has ~88 unit-style tests; e2e quality suite exists but isn't in CI. Most cleanups in this list double as opportunities to add unit tests.
- **`RuntimeDispatchRequest` carries API credentials in its payload** (`processing_dispatcher.py:277`). Service-to-service auth via a header would be cleaner; it also lets credentials rotate without invalidating in-flight runs.
- **PT-BR strings are hardcoded throughout the web app.** Not a problem for the thesis, but if anyone wants to demo this in English later, retrofitting `next-intl` will cost more than introducing it now.
- **No accessibility on ReactFlow nodes/popovers.** Missing ARIA roles, no keyboard dismiss for the agent hover popover. Easy to add while `architecture-flow.tsx` is being split (#5).
