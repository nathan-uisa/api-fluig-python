"""
Módulo para busca de telefone no diretório do Google (People API)
"""
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def buscar_telefone_no_diretorio(email_remetente: str) -> str:
    """
    Busca o telefone do contato no diretório do Google Workspace
    
    Args:
        email_remetente: Email do remetente
        
    Returns:
        Telefone encontrado ou string vazia
    """
    try:
        service = criar_servico_people()
        if not service:
            logger.warning("[people_service] Não foi possível criar serviço People API")
            return ""
        
        # Busca pessoa no diretório
        results = service.people().searchDirectoryPeople(
            query=email_remetente,
            readMask="phoneNumbers,emailAddresses",
            sources=["DIRECTORY_SOURCE_TYPE_DOMAIN_CONTACT", "DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"]
        ).execute()
        
        people = results.get('people', [])
        
        if people and len(people) > 0:
            person = people[0]
            
            # Verifica se o email bate
            email_addresses = person.get('emailAddresses', [])
            email_bate = any(e.get('value') == email_remetente for e in email_addresses)
            
            if email_bate:
                phone_numbers = person.get('phoneNumbers', [])
                if phone_numbers and len(phone_numbers) > 0:
                    telefone = phone_numbers[0].get('value', '')
                    logger.info(f"[people_service] Telefone encontrado para {email_remetente}: {telefone}")
                    return telefone
        
        logger.debug(f"[people_service] Telefone não encontrado para {email_remetente}")
        return ""
        
    except Exception as e:
        logger.warning(f"[people_service] Aviso: Não foi possível obter telefone (People API): {str(e)}")
        return ""


def criar_servico_people():
    """
    Cria serviço do People API usando conta de serviço
    """
    try:
        logger.debug("[people_service] Criando serviço People API...")
        
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
            scopes=['https://www.googleapis.com/auth/directory.readonly']
        )
        
        # People API requer delegação de domínio (deve usar um usuário do Google Workspace)
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
            logger.debug(f"[people_service] Usando delegação para: {ConfigEnvSetings.GMAIL_DELEGATE_USER}")
        
        service = build('people', 'v1', credentials=credentials)
        logger.debug("[people_service] Serviço People API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[people_service] Erro ao criar serviço People API: {str(e)}")
        import traceback
        logger.debug(f"[people_service] Traceback: {traceback.format_exc()}")
        return None
