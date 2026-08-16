# Esquema e anonimização dos cenários

## Campos permitidos

| Campo | Finalidade | Regra |
|---|---|---|
| `scenario_id` | rastreabilidade | identificador aleatório, sem vínculo com conversa real |
| `intent` | estratificação | vocabulário controlado: FAQ, estoque, anexo, revisão, múltipla intenção |
| `input_text` | entrada do teste | sintético ou anonimizado; sem trechos reconhecíveis |
| `conversation_history` | avaliar continuidade | somente turnos necessários e transformados |
| `attachment_type` | testar multimodalidade | tipo genérico; arquivo sintético ou saneado |
| `expected_route` | validar roteamento | rota esperada definida pelos autores |
| `expected_tools` | validar ações | lista de ferramentas esperadas |
| `risk_level` | aplicar revisão | baixo, moderado ou alto, com critério documentado |
| `quality_criteria` | orientar avaliação | fatos e comportamentos esperados, sem resposta privada copiada |

## Transformações obrigatórias

Remover nomes, telefones, e-mails, endereços, documentos, identificadores de pedidos, estabelecimentos, datas raras, URLs assinadas, mídia original e detalhes clínicos individualizantes. Generalizar quantidades, datas e localizações quando não forem essenciais. Substituir entidades por rótulos funcionais e reescrever a mensagem para preservar a intenção sem conservar formulação reconhecível.

## Processo de revisão

A transformação ocorre em ambiente privado. Uma segunda revisão deve procurar identificadores diretos, combinações quase identificadoras e conteúdo clínico desnecessário. O GitHub recebe somente o cenário final, seu schema e métricas agregadas. A tabela que permita relacionar cenário e conversa original, se existir, permanece fora do repositório e segue prazo de retenção definido pelos autores.

## Decisões pendentes

Fonte, autorização, volume, período e retenção dos dados reais: `TBD-OQ-001`. Nenhuma coleta definitiva deve começar antes da resposta e da validação institucional aplicável.
