# 🔄 Fluxos do Sistema

O sistema possui fluxos críticos que garantem a segurança e a integridade dos dados operacionais.

## 🔐 Fluxo de Autenticação (Google OAuth)

A autenticação é feita exclusivamente via contas institucionais do Google. O sistema implementa uma camada extra de segurança para impedir acessos não autorizados.

```mermaid
flowchart TD
    A[Usuário clica em Login Google] --> B[Redirecionamento para Google]
    B --> C{Autenticação Google Ok?}
    C -->|Sim| D[Criação automática do perfil de Usuário]
    D --> E[Status: Inativo por padrão]
    E --> F[Admin recebe solicitação]
    F --> G{Admin Aprova?}
    G -->|Sim| H[Usuário Ativo + Role Definida]
    G -->|Não| I[Acesso Negado]
    C -->|Não| J[Erro de Login]
    H --> K[Acesso ao Dashboard]
```

## ⚙️ Ciclo de Vida Operacional (Mapa de Força)

A operação das unidades segue um ciclo diário rígido baseado no **Horário Operacional (07:40 AM)**.

```mermaid
sequenceDiagram
    participant U as Operador (Posto)
    participant S as Servidor (Django)
    participant B as Banco de Dados

    U->>S: Acessa Compor Mapa
    S->>S: Calcula Data Operacional (Se < 07:40, dia anterior)
    S->>B: Busca/Cria MapaDiario para Data/Unidade
    B-->>S: Retorna MapaDiario
    U->>S: Aloca Militar em Viatura (HTMX)
    S->>B: Valida Disponibilidade (Militar já escalado hoje?)
    B-->>S: Confirmação
    S-->>U: Retorna Card de Viatura Atualizado (HTML Partial)
```

## 📊 Sincronização de Dados (Google Sheets)

Para manter a base de dados sincronizada com as planilhas da corporação, o sistema executa comandos de gerenciamento.

- **Frequência**: Recomendado executar via Cron Job ou Celery Beat (diariamente às 02:00 AM).
- **Processamento**: O sistema utiliza o **Pandas** para processar as planilhas em massa, garantindo performance.

```mermaid
flowchart LR
    A[Google Sheet Pública] --> B[Management Command]
    B --> C[Pandas read_excel/csv]
    C --> D{Existe no Banco?}
    D -->|Sim| E[Update Dados]
    D -->|Não| F[Create Novo Registro]
    E --> G[Log de Sincronização]
    F --> G
```

### Regras Críticas de Sincronização:
1. **Unicidade**: O RE (Registro Estatístico) é a chave primária lógica para funcionários.
2. **Histórico**: Funcionários que saem da planilha não são deletados, mas marcados como inativos para preservar o histórico das escalas passadas.
