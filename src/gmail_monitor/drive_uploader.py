"""
Módulo para upload de anexos no Google Drive
"""
import io
from typing import Optional, List
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from src.auth.auth_google_drive import criar_servico_drive
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def salvar_anexo_no_drive(conteudo_bytes: bytes, nome_arquivo: str, folder_id: Optional[str] = None) -> Optional[str]:
    """
    Salva um anexo no Google Drive e retorna o ID do arquivo
    
    Args:
        conteudo_bytes: Conteúdo do arquivo em bytes
        nome_arquivo: Nome do arquivo
        folder_id: ID da pasta no Drive (usa FOLDER_ID_DRIVE se não fornecido)
        
    Returns:
        ID do arquivo no Drive ou None em caso de erro
    """
    try:
        if not folder_id:
            folder_id = ConfigEnvSetings.FOLDER_ID_DRIVE
        
        logger.info(f"[drive_uploader] Salvando arquivo {nome_arquivo} no Drive (pasta: {folder_id})...")
        
        # Cria serviço do Drive com escopo de escrita
        service = criar_servico_drive_write()
        if not service:
            logger.error("[drive_uploader] Falha ao criar serviço do Google Drive")
            return None
        
        # Cria o arquivo na pasta especificada
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(conteudo_bytes),
            mimetype='application/octet-stream',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        logger.info(f"[drive_uploader] Arquivo salvo: {nome_arquivo} | ID: {file_id}")
        
        return file_id
        
    except HttpError as e:
        logger.error(f"[drive_uploader] Erro HTTP ao salvar arquivo {nome_arquivo}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[drive_uploader] ERRO CRÍTICO ao salvar anexo {nome_arquivo}: {str(e)}")
        import traceback
        logger.debug(f"[drive_uploader] Traceback: {traceback.format_exc()}")
        return None


def criar_servico_drive_write():
    """
    Cria serviço do Google Drive com permissão de escrita
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from src.modelo_dados.modelo_settings import ConfigEnvSetings
    
    try:
        logger.info("[drive_uploader] Criando serviço do Google Drive (escopo de escrita)...")
        
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
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        logger.info("[drive_uploader] Serviço do Google Drive criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[drive_uploader] Erro ao criar serviço do Google Drive: {str(e)}")
        import traceback
        logger.debug(f"[drive_uploader] Traceback: {traceback.format_exc()}")
        return None
