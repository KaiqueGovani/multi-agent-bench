"""Unit tests for the scenario classification logic in messages route."""

from types import SimpleNamespace

import pytest

from app.api.routes.messages import _classify_scenario
from app.runtime.mock.processing import MockProcessingRuntime
from app.services.processing_dispatcher import ProcessingDispatcher


class TestClassifyScenario:
    """Tests for _classify_scenario function."""

    def test_stock_inquiry_keywords(self):
        assert _classify_scenario("Tem dipirona em estoque?", None) == "stock_inquiry"
        assert _classify_scenario("Qual a disponibilidade de ibuprofeno?", None) == "stock_inquiry"
        assert _classify_scenario("Quanto custa o paracetamol?", None) == "stock_inquiry"
        assert _classify_scenario("Esse medicamento está disponível?", None) == "stock_inquiry"
        assert _classify_scenario("Vocês tem esse produto?", None) == "stock_inquiry"

    def test_clinical_guidance_keywords(self):
        assert _classify_scenario("Qual a dosagem de dipirona para crianças?", None) == "clinical_guidance"
        assert _classify_scenario("Esse remédio tem efeito colateral?", None) == "clinical_guidance"
        assert _classify_scenario("Posso tomar dipirona com ibuprofeno? Tem interação?", None) == "clinical_guidance"
        assert _classify_scenario("Gestante pode tomar esse remédio?", None) == "clinical_guidance"
        assert _classify_scenario("Sou alérgico a dipirona, posso usar paracetamol?", None) == "clinical_guidance"

    def test_faq_inquiry_keywords(self):
        assert _classify_scenario("Qual o horário de funcionamento?", None) == "faq_inquiry"
        assert _classify_scenario("Vocês fazem entrega?", None) == "faq_inquiry"
        assert _classify_scenario("Como funciona a devolução?", None) == "faq_inquiry"
        assert _classify_scenario("Quais formas de pagamento?", None) == "faq_inquiry"
        assert _classify_scenario("A farmácia está aberta no sábado?", None) == "faq_inquiry"

    def test_attachment_analysis_with_images(self):
        assert _classify_scenario("Segue a foto", ["image/jpeg"]) == "attachment_analysis"
        assert _classify_scenario("Veja esse documento", ["image/png"]) == "attachment_analysis"
        assert _classify_scenario(None, ["image/webp"]) == "attachment_analysis"

    def test_attachment_analysis_with_pdf(self):
        assert _classify_scenario("Analise essa receita", ["application/pdf"]) == "attachment_analysis"
        assert _classify_scenario(None, ["application/pdf"]) == "attachment_analysis"

    def test_general_inquiry_fallback(self):
        assert _classify_scenario("Olá, boa tarde!", None) == "general_inquiry"
        assert _classify_scenario("Obrigado pela ajuda", None) == "general_inquiry"
        assert _classify_scenario("Bom dia", None) == "general_inquiry"

    def test_empty_text_no_attachments(self):
        assert _classify_scenario(None, None) == "general_inquiry"
        assert _classify_scenario("", None) == "general_inquiry"

    def test_attachment_takes_priority_over_text(self):
        # Even if text mentions stock, presence of image triggers attachment scenario
        assert _classify_scenario("Tem esse produto em estoque?", ["image/jpeg"]) == "attachment_analysis"

    def test_case_insensitive(self):
        assert _classify_scenario("TEM DIPIRONA EM ESTOQUE?", None) == "stock_inquiry"
        assert _classify_scenario("QUAL A DOSAGEM?", None) == "clinical_guidance"
        assert _classify_scenario("QUAL O HORÁRIO?", None) == "faq_inquiry"

    def test_empty_file_types_list(self):
        assert _classify_scenario("Olá", []) == "general_inquiry"


def test_mock_runtime_opening_hours_response() -> None:
    response = MockProcessingRuntime._build_response_text(
        False,
        "Qual é o horário de funcionamento da farmácia?",
    )
    assert "08:00" in response
    assert "22:00" in response


def test_mock_runtime_stock_follow_up_uses_context() -> None:
    context = (
        "Ultima mensagem do usuario: E ibuprofeno?\n\n"
        "Contexto recente:\n"
        "Usuario: Tem dipirona disponivel?\n"
        "Assistente: Temos 17 frascos de dipirona disponiveis.\n"
        "Usuario: E ibuprofeno?"
    )
    assert MockProcessingRuntime._looks_like_stock_question("E ibuprofeno?", context)
    response = MockProcessingRuntime._build_response_text(False, context, route="stock_lookup")
    assert "ibuprofeno" in response
    assert "9 caixas" in response


def test_runtime_history_filters_other_architecture_outbound() -> None:
    dispatcher = ProcessingDispatcher()
    inbound = SimpleNamespace(direction="inbound", metadata_json={})
    workflow_outbound = SimpleNamespace(
        direction="outbound",
        metadata_json={"architectureMode": "structured_workflow"},
    )
    swarm_outbound = SimpleNamespace(
        direction="outbound",
        metadata_json={"architectureMode": "decentralized_swarm"},
    )

    assert dispatcher._belongs_to_runtime_history(inbound, "structured_workflow")
    assert dispatcher._belongs_to_runtime_history(workflow_outbound, "structured_workflow")
    assert not dispatcher._belongs_to_runtime_history(swarm_outbound, "structured_workflow")
