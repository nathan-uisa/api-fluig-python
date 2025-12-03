"""
Módulo para integração com Google Drive usando conta de serviço
"""
import io
from typing import Tuple, Optional
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from src.auth.auth_google_drive import criar_servico_drive
from src.utilitarios_centrais.logger import logger


def baixar_arquivo_drive(file_id: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Baixa um arquivo do Google Drive usando conta de serviço
    
    Args:
        file_id: ID do arquivo no Google Drive
        
    Returns:
        Tupla (conteudo_bytes, nome_arquivo) ou (None, None) em caso de erro
    """
    try:
        logger.info(f"[google_drive_utils] Iniciando download do arquivo {file_id} do Google Drive...")
        
        service = criar_servico_drive()
        if not service:
            logger.error("[google_drive_utils] Falha ao criar serviço do Google Drive")
            return (None, None)
        
        # Obtém metadados do arquivo
        file_metadata = service.files().get(fileId=file_id, fields='name, mimeType').execute()
        nome_arquivo = file_metadata.get('name', 'arquivo_sem_nome')
        logger.info(f"[google_drive_utils] Arquivo encontrado: {nome_arquivo}")
        
        # Baixa o arquivo
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"[google_drive_utils] Progresso: {int(status.progress() * 100)}%")
        
        conteudo_bytes = file_content.getvalue()
        logger.info(f"[google_drive_utils] Arquivo {nome_arquivo} baixado com sucesso ({len(conteudo_bytes)} bytes)")
        
        return (conteudo_bytes, nome_arquivo)
        
    except HttpError as e:
        logger.error(f"[google_drive_utils] Erro HTTP ao baixar arquivo {file_id}: {str(e)}")
        return (None, None)
    except Exception as e:
        logger.error(f"[google_drive_utils] Erro ao baixar arquivo {file_id}: {str(e)}")
        import traceback
        logger.debug(f"[google_drive_utils] Traceback: {traceback.format_exc()}")
        return (None, None)

