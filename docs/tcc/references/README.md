# Registro vivo de referências

O arquivo `registry.csv` funciona como funil editorial.

- `candidate`: encontrada, ainda não verificada na fonte primária.
- `verified`: metadados e conteúdo relevante conferidos.
- `cited`: usada em uma afirmação específica do manuscrito.
- `watch`: útil apenas se o escopo técnico mudar.
- `reject`: duplicada, fraca, inacessível ou fora do tema.

Uma boa referência responde a pelo menos uma pergunta do trabalho: como agentes são coordenados; como arquiteturas são comparadas; como qualidade, custo, latência, segurança e robustez são avaliados; ou quais são os requisitos do atendimento farmacêutico.

## Matriz de trabalhos correlatos

O arquivo `related-works-matrix.csv` é a fonte versionável do quadro comparativo do Capítulo 3. Cada trabalho deve apontar para um `registry_id`, explicitar sua relação com o MAB e registrar o estado da referência no DOCX.

Uma linha sem `registry_id`, ou com `metadata_status` diferente de `verified`, representa dívida editorial e não autoriza novas afirmações no manuscrito. Divergências na coluna `abnt_status` devem ser corrigidas na próxima sincronização do DOCX, sempre com base na fonte primária indicada no registro vivo.
