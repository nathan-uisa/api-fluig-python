"""
Script de teste para listar emails não lidos do Gmail
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


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


def listar_emails_nao_lidos():
    """Lista emails não lidos"""
    try:
        service = criar_servico_gmail()
        if not service:
            print("Erro: Nao foi possivel criar servico Gmail")
            return
        
        print("\n" + "="*80)
        print("LISTANDO EMAILS NAO LIDOS")
        print("="*80 + "\n")
        
        # Busca threads não lidas
        query = 'is:unread'
        threads = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()
        
        thread_list = threads.get('threads', [])
        total = len(thread_list)
        
        print(f"Total de threads não lidas encontradas: {total}\n")
        
        if total == 0:
            print("Nenhum email nao lido encontrado.")
            return
        
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
                
                # Obtém detalhes da mensagem
                message_detail = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Extrai informações
                headers = message_detail['payload'].get('headers', [])
                email_from = next((h['value'] for h in headers if h['name'] == 'From'), 'N/A')
                email_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
                email_date = next((h['value'] for h in headers if h['name'] == 'Date'), 'N/A')
                
                # Verifica labels
                labels = message_detail.get('labelIds', [])
                tem_label_processados = 'Label_1' in labels or any('PROCESSADOS' in str(l) for l in labels)
                
                print(f"\n[{idx}/{total}] Thread ID: {thread_id}")
                print(f"  De: {email_from}")
                print(f"  Assunto: {email_subject}")
                print(f"  Data: {email_date}")
                print(f"  Labels: {', '.join(labels[:5])}")
                print(f"  Processado: {'SIM' if tem_label_processados else 'NAO'}")
                print("-" * 80)
                
            except Exception as e:
                print(f"  Erro ao processar thread {thread_id}: {str(e)}")
                continue
        
        print(f"\nProcessamento concluido. Total: {total} thread(s)")
        
    except HttpError as e:
        print(f"Erro HTTP: {str(e)}")
        if e.resp.status == 403:
            print("   AVISO: Verifique as permissoes da conta de servico")
    except Exception as e:
        print(f"Erro: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\nIniciando teste de listagem de emails nao lidos...\n")
    listar_emails_nao_lidos()
    print("\nTeste finalizado!\n")
