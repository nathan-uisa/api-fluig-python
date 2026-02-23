"""
Script de teste para verificar padrões de deduplicação de emails
Testa se os emails contêm os padrões configurados sem processar nada
"""
import sys
import os
import base64
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger

# Importações diretas para evitar dependências circulares
# Carrega EmailDeduplicator diretamente sem passar pelo __init__.py
spec_deduplicator = importlib.util.spec_from_file_location(
    "email_deduplicator",
    root_dir / "src" / "gmail_monitor" / "email_deduplicator.py"
)
email_deduplicator_module = importlib.util.module_from_spec(spec_deduplicator)
spec_deduplicator.loader.exec_module(email_deduplicator_module)
EmailDeduplicator = email_deduplicator_module.EmailDeduplicator

# Importa extrair_email_remetente diretamente
spec_validator = importlib.util.spec_from_file_location(
    "email_validator",
    root_dir / "src" / "gmail_monitor" / "email_validator.py"
)
email_validator_module = importlib.util.module_from_spec(spec_validator)
spec_validator.loader.exec_module(email_validator_module)
extrair_email_remetente = email_validator_module.extrair_email_remetente


def criar_servico_gmail():
    """Cria serviço do Gmail API"""
    try:
        logger.info("[test] Criando serviço Gmail API...")
        
        credenciais_info = {
            "type": ConfigEnvSetings.TYPE,
            "project_id": ConfigEnvSetings.PROJECT_ID,
            "private_key_id": ConfigEnvSetings.PRIVCATE_JEY_ID,
            "private_key": ConfigEnvSetings.PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": ConfigEnvSetings.CLIENT_EMAIL,
            "client_id": ConfigEnvSetings.CLIENT_ID,
            "auth_uri": ConfigEnvSetings.AUTH_URI,
            "token_uri": ConfigEnvSetings.TOKEN_URI,
            "auth_provider_x509_cert_url": ConfigEnvSetings.AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": ConfigEnvSetings.CLIENT_X509_CERT_URL,
            "universe_domain": ConfigEnvSetings.UNIVERSE_DOMAIN
        }
        
        credentials = service_account.Credentials.from_service_account_info(
            credenciais_info,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        
        # Se houver usuário configurado para delegação, usa ele
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
            logger.info(f"[test] Usando delegação para: {ConfigEnvSetings.GMAIL_DELEGATE_USER}")
        
        service = build('gmail', 'v1', credentials=credentials)
        logger.info("[test] Serviço Gmail API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço Gmail API: {str(e)}")
        import traceback
        logger.debug(f"[test] Traceback: {traceback.format_exc()}")
        return None


def extrair_corpo_email(message_detail: Dict[str, Any]) -> str:
    """
    Extrai o corpo do email da mensagem (texto plano preferencialmente)
    """
    try:
        payload = message_detail.get('payload', {})
        body_plain = ''
        body_html = ''
        
        def processar_parts(parts: List[Dict]):
            """Processa parts recursivamente"""
            nonlocal body_plain, body_html
            
            for part in parts:
                mime_type = part.get('mimeType', '')
                
                # Se tem parts aninhadas, processa recursivamente
                if 'parts' in part:
                    processar_parts(part['parts'])
                    continue
                
                # Tenta obter texto plano
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data and not body_plain:
                        body_plain = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                
                # Tenta obter HTML como fallback
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data')
                    if data and not body_html:
                        body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Processa parts se existirem
        if 'parts' in payload:
            processar_parts(payload['parts'])
        else:
            # Email simples sem partes
            mime_type = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data')
            if data:
                if mime_type == 'text/plain':
                    body_plain = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html':
                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Retorna texto plano se disponível, senão HTML
        return body_plain if body_plain else body_html
        
    except Exception as e:
        logger.debug(f"[test] Erro ao extrair corpo do email: {str(e)}")
        return ''


def testar_padroes_deduplicacao():
    """Testa padrões de deduplicação nos emails"""
    try:
        service = criar_servico_gmail()
        if not service:
            print("Erro: Não foi possível criar serviço Gmail")
            return
        
        print("\n" + "="*80)
        print("TESTE DE PADRÕES DE DEDUPLICAÇÃO DE EMAILS")
        print("="*80 + "\n")
        
        # Carrega configurações de deduplicação
        print("Carregando configurações de deduplicação do Drive...")
        deduplicator = EmailDeduplicator()
        
        print(f"\nPadrões configurados: {len(deduplicator.padroes_config) if deduplicator.padroes_config else 0}")
        if deduplicator.padroes_config:
            for idx, padrao in enumerate(deduplicator.padroes_config, 1):
                print(f"  {idx}. {padrao}")
        else:
            print("  Nenhum padrão configurado")
        
        print(f"\nEmails configurados para deduplicação: {len(deduplicator.emails_deduplicacao) if deduplicator.emails_deduplicacao else 0}")
        if deduplicator.emails_deduplicacao:
            for idx, email in enumerate(deduplicator.emails_deduplicacao, 1):
                print(f"  {idx}. {email}")
        else:
            print("  Nenhum email específico configurado (todos serão verificados)")
        
        if not deduplicator.padroes_config:
            print("\n⚠️  AVISO: Nenhum padrão de deduplicação configurado!")
            print("   Configure os padrões na página de configurações antes de executar este teste.")
            return
        
        print("\n" + "-"*80)
        print("Buscando os 20 primeiros emails não lidos...")
        print("-"*80 + "\n")
        
        # Busca threads não lidas
        query = 'is:unread'
        threads = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=20
        ).execute()
        
        thread_list = threads.get('threads', [])
        total = len(thread_list)
        
        print(f"Total de threads não lidas encontradas: {total}\n")
        
        if total == 0:
            print("Nenhum email não lido encontrado.")
            return
        
        # Estatísticas
        emails_com_padrao = 0
        emails_sem_padrao = 0
        emails_fora_lista = 0
        
        # Processa cada thread
        for idx, thread_item in enumerate(thread_list, 1):
            thread_id = thread_item['id']
            
            try:
                # Obtém detalhes da thread
                thread = service.users().threads().get(
                    userId='me',
                    id=thread_id
                ).execute()
                
                # Pega a primeira mensagem
                messages = thread.get('messages', [])
                if not messages:
                    continue
                
                message = messages[0]
                message_id = message['id']
                
                # Obtém detalhes completos da mensagem
                message_detail = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                
                # Extrai informações
                headers = message_detail['payload'].get('headers', [])
                email_from = next((h['value'] for h in headers if h['name'] == 'From'), 'N/A')
                email_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
                email_date = next((h['value'] for h in headers if h['name'] == 'Date'), 'N/A')
                email_remetente = extrair_email_remetente(email_from)
                
                # Extrai corpo do email
                email_body = extrair_corpo_email(message_detail)
                
                print(f"\n[{idx}/{total}] Thread ID: {thread_id}")
                print(f"  De: {email_from}")
                print(f"  Remetente: {email_remetente}")
                print(f"  Assunto: {email_subject[:80]}{'...' if len(email_subject) > 80 else ''}")
                print(f"  Data: {email_date}")
                
                # Verifica se o email está na lista de deduplicação
                if deduplicator.emails_deduplicacao:
                    email_remetente_lower = email_remetente.lower().strip()
                    if email_remetente_lower not in deduplicator.emails_deduplicacao:
                        print(f"  ⚠️  Email NÃO está na lista de deduplicação - não será verificado")
                        emails_fora_lista += 1
                        print("-" * 80)
                        continue
                
                # Extrai identificador usando os padrões
                identificador, padrao_usado = deduplicator.extrair_identificador(email_subject, email_body)
                
                if identificador:
                    print(f"  ✅ PADRÃO ENCONTRADO!")
                    print(f"     Padrão usado: {padrao_usado}")
                    print(f"     Identificador extraído: {identificador}")
                    
                    # Verifica se já foi processado
                    if identificador in deduplicator.identificadores_processados:
                        valor = deduplicator.identificadores_processados[identificador]
                        print(f"       Este identificador JÁ FOI PROCESSADO anteriormente")
                        if '|process_id:' in valor:
                            try:
                                process_id_str = valor.split('|process_id:')[1]
                                print(f"     Process Instance ID: {process_id_str}")
                            except:
                                pass
                    else:
                        print(f"      Este identificador NÃO foi processado ainda (seria um novo chamado)")
                    
                    emails_com_padrao += 1
                else:
                    print(f"   Nenhum padrão encontrado neste email")
                    emails_sem_padrao += 1
                
                # Mostra preview do corpo (primeiras 200 caracteres)
                if email_body:
                    preview = email_body[:200].replace('\n', ' ').replace('\r', ' ')
                    print(f"  Preview do corpo: {preview}...")
                
                print("-" * 80)
                
            except Exception as e:
                print(f"   Erro ao processar thread {thread_id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Resumo
        print("\n" + "="*80)
        print("RESUMO DO TESTE")
        print("="*80)
        print(f"Total de emails analisados: {total}")
        print(f"   Emails com padrão encontrado: {emails_com_padrao}")
        print(f"   Emails sem padrão: {emails_sem_padrao}")
        if deduplicator.emails_deduplicacao:
            print(f"    Emails fora da lista de deduplicação: {emails_fora_lista}")
        print("="*80 + "\n")
        
        if emails_com_padrao > 0:
            print("  Emails com padrão encontrado seriam verificados para duplicação")
            print("   e não abririam novo chamado se o identificador já foi processado.\n")
        
    except HttpError as e:
        print(f"Erro HTTP: {str(e)}")
        if e.resp.status == 403:
            print("   AVISO: Verifique as permissões da conta de serviço")
    except Exception as e:
        print(f"Erro: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nIniciando teste de padrões de deduplicação...\n")
    testar_padroes_deduplicacao()
    print("\nTeste finalizado!\n")
