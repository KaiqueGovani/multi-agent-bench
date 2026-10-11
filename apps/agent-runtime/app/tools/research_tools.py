"""Controlled research sources; no ERP, OCR, image recognition or order system."""
from strands import tool
from app.tools.domain_tools import faq_lookup, infer_product_name, STOCK_CATALOG


@tool()
def stock_lookup(question: str) -> dict:
    """Consulte disponibilidade controlada. Não há preço; ausência do catálogo é desconhecida."""
    product = infer_product_name(question)
    item = STOCK_CATALOG.get(product)
    return {"product": product, "catalogued": item is not None,
            "available": item.get("available") if item else None,
            "quantity": item.get("quantity") if item else None,
            "unit": item.get("unit") if item else None,
            "price": None, "source": "controlled-poc-catalog-v1", "real_inventory": False}


@tool()
def attachment_intake(attachments: list[dict]) -> dict:
    """Inspecione somente metadados dos anexos. Não lê conteúdo, imagem ou receita."""
    keys = ("attachmentId", "originalFilename", "mimeType", "sizeBytes", "pageCount")
    return {"attachments": [{k: a.get(k) for k in keys} for a in attachments],
            "content_read": False, "ocr_available": False, "vision_available": False,
            "note": "Solicite a informação textual ou encaminhe o documento para análise humana; não inferir conteúdo."}
