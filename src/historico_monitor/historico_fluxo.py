"""
Gerenciador de fluxo de histórico de chamados

Este módulo processa os itens do histórico baseado em regras configuráveis
definidas no arquivo de configuração de fluxo, gerando mensagens personalizadas
para o envio de emails.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import hashlib
import configparser
from src.utilitarios_centrais.logger import logger


class HistoricoFluxoManager:
    """
    Gerencia a lógica de fluxo do histórico de chamados
    
    Processa itens do histórico baseado em regras configuráveis para gerar
    mensagens personalizadas para emails.
    """
    
    def __init__(self, arquivo_config: Optional[str] = None):
        """
        Inicializa o gerenciador de fluxo
        
        Args:
            arquivo_config: Caminho para o arquivo de configuração de fluxo (.ini)
                          (padrão: src/historico_monitor/config/fluxo.ini)
        """
        if arquivo_config is None:
            current_dir = Path(__file__).parent
            arquivo_config = current_dir / "config" / "fluxo.ini"
        
        self.arquivo_config = Path(arquivo_config)
        self.regras = self._carregar_regras()
        logger.debug(f"[HistoricoFluxoManager] Inicializado - {len(self.regras)} regra(s) carregada(s)")
    
    def _carregar_regras(self) -> Dict[str, Dict[str, Any]]:
        """
        Carrega as regras do arquivo de configuração de fluxo (.ini)
        
        Returns:
            Dicionário com as regras organizadas por state_name e tipo
        """
        regras = {}
        
        if not self.arquivo_config.exists():
            logger.warning(f"[HistoricoFluxoManager] Arquivo de configuração não encontrado: {self.arquivo_config}")
            return regras
        
        try:
            config = configparser.ConfigParser()
            config.read(self.arquivo_config, encoding='utf-8')
            
            # Processa todas as seções
            for section_name in config.sections():
                section = config[section_name]
                
                # Determina o tipo de regra (state_name ou tipo)
                if section_name.startswith('state_name:'):
                    state_name = section_name.replace('state_name:', '')
                    regra_key = f"state_name:{state_name}"
                    # Obtém descricao_etapa se existir, caso contrário None
                    descricao_etapa = section.get('descricao_etapa', fallback=None)
                    if descricao_etapa:
                        descricao_etapa = descricao_etapa.strip()
                        if not descricao_etapa:
                            descricao_etapa = None
                    regras[regra_key] = {
                        'tipo': 'state_name',
                        'valor': state_name,
                        'pular': section.getboolean('pular', fallback=False),
                        'descricao_etapa': descricao_etapa,
                        'mostrar_observacao': section.getboolean('mostrar_observacao', fallback=False),
                        'mostrar_responsaveis': section.getboolean('mostrar_responsaveis', fallback=False)
                    }
                elif section_name.startswith('tipo:'):
                    tipo = section_name.replace('tipo:', '')
                    regra_key = f"tipo:{tipo}"
                    # Obtém descricao_etapa se existir, caso contrário None
                    descricao_etapa = section.get('descricao_etapa', fallback=None)
                    if descricao_etapa:
                        descricao_etapa = descricao_etapa.strip()
                        if not descricao_etapa:
                            descricao_etapa = None
                    regras[regra_key] = {
                        'tipo': 'tipo',
                        'valor': tipo,
                        'pular': section.getboolean('pular', fallback=False),
                        'descricao_etapa': descricao_etapa,
                        'mostrar_observacao': section.getboolean('mostrar_observacao', fallback=False),
                        'mostrar_responsaveis': section.getboolean('mostrar_responsaveis', fallback=False)
                    }
            
            logger.info(f"[HistoricoFluxoManager] {len(regras)} regra(s) carregada(s) do arquivo de configuração")
            return regras
            
        except Exception as e:
            logger.error(f"[HistoricoFluxoManager] Erro ao carregar regras de fluxo: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoFluxoManager] Traceback: {traceback.format_exc()}")
            return {}
    
    def processar_item(
        self,
        item: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Processa um item do histórico baseado nas regras de fluxo
        
        Args:
            item: Item do histórico (MOVEMENT, OBSERVATION, ATTACHMENT)
        
        Returns:
            Dicionário com informações processadas para o email ou None se deve ser pulado
        """
        tipo = item.get('type', 'UNKNOWN')
        state_name = item.get('state', {}).get('stateName', '')
        observation_description = item.get('observationDescription', '')
        usuario = item.get('user', {}).get('name', 'Sistema')
        data = item.get('date', '')
        
        # Regra especial: Ignora OBSERVATION com "Registro criado"
        if tipo == 'OBSERVATION' and observation_description and observation_description.strip() == 'Registro criado':
            logger.debug(f"[HistoricoFluxoManager] Item OBSERVATION 'Registro criado' ignorado (não será salvo nem enviado)")
            return None
        
        # Formata data
        try:
            from datetime import datetime
            if data:
                dt = datetime.fromisoformat(data.replace('Z', '+00:00'))
                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
            else:
                data_formatada = 'Data não disponível'
        except:
            data_formatada = data
        
        # Verifica regra por state_name primeiro (para MOVEMENT)
        if state_name:
            regra_key = f"state_name:{state_name}"
            if regra_key in self.regras:
                regra = self.regras[regra_key]
                
                # Se deve pular, retorna None
                if regra.get('pular', False):
                    logger.debug(f"[HistoricoFluxoManager] Item pulado por regra (state_name: {state_name})")
                    return None
                
                # Processa descrição da etapa
                descricao_etapa = regra.get('descricao_etapa')
                if descricao_etapa:
                    # Substitui placeholders
                    responsaveis = self._obter_responsaveis(item)
                    if responsaveis:
                        descricao_etapa = descricao_etapa.replace("'responsaveis'", responsaveis)
                    
                    # Substitui observation_description se necessário
                    if observation_description:
                        descricao_etapa = descricao_etapa.replace("'observation_description'", observation_description)
                    
                    return {
                        'tipo': tipo,
                        'state_name': state_name,
                        'descricao_principal': descricao_etapa,
                        'descricao_secundaria': '',
                        'mostrar_observacao': regra.get('mostrar_observacao', False),
                        'observation_description': observation_description if regra.get('mostrar_observacao', False) else '',
                        'mostrar_responsaveis': regra.get('mostrar_responsaveis', False),
                        'responsaveis': responsaveis if regra.get('mostrar_responsaveis', False) else '',
                        'usuario': usuario,
                        'data': data_formatada,
                        'eh_attachment': False,
                        'attachment_description': '',
                        'eh_imagem': False,
                        'cid_imagem': ''
                    }
        
        # Verifica regra por tipo
        regra_key = f"tipo:{tipo}"
        if regra_key in self.regras:
            regra = self.regras[regra_key]
            
            if regra.get('pular', False):
                logger.debug(f"[HistoricoFluxoManager] Item pulado por regra (tipo: {tipo})")
                return None
            
            # Processa ATTACHMENT
            if tipo == 'ATTACHMENT':
                attachment_description = item.get('attachmentDescription', 'Arquivo')
                extensao = attachment_description.lower().split('.')[-1] if '.' in attachment_description else ''
                tipos_imagem = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
                eh_imagem = extensao in tipos_imagem
                attachment_id = item.get('attachmentId', '')
                # Gera CID único baseado no attachment_id e nome do arquivo
                cid_base = f"{attachment_id}_{attachment_description}" if attachment_id else attachment_description
                cid_hash = hashlib.md5(cid_base.encode()).hexdigest()[:8]
                cid_imagem = f"anexo_{cid_hash}"
                
                return {
                    'tipo': tipo,
                    'state_name': state_name,
                    'descricao_principal': f"Anexo: {attachment_description}",
                    'descricao_secundaria': '',
                    'mostrar_observacao': False,
                    'observation_description': '',
                    'mostrar_responsaveis': False,
                    'responsaveis': '',
                    'usuario': usuario,
                    'data': data_formatada,
                    'eh_attachment': True,
                    'attachment_description': attachment_description,
                    'eh_imagem': eh_imagem,
                    'cid_imagem': cid_imagem
                }
            
            # Processa OBSERVATION
            elif tipo == 'OBSERVATION':
                return {
                    'tipo': tipo,
                    'state_name': state_name,
                    'descricao_principal': observation_description if observation_description else 'Observação',
                    'descricao_secundaria': '',
                    'mostrar_observacao': False,  # Já está na descrição principal
                    'observation_description': '',
                    'mostrar_responsaveis': False,
                    'responsaveis': '',
                    'usuario': usuario,
                    'data': data_formatada,
                    'eh_attachment': False,
                    'attachment_description': '',
                    'eh_imagem': False,
                    'cid_imagem': ''
                }
        
        # Se não encontrou regra específica, usa lógica padrão
        return self._processar_item_padrao(item, tipo, state_name, observation_description, usuario, data_formatada)
    
    def _processar_item_padrao(
        self,
        item: Dict[str, Any],
        tipo: str,
        state_name: str,
        observation_description: str,
        usuario: str,
        data_formatada: str
    ) -> Dict[str, Any]:
        """
        Processa item usando lógica padrão quando não há regra específica
        
        Args:
            item: Item do histórico
            tipo: Tipo do item
            state_name: Nome do estado
            observation_description: Descrição da observação
            usuario: Nome do usuário
            data_formatada: Data formatada
        
        Returns:
            Dicionário com informações processadas
        """
        if tipo == 'MOVEMENT':
            estado_origem = item.get('state', {}).get('stateName', '')
            estado_destino = item.get('targetState', {}).get('stateName', '')
            if estado_origem and estado_destino:
                descricao_principal = f"{estado_origem} → {estado_destino}"
            elif state_name:
                descricao_principal = state_name
            else:
                descricao_principal = observation_description if observation_description else 'Movimento'
            
            mostrar_obs = observation_description and not observation_description.startswith('Automatic Task:')
            
            return {
                'tipo': tipo,
                'state_name': state_name,
                'descricao_principal': descricao_principal,
                'descricao_secundaria': '',
                'mostrar_observacao': mostrar_obs,
                'observation_description': observation_description if mostrar_obs else '',
                'mostrar_responsaveis': False,
                'responsaveis': '',
                'usuario': usuario,
                'data': data_formatada,
                'eh_attachment': False,
                'attachment_description': '',
                'eh_imagem': False,
                'cid_imagem': ''
            }
        else:
            # Para outros tipos, retorna padrão
            return {
                'tipo': tipo,
                'state_name': state_name,
                'descricao_principal': state_name if state_name else 'Atualização',
                'descricao_secundaria': '',
                'mostrar_observacao': False,
                'observation_description': '',
                'mostrar_responsaveis': False,
                'responsaveis': '',
                'usuario': usuario,
                'data': data_formatada,
                'eh_attachment': False,
                'attachment_description': '',
                'eh_imagem': False,
                'cid_imagem': ''
            }
    
    def _obter_responsaveis(self, item: Dict[str, Any]) -> str:
        """
        Obtém o primeiro responsável de um item
        
        Args:
            item: Item do histórico
        
        Returns:
            String com o nome do primeiro responsável (apenas o primeiro)
        """
        responsaveis = item.get('chosenAssignees', [])
        if not responsaveis:
            return ''
        
        # Retorna apenas o primeiro responsável
        primeiro = responsaveis[0]
        nome = primeiro.get('name', '')
        return nome if nome else ''
    
    def processar_itens(
        self,
        itens: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Processa uma lista de itens do histórico
        
        Args:
            itens: Lista de itens do histórico
        
        Returns:
            Lista de itens processados (itens pulados são removidos)
        """
        itens_processados = []
        
        for item in itens:
            item_processado = self.processar_item(item)
            if item_processado:  # None significa que deve ser pulado
                itens_processados.append(item_processado)
        
        return itens_processados
