"""Unit tests for the scenario classification logic in messages route."""

import pytest

from app.api.routes.messages import _classify_scenario


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
