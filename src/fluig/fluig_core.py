from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import json
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.modelo_dados.modelos_fluig import DatasetConfig
from src.utilitarios_centrais.logger import logger
from src.fluig.fluig_requests import RequestsFluig
from src.web.web_cookies import carregar_cookies, cookies_para_requests
from src.web.web_auth_manager import garantir_autenticacao, obter_cookies_validos
import requests
import io

class FluigCore():
    def __init__(self, ambiente: str = "PRD"):
        """
        Inicializa a classe FluigCore
        
        Args:
            ambiente: Ambiente ('PRD' ou 'QLD')
        """
        logger.info(f"[FluigCore] Inicializando - Ambiente: {ambiente}")
        
        # Armazena ambiente
        self.ambiente = ambiente
        
        # Inicializa requests
        self.requests = RequestsFluig(ambiente)
        
        # Configura URL base
        if ambiente == "PRD":
            self.url_base = ConfigEnvSetings.URL_FLUIG_PRD
            logger.debug(f"[FluigCore] URL base PRD configurada: {self.url_base}")
        elif ambiente == "QLD":
            self.url_base = ConfigEnvSetings.URL_FLUIG_QLD
            logger.debug(f"[FluigCore] URL base QLD configurada: {self.url_base}")
        else:
            logger.error(f"[FluigCore] Ambiente inválido: {ambiente}")
            raise ValueError(f"Ambiente inválido: {ambiente}")
        
        logger.info(f"[FluigCore] Instância criada com sucesso")

    def Dataset_config(self, dataset_id: str, user: str) -> dict:
        """
        Retorna configuração de busca do dataset
        
        Determina automaticamente se USER é email ou nome/chapa baseado na presença de '@'
        e retorna os parâmetros datasetId e filterFields conforme o dataset configurado.
        
        Args:
            dataset_id: ID do dataset conforme DatasetConfig
            user: Usuário para busca (email ou nome/chapa)
        
        Returns:
            Dicionário com dados do dataset ou resposta HTTP
        
        Raises:
            ValueError: Se dataset_id não existe ou user não foi fornecido
        """
        logger.info(f"[Dataset_config] Iniciando configuração de busca - Ambiente: {self.ambiente}, Dataset: {dataset_id}, User: {user}")
        
        # Valida dataset_id
        if not dataset_id:
            logger.error("[Dataset_config] dataset_id não fornecido")
            raise ValueError("[Dataset_config] dataset_id não fornecido")
        
        logger.debug(f"[Dataset_config] Dataset ID: {dataset_id}")
        if not user:
            logger.error("[Dataset_config] user não fornecido")
            raise ValueError("[Dataset_config] user não fornecido")
        
        logger.debug(f"[Dataset_config] User: {user}")
        

        logger.info(f"[Dataset_config] Carregando configuração do dataset '{dataset_id}'...")
        datasets = DatasetConfig()
        
        if dataset_id not in datasets:
            datasets_disponiveis = ', '.join(datasets.keys())
            logger.error(
                f"[Dataset_config] Dataset '{dataset_id}' não encontrado. "
                f"Datasets disponíveis: {datasets_disponiveis}"
            )
            raise ValueError(
                f"[Dataset_config] Dataset '{dataset_id}' não encontrado. "
                f"Datasets disponíveis: {datasets_disponiveis}"
            )
        
        config = datasets[dataset_id]
        logger.info(f"[Dataset_config] Configuração do dataset carregada: {config.get('nome_dataset', dataset_id)}")
        
        # Determinar tipo de busca e campo a usar
        user_stripped = user.strip()
        
        if '@' in user:
            # Busca por email
            campo_busca = config['campo_email']
            tipo_busca = "email"
            logger.info(f"[Dataset_config] Tipo de busca detectado: {tipo_busca} (contém '@')")
        elif dataset_id == 'colleague' and 'campo_currentProject' in config and user_stripped.isdigit():
            # Busca por CHAPA (número) no dataset colleague - usar currentProject
            campo_busca = config['campo_currentProject']
            tipo_busca = "chapa (currentProject)"
            logger.info(f"[Dataset_config] Tipo de busca detectado: {tipo_busca} (CHAPA numérica '{user_stripped}' no dataset colleague)")
        else:
            # Busca por nome (não é email e não é número)
            campo_busca = config['campo_nome']
            tipo_busca = "nome"
            logger.info(f"[Dataset_config] Tipo de busca detectado: {tipo_busca} (nome/chapa)")
        
        logger.debug(f"[Dataset_config] Campo de busca selecionado: {campo_busca}")
        parametro = {
            'datasetId': config['datasetId'],
            'filterFields': f'{campo_busca},{user}'
        }
        
        logger.info(
            f"[Dataset_config] Parâmetros configurados - "
            f"datasetId: {parametro['datasetId']}, "
            f"filterFields: {parametro['filterFields']}"
        )
        url_suffix = config.get('url', '/api/public/ecm/dataset/search')
        url_dataset = self.url_base + url_suffix
        logger.debug(f"[Dataset_config] URL dataset configurada: {url_dataset}")
        logger.info(f"[Dataset_config] Fazendo requisição GET para: {url_dataset}")
        resposta = self.requests.RequestTipoGET(url_dataset, parametro)
        if resposta.status_code == 200:
            try:
                dados = resposta.json()
                logger.info(f"[Dataset_config] Requisição bem-sucedida - {len(dados.get('content', []))} resultado(s) encontrado(s)")
                return dados
            except Exception as e:
                logger.error(f"[Dataset_config] Erro ao processar resposta JSON: {str(e)}")
                return resposta
        else:
            logger.error(f"[Dataset_config] Erro na requisição - Status: {resposta.status_code}")
            return resposta

    def AberturaDeChamado(self,tipo_chamado: str, Item: any, usuario_atendido: Optional[str] = None):
        """
            ITEM
            class AberturaChamadoClassificado(BaseModel):
                titulo: str
                descricao: str
                usuario: str
                servico: str
        """
        """
        Abre um chamado no Fluig
        
        Args:
            tipo_chamado: Tipo de chamado ('classificado' ou 'funcional')
            usuario_atendido: Nome do usuário atendido (opcional)
        """
        logger.info(f"[AberturaDeChamado] Iniciando abertura de chamado - Tipo: {tipo_chamado}, UsuarioAtendido: {usuario_atendido}")
        url = self.url_base + "/process-management/api/v2/processes/Abertura%20de%20Chamados/start"
        
        # Obtém autenticação baseado no ambiente (usa apenas FLUIG_ADMIN_USER)
        if self.ambiente == "QLD":
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            logger.debug(f"[AberturaDeChamado] Usando credenciais QLD - Usuário: {usuario}")
        else:
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            logger.debug(f"[AberturaDeChamado] Usando credenciais PRD - Usuário: {usuario}")
        
        sucesso, cookies_list = garantir_autenticacao(ambiente=self.ambiente, usuario=usuario, senha=senha)
        if not sucesso or not cookies_list:
            logger.error("[AberturaDeChamado] Falha ao garantir autenticação")
            raise ValueError("[AberturaDeChamado] Falha ao garantir autenticação")
        cookies_dict = cookies_para_requests(cookies_list)
        if not cookies_dict:
            logger.error("[AberturaDeChamado] Falha ao converter cookies")
            raise ValueError("[AberturaDeChamado] Falha ao converter cookies")
        from src.utilitarios_centrais.payloads import PayloadChamadoClassificado, PayloadChamadoNormal
        
        if tipo_chamado == "classificado":
            payload = PayloadChamadoClassificado(Item, ambiente=self.ambiente, usuario_atendido=usuario_atendido)
            if not payload:
                logger.error("[AberturaDeChamado] Falha ao montar payload do chamado classificado")
                raise ValueError("[AberturaDeChamado] Falha ao montar payload do chamado classificado")
        elif tipo_chamado == "normal":
            payload = PayloadChamadoNormal(Item, ambiente=self.ambiente, usuario_atendido=usuario_atendido)
            if not payload:
                logger.error("[AberturaDeChamado] Falha ao montar payload do chamado normal")
                raise ValueError("[AberturaDeChamado] Falha ao montar payload do chamado normal")
        else:
            logger.error(f"[AberturaDeChamado] Tipo de chamado inválido: {tipo_chamado}")
            raise ValueError(f"[AberturaDeChamado] Tipo de chamado inválido: {tipo_chamado}")
        
        logger.info(f"[AberturaDeChamado] Enviando requisição POST para: {url}")
        resposta = self.requests.RequestTipoPostCookies(url, payload, cookies_dict)
        resultado = {
            "status_code": resposta.status_code,
            "sucesso": resposta.status_code == 200
        }
        
        try:
            resultado["dados"] = resposta.json()
            logger.info(f"[AberturaDeChamado] Resposta processada com sucesso - Status: {resposta.status_code}")
        except Exception as e:
            logger.warning(f"[AberturaDeChamado] Erro ao processar JSON da resposta: {str(e)}")
            resultado["dados"] = None
            resultado["texto"] = resposta.text[:500] if resposta.text else ""
        
        return resultado

    def upload_arquivo_fluig(self, arquivo_bytes: bytes, nome_arquivo: str, colleague_id: str) -> dict | None:
        """
        Faz upload de um arquivo no Fluig usando o endpoint /ecm/upload
        
        IMPORTANTE: Usa apenas FLUIG_ADMIN_USER
        
        Args:
            arquivo_bytes: Conteúdo do arquivo em bytes
            nome_arquivo: Nome do arquivo
            colleague_id: ID do colaborador (userId) - deve ser ADMIN_COLLEAGUE_ID ou USER_COLLEAGUE_ID
            
        Returns:
            Dicionário com resposta do upload ou None em caso de erro
        """
        try:
            logger.info(f"[upload_arquivo_fluig] Iniciando upload do arquivo: {nome_arquivo}")
            
            # Obtém autenticação - USA APENAS FLUIG_ADMIN_USER
            if self.ambiente == "QLD":
                usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
                senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            else:
                usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
                senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            
            sucesso, cookies_list = garantir_autenticacao(ambiente=self.ambiente, usuario=usuario, senha=senha)
            if not sucesso or not cookies_list:
                logger.error("[upload_arquivo_fluig] Falha ao garantir autenticação")
                return None
            
            cookies_dict = cookies_para_requests(cookies_list)
            if not cookies_dict:
                logger.error("[upload_arquivo_fluig] Falha ao converter cookies")
                return None
            
            # URL do endpoint de upload
            url_upload = self.url_base + "/ecm/upload"
            
            # Prepara arquivo para multipart/form-data
            # NÃO definir Content-Type manualmente - requests define automaticamente com boundary
            files = {
                'files': (nome_arquivo, arquivo_bytes, 'application/octet-stream')
            }
            
            data = {
                'userId': colleague_id
            }
            
            # Log dos dados que serão enviados
            logger.info(f"[upload_arquivo_fluig] Dados do upload:")
            logger.info(f"[upload_arquivo_fluig] - URL: {url_upload}")
            logger.info(f"[upload_arquivo_fluig] - userId: {colleague_id}")
            logger.info(f"[upload_arquivo_fluig] - Nome arquivo: {nome_arquivo}")
            logger.info(f"[upload_arquivo_fluig] - Tamanho arquivo: {len(arquivo_bytes)} bytes")
            logger.info(f"[upload_arquivo_fluig] - Content-Type arquivo: application/octet-stream")
            
            # Faz requisição - SEM definir Content-Type (requests define automaticamente com multipart boundary)
            logger.info(f"[upload_arquivo_fluig] Enviando arquivo para: {url_upload}")
            resposta = requests.post(
                url_upload,
                files=files,
                data=data,
                cookies=cookies_dict,
                timeout=60
            )
            
            if resposta.status_code == 200:
                try:
                    resultado = resposta.json()
                    
                    # Verifica se há erro no conteúdo da resposta
                    if 'files' in resultado and len(resultado['files']) > 0:
                        primeiro_arquivo = resultado['files'][0]
                        if 'error' in primeiro_arquivo:
                            logger.error(f"[upload_arquivo_fluig] Erro no upload: {primeiro_arquivo['error']}")
                            return None
                        logger.info(f"[upload_arquivo_fluig] Upload realizado com sucesso: {resultado}")
                        return resultado
                    else:
                        logger.error(f"[upload_arquivo_fluig] Resposta inesperada: {resultado}")
                        return None
                except Exception as e:
                    logger.error(f"[upload_arquivo_fluig] Erro ao processar resposta JSON: {str(e)}")
                    return None
            else:
                logger.error(f"[upload_arquivo_fluig] Erro no upload - Status: {resposta.status_code}, Resposta: {resposta.text[:500]}")
                return None
                
        except Exception as e:
            logger.error(f"[upload_arquivo_fluig] Erro inesperado no upload: {str(e)}")
            import traceback
            logger.debug(f"[upload_arquivo_fluig] Traceback: {traceback.format_exc()}")
            return None

    def anexar_arquivo_chamado(
        self,
        process_instance_id: int,
        nome_arquivo: str,
        version: int = 57,
        current_movto: int = 3
    ) -> bool:
        """
        Anexa um arquivo a um chamado usando o endpoint saveAttachments
        
        IMPORTANTE: 
        - Usa FLUIG_ADMIN_USER para autenticação
        - Usa ADMIN_COLLEAGUE_ID para taskUserId e colleagueId no payload
        - attachedUser é fixo: "Infra Automação"
        
        Args:
            process_instance_id: ID do chamado (processInstanceId)
            nome_arquivo: Nome do arquivo (usado em name, description e fileName)
            version: Versão do processo (padrão: 57)
            current_movto: Movimento atual (padrão: 3)
            
        Returns:
            True se anexou com sucesso, False caso contrário
        """
        try:
            logger.info(f"[anexar_arquivo_chamado] Anexando arquivo {nome_arquivo} ao chamado {process_instance_id}")
            
            # Obtém ADMIN_COLLEAGUE_ID para usar no payload
            admin_colleague_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
            if not admin_colleague_id or admin_colleague_id == "":
                logger.error("[anexar_arquivo_chamado] ADMIN_COLLEAGUE_ID não configurado")
                return False
            
            # Obtém autenticação - USA APENAS FLUIG_ADMIN_USER
            if self.ambiente == "QLD":
                usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
                senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            else:
                usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
                senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            
            sucesso, cookies_list = garantir_autenticacao(ambiente=self.ambiente, usuario=usuario, senha=senha)
            if not sucesso or not cookies_list:
                logger.error("[anexar_arquivo_chamado] Falha ao garantir autenticação")
                return False
            
            cookies_dict = cookies_para_requests(cookies_list)
            if not cookies_dict:
                logger.error("[anexar_arquivo_chamado] Falha ao converter cookies")
                return False
            
            # URL do endpoint saveAttachments
            url_save = self.url_base + "/ecm/api/rest/ecm/workflowView/saveAttachments"
            
            # Monta payload conforme payload_anexar_arquivo_chamado.json
            # IMPORTANTE: taskUserId e colleagueId devem ser ADMIN_COLLEAGUE_ID
            # attachedUser é fixo: "Infra Automação"
            payload = {"processId": "Abertura de Chamados","version": version,"managerMode": False,"taskUserId": admin_colleague_id,"processInstanceId": process_instance_id,"isDigitalSigned": False,"selectedState": 5,"attachments": [{"id": 1,"fullPath": "BPM","droppedZipZone": False,"name": nome_arquivo,"newAttach": True,"description": nome_arquivo,"documentId": 0,"attachedUser": "Infra Automação","attachedActivity": "Aguardando Classificação","attachments": [{"attach": False,"principal": True,"fileName": nome_arquivo}],"hasOwnSubMenu": True,"enablePublish": False,"enableEdit": False,"enableEditContent": False,"fromUpload": True,"enableDownload": True,"hasMoreOptions": False,"iconClass": "fluigicon-file-upload","iconUrl": False,"colleagueId": admin_colleague_id}],"currentMovto": current_movto}
            
            # Log do payload completo
            import json
            payload_json = json.dumps(payload, indent=2, ensure_ascii=False)
            logger.info(f"[anexar_arquivo_chamado] Payload completo:{payload_json}")
            
            # Headers
            headers = {
                'Content-Type': 'application/json; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            logger.info(f"[anexar_arquivo_chamado] Headers: {headers}")
            
            # Faz requisição
            logger.info(f"[anexar_arquivo_chamado] Enviando requisição para: {url_save}")
            resposta = requests.post(
                url_save,
                json=payload,
                cookies=cookies_dict,
                headers=headers,
                timeout=30
            )
            
            if resposta.status_code == 200:
                try:
                    resultado = resposta.json()
                    
                    # Verifica se há erro na resposta
                    if resultado.get("content") == "ERROR" or resultado.get("message"):
                        mensagem_erro = resultado.get("message", {})
                        if isinstance(mensagem_erro, dict):
                            erro_msg = mensagem_erro.get("message", "Erro desconhecido")
                        else:
                            erro_msg = str(mensagem_erro)
                        logger.error(f"[anexar_arquivo_chamado] Erro retornado pelo Fluig: {erro_msg}")
                        logger.debug(f"[anexar_arquivo_chamado] Resposta completa: {resultado}")
                        return False
                    
                    # Verifica se anexou com sucesso
                    content = resultado.get("content", {})
                    if content and content.get("hasNewAttachment"):
                        logger.info(f"[anexar_arquivo_chamado] Arquivo anexado com sucesso ao chamado {process_instance_id}")
                        logger.debug(f"[anexar_arquivo_chamado] Resposta: {resultado}")
                        return True
                    else:
                        logger.warning(f"[anexar_arquivo_chamado] Resposta sem confirmação de anexo: {resultado}")
                        return True  # Assumir sucesso se status 200 e sem erro
                except Exception as e:
                    logger.error(f"[anexar_arquivo_chamado] Erro ao processar resposta JSON: {str(e)}")
                    return False
            else:
                logger.error(f"[anexar_arquivo_chamado] Erro ao anexar arquivo - Status: {resposta.status_code}, Resposta: {resposta.text[:500]}")
                return False
                
        except Exception as e:
            logger.error(f"[anexar_arquivo_chamado] Erro inesperado ao anexar arquivo: {str(e)}")
            import traceback
            logger.debug(f"[anexar_arquivo_chamado] Traceback: {traceback.format_exc()}")
            return False

    def listar_chamados_tasks(
        self,
        assignee: Optional[str] = None,
        status: str = "NOT_COMPLETED",
        sla_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 1000,
        order: str = "processInstanceId",
        cookies_list: Optional[List[Dict]] = None,
        usuario: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Lista chamados (tasks) usando o endpoint v2 /process-management/api/v2/tasks
        
        IMPORTANTE: Usa exclusivamente autenticação OAuth 1.0 (CK, CS, TK, TS)
        
        Args:
            assignee: ID do colleague (opcional, usa USER_COLLEAGUE_ID se não fornecido)
            status: Status das tarefas (padrão: 'NOT_COMPLETED')
            sla_status: Status do SLA (opcional, None para todos)
            page: Número da página (padrão: 1)
            page_size: Quantidade de registros por página (padrão: 1000)
            order: Campo para ordenação (padrão: 'processInstanceId')
            cookies_list: DEPRECATED - não é mais usado, mantido apenas para compatibilidade
            usuario: DEPRECATED - não é mais usado, mantido apenas para compatibilidade
        
        Returns:
            Dados JSON com lista de chamados (tasks) ou None
        """
        try:
            # Obtém assignee se não fornecido
            if not assignee:
                if self.ambiente.upper() == "QLD":
                    assignee = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                else:
                    assignee = ConfigEnvSetings.USER_COLLEAGUE_ID
                    
            if not assignee:
                logger.error(f"[listar_chamados_tasks] assignee não configurado para ambiente {self.ambiente}")
                return None
            
            logger.info(f"[listar_chamados_tasks] Usando assignee: {assignee} para ambiente {self.ambiente}")
            logger.info(f"[listar_chamados_tasks] Usando autenticação OAuth 1.0 (CK, CS, TK, TS)")
            
            # Usa URL base já configurada na instância
            parsed_url = urlparse(self.url_base)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Monta URL do endpoint v2
            url = f"{base_url}/process-management/api/v2/tasks"
            
            # Parâmetros da query
            params = {
                'assignee': assignee,
                'status': status,
                'page': page,
                'pageSize': page_size,
                'order': order
            }
            
            # Adiciona slaStatus apenas se fornecido
            if sla_status:
                params['slaStatus'] = sla_status
            
            logger.info(f"[listar_chamados_tasks] Fazendo requisição para {self.ambiente}...")
            logger.debug(f"[listar_chamados_tasks] URL: {url}")
            logger.debug(f"[listar_chamados_tasks] Params: {params}")
            
            # Usa autenticação OAuth 1.0 através do RequestsFluig
            response = self.requests.RequestTipoGET(url, params)
            
            logger.info(f"[listar_chamados_tasks] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    items = data.get('items', [])
                    has_next = data.get('hasNext', False)
                    logger.info(f"[listar_chamados_tasks] {len(items)} chamado(s) encontrado(s), hasNext: {has_next}")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"[listar_chamados_tasks] Erro ao decodificar JSON: {str(e)}")
                    logger.debug(f"[listar_chamados_tasks] Resposta: {response.text[:500]}")
                    return None
            else:
                logger.error(f"[listar_chamados_tasks] Erro na requisição - Status: {response.status_code}")
                logger.debug(f"[listar_chamados_tasks] Resposta: {response.text[:500]}")
                if response.status_code == 401:
                    logger.error("[listar_chamados_tasks] Erro de autenticação. Verifique as credenciais OAuth 1.0 (CK, CS, TK, TS)")
                return None
                
        except Exception as e:
            logger.error(f"[listar_chamados_tasks] Erro ao listar chamados: {str(e)}")
            import traceback
            logger.debug(f"[listar_chamados_tasks] Traceback: {traceback.format_exc()}")
            return None

    def obter_detalhes_chamado(
        self,
        process_instance_id: int,
        task_user_id: Optional[str] = None,
        cookies_list: Optional[List[Dict]] = None,
        usuario: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de um chamado do Fluig usando o endpoint oficial da API v2
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            task_user_id: (DEPRECADO - não usado mais, mantido para compatibilidade)
            cookies_list: (DEPRECADO - não usado mais, mantido para compatibilidade)
            usuario: (DEPRECADO - não usado mais, mantido para compatibilidade)
        
        Returns:
            Dados JSON com detalhes do chamado ou None
        """
        try:
            # Usa URL base já configurada na instância
            parsed_url = urlparse(self.url_base)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Endpoint oficial da API v2 do Fluig
            url = f"{base_url}/process-management/api/v2/requests/{process_instance_id}"
            
            # Parâmetros da query string
            parametros = {
                "expand": "formFields"
            }
            
            logger.info(f"[obter_detalhes_chamado] Buscando detalhes do chamado {process_instance_id}...")
            logger.debug(f"[obter_detalhes_chamado] URL: {url}")
            
            # Usa autenticação OAuth1 através do RequestsFluig
            response = self.requests.RequestTipoGET(url, parametros)
            
            logger.info(f"[obter_detalhes_chamado] Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Simplifica formFields: transforma array de {field, value} em dicionário simples
                    if "formFields" in data and isinstance(data["formFields"], list):
                        form_fields_dict = {}
                        for item in data["formFields"]:
                            if isinstance(item, dict) and "field" in item and "value" in item:
                                form_fields_dict[item["field"]] = item["value"]
                        data["formFields"] = form_fields_dict
                    
                    logger.info(f"[obter_detalhes_chamado] Detalhes obtidos com sucesso")
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"[obter_detalhes_chamado] Erro ao decodificar JSON: {str(e)}")
                    logger.debug(f"[obter_detalhes_chamado] Resposta: {response.text[:500]}")
                    return None
            else:
                logger.error(f"[obter_detalhes_chamado] Erro HTTP {response.status_code}")
                logger.error(f"[obter_detalhes_chamado] Resposta do servidor: {response.text[:500]}")
                
                if response.status_code in [401, 403]:
                    logger.warning("[obter_detalhes_chamado] Erro de autenticação. Verifique as credenciais OAuth1 (CK, CS, TK, TS)")
                elif response.status_code == 404:
                    logger.warning(f"[obter_detalhes_chamado] Chamado {process_instance_id} não encontrado")
                elif response.status_code == 500:
                    logger.warning(f"[obter_detalhes_chamado] Erro interno do servidor. Verifique se o chamado existe")
                
                return None
                
        except Exception as e:
            logger.error(f"[obter_detalhes_chamado] Erro inesperado: {str(e)}")
            return None