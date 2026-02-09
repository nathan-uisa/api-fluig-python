"""
Script de teste para checar permissões do usuário de serviço
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
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.send'
            ]
        )
        
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
        
        service = build('gmail', 'v1', credentials=credentials)
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço Gmail API: {str(e)}")
        return None


def criar_servico_drive():
    """Cria serviço do Google Drive API"""
    try:
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
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        
        service = build('drive', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço Drive API: {str(e)}")
        return None


def criar_servico_people():
    """Cria serviço do People API"""
    try:
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
        
        # People API requer delegação de domínio
        if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
            credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
        
        service = build('people', 'v1', credentials=credentials)
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço People API: {str(e)}")
        return None


def testar_gmail(service):
    """Testa permissões do Gmail"""
    print("\nTestando Gmail API...")
    try:
        # Tenta obter perfil do usuário
        profile = service.users().getProfile(userId='me').execute()
        print(f"  Acesso ao Gmail: OK")
        print(f"     Email: {profile.get('emailAddress', 'N/A')}")
        print(f"     Total de mensagens: {profile.get('messagesTotal', 'N/A')}")
        print(f"     Total de threads: {profile.get('threadsTotal', 'N/A')}")
        
        # Tenta listar labels
        labels = service.users().labels().list(userId='me').execute()
        print(f"  Listar labels: OK ({len(labels.get('labels', []))} labels encontradas)")
        
        # Tenta buscar emails
        threads = service.users().threads().list(userId='me', maxResults=1).execute()
        print(f"  Buscar emails: OK")
        
        return True
        
    except HttpError as e:
        print(f"  Erro: {str(e)}")
        if e.resp.status == 403:
            print(f"     Permissao negada (403). Verifique:")
            print(f"        - Se a delegação de domínio está configurada")
            print(f"        - Se os escopos OAuth estão corretos")
            print(f"        - Se GMAIL_DELEGATE_USER está configurado corretamente")
        return False
    except Exception as e:
        print(f"  Erro: {str(e)}")
        return False


def testar_drive(service):
    """Testa permissões do Google Drive"""
    print("\nTestando Google Drive API...")
    try:
        # Tenta listar arquivos
        files = service.files().list(pageSize=1).execute()
        print(f"  Acesso ao Drive: OK")
        
        # Testa acesso à pasta configurada
        folder_id = ConfigEnvSetings.FOLDER_ID_DRIVE
        if folder_id:
            try:
                folder = service.files().get(fileId=folder_id).execute()
                print(f"  Acesso à pasta configurada: OK")
                print(f"     Nome da pasta: {folder.get('name', 'N/A')}")
            except HttpError as e:
                if e.resp.status == 404:
                    print(f"  Pasta não encontrada (ID: {folder_id})")
                elif e.resp.status == 403:
                    print(f"  Sem permissão para acessar a pasta (ID: {folder_id})")
                    print(f"     Compartilhe a pasta com: {ConfigEnvSetings.CLIENT_EMAIL}")
                else:
                    print(f"  Erro ao acessar pasta: {str(e)}")
        
        return True
        
    except HttpError as e:
        print(f"  Erro: {str(e)}")
        if e.resp.status == 403:
            print(f"     Permissao negada (403). Verifique os escopos OAuth")
        return False
    except Exception as e:
        print(f"  Erro: {str(e)}")
        return False


def testar_people(service):
    """Testa permissões do People API"""
    print("\nTestando People API...")
    try:
        # Tenta buscar no diretório
        results = service.people().searchDirectoryPeople(
            query="test",
            readMask="emailAddresses",
            sources=["DIRECTORY_SOURCE_TYPE_DOMAIN_CONTACT"]
        ).execute()
        
        print(f"  Acesso ao People API: OK")
        print(f"     Resultados de teste: {len(results.get('people', []))} contato(s)")
        
        return True
        
    except HttpError as e:
        print(f"  Erro: {str(e)}")
        if e.resp.status == 403:
            print(f"     Permissao negada (403). Verifique:")
            print(f"        - Se a API People está habilitada")
            print(f"        - Se os escopos OAuth estão corretos")
            print(f"        - Se a delegação de domínio está configurada")
        elif e.resp.status == 400:
            error_message = str(e)
            if "Must be a G Suite domain user" in error_message or "G Suite domain user" in error_message:
                print(f"     Requisicao invalida (400): 'Must be a G Suite domain user'")
                print(f"        A People API requer delegação de domínio.")
                print(f"        Configure GMAIL_DELEGATE_USER no arquivo .env")
        return False
    except Exception as e:
        print(f"  Erro: {str(e)}")
        return False


def checar_permissoes():
    """Checa todas as permissões"""
    print("\n" + "="*80)
    print("VERIFICANDO PERMISSOES DO USUARIO DE SERVICO")
    print("="*80)
    
    print(f"\nInformacoes da Conta de Servico:")
    print(f"   Email: {ConfigEnvSetings.CLIENT_EMAIL}")
    print(f"   Project ID: {ConfigEnvSetings.PROJECT_ID}")
    
    if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
        print(f"   Delegacao para: {ConfigEnvSetings.GMAIL_DELEGATE_USER}")
    else:
        print(f"   AVISO: GMAIL_DELEGATE_USER nao configurado")
    
    # Testa Gmail
    gmail_service = criar_servico_gmail()
    gmail_ok = testar_gmail(gmail_service) if gmail_service else False
    
    # Testa Drive
    drive_service = criar_servico_drive()
    drive_ok = testar_drive(drive_service) if drive_service else False
    
    # Testa People
    people_service = criar_servico_people()
    people_ok = testar_people(people_service) if people_service else False
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DAS PERMISSOES")
    print("="*80)
    print(f"  Gmail API:     {'OK' if gmail_ok else 'FALHOU'}")
    print(f"  Drive API:     {'OK' if drive_ok else 'FALHOU'}")
    print(f"  People API:    {'OK' if people_ok else 'FALHOU'}")
    
    if gmail_ok and drive_ok and people_ok:
        print("\nTodas as permissoes estao OK!")
    else:
        print("\nAlgumas permissoes falharam. Verifique a configuracao.")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\nIniciando verificacao de permissoes...\n")
    checar_permissoes()
    print("\nVerificacao finalizada!\n")
