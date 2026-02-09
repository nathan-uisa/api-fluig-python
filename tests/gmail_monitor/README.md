# Testes do Módulo Gmail Monitor

Esta pasta contém scripts de teste para validar e verificar o funcionamento do módulo de monitoramento de emails.

## Scripts Disponíveis

### 1. `test_processar_email_mais_recente.py` ⭐ **TESTE DE INTEGRAÇÃO**
Processa o email mais recente seguindo o fluxo completo.

**Uso:**
```bash
python tests/gmail_monitor/test_processar_email_mais_recente.py
```

Este é o teste mais completo, simulando todo o processo de monitoramento.

---

### 2. `test_listar_emails_nao_lidos.py`
Lista todos os emails não lidos da caixa de entrada.

**Uso:**
```bash
python tests/gmail_monitor/test_listar_emails_nao_lidos.py
```

**O que faz:**
- Conecta ao Gmail via API
- Busca threads não lidas
- Exibe informações de cada email (remetente, assunto, data, labels)
- Indica se o email já foi processado

---

### 3. `test_listar_emails_processados.py`
Lista emails que foram lidos e marcados com a label "PROCESSADOS".

**Uso:**
```bash
python tests/gmail_monitor/test_listar_emails_processados.py
```

**O que faz:**
- Busca emails com a label PROCESSADOS
- Exibe informações detalhadas de cada email processado
- Mostra status de leitura e labels aplicadas

---

### 4. `test_checar_permissoes.py`
Verifica se a conta de serviço tem todas as permissões necessárias.

**Uso:**
```bash
python tests/gmail_monitor/test_checar_permissoes.py
```

**O que faz:**
- Testa acesso ao Gmail API (leitura, modificação, envio)
- Testa acesso ao Google Drive API (leitura, escrita)
- Testa acesso ao People API (diretório)
- Verifica acesso à pasta configurada no Drive
- Exibe resumo das permissões

**Resultado esperado:**
```
✅ Gmail API:     ✅ OK
✅ Drive API:     ✅ OK
✅ People API:    ✅ OK
```

---

### 5. `test_enviar_email.py`
Envia um email de teste para um destinatário específico.

**Uso:**
```bash
# Envio básico
python tests/gmail_monitor/test_enviar_email.py usuario@uisa.com.br

# Com assunto personalizado
python tests/gmail_monitor/test_enviar_email.py usuario@uisa.com.br --assunto "Teste Personalizado"

# Com assunto e corpo personalizados
python tests/gmail_monitor/test_enviar_email.py usuario@uisa.com.br --assunto "Teste" --corpo "Corpo do email"
```

**O que faz:**
- Envia email de teste usando Gmail API
- Valida se as permissões de envio estão funcionando
- Retorna ID da mensagem enviada

**Importante:**
- Requer `GMAIL_DELEGATE_USER` configurado para enviar em nome de um usuário
- Sem delegação, o email será enviado da conta de serviço

---

### 5. `test_processar_email_mais_recente.py`
Processa o email não lido mais recente seguindo o fluxo completo do monitoramento.

**O que faz:**
- Busca o email não lido mais recente
- Valida o remetente (domínio e emails bloqueados)
- Extrai o corpo do email
- Processa anexos e salva no Google Drive
- Busca telefone no diretório do Google Workspace
- Chama a API para abrir chamado UISA
- Processa a resposta e envia email de confirmação
- Marca o email como processado

**Uso:**
```bash
python tests/gmail_monitor/test_processar_email_mais_recente.py
```

**Este é um teste de integração completo** que simula exatamente o que o `GmailMonitorService` faz, mas apenas para um email específico.

---

### 7. `test_listar_contatos_people.py`
Lista contatos do diretório do Google Workspace via People API.

**⚠️ IMPORTANTE:** 
- A query é obrigatória para este teste
- Requer `GMAIL_DELEGATE_USER` configurado (delegação de domínio obrigatória)

**Uso:**
```bash
# Buscar por email (obrigatório)
python tests/gmail_monitor/test_listar_contatos_people.py --query "usuario@uisa.com.br"

# Buscar por nome
python tests/gmail_monitor/test_listar_contatos_people.py --query "nome sobrenome"

# Limitar número de resultados
python tests/gmail_monitor/test_listar_contatos_people.py --query "usuario@uisa.com.br" --max 20

# Forma abreviada
python tests/gmail_monitor/test_listar_contatos_people.py -q "silva" -m 10
```

**O que faz:**
- Busca contatos no diretório do Google Workspace
- Exibe nome, email, telefone e organização
- Permite busca por termo específico
- Mostra estatísticas dos contatos encontrados

---

## Pré-requisitos

Antes de executar os testes, certifique-se de que:

1. ✅ As variáveis de ambiente estão configuradas no `.env`
2. ✅ As APIs estão habilitadas no Google Cloud Console:
   - Gmail API
   - Google Drive API
   - People API
3. ✅ A delegação de domínio está configurada (para Gmail e People)
4. ✅ A pasta do Drive está compartilhada com a conta de serviço

## Executando Todos os Testes

### Opção 1: Script Automático (Recomendado)

Execute todos os testes automaticamente:

```bash
# Windows (PowerShell)
python tests/gmail_monitor/run_all_tests.py

# Linux/Mac
python3 tests/gmail_monitor/run_all_tests.py
```

Este script executa todos os testes em sequência e exibe um resumo ao final.

### Opção 2: Execução Manual

Para executar cada teste individualmente:

```bash
# Windows (PowerShell)
python tests/gmail_monitor/test_checar_permissoes.py
python tests/gmail_monitor/test_listar_emails_nao_lidos.py
python tests/gmail_monitor/test_listar_emails_processados.py
python tests/gmail_monitor/test_listar_contatos_people.py

# Linux/Mac
python3 tests/gmail_monitor/test_checar_permissoes.py
python3 tests/gmail_monitor/test_listar_emails_nao_lidos.py
python3 tests/gmail_monitor/test_listar_emails_processados.py
python3 tests/gmail_monitor/test_listar_contatos_people.py
```

## Troubleshooting

### Erro: "Permission denied" ou "403"
- Verifique se a delegação de domínio está configurada
- Verifique se os escopos OAuth estão corretos
- Verifique se `GMAIL_DELEGATE_USER` está configurado

### Erro: "API not enabled"
- Habilite as APIs necessárias no Google Cloud Console
- Aguarde alguns minutos após habilitar

### Erro: "Folder not found" (Drive)
- Verifique se `FOLDER_ID_DRIVE` está correto
- Compartilhe a pasta com o email da conta de serviço

### Erro: "No contacts found" ou "Must be a G Suite domain user" (People)
- **OBRIGATÓRIO:** Configure `GMAIL_DELEGATE_USER` no arquivo `.env` com um email do Google Workspace
- Verifique se a API People está habilitada
- Verifique se a delegação de domínio está configurada no Google Workspace Admin
- A People API requer delegação de domínio para funcionar
- Tente buscar por um termo específico (email ou nome)

## Estrutura dos Testes

Todos os testes seguem o mesmo padrão:
1. Importam as configurações do projeto
2. Criam os serviços necessários (Gmail, Drive, People)
3. Executam as operações de teste
4. Exibem resultados formatados
5. Tratam erros com mensagens claras

## Logs

Os testes utilizam o mesmo sistema de logs do projeto. Os logs são salvos em:
- `logs/api_fluig.log`

Para ver logs em tempo real durante os testes, monitore o arquivo de log.
