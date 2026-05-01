import type { Page, Route } from "@playwright/test";

const API_BASE_URL = "http://127.0.0.1:8000";
const NOW = "2026-04-29T03:54:36.000Z";

export const mockIds = {
  centralizedConversation: "11111111-1111-4111-8111-111111111111",
  workflowConversation: "22222222-2222-4222-8222-222222222222",
  swarmConversation: "33333333-3333-4333-8333-333333333333",
  centralizedRun: "aaaa1111-1111-4111-8111-111111111111",
  draftConversation: "44444444-4444-4444-8444-444444444444",
  draftRun: "dddd4444-4444-4444-8444-444444444444",
  workflowRun: "bbbb2222-2222-4222-8222-222222222222",
  swarmRun: "cccc3333-3333-4333-8333-333333333333",
} as const;

const conversationSummaries = [
  {
    architectureMode: "centralized_orchestration",
    channel: "web_chat",
    conversationId: mockIds.centralizedConversation,
    eventCount: 9,
    lastMessage: "Tem dipirona em estoque?",
    latestRunId: mockIds.centralizedRun,
    messageCount: 2,
    reviewPending: false,
    status: "completed",
    updatedAt: NOW,
  },
  {
    architectureMode: "structured_workflow",
    channel: "web_chat",
    conversationId: mockIds.workflowConversation,
    eventCount: 8,
    lastMessage: "Analise esse PDF de receita.",
    latestRunId: mockIds.workflowRun,
    messageCount: 2,
    reviewPending: true,
    status: "human_review_required",
    updatedAt: NOW,
  },
  {
    architectureMode: "decentralized_swarm",
    channel: "web_chat",
    conversationId: mockIds.swarmConversation,
    eventCount: 10,
    lastMessage: "Tem dipirona em estoque?",
    latestRunId: mockIds.swarmRun,
    messageCount: 2,
    reviewPending: false,
    status: "completed",
    updatedAt: NOW,
  },
];

const architectureDistribution = [
  { averageRunDurationMs: 6200, count: 1, key: "centralized_orchestration" },
  { averageRunDurationMs: 8100, count: 1, key: "structured_workflow" },
  { averageRunDurationMs: 9500, count: 1, key: "decentralized_swarm" },
];

const scenarioDistribution = [
  { count: 2, key: "stock-availability" },
  { count: 1, key: "document-review" },
];

const runs = {
  [mockIds.centralizedConversation]: [buildRun(mockIds.centralizedRun, mockIds.centralizedConversation, "centralized_orchestration", "completed", 6200)],
  [mockIds.draftConversation]: [buildRun(mockIds.draftRun, mockIds.draftConversation, "centralized_orchestration", "running", 0)],
  [mockIds.workflowConversation]: [buildRun(mockIds.workflowRun, mockIds.workflowConversation, "structured_workflow", "human_review_required", 8100)],
  [mockIds.swarmConversation]: [buildRun(mockIds.swarmRun, mockIds.swarmConversation, "decentralized_swarm", "completed", 9500)],
};

const conversationDetails = {
  [mockIds.centralizedConversation]: {
    attachments: [],
    conversation: buildConversation(mockIds.centralizedConversation, "centralized_orchestration", "completed"),
    events: buildConversationEvents(mockIds.centralizedConversation, "centralized_orchestration"),
    messages: buildMessages(mockIds.centralizedConversation, "Tem dipirona em estoque?", "Temos dipirona 500 mg disponível."),
    reviewTasks: [],
    runs: runs[mockIds.centralizedConversation],
  },
  [mockIds.workflowConversation]: {
    attachments: [],
    conversation: buildConversation(mockIds.workflowConversation, "structured_workflow", "human_review_required"),
    events: buildConversationEvents(mockIds.workflowConversation, "structured_workflow"),
    messages: buildMessages(mockIds.workflowConversation, "Analise esse PDF de receita.", "Documento recebido. Encaminhando para revisão."),
    reviewTasks: [
      {
        conversationId: mockIds.workflowConversation,
        createdAt: NOW,
        id: "review-workflow-1",
        messageId: `${mockIds.workflowConversation}-outbound`,
        metadata: { priority: "high" },
        reason: "validacao_clinica",
        status: "open",
      },
    ],
    runs: runs[mockIds.workflowConversation],
  },
  [mockIds.draftConversation]: {
    attachments: [],
    conversation: buildConversation(mockIds.draftConversation, "centralized_orchestration", "active"),
    events: buildConversationEvents(mockIds.draftConversation, "centralized_orchestration"),
    messages: buildMessages(mockIds.draftConversation, "Nova mensagem de teste", "Processando a nova conversa."),
    reviewTasks: [],
    runs: runs[mockIds.draftConversation],
  },
  [mockIds.swarmConversation]: {
    attachments: [],
    conversation: buildConversation(mockIds.swarmConversation, "decentralized_swarm", "completed"),
    events: buildConversationEvents(mockIds.swarmConversation, "decentralized_swarm"),
    messages: buildMessages(mockIds.swarmConversation, "Tem dipirona em estoque?", "O estoque foi confirmado pelo fluxo swarm."),
    reviewTasks: [],
    runs: runs[mockIds.swarmConversation],
  },
} as const;

const runExecutions = {
  [mockIds.centralizedRun]: {
    executionEvents: [
      buildRunEvent(mockIds.centralizedRun, mockIds.centralizedConversation, 1, "node", "supervisor.started", "completed", "supervisor_agent"),
      buildRunEvent(mockIds.centralizedRun, mockIds.centralizedConversation, 2, "tool", "faq.lookup", "completed", "faq_agent", { toolName: "faq_lookup" }),
      buildRunEvent(mockIds.centralizedRun, mockIds.centralizedConversation, 3, "tool", "stock.lookup", "completed", "stock_agent", { toolName: "stock_lookup" }),
      buildRunEvent(mockIds.centralizedRun, mockIds.centralizedConversation, 4, "response", "response.final", "completed", "response_streamer"),
    ],
    projection: {
      activeActorName: "response_streamer",
      activeNodeId: "response_streamer",
      architectureMode: "centralized_orchestration",
      architectureView: {
        actors: {
          faq: { actorName: "faq_agent", nodeId: "faq-node", status: "completed" },
          image: { actorName: "image_intake_agent", nodeId: "image-node", status: "pending" },
          stock: { actorName: "stock_agent", nodeId: "stock-node", status: "completed" },
          supervisor: { actorName: "supervisor_agent", nodeId: "supervisor-node", status: "completed" },
        },
        handoffs: [],
        stages: [],
      },
      conversationId: mockIds.centralizedConversation,
      currentPhase: "completed",
      messageId: `${mockIds.centralizedConversation}-inbound`,
      metrics: { eventCount: 4, handoffCount: 2, toolCallCount: 2 },
      runId: mockIds.centralizedRun,
      runStatus: "completed",
      source: "mock",
      state: {},
      updatedAt: NOW,
    },
    run: runs[mockIds.centralizedConversation][0],
  },
  [mockIds.workflowRun]: {
    executionEvents: [
      buildRunEvent(mockIds.workflowRun, mockIds.workflowConversation, 1, "node", "classify", "completed", "router_agent"),
      buildRunEvent(mockIds.workflowRun, mockIds.workflowConversation, 2, "node", "gather", "completed", "workflow_evidence_agent"),
      buildRunEvent(mockIds.workflowRun, mockIds.workflowConversation, 3, "review", "review.required", "human_review_required", "workflow_review_agent"),
    ],
    projection: {
      activeActorName: "workflow_review_agent",
      activeNodeId: "review-node",
      architectureMode: "structured_workflow",
      architectureView: {
        actors: {},
        handoffs: [],
        stages: [
          { actorName: "router_agent", nodeId: "classify-node", stage: "classify", status: "completed" },
          { actorName: "workflow_evidence_agent", nodeId: "evidence-node", stage: "gather_evidence", status: "completed" },
          { actorName: "workflow_multimodal_agent", nodeId: "multimodal-node", stage: "multimodal_analysis", status: "completed" },
          { actorName: "workflow_review_agent", nodeId: "review-node", stage: "review_gate", status: "running" },
          { actorName: "workflow_synthesis_agent", nodeId: "synth-node", stage: "synthesize", status: "pending" },
        ],
      },
      conversationId: mockIds.workflowConversation,
      currentPhase: "review_gate",
      messageId: `${mockIds.workflowConversation}-inbound`,
      metrics: { eventCount: 3, handoffCount: 0, toolCallCount: 1 },
      runId: mockIds.workflowRun,
      runStatus: "human_review_required",
      source: "mock",
      state: {},
      updatedAt: NOW,
    },
    run: runs[mockIds.workflowConversation][0],
  },
  [mockIds.draftRun]: {
    executionEvents: [
      buildRunEvent(mockIds.draftRun, mockIds.draftConversation, 1, "node", "supervisor.started", "running", "supervisor_agent"),
    ],
    projection: {
      activeActorName: "supervisor_agent",
      activeNodeId: "supervisor-node",
      architectureMode: "centralized_orchestration",
      architectureView: {
        actors: {
          supervisor: { actorName: "supervisor_agent", nodeId: "supervisor-node", status: "running" },
        },
        handoffs: [],
        stages: [],
      },
      conversationId: mockIds.draftConversation,
      currentPhase: "dispatch",
      messageId: `${mockIds.draftConversation}-inbound`,
      metrics: { eventCount: 1, handoffCount: 0, toolCallCount: 0 },
      runId: mockIds.draftRun,
      runStatus: "running",
      source: "mock",
      state: {},
      updatedAt: NOW,
    },
    run: runs[mockIds.draftConversation][0],
  },
  [mockIds.swarmRun]: {
    executionEvents: [
      buildRunEvent(mockIds.swarmRun, mockIds.swarmConversation, 1, "node", "coordinator.started", "completed", "coordinator_agent"),
      buildRunEvent(mockIds.swarmRun, mockIds.swarmConversation, 2, "handoff", "handoff.faq", "completed", "faq_agent"),
      buildRunEvent(mockIds.swarmRun, mockIds.swarmConversation, 3, "handoff", "handoff.stock", "completed", "stock_agent"),
      buildRunEvent(mockIds.swarmRun, mockIds.swarmConversation, 4, "response", "response.final", "completed", "swarm_synthesizer"),
    ],
    projection: {
      activeActorName: "swarm_synthesizer",
      activeNodeId: "swarm-synth-node",
      architectureMode: "decentralized_swarm",
      architectureView: {
        actors: {
          coordinator: { actorName: "coordinator_agent", nodeId: "coordinator-node", status: "completed" },
          faq: { actorName: "faq_agent", nodeId: "faq-node", status: "completed" },
          image: { actorName: "image_intake_agent", nodeId: "image-node", status: "pending" },
          stock: { actorName: "stock_agent", nodeId: "stock-node", status: "completed" },
          synth: { actorName: "swarm_synthesizer", nodeId: "swarm-synth-node", status: "running" },
        },
        handoffs: [
          { payload: { from: "coordinator_agent", to: "faq_agent" } },
          { payload: { from: "coordinator_agent", to: "stock_agent" } },
          { payload: { from: "stock_agent", to: "swarm_synthesizer" } },
        ],
        stages: [],
      },
      conversationId: mockIds.swarmConversation,
      currentPhase: "synthesize",
      messageId: `${mockIds.swarmConversation}-inbound`,
      metrics: { eventCount: 4, handoffCount: 3, toolCallCount: 2 },
      runId: mockIds.swarmRun,
      runStatus: "completed",
      source: "mock",
      state: {},
      updatedAt: NOW,
    },
    run: runs[mockIds.swarmConversation][0],
  },
} as const;

const comparisonContexts = {
  [mockIds.centralizedRun]: buildComparisonContext(mockIds.centralizedRun, mockIds.centralizedConversation, "centralized_orchestration"),
  [mockIds.draftRun]: buildComparisonContext(mockIds.draftRun, mockIds.draftConversation, "centralized_orchestration"),
  [mockIds.workflowRun]: buildComparisonContext(mockIds.workflowRun, mockIds.workflowConversation, "structured_workflow"),
  [mockIds.swarmRun]: buildComparisonContext(mockIds.swarmRun, mockIds.swarmConversation, "decentralized_swarm"),
} as const;

const dashboardMetrics = {
  byArchitecture: architectureDistribution,
  byAttachmentType: [
    { count: 1, key: "application/pdf" },
    { count: 2, key: "none" },
  ],
  byModel: [{ count: 3, key: "mock" }],
  byScenario: scenarioDistribution,
  byTool: [
    { count: 2, key: "faq_lookup" },
    { count: 2, key: "stock_lookup" },
  ],
  conversations: conversationSummaries.map((summary) => ({
    conversationId: summary.conversationId,
    lastMessage: summary.lastMessage,
    latestRunId: summary.latestRunId,
    reviewPending: summary.reviewPending,
    runCount: 1,
    status: summary.status,
    updatedAt: summary.updatedAt,
  })),
  generatedAt: NOW,
  latencyPercentiles: { p50: 6200, p95: 9500 },
  totals: {
    attachments: 1,
    averageRunDurationMs: 7933,
    conversations: 3,
    events: 27,
    messages: 6,
    runs: 3,
    runsCompleted: 2,
    runsFailed: 0,
    runsHumanReview: 1,
  },
};

const reviewTasks = {
  reviewTasks: conversationDetails[mockIds.workflowConversation].reviewTasks,
};

export async function installMockEventSource(page: Page) {
  await page.addInitScript(() => {
    class MockEventSource {
      url: string;
      readyState = 1;
      onopen: ((event: Event) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      listeners = new Map<string, Array<(event: MessageEvent) => void>>();

      constructor(url: string) {
        this.url = url;
        queueMicrotask(() => {
          this.onopen?.(new Event("open"));
          this.dispatch("heartbeat", new MessageEvent("heartbeat", { data: "" }));
        });
      }

      addEventListener(type: string, listener: (event: MessageEvent) => void) {
        const current = this.listeners.get(type) ?? [];
        current.push(listener);
        this.listeners.set(type, current);
      }

      removeEventListener(type: string, listener: (event: MessageEvent) => void) {
        const current = this.listeners.get(type) ?? [];
        this.listeners.set(
          type,
          current.filter((candidate) => candidate !== listener),
        );
      }

      close() {
        this.readyState = 2;
      }

      private dispatch(type: string, event: MessageEvent) {
        for (const listener of this.listeners.get(type) ?? []) {
          listener(event);
        }
      }
    }

    Object.defineProperty(window, "EventSource", {
      configurable: true,
      value: MockEventSource,
      writable: true,
    });
  });
}

export async function mockFrontendApi(page: Page) {
  await page.route(`${API_BASE_URL}/**`, async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const body = resolveResponseBody(url.pathname, method);
    if (body === null) {
      await route.fulfill({
        body: JSON.stringify({ detail: `No mock for ${method} ${url.pathname}` }),
        contentType: "application/json",
        status: 404,
      });
      return;
    }

    await route.fulfill({
      body: JSON.stringify(body),
      contentType: "application/json",
      status: 200,
    });
  });
}

function resolveResponseBody(pathname: string, method: string) {
  if (method === "POST" && pathname === "/conversations") {
    return {
      channel: "web_chat",
      conversationId: mockIds.draftConversation,
      createdAt: NOW,
      status: "active",
    };
  }
  if (method === "POST" && pathname === "/messages") {
    return {
      acceptedAt: NOW,
      conversationId: mockIds.draftConversation,
      correlationId: `corr-${mockIds.draftConversation}`,
      messageId: `${mockIds.draftConversation}-inbound`,
      runId: mockIds.draftRun,
      status: "accepted",
    };
  }
  if (method === "GET" && pathname === "/conversations") {
    return { conversations: conversationSummaries };
  }
  if (method === "GET" && pathname === "/reviews") {
    return reviewTasks;
  }
  if (method === "GET" && pathname === "/dashboard/metrics") {
    return dashboardMetrics;
  }
  if (method === "GET" && /^\/conversations\/[^/]+$/.test(pathname)) {
    const conversationId = pathname.split("/")[2];
    return conversationDetails[conversationId as keyof typeof conversationDetails] ?? null;
  }
  if (method === "GET" && /^\/conversations\/[^/]+\/events$/.test(pathname)) {
    const conversationId = pathname.split("/")[2];
    return conversationDetails[conversationId as keyof typeof conversationDetails]?.events ?? null;
  }
  if (method === "GET" && /^\/runs\/[^/]+\/execution$/.test(pathname)) {
    const runId = pathname.split("/")[2];
    return runExecutions[runId as keyof typeof runExecutions] ?? null;
  }
  if (method === "GET" && /^\/runs\/[^/]+\/comparison-context$/.test(pathname)) {
    const runId = pathname.split("/")[2];
    return comparisonContexts[runId as keyof typeof comparisonContexts] ?? null;
  }
  return null;
}

function buildConversation(
  conversationId: string,
  architectureMode: string,
  status: string,
) {
  return {
    channel: "web_chat",
    createdAt: NOW,
    id: conversationId,
    metadata: {
      architectureMode,
      locale: "pt-BR",
      runtimeMode: "mock",
    },
    status,
    updatedAt: NOW,
    userSessionId: "session-123",
  };
}

function buildMessages(
  conversationId: string,
  inboundText: string,
  outboundText: string,
) {
  return [
    {
      contentText: inboundText,
      conversationId,
      correlationId: `corr-${conversationId}-1`,
      createdAtClient: NOW,
      createdAtServer: NOW,
      direction: "inbound",
      id: `${conversationId}-inbound`,
      metadata: {},
      status: "completed",
    },
    {
      contentText: outboundText,
      conversationId,
      correlationId: `corr-${conversationId}-2`,
      createdAtClient: NOW,
      createdAtServer: NOW,
      direction: "outbound",
      id: `${conversationId}-outbound`,
      metadata: {},
      status: "completed",
    },
  ];
}

function buildConversationEvents(conversationId: string, architectureMode: string) {
  return [
    {
      actorName: "runtime",
      conversationId,
      correlationId: `corr-${conversationId}-1`,
      createdAt: NOW,
      durationMs: 120,
      eventType: "processing.started",
      id: `${conversationId}-event-1`,
      messageId: `${conversationId}-inbound`,
      parentEventId: null,
      payload: { architectureMode },
      status: "completed",
    },
    {
      actorName: architectureMode === "decentralized_swarm" ? "coordinator_agent" : "supervisor_agent",
      conversationId,
      correlationId: `corr-${conversationId}-1`,
      createdAt: NOW,
      durationMs: 240,
      eventType: "actor.completed",
      id: `${conversationId}-event-2`,
      messageId: `${conversationId}-inbound`,
      parentEventId: `${conversationId}-event-1`,
      payload: { architectureMode },
      status: "completed",
    },
    {
      actorName: "response_streamer",
      conversationId,
      correlationId: `corr-${conversationId}-1`,
      createdAt: NOW,
      durationMs: 380,
      eventType: "processing.completed",
      id: `${conversationId}-event-3`,
      messageId: `${conversationId}-outbound`,
      parentEventId: `${conversationId}-event-2`,
      payload: { architectureMode },
      status: architectureMode === "structured_workflow" ? "human_review_required" : "completed",
    },
  ];
}

function buildRun(
  runId: string,
  conversationId: string,
  architectureKey: string,
  status: string,
  totalDurationMs: number,
) {
  return {
    aiSessionId: `session-${runId}`,
    conversationId,
    correlationId: `corr-${conversationId}`,
    createdAt: NOW,
    experiment: { architectureKey, scenarioId: architectureKey === "structured_workflow" ? "document-review" : "stock-availability" },
    externalRunId: `ext-${runId}`,
    finalOutcome: status,
    finishedAt: NOW,
    humanReviewRequired: status === "human_review_required",
    id: runId,
    messageId: `${conversationId}-inbound`,
    startedAt: NOW,
    status,
    summary: { label: architectureKey },
    totalDurationMs,
    traceId: `trace-${runId}`,
    updatedAt: NOW,
  };
}

function buildRunEvent(
  runId: string,
  conversationId: string,
  sequenceNo: number,
  eventFamily: string,
  eventName: string,
  status: string,
  actorName: string,
  extra: { toolName?: string } = {},
) {
  return {
    actorName,
    conversationId,
    correlationId: `corr-${conversationId}`,
    createdAt: NOW,
    durationMs: 200,
    eventFamily,
    eventName,
    externalEventId: `${runId}-ext-${sequenceNo}`,
    id: `${runId}-event-${sequenceNo}`,
    messageId: `${conversationId}-inbound`,
    nodeId: `${actorName}-${sequenceNo}`,
    payload: {},
    runId,
    sequenceNo,
    source: "mock",
    status,
    toolName: extra.toolName ?? null,
  };
}

function buildComparisonContext(runId: string, conversationId: string, architectureKey: string) {
  return {
    architectureDistribution,
    peerRuns: runs[conversationId as keyof typeof runs],
    run: buildRun(runId, conversationId, architectureKey, architectureKey === "structured_workflow" ? "human_review_required" : "completed", 6200),
    scenarioDistribution,
  };
}
