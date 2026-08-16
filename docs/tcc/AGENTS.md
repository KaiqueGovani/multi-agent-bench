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
