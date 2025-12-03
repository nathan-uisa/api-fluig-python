"""
Módulo para autenticação no Google Drive usando conta de serviço
"""
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def criar_servico_drive() -> Optional[object]:
    """
    Cria serviço do Google Drive usando conta de serviço
    
    Returns:
        Serviço do Google Drive ou None em caso de erro
    """
    try:
        logger.info("[auth_google_drive] Criando serviço do Google Drive...")
        
        # Monta credenciais da conta de serviço
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
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        logger.info("[auth_google_drive] Serviço do Google Drive criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[auth_google_drive] Erro ao criar serviço do Google Drive: {str(e)}")
        import traceback
        logger.debug(f"[auth_google_drive] Traceback: {traceback.format_exc()}")
        return None

