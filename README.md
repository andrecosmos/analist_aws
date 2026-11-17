# Copiloto Inteligente de Autopeças

Dashboard full-stack para gestão comercial de autopeças, com análise financeira por canal de venda, controle de estoque, cálculo de comissões e recomendações de reposição geradas por IA.

O projeto combina uma API REST em FastAPI com um painel interativo em Streamlit e utiliza PostgreSQL/Supabase como banco de dados.

## Funcionalidades

- Cadastro de vendas com validação de estoque
- Cálculo automático de comissão de marketplaces e vendedores
- Cálculo de lucro líquido por venda e por canal
- Dashboard com faturamento, margem e desempenho comercial
- Identificação de produtos abaixo do estoque mínimo
- Mapeamento entre produtos e veículos compatíveis
- Relatório executivo em PDF
- Sugestões estratégicas de compra com Google Gemini
- Migrações de banco com Alembic

## Tecnologias

- Python 3.14
- FastAPI
- Streamlit
- SQLAlchemy
- PostgreSQL / Supabase
- Alembic
- Pydantic
- Google Gemini API
- Matplotlib e ReportLab
- Docker

## Arquitetura

```text
app_frontend.py
  |
  | HTTP
  v
app/main.py -> FastAPI
  |
  +-> app/database/database.py -> PostgreSQL/Supabase
  +-> app/models/models.py       -> SQLAlchemy ORM
  +-> app/schemas/schemas.py     -> Validação Pydantic
  +-> Google Gemini               -> Recomendação de compras
```

## Pré-requisitos

- Python 3.14
- Conta e banco PostgreSQL
- Chave da API Google Gemini
- Docker opcional

## Configuração local

Clone o projeto e crie um ambiente virtual:

```bash
git clone <URL_DO_REPOSITORIO>
cd analist

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure as variáveis de ambiente:

```bash
cp .env.example .env
```

Edite `.env` e informe:

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco
GEMINI_API_KEY=sua_chave_da_google_gemini
```

Para PostgreSQL gerenciado pelo Supabase, use a connection string fornecida pelo provedor. Evite usar a senha diretamente no código ou em arquivos versionados.

## Migração e dados iniciais

Aplique as migrações:

```bash
alembic upgrade head
```

Opcionalmente, carregue dados demonstrativos:

```bash
python seed.py
```

O script cria canais de venda, vendedores, produtos, veículos compatíveis e um histórico fictício de vendas para desenvolvimento e demonstração.

## Executando a aplicação

Em um terminal, inicie a API:

```bash
uvicorn app.main:app --reload
```

Em outro terminal, inicie o dashboard:

```bash
streamlit run app_frontend.py
```

- API: http://127.0.0.1:8000
- Documentação Swagger: http://127.0.0.1:8000/docs
- Dashboard: http://localhost:8501

## API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Verifica o estado da API |
| `POST` | `/vendas` | Registra uma venda e atualiza o estoque |
| `GET` | `/analise/financeira` | Retorna faturamento, margem e lucro por canal |
| `GET` | `/estoque/critico` | Lista produtos abaixo do estoque mínimo |
| `GET` | `/ia/sugestao-compra` | Gera recomendações de compra com Gemini |
| `GET` | `/analise/relatorio-pdf` | Gera e disponibiliza relatório em PDF |

Exemplo de cadastro de venda:

```json
{
  "produto_id": 1,
  "canal_venda_id": 3,
  "vendedor_id": 1,
  "quantidade": 2,
  "preco_venda_total": 240.00
}
```

## Docker

Construa e execute somente a API:

```bash
docker build -t copiloto-autopecas .
docker run --env-file .env -p 8000:8000 copiloto-autopecas
```

O Streamlit deve continuar sendo iniciado separadamente:

```bash
streamlit run app_frontend.py
```

## Estrutura do projeto

```text
.
├── app/
│   ├── main.py
│   ├── database/
│   │   └── database.py
│   ├── models/
│   │   └── models.py
│   └── schemas/
│       └── schemas.py
├── migrations/
│   └── versions/
├── app_frontend.py
├── seed.py
├── requirements.txt
├── Dockerfile
├── alembic.ini
└── .env.example
```

## Boas práticas de segurança

- Nunca versione arquivos `.env` ou credenciais reais
- Rotacione imediatamente qualquer segredo que já tenha sido exposto
- Restrinja a chave da Gemini a um projeto e limites de uso adequados
- Use usuários de banco com permissões mínimas necessárias
- Em produção, configure CORS e autenticação antes de publicar a API

## Melhorias futuras

- Implementar testes unitários e de integração
- Adicionar autenticação e autorização
- Criar pipeline de CI com lint, testes e build Docker
- Centralizar as regras de negócio em uma camada de serviços
- Migrar IDs fixos do frontend para consultas dinâmicas à API
- Tornar a URL da API configurável por variável de ambiente
- Adicionar logs estruturados e monitoramento
- Criar testes específicos para cálculo de comissões e estoque

## Licença

Defina a licença utilizada pelo projeto antes da distribuição pública, por exemplo MIT.
# analist_aws
