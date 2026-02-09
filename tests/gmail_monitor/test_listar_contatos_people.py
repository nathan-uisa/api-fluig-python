"""
Script de teste para listar contatos do People API (Google Workspace Directory)
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


def criar_servico_people():
    """Cria serviço do People API"""
    try:
        logger.info("[test] Criando serviço People API...")
        
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
            logger.info(f"[test] Usando delegação para: {ConfigEnvSetings.GMAIL_DELEGATE_USER}")
        else:
            logger.warning("[test] GMAIL_DELEGATE_USER nao configurado. People API requer delegação de domínio.")
            print("  AVISO: GMAIL_DELEGATE_USER nao está configurado.")
            print("   A People API requer delegação de domínio para funcionar.")
            print("   Configure GMAIL_DELEGATE_USER no arquivo .env")
        
        service = build('people', 'v1', credentials=credentials)
        logger.info("[test] Serviço People API criado com sucesso")
        return service
        
    except Exception as e:
        logger.error(f"[test] Erro ao criar serviço People API: {str(e)}")
        import traceback
        logger.debug(f"[test] Traceback: {traceback.format_exc()}")
        return None


def listar_contatos(query: str = None, max_results: int = 50):
    """Lista contatos do diretório do Google Workspace"""
    try:
        service = criar_servico_people()
        if not service:
            print(" Erro: Nao foi possível criar serviço People API")
            return
        
        print("\n" + "="*80)
        print(" LISTANDO CONTATOS DO PEOPLE API (Google Workspace Directory)")
        print("="*80 + "\n")
        
        # A API People requer uma query obrigatória
        if not query:
            print("  A API People requer uma query obrigatória.")
            print("   Use --query ou -q para especificar um termo de busca.")
            print("\n   Exemplos:")
            print("   python test_listar_contatos_people.py --query usuario@uisa.com.br")
            print("   python test_listar_contatos_people.py --query 'nome'")
            print("   python test_listar_contatos_people.py -q 'silva'")
            return
        
        print(f" Buscando por: '{query}'")
        print(f" Limite de resultados: {max_results}\n")
        
        # Busca no diretório
        options = {
            'query': query,  # Query é obrigatória
            'readMask': 'names,emailAddresses,phoneNumbers,organizations',
            'sources': [
                'DIRECTORY_SOURCE_TYPE_DOMAIN_CONTACT',
                'DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE'
            ],
            'pageSize': max_results
        }
        
        results = service.people().searchDirectoryPeople(**options).execute()
        
        people = results.get('people', [])
        total = len(people)
        
        print(f"Total de contatos encontrados: {total}\n")
        
        if total == 0:
            print(" Nenhum contato encontrado para a query especificada.")
            print("    Tente usar um termo diferente ou mais específico.")
            return
        
        # Processa cada contato
        for idx, person in enumerate(people, 1):
            print(f"\n[{idx}/{total}] Contato ID: {person.get('resourceName', 'N/A')}")
            
            # Nome
            names = person.get('names', [])
            if names:
                nome = names[0].get('displayName', 'N/A')
                nome_completo = names[0].get('fullName', 'N/A')
                print(f"   Nome: {nome}")
                if nome_completo != nome:
                    print(f"     Nome completo: {nome_completo}")
            
            # Emails
            emails = person.get('emailAddresses', [])
            if emails:
                print(f"   Email(s):")
                for email in emails:
                    email_value = email.get('value', 'N/A')
                    email_type = email.get('type', 'N/A')
                    print(f"     - {email_value} ({email_type})")
            
            # Telefones
            phones = person.get('phoneNumbers', [])
            if phones:
                print(f"   Telefone(s):")
                for phone in phones:
                    phone_value = phone.get('value', 'N/A')
                    phone_type = phone.get('type', 'N/A')
                    print(f"     - {phone_value} ({phone_type})")
            else:
                print(f"   Telefone: N/A")
            
            # Organização
            organizations = person.get('organizations', [])
            if organizations:
                org = organizations[0]
                org_name = org.get('name', 'N/A')
                org_title = org.get('title', 'N/A')
                print(f"   Organização: {org_name}")
                if org_title:
                    print(f"     Cargo: {org_title}")
            
            print("-" * 80)
        
        print(f"\n Processamento concluído. Total: {total} contato(s)")
        
        # Estatísticas
        total_com_telefone = sum(1 for p in people if p.get('phoneNumbers'))
        total_com_email = sum(1 for p in people if p.get('emailAddresses'))
        
        print(f"\n Estatísticas:")
        print(f"   Contatos com telefone: {total_com_telefone}/{total}")
        print(f"   Contatos com email: {total_com_email}/{total}")
        
    except HttpError as e:
        print(f" Erro HTTP: {str(e)}")
        if e.resp.status == 403:
            print("     Permissão negada (403). Verifique:")
            print("      - Se a API People está habilitada no Google Cloud Console")
            print("      - Se o escopo 'directory.readonly' está configurado")
            print("      - Se a delegação de domínio está configurada no Google Workspace Admin")
        elif e.resp.status == 400:
            error_message = str(e)
            if "Must be a G Suite domain user" in error_message or "G Suite domain user" in error_message:
                print("     Requisição inválida (400): 'Must be a G Suite domain user'")
                print("      A People API requer delegação de domínio.")
                print("      Configure GMAIL_DELEGATE_USER no arquivo .env com um email do Google Workspace.")
                print("      Exemplo: GMAIL_DELEGATE_USER=usuario@uisa.com.br")
            else:
                print("     Requisição inválida (400).")
                print("      A API People requer uma query válida.")
                print("      Verifique se a query foi fornecida e está no formato correto.")
    except Exception as e:
        print(f" Erro: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Lista contatos do People API',
        epilog='Exemplos:\n'
               '  python test_listar_contatos_people.py --query usuario@uisa.com.br\n'
               '  python test_listar_contatos_people.py -q "nome sobrenome"\n'
               '  python test_listar_contatos_people.py --query silva --max 20',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--query', '-q',
        required=True,
        help='Termo de busca obrigatório (email, nome, etc.)'
    )
    parser.add_argument(
        '--max', '-m',
        type=int,
        default=50,
        help='Número máximo de resultados (padrão: 50)'
    )
    
    args = parser.parse_args()
    
    print("\n Iniciando teste de listagem de contatos...\n")
    listar_contatos(query=args.query, max_results=args.max)
    print("\n Teste finalizado!\n")
