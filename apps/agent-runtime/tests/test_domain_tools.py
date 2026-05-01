import pytest

from app.tools.domain_tools import (
    attachment_intake,
    catalog_contains,
    faq_lookup,
    request_human_review,
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


def test_request_human_review() -> None:
    review = request_human_review("policy")
    assert review["reviewRequired"] is True


# ---------------------------------------------------------------------------
# catalog_contains
# ---------------------------------------------------------------------------

def test_catalog_contains_finds_product() -> None:
    assert catalog_contains("Tem dipirona em estoque?") == "dipirona"


def test_catalog_contains_returns_none_for_unknown() -> None:
    assert catalog_contains("Tem xyzabc123?") is None


@pytest.mark.parametrize(
    "product",
    ["paracetamol", "omeprazol", "loratadina", "azitromicina", "rivotril", "insulina"],
)
def test_catalog_contains_new_products(product: str) -> None:
    assert catalog_contains(f"Tem {product} disponivel?") == product


# ---------------------------------------------------------------------------
# New FAQ topics
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "keyword,expected_topic",
    [
        ("devolucao", "devolucao"),
        ("pagamento", "pagamento"),
        ("desconto", "desconto"),
        ("manipulacao", "manipulacao"),
        ("vacina", "vacina"),
        ("generico", "generico"),
    ],
)
def test_faq_lookup_new_topics(keyword: str, expected_topic: str) -> None:
    result = faq_lookup(f"Informacoes sobre {keyword}")
    assert result["topic"] == expected_topic
    assert len(result["answer"]) > 0


def test_faq_lookup_unknown_topic_returns_geral() -> None:
    result = faq_lookup("Algo completamente fora do escopo")
    assert result["topic"] == "geral"


# ---------------------------------------------------------------------------
# New stock items
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "product,expected_available",
    [
        ("paracetamol", True),
        ("azitromicina", False),
        ("insulina", True),
    ],
)
def test_stock_lookup_new_items(product: str, expected_available: bool) -> None:
    result = stock_lookup(f"Tem {product} em estoque?")
    assert result["product"] == product
    assert result["available"] is expected_available


def test_stock_lookup_insulina_low_stock() -> None:
    result = stock_lookup("Tem insulina?")
    assert result["product"] == "insulina"
    assert result["quantity"] == 2


def test_stock_lookup_unknown_product() -> None:
    result = stock_lookup("Tem xyzabc123?")
    assert result["product"] == "produto_nao_identificado"
    assert result["available"] is False


# ---------------------------------------------------------------------------
# Enriched attachment_intake
# ---------------------------------------------------------------------------

def test_attachment_intake_image_analysis() -> None:
    result = attachment_intake([{"attachmentId": "a1", "originalFilename": "foto.png", "mimeType": "image/png", "sizeBytes": 128}])
    analysis = result["summaries"][0]["analysis"]
    assert analysis["type"] == "image"
    assert analysis["detected_content"] == "medication_package"
    assert analysis["confidence"] == 0.85


def test_attachment_intake_pdf_analysis() -> None:
    result = attachment_intake([{"attachmentId": "a2", "originalFilename": "receita.pdf", "mimeType": "application/pdf", "sizeBytes": 256}])
    analysis = result["summaries"][0]["analysis"]
    assert analysis["type"] == "document"
    assert analysis["detected_content"] == "prescription"
    assert analysis["confidence"] == 0.90


def test_attachment_intake_unknown_type_analysis() -> None:
    result = attachment_intake([{"attachmentId": "a3", "originalFilename": "data.csv", "mimeType": "text/csv", "sizeBytes": 64}])
    analysis = result["summaries"][0]["analysis"]
    assert analysis["type"] == "unknown"
    assert "nao suportado" in analysis["note"]
