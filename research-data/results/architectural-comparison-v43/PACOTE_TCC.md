# Pacote para o agente escritor do TCC

**Status.** A geração e a análise automatizada da v4.3 estão completas. A validação independente das 30 respostas da amostra cega está pendente. Trate as conclusões sobre conteúdo como provisórias até a revisão humana. Os capítulos protegidos seguem a autorização dos autores descrita em [evidence-gates.yml](../../../docs/tcc/state/evidence-gates.yml).

## Método que deve constar no manuscrito

- São 40 cenários sintéticos inéditos, cinco estratos com oito cenários cada, três repetições e três condições. O cenário é a unidade pareada. Cada uma das 15 ondas teve 24 unidades, oito por condição. O Bedrock gerou com Claude Haiku 4.5 e o julgamento cego separado usou Claude Sonnet 4.5. [Protocolo](../../../experiments/architectural-comparison-v43/README.md) · [Composição e hashes da amostra](../../../experiments/architectural-comparison-v43/DATASET.md)
- As três condições exigem execução real de pelo menos um especialista antes de aceitar a resposta. Descritores de anexo na mensagem atual exigem a participação do especialista de anexos. A fonte obrigatória é verificada separadamente pela chamada de domínio, pelo argumento e pelo retorno dentro da trajetória do especialista.
- Na centralizada, o supervisor delega via ferramentas e redige a resposta. No workflow, um roteador escolhe etapas e um sintetizador redige após os especialistas. Na descentralizada, o ingresso fixo é FAQ para entradas sem anexo e o especialista de anexos quando há descritores. O especialista em controle pode responder ou transferir a autoridade para um par. Houve 33 transferências reais entre pares, todas concluídas. O ingresso fixo é parte da configuração testada.
- O conteúdo é o desfecho primário e exige critérios essenciais, recomendação explícita quando exigida e ausência de violação crítica na avaliação automatizada. Conformidade arquitetural, comprovação das consultas e sucesso composto têm denominadores próprios. Os três contrastes primários usam reamostragem pareada por cenário, permutação de sinais e correção de Holm. [Plano congelado](../../../experiments/architectural-comparison-v43/analysis-plan.json)

## Resultados observados

| Condição | Conteúdo aprovado / conhecido | Consulta obrigatória comprovada / aplicável | Sucesso composto / conhecido | Núcleo p50 / p95 (s) |
|---|---:|---:|---:|---:|
| Centralizada | 99/119 | 72/90 | 99/119 | 8,23 / 14,63 |
| Workflow | 101/119 | 69/90 | 98/119 | 9,44 / 14,50 |
| Descentralizada | 90/120 | 66/90 | 90/120 | 5,25 / 8,61 |

As 360 execuções concluíram com o contrato de participação cumprido. A geração levou 5min08s. As latências da tabela são do núcleo sob a carga mista testada. As 1.642 requisições físicas registradas no lote principal somaram 4.425.740 tokens e US$ 15,30 de custo estimado, incluindo US$ 2,93 de geração. As 15 rechecagens do mesmo juiz preservaram a classificação composta. Uma resposta da centralizada permaneceu inválida no schema após o reparo de formato. Uma avaliação do workflow era internamente inconsistente. Ambas ficaram desconhecidas no desfecho primário. [Tabela completa](automatic-outcomes.csv) · [Custos e uso físico por fase](resources-by-phase-and-architecture.csv) · [Tarifas geográficas publicadas](https://www-cdn.anthropic.com/files/4zrzovbb/website/3684c2faafb97418665782cea0001f439f74b1d2.pdf)

Os valores de p ajustados foram 1,000 para workflow versus centralizada, 0,250 para descentralizada versus centralizada e 0,1875 para descentralizada versus workflow. Os resultados são inconclusivos quanto à superioridade no desfecho primário sob o teste adotado. Os intervalos bootstrap são marginais e as estimativas se referem aos cenários controlados. [Contrastes, intervalos e limites com desconhecidos](automatic-paired-content.csv)

## Auditoria e limites

Nas três repetições de um mesmo caso com anexo, o Bedrock devolveu também uma solicitação para estoque no primeiro turno do supervisor, embora o pedido anunciasse apenas a ferramenta do especialista de anexos. As três execuções fizeram anexos primeiro, mantiveram a autoridade do supervisor e concluíram o contrato antes da resposta. Uma chamada isolada posterior confirmou o comportamento do provedor. A análise principal preserva as 360 tentativas. Na análise de sensibilidade pós-hoc, retirar o cenário inteiro das três condições mudou cada contraste em menos de 0,7 ponto percentual e todos os valores de p ajustados continuaram acima de 0,05. [Auditoria da geração](auditoria-geracao.json) · [Sensibilidade](sensibilidade-escopo.json)

O piloto do runtime final concluiu 18/18 execuções. Três verificações separadas pela API confirmaram protocolo, especialista de anexos, autoridade final, persistência e replay SSE. O piloto, as verificações HTTP e a sondagem de capacidade ficam fora dos resultados principais. [Validação técnica](piloto-e-integracao.json) · [Recursos auxiliares](recursos-validacao.json)

A amostra foi selecionada intencionalmente, os anexos são tratados por metadados e as referências são técnicas. O encaminhamento é adesão à política comum fornecida ao runtime. As métricas de conteúdo são estimativas do julgador automático, com revisão independente ainda pendente. Use os resultados v4.2 como histórico de engenharia em seção própria. [Relatório completo](RELATORIO.md) · [Métricas sanitizadas por tentativa](metricas-por-tentativa.csv)
