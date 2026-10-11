# Esquema e anonimização dos cenários

## Campos permitidos

| Campo | Finalidade | Regra |
|---|---|---|
| `scenario_id` | rastreabilidade | identificador aleatório, sem vínculo com conversa real |
| `stratum` | estratificação principal | vocabulário controlado: FAQ, estoque, anexos, revisão profissional, continuidade de contexto |
| `difficulty` | balanceamento do conjunto | baixa, intermediária ou alta, conforme critérios versionados |
| `intent` | intenção principal | rótulo funcional definido após triagem; não substitui o estrato |
| `input_text` | entrada do teste | sintético ou anonimizado; sem trechos reconhecíveis |
| `conversation_history` | avaliar continuidade | somente turnos necessários e transformados |
| `attachment_type` | testar multimodalidade | tipo genérico; arquivo sintético ou saneado |
| `expected_route` | validar roteamento | rota esperada definida pelos autores |
| `expected_tools` | validar ações | lista de ferramentas esperadas |
| `risk_level` | aplicar revisão | baixo, moderado ou alto, com critério documentado |
| `quality_criteria` | orientar avaliação | fatos e comportamentos esperados, sem resposta privada copiada |
| `prohibited_content` | segurança | informações ou condutas que não devem aparecer na resposta |
| `professional_review_required` | segurança | decisão booleana validada por farmacêutico |

## Transformações obrigatórias

Remover nomes, telefones, e-mails, endereços, documentos, identificadores de pedidos, estabelecimentos, datas raras, URLs assinadas, mídia original e detalhes clínicos individualizantes. Generalizar quantidades, datas e localizações quando não forem essenciais. Substituir entidades por rótulos funcionais e reescrever a mensagem para preservar a intenção sem conservar formulação reconhecível.

## Processo de construção e revisão

A transformação ocorre em ambiente privado. O fluxo previsto é: conversa real → anonimização → triagem de elegibilidade e remoção de duplicatas → classificação por objetivo experimental → validação farmacêutica dos casos sensíveis → elaboração do gabarito → inclusão no *benchmark*.

Uma segunda revisão deve procurar identificadores diretos, combinações quase identificadoras e conteúdo clínico desnecessário. O GitHub recebe somente o cenário final, seu *schema* e métricas agregadas. A tabela que permita relacionar cenário e conversa original, se existir, permanece fora do repositório e segue prazo de retenção definido pelos autores.

O catálogo final terá 40 cenários, distribuídos em cinco estratos de oito. Cada estrato conterá três cenários de menor complexidade, três intermediários e dois de maior complexidade. Os estratos podem se sobrepor; a classificação principal serve ao balanceamento do experimento.

## Decisão ainda pendente

A fonte e a estratégia de transformação foram definidas: conversas reais tratadas em ambiente privado e convertidas em cenários anonimizados. A regra de segmentação dos históricos em episódios continua pendente na `OQ-004` e será decidida após a coleta exploratória.

Nenhuma coleta ou transformação poderá prosseguir sem a confirmação prévia dos requisitos institucionais aplicáveis de autorização, consentimento, minimização, retenção e descarte.
