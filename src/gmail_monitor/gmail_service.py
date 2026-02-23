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
from .email_validator import validar_email_uisa, extrair_email_remetente
from .people_service import buscar_telefone_no_diretorio
from .email_sender import enviar_email, criar_template_email_chamado, criar_template_email_erro
from .email_deduplicator import EmailDeduplicator


class GmailMonitorService:
    """
    Serviço para monitorar emails do Gmail e processar chamados automaticamente
    """
    
    def __init__(self):
        self.label_processados = "PROCESSADOS"
        self.gmail_service = None
        self.label_id = None
        self.deduplicator = EmailDeduplicator()
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
                    
                    # Verifica duplicação baseada em padrões (UUID, MAC, etc.)
                    eh_duplicado, identificador, process_id_existente = self.deduplicator.verificar_duplicado(
                        email_subject, email_body, email_remetente
                    )
                    
                    if eh_duplicado:
                        logger.info(
                            f"[gmail_service] Email duplicado detectado - Identificador: {identificador}, "
                            f"Chamado existente: {process_id_existente if process_id_existente else 'N/A'}. "
                            f"Email não será processado."
                        )
                        # Marca como processado para não tentar novamente
                        self._marcar_como_processado(thread_id)
                        continue
                    
                    # Processa anexos
                    anexos = self._processar_anexos(message_detail)
                    
                    # Chama a API para abrir chamado
                    resposta = self._chamar_api_chamado(
                        assunto=email_subject,
                        corpo=email_body,
                        email=email_remetente,
                        anexos=anexos
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
                        
                        # Marca identificador como processado para deduplicação futura
                        process_instance_id = None
                        if resposta:
                            try:
                                resposta_json = json.loads(resposta) if isinstance(resposta, str) else resposta
                                dados = resposta_json.get('dados', {})
                                if isinstance(dados, dict):
                                    process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
                            except:
                                pass
                        
                        self.deduplicator.marcar_como_processado(email_subject, email_body, process_instance_id)
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
    
    def _processar_anexos(self, message_detail: Dict) -> List[Dict[str, str]]:
        """
        Processa anexos do email e retorna em formato base64 (sem salvar no Drive)
        
        Trata diferentes estruturas de email:
        - Emails simples (sem multipart): verifica anexo diretamente no payload.body
        - Emails multipart: processa parts recursivamente para encontrar anexos aninhados
        
        Returns:
            Lista de dicionários com 'nome' e 'conteudo_base64', ou lista vazia se não houver anexos
        """
        anexos = []
        
        try:
            payload = message_detail.get('payload', {})
            message_id = message_detail.get('id')
            
            if not message_id:
                logger.warning("[gmail_service] Message ID não encontrado - não é possível processar anexos")
                return anexos
            
            import base64
            
            def processar_part(part: Dict):
                """
                Processa uma part individual, verificando se é um anexo
                e processando recursivamente se tiver parts aninhadas
                """
                # Verifica se esta part é um anexo
                filename = part.get('filename')
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')
                        
                if filename and attachment_id:
                    # Esta part é um anexo
                    try:
                        # Baixa o anexo
                        attachment = self.gmail_service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=attachment_id
                        ).execute()
                        
                        # Decodifica o conteúdo (Gmail usa base64 URL-safe)
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        
                        # Converte para base64 padrão (não URL-safe)
                        conteudo_base64 = base64.b64encode(file_data).decode('utf-8')
                        
                        anexos.append({
                            'nome': filename,
                            'conteudo_base64': conteudo_base64
                        })
                        logger.info(f"[gmail_service] Anexo processado com sucesso: {filename} ({len(file_data)} bytes)")
                    except Exception as e:
                        logger.error(f"[gmail_service] Erro ao baixar anexo {filename}: {str(e)}")
                
                # Processa parts aninhadas (para emails multipart complexos)
                if 'parts' in part:
                    for nested_part in part['parts']:
                        processar_part(nested_part)
            
            # Verifica se é email simples (sem multipart) com anexo direto
            if 'parts' not in payload:
                # Email simples - verifica se há anexo diretamente no body
                body = payload.get('body', {})
                filename = payload.get('filename')
                attachment_id = body.get('attachmentId')
                
                if filename and attachment_id:
                    # Email simples com anexo
                    try:
                        attachment = self.gmail_service.users().messages().attachments().get(
                            userId='me',
                            messageId=message_id,
                            id=attachment_id
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(attachment['data'])
                        conteudo_base64 = base64.b64encode(file_data).decode('utf-8')
                        
                        anexos.append({
                            'nome': filename,
                            'conteudo_base64': conteudo_base64
                        })
                        logger.info(f"[gmail_service] Anexo processado com sucesso (email simples): {filename} ({len(file_data)} bytes)")
                    except Exception as e:
                        logger.error(f"[gmail_service] Erro ao baixar anexo {filename}: {str(e)}")
            else:
                # Email multipart - processa todas as parts recursivamente
                for part in payload['parts']:
                    processar_part(part)
            
            # Log do resultado
            if anexos:
                logger.info(f"[gmail_service] Encontrados {len(anexos)} anexo(s) no email.")
            else:
                logger.info(f"[gmail_service] Nenhum anexo encontrado no email.")
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao processar anexos da mensagem: {str(e)}")
            import traceback
            logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
        
        return anexos
    
    def _chamar_api_chamado(self, assunto: str, corpo: str, email: str, anexos: List[Dict[str, str]]) -> Optional[str]:
        """Abre chamado usando funções internas do projeto com anexos diretos (base64)"""
        try:
            # Usa ambiente PRD por padrão (pode ser configurado via variável de ambiente)
            ambiente = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_AMBIENTE', 'prd').upper()
            
            # Verifica se o email tem configuração salva
            from src.configs.config_manager import get_config_manager
            config_manager = get_config_manager()
            configs = config_manager.carregar_configuracao(email)
            
            # Se encontrou configuração e tem servico_id, abre chamado classificado
            if configs and configs.get('servico_id') and configs.get('servico_id').strip():
                logger.info(f"[gmail_service] Configuração encontrada para email {email} - abrindo chamado classificado")
                return self._abrir_chamado_classificado(
                    assunto=assunto,
                    corpo=corpo,
                    email=email,
                    anexos=anexos,
                    configs=configs,
                    ambiente=ambiente
                )
            
            # Busca telefone
            telefone = buscar_telefone_no_diretorio(email)
            
            # Converte anexos para formato AnexoBase64
            from src.modelo_dados.modelos_fluig import AnexoBase64
            anexos_base64 = None
            if anexos and len(anexos) > 0:
                anexos_base64 = [
                    AnexoBase64(nome=anexo['nome'], conteudo_base64=anexo['conteudo_base64'])
                    for anexo in anexos
                ]
                logger.info(f"[gmail_service] Processando {len(anexos_base64)} anexo(s) em base64")
            
            # Abrir chamado UISA (normal)
            logger.info("[gmail_service] Abrindo chamado UISA (normal)")
            fluig_core = FluigCore(ambiente=ambiente)
            process_instance_id = None
            
            item_uisa = AberturaChamado(
                titulo=assunto,
                descricao=corpo,
                usuario=email,
                telefone=telefone if telefone else None,
                anexos=anexos_base64
            )
            resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=item_uisa)
            
            if resposta and resposta.get('sucesso'):
                dados = resposta.get('dados', {})
                if dados and isinstance(dados, dict):
                    process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
                
                if process_instance_id:
                    logger.info(f"[gmail_service] Chamado aberto com sucesso - ID: {process_instance_id}")
                    
                    # Salva histórico inicial do chamado (chamados abertos via email são monitorados)
                    try:
                        logger.info(f"[gmail_service] Salvando histórico inicial do chamado {process_instance_id}...")
                        from src.historico_monitor.historico_manager import HistoricoManager
                        historico_manager = HistoricoManager()
                        
                        # Obtém histórico inicial do Fluig
                        historico_inicial = fluig_core.obter_historico_chamado(process_instance_id)
                        
                        if historico_inicial:
                            sucesso_salvamento = historico_manager.salvar_historico(
                                process_instance_id=process_instance_id,
                                historico_data=historico_inicial,
                                ambiente=ambiente,
                                email_remetente=email
                            )
                            if sucesso_salvamento:
                                logger.info(f"[gmail_service] Histórico inicial do chamado {process_instance_id} salvo com sucesso")
                            else:
                                logger.warning(f"[gmail_service] Falha ao salvar histórico inicial do chamado {process_instance_id}")
                        else:
                            logger.warning(f"[gmail_service] Não foi possível obter histórico inicial do chamado {process_instance_id}")
                    except Exception as e:
                        # Não falha a abertura do chamado se houver erro ao salvar histórico
                        logger.error(f"[gmail_service] Erro ao salvar histórico inicial do chamado {process_instance_id}: {str(e)}")
                        import traceback
                        logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
                    
                    # Processar e anexar arquivos se houver anexos
                    if anexos and len(anexos) > 0 and process_instance_id:
                        logger.info(f"[gmail_service] Iniciando anexo de {len(anexos)} arquivo(s) ao chamado {process_instance_id}")
                        
                        # Obtém colleague_id baseado no ambiente
                        if ambiente == "PRD":
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID
                        else:  # QLD
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                        
                        if not colleague_id or colleague_id == "":
                            logger.error(f"[gmail_service] Colleague ID não configurado para ambiente {ambiente} - não será possível fazer upload/anexar arquivos")
                        else:
                            logger.info(f"[gmail_service] Usando Colleague ID: {colleague_id} para upload")
                            
                            # Processa anexos: decodifica base64 para bytes
                            import base64
                            arquivos_processados = []
                            for anexo in anexos:
                                try:
                                    conteudo_bytes = base64.b64decode(anexo['conteudo_base64'])
                                    arquivos_processados.append({
                                        'bytes': conteudo_bytes,
                                        'nome': anexo['nome']
                                    })
                                    logger.info(f"[gmail_service] Anexo {anexo['nome']} processado com sucesso ({len(conteudo_bytes)} bytes)")
                                except Exception as e:
                                    logger.error(f"[gmail_service] Erro ao processar anexo {anexo['nome']}: {str(e)} - continuando sem anexo")
                            
                            # Para cada arquivo, faz upload e anexa ao chamado
                            for arquivo in arquivos_processados:
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
    
    def _abrir_chamado_classificado(
        self, 
        assunto: str, 
        corpo: str, 
        email: str, 
        anexos: List[Dict[str, str]], 
        configs: Dict[str, str],
        ambiente: str
    ) -> Optional[str]:
        """Abre chamado classificado usando configurações salvas"""
        try:
            logger.info(f"[gmail_service] Abrindo chamado classificado para email: {email}")
            
            # Busca telefone
            telefone = buscar_telefone_no_diretorio(email)
            
            # Converte anexos para formato AnexoBase64
            from src.modelo_dados.modelos_fluig import AnexoBase64, AberturaChamadoClassificado
            anexos_base64 = None
            if anexos and len(anexos) > 0:
                anexos_base64 = [
                    AnexoBase64(nome=anexo['nome'], conteudo_base64=anexo['conteudo_base64'])
                    for anexo in anexos
                ]
                logger.info(f"[gmail_service] Processando {len(anexos_base64)} anexo(s) em base64")
            
            # Busca colleagueId do usuario_responsavel se fornecido
            target_assignee = None
            usuario_responsavel = configs.get('usuario_responsavel', '').strip()
            if usuario_responsavel:
                logger.info(f"[gmail_service] Buscando colleagueId para usuario_responsavel: {usuario_responsavel}")
                fluig_core_temp = FluigCore(ambiente=ambiente)
                dados_colleague = fluig_core_temp.Dataset_config(dataset_id="colleague", user=usuario_responsavel)
                
                if not hasattr(dados_colleague, 'status_code') and dados_colleague and dados_colleague.get('content'):
                    content = dados_colleague.get('content', [])
                    if isinstance(content, list) and len(content) > 0:
                        colleague_data = content[0]
                    elif isinstance(content, dict) and 'values' in content:
                        values = content.get('values', [])
                        if values and len(values) > 0:
                            colleague_data = values[0]
                        else:
                            colleague_data = None
                    else:
                        colleague_data = None
                    
                    if colleague_data:
                        target_assignee = colleague_data.get('colleagueId', '')
                        if target_assignee:
                            logger.info(f"[gmail_service] ColleagueId encontrado para usuario_responsavel: {target_assignee}")
                        else:
                            logger.warning(f"[gmail_service] ColleagueId não encontrado nos dados para usuario_responsavel: {usuario_responsavel}")
                    else:
                        logger.warning(f"[gmail_service] Nenhum dado encontrado no dataset colleague para usuario_responsavel: {usuario_responsavel}")
                else:
                    logger.warning(f"[gmail_service] Erro ao buscar colleagueId para usuario_responsavel: {usuario_responsavel}")
            
            # Cria item de chamado classificado
            item_classificado = AberturaChamadoClassificado(
                titulo=assunto,
                descricao=corpo,
                usuario=email,
                telefone=telefone if telefone else None,
                servico=configs.get('servico_id', '').strip(),
                anexos=anexos_base64
            )
            
            # Abre chamado classificado
            fluig_core = FluigCore(ambiente=ambiente)
            resposta = fluig_core.AberturaDeChamado(
                tipo_chamado="classificado", 
                Item=item_classificado,
                target_assignee=target_assignee
            )
            
            if resposta and resposta.get('sucesso'):
                dados = resposta.get('dados', {})
                if dados and isinstance(dados, dict):
                    process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
                
                if process_instance_id:
                    logger.info(f"[gmail_service] Chamado classificado aberto com sucesso - ID: {process_instance_id}")
                    
                    # Salva histórico inicial do chamado (chamados abertos via email são monitorados)
                    try:
                        logger.info(f"[gmail_service] Salvando histórico inicial do chamado {process_instance_id}...")
                        from src.historico_monitor.historico_manager import HistoricoManager
                        historico_manager = HistoricoManager()
                        
                        # Obtém histórico inicial do Fluig
                        historico_inicial = fluig_core.obter_historico_chamado(process_instance_id)
                        
                        if historico_inicial:
                            sucesso_salvamento = historico_manager.salvar_historico(
                                process_instance_id=process_instance_id,
                                historico_data=historico_inicial,
                                ambiente=ambiente,
                                email_remetente=email
                            )
                            if sucesso_salvamento:
                                logger.info(f"[gmail_service] Histórico inicial do chamado {process_instance_id} salvo com sucesso")
                            else:
                                logger.warning(f"[gmail_service] Falha ao salvar histórico inicial do chamado {process_instance_id}")
                        else:
                            logger.warning(f"[gmail_service] Não foi possível obter histórico inicial do chamado {process_instance_id}")
                    except Exception as e:
                        # Não falha a abertura do chamado se houver erro ao salvar histórico
                        logger.error(f"[gmail_service] Erro ao salvar histórico inicial do chamado {process_instance_id}: {str(e)}")
                        import traceback
                        logger.debug(f"[gmail_service] Traceback: {traceback.format_exc()}")
                    
                    # Processar e anexar arquivos se houver anexos
                    if anexos and len(anexos) > 0 and process_instance_id:
                        logger.info(f"[gmail_service] Iniciando anexo de {len(anexos)} arquivo(s) ao chamado {process_instance_id}")
                        
                        # Obtém colleague_id baseado no ambiente
                        if ambiente == "PRD":
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID
                        else:  # QLD
                            colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                        
                        if not colleague_id or colleague_id == "":
                            logger.error(f"[gmail_service] Colleague ID não configurado para ambiente {ambiente} - não será possível fazer upload/anexar arquivos")
                        else:
                            logger.info(f"[gmail_service] Usando Colleague ID: {colleague_id} para upload")
                            
                            # Processa anexos: decodifica base64 para bytes
                            import base64
                            arquivos_processados = []
                            for anexo in anexos:
                                try:
                                    conteudo_bytes = base64.b64decode(anexo['conteudo_base64'])
                                    arquivos_processados.append({
                                        'bytes': conteudo_bytes,
                                        'nome': anexo['nome']
                                    })
                                    logger.info(f"[gmail_service] Anexo {anexo['nome']} processado com sucesso ({len(conteudo_bytes)} bytes)")
                                except Exception as e:
                                    logger.error(f"[gmail_service] Erro ao processar anexo {anexo['nome']}: {str(e)} - continuando sem anexo")
                            
                            # Para cada arquivo, faz upload e anexa ao chamado
                            for arquivo in arquivos_processados:
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
                    logger.error(f"[gmail_service] Chamado classificado aberto mas processInstanceId não encontrado")
                    return None
            else:
                logger.error(f"[gmail_service] Falha ao abrir chamado classificado: {resposta.get('texto', 'Erro desconhecido') if resposta else 'Resposta vazia'}")
                return None
            
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao abrir chamado classificado: {str(e)}")
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
                mensagem_erro = resposta.get('mensagem', 'Erro genérico')
                logger.warning(f"[gmail_service] Chamado rejeitado: {mensagem_erro}")
                
                # Criar template HTML formatado para erro
                html_template = criar_template_email_erro(mensagem_erro)
                
                # Corpo em texto plano (fallback)
                corpo_texto = f"O chamado não pôde ser aberto.\n\nMotivo: {mensagem_erro}"
                
                enviar_email(
                    email_remetente,
                    "Chamado Não Pôde Ser Aberto",
                    corpo_texto,
                    html=html_template
                )
                return False
        
        if process_instance_id:
            link = f"https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID={process_instance_id}"
            logger.info(f"[gmail_service] Chamado criado - ID: {process_instance_id}")
            
            # Criar template HTML formatado
            html_template = criar_template_email_chamado(process_instance_id, link, email_remetente)
            
            # Corpo em texto plano (fallback para clientes que não suportam HTML)
            corpo_texto = f"Chamado criado com sucesso.\n\nNúmero: {process_instance_id}\n\nLink: {link}\n\nO chamado foi criado com sucesso! As atualizações do chamado serão enviadas para o email {email_remetente}."
            
            enviar_email(
                email_remetente,
                f"Chamado Criado - #{process_instance_id}",
                corpo_texto,
                html=html_template
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
                    body={'addLabelIds': [self.label_id],'removeLabelIds': ['UNREAD']}).execute()
            else:
                # Se não tem label, apenas marca como lido
                self.gmail_service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body={'removeLabelIds': ['UNREAD']}).execute()
        except Exception as e:
            logger.error(f"[gmail_service] Erro ao adicionar label: {str(e)}")
            # Tenta apenas marcar como lido
            try:
                self.gmail_service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body={'removeLabelIds': ['UNREAD']}).execute()
            except:
                pass
