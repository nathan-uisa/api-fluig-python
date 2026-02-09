"""
Script de teste para enviar email de teste
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from email.mime.text import MIMEText
import base64
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
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Se houver usuário configurado para delegação, usa ele
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
            logger.info(f"[test] Usando delegação para: {ConfigEnvSetings.GMAIL_DELEGATE_USER}")
        else:
            print("  GMAIL_DELEGATE_USER nao configurado. O email será enviado da conta de serviço.")
        
        service = build('gmail', 'v1', credentials=credentials)
        logger.info("[test] Serviço Gmail API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço Gmail API: {str(e)}")
        import traceback
        logger.debug(f"[test] Traceback: {traceback.format_exc()}")
        return None


def enviar_email_teste(destinatario: str, assunto: str = None, corpo: str = None):
    """Envia email de teste"""
    try:
        service = criar_servico_gmail()
        if not service:
            print(" Erro: Nao foi possível criar serviço Gmail")
            return False
        
        print("\n" + "="*80)
        print(" ENVIANDO EMAIL DE TESTE")
        print("="*80 + "\n")
        
        # Valida email
        if not destinatario or '@' not in destinatario:
            print(f" Email inválido: {destinatario}")
            return False
        
        # Define assunto e corpo padrão se nao fornecidos
        if not assunto:
            assunto = "Teste de Envio - Gmail Monitor"
        
        if not corpo:
            from datetime import datetime
            data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            corpo = f"""Este é um email de teste do sistema de monitoramento de emails.

Informações do teste:
- Conta de serviço: {ConfigEnvSetings.CLIENT_EMAIL}
- Destinatário: {destinatario}
- Data/Hora: {data_hora}

Se você recebeu este email, significa que:
 A configuração do Gmail API está funcionando
 As permissoes de envio estão corretas
 A delegação de domínio está configurada (se aplicável)

Este é apenas um teste. Você pode ignorar este email.
"""
        
        print(f" Destinatário: {destinatario}")
        print(f" Assunto: {assunto}")
        print(f" Corpo: {len(corpo)} caracteres")
        print("\n⏳ Enviando email...")
        
        # Cria mensagem
        message = MIMEText(corpo)
        message['to'] = destinatario
        message['subject'] = assunto
        
        # Se houver delegação, adiciona o email de origem
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            message['from'] = ConfigEnvSetings.GMAIL_DELEGATE_USER
        
        # Codifica em base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Envia email
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        message_id = send_message.get('id')
        
        print(f"\n Email enviado com sucesso!")
        print(f"   ID da mensagem: {message_id}")
        print(f"   Thread ID: {send_message.get('threadId', 'N/A')}")
        
        return True
        
    except HttpError as e:
        print(f"\n Erro HTTP: {str(e)}")
        if e.resp.status == 403:
            print("     Permissão negada (403). Verifique:")
            print("      - Se o escopo 'gmail.send' está habilitado")
            print("      - Se a delegação de domínio está configurada")
            print("      - Se GMAIL_DELEGATE_USER está configurado corretamente")
        elif e.resp.status == 400:
            print("     Requisição inválida (400). Verifique:")
            print("      - Se o email do destinatário está correto")
            print("      - Se o formato da mensagem está correto")
        return False
    except Exception as e:
        print(f"\n Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Envia email de teste')
    parser.add_argument('email', help='Email do destinatário')
    parser.add_argument('--assunto', '-s', help='Assunto do email (opcional)')
    parser.add_argument('--corpo', '-c', help='Corpo do email (opcional)')
    
    args = parser.parse_args()
    
    print("\n Iniciando teste de envio de email...\n")
    
    sucesso = enviar_email_teste(
        destinatario=args.email,
        assunto=args.assunto,
        corpo=args.corpo
    )
    
    if sucesso:
        print("\n Email enviado com sucesso!\n")
    else:
        print("\n Falha ao enviar email.\n")
        sys.exit(1)
