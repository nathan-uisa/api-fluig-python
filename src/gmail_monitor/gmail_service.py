"""
Serviço principal para monitoramento de emails do Gmail
"""
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelos_fluig import AberturaChamado
from src.fluig.fluig_core import FluigCore
from src.utilitarios_centrais.google_drive_utils import baixar_arquivo_drive
from .email_validator import validar_email_uisa, extrair_email_remetente
from .drive_uploader import salvar_anexo_no_drive
from .people_service import buscar_telefone_no_diretorio
from .email_sender import enviar_email


class GmailMonitorService:
    """
    Serviço para monitorar emails do Gmail e processar chamados automaticamente
    """
    
    def __init__(self):
        self.label_processados = "PROCESSADOS"
        self.gmail_service = None
        self.label_id = None
        self._inicializar_servico()
    
    def _inicializar_servico(self):
        """Inicializa o serviço do Gmail"""
        try:
            logger.info("[gmail_service] Inicializando serviço Gmail...")
            
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
            
            self.gmail_service = build('gmail', 'v1', credentials=credentials)
            
            # Cria ou obtém a label PROCESSADOS
            self._criar_label_se_nao_existir()
            
            logger.info("[gmail_service] Serviço Gmail inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao inicializar serviço Gmail: {str(e)}")
            import traceback
            logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
    
    def _criar_label_se_nao_existir(self):
        """Cria a label PROCESSADOS se não existir"""
        try:
            # Lista todas as labels
            labels = self.gmail_service.users().labels().list(userId='me').execute()
            
            for label in labels.get('labels', []):
                if label['name'] == self.label_processados:
                    self.label_id = label['id']
                    logger.info(f"[gmail_service] Label '{self.label_processados}' encontrada (ID: {self.label_id})")
                    return
            
            # Cria a label se não existir
            label_obj = {
                'name': self.label_processados,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.gmail_service.users().labels().create(
                userId='me',
                body=label_obj
            ).execute()
            
            self.label_id = created_label['id']
            logger.info(f"[gmail_service] Label '{self.label_processados}' criada (ID: {self.label_id})")
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao criar/obter label: {str(e)}")
    
    def processar_emails(self):
        """
        Processa emails não lidos e abre chamados
        """
        try:
            logger.info("[gmail_service] Iniciando processamento de emails...")
            
            # Busca threads não lidas
            query = 'is:unread'
            threads = self.gmail_service.users().threads().list(
                userId='me',
                q=query
            ).execute()
            
            thread_list = threads.get('threads', [])
            logger.info(f"[gmail_service] Encontradas {len(thread_list)} thread(s) não lida(s)")
            
            for thread_item in thread_list:
                thread_id = thread_item['id']
                
                try:
                    # Obtém detalhes da thread
                    thread = self.gmail_service.users().threads().get(
                        userId='me',
                        id=thread_id
                    ).execute()
                    
                    # Verifica se já tem a label PROCESSADOS
                    labels = thread.get('labelIds', [])
                    if self.label_id and self.label_id in labels:
                        logger.info(f"[gmail_service] Email já processado - pulando thread ID: {thread_id}")
                        continue
                    
                    # Pega a primeira mensagem da thread
                    messages = thread.get('messages', [])
                    if not messages:
                        continue
                    
                    message = messages[0]
                    message_id = message['id']
                    
                    # Obtém detalhes da mensagem
                    message_detail = self.gmail_service.users().messages().get(
                        userId='me',
                        id=message_id,
                        format='full'
                    ).execute()
                    
                    # Extrai informações do email
                    headers = message_detail['payload'].get('headers', [])
                    email_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    email_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    email_remetente = extrair_email_remetente(email_from)
                    
                    # Obtém corpo do email
                    email_body = self._extrair_corpo_email(message_detail)
                    
                    logger.info(f"[gmail_service] Processando email de: {email_remetente}")
                    logger.info(f"[gmail_service] Assunto: {email_subject}")
                    
                    # Validação de segurança do domínio
                    validacao = validar_email_uisa(email_remetente)
                    if not validacao['valido']:
                        logger.info(f"[gmail_service] Email bloqueado - não processado: {email_remetente} - Motivo: {validacao['mensagem']}")
                        
                        # Se é da BLACK_LIST_EMAILS, apenas passa (não marca como processado)
                        if validacao.get('is_blacklist', False):
                            logger.info(f"[gmail_service] Email na BLACK_LIST_EMAILS - pulando sem marcar como processado")
                            continue
                        
                        # Outros emails bloqueados são marcados como processados para não tentar novamente
                        self._marcar_como_processado(thread_id)
                        continue
                    
                    # Processa anexos
                    anexos_ids = self._processar_anexos(message_detail)
                    
                    # Chama a API para abrir chamado
                    resposta = self._chamar_api_chamado(
                        assunto=email_subject,
                        corpo=email_body,
                        email=email_remetente,
                        anexos_ids=anexos_ids
                    )
                    
                    chamado_aberto_com_sucesso = False
                    
                    if resposta:
                        try:
                            resposta_json = json.loads(resposta) if isinstance(resposta, str) else resposta
                            logger.info(f"[gmail_service] Resposta da API: {json.dumps(resposta_json)}")
                            chamado_aberto_com_sucesso = self._processar_resposta_chamado(resposta_json, email_remetente, email_subject)
                        except json.JSONDecodeError as e:
                            logger.error(f"[gmail_service] Erro ao processar JSON de resposta: {str(e)}")
                            chamado_aberto_com_sucesso = False
                    else:
                        logger.error(f"[gmail_service] Falha ao abrir chamado - resposta vazia ou erro na API")
                        chamado_aberto_com_sucesso = False
                    
                    # Só marca como processado se o chamado foi aberto com sucesso
                    if chamado_aberto_com_sucesso:
                        logger.info(f"[gmail_service] Chamado aberto com sucesso - marcando email como processado")
                        self._marcar_como_processado(thread_id)
                    else:
                        logger.warning(f"[gmail_service] Email NÃO será marcado como processado devido à falha. Permanecerá não lido para nova tentativa.")
                    
                except Exception as e:
                    logger.error(f"[gmail_service] Erro ao processar thread {thread_id}: {str(e)}")
                    import traceback
                    logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
                    continue
            
            logger.info("[gmail_service] Processamento de emails concluído")
            
        except HttpError as e:
            logger.error(f"[gmail_service] Erro HTTP ao processar emails: {str(e)}")
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao processar emails: {str(e)}")
            import traceback
            logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
    
    def _extrair_corpo_email(self, message_detail: Dict) -> str:
        """Extrai o corpo do email em texto plano"""
        try:
            payload = message_detail.get('payload', {})
            
            # Tenta obter texto plano
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data')
                        if data:
                            import base64
                            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            # Se não encontrou em parts, tenta diretamente
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data')
                if data:
                    import base64
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            return ""
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao extrair corpo do email: {str(e)}")
            return ""
    
    def _processar_anexos(self, message_detail: Dict) -> List[str]:
        """Processa anexos do email e salva no Drive"""
        anexos_ids = []
        
        try:
            payload = message_detail.get('payload', {})
            
            def processar_parts(parts):
                for part in parts:
                    filename = part.get('filename')
                    if filename and part.get('body', {}).get('attachmentId'):
                        attachment_id = part['body']['attachmentId']
                        message_id = message_detail['id']
                        
                        # Baixa o anexo
                        attachment = self.gmail_service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=attachment_id
                        ).execute()
                        
                        # Decodifica o conteúdo
                        import base64
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        
                        # Salva no Drive
                        file_id = salvar_anexo_no_drive(file_data, filename)
                        if file_id:
                            anexos_ids.append(file_id)
                            logger.info(f"[gmail_service] Anexo processado com sucesso. ID adicionado à lista: {file_id}")
            
            if 'parts' in payload:
                processar_parts(payload['parts'])
            
            if anexos_ids:
                logger.info(f"[gmail_service] Encontrados {len(anexos_ids)} anexo(s) no email.")
            else:
                logger.info(f"[gmail_service] Nenhum anexo encontrado no email.")
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao processar anexos da mensagem: {str(e)}")
        
        return anexos_ids
    
    def _chamar_api_chamado(self, assunto: str, corpo: str, email: str, anexos_ids: List[str]) -> Optional[str]:
        """Abre chamado usando funções internas do projeto"""
        try:
            # Usa ambiente PRD por padrão (pode ser configurado via variável de ambiente)
            ambiente = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_AMBIENTE', 'prd').upper()
            
            # Busca telefone
            telefone = buscar_telefone_no_diretorio(email)
            
            # 1. Validar e baixar anexos do Google Drive (se houver)
            arquivos_baixados = []
            if anexos_ids and len(anexos_ids) > 0:
                logger.info(f"[gmail_service] Iniciando download de {len(anexos_ids)} arquivo(s) do Google Drive")
                for file_id in anexos_ids:
                    try:
                        conteudo_bytes, nome_arquivo = baixar_arquivo_drive(file_id)
                        if conteudo_bytes and nome_arquivo:
                            arquivos_baixados.append({
                                'bytes': conteudo_bytes,
                                'nome': nome_arquivo,
                                'file_id': file_id
                            })
                            logger.info(f"[gmail_service] Arquivo {file_id} baixado com sucesso: {nome_arquivo}")
                        else:
                            logger.warning(f"[gmail_service] Falha ao baixar arquivo {file_id} - continuando sem anexo")
                    except Exception as e:
                        logger.error(f"[gmail_service] Erro ao processar anexo {file_id}: {str(e)} - continuando sem anexo")
            
            # 2. Abrir chamado UISA (normal)
            logger.info("[gmail_service] Abrindo chamado UISA (normal)")
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
                    logger.info(f"[gmail_service] Chamado aberto com sucesso - ID: {process_instance_id}")
                    
                    # 3. Se houver anexos e chamado foi criado, anexar arquivos
                    if arquivos_baixados and process_instance_id:
                        logger.info(f"[gmail_service] Iniciando anexo de {len(arquivos_baixados)} arquivo(s) ao chamado {process_instance_id}")
                        
                        # Obtém colleague ID baseado no ambiente
                        if ambiente == "PRD":
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID
                        else:  # QLD
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                        
                        if not colleague_id or colleague_id == "":
                            logger.error(f"[gmail_service] Colleague ID não configurado para ambiente {ambiente} - não será possível fazer upload/anexar arquivos")
                        else:
                            logger.info(f"[gmail_service] Usando Colleague ID: {colleague_id} para upload")
                            # Para cada arquivo, faz upload e anexa ao chamado
                            for arquivo in arquivos_baixados:
                                try:
                                    logger.info(f"[gmail_service] Fazendo upload do arquivo: {arquivo['nome']}")
                                    resultado_upload = fluig_core.upload_arquivo_fluig(
                                        arquivo_bytes=arquivo['bytes'],
                                        nome_arquivo=arquivo['nome'],
                                        colleague_id=colleague_id
                                    )
                                    
                                    if resultado_upload:
                                        logger.info(f"[gmail_service] Upload do arquivo {arquivo['nome']} realizado com sucesso")
                                        
                                        # Anexa ao chamado
                                        logger.info(f"[gmail_service] Anexando arquivo {arquivo['nome']} ao chamado {process_instance_id}")
                                        sucesso_anexo = fluig_core.anexar_arquivo_chamado(
                                            process_instance_id=process_instance_id,
                                            nome_arquivo=arquivo['nome']
                                        )
                                        
                                        if sucesso_anexo:
                                            logger.info(f"[gmail_service] Arquivo {arquivo['nome']} anexado ao chamado {process_instance_id}")
                                        else:
                                            logger.error(f"[gmail_service] Falha ao anexar arquivo {arquivo['nome']} ao chamado {process_instance_id}")
                                    else:
                                        logger.error(f"[gmail_service] Falha no upload do arquivo {arquivo['nome']}")
                                        
                                except Exception as e:
                                    logger.error(f"[gmail_service] Erro ao processar anexo {arquivo['nome']}: {str(e)} - continuando com próximo arquivo")
                                    import traceback
                                    logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
                    
                    # Retorna o processInstanceId como string JSON
                    return json.dumps(process_instance_id)
                else:
                    logger.error(f"[gmail_service] Chamado aberto mas processInstanceId não encontrado na resposta")
                    logger.debug(f"[gmail_service] Dados recebidos: {dados}")
                    return None
            else:
                logger.error(f"[gmail_service] Falha ao abrir chamado - Status: {resposta.get('status_code') if resposta else 'N/A'}")
                logger.error(f"[gmail_service] Resposta: {resposta.get('texto', 'Erro desconhecido') if resposta else 'Resposta vazia'}")
                return None
                
        except Exception as e:
            logger.error(f"[gmail_service] Erro fatal ao abrir chamado: {str(e)}")
            import traceback
            logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
            return None
    
    def _processar_resposta_chamado(self, resposta: Any, email_remetente: str, assunto_original: str) -> bool:
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
                logger.warning(f"[gmail_service] Chamado rejeitado: {resposta.get('mensagem', 'Erro genérico')}")
                enviar_email(
                    email_remetente,
                    "Chamado Não Aprovado",
                    f"O chamado não pôde ser aberto.\nMotivo: {resposta.get('mensagem', 'Erro genérico')}"
                )
                return False
        
        if process_instance_id:
            link = f"https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID={process_instance_id}"
            logger.info(f"[gmail_service] Chamado criado com sucesso - ID: {process_instance_id}")
            enviar_email(
                email_remetente,
                f"Chamado Aberto - #{process_instance_id}",
                f"Chamado criado com sucesso.\nNúmero: {process_instance_id}\nLink: {link}"
            )
            return True
        else:
            logger.error("[gmail_service] Erro: processInstanceId não identificado na resposta.")
            return False
    
    def _marcar_como_processado(self, thread_id: str):
        """Marca a thread como processada"""
        try:
            if self.label_id:
                self.gmail_service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body={
                        'addLabelIds': [self.label_id],
                        'removeLabelIds': ['UNREAD']
                    }
                ).execute()
            else:
                # Se não tem label, apenas marca como lido
                self.gmail_service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao adicionar label: {str(e)}")
            # Tenta apenas marcar como lido
            try:
                self.gmail_service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            except:
                pass
