"""Decentralized swarm architecture.

Agents collaborate peer-to-peer through a handoff loop.  A coordinator
starts the chain, specialist agents process in sequence, and a
synthesizer composes the final response.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.architectures.centralized import _detect_review_required_in_text, _infer_route_from_tools

# Optional dependency — Strands SDK tool decorator for handoff_to_peer
try:  # pragma: no cover - optional dependency
    from strands import tool as strands_tool
except Exception:  # pragma: no cover
    def strands_tool(*_args, **_kwargs):
        def decorator(func):
            return func
        return decorator


# ---------------------------------------------------------------------------
# Handoff tool factory — closure captures ctx, agents dict, and counters
# ---------------------------------------------------------------------------

def _make_handoff_tool(ctx: ExecutionContext, agents: dict, handoff_count_ref: list[int], original_text: str):
    """Build a ``handoff_to_peer`` tool bound to the current execution context.

    The *agents* dict is captured **by reference** so specialists added after
    this factory call are visible to the tool at invocation time.
    """

    @strands_tool()
    def handoff_to_peer(peer_name: str, reason: str) -> dict:
        """Delega a execução para outro agente do swarm. Use quando precisar de um especialista diferente para complementar a resposta."""
        if handoff_count_ref[0] >= ctx.settings.runtime_max_handoffs:
            return {
                "error": "max_handoffs_exceeded",
                "message": f"Limite de {ctx.settings.runtime_max_handoffs} handoffs atingido. Sintetize a resposta com as informacoes disponiveis.",
            }

        peer = agents.get(peer_name)
        if peer is None:
            return {
                "error": "unknown_peer",
                "message": f"Agente '{peer_name}' nao encontrado.",
            }

        handoff_count_ref[0] += 1
        ctx.handoff_count = handoff_count_ref[0]
        ctx.loop_count += 1

        ctx.emit(
            "handoff", "requested", "running",
            actor_name=peer_name,
            node_id=f"swarm.handoff.{handoff_count_ref[0]}",
            payload={"to": peer_name, "reason": reason, "hop": handoff_count_ref[0]},
        )
        ctx.emit(
            "node", "started", "running",
            actor_name=peer_name,
            node_id=f"swarm.{peer_name}",
            payload={"stage": "handoff_loop"},
        )

        try:
            peer_result = str(peer(f"Contexto delegado: {reason}. Pergunta original: {original_text}"))
        except Exception as exc:
            ctx.tool_error_count += 1
            ctx.emit(
                "node", "completed", "failed",
                actor_name=peer_name,
                node_id=f"swarm.{peer_name}",
                payload={"stage": "handoff_loop", "error": str(exc)[:300]},
            )
            return {
                "error": "peer_failed",
                "peer": peer_name,
                "message": f"Especialista '{peer_name}' falhou: {str(exc)[:200]}",
            }

        ctx.emit_message(peer_name, f"swarm.{peer_name}.message", peer_result[:200])
        ctx.emit(
            "node", "completed", "completed",
            actor_name=peer_name,
            node_id=f"swarm.{peer_name}",
            payload={"stage": "handoff_loop"},
        )

        return {"peer": peer_name, "result": peer_result}

    return handoff_to_peer


# ---------------------------------------------------------------------------
# Agent prompt constants
# ---------------------------------------------------------------------------

_PROMPT_FAQ = (
    "Voce e um especialista em FAQ de farmacia dentro de um swarm colaborativo. "
    "Use faq_lookup para buscar informacoes. Se a pergunta tambem envolver estoque, "
    'use handoff_to_peer("stock_specialist", "complementar com dados de estoque"). '
    "Caso contrario, retorne sua resposta diretamente em PT-BR. "
    "Se a pergunta for clinica, recomende consultar um farmaceutico."
)

_PROMPT_STOCK = (
    "Voce e um especialista em estoque dentro de um swarm colaborativo. "
    "Use stock_lookup para consultar disponibilidade. Se precisar de contexto "
    'adicional de FAQ, use handoff_to_peer("faq_specialist", "complementar com '
    'informacoes gerais"). Caso contrario, retorne sua resposta em PT-BR.'
)

_PROMPT_IMAGE = (
    "Voce e um especialista em analise de anexos dentro de um swarm colaborativo. "
    "Use attachment_intake para analisar imagens/PDFs. Apos analisar, se for "
    "necessario complementar com FAQ ou estoque, use handoff_to_peer com o peer "
    "apropriado. Caso contrario, retorne sua resposta em PT-BR."
)

_PROMPT_SYNTHESIZER = (
    "Voce e o sintetizador final de um swarm descentralizado de atendimento "
    "farmaceutico. Receba as evidencias acumuladas dos specialists e componha "
    "uma resposta em portugues do Brasil, em prosa corrida, clara e objetiva. "
    "Se a pergunta envolver dosagem, interacao, efeito colateral ou gestacao, "
    "recomende consultar um farmaceutico ou medico. Nunca forneca dosagens especificas."
)

_PROMPT_COORDINATOR = (
    "Voce e o coordenador de um swarm descentralizado de atendimento farmaceutico. "
    "Voce NAO responde diretamente ao usuario. Sua funcao e analisar a mensagem e "
    "delegar para o especialista correto usando handoff_to_peer: "
    '"faq_specialist" para perguntas genericas; '
    '"stock_specialist" para consultas de estoque/disponibilidade; '
    '"image_specialist" se houver anexos. '
    "Sempre use handoff_to_peer com o nome do peer e o motivo da delegacao."
)


@register("decentralized_swarm")
class SwarmExecutor:
    """Decentralized swarm: peer-to-peer agent collaboration via handoff loop."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""

        if ctx.settings.enable_live_llm:
            return self._execute_live(ctx, text)

        return self._execute_mock(ctx, text)

    # ------------------------------------------------------------------
    # Live execution — peer-to-peer swarm with 5 agents
    # ------------------------------------------------------------------

    def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        from app.tools.domain_tools import attachment_intake, faq_lookup, stock_lookup

        # 1. Shared mutable state
        agents: dict = {}
        handoff_count_ref: list[int] = [0]

        # 2. Build handoff tool (captures agents dict by reference)
        handoff_tool = _make_handoff_tool(ctx, agents, handoff_count_ref, original_text=text)

        # 3. Create specialist agents — populate the shared dict
        faq_agent = ctx.create_agent(
            system_prompt=_PROMPT_FAQ,
            tools=[faq_lookup, handoff_tool],
            actor_name="faq_specialist",
        )
        stock_agent = ctx.create_agent(
            system_prompt=_PROMPT_STOCK,
            tools=[stock_lookup, handoff_tool],
            actor_name="stock_specialist",
        )
        image_agent = ctx.create_agent(
            system_prompt=_PROMPT_IMAGE,
            tools=[attachment_intake, handoff_tool],
            actor_name="image_specialist",
        )
        synthesizer = ctx.create_agent(
            system_prompt=_PROMPT_SYNTHESIZER,
            tools=[],
            actor_name="swarm_synthesizer",
        )
        coordinator = ctx.create_agent(
            system_prompt=_PROMPT_COORDINATOR,
            tools=[handoff_tool],
            actor_name="swarm_coordinator",
        )

        # Fallback to mock if any agent creation failed (live LLM unavailable)
        if any(a is None for a in (faq_agent, stock_agent, image_agent, synthesizer, coordinator)):
            return self._execute_mock(ctx, text)

        # 4. Register agents in the shared dict so handoff_to_peer can find them
        agents["faq_specialist"] = faq_agent
        agents["stock_specialist"] = stock_agent
        agents["image_specialist"] = image_agent
        agents["swarm_synthesizer"] = synthesizer
        agents["swarm_coordinator"] = coordinator

        # 5. Execution flow — coordinator dispatches via handoff_to_peer
        ctx.emit_reasoning(
            "swarm_coordinator", "swarm.dispatch",
            "Swarm LLM ativo — coordenador analisa e delega via handoff_to_peer.",
            "live_llm",
            ["faq_specialist", "stock_specialist", "image_specialist"],
        )
        ctx.emit(
            "node", "started", "running",
            actor_name="swarm_coordinator",
            node_id="swarm.swarm_coordinator",
            payload={"stage": "dispatch"},
        )

        coordinator_result = str(coordinator(text))

        ctx.emit(
            "node", "completed", "completed",
            actor_name="swarm_coordinator",
            node_id="swarm.swarm_coordinator",
            payload={"stage": "dispatch"},
        )

        # 6. Synthesizer pass — if coordinator result looks like a tool artifact
        needs_synthesis = (
            len(coordinator_result.strip()) < 40
            or "handoff_to_peer" in coordinator_result
            or "tool_use" in coordinator_result
        )

        if needs_synthesis:
            ctx.emit(
                "node", "started", "running",
                actor_name="swarm_synthesizer",
                node_id="swarm.swarm_synthesizer",
                payload={"stage": "synthesis"},
            )
            ctx.emit_reasoning(
                "swarm_synthesizer", "swarm.synthesizer.reasoning",
                "Sintetizando resposta final a partir das evidencias coletadas.",
                "synthesis",
            )
            synthesizer_result = str(synthesizer(
                f"Resultado do swarm: {coordinator_result}. Pergunta original: {text}"
            ))
            ctx.emit(
                "node", "completed", "completed",
                actor_name="swarm_synthesizer",
                node_id="swarm.swarm_synthesizer",
                payload={"stage": "synthesis"},
            )
            final_text = synthesizer_result.strip()
        else:
            final_text = coordinator_result.strip()

        # 7. Route inference and finalization
        route = "faq"  # default
        # Infer from tool calls tracked by hook providers on each agent
        # The handoff_count_ref tells us specialists ran; use first tool heuristic
        # Since tool_calls are tracked per-agent via hooks, we check ctx counters
        if ctx.tool_call_count > 0:
            # Heuristic: if stock_lookup was called, route is stock_lookup
            lower_text = text.lower()
            if any(kw in lower_text for kw in ["estoque", "disponivel", "disponibilidade", "tem "]):
                route = "stock_lookup"
            elif ctx.request.latest_message.attachments:
                route = "image_intake"

        review_required = _detect_review_required_in_text(final_text)

        ctx.emit_final(
            final_text,
            route=route,
            final_actor="swarm_synthesizer",
            architecture_mode="decentralized_swarm",
            review_required=review_required,
        )
        ctx.emit(
            "run", "completed", "completed",
            payload={"phase": "completed", "reviewRequired": review_required},
        )
        return ctx.build_result(final_text, review_required)

    # ------------------------------------------------------------------
    # Mock execution — consistent event pattern with handoff tracking
    # ------------------------------------------------------------------

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = "faq"
        specialist_actor = "faq_agent"

        # Handoff chain: coordinator → specialist → synthesizer
        chain = ["swarm_coordinator", specialist_actor, "swarm_synthesizer"]

        specialist_result: dict = {}
        for index, actor_name in enumerate(chain):
            node_id = f"swarm.{index}.{actor_name}"
            ctx.emit(
                "node", "started", "running",
                actor_name=actor_name, node_id=node_id,
                payload={"stage": "handoff_loop", "position": index, "hop": index},
            )

            if index == 0:
                ctx.emit_reasoning(
                    "swarm_coordinator", "swarm.coordinator.reasoning",
                    thought="Modo mock — sem classificação real.",
                    decision=route, candidates=[route],
                )
            elif actor_name == specialist_actor:
                ctx.emit_reasoning(
                    actor_name, f"swarm.{actor_name}.reasoning",
                    thought="Especialista acionado via handoff em modo mock.",
                    decision=route, candidates=[route],
                )
            elif actor_name == "swarm_synthesizer":
                ctx.emit_reasoning(
                    "swarm_synthesizer", "swarm.synthesizer.reasoning",
                    thought="Sintetizando resposta final em modo mock.",
                    decision="synthesize", candidates=["synthesize"],
                )

            if index > 0:
                ctx.loop_count += 1
                ctx.handoff_count += 1
                ctx.emit(
                    "handoff", "requested", "running",
                    actor_name=chain[index - 1],
                    node_id=f"swarm.handoff.{index}",
                    payload={"from": chain[index - 1], "to": actor_name, "hop": index},
                )

            if actor_name == specialist_actor:
                specialist_result = ctx.run_specialist(actor_name, phase="swarm")
                ctx.emit_message(
                    actor_name, f"swarm.{index}.{actor_name}.message",
                    "Especialista analisou a solicitação em modo mock.",
                )

            ctx.emit(
                "node", "completed", "completed",
                actor_name=actor_name, node_id=node_id,
                payload={"stage": "handoff_loop", "position": index, "hop": index},
            )

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="decentralized_swarm",
            route=route,
            specialist_result=specialist_result,
            review_required=False,
        )
        ctx.emit_final(
            final_text,
            route=route,
            final_actor="swarm_synthesizer",
            architecture_mode="decentralized_swarm",
            review_required=False,
        )
        ctx.emit("run", "completed", "completed", payload={"phase": "completed", "reviewRequired": False})
        return ctx.build_result(final_text, False)
