import { expect, test } from "@playwright/test";

import { installMockEventSource, mockFrontendApi, mockIds } from "./support/mock-runtime-fixtures";

/**
 * Regression tests for the four chat-experience bugs reported in 2026-06.
 *
 * Bug 1: streaming bubble disappeared for ~1s after response.final and
 *        before refreshConversationDetail completed.
 * Bug 2: previous-turn outbound messages disappeared on the second send
 *        (multi-architecture filter only kept inbound + currently streaming).
 * Bug 3: switching architecture tabs left the chat blank until the user
 *        toggled away and back, because filteredMessages had nothing to
 *        show for the just-selected architecture.
 * Bug 4: SwarmFlow kept blue "active" arrows after the run had finished
 *        because edgeStateFromEvents ignored the terminal flag when an
 *        explicit handoff event still had status="running".
 */

test.describe("Regression — multi-architecture message visibility (bugs #2, #3)", () => {
  test("filters outbound messages by selected architecture's runtimeRunId", async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    const NOW = "2026-04-29T03:54:36.000Z";
    const conversationId = "55555555-5555-4555-8555-555555555555";
    const centralRunId = "55555555-1111-4111-8111-111111111111";
    const workflowRunId = "55555555-2222-4222-8222-222222222222";
    const swarmRunId = "55555555-3333-4333-8333-333333333333";

    const buildRunFixture = (id: string, key: string, status: string) => ({
      id,
      conversationId,
      messageId: `${conversationId}-inbound`,
      correlationId: `corr-${conversationId}-1`,
      aiSessionId: null,
      createdAt: NOW,
      updatedAt: NOW,
      startedAt: NOW,
      finishedAt: NOW,
      status,
      totalDurationMs: 1000,
      experiment: { architectureKey: key, comparisonOnly: key !== "centralized_orchestration" },
      summary: {},
    });

    const buildOutbound = (runId: string, key: string, body: string) => ({
      contentText: body,
      conversationId,
      correlationId: `corr-${conversationId}-1`,
      createdAtClient: NOW,
      createdAtServer: NOW,
      direction: "outbound",
      id: `${runId}-outbound`,
      metadata: { runtimeRunId: runId, architectureMode: key },
      status: "completed",
    });

    // Override conversation detail and runs/<id>/execution endpoints with
    // a fixture containing one inbound + three architecture-tagged outbound
    // messages. The filter under test must show only the outbound that
    // belongs to the selected architecture.
    await page.route(/^https?:\/\/(127\.0\.0\.1|localhost):8000\/conversations\/[^/]+$/, async (route) => {
      const url = new URL(route.request().url());
      if (!url.pathname.endsWith(conversationId)) {
        await route.continue();
        return;
      }
      const body = {
        attachments: [],
        conversation: {
          id: conversationId,
          channel: "web_chat",
          createdAt: NOW,
          updatedAt: NOW,
          status: "completed",
          userSessionId: "session-multi-arch",
          metadata: { architectureMode: "all_architectures" },
        },
        events: [],
        messages: [
          {
            contentText: "Quero comparar arquiteturas.",
            conversationId,
            correlationId: `corr-${conversationId}-1`,
            createdAtClient: NOW,
            createdAtServer: NOW,
            direction: "inbound",
            id: `${conversationId}-inbound`,
            metadata: {},
            status: "completed",
          },
          buildOutbound(centralRunId, "centralized_orchestration", "Resposta CENTRALIZED Orchestration aqui."),
          buildOutbound(workflowRunId, "structured_workflow", "Resposta STRUCTURED Workflow aqui."),
          buildOutbound(swarmRunId, "decentralized_swarm", "Resposta DECENTRALIZED Swarm aqui."),
        ],
        reviewTasks: [],
        runs: [
          buildRunFixture(centralRunId, "centralized_orchestration", "completed"),
          buildRunFixture(workflowRunId, "structured_workflow", "completed"),
          buildRunFixture(swarmRunId, "decentralized_swarm", "completed"),
        ],
      };
      await route.fulfill({
        body: JSON.stringify(body),
        contentType: "application/json",
        status: 200,
      });
    });
    await page.route(/^https?:\/\/(127\.0\.0\.1|localhost):8000\/runs\/[^/]+\/execution$/, async (route) => {
      const url = new URL(route.request().url());
      const runId = url.pathname.split("/")[2];
      const isCentral = runId === centralRunId;
      const body = {
        executionEvents: [],
        projection: {
          activeActorName: null,
          activeNodeId: null,
          architectureMode: isCentral
            ? "centralized_orchestration"
            : runId === workflowRunId
              ? "structured_workflow"
              : "decentralized_swarm",
          architectureView: { actors: {}, handoffs: [], stages: [] },
          conversationId,
          currentPhase: "completed",
          messageId: `${conversationId}-inbound`,
          metrics: { eventCount: 0, handoffCount: 0, toolCallCount: 0 },
          runId,
          runStatus: "completed",
          source: "mock",
          state: {},
          updatedAt: NOW,
        },
        run: buildRunFixture(
          runId,
          isCentral ? "centralized_orchestration" : runId === workflowRunId ? "structured_workflow" : "decentralized_swarm",
          "completed",
        ),
      };
      await route.fulfill({ body: JSON.stringify(body), contentType: "application/json", status: 200 });
    });

    await page.goto(`/?conversationId=${conversationId}`);
    const list = page.getByTestId("message-list");
    await expect(list).toBeVisible();
    // The architecture picker should be visible (3 runs).
    await expect(list).toContainText("Quero comparar arquiteturas.");

    // Default selection is centralized_orchestration (first run).
    await expect(list).toContainText("CENTRALIZED Orchestration");
    await expect(list).not.toContainText("STRUCTURED Workflow");
    await expect(list).not.toContainText("DECENTRALIZED Swarm");

    // Switch to the workflow architecture tab.
    await page.getByRole("button", { name: /Workflow estruturado/i }).click();
    await expect(list).toContainText("STRUCTURED Workflow");
    await expect(list).not.toContainText("CENTRALIZED Orchestration");
    await expect(list).not.toContainText("DECENTRALIZED Swarm");

    // Switch to the swarm tab.
    await page.getByRole("button", { name: /Swarm descentralizado/i }).click();
    await expect(list).toContainText("DECENTRALIZED Swarm");
    await expect(list).not.toContainText("CENTRALIZED Orchestration");
    await expect(list).not.toContainText("STRUCTURED Workflow");
  });

  test("streaming bubble keeps content after response.final until refresh lands", async ({ page }) => {
    // Inject an EventSource that fires partials, then a response.final,
    // and verify the streaming bubble never goes blank between the
    // partial and the persisted outbound landing via refresh.
    await installMockEventSource(page);
    await mockFrontendApi(page);

    await page.addInitScript(() => {
      const Original = window.EventSource;
      class StreamThenFinalEventSource extends Original {
        constructor(url: string) {
          super(url);
          queueMicrotask(() => {
            const conversationId = url.match(/conversations\/([^/]+)/)?.[1] ?? "";
            const runId = "regression-stream-run";
            const partial = {
              id: "stream-partial-1",
              conversationId,
              messageId: null,
              eventType: "response.partial",
              actorName: "response_streamer",
              parentEventId: null,
              correlationId: "corr-stream-1",
              payload: { contentText: "Resposta em andamento", runId },
              createdAt: new Date().toISOString(),
              durationMs: null,
              status: "running",
            };
            const finalEvent = {
              id: "stream-final-1",
              conversationId,
              messageId: null,
              eventType: "response.final",
              actorName: "response_streamer",
              parentEventId: null,
              correlationId: "corr-stream-1",
              payload: { contentText: "Resposta completa final", runId },
              createdAt: new Date().toISOString(),
              durationMs: 250,
              status: "completed",
            };
            const dispatch = (evt: object) => {
              const listeners = (this as unknown as { listeners: Map<string, Array<(e: MessageEvent) => void>> }).listeners;
              for (const listener of listeners.get("processing.event") ?? []) {
                listener(new MessageEvent("processing.event", { data: JSON.stringify(evt) }));
              }
            };
            setTimeout(() => dispatch(partial), 80);
            setTimeout(() => dispatch(finalEvent), 200);
          });
        }
      }
      Object.defineProperty(window, "EventSource", {
        configurable: true,
        value: StreamThenFinalEventSource,
        writable: true,
      });
    });

    await page.goto(`/?conversationId=${mockIds.centralizedConversation}`);
    const list = page.getByTestId("message-list");
    await expect(list).toBeVisible();
    // Wait for the streaming text to appear...
    await expect(list).toContainText("Resposta em andamento", { timeout: 4000 });
    // ...and ensure the final text replaces it without a blank gap. The
    // bubble must still display *something* the moment response.final fires.
    await expect(list).toContainText("Resposta completa final", { timeout: 4000 });
  });
});

test.describe("Regression — SwarmFlow settles when run completes (bug #4)", () => {
  test("swarm flow does not animate edges when run is terminal even if handoff status is still 'running'", async ({ page }) => {
    await installMockEventSource(page);
    await mockFrontendApi(page);

    // Override the runs/<swarmRun>/execution response to embed a handoff
    // event whose status is still "running" while the run as a whole is
    // already "completed". Before the fix this would render a blue,
    // animated edge (state = "active") because edgeStateFromEvents
    // ignored the terminal flag in the explicit-handoff branch.
    await page.route(/^https?:\/\/(127\.0\.0\.1|localhost):8000\/runs\/[^/]+\/execution$/, async (route) => {
      const NOW = "2026-04-29T03:54:36.000Z";
      const runId = mockIds.swarmRun;
      const conversationId = mockIds.swarmConversation;
      const mkEvent = (
        seq: number,
        family: string,
        name: string,
        status: string,
        actorName: string,
        payload: Record<string, unknown> = {},
      ) => ({
        actorName,
        conversationId,
        correlationId: `corr-${conversationId}-1`,
        createdAt: NOW,
        durationMs: 100,
        eventFamily: family,
        eventName: name,
        externalEventId: null,
        id: `${runId}-event-${seq}`,
        messageId: `${conversationId}-inbound`,
        nodeId: `${actorName}-node`,
        payload,
        runId,
        sequenceNo: seq,
        source: "mock",
        status,
        toolName: null,
      });
      const body = {
        executionEvents: [
          mkEvent(1, "node", "started", "completed", "swarm_coordinator"),
          // Handoff event whose status is still RUNNING — exactly the
          // scenario that triggered the bug.
          mkEvent(2, "handoff", "requested", "running", "swarm_coordinator", {
            from: "swarm_coordinator",
            to: "faq_specialist",
          }),
          mkEvent(3, "node", "completed", "completed", "faq_specialist"),
          mkEvent(4, "response", "final", "completed", "swarm_synthesizer", {
            contentText: "Final swarm response",
          }),
        ],
        projection: {
          activeActorName: null,
          activeNodeId: null,
          architectureMode: "decentralized_swarm",
          architectureView: {
            actors: {
              coordinator: { actorName: "swarm_coordinator", nodeId: "coord-node", status: "completed" },
              faq: { actorName: "faq_specialist", nodeId: "faq-node", status: "completed" },
              synth: { actorName: "swarm_synthesizer", nodeId: "synth-node", status: "completed" },
            },
            handoffs: [{ payload: { from: "swarm_coordinator", to: "faq_specialist" }, status: "running" }],
            stages: [],
          },
          conversationId,
          currentPhase: "completed",
          messageId: `${conversationId}-inbound`,
          metrics: { eventCount: 4, handoffCount: 1, toolCallCount: 0 },
          runId,
          runStatus: "completed",
          source: "mock",
          state: {},
          updatedAt: NOW,
        },
        run: {
          id: runId,
          conversationId,
          messageId: `${conversationId}-inbound`,
          correlationId: `corr-${conversationId}-1`,
          aiSessionId: null,
          createdAt: NOW,
          updatedAt: NOW,
          startedAt: NOW,
          finishedAt: NOW,
          status: "completed",
          totalDurationMs: 9500,
          experiment: { architectureKey: "decentralized_swarm" },
          summary: {},
        },
      };
      await route.fulfill({
        body: JSON.stringify(body),
        contentType: "application/json",
        status: 200,
      });
    });

    await page.goto(`/?conversationId=${mockIds.swarmConversation}`);
    await page.getByTestId("flow-toggle").click();
    await expect(page.getByTestId("runtime-visual-swarm")).toBeVisible();

    const flow = page.getByTestId("runtime-visual-swarm");
    await flow.waitFor();
    // After the fix, no edges should be animated when the run is terminal,
    // regardless of whether handoff event statuses were left at "running".
    // We assert there is no <animateMotion> element under the swarm flow.
    const animateMotionCount = await flow.locator("svg animateMotion").count();
    expect(animateMotionCount).toBe(0);
  });
});
