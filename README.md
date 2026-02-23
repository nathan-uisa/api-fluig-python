# API Fluig - Abertura de Chamados

API REST desenvolvida com FastAPI para integração com o sistema Fluig, permitindo abertura automatizada de chamados nos ambientes de produção (PRD) e qualidade (QLD), com suporte a processamento inteligente via Inteligência Artificial e autenticação via OAuth 1.0.

**Versão Atual:** 7.3.2

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
- **Campo Solicitante**: Suporte a Chapa, email ou placeholders com busca automática do nome formatado
- **Autocomplete de Serviços**: Busca e seleção inteligente de serviços com preenchimento automático de campos
- **Modal de Processamento**: Interface visual para acompanhamento da criação de chamados em tempo real
- **Visualização Prévia**: Prévia dos chamados incluindo título, descrição e solicitante processado
- **Gerenciamento de Serviços**: Consulta de lista de serviços e detalhes de serviços específicos
- **Consulta de Datasets**: Busca de dados em datasets do Fluig (colleague, funcionários, aprovadores) com suporte a busca por CHAPA
- **Detalhes de Chamados**: Obtenção de detalhes completos de chamados existentes
- **Autenticação OAuth 1.0**: Autenticação segura via OAuth 1.0 para todas as operações com o Fluig
- **Inteligência Artificial**: Extração de informações de chamados usando Google Generative AI (Gemini)
- **Autenticação via API Key**: Proteção de todas as rotas com API Key
- **Monitoramento de Emails**: Processamento automático de emails do Gmail para abertura de chamados (substitui Apps Script)
- **Processos Genéricos**: Endpoints para iniciar qualquer processo/formulário do Fluig com payload genérico
- **Upload e Anexo de Arquivos**: Upload de arquivos no ECM e anexo a processos existentes (base64 ou multipart/form-data)
- **Obtenção Automática de Detalhes**: Detecção automática de versão, movimento e atividade de processos
- **Logs Completos**: Sistema abrangente de logging com rastreamento detalhado em todas as operações
- **Validação Robusta**: Tratamento de erros e validações em todas as etapas do processo

## Requisitos

- Python 3.8+
- FastAPI 0.104.1+
- Uvicorn 0.24.0+
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

# ID do Colaborador QLD (opcional)
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

### Webapp:

Acesse a interface web para criação de chamados:
- Login: `http://127.0.0.1:3000/login`
- Criar Chamado: `http://127.0.0.1:3000/chamado`

**Funcionalidades do Webapp:**
- Autenticação via Google OAuth 2.0
- Criação de chamados únicos ou em lote via planilha Excel
- Autocomplete de serviços com preenchimento automático de campos
- Campo "Solicitante" com suporte a chapa, email ou placeholders da planilha
- Busca automática do nome formatado do solicitante (primeira letra maiúscula)
- Campo UsuarioAtendido preenchido automaticamente quando solicitante é informado
- Modal de processamento com acompanhamento em tempo real
- Visualização prévia dos chamados incluindo título, descrição e solicitante
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
  "anexos": [
    {
      "nome": "documento.pdf",
      "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
    }
  ]
}
```

**Nota:** 
- O campo `telefone` é opcional. Se não fornecido ou vazio, será usado o valor padrão `"65"`.
- O campo `anexos` é opcional e aceita uma lista de anexos em base64. Cada anexo deve conter `nome` (string) e `conteudo_base64` (string com o conteúdo do arquivo codificado em base64).

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
- `colleague`: Busca por colaborador (email, nome ou chapa)
  - Email: usa campo `mail`
  - chapa (número): usa campo `currentProject`
  - Nome (texto): usa campo `colleagueName`
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

### 7. Iniciar Processo Genérico

**POST** `/api/v1/fluig/{ambiente}/processos/iniciar`

Inicia qualquer processo ou formulário do Fluig usando um payload genérico e flexível.

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "process_id": "Abertura de Chamados",
  "payload": {
    "processId": "Abertura de Chamados",
    "version": 1,
    "managerMode": false,
    "taskUserId": "12345",
    "isDigitalSigned": false,
    "selectedState": 5,
    "campos": {
      "titulo": "Exemplo",
      "descricao": "Descrição do exemplo"
    }
  }
}
```

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "process_id": "Abertura de Chamados",
  "process_instance_id": 12345,
  "dados": { ... },
  "mensagem": "Processo iniciado com sucesso"
}
```

**Exemplo:**
```bash
POST /api/v1/fluig/prd/processos/iniciar
POST /api/v1/fluig/qld/processos/iniciar
```

---

### 8. Upload de Arquivos

**POST** `/api/v1/fluig/{ambiente}/processos/upload`

Faz upload de arquivo(s) no ECM do Fluig sem criar processo.

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "arquivos": [
    {
      "nome": "documento.pdf",
      "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
    }
  ],
  "colleague_id": "12345"
}
```

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "total_arquivos": 1,
  "arquivos_enviados": 1,
  "arquivos_com_erro": 0,
  "detalhes": {
    "enviados": [
      {
        "nome": "documento.pdf",
        "tamanho_bytes": 1024,
        "dados": { ... }
      }
    ],
    "erros": []
  }
}
```

**Exemplo:**
```bash
POST /api/v1/fluig/prd/processos/upload
POST /api/v1/fluig/qld/processos/upload
```

---

### 9. Anexar Arquivos (Base64)

**POST** `/api/v1/fluig/{ambiente}/processos/anexar`

Anexa arquivo(s) codificados em base64 a um processo/chamado existente.

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body:**
```json
{
  "process_id": "Abertura de Chamados",
  "process_instance_id": 657984,
  "arquivos": [
    {
      "nome": "documento.pdf",
      "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
    }
  ]
}
```

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "process_id": "Abertura de Chamados",
  "process_instance_id": 657984,
  "total_arquivos": 1,
  "arquivos_anexados": 1,
  "arquivos_com_erro": 0,
  "detalhes": {
    "anexados": [
      {
        "documentId": 12345,
        "fileName": "documento.pdf",
        "fullPath": "BPM"
      }
    ],
    "erros": []
  }
}
```

**Nota:** Os valores de `version`, `current_movto` e `attached_activity` são obtidos automaticamente da atividade do chamado.

**Exemplo:**
```bash
POST /api/v1/fluig/prd/processos/anexar
POST /api/v1/fluig/qld/processos/anexar
```

---

### 10. Anexar Arquivos (Upload Direto)

**POST** `/api/v1/fluig/{ambiente}/processos/anexar-upload`

Anexa arquivo(s) brutos (multipart/form-data) a um processo/chamado existente. Ideal para uso no Swagger UI.

**Path Parameters:**
- `ambiente` (obrigatório): Ambiente do Fluig (`prd` ou `qld`)

**Body (multipart/form-data):**
- `process_id`: ID ou nome do processo (ex: "Abertura de Chamados")
- `process_instance_id`: Número do chamado
- `arquivos`: Arquivo(s) para anexar

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "process_id": "Abertura de Chamados",
  "process_instance_id": 657984,
  "total_arquivos": 1,
  "arquivos_anexados": 1,
  "arquivos_com_erro": 0,
  "detalhes": {
    "anexados": [
      {
        "documentId": 12345,
        "fileName": "documento.pdf",
        "fullPath": "BPM"
      }
    ],
    "erros": []
  }
}
```

**Nota:** Os valores de `version`, `current_movto` e `attached_activity` são obtidos automaticamente da atividade do chamado.

**Exemplo:**
```bash
POST /api/v1/fluig/prd/processos/anexar-upload
POST /api/v1/fluig/qld/processos/anexar-upload
```

---

### 11. Rotas do Webapp

#### 7.1. Login

**GET** `/login`

Página de login do webapp com autenticação Google OAuth 2.0.

**GET** `/login/callback`

Callback do OAuth 2.0 após autenticação.

**GET** `/logout`

Encerra a sessão do usuário.

#### 7.2. Criação de Chamados

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
- Campo "Solicitante" com suporte a chapa, email ou placeholders
- Busca automática do nome formatado do solicitante via dataset colleague
- Campo UsuarioAtendido preenchido automaticamente com nome formatado corretamente
- Modal de processamento com feedback em tempo real
- Visualização prévia dos chamados incluindo solicitante processado
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
│   │   ├── fluig_core.py            # Classe principal para interação com Fluig
│   │   └── fluig_requests.py        # Classe para requisições HTTP ao Fluig
│   ├── web/
│   │   ├── web_auth_manager.py      # Gerenciador centralizado de autenticação
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
│   │   ├── rt_fluig_processos.py    # Rotas genéricas de processos (iniciar, upload, anexar)
│   │   └── webapp/
│   │       ├── rt_login.py          # Rotas de autenticação do webapp
│   │       └── rt_chamado.py        # Rotas de criação de chamados do webapp
│   ├── site/
│   │   ├── classes/                 # Classes do webapp (legado - removido)
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── style.css        # Estilos do webapp
│   │   │   └── js/
│   │   │       ├── chamado.js       # JavaScript do formulário de chamados
│   │   │       └── configuracoes.js # JavaScript da página de configurações
│   │   ├── templates/
│   │   │   ├── chamado.html         # Template HTML do formulário de chamados
│   │   │   ├── configuracoes.html   # Template HTML da página de configurações
│   │   │   └── login.html           # Template HTML da página de login
│   │   ├── planilha.py              # Processamento de planilhas Excel
│   │   └── abrir_chamados.py        # Lógica de criação de chamados em lote
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
│   ├── json/                        # Diretório para arquivos JSON (serviços)
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

O sistema utiliza autenticação via OAuth 1.0 para todas as operações com o Fluig:

- **Autenticação OAuth 1.0**: Todas as requisições utilizam OAuth 1.0 com Consumer Key/Secret e Token/Token Secret
- **Credenciais por Ambiente**: 
  - Ambiente PRD: usa `CK`, `CS`, `TK`, `TS`
  - Ambiente QLD: usa `CK_QLD`, `CS_QLD`, `TK_QLD`, `TS_QLD`
- **Colleague ID por Ambiente**: 
  - Ambiente PRD: usa `ADMIN_COLLEAGUE_ID`
  - Ambiente QLD: usa `USER_COLLEAGUE_ID_QLD`

### Códigos de Status HTTP:

- `200`: Sucesso
- `400`: Erro de validação
- `401`: Não autorizado (API Key inválida)
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

### Iniciar processo genérico:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/processos/iniciar" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "process_id": "Abertura de Chamados",
    "payload": {
      "processId": "Abertura de Chamados",
      "version": 1,
      "managerMode": false,
      "taskUserId": "12345",
      "isDigitalSigned": false,
      "selectedState": 5,
      "campos": {
        "titulo": "Exemplo",
        "descricao": "Descrição do exemplo"
      }
    }
  }'
```

### Upload de arquivo:
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/processos/upload" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "arquivos": [
      {
        "nome": "documento.pdf",
        "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
      }
    ]
  }'
```

### Anexar arquivo (base64):
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/processos/anexar" \
  -H "API-KEY: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "process_id": "Abertura de Chamados",
    "process_instance_id": 657984,
    "arquivos": [
      {
        "nome": "documento.pdf",
        "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
      }
    ]
  }'
```

### Anexar arquivo (upload direto):
```bash
curl -X POST "http://127.0.0.1:3000/api/v1/fluig/prd/processos/anexar-upload" \
  -H "API-KEY: sua_api_key" \
  -F "process_id=Abertura de Chamados" \
  -F "process_instance_id=657984" \
  -F "arquivos=@documento.pdf"
```

## Monitoramento de Emails (Gmail Monitor)

O projeto inclui um módulo completo de monitoramento de emails que substitui o Apps Script do Google. Este módulo:

- Monitora automaticamente emails não lidos no Gmail
- Valida remetentes (domínio UISA ou emails permitidos)
- Processa anexos e salva no Google Drive
- Busca telefone do remetente no diretório do Google Workspace
- Abre chamados automaticamente via API
- Envia emails de confirmação aos usuários

### Configuração

Para configurar o monitoramento de emails, consulte a documentação completa em:
**[src/gmail_monitor/README.md](src/gmail_monitor/README.md)**

### Funcionalidades

- ✅ Monitoramento automático em background
- ✅ Processamento de anexos
- ✅ Validação de segurança de emails
- ✅ Suporte a emails UISA
- ✅ Integração com Google Drive e People API
- ✅ Logs detalhados de todas as operações

### Desativar Monitoramento

O monitoramento é iniciado automaticamente com a aplicação. Para desativar, comente as linhas no `main.py`:

```python
# iniciar_monitoramento_gmail()
# parar_monitoramento_gmail()
```

## Monitoramento de Histórico de Chamados

O projeto inclui um sistema completo de monitoramento de histórico de chamados abertos via email. Este sistema:

- Salva automaticamente o histórico inicial quando um chamado é aberto via email
- Monitora atualizações nos históricos periodicamente (a cada 1 hora, configurável)
- Detecta novos eventos (MOVEMENT, OBSERVATION, ATTACHMENT) nos chamados
- Armazena históricos em arquivos `.ini` usando ConfigParser

### Configuração

Para configurar o monitoramento de histórico, consulte a documentação completa em:
**[src/historico_monitor/README.md](src/historico_monitor/README.md)**

### Funcionalidades

- ✅ Salvamento automático de histórico ao abrir chamado via email
- ✅ Monitoramento periódico de atualizações
- ✅ Detecção automática de novos eventos
- ✅ Armazenamento simples em arquivos `.ini`
- ✅ Inicialização automática com a aplicação

### Variáveis de Ambiente

```env
# Habilitar/desabilitar monitoramento (padrão: true)
HISTORICO_MONITOR_ENABLED=true

# Intervalo de verificação em horas (padrão: 1.0)
HISTORICO_CHECK_INTERVAL_HOURS=1.0

# Ambiente do Fluig para monitoramento (padrão: PRD)
HISTORICO_MONITOR_AMBIENTE=PRD
```

### Desativar Monitoramento

O monitoramento é iniciado automaticamente com a aplicação. Para desativar, configure no `.env`:

```env
HISTORICO_MONITOR_ENABLED=false
```

## Logs

### Níveis de Log

- **INFO**: Operações principais, requisições recebidas, sucessos
- **DEBUG**: Detalhes de processamento, validações internas, payloads
- **WARNING**: Situações que requerem atenção (dados não encontrados, validações)
- **ERROR**: Erros que impedem a operação (com stack trace completo)

### Logs Implementados

- **Rotas**: Todas as rotas principais registram entrada, processamento e resultado
- **Autenticação**: Tentativas de autenticação e falhas são registradas
- **Requisições Fluig**: Todas as chamadas à API Fluig são logadas com detalhes
- **Datasets**: Buscas em datasets são registradas com parâmetros e resultados
- **IA**: Processamento de IA com contador de tentativas e erros
- **Payloads**: Construção de payloads é logada para debugging
- **OAuth**: Requisições OAuth 1.0 são logadas com detalhes

### Localização dos Logs

Os logs são salvos automaticamente na pasta `logs/` na raiz do projeto.


Para ver o histórico completo de versões, consulte o arquivo - `version`.

## 📞 Suporte

Deus lhe ajude.
