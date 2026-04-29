from app.tools.domain_tools import (
    attachment_intake,
    faq_lookup,
    infer_route,
    request_human_review,
    should_request_review,
    stock_lookup,
)


def test_faq_lookup_returns_controlled_answer() -> None:
    result = faq_lookup("Qual o horario da farmacia?")
    assert result["topic"] == "horario"


def test_stock_lookup_uses_controlled_catalog() -> None:
    result = stock_lookup("Tem dipirona em estoque?")
    assert result["product"] == "dipirona"
    assert result["available"] is True


def test_attachment_intake_summarizes_metadata() -> None:
    result = attachment_intake(
        [
            {
                "attachmentId": "a1",
                "originalFilename": "foto.png",
                "mimeType": "image/png",
                "sizeBytes": 128,
                "width": 32,
                "height": 32,
            }
        ]
    )
    assert result["attachmentCount"] == 1


def test_review_detection_and_route_inference() -> None:
    assert should_request_review("preciso de revisao humana") is True
    assert infer_route("Tem dipirona em estoque?", []) == "stock_lookup"
    assert infer_route("Analise a foto", [{"mimeType": "image/png"}]) == "image_intake"
    review = request_human_review("policy")
    assert review["reviewRequired"] is True
