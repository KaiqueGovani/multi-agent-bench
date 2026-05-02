# ⚠️ DEPRECATED

Estes cenários JSON foram migrados para o framework e2e-quality em YAML.

**Nova localização:** `tests/e2e-quality/scenarios/`

Os arquivos JSON são mantidos temporariamente porque `scripts/run_fixture_scenarios.py`
ainda os consome. Em uma iteração futura, o script será reescrito para ler do YAML
e estes arquivos serão removidos.

## Mapeamento

| JSON antigo | YAML novo (suite/id) |
|---|---|
| faq-question.json | pharmacy/faq_horario_funcionamento |
| stock-availability.json | pharmacy/consulta_estoque_dipirona |
| human-review-needed.json | pharmacy/revisao_humana_forcada |
| product-image.json | attachments/imagem_produto |
| document-pdf.json | attachments/documento_pdf |
| invalid-attachment.json | attachments/anexo_invalido |
