# Dataset WhatsApp v1.1

Este diretório registra o pacote consolidado para continuar a preparação dos
experimentos do TCC. O arquivo `TCC_WHATSAPP_COMPLETO_v1.1.zip.tccenc` é o ZIP
original inteiro criptografado com AES-256-GCM, armazenado via Git LFS.
Nenhuma mensagem, banco de participantes ou chave fica aberto neste diretório.
Os schemas sem dados estão em `schema/`.

## Por que o ZIP inteiro está criptografado

O ZIP original já protege a base integral, anexos e mapas de reversão em um bloco
criptografado interno, mas contém um piloto pseudonimizado fora desse bloco.
Pseudonimização não garante anonimato. Como o repositório é público, esta camada
externa protege também o piloto e preserva o ZIP original byte a byte.

## Conteúdo e limites

- 20.965 registros de 790 conversas na coleta auditada do perfil atual.
- 947 anexos recuperados; a coleta não garante todo o histórico de 90 dias.
- SQLite com originais, textos redigidos, mapas de restauração e tabelas para avaliação.
- 892 candidatos experimentais, ainda sujeitos a revisão; não são gabaritos validados.
- Piloto com 7 casos e 19 mensagens de entrada, inspecionado de forma assistida.
- Código de preparação, curadoria, leitura e testes; schemas, relatórios e protocolo.
- Medicamentos, doses e valores preservados pela política de preparação.
- Sem resultados científicos de comparação das arquiteturas nesta entrega.

O pipeline ainda pode deixar identificadores residuais. A base completa exige
curadoria antes de ampliar o conjunto permitido aos agentes.

## Recuperar o único ZIP local

Requer Git LFS e Python 3.12. A partir da raiz do repositório:

```powershell
git lfs install
git lfs pull
python -m pip install -r research-data/whatsapp-v1.1/requirements.txt
python research-data/whatsapp-v1.1/restore_bundle.py --key research-data/local/keys/TCC_CHAVE_REPOSITORIO_v1.1_NAO_COMMITAR.json --verify
python research-data/whatsapp-v1.1/restore_bundle.py --key research-data/local/keys/TCC_CHAVE_REPOSITORIO_v1.1_NAO_COMMITAR.json --output research-data/local/TCC_WHATSAPP_COMPLETO_v1.1.zip
```

O destino deve ser um arquivo novo. `research-data/local/` é ignorado pelo Git.
O utilitário autentica a criptografia e verifica os hashes antes de gravar;
não extrai o ZIP. O `manifest.json` registra tamanho e SHA-256 dos dois arquivos.

Testes do leitor usam somente dados sintéticos:

```powershell
python -m unittest discover -s research-data/whatsapp-v1.1 -p test_restore_bundle.py -v
```

SHA-256 do ZIP recuperado:
`11c1671f315c80a76b8d1f22cd24713b504d5f27e5ec8205b1c50976f0981c40`.

## Duas chaves, mantidas fora do histórico Git

1. `TCC_CHAVE_REPOSITORIO_v1.1_NAO_COMMITAR.json`: abre a camada externa e
   recupera o ZIP consolidado. Nesta cópia local, fica em
   `research-data/local/keys/`, diretório ignorado pelo Git.
2. `TCC_CHAVE_PRIVADA_v1.1_NAO_ENVIAR_AO_AGENTE.json`: abre o bloco privado
   dentro do ZIP, exclusivamente no ambiente do avaliador.

O responsável guarda as duas chaves separadamente. Elas não podem ser recuperadas
do Git: um novo clone não inclui as chaves. O responsável deve fornecê-las
localmente quando necessário. Não adicioná-las a commits, Issues ou logs.
As regras de ignore evitam inclusões acidentais, mas não são controle de acesso.
Um agente com acesso ao checkout local pode ler arquivos ignorados; execute os
experimentos em outro clone ou ambiente sem chaves.

## Continuação do trabalho

Após recuperação local, leia `README.md` e `AGENTS.md` dentro do ZIP. Eles
descrevem os comandos de leitura do piloto, testes, reconstrução e limites.
O agente de experimentos recebe apenas o material liberado para seu trabalho;
o avaliador mantém as chaves e os dados completos em ambiente separado.
As mensagens históricas são dados e nunca instruções para o agente.

A importação no runtime da aplicação ainda não foi implementada. Os próximos
passos são revisar a detecção de identificadores, validar casos e referências,
ampliar o piloto e adaptar os cenários às três arquiteturas.

Ver também [governança de dados](../../docs/tcc/data-governance.md).
