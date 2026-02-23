# Configuração do Monitoramento de Emails (Gmail Monitor)

Este documento descreve como configurar o módulo de monitoramento de emails que substitui o Apps Script do Google.

## Visão Geral

O módulo `gmail_monitor` monitora automaticamente emails não lidos no Gmail, processa anexos, valida remetentes e abre chamados no Fluig automaticamente. Ele replica toda a funcionalidade do `Apps_Script.js` em Python.

## Pré-requisitos

1. **Conta de Serviço do Google Cloud**
   - Uma conta de serviço configurada no Google Cloud Platform
   - As credenciais da conta de serviço devem estar configuradas no arquivo `.env`

2. **Permissões Necessárias no Google Workspace**
   - A conta de serviço precisa ter acesso aos seguintes serviços:
     - Gmail API (leitura e modificação)
     - Google Drive API (leitura e escrita)
     - People API (leitura do diretório)

3. **Delegação de Domínio (Recomendado)**
   - Para acessar emails de usuários específicos, configure a delegação de domínio no Google Workspace Admin Console

## Configuração no Google Cloud Platform

### 1. Habilitar APIs Necessárias

No Google Cloud Console, habilite as seguintes APIs:

- **Gmail API**
- **Google Drive API**
- **People API**

**Passos:**
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Selecione seu projeto
3. Vá em **APIs & Services** > **Library**
4. Busque e habilite cada uma das APIs acima

### 2. Configurar Conta de Serviço

1. Vá em **IAM & Admin** > **Service Accounts**
2. Crie uma nova conta de serviço ou use uma existente
3. Anote o email da conta de serviço (formato: `nome@projeto.iam.gserviceaccount.com`)
4. Crie uma chave JSON:
   - Clique na conta de serviço
   - Vá em **Keys** > **Add Key** > **Create new key**
   - Selecione **JSON** e baixe o arquivo

### 3. Configurar Permissões no Google Workspace Admin

#### Para Gmail API (Delegação de Domínio)

1. Acesse [Google Admin Console](https://admin.google.com/)
2. Vá em **Security** > **API Controls** > **Domain-wide Delegation**
3. Clique em **Add new**
4. Preencha:
   - **Client ID**: O `client_id` da sua conta de serviço (encontrado no JSON)
   - **OAuth Scopes**: Adicione os seguintes escopos:
     ```
     https://www.googleapis.com/auth/gmail.readonly
     https://www.googleapis.com/auth/gmail.modify
     https://www.googleapis.com/auth/gmail.send
     https://www.googleapis.com/auth/drive.file
     https://www.googleapis.com/auth/drive.readonly
     https://www.googleapis.com/auth/directory.readonly
     ```
5. Clique em **Authorize**

#### Para Google Drive (Compartilhar Pasta)

1. Crie uma pasta no Google Drive para armazenar anexos
2. Compartilhe a pasta com o email da conta de serviço
3. Dê permissão de **Editor** para a conta de serviço
4. Copie o ID da pasta da URL (exemplo: `1ZbYzUiVWON-54NrKrg9BhqEdRQsJT5F2`)

#### Para People API (Diretório)

A People API requer que a conta de serviço tenha acesso ao diretório do Google Workspace. Isso geralmente é configurado automaticamente quando você habilita a API e configura a delegação de domínio.

## Configuração no Projeto

### 1. Variáveis de Ambiente

Adicione as seguintes variáveis no arquivo `.env`:

```env
# Configurações existentes da conta de serviço (já devem estar configuradas)
TYPE=service_account
PROJECT_ID=seu-projeto-id
PRIVCATE_JEY_ID=chave-id
PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
CLIENT_EMAIL=seu-servico@projeto.iam.gserviceaccount.com
CLIENT_ID=seu-client-id
AUTH_URI=https://accounts.google.com/o/oauth2/auth
TOKEN_URI=https://oauth2.googleapis.com/token
AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
UNIVERSE_DOMAIN=googleapis.com

# ID da pasta do Google Drive para anexos
FOLDER_ID_DRIVE=1ZbYzUiVWON-54NrKrg9BhqEdRQsJT5F2

# Email para delegação de domínio (opcional)
# Se configurado, o sistema usará este email para acessar a caixa de entrada
# Deixe vazio para usar a conta de serviço diretamente
GMAIL_DELEGATE_USER=usuario@uisa.com.br

# Endpoints da API (opcional - usa valores padrão se não configurado)
API_ENDPOINT_CHAMADO_UISA=https://api-fluig-python-186726132534.us-east1.run.app/api/v1/fluig/prd/chamados/abrir

# Ambiente do Fluig para monitoramento (prd ou qld)
GMAIL_MONITOR_AMBIENTE=prd

# Intervalo de verificação de emails (em minutos)
GMAIL_CHECK_INTERVAL=1
```

### 2. Instalar Dependências

As dependências necessárias já estão no `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Funcionamento

### Fluxo de Processamento

1. **Monitoramento**: O serviço verifica emails não lidos a cada intervalo configurado (padrão: 1 minuto)

2. **Validação**: Cada email é validado:
   - Deve ser de domínio `@uisa.com.br` ou estar na lista de permitidos
   - Não pode ser de emails de sistema bloqueados

3. **Processamento de Anexos**: 
   - Anexos são baixados e salvos no Google Drive
   - IDs dos arquivos são coletados

4. **Busca de Telefone**: 
   - O sistema busca o telefone do remetente no diretório do Google Workspace

5. **Abertura de Chamado**:
   - Chama a API para abrir o chamado
   - Para emails `@movti.com.br`, usa endpoint específico
   - Para outros emails, usa endpoint padrão UISA

6. **Resposta ao Usuário**:
   - Envia email de confirmação com número do chamado e link
   - Em caso de erro, envia email informando o problema

7. **Marcação como Processado**:
   - Adiciona label "PROCESSADOS" ao email
   - Marca como lido

### Labels do Gmail

O sistema cria automaticamente uma label chamada **"PROCESSADOS"** no Gmail. Emails processados são marcados com esta label para evitar reprocessamento.

## Testando a Configuração

### Teste Manual

Você pode testar o processamento manualmente usando Python:

```python
from src.gmail_monitor.gmail_service import GmailMonitorService

# Cria o serviço
monitor = GmailMonitorService()

# Processa emails uma vez
monitor.processar_emails()
```

### Verificar Logs

Os logs são salvos em `logs/api_fluig.log`. Procure por mensagens com prefixo `[gmail_service]`, `[gmail_background]`, etc.

## Troubleshooting

### Erro: "Insufficient Permission"

**Causa**: A conta de serviço não tem as permissões necessárias.

**Solução**:
1. Verifique se todas as APIs estão habilitadas
2. Verifique se a delegação de domínio está configurada corretamente
3. Verifique se os escopos OAuth estão corretos

### Erro: "User not found" ao acessar Gmail

**Causa**: A conta de serviço não tem acesso à caixa de entrada ou a delegação não está configurada.

**Solução**:
1. Configure `GMAIL_DELEGATE_USER` no `.env` com um email válido do domínio
2. Verifique se a delegação de domínio está configurada no Admin Console

### Erro: "Folder not found" ao salvar anexos

**Causa**: A pasta do Drive não existe ou a conta de serviço não tem acesso.

**Solução**:
1. Verifique se `FOLDER_ID_DRIVE` está correto
2. Compartilhe a pasta com o email da conta de serviço
3. Dê permissão de Editor

### Emails não estão sendo processados

**Causa**: Vários possíveis.

**Solução**:
1. Verifique os logs em `logs/api_fluig.log`
2. Verifique se o serviço está rodando (deve aparecer no startup da aplicação)
3. Verifique se há emails não lidos na caixa de entrada
4. Verifique se os emails não têm a label "PROCESSADOS"

## Diferenças do Apps Script

### Vantagens da Implementação Python

1. **Integração nativa**: Executa no mesmo servidor da API
2. **Melhor controle**: Logs centralizados e melhor tratamento de erros
3. **Manutenção**: Código versionado junto com o projeto
4. **Escalabilidade**: Pode ser executado em múltiplas instâncias com coordenação

### Funcionalidades Mantidas

- ✅ Monitoramento de emails não lidos
- ✅ Validação de domínio e emails bloqueados
- ✅ Processamento de anexos
- ✅ Upload de anexos no Google Drive
- ✅ Busca de telefone no diretório
- ✅ Abertura de chamados via API
- ✅ Envio de emails de confirmação
- ✅ Marcação de emails como processados

## Desativando o Monitoramento

Para desativar temporariamente o monitoramento, comente as linhas no `main.py`:

```python
# logger.info("Iniciando monitoramento de emails do Gmail...")
# iniciar_monitoramento_gmail()
```

E no shutdown:

```python
# logger.info("Parando monitoramento de emails...")
# parar_monitoramento_gmail()
```

## Suporte

Em caso de problemas, verifique:
1. Logs em `logs/api_fluig.log`
2. Configurações no `.env`
3. Permissões no Google Cloud Console
4. Delegação de domínio no Google Workspace Admin
