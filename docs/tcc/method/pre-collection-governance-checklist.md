# Checklist de prontidão para a coleta exploratória

Status: aguardando confirmação humana. Este registro operacional não constitui parecer jurídico, autorização ética ou consentimento.

## Finalidade e regra de início

Este checklist verifica as condições mínimas para a caracterização exploratória de aproximadamente 20 históricos de atendimento em ambiente privado. A coleta somente deverá começar quando todos os itens obrigatórios estiverem marcados como `confirmed` por um autor, após consulta ao orientador e à instância institucional aplicável.

As evidências de autorização, os dados brutos e qualquer material identificável devem permanecer fora do repositório público. No GitHub será registrada apenas a situação agregada de prontidão, sem nomes, mensagens, identificadores, credenciais ou informações de saúde.

Estados permitidos:

- `pending`: ainda não verificado;
- `confirmed`: verificado por um autor com evidência preservada em ambiente privado;
- `not_applicable`: dispensado pela instância competente, com justificativa privada;
- `blocked`: requisito não atendido; a coleta não pode começar.

## Checklist obrigatório

| ID | Condição de prontidão | Evidência a preservar fora do repositório | Estado atual |
|---|---|---|---|
| GOV-01 | A finalidade da coleta e o uso dos históricos para derivar cenários foram apresentados ao orientador. | Registro da orientação e da decisão aplicável. | `pending` |
| GOV-02 | Foram definidos pela instituição os requisitos aplicáveis de autorização, consentimento e eventual avaliação ética. | Parecer, autorização ou justificativa de não aplicabilidade. | `pending` |
| GOV-03 | O acesso aos históricos foi autorizado pelo responsável legítimo pelo canal e pelos dados. | Registro da autorização e do escopo permitido. | `pending` |
| GOV-04 | Os campos mínimos necessários e os conteúdos que não devem ser coletados foram definidos. | Lista privada de campos permitidos e excluídos. | `pending` |
| GOV-05 | O ambiente privado de coleta foi separado do repositório público e possui acesso restrito. | Descrição do ambiente e dos controles de acesso, sem credenciais. | `pending` |
| GOV-06 | O prazo de retenção, a forma de descarte e o responsável por executá-los foram definidos. | Plano privado de retenção e descarte. | `pending` |
| GOV-07 | O procedimento de anonimização cobre identificadores diretos, quase identificadores e conteúdo clínico desnecessário. | Versão do procedimento e amostra sintética de validação. | `pending` |
| GOV-08 | Uma segunda revisão de anonimização será realizada antes de transformar qualquer caso em cenário. | Registro privado da revisão, sem reproduzir o conteúdo analisado. | `pending` |
| GOV-09 | A eventual tabela de correspondência entre origem e cenário permanecerá separada, com acesso e retenção próprios. | Local privado e regra de acesso, sem publicar o caminho ou a chave. | `pending` |
| GOV-10 | Foi definida a resposta a incidente para exportação indevida, exposição ou suspeita de reidentificação. | Procedimento privado de interrupção, contenção e comunicação. | `pending` |

## Critério de decisão

- `GO`: GOV-01 a GOV-10 estão `confirmed` ou, quando cabível, `not_applicable` por decisão da instância competente.
- `NO-GO`: qualquer item está `pending` ou `blocked`. Nenhum histórico deve ser exportado, copiado ou analisado.

O status atual é `NO-GO`. A existência deste checklist não confirma nenhum requisito e não autoriza a coleta.

## Registro agregado após a verificação

Quando a governança for confirmada, o repositório poderá registrar somente:

- versão e data de verificação do checklist;
- decisão agregada `GO` ou `NO-GO`;
- papéis que realizaram a verificação, sem dados pessoais desnecessários;
- faixa ou quantidade agregada de históricos processados;
- versão do procedimento de anonimização; e
- confirmação de que dados brutos e evidências permaneceram no ambiente privado.

As decisões sobre unidade de análise, segmentação e categorias observadas continuam na OQ-004 e só serão registradas após a caracterização exploratória, sem conteúdo reconhecível.
