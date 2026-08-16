# Regras para agentes em `docs/tcc`

1. Leia `state/ralph-state.yml`, `automation/daily-prompt.md`, `data-governance.md` e o capítulo-alvo antes de editar.
2. Execute uma única ação delimitada por rodada. Prefira uma alteração pequena, revisável e completa.
3. Preserve o sentido técnico e o estágio real do projeto. O protótipo existe; os testes ainda estão sendo preparados/executados.
4. Não fabrique citações, DOIs, páginas, autores, métricas, resultados ou conclusões.
5. Para referências novas, registre primeiro como `candidate`; só use no texto após verificação da fonte primária.
6. Priorize artigos revisados por pares, trabalhos de conferência, normas, documentação oficial e relatórios institucionais. Blogs servem como contexto técnico, não como principal sustentação científica.
7. Mantenha vínculo entre afirmação, citação e entrada do registro de referências.
8. Não grave dados brutos de WhatsApp, nomes, telefones, anexos, identificadores ou transcrições reconhecíveis no repositório.
9. Alinhe a descrição técnica ao código atual. Se houver divergência, registre-a como pendência; não “corrija” a narrativa inventando uma implementação.
10. Atualize `state/ralph-state.yml` e crie um registro em `state/runs/` ao fim de cada execução.
11. Antes de editar os capítulos 7, 8 ou 9, leia `state/evidence-gates.yml`. Se o gate correspondente estiver `closed`, preserve somente títulos e placeholders; escolha outra ação do backlog.
12. O agente nunca pode alterar um gate de `closed` para `open`. Essa mudança exige autorização humana explícita dos autores após verificação das evidências.
13. No início da execução, consulte `open-questions/questions.yml` e as Issues vinculadas. Priorize incorporar respostas humanas já recebidas quando isso produzir um incremento textual completo e verificável.
14. Quando uma decisão, experiência prática ou informação não recuperável das fontes bloquear ou enriquecer materialmente o texto, registre uma Open Question conforme `open-questions/README.md` e abra uma Issue com o prefixo `[TCC][Open Question]`.
15. Crie no máximo uma pergunta por execução e mantenha no máximo cinco perguntas com status `open` ou `answered`. Não faça perguntas genéricas, duplicadas ou respondíveis pelo código, documentos ou literatura disponível.
16. Respostas humanas são insumos editoriais e decisões dos autores; não substituem referências acadêmicas para afirmações factuais externas e não abrem evidence gates.
17. O escopo dos agentes é exclusivamente documental: manuscrito, DOCX, referências, protocolos, estado e Open Questions. É proibido editar código-fonte, testes, infraestrutura ou configuração do protótipo.
18. Grave as mudanças diretamente na branch dedicada `agent/tcc-ralph-setup`. Não crie nem utilize pull requests para as execuções recorrentes.
