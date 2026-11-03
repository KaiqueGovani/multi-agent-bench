# Apresentação da coleta histórica

Execute a partir de `apps/web`:

```bash
npm ci
npm run build
npm run start -- --hostname 127.0.0.1
```

Abra http://127.0.0.1:3000/research/defense e selecione “Apresentar à banca”. Use as setas, os botões e Esc. O link também aparece em `/research`. Esta página usa os agregados públicos de matrix40-v1-final e funciona localmente sem serviços externos após instalar e compilar. As comparações v4.2 e v4.4 continuam acessíveis em suas páginas próprias.

## Roteiro de três minutos

- 0:00–0:40 · Felipe apresenta a pergunta, a matriz 40 × 3 × 5 e os três fluxos. Explica que cada tentativa produz uma resposta.
- 0:40–1:30 · Felipe mostra os três gráficos. O workflow obteve três sucessos adicionais, com custo 2,79 vezes maior. O intervalo da diferença de sucesso inclui ganhos e perdas. A vantagem de tempo e custo do agente único vale para o regime avaliado.
- 1:30–2:15 · Kaique explica sucesso técnico e de tarefa. Usa R-faq-02 para mostrar o requisito de horário e a consulta ausente. A categoria inteira teve 5/40 sucessos por condição. Uma avaliação inválida continuou classificada como falha por evidência objetiva.
- 2:15–3:00 · Kaique compara as contagens de invocações em R-stock-03. As três configurações cumpriram a tarefa. Encerra com a contribuição de relacionar resposta, consultas e processamento e os limites da avaliação automática.

## Fontes e escolhas editoriais

Agregados são importados de `research-data/results/matrix40-v1-final/results-summary.json` durante o build. Custos por tentativa são estimativas transcritas da Tabela 20 do PDF fornecido, página impressa 77. Custos por etapa vêm da Tabela 19. O contraste de sucesso usa a Tabela 12, página 68 da revisão de 31/10. R-faq-02 usa a Tabela 30 do Apêndice B. R-stock-03 apresenta a reconstrução documental das Figuras 11 e 14. A página identifica essas reconstruções e não contém transcrições privadas ou tempos individuais inventados.

Os registros detalhados privados não foram necessários à apresentação pública. Para inspeção de trajetórias completas pelos autores, use o replay privado existente e suas regras de acesso. As medianas de latência representam medianas por cenário. Estimativa tarifária e cobrança real têm origens diferentes.
