# Padrao de UI da POC

O frontend da POC segue o padrao ShadCN/UI usado em muitos projetos React: componentes locais versionados no repositorio, tokens CSS globais e composicao com Tailwind.

## Diretrizes

- Componentes reutilizaveis ficam em `apps/web/src/components/ui`.
- Usar `cn` em `apps/web/src/lib/utils.ts` para combinar classes Tailwind com `clsx` e `tailwind-merge`.
- Usar `class-variance-authority` para variantes de componentes como `Button` e `Badge`.
- Usar tokens semanticos do Tailwind: `background`, `foreground`, `card`, `muted`, `primary`, `destructive`, `border`, `input` e `ring`.
- Usar icones de `lucide-react` em botoes e estados quando fizer sentido.
- Evitar bibliotecas de componentes globais que escondam o markup. O padrao ShadCN favorece componentes locais editaveis.

## Componentes locais atuais

- `Button`
- `Badge`
- `Card`
- `Alert`
- `Input`
- `Textarea`

## Estrutura da tela

- Header compacto com identificacao da conversa e badges de contexto.
- Lista de mensagens composta com cards, badges e bolhas customizadas com tokens ShadCN.
- Composer fixo na base da area principal, usando `Input`, `Textarea` e `Button`.
- Timeline operacional no painel lateral, usando `Card`, `Badge` e uma linha vertical controlada localmente.

## Tema

O tema e definido por CSS variables em `globals.css` e mapeado no `tailwind.config.ts`, seguindo o setup padrao do ShadCN.

## CSS global

`globals.css` continua existindo porque carrega as diretivas do Tailwind:

- `@tailwind base`
- `@tailwind components`
- `@tailwind utilities`

Ele tambem concentra os tokens CSS do tema. Estilos de componente devem ficar nos componentes locais em `components/ui` ou nos componentes de feature.
