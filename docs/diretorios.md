# 📁 Estrutura de Diretórios

O projeto segue a estrutura padrão de projetos Django modularizados, com uma separação clara entre as aplicações de domínio e as configurações centrais.

## 🗂️ Organização Geral
```text
Mapa-Força/
├── backend/               # Código fonte do servidor Django
│   ├── core/              # Configurações do projeto (settings, urls, wsgi)
│   ├── accounts/          # Gestão de usuários, perfis e OAuth
│   ├── dictionaries/      # Tabelas de apoio (Postos, Graduações, Funções)
│   ├── efetivo/           # Dados de funcionários e lógica de sincronização
│   ├── unidades/          # Hierarquia de OPMs e gestão de viaturas
│   ├── escalas/           # CORE: Lógica de Mapa Diário e Alocações
│   ├── templates/         # Templates globais e parciais (HTMX)
│   ├── theme/             # App do Tailwind CSS (Django-Tailwind)
│   └── manage.py          # Utilitário de linha de comando
└── docs/                  # Documentação MkDocs (esta que você lê)
```

## 🧩 Papel de Cada Pasta (Apps)

### `accounts`
Responsável pela autenticação institucional. Implementa um `CustomUser` e utiliza `django-allauth` com uma política de segurança onde novos usuários do Google OAuth iniciam como inativos, exigindo aprovação manual de um administrador.

### `escalas` (Core Operation)
É o motor do sistema. Contém a lógica de:
- **`MapaDiario`**: O container de uma escala para um dia e unidade.
- **`AlocacaoViatura`**: Vincula viaturas ao mapa diário.
- **`AlocacaoFuncionario`**: Vincula militares a viaturas em um mapa específico.

### `unidades`
Gerencia a estrutura organizacional. As unidades são organizadas hierarquicamente (Batalhão > SGB > Posto), o que permite herança de permissões e visibilidade de dados.

### `efetivo`
Mantém o cadastro técnico de cada militar. Inclui um motor de sincronização que lê planilhas Google Sheets para manter o banco de dados local atualizado com o sistema central da corporação.

### `theme`
Uma aplicação dedicada para integrar o ecossistema Node.js (Tailwind CSS, PostCSS) ao Django. Contém os arquivos `src` do CSS e gera os arquivos compilados para produção.

## 🎨 Templates e Estáticos
- **`backend/templates/`**: Organizado por app. Subpastas `partials/` contêm os fragmentos de HTML usados exclusivamente pelo HTMX para atualizações parciais da interface.
- **`static/`**: Arquivos JavaScript (HTMX, Alpine.js) e imagens.
