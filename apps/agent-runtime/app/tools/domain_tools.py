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
    "devolucao": "Aceitamos devolucoes em ate 7 dias com nota fiscal e embalagem lacrada. Medicamentos controlados nao podem ser devolvidos. (POC simulada)",
    "pagamento": "Aceitamos cartao de credito, debito, Pix e dinheiro. Parcelamento em ate 3x sem juros para compras acima de R$100. (POC simulada)",
    "desconto": "Nosso programa de fidelidade oferece 10%% de desconto a partir da quinta compra. Descontos adicionais para idosos e conveniados. (POC simulada)",
    "manipulacao": "Oferecemos servicos de manipulacao com prazo medio de 3 dias uteis. Necessario receita medica para formulas personalizadas. (POC simulada)",
    "vacina": "Disponibilizamos vacinas contra gripe e COVID-19 mediante agendamento. Consulte disponibilidade com nosso farmaceutico. (POC simulada)",
    "generico": "Sempre oferecemos a opcao de medicamento generico quando disponivel. Genericos possuem o mesmo principio ativo e eficacia comprovada pela Anvisa. (POC simulada)",
}

STOCK_CATALOG = {
    "dipirona": {"available": True, "quantity": 17, "unit": "frascos"},
    "ibuprofeno": {"available": True, "quantity": 9, "unit": "caixas"},
    "amoxicilina": {"available": False, "quantity": 0, "unit": "caixas"},
    "paracetamol": {"available": True, "quantity": 23, "unit": "caixas"},
    "omeprazol": {"available": True, "quantity": 5, "unit": "caixas"},
    "loratadina": {"available": True, "quantity": 12, "unit": "caixas"},
    "azitromicina": {"available": False, "quantity": 0, "unit": "caixas"},
    "rivotril": {"available": False, "quantity": 0, "unit": "caixas"},
    "insulina": {"available": True, "quantity": 2, "unit": "frascos"},
}


def infer_product_name(text: str | None) -> str:
    normalized = (text or "").lower()
    for candidate in STOCK_CATALOG:
        if candidate in normalized:
            return candidate
    return "produto_nao_identificado"


@tool()
def faq_lookup(question: str) -> dict[str, Any]:
    """Busca na base de FAQ da farmácia pelo tema mais relevante à pergunta do usuário. Use quando a pergunta for genérica ou clínica."""
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
    """Consulta disponibilidade simulada de um produto no estoque. Use quando o usuário perguntar sobre disponível, preço ou estoque de um produto específico."""
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
    """Analisa anexos (imagens, PDFs) enviados pelo usuário. Use quando houver anexos na mensagem."""
    summaries = []
    for attachment in attachments:
        mime = attachment.get("mimeType") or ""
        if mime.startswith("image/"):
            analysis = {"type": "image", "detected_content": "medication_package", "confidence": 0.85, "note": "Analise visual simulada"}
        elif mime == "application/pdf":
            analysis = {"type": "document", "detected_content": "prescription", "confidence": 0.90, "note": "Analise documental simulada"}
        else:
            analysis = {"type": "unknown", "note": "Tipo nao suportado para analise automatica"}
        summaries.append(
            {
                "attachmentId": attachment.get("attachmentId"),
                "filename": attachment.get("originalFilename"),
                "mimeType": attachment.get("mimeType"),
                "sizeBytes": attachment.get("sizeBytes"),
                "width": attachment.get("width"),
                "height": attachment.get("height"),
                "pageCount": attachment.get("pageCount"),
                "analysis": analysis,
            }
        )
    return {
        "attachmentCount": len(attachments),
        "summaries": summaries,
        "note": "Analise multimodal controlada; sem OCR ou visao computacional clinica real.",
    }


def request_human_review(reason: str) -> dict[str, Any]:
    return {
        "reviewRequired": True,
        "reason": reason,
        "policy": "strands-review-v1",
    }


def catalog_contains(text: str) -> str | None:
    """Return the matching product name from STOCK_CATALOG, or None."""
    normalized = (text or "").lower()
    for candidate in STOCK_CATALOG:
        if candidate in normalized:
            return candidate
    return None
