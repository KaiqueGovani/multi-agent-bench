"""Structured workflow architecture.

A predefined pipeline of stages (classify → evidence → review →
synthesize) processes the message sequentially.  Each stage is handled
by a dedicated agent with a fixed responsibility.
"""

from __future__ import annotations

from app.architectures import register
from app.architectures.base import ExecutionContext, ExecutionResult
from app.architectures.centralized import _detect_review_required_in_text

# Valid routes the classify stage may return
_VALID_ROUTES = {"faq", "stock_lookup", "image_intake"}

# Route → (actor_name, tool_function_name, domain_label)
_ROUTE_MAP = {
    "faq": ("faq_agent", "faq_lookup", "FAQ"),
    "stock_lookup": ("stock_agent", "stock_lookup", "estoque"),
    "image_intake": ("image_intake_agent", "attachment_intake", "análise de imagem"),
}


@register("structured_workflow")
class WorkflowExecutor:
    """Structured workflow: predefined pipeline stages with specialised agents."""

    def execute(self, ctx: ExecutionContext) -> ExecutionResult:
        text = ctx.request.latest_message.content_text or ""

        if ctx.settings.enable_live_llm:
            return self._execute_live(ctx, text)

        return self._execute_mock(ctx, text)

    # ------------------------------------------------------------------
    # Live pipeline — 5 Strands Agents in sequence
    # ------------------------------------------------------------------

    def _execute_live(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        from app.tools.domain_tools import faq_lookup, stock_lookup, attachment_intake

        _tool_by_name = {
            "faq_lookup": faq_lookup,
            "stock_lookup": stock_lookup,
            "attachment_intake": attachment_intake,
        }

        has_attachments = bool(ctx.request.latest_message.attachments)

        # --- Stage 1: classify ----------------------------------------
        router = ctx.create_agent(
            system_prompt=(
                "Você é um classificador de intenções para atendimento farmacêutico. "
                "Dada a mensagem do usuário, retorne APENAS uma das seguintes labels: "
                '"faq", "stock_lookup", "image_intake". '
                "Responda SOMENTE com a label, sem explicação adicional."
            ),
            tools=[],
            actor_name="router_agent",
        )
        if router is None:
            return self._execute_mock(ctx, text)

        ctx.emit("node", "started", "running", actor_name="router_agent",
                 node_id="workflow.classify", payload={"stage": "classify"})
        ctx.emit_reasoning("router_agent", "workflow.classify.reasoning",
                           thought="Classificando intenção...", decision="pending")

        try:
            raw_route = str(router(text)).strip().lower()
        except Exception:
            raw_route = "faq"

        route = raw_route if raw_route in _VALID_ROUTES else "faq"
        if has_attachments:
            route = "image_intake"

        ctx.emit_reasoning("router_agent", "workflow.classify.reasoning",
                           thought="Classificando intenção...", decision=route,
                           candidates=list(_VALID_ROUTES))
        ctx.emit("node", "completed", "completed", actor_name="router_agent",
                 node_id="workflow.classify", payload={"stage": "classify", "route": route})
        ctx.loop_count += 1

        # --- Stage 2: gather_evidence ---------------------------------
        actor_name, tool_name, domain = _ROUTE_MAP[route]
        tool_fn = _tool_by_name[tool_name]

        evidence_agent = ctx.create_agent(
            system_prompt=(
                f"Você é um especialista de {domain} de farmácia. "
                f"Use a ferramenta {tool_name} para buscar evidência relevante. "
                "Retorne o conteúdo da ferramenta em uma frase curta em PT-BR. "
                "Não invente informações."
            ),
            tools=[tool_fn],
            actor_name=actor_name,
        )
        if evidence_agent is None:
            return self._execute_mock(ctx, text)

        ctx.emit("node", "started", "running", actor_name=actor_name,
                 node_id="workflow.evidence", payload={"stage": "gather_evidence"})
        ctx.emit_reasoning(actor_name, "workflow.evidence.reasoning",
                           thought=f"Coletando evidência via {tool_name}...", decision=tool_name)

        try:
            evidence_text = str(evidence_agent(text)).strip()
        except Exception:
            evidence_text = ""

        ctx.emit("node", "completed", "completed", actor_name=actor_name,
                 node_id="workflow.evidence", payload={"stage": "gather_evidence"})
        ctx.loop_count += 1

        # --- Stage 3: multimodal_analysis (conditional) ---------------
        if has_attachments and route != "image_intake":
            mm_agent = ctx.create_agent(
                system_prompt=(
                    "Você é um especialista de análise de imagem de farmácia. "
                    "Use a ferramenta attachment_intake para buscar evidência relevante. "
                    "Retorne o conteúdo da ferramenta em uma frase curta em PT-BR. "
                    "Não invente informações."
                ),
                tools=[attachment_intake],
                actor_name="image_intake_agent",
            )
            if mm_agent is None:
                return self._execute_mock(ctx, text)

            ctx.emit("node", "started", "running", actor_name="image_intake_agent",
                     node_id="workflow.multimodal", payload={"stage": "multimodal_analysis"})
            ctx.emit_reasoning("image_intake_agent", "workflow.multimodal.reasoning",
                               thought="Analisando anexos...", decision="attachment_intake")

            try:
                mm_result = str(mm_agent(text)).strip()
                evidence_text = f"{evidence_text}\n{mm_result}"
            except Exception:
                pass

            ctx.emit("node", "completed", "completed", actor_name="image_intake_agent",
                     node_id="workflow.multimodal", payload={"stage": "multimodal_analysis"})
            ctx.loop_count += 1

        # --- Stage 4: review_gate -------------------------------------
        review_agent = ctx.create_agent(
            system_prompt=(
                "Você é um revisor de conformidade farmacêutica. "
                "Analise a pergunta original e a evidência coletada. "
                'Responda APENAS "review_required: true" ou "review_required: false". '
                "Marque true se: a pergunta envolve dosagem, interação medicamentosa, "
                "efeito colateral, gestação, ou produtos controlados; OU a evidência é "
                "insuficiente para resposta segura."
            ),
            tools=[],
            actor_name="review_agent",
        )
        if review_agent is None:
            return self._execute_mock(ctx, text)

        ctx.emit("node", "started", "running", actor_name="review_agent",
                 node_id="workflow.review", payload={"stage": "review_gate"})
        ctx.emit_reasoning("review_agent", "workflow.review.reasoning",
                           thought="Avaliando necessidade de revisão...", decision="pending")

        review_input = f"Pergunta: {text}\nEvidência: {evidence_text}"
        try:
            review_output = str(review_agent(review_input)).strip().lower()
            review_required = "true" in review_output
        except Exception:
            # Fallback to keyword detection if review agent fails
            review_required = _detect_review_required_in_text(evidence_text)

        ctx.emit_reasoning("review_agent", "workflow.review.reasoning",
                           thought="Avaliando necessidade de revisão...",
                           decision=str(review_required).lower())
        ctx.emit("node", "completed", "completed", actor_name="review_agent",
                 node_id="workflow.review", payload={"stage": "review_gate",
                                                     "review_required": review_required})
        ctx.loop_count += 1

        # --- Stage 5: synthesize --------------------------------------
        synthesis_agent = ctx.create_agent(
            system_prompt=(
                "Você é o sintetizador final do atendimento farmacêutico. "
                "Receba a evidência coletada e componha uma resposta em português do Brasil, "
                "em prosa corrida, clara e objetiva. Se review_required=true, inclua a "
                "recomendação de consultar um farmacêutico ou médico. "
                "Nunca forneça dosagens específicas."
            ),
            tools=[],
            actor_name="synthesis_agent",
        )
        if synthesis_agent is None:
            return self._execute_mock(ctx, text)

        ctx.emit("node", "started", "running", actor_name="synthesis_agent",
                 node_id="workflow.synthesize", payload={"stage": "synthesize"})
        ctx.emit_reasoning("synthesis_agent", "workflow.synthesize.reasoning",
                           thought="Sintetizando resposta final...", decision="composing")

        synth_input = f"Pergunta: {text}\nEvidência: {evidence_text}\nReview: {review_required}"
        try:
            final_text = str(synthesis_agent(synth_input)).strip()
        except Exception:
            final_text = evidence_text

        ctx.emit("node", "completed", "completed", actor_name="synthesis_agent",
                 node_id="workflow.synthesize", payload={"stage": "synthesize"})
        ctx.loop_count += 1

        # --- Finalize -------------------------------------------------
        ctx.emit_final(final_text, route=route, final_actor="synthesis_agent",
                       architecture_mode="structured_workflow", review_required=review_required)
        ctx.emit("run", "completed", "completed",
                 payload={"phase": "completed", "reviewRequired": review_required})
        return ctx.build_result(final_text, review_required)

    # ------------------------------------------------------------------
    # Mock pipeline — mirrors live stage names and actor names
    # ------------------------------------------------------------------

    def _execute_mock(self, ctx: ExecutionContext, text: str) -> ExecutionResult:
        route = "faq"
        specialist_actor = ctx.specialist_actor(route)
        has_attachments = bool(ctx.request.latest_message.attachments)

        # Build the stage pipeline (matches live actor/node names exactly)
        stages: list[tuple[str, str, dict]] = [
            ("workflow.classify", "router_agent", {"stage": "classify", "route": route}),
            ("workflow.evidence", specialist_actor, {"stage": "gather_evidence"}),
        ]
        if has_attachments:
            stages.append(("workflow.multimodal", "image_intake_agent", {"stage": "multimodal_analysis"}))
        stages.append(("workflow.review", "review_agent", {"stage": "review_gate"}))
        stages.append(("workflow.synthesize", "synthesis_agent", {"stage": "synthesize"}))

        # Stage-specific reasoning thoughts
        _reasoning = {
            "workflow.classify": ("Modo mock — sem classificação real.", route, ["faq"]),
            "workflow.evidence": (f"Coletando evidência via {specialist_actor}...", "mock_tool", None),
            "workflow.multimodal": ("Analisando anexos em modo mock...", "mock_attachment", None),
            "workflow.review": ("Avaliando necessidade de revisão em modo mock...", "false", None),
            "workflow.synthesize": ("Sintetizando resposta final em modo mock...", "composing", None),
        }

        # Execute each stage in order
        specialist_result: dict = {}
        for node_id, actor_name, payload in stages:
            ctx.emit("node", "started", "running", actor_name=actor_name,
                     node_id=node_id, payload=payload)

            # Emit actor.reasoning for every stage
            thought, decision, candidates = _reasoning.get(node_id, ("Processando...", "mock", None))
            ctx.emit_reasoning(actor_name, f"{node_id}.reasoning",
                               thought=thought, decision=decision,
                               candidates=candidates or [])

            if node_id == "workflow.evidence":
                specialist_result = ctx.run_specialist(specialist_actor, phase="workflow")

            ctx.emit("node", "completed", "completed", actor_name=actor_name,
                     node_id=node_id, payload=payload)
            ctx.loop_count += 1

        # Compose and emit final response
        final_text = ctx.compose_response(
            architecture="structured_workflow",
            route=route,
            specialist_result=specialist_result,
            review_required=False,
        )
        ctx.emit_final(
            final_text,
            route=route,
            final_actor="synthesis_agent",
            architecture_mode="structured_workflow",
            review_required=False,
        )
        ctx.emit("run", "completed", "completed",
                 payload={"phase": "completed", "reviewRequired": False})
        return ctx.build_result(final_text, False)
