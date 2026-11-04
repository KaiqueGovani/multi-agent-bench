# Auditoria das repetições da coleta v4.4

Das 120 combinações de cenário e arquitetura, 14 tiveram entre um e quatro sucessos em cinco tentativas. Foram seis combinações na orquestração centralizada, seis no swarm e duas no workflow. Entre as 70 tentativas dessas combinações, todas as 29 reprovações ocorreram no critério composto de conteúdo. As 30 tentativas sujeitas a uma consulta obrigatória a cumpriram. [Registros sanitizados das 600 tentativas](../../research-data/results/architectural-comparison-v44/units.csv)

Em 12 das 14 combinações, o texto final foi idêntico nas cinco repetições. Nas outras duas, apareceram duas variantes de texto. Todas as 14 tiveram ao menos um par de aprovação e reprovação com os mesmos campos substantivos na entrada do juiz. Isso ocorreu em 60 dos 64 pares possíveis. Nos outros quatro, a resposta final foi o único campo substantivo diferente. Os pares compartilham tentativas e a contagem é descritiva.

Três das 15 rechecagens abrangeram combinações com resultado misto. Em uma delas, o juiz passou de reprovação para aprovação ao rever a mesma resposta com o mesmo arquivo de entrada e a mesma configuração, com temperatura zero. O veredito mudou no critério que pedia explicitar os limites da operação. Os resultados primários foram preservados. [Resumo das rechecagens](../../research-data/results/architectural-comparison-v44/recheck-analysis.json)

Os registros localizam mudanças no julgamento mesmo com a entrada observada constante. A instrumentação da geração permite comparar a configuração e os hashes registrados de contexto. Ela não contém o corpo integral de cada requisição física ao provedor. A causa interna da mudança de julgamento permanece indeterminada.
