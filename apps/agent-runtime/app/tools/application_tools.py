"""Application domain adapters with explicit provenance.

Current application integrations are still POC fixtures: no ERP, OCR, or vision.
Adapters normalize those capabilities to the common specialist contract. A future
ERP adapter can replace this binding without changing the agent topology.
"""
from strands import tool
from app.tools import research_tools as controlled


@tool()
def faq_lookup(question: str) -> dict:
    """Consulte as informações de atendimento da integração POC da aplicação."""
    return {**controlled.faq_lookup(question=question), "sourceProfile": "application-controlled-poc-adapter"}


@tool()
def stock_lookup(question: str) -> dict:
    """Consulte o catálogo POC da aplicação; não existe integração ERP ou preço real."""
    return {**controlled.stock_lookup(question=question), "sourceProfile": "application-controlled-poc-adapter"}


@tool()
def attachment_intake(attachments: list[dict]) -> dict:
    """Inspecione metadados da aplicação; não há leitura de imagem, receita ou OCR."""
    return {**controlled.attachment_intake(attachments=attachments), "sourceProfile": "application-controlled-poc-adapter"}


APPLICATION_TOOLS = {"faq": faq_lookup, "stock": stock_lookup, "attachments": attachment_intake}
