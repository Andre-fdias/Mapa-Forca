# 🚀 Deploy e Ambiente

Para rodar o sistema em produção, é necessário configurar o ambiente Django corretamente e garantir que as dependências de sistema e integrações Google estejam ativas.

## 🔑 Variáveis de Ambiente (`.env`)

O sistema espera as seguintes variáveis configuradas no ambiente do servidor:

### Configurações de Banco de Dados
- `DATABASE_URL`: URL de conexão (ex: `postgres://user:pass@host:port/dbname`).
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: Configurações explícitas se `DATABASE_URL` não for usado.

### Segurança e Django
- `SECRET_KEY`: Chave secreta única para cada ambiente.
- `DEBUG`: Deve ser `False` em produção.
- `ALLOWED_HOSTS`: Lista de domínios permitidos (ex: `mapaforca.com,www.mapaforca.com`).

### Integração Google OAuth 2.0
- `GOOGLE_CLIENT_ID`: Obtido no Google Cloud Console.
- `GOOGLE_CLIENT_SECRET`: Obtido no Google Cloud Console.

---

## 📦 Dependências do Sistema

- **Python 3.10+**: Linguagem base.
- **Node.js**: Necessário apenas para o build do Tailwind CSS no ambiente de desenvolvimento/CI.
- **PostgreSQL**: Recomendado como banco de dados relacional.
- **Poetry / Pipenv / venv**: O projeto utiliza um `requirements.txt` para gestão de pacotes.

### Instalação em Produção
```bash
# Clone o repositório
git clone https://github.com/seu-repo/mapa-forca.git
cd mapa-forca

# Instale as dependências Python
pip install -r requirements.txt

# Execute as migrações do banco
python manage.py migrate

# Colete os arquivos estáticos (Tailwind já deve estar compilado)
python manage.py collectstatic --no-input
```

---

## 🛠️ Configuração do Servidor

Recomenda-se o uso de **Gunicorn** com **Nginx** como proxy reverso.

### Exemplo de Configuração Gunicorn
```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### Build do CSS (Tailwind)
Em produção, não é necessário rodar o servidor do Tailwind. O comando `python manage.py tailwind build` deve ser executado no pipeline de CI/CD para gerar o arquivo CSS estático antes do `collectstatic`.

---

## 🔄 Sincronização Periódica
Configurar um **Cron Job** para rodar os comandos de sincronização de dados institucionais (via Google Sheets):

```bash
# Exemplo: Sincronizar efetivo todo dia às 03:00 AM
0 3 * * * /path/to/venv/bin/python /path/to/project/manage.py sync_efetivo_sheets >> /var/log/mapaforca_sync.log 2>&1
```
