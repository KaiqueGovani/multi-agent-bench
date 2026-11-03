# Dados e referência histórica da v4.4

A matriz usa `real-conversations-v1.0`, o mesmo catálogo técnico de 40 recortes revisados que serviu às coortes v4.1 e v4.2. As 600 novas unidades correspondem a cinco repetições de cada combinação de cenário e condição, 200 por condição. A nova geração produz respostas próprias para a nova coorte. As respostas, julgamentos e métricas das coortes anteriores permanecem identificados em suas versões.

## Escopo dos dados

Os 40 cenários correspondem a episódios individuais da partição de teste, de 40 grupos conhecidos distintos. A curadoria anterior excluiu os sete grupos conhecidos de desenvolvimento. Cada recorte termina na solicitação focal do cliente e a referência técnica foi construída a partir desse recorte, da política comum e dos contratos determinísticos do benchmark. A execução se restringe ao material já liberado para a pesquisa. O pacote privado conserva as entradas, os critérios, as decisões de evidência e a documentação de curadoria.

| Dimensão | Composição do catálogo |
|---|---|
| Estratos | 8 FAQ, 8 estoque, 8 anexos, 8 encaminhamento profissional e 8 continuidade |
| Dificuldade | 15 simples, 15 intermediários e 10 complexos |
| Histórico | 36 cenários com contexto anterior |
| Anexos | 14 cenários com 17 descritores |
| Encaminhamento | 8 cenários com recomendação profissional prevista pela regra comum |
| Evidência de fontes | 20 consultas obrigatórias em 19 cenários e 33 consultas opcionais |

O runtime recebe os textos revisados do recorte e os descritores permitidos. O julgamento usa a referência técnica de cada tarefa e a resposta. Os anexos são representados por metadados e a avaliação de encaminhamento mede o cumprimento da política textual. As referências são técnicas e as conclusões se restringem às condições simuladas do benchmark. [Governança de dados](../../docs/tcc/data-governance.md)

## Referência das condições

Workflow e swarm seguem a implementação v4.2 sob o perfil `controlled-research`. O workflow usa um roteador, especialistas de domínio e um sintetizador. O swarm v4.2 usa coordenação inicial, especialistas com a ferramenta de transferência para pares e síntese final. A comparação entre snapshots v4.1 e v4.2 confirmou os mesmos prompts desses papéis, a mesma política de domínio e arquivos idênticos de fontes controladas. Nos dois ramos, a v4.2 passou a criar especialistas por uma fábrica comum. No swarm, o bootstrap passou a registrar os vínculos de invocação dos eventos. O snapshot v4.2 é a referência efetiva para execução e instrumentação desses dois braços.

O piloto técnico usa o catálogo sintético de seis casos do piloto v4.2. Uma nova execução por caso e condição resulta em 18 tentativas próprias da fase de engenharia. Essa fase cobre os cinco estratos e inclui uma tarefa que combina anexo, pagamento e encaminhamento.

## Identidade dos arquivos

Os seis assets do catálogo conferem na origem e nas cópias dos dois manifestos históricos. Os 40 objetos de caso coincidem integralmente, com os mesmos hashes individuais e o mesmo hash da lista serializada. Os arquivos de entrada e gabarito estão fora do Git. Os hashes abaixo permitem conferir a linhagem do lote com acesso ao pacote privado.

| Artefato | SHA-256 |
|---|---|
| Catálogo `cenarios40.json` | `9dd22bdc3e22da4e7d781bcdad2592ec4710cf756436cf134289b2d48c8c19ad` |
| Lista de casos em serialização canônica | `8c251bec5e78dc6f355840fb89f6e400c3988fa9f68496e31fd25b476b600866` |
| Entradas `entradas40.json` | `3119c164056fea08e32e6f669c26dc992f10441c1af80f16ac183c893c793098` |
| Decisões `decisoes_evidencia.json` | `90f5043d706da91a377974f04008804de0874a80e1cb14250394ef4d93994fb3` |
| Protocolo de curadoria | `7638aeee22b9b0b9cd33cc1141b64e871add23d113d26168ddcaf2c079fa3314` |
| Caderno de cenários | `23f1afefa28f7ba10e1c5e4755875214142c1e408a33e035ef5dce6473f88599` |
| README do catálogo privado | `87f14dfdb41cb01e08605ed2140b821efb6c0637bb0d6844897cc85fca4981ef` |
| Manifesto v4.1 | `921b54f9310e3281c519e5b61100304aa3a4755a27daf0238a96c3910f4cf208` |
| Manifesto v4.2 | `ea77cc3cf50a8c1fe8d6c84d22ad0bf5fccaa171773c00b26421f0ce46c1b917` |
| Executor `comparison.py` no snapshot v4.2 | `7b3e036fecbe32fbd97f4267de7b82c6df8d1c6756d5fa4ab14358ca7a3b3ff4` |
| Ferramentas `domain_tools.py` | `aa2466ea6eb42fbc74f4f0d8d20ad5d7ebdc893d6527506634c271dad35e547c` |
| Ferramentas `research_tools.py` | `8273ca024b631eac53999a717f3fc109845d327bc9b0edbf1f21a806285dc914` |
| Catálogo sintético do piloto | `be3ce46328a3ef17986711062e4499148bf53db66ba08c691eb17b1278665b57` |
| Configuração calibrada do juiz | `6f45a31db81c9c6340bb13f7e199776890a300415ccbad0d408af6d09b143582` |
| Mensagem de sistema do juiz | `ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36` |

A configuração histórica usa Haiku 4.5 na geração e Sonnet 4.5 no julgamento, ambos em `us-west-2`, com temperatura zero. O manifesto v4.2 registra a verificação de consultas em especialistas como `objective-evidence-v5.4-nested`. A configuração do juiz tem o mesmo hash nas duas versões históricas. [Protocolo v4.2](../architectural-comparison-v42/README.md) · [Catálogo sintético do piloto](../corrected-comparison-v4.2/pilot-six.json)
