from __future__ import annotations

from typing import Any


try:  # pragma: no cover - optional decorator if strands is present
    from strands import tool
except Exception:  # pragma: no cover
    def tool(*_args, **_kwargs):
        def decorator(func):
            return func
        return decorator


FAQ_KB = {
    "horario": "A farmacia funciona diariamente das 08:00 as 22:00 no contexto simulado da POC.",
    "entrega": "A POC considera entrega local em ate 90 minutos, sem roteirizacao real.",
    "receita": "Casos que dependem de validacao clinica ou medicamentosa devem seguir para revisao humana.",
}

STOCK_CATALOG = {
    "dipirona": {"available": True, "quantity": 17, "unit": "frascos"},
    "ibuprofeno": {"available": True, "quantity": 9, "unit": "caixas"},
    "amoxicilina": {"available": False, "quantity": 0, "unit": "caixas"},
}


def infer_product_name(text: str | None) -> str:
    normalized = (text or "").lower()
    for candidate in STOCK_CATALOG:
        if candidate in normalized:
            return candidate
    return "produto_nao_identificado"


@tool()
def faq_lookup(question: str) -> dict[str, Any]:
    normalized = question.lower()
    for key, answer in FAQ_KB.items():
        if key in normalized:
            return {"topic": key, "answer": answer}
    return {
        "topic": "geral",
        "answer": "A POC nao consulta uma base real; o atendimento deve responder com cautela e pode solicitar revisao humana.",
    }


@tool()
def stock_lookup(question: str) -> dict[str, Any]:
    product = infer_product_name(question)
    item = STOCK_CATALOG.get(product)
    if item is None:
        return {
            "product": product,
            "available": False,
            "quantity": 0,
            "unit": "itens",
            "note": "Produto nao mapeado no catalogo controlado da POC.",
        }
    return {
        "product": product,
        **item,
        "note": "Consulta simulada de disponibilidade, sem integracao com ERP real.",
    }


@tool()
def attachment_intake(attachments: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = []
    for attachment in attachments:
        summaries.append(
            {
                "attachmentId": attachment.get("attachmentId"),
                "filename": attachment.get("originalFilename"),
                "mimeType": attachment.get("mimeType"),
                "sizeBytes": attachment.get("sizeBytes"),
                "width": attachment.get("width"),
                "height": attachment.get("height"),
                "pageCount": attachment.get("pageCount"),
            }
        )
    return {
        "attachmentCount": len(attachments),
        "summaries": summaries,
        "note": "Analise multimodal controlada; sem OCR ou visao computacional clinica real.",
    }


@tool()
def request_human_review(reason: str) -> dict[str, Any]:
    return {
        "reviewRequired": True,
        "reason": reason,
        "policy": "strands-review-v1",
    }


def should_request_review(text: str | None) -> bool:
    normalized = (text or "").lower()
    return any(
        term in normalized
        for term in [
            "revisao humana",
            "revisão humana",
            "supervisor",
            "farmaceutico",
            "farmacêutico",
            "dosagem",
            "efeito colateral",
        ]
    )


def infer_route(text: str | None, attachments: list[dict[str, Any]]) -> str:
    if attachments:
        return "image_intake"
    normalized = (text or "").lower()
    if any(term in normalized for term in ["tem ", "estoque", "disponivel", "disponível"]):
        return "stock_lookup"
    return "faq"
