# ✨ Boas Práticas e Segurança

Para garantir a longevidade e a segurança do **Mapa-Força**, as seguintes diretrizes devem ser seguidas pela equipe de desenvolvimento e operação.

## 🛡️ Segurança

### Autenticação e Autorização
1. **Acesso por Convite**: Novos usuários Google OAuth são inativos por padrão. A ativação manual e a atribuição de papéis (`BATALHAO`, `SGB`, `POSTO`) são obrigatórias.
2. **Mixins de Permissão**: Todas as views devem herdar de `LoginRequiredMixin` e utilizar verificações de nível de acesso (ex: um operador de Posto A não pode editar o mapa do Posto B).

### Proteção de Dados
- **Variáveis de Ambiente**: Nunca comite arquivos `.env` ou segredos no Git. Utilize serviços de gestão de segredos em produção.
- **CSRF Protection**: O HTMX já está configurado para incluir o token CSRF nas requisições `POST`. Nunca desabilite essa proteção globalmente.
- **XSS**: O Django escapa automaticamente as variáveis nos templates. Tenha cuidado redobrado ao usar a tag `|safe` (evite-a se o conteúdo vier do usuário).

---

## 💻 Organização de Código

### Padrões Django
- **Fat Models, Thin Views**: Mantenha a lógica de negócio pesada nos modelos ou em arquivos de serviço (`services.py`) para facilitar o teste unitário.
- **Query Optimization**: Utilize `select_related` e `prefetch_related` para evitar o problema de N+1 consultas ao carregar listas de alocações e viaturas.

### Frontend (Tailwind + HTMX)
- **Extração de Componentes**: Se um fragmento de HTML for usado em mais de dois lugares, mova-o para um partial em `templates/components/`.
- **Classes Utilitárias**: Evite criar arquivos CSS customizados. Use as classes utilitárias do Tailwind no próprio HTML.

---

## 🚀 Escalabilidade

### Sincronização Assíncrona
À medida que o número de funcionários aumenta, os comandos de sincronização (`sync_efetivo_sheets`) podem demorar. Para escala maior:
1. Migre os Management Commands para tarefas **Celery**.
2. Utilize o **Redis** como broker para processamento em background.

### Cache
- Utilize o sistema de cache do Django (`memcached` ou `redis`) para os dados de "Dicionários" e "Hierarquia de Unidades", que mudam raramente.

---

## 🧪 Testes e Validação
- **Testes Unitários**: Priorize testar a lógica do `get_data_operacional` e as validações de alocação duplicada.
- **HTMX Testing**: Verifique se as views retornam apenas os fragmentos HTML esperados (status code 200 e conteúdo parcial).
