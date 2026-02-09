"""
Módulo para envio de emails via Gmail API
"""
from typing import Optional
from email.mime.text import MIMEText
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def enviar_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """
    Envia um email usando Gmail API
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo: Corpo do email (texto plano)
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        service = criar_servico_gmail()
        if not service:
            logger.error("[email_sender] Falha ao criar serviço Gmail")
            return False
        
        # Cria mensagem
        message = MIMEText(corpo)
        message['to'] = destinatario
        message['subject'] = assunto
        
        # Codifica em base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Envia email
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        logger.info(f"[email_sender] Email enviado para: {destinatario} | ID: {send_message.get('id')}")
        return True
        
    except HttpError as e:
        logger.error(f"[email_sender] Erro HTTP ao enviar email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"[email_sender] Erro ao enviar email: {str(e)}")
        import traceback
        logger.debug(f"[email_sender] Traceback: {traceback.format_exc()}")
        return False


def criar_servico_gmail():
    """
    Cria serviço do Gmail API usando conta de serviço com delegação de domínio
    """
    try:
        logger.debug("[email_sender] Criando serviço Gmail API...")
        
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
        
        # Se houver um usuário configurado para delegação, usa ele
        # Caso contrário, usa a conta de serviço diretamente
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
        
        service = build('gmail', 'v1', credentials=credentials)
        logger.debug("[email_sender] Serviço Gmail API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[email_sender] Erro ao criar serviço Gmail API: {str(e)}")
        import traceback
        logger.debug(f"[email_sender] Traceback: {traceback.format_exc()}")
        return None
