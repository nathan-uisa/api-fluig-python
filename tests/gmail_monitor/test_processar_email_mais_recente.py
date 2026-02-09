"""
Script de teste para processar o email mais recente e abrir chamado
Testa o fluxo completo do monitoramento de emails
"""
import sys
import os
import json
import base64
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
from src.modelo_dados.modelos_fluig import AberturaChamado
from src.fluig.fluig_core import FluigCore
from src.utilitarios_centrais.google_drive_utils import baixar_arquivo_drive
from src.gmail_monitor.email_validator import validar_email_uisa, extrair_email_remetente
from src.gmail_monitor.drive_uploader import salvar_anexo_no_drive
from src.gmail_monitor.people_service import buscar_telefone_no_diretorio
from src.gmail_monitor.email_sender import enviar_email


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
            scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
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


def obter_label_processados(service):
    """Obtém ou cria a label PROCESSADOS"""
    try:
        labels = service.users().labels().list(userId='me').execute()
        
        for label in labels.get('labels', []):
            if label['name'] == 'PROCESSADOS':
                return label['id']
        
        # Se nao encontrou, tenta criar
        label_obj = {
            'name': 'PROCESSADOS',
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        created_label = service.users().labels().create(
            userId='me',
            body=label_obj
        ).execute()
        
        return created_label['id']
        
    except Exception as e:
        logger.error(f"[test] Erro ao obter/criar label PROCESSADOS: {str(e)}")
        return None


def buscar_email_mais_recente(service):
    """Busca o email nao lido mais recente"""
    try:
        # Busca threads nao lidas (a API já retorna ordenadas por data, mais recente primeiro)
        query = 'is:unread'
        threads = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=10  # Busca mais threads para garantir que pegamos o mais recente
        ).execute()
        
        thread_list = threads.get('threads', [])
        
        if not thread_list:
            return None, None
        
        # Itera pelos threads para encontrar o primeiro nao processado
        # A API do Gmail já retorna ordenado por data (mais recente primeiro)
        label_processados_id = obter_label_processados(service)
        
        for thread_item in thread_list:
            temp_thread_id = thread_item['id']
            
            # Obtém detalhes da thread
            thread = service.users().threads().get(
                userId='me',
                id=temp_thread_id
            ).execute()
            
            # Verifica se já tem a label PROCESSADOS
            labels = thread.get('labelIds', [])
            if label_processados_id and label_processados_id in labels:
                continue  # Pula emails já processados
            
            # Pega a primeira mensagem da thread
            messages = thread.get('messages', [])
            if not messages:
                continue
            
            message_id = messages[0]['id']
            
            # Obtém detalhes completos da mensagem
            message_detail = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Retorna o primeiro thread nao processado encontrado (mais recente)
            return temp_thread_id, message_detail
        
        # Se chegou aqui, todos os threads já foram processados
        return None, None
        
    except Exception as e:
        logger.error(f"[test] Erro ao buscar email mais recente: {str(e)}")
        import traceback
        logger.debug(f"[test] Traceback: {traceback.format_exc()}")
        return None, None


def extrair_corpo_email(message_detail: Dict) -> str:
    """Extrai o corpo do email em texto plano"""
    try:
        payload = message_detail.get('payload', {})
        
        # Tenta obter texto plano
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Se nao encontrou em parts, tenta diretamente
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return ""
        
    except Exception as e:
        logger.error(f"[test] Erro ao extrair corpo do email: {str(e)}")
        return ""


def processar_anexos(service, message_detail: Dict) -> List[str]:
    """Processa anexos do email e salva no Drive"""
    anexos_ids = []
    
    try:
        payload = message_detail.get('payload', {})
        message_id = message_detail['id']
        
        def processar_parts(parts):
            for part in parts:
                filename = part.get('filename')
                if filename and part.get('body', {}).get('attachmentId'):
                    attachment_id = part['body']['attachmentId']
                    
                    # Baixa o anexo
                    attachment = service.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute()
                    
                    # Decodifica o conteúdo
                    file_data = base64.urlsafe_b64decode(attachment['data'])
                    
                    # Salva no Drive
                    file_id = salvar_anexo_no_drive(file_data, filename)
                    if file_id:
                        anexos_ids.append(file_id)
                        logger.info(f"[test] Anexo processado: {filename} (ID: {file_id})")
        
        if 'parts' in payload:
            processar_parts(payload['parts'])
        
        if anexos_ids:
            print(f"   {len(anexos_ids)} anexo(s) processado(s) e salvo(s) no Drive")
        else:
            print(f"   Nenhum anexo encontrado")
        
    except Exception as e:
        logger.error(f"[test] Erro ao processar anexos: {str(e)}")
    
    return anexos_ids


def chamar_api_chamado(assunto: str, corpo: str, email: str, anexos_ids: List[str]) -> Optional[str]:
    """Abre chamado usando funções internas do projeto"""
    try:
        ambiente = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_AMBIENTE', 'prd').upper()
        
        # Busca telefone
        telefone = buscar_telefone_no_diretorio(email)
        if telefone:
            print(f"   Telefone encontrado: {telefone}")
        else:
            print(f"   Telefone nao encontrado no diretório")
        
        # 1. Validar e baixar anexos do Google Drive (se houver)
        arquivos_baixados = []
        if anexos_ids and len(anexos_ids) > 0:
            print(f"   Baixando {len(anexos_ids)} anexo(s) do Google Drive...")
            for file_id in anexos_ids:
                try:
                    conteudo_bytes, nome_arquivo = baixar_arquivo_drive(file_id)
                    if conteudo_bytes and nome_arquivo:
                        arquivos_baixados.append({
                            'bytes': conteudo_bytes,
                            'nome': nome_arquivo,
                            'file_id': file_id
                        })
                        print(f"   Arquivo {file_id} baixado: {nome_arquivo}")
                    else:
                        print(f"   Falha ao baixar arquivo {file_id}")
                except Exception as e:
                    print(f"   Erro ao processar anexo {file_id}: {str(e)}")
        
        # 2. Abrir chamado UISA (normal)
        print(f"   Abrindo chamado UISA (normal)")
        fluig_core = FluigCore(ambiente=ambiente)
        process_instance_id = None
        
        item_uisa = AberturaChamado(
            titulo=assunto,
            descricao=corpo,
            usuario=email,
            telefone=telefone if telefone else None,
            anexos_ids=anexos_ids if anexos_ids else None
        )
        resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=item_uisa)
        
        if resposta and resposta.get('sucesso'):
            dados = resposta.get('dados', {})
            if dados and isinstance(dados, dict):
                process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
            
            if process_instance_id:
                print(f"   Chamado aberto com sucesso - ID: {process_instance_id}")
                
                # 3. Se houver anexos e chamado foi criado, anexar arquivos
                if arquivos_baixados and process_instance_id:
                    print(f"   Anexando {len(arquivos_baixados)} arquivo(s) ao chamado...")
                    
                    # Obtém colleague ID baseado no ambiente
                    if ambiente == "PRD":
                        colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID
                    else:  # QLD
                        colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                    
                    if not colleague_id or colleague_id == "":
                        print(f"   [AVISO] Colleague ID não configurado - não será possível anexar arquivos")
                    else:
                        for arquivo in arquivos_baixados:
                            try:
                                resultado_upload = fluig_core.upload_arquivo_fluig(
                                    arquivo_bytes=arquivo['bytes'],
                                    nome_arquivo=arquivo['nome'],
                                    colleague_id=colleague_id
                                )
                                
                                if resultado_upload:
                                    sucesso_anexo = fluig_core.anexar_arquivo_chamado(
                                        process_instance_id=process_instance_id,
                                        nome_arquivo=arquivo['nome']
                                    )
                                    if sucesso_anexo:
                                        print(f"   Arquivo {arquivo['nome']} anexado com sucesso")
                                    else:
                                        print(f"   Falha ao anexar arquivo {arquivo['nome']}")
                                else:
                                    print(f"   Falha no upload do arquivo {arquivo['nome']}")
                            except Exception as e:
                                print(f"   Erro ao processar anexo {arquivo['nome']}: {str(e)}")
                
                # Retorna o processInstanceId como string JSON
                return json.dumps(process_instance_id)
            else:
                print(f"   [ERRO] processInstanceId não encontrado na resposta")
                return None
        else:
            print(f"   [ERRO] Falha ao abrir chamado")
            if resposta:
                print(f"   Status: {resposta.get('status_code', 'N/A')}")
                print(f"   Mensagem: {resposta.get('texto', 'Erro desconhecido')}")
            return None
            
    except Exception as e:
        print(f"   [ERRO] Erro fatal ao abrir chamado: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def processar_resposta_chamado(resposta: Any, email_remetente: str, assunto_original: str) -> bool:
    """
    Processa a resposta da API e envia email de confirmação
    
    Returns:
        True se o chamado foi aberto com sucesso, False caso contrário
    """
    process_instance_id = None
    
    if isinstance(resposta, (int, float)):
        process_instance_id = int(resposta)
    elif isinstance(resposta, str):
        try:
            resposta_json = json.loads(resposta)
            if isinstance(resposta_json, dict):
                resposta = resposta_json
            else:
                process_instance_id = int(resposta_json)
        except (json.JSONDecodeError, ValueError):
            try:
                process_instance_id = int(resposta)
            except ValueError:
                pass
    elif isinstance(resposta, dict):
        if resposta.get('processInstanceId'):
            process_instance_id = resposta['processInstanceId']
        elif resposta.get('dados', {}).get('processInstanceId'):
            process_instance_id = resposta['dados']['processInstanceId']
        elif resposta.get('status') in ['rejeitado', 'erro']:
            print(f"    Chamado rejeitado: {resposta.get('mensagem', 'Erro genérico')}")
            enviar_email(
                email_remetente,
                "Chamado Nao Aprovado",
                f"O chamado nao pôde ser aberto.\nMotivo: {resposta.get('mensagem', 'Erro genérico')}"
            )
            return False
    
    if process_instance_id:
        link = f"https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID={process_instance_id}"
        print(f"   Chamado criado com sucesso!")
        print(f"     Número: {process_instance_id}")
        print(f"     Link: {link}")
        
        enviar_email(
            email_remetente,
            f"Chamado Aberto - #{process_instance_id}",
            f"Chamado criado com sucesso.\nNúmero: {process_instance_id}\nLink: {link}"
        )
        print(f"   Email de confirmação enviado para: {email_remetente}")
        return True
    else:
        print(f"   Erro: processInstanceId nao identificado na resposta.")
        print(f"     Resposta recebida: {resposta}")
        return False


def marcar_como_processado(service, thread_id: str):
    """Marca a thread como processada"""
    try:
        label_id = obter_label_processados(service)
        
        if label_id:
            service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={
                    'addLabelIds': [label_id],
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            print(f"   Email marcado como processado")
        else:
            # Se nao tem label, apenas marca como lido
            service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"   Email marcado como lido")
    except Exception as e:
        logger.error(f"[test] Erro ao marcar como processado: {str(e)}")


def processar_email_mais_recente():
    """Processa o email mais recente seguindo o fluxo completo"""
    try:
        service = criar_servico_gmail()
        if not service:
            print(" Erro: Nao foi possível criar serviço Gmail")
            return False
        
        print("\n" + "="*80)
        print(" PROCESSANDO EMAIL MAIS RECENTE - TESTE DE INTEGRAÇÃO")
        print("="*80 + "\n")
        
        # Busca email mais recente
        print(" Buscando email nao lido mais recente...")
        thread_id, message_detail = buscar_email_mais_recente(service)
        
        if not thread_id or not message_detail:
            print(" Nenhum email nao lido encontrado para processar.")
            return True
        
        print(f" Email encontrado! Thread ID: {thread_id}\n")
        
        # Extrai informações do email
        headers = message_detail['payload'].get('headers', [])
        email_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        email_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
        email_remetente = extrair_email_remetente(email_from)
        email_date = next((h['value'] for h in headers if h['name'] == 'Date'), 'N/A')
        
        print(" Informações do Email:")
        print(f"   De: {email_from}")
        print(f"   Remetente: {email_remetente}")
        print(f"   Assunto: {email_subject}")
        print(f"   Data: {email_date}")
        
        # Validação de segurança
        print(f"\n Validando email...")
        validacao = validar_email_uisa(email_remetente)
        if not validacao['valido']:
            print(f"   Email bloqueado: {validacao['mensagem']}")
            print(f"    Email nao será processado.")
            marcar_como_processado(service, thread_id)
            return False
        
        print(f"   Email validado com sucesso")
        
        # Extrai corpo do email
        print(f"\n Extraindo corpo do email...")
        email_body = extrair_corpo_email(message_detail)
        if email_body:
            print(f"   Corpo extraído ({len(email_body)} caracteres)")
            print(f"   Preview: {email_body[:100]}...")
        else:
            print(f"    Corpo do email vazio ou nao encontrado")
        
        # Processa anexos
        print(f"\n Processando anexos...")
        anexos_ids = processar_anexos(service, message_detail)
        
        # Chama API para abrir chamado
        print(f"\n Abrindo chamado via API...")
        resposta = chamar_api_chamado(
            assunto=email_subject,
            corpo=email_body,
            email=email_remetente,
            anexos_ids=anexos_ids
        )
        
        chamado_aberto_com_sucesso = False
        
        if resposta:
            print(f"\n Processando resposta da API...")
            try:
                resposta_json = json.loads(resposta) if isinstance(resposta, str) else resposta
                chamado_aberto_com_sucesso = processar_resposta_chamado(resposta_json, email_remetente, email_subject)
            except json.JSONDecodeError as e:
                print(f"    Erro ao processar JSON de resposta: {str(e)}")
                print(f"   Resposta bruta: {resposta[:200]}")
                chamado_aberto_com_sucesso = False
        else:
            print(f"   Falha ao abrir chamado")
            chamado_aberto_com_sucesso = False
        
        # Só marca como processado se o chamado foi aberto com sucesso
        if chamado_aberto_com_sucesso:
            print(f"\n  Marcando email como processado...")
            marcar_como_processado(service, thread_id)
            print(f"\n Processamento concluído com sucesso!")
            return True
        else:
            print(f"\n [AVISO] Email NÃO será marcado como processado devido à falha.")
            print(f"   O email permanecerá não lido para nova tentativa.")
            return False
        
    except HttpError as e:
        print(f"\n Erro HTTP: {str(e)}")
        if e.resp.status == 403:
            print("     Verifique as permissoes da conta de serviço")
        return False
    except Exception as e:
        print(f"\n Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Processa o email mais recente e abre chamado',
        epilog='Este teste simula o fluxo completo do monitoramento de emails.\n'
               'Ele busca o email nao lido mais recente, processa anexos,\n'
               'valida o remetente e abre um chamado via API.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    args = parser.parse_args()
    
    print("\n Iniciando teste de processamento de email mais recente...\n")
    
    sucesso = processar_email_mais_recente()
    
    if sucesso:
        print("\n Teste concluído com sucesso!\n")
    else:
        print("\n Teste falhou. Verifique os logs acima.\n")
        sys.exit(1)
