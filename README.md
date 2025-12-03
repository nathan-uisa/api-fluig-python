# API Fluig - Abertura de Chamados

API REST desenvolvida com FastAPI para integração com o sistema Fluig, permitindo abertura automatizada de chamados nos ambientes de produção (PRD) e qualidade (QLD), com suporte a processamento inteligente via Inteligência Artificial e gerenciamento automático de autenticação via cookies.

## Índice

- [Funcionalidades](#funcionalidades)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Endpoints](#endpoints)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Autenticação](#autenticação)
- [Logs](#logs)
- [Versão](#versão)

## Funcionalidades

- **Abertura de Chamados**: Criação automática de chamados no Fluig (PRD e QLD), com suporte a chamados classificados e não classificados
- **Webapp Integrado**: Interface web completa para criação de chamados com autenticação Google OAuth 2.0
- **Geração em Lote**: Criação de múltiplos chamados via planilha Excel com processamento de placeholders
- **Autocomplete de Serviços**: Busca e seleção inteligente de serviços com preenchimento automático de campos
- **Modal de Processamento**: Interface visual para acompanhamento da criação de chamados em tempo real
- **Gerenciamento de Serviços**: Consulta de lista de serviços e detalhes de serviços específicos
- **Consulta de Datasets**: Busca de dados em datasets do Fluig (colleague, funcionários, aprovadores)
- **Detalhes de Chamados**: Obtenção de detalhes completos de chamados existentes
- **Integração com Terceiros**: Suporte especializado para integração com Movti, incluindo extração inteligente de usuários via IA
- **Autenticação Automática**: Sistema de gerenciamento de cookies com validação de expiração e re-autenticação automática
- **Inteligência Artificial**: Extração de informações de chamados usando Google Generative AI (Gemini)
- **Autenticação via API Key**: Proteção de todas as rotas com API Key
- **Logs Completos**: Sistema abrangente de logging com rastreamento detalhado em todas as operações
- **Validação Robusta**: Tratamento de erros e validações em todas as etapas do processo

## Requisitos

- Python 3.8+
- FastAPI 0.104.1+
- Uvicorn 0.24.0+
- Selenium 4.15.2+ (para autenticação via navegador)
- Requests 2.31.0+
- Pydantic 2.5.0+
- Pydantic-settings 2.1.0+
- Python-dotenv 1.0.0+

## Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd 23-fluig-api-python
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Configuração

1. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# API Key para autenticação
API_KEY=sua_api_key_aqui
API_NAME=nome_da_api

# Credenciais OAuth1 Fluig PRD (opcional, para compatibilidade)
CK=consumer_key_prd
CS=consumer_secret_prd
TK=token_prd
TS=token_secret_prd

# Credenciais OAuth1 Fluig QLD (opcional, para compatibilidade)
CK_QLD=consumer_key_qld
CS_QLD=consumer_secret_qld
TK_QLD=token_qld
TS_QLD=token_secret_qld

# URLs Fluig
URL_FLUIG_PRD=https://seu-fluig-prd.com.br
URL_FLUIG_QLD=https://seu-fluig-qld.com.br

# Credenciais de Login Fluig (para autenticação via navegador)
FLUIG_ADMIN_USER=admin@usuario.com.br
FLUIG_ADMIN_PASS=senha_admin
FLUIG_USER_NAME=usuario@usuario.com.br
FLUIG_USER_PASS=senha_usuario

# Credenciais de Login Fluig QLD (para autenticação via navegador no ambiente qualidade)
FLUIG_USER_NAME_QLD=usuario_qld@usuario.com.br
FLUIG_USER_PASS_QLD=senha_usuario_qld
USER_COLLEAGUE_ID_QLD=id_do_colaborador_qld

# ID do Colaborador Admin (para consultas PRD)
ADMIN_COLLEAGUE_ID=id_do_colaborador_admin

# Configurações IA (Google Generative AI)
IA_KEYS=sua_chave_1,sua_chave_2
IA_MODELS=gemini-pro,gemini-pro-vision

# Listas de controle (opcional)
WHITE_LIST_DOMAINS=dominio1.com,dominio2.com
BLACK_LIST_EMAILS=email1@exemplo.com,email2@exemplo.com

# Configurações do Webapp (Google OAuth 2.0)
GOOGLE_CLIENT_ID=seu_client_id_google
GOOGLE_CLIENT_PROJECT_ID=seu_project_id_google
GOOGLE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
GOOGLE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GOOGLE_REDIRECT_URIS=http://localhost:3000/login/callback
GOOGLE_CLIENT_SECRET=seu_client_secret_google
```

2. As pastas `src/json/` e `logs/` serão criadas automaticamente quando necessário.

## Uso

### Executar a aplicação:

```bash
python main.py
```

A API estará disponível em `http://127.0.0.1:3000`

### Documentação interativa:

Acesse a documentação automática do FastAPI:
- Swagger UI: `http://127.0.0.1:3000/docs`
- ReDoc: `http://127.0.0.1:3000/redoc`

### Webapp:

Acesse a interface web para criação de chamados:
- Login: `http://127.0.0.1:3000/login`
- Criar Chamado: `http://127.0.0.1:3000/chamado`

**Funcionalidades do Webapp:**
- Autenticação via Google OAuth 2.0
- Criação de chamados únicos ou em lote via planilha Excel
- Autocomplete de serviços com preenchimento automático de campos
- Modal de processamento com acompanhamento em tempo real
- Suporte a placeholders em planilhas (`<A>`, `<B>`, etc.)

## Endpoints


### 1. Abertura de Chamado (Sem Classificação)

**POST** `/api/v1/fluig/{ambiente}/chamados/abrir`

Abre um chamado sem classificação no Fluig. O ambiente é especificado no path (`prd` ou `qld`).

**Headers:**
```
API-KEY: sua_api_key
Content-Type: application/json
```

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "titulo": "Título do chamado",
  "descricao": "Descrição detalhada do chamado",
  "usuario": "email@usuario.com.br",
  "telefone": "5565999999999",
  "anexos_ids": ["id_arquivo_1", "id_arquivo_2"]
}
```

**Nota:** 
- O campo `telefone` é opcional. Se não fornecido ou vazio, será usado o valor padrão `"65"`.
- O campo `anexos_ids` é opcional e aceita uma lista de IDs de arquivos do Google Drive para anexar ao chamado.

**Resposta de Sucesso:**
```json
12345
```
(processInstanceId do chamado criado - retornado como número)

**Exemplo:**
```bash
POST /api/v1/fluig/prd/chamados/abrir
POST /api/v1/fluig/qld/chamados/abrir
```

---

### 2. Abertura de Chamado Classificado

**POST** `/api/v1/fluig/{ambiente}/chamados/abrir-classificado`

Abre um chamado classificado (com serviço) no Fluig. O ambiente é especificado no path (`prd` ou `qld`).

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "titulo": "Título do chamado",
  "descricao": "Descrição detalhada do chamado",
  "usuario": "email@usuario.com.br",
  "servico": "63531",
  "telefone": "5565999999999"
}
```

**Nota:** O campo `telefone` é opcional. Se não fornecido ou vazio, será usado o valor padrão `"65"`.

**Resposta de Sucesso:**
```json
12345
```
(processInstanceId do chamado criado - retornado como número)

**Exemplo:**
```bash
POST /api/v1/fluig/prd/chamados/abrir-classificado
POST /api/v1/fluig/qld/chamados/abrir-classificado
```

---

### 3. Detalhes de Chamado

**POST** `/api/v1/fluig/{ambiente}/chamados/detalhes`

Obtém os detalhes completos de um chamado existente. O ambiente é especificado no path (`prd` ou `qld`).

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "process_instance_id": 12345
}
```

**Resposta de Sucesso:**
```json
{
  "processInstanceId": 12345,
  "status": "Em Andamento",
  "formFields": { ... },
  ...
}
```

**Exemplo:**
```bash
POST /api/v1/fluig/prd/chamados/detalhes
POST /api/v1/fluig/qld/chamados/detalhes
```

---

### 4. Lista de Serviços

**GET** `/api/v1/fluig/{ambiente}/servicos`

Obtém a lista completa de serviços disponíveis no Fluig. O ambiente é especificado no path (`prd` ou `qld`).

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Query Parameters:**
- `limit` (opcional): Limite de resultados. Padrão: `300`
- `offset` (opcional): Offset para paginação. Padrão: `0`
- `orderby` (opcional): Ordenação. Padrão: `servico_ASC`
- `forcar_login` (opcional): Força novo login mesmo com cookies válidos. Padrão: `false`

**Resposta de Sucesso:**
```json
{
  "content": [
    {
      "id": "63531",
      "servico": "Nome do Serviço",
      ...
    },
    ...
  ]
}
```

**Nota:** Os serviços são automaticamente salvos em `src/json/servicos_{ambiente}.json`

**Exemplo:**
```bash
GET /api/v1/fluig/prd/servicos?limit=100
GET /api/v1/fluig/qld/servicos?limit=100
```

---

### 5. Detalhes de Serviço

**POST** `/api/v1/fluig/{ambiente}/servicos/detalhes`

Obtém os detalhes completos de um serviço específico. O ambiente é especificado no path (`prd` ou `qld`).

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "id_servico": "63531"
}
```

**Resposta de Sucesso:**
```json
{
  "id": "63531",
  "servico": "Nome do Serviço",
  "descricao": "Descrição do serviço",
  ...
}
```

**Nota:** Os detalhes são automaticamente salvos em `src/json/servico_detalhes_{id_servico}_{ambiente}.json`

**Exemplo:**
```bash
POST /api/v1/fluig/prd/servicos/detalhes
POST /api/v1/fluig/qld/servicos/detalhes
```

---

### 6. Busca em Dataset

**POST** `/api/v1/fluig/{ambiente}/datasets/buscar`

Busca dados em um dataset do Fluig usando email ou chapa/nome. O ambiente é especificado no path (`prd` ou `qld`).

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "dataset_id": "colleague",
  "user": "email@usuario.com.br"
}
```

**Datasets Disponíveis:**
- `colleague`: Busca por colaborador (email ou nome)
- `ds_funcionarios`: Busca por funcionário (email ou chapa)
- `ds_aprovadores`: Busca por aprovador (email ou nome)

**Resposta de Sucesso:**
```json
{
  "content": [
    {
      "colleagueId": "id_do_colaborador",
      "colleagueName": "Nome do Colaborador",
      "mail": "email@usuario.com.br",
      ...
    }
  ]
}
```

**Exemplo:**
```bash
POST /api/v1/fluig/prd/datasets/buscar
POST /api/v1/fluig/qld/datasets/buscar
```

---

### 7. Abertura de Chamado Movti (Terceiro)

**POST** `/api/v1/terceiros/{provider}/chamados/abrir-classificado`

Abre um chamado classificado no Fluig para terceiros, utilizando IA para extrair informações do usuário da descrição.

**Path Parameters:**
- `provider` (obrigatório): Provider terceiro (`movit`)

**Body:**
```json
{
  "titulo": "Título do chamado",
  "descricao": "Descrição do chamado que pode conter email ou chapa do usuário"
}
```

**Características:**
- Utiliza IA (Google Gemini) para extrair email ou chapa do usuário da descrição
- Se encontrar um usuário válido no Fluig, utiliza os dados reais
- Caso contrário, utiliza dados de um usuário fake pré-configurado
- Sempre utiliza o serviço fixo `1142587` para Movti
- Ambiente sempre PRD para terceiros

**Resposta de Sucesso:**
```json
12345
```
(processInstanceId do chamado criado - retornado como número)

**Exemplo:**
```bash
POST /api/v1/terceiros/movit/chamados/abrir-classificado
```

---

### 8. Rotas do Webapp

#### 8.1. Login

**GET** `/login`

Página de login do webapp com autenticação Google OAuth 2.0.

**GET** `/login/callback`

Callback do OAuth 2.0 após autenticação.

**GET** `/logout`

Encerra a sessão do usuário.

#### 8.2. Criação de Chamados

**GET** `/chamado`

Página principal do formulário de criação de chamados.

**POST** `/chamado`

Cria um chamado único ou processa planilha para criação em lote.

**Body (Form Data):**
- `ds_titulo`: Título do chamado
- `ds_chamado`: Descrição do chamado
- `servico_id`: ID do serviço (opcional, para chamado classificado)
- `planilha`: Arquivo Excel (.xlsx) para criação em lote (opcional)
- `qtd_chamados`: Quantidade de chamados a criar (quando usar planilha)
- `ignorar_primeira_linha`: Ignorar primeira linha da planilha (cabeçalho)

**Endpoints Auxiliares:**

- **POST** `/chamado/carregar-planilha`: Carrega e processa planilha Excel
- **POST** `/chamado/preview`: Gera prévia dos chamados com placeholders substituídos
- **GET** `/listar_servicos`: Retorna lista de serviços para autocomplete
- **POST** `/buscar_detalhes_servico`: Busca detalhes de um serviço por documentid

**Características:**
- Autenticação via sessão (Google OAuth 2.0)
- Busca automática de dados do funcionário via dataset interno
- Suporte a chamados classificados e não classificados
- Processamento de placeholders em planilhas (`<A>`, `<B>`, etc.)
- Modal de processamento com feedback em tempo real
- Cache local de detalhes de serviços

---

## Estrutura do Projeto

```
api-fluig-python/
├── src/
│   ├── auth/
│   │   ├── auth_api.py              # Autenticação via API Key
│   │   ├── auth_fluig.py            # Autenticação OAuth1 (legado)
│   │   └── auth_google_drive.py    # Autenticação Google Drive
│   ├── fluig/
│   │   └── fluig_core.py            # Classe principal para interação com Fluig
│   ├── fluig_requests/
│   │   └── requests.py              # Funções auxiliares para requisições HTTP
│   ├── web/
│   │   ├── web_auth_manager.py      # Gerenciador centralizado de autenticação
│   │   ├── web_cookies.py           # Gerenciamento de cookies (salvar, carregar, validar)
│   │   ├── web_driver.py            # Configuração do ChromeDriver/Selenium
│   │   ├── web_login_fluig.py       # Login via Selenium (unificado para PRD e QLD)
│   │   ├── web_servicos_fluig.py    # Funções para consulta de serviços
│   │   └── web_chamado_fluig.py     # Funções para consulta de chamados
│   ├── modelo_dados/
│   │   ├── modelo_settings.py       # Configurações e variáveis de ambiente
│   │   ├── modelos_fluig.py        # Modelos Pydantic para validação Fluig
│   │   ├── modelo_sites.py          # Modelos Pydantic específicos do webapp
│   │   └── modelo_database.py       # Modelos de banco de dados
│   ├── rotas/
│   │   ├── rt_fluig_chamados.py     # Rotas unificadas de chamados (PRD/QLD)
│   │   ├── rt_fluig_servicos.py     # Rotas unificadas de serviços (PRD/QLD)
│   │   ├── rt_fluig_datasets.py     # Rotas unificadas de datasets (PRD/QLD)
│   │   ├── rt_terceiro.py           # Rotas para integrações de terceiros (Movti)
│   │   └── webapp/
│   │       ├── rt_login.py          # Rotas de autenticação do webapp
│   │       └── rt_chamado.py        # Rotas de criação de chamados do webapp
│   ├── site/
│   │   ├── classes/                 # Classes do webapp (legado - removido)
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── style.css        # Estilos do webapp
│   │   │   └── js/
│   │   │       └── chamado.js       # JavaScript do formulário de chamados
│   │   ├── templates/
│   │   │   └── chamado.html         # Template HTML do formulário de chamados
│   │   ├── planilha.py              # Processamento de planilhas Excel
│   │   └── abrir_chamados.py        # Lógica de criação de chamados em lote
│   ├── terceiro/
│   │   └── movit_core.py            # Lógica específica para Movti
│   ├── utilitarios_centrais/
│   │   ├── logger.py                # Configuração de logging
│   │   ├── payloads.py              # Construção de payloads para chamados
│   │   ├── json_utils.py            # Funções utilitárias para salvamento de JSON
│   │   ├── fake_user.py             # Dados de usuário fake para testes
│   │   ├── email_utils.py           # Utilitários para processamento de email
│   │   └── google_drive_utils.py    # Utilitários para Google Drive
│   ├── ia/
│   │   └── ia.py                    # Integração com Google Generative AI
│   │   └── prompts/
│   │       └── prompts.py          # Prompts para IA
│   ├── base_ia/                     # Módulo de IA alternativo (legado)
│   ├── json/                        # Diretório para arquivos JSON (cookies, serviços)
│   │   └── services/                # Detalhes de serviços salvos localmente
│   └── chromedriver-linux64/        # ChromeDriver para Linux
├── logs/                            # Diretório de logs (criado automaticamente)
├── main.py                          # Aplicação principal FastAPI
├── requirements.txt                 # Dependências do projeto
├── Dockerfile                       # Configuração Docker
└── README.md                        # Este arquivo
```

## Autenticação

### Autenticação da API

Todas as rotas da API REST (exceto `/` e rotas do webapp) requerem autenticação via header `API-KEY`:

```
API-KEY: sua_api_key_configurada_no_env
```

### Autenticação do Webapp

O webapp utiliza autenticação via Google OAuth 2.0:

- **Login**: Usuários fazem login através do Google OAuth 2.0
- **Sessão**: Após autenticação, uma sessão é criada e mantida
- **Proteção de Rotas**: Rotas do webapp (`/login`, `/chamado`) são protegidas por sessão
- **Logout**: Usuários podem fazer logout através da rota `/logout`

### Autenticação no Fluig

O sistema utiliza autenticação via cookies obtidos através de login via Selenium:

- **Login Automático**: O sistema realiza login via navegador (Selenium) quando necessário
- **Login Unificado**: Um único módulo (`web_login_fluig.py`) gerencia login para ambos os ambientes (PRD e QLD)
- **Seleção Automática de Ambiente**: O sistema seleciona automaticamente a URL correta baseado no parâmetro ambiente
- **Credenciais por Ambiente**: 
  - Ambiente PRD: usa `FLUIG_USER_NAME` e `FLUIG_USER_PASS`
  - Ambiente QLD: usa `FLUIG_USER_NAME_QLD` e `FLUIG_USER_PASS_QLD`
- **Gerenciamento de Cookies**: Cookies são salvos em `src/json/cookies_{usuario}_{ambiente}.json`
- **Validação de Expiração**: O sistema verifica automaticamente se os cookies estão expirados (incluindo JWT)
- **Re-autenticação Automática**: Se os cookies estiverem expirados ou inválidos, o sistema realiza login novamente automaticamente
- **Usuários Separados**: Cookies são gerenciados separadamente para cada usuário e ambiente
- **Colleague ID por Ambiente**: 
  - Ambiente PRD: usa `ADMIN_COLLEAGUE_ID`
  - Ambiente QLD: usa `USER_COLLEAGUE_ID_QLD`

### Códigos de Status HTTP:

- `200`: Sucesso
- `400`: Erro de validação
- `401`: Não autorizado (API Key inválida ou cookies expirados)
- `403`: Acesso negado
- `500`: Erro interno do servidor

## Exemplo de Uso com cURL

### Abertura de chamado sem classificação (PRD):
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/chamados/abrir" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Problema no sistema",
    "descricao": "O sistema está apresentando lentidão",
    "usuario": "usuario@email.com.br",
    "telefone": "5565999999999"
  }'
```

### Abertura de chamado sem classificação (QLD):
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/qld/chamados/abrir" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Problema no sistema",
    "descricao": "O sistema está apresentando lentidão",
    "usuario": "usuario@email.com.br"
  }'
```

### Abertura de chamado classificado:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/chamados/abrir-classificado" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Solicitação de acesso",
    "descricao": "Preciso de acesso ao sistema X",
    "usuario": "usuario@email.com.br",
    "servico": "DocumentId",
    "telefone": "5565999999999"
  }'
```

### Buscar detalhes de chamado:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/chamados/detalhes" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "process_instance_id": 12345
  }'
```

### Buscar lista de serviços:
```bash
curl -X GET "http://127.0.0.1:3000/api/v1/fluig/prd/servicos?limit=100" \
  -H "API-KEY: sua_api_key"
```

### Buscar detalhes de um serviço:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/servicos/detalhes" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "id_servico": "63531"
  }'
```

### Buscar em dataset:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/datasets/buscar" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "colleague",
    "user": "usuario@email.com.br"
  }'
```

### Abertura de chamado Movti (Terceiro):
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/terceiros/movit/chamados/abrir-classificado" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Alerta de Segurança",
    "descricao": "Alerta detectado para o usuário usuario@email.com.br"
  }'
```

## Logs

### Níveis de Log

- **INFO**: Operações principais, requisições recebidas, sucessos
- **DEBUG**: Detalhes de processamento, validações internas, payloads
- **WARNING**: Situações que requerem atenção (cookies expirados, dados não encontrados)
- **ERROR**: Erros que impedem a operação (com stack trace completo)

### Logs Implementados

- **Rotas**: Todas as rotas principais registram entrada, processamento e resultado
- **Autenticação**: Tentativas de autenticação, validação de cookies e falhas são registradas
- **Requisições Fluig**: Todas as chamadas à API Fluig são logadas com detalhes
- **Datasets**: Buscas em datasets são registradas com parâmetros e resultados
- **IA**: Processamento de IA com contador de tentativas e erros
- **Payloads**: Construção de payloads é logada para debugging
- **Cookies**: Gerenciamento de cookies (salvar, carregar, validar) é logado

### Localização dos Logs

Os logs são salvos automaticamente na pasta `logs/` na raiz do projeto.

## Versão

**Versão Atual: 3.0.0**

### Mudanças na Versão 3.0.0 (Padronização):
- ✅ **Padronização de Rotas**: Todas as rotas agora seguem o padrão `/api/v1/fluig/{ambiente}/...`
- ✅ **Ambiente como Path Parameter**: Ambiente (`prd` ou `qld`) agora é especificado no path da URL
- ✅ **Versionamento de API**: Implementado prefixo `/api/v1` para versionamento
- ✅ **Estrutura RESTful**: Hierarquia clara e semântica para melhor organização
- ✅ **Rotas Unificadas**: Rotas PRD e QLD unificadas em um único endpoint com parâmetro de ambiente
- ✅ **Rotas de Terceiros**: Padronizadas para `/api/v1/terceiros/{provider}/...`
- ✅ **Webapp Integrado**: Interface web completa para criação de chamados com autenticação Google OAuth 2.0
- ✅ **Geração em Lote**: Suporte a criação de múltiplos chamados via planilha Excel
- ✅ **Autocomplete de Serviços**: Busca e seleção inteligente de serviços com preenchimento automático
- ✅ **Modal de Processamento**: Interface visual para acompanhamento da criação de chamados em tempo real
- ✅ **Refatoração de Modelos**: Modelos de dados organizados em `src/modelo_dados/` (incluindo `modelo_sites.py`)
- ✅ **Otimização de Performance**: Uso direto de `FluigCore` em vez de requisições HTTP internas
- ✅ **Compatibilidade**: Mantida estrutura anterior para facilitar migração gradual

### Versões Anteriores (2.1.1 e anteriores):

Principais mudanças nas versões anteriores:
- **Rotas QLD Completas**: Implementação completa de rotas para ambiente de qualidade
  - `/fluigqld/chamado/abrir` - Abertura de chamados sem classificação
  - `/fluigqld/chamado/detalhes` - Detalhes de chamados
  - `/fluigqld/servicos` - Lista de serviços
  - `/fluigqld/servicos/detalhes` - Detalhes de serviços
  - `/fluigqld/datasets/buscar` - Busca em datasets
- **Isolamento de Ambientes**: Garantia de que rotas QLD não utilizam dados do ambiente PRD
- **Consolidação de Login**: Unificação dos módulos de login em um único arquivo com seleção automática de ambiente
- **Seleção Dinâmica de Credenciais**: Sistema seleciona automaticamente credenciais corretas baseado no ambiente
- **Centralização de Funções**: Funções de salvamento JSON centralizadas em `json_utils.py`
- **Correção de Colleague ID**: Seleção automática do colleague ID correto por ambiente
- Sistema de autenticação via cookies com Selenium
- Gerenciamento automático de cookies com validação de expiração (incluindo JWT)
- Suporte a múltiplos usuários com cookies separados por ambiente
- Integração com Movti usando IA para extração de usuários
- Estrutura modular e organizada

Para ver o histórico completo de versões, consulte o arquivo - `version`.
