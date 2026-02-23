"""
Gerenciador de histórico de chamados usando ConfigParser

Este módulo gerencia o salvamento e leitura de históricos de chamados
abertos via email, utilizando ConfigParser para armazenar os dados.
Agora usa apenas Google Drive (não salva arquivos locais)
"""
import json
import io
import os
from configparser import ConfigParser
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.utilitarios_centrais.logger import logger


class HistoricoManager:
    """
    Gerencia o salvamento e leitura de históricos de chamados usando ConfigParser
    
    Os históricos são salvos no Google Drive na subpasta 'historicos/'
    com o nome: historico_{process_instance_id}.ini
    Não salva mais arquivos localmente
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa o HistoricoManager
        
        Args:
            base_path: Caminho base (mantido para compatibilidade, mas não usado)
        """
        # Não cria mais diretório local
        logger.info(f"[HistoricoManager] Inicializado - Usando Google Drive para armazenamento")
    
    def _get_nome_arquivo_historico(self, process_instance_id: int) -> str:
        """
        Retorna o nome do arquivo de histórico para um chamado
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            
        Returns:
            Nome do arquivo de histórico
        """
        return f"historico_{process_instance_id}.ini"
    
    def _ler_config_do_drive(self, nome_arquivo: str) -> Optional[ConfigParser]:
        """
        Lê configuração do histórico do Google Drive
        
        Args:
            nome_arquivo: Nome do arquivo no Drive
            
        Returns:
            ConfigParser com os dados ou None se não encontrado
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug(f"[HistoricoManager] Google Drive não disponível - não é possível ler histórico")
                return None
            
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo, subpasta='historicos')
            
            if not conteudo:
                return None
            
            config = ConfigParser()
            config.read_string(conteudo)
            return config
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao ler histórico do Drive: {str(e)}")
            return None
    
    def _salvar_config_no_drive(self, config: ConfigParser, nome_arquivo: str) -> bool:
        """
        Salva configuração do histórico no Google Drive
        
        Args:
            config: ConfigParser com os dados
            nome_arquivo: Nome do arquivo no Drive
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.error(f"[HistoricoManager] Google Drive não disponível - não é possível salvar histórico")
                return False
            
            # Converte configuração para string
            output = io.StringIO()
            config.write(output)
            conteudo = output.getvalue()
            
            # Salva no Drive
            return drive_manager.salvar_config_no_drive(conteudo, nome_arquivo, subpasta='historicos')
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao salvar histórico no Drive: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoManager] Traceback: {traceback.format_exc()}")
            return False
    
    def _email_excluido_do_historico(self, email: Optional[str]) -> bool:
        """
        Verifica se um email está na lista de exclusão do monitoramento de histórico
        
        Args:
            email: Email a verificar
            
        Returns:
            True se o email deve ser excluído, False caso contrário
        """
        if not email:
            return False
        
        try:
            from src.modelo_dados.modelo_settings import ConfigEnvSetings
            from src.configs.config_manager import get_config_manager_gerais
            
            # Tenta obter da configuração geral primeiro (prioridade)
            config_manager = get_config_manager_gerais()
            configs = config_manager.carregar_configuracao()
            exclude_emails_str = configs.get('historico_exclude_emails', '')
            
            # Se não encontrou na configuração, tenta do .env
            if not exclude_emails_str:
                exclude_emails_str = getattr(ConfigEnvSetings, 'HISTORICO_EXCLUDE_EMAILS', '')
            
            if not exclude_emails_str:
                return False
            
            # Normaliza email para comparação
            email_normalizado = email.strip().lower()
            
            # Divide a lista e verifica cada email
            emails_excluidos = [e.strip().lower() for e in exclude_emails_str.split(',') if e.strip()]
            
            return email_normalizado in emails_excluidos
            
        except Exception as e:
            logger.debug(f"[HistoricoManager] Erro ao verificar email excluído: {str(e)}")
            return False
    
    def salvar_historico(
        self,
        process_instance_id: int,
        historico_data: Dict[str, Any],
        ambiente: str = "PRD",
        email_remetente: Optional[str] = None
    ) -> bool:
        """
        Salva o histórico de um chamado em arquivo .ini usando ConfigParser
        Não salva se o email do remetente estiver na lista de exclusão
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            historico_data: Dicionário com os dados do histórico (items, hasNext, etc.)
            ambiente: Ambiente do Fluig (PRD ou QLD)
            email_remetente: Email do remetente para notificações (opcional)
            
        Returns:
            True se salvou com sucesso, False caso contrário (ou se email está excluído)
        """
        # Verifica se o email está na lista de exclusão
        if self._email_excluido_do_historico(email_remetente):
            logger.info(f"[HistoricoManager] Email {email_remetente} está na lista de exclusão - histórico do chamado {process_instance_id} não será monitorado")
            return False
        
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            # Cria ConfigParser
            config = ConfigParser()
            
            # Se arquivo já existe no Drive, carrega para preservar outras seções
            config_existente = self._ler_config_do_drive(nome_arquivo)
            if config_existente:
                # Copia todas as seções do config existente
                for secao in config_existente.sections():
                    if secao not in config:
                        config.add_section(secao)
                    for opcao in config_existente.options(secao):
                        config.set(secao, opcao, config_existente.get(secao, opcao))
            
            # Seção principal com metadados
            if 'METADADOS' not in config:
                config.add_section('METADADOS')
            
            config.set('METADADOS', 'process_instance_id', str(process_instance_id))
            config.set('METADADOS', 'ambiente', ambiente)
            config.set('METADADOS', 'data_criacao', datetime.now().isoformat())
            config.set('METADADOS', 'data_ultima_atualizacao', datetime.now().isoformat())
            config.set('METADADOS', 'total_items', str(len(historico_data.get('items', []))))
            config.set('METADADOS', 'has_next', str(historico_data.get('hasNext', False)))
            
            # Salva email do remetente se fornecido
            if email_remetente:
                config.set('METADADOS', 'email_remetente', email_remetente)
            
            # Salva cada item do histórico em uma seção separada
            items = historico_data.get('items', [])
            
            # Inverte a ordem dos itens para que os mais antigos recebam números menores
            # e os mais recentes recebam números maiores (ITEM_1 = mais antigo, ITEM_N = mais recente)
            items = list(reversed(items))
            
            # Remove seções antigas de itens que não existem mais (para limpar itens removidos)
            secoes_existentes = [sec for sec in config.sections() if sec.startswith('ITEM_')]
            for secao in secoes_existentes:
                try:
                    item_num = int(secao.replace('ITEM_', ''))
                    if item_num > len(items):
                        config.remove_section(secao)
                except ValueError:
                    continue
            
            # Salva cada item em sua própria seção
            for idx, item in enumerate(items):
                # Regra especial: Ignora OBSERVATION com "Registro criado"
                tipo = item.get('type', 'UNKNOWN')
                observation_description = item.get('observationDescription', '')
                if tipo == 'OBSERVATION' and observation_description and observation_description.strip() == 'Registro criado':
                    logger.debug(f"[HistoricoManager] Item OBSERVATION 'Registro criado' ignorado (não será salvo)")
                    continue
                
                secao_item = f'ITEM_{idx + 1}'
                if secao_item not in config:
                    config.add_section(secao_item)
                
                # Informações básicas do item
                data_item = item.get('date', '')
                usuario = item.get('user', {}).get('name', 'Sistema')
                usuario_code = item.get('user', {}).get('code', '')
                
                config.set(secao_item, 'tipo', tipo)
                config.set(secao_item, 'data', data_item)
                config.set(secao_item, 'usuario', usuario)
                config.set(secao_item, 'usuario_code', usuario_code)
                
                # Obtém stateName (presente em todos os tipos)
                state_name = item.get('state', {}).get('stateName', '')
                if state_name:
                    config.set(secao_item, 'state_name', state_name)
                
                # Obtém observationDescription (pode aparecer em qualquer tipo)
                observation_description = item.get('observationDescription')
                #logger.info(f"[HistoricoManager] Observation Description: {observation_description}")
                if observation_description and observation_description.strip():
                    config.set(secao_item, 'observation_description', observation_description)
                elif config.has_option(secao_item, 'observation_description'):
                    # Remove observation_description se não existir mais no item
                    config.remove_option(secao_item, 'observation_description')
                
                # Informações específicas por tipo
                if tipo == 'OBSERVATION':
                    config.set(secao_item, 'observation_id', str(item.get('observationId', '')))
                    # Remove descricao se existir (duplicado de observation_description)
                    if config.has_option(secao_item, 'descricao'):
                        config.remove_option(secao_item, 'descricao')
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                elif tipo == 'ATTACHMENT':
                    config.set(secao_item, 'attachment_id', str(item.get('attachmentId', '')))
                    config.set(secao_item, 'descricao', item.get('attachmentDescription', ''))
                    config.set(secao_item, 'attachment_version', str(item.get('attachmentVersion', '')))
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                elif tipo == 'MOVEMENT':
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                    estado_origem = item.get('state', {}).get('stateName', '')
                    estado_destino = item.get('targetState', {}).get('stateName', '')
                    config.set(secao_item, 'estado_origem', estado_origem)
                    config.set(secao_item, 'estado_destino', estado_destino)
                    # Remove descricao se existir (duplicado de observation_description)
                    if config.has_option(secao_item, 'descricao'):
                        config.remove_option(secao_item, 'descricao')
                    
                    # Responsáveis (chosenAssignees)
                    responsaveis = item.get('chosenAssignees', [])
                    responsaveis_nomes = [r.get('name', '') for r in responsaveis if r.get('name')]
                    if responsaveis_nomes:
                        config.set(secao_item, 'responsaveis', ', '.join(responsaveis_nomes))
                
                # Flag de email (se não existir, cria como false para novos itens)
                if not config.has_option(secao_item, 'email_enviado'):
                    config.set(secao_item, 'email_enviado', 'false')
            
            # Salva dados completos em uma seção única
            if 'DADOS_COMPLETOS' not in config:
                config.add_section('DADOS_COMPLETOS')
            
            historico_json = json.dumps(historico_data, ensure_ascii=False, indent=2)
            config.set('DADOS_COMPLETOS', 'historico_json', historico_json)
            
            # Salva no Google Drive
            sucesso = self._salvar_config_no_drive(config, nome_arquivo)
            
            if sucesso:
                logger.info(f"[HistoricoManager] Histórico do chamado {process_instance_id} salvo com sucesso no Drive")
                return True
            else:
                logger.error(f"[HistoricoManager] Falha ao salvar histórico do chamado {process_instance_id} no Drive")
                return False
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao salvar histórico do chamado {process_instance_id}: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoManager] Traceback: {traceback.format_exc()}")
            return False
    
    def ler_historico(self, process_instance_id: int) -> Optional[Dict[str, Any]]:
        """
        Lê o histórico de um chamado do arquivo .ini
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            
        Returns:
            Dicionário com os dados do histórico ou None se não encontrado
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            config = self._ler_config_do_drive(nome_arquivo)
            
            if not config:
                logger.debug(f"[HistoricoManager] Arquivo de histórico não encontrado no Drive: {nome_arquivo}")
                return None
            
            if 'DADOS_COMPLETOS' not in config:
                logger.warning(f"[HistoricoManager] Seção DADOS_COMPLETOS não encontrada no arquivo {nome_arquivo}")
                return None
            
            if not config.has_option('DADOS_COMPLETOS', 'historico_json'):
                logger.warning(f"[HistoricoManager] Campo historico_json não encontrado na seção DADOS_COMPLETOS do arquivo {nome_arquivo}")
                return None
            
            # Lê JSON do histórico
            historico_json = config.get('DADOS_COMPLETOS', 'historico_json')
            historico_data = json.loads(historico_json)
            
            logger.debug(f"[HistoricoManager] Histórico do chamado {process_instance_id} lido com sucesso")
            return historico_data
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao ler histórico do chamado {process_instance_id}: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoManager] Traceback: {traceback.format_exc()}")
            return None
    
    def obter_metadados(self, process_instance_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém apenas os metadados do histórico (sem os dados completos)
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            
        Returns:
            Dicionário com metadados ou None se não encontrado
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            config = self._ler_config_do_drive(nome_arquivo)
            
            if not config:
                return None
            
            if 'METADADOS' not in config:
                return None
            
            metadados = {
                'process_instance_id': config.getint('METADADOS', 'process_instance_id'),
                'ambiente': config.get('METADADOS', 'ambiente'),
                'data_criacao': config.get('METADADOS', 'data_criacao'),
                'data_ultima_atualizacao': config.get('METADADOS', 'data_ultima_atualizacao'),
                'total_items': config.getint('METADADOS', 'total_items'),
                'has_next': config.getboolean('METADADOS', 'has_next')
            }
            
            return metadados
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao obter metadados do chamado {process_instance_id}: {str(e)}")
            return None
    
    def listar_chamados_monitorados(self) -> List[int]:
        """
        Lista todos os chamados que têm histórico salvo no Google Drive
        
        Returns:
            Lista de process_instance_id dos chamados monitorados
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug(f"[HistoricoManager] Google Drive não disponível - não é possível listar chamados")
                return []
            
            chamados = []
            
            # Lista todos os arquivos historico_*.ini no Drive
            arquivos = drive_manager.listar_configs(subpasta='historicos')
            
            for arquivo_info in arquivos:
                try:
                    nome_arquivo = arquivo_info['nome']
                    if nome_arquivo.startswith('historico_') and nome_arquivo.endswith('.ini'):
                    # Extrai process_instance_id do nome do arquivo
                        process_id_str = nome_arquivo.replace("historico_", "").replace(".ini", "")
                    process_id = int(process_id_str)
                    chamados.append(process_id)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"[HistoricoManager] Não foi possível extrair process_instance_id de {arquivo_info.get('nome', '')}: {str(e)}")
                    continue
            
            logger.debug(f"[HistoricoManager] Encontrados {len(chamados)} chamado(s) monitorado(s) no Drive")
            return sorted(chamados)
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao listar chamados monitorados: {str(e)}")
            return []
    
    def atualizar_historico(
        self,
        process_instance_id: int,
        novo_historico: Dict[str, Any],
        ambiente: str = "PRD"
    ) -> bool:
        """
        Atualiza o histórico de um chamado existente
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            novo_historico: Dicionário com os novos dados do histórico
            ambiente: Ambiente do Fluig (PRD ou QLD)
            
        Returns:
            True se atualizou com sucesso, False caso contrário
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            # Carrega configuração existente do Drive
            config = self._ler_config_do_drive(nome_arquivo)
            
            # Se arquivo não existe, cria novo
            if not config:
                logger.info(f"[HistoricoManager] Arquivo não existe no Drive, criando novo histórico para chamado {process_instance_id}")
                # Obtém email do remetente se existir (não há como obter aqui, será None)
                return self.salvar_historico(process_instance_id, novo_historico, ambiente)
            
            # Config já carregado do Drive
            
            # Preserva email do remetente se existir
            email_remetente = None
            if 'METADADOS' in config and config.has_option('METADADOS', 'email_remetente'):
                email_remetente = config.get('METADADOS', 'email_remetente')
            
            # Atualiza metadados
            if 'METADADOS' not in config:
                config.add_section('METADADOS')
            
            config.set('METADADOS', 'data_ultima_atualizacao', datetime.now().isoformat())
            config.set('METADADOS', 'total_items', str(len(novo_historico.get('items', []))))
            config.set('METADADOS', 'has_next', str(novo_historico.get('hasNext', False)))
            
            # Preserva email do remetente
            if email_remetente:
                config.set('METADADOS', 'email_remetente', email_remetente)
            
            # Atualiza itens do histórico (preservando flags de email existentes)
            items = novo_historico.get('items', [])
            
            # Inverte a ordem dos itens para que os mais antigos recebam números menores
            # e os mais recentes recebam números maiores (ITEM_1 = mais antigo, ITEM_N = mais recente)
            items = list(reversed(items))
            
            # Remove seções antigas de itens que não existem mais
            secoes_existentes = [sec for sec in config.sections() if sec.startswith('ITEM_')]
            for secao in secoes_existentes:
                try:
                    item_num = int(secao.replace('ITEM_', ''))
                    if item_num > len(items):
                        config.remove_section(secao)
                except ValueError:
                    continue
            
            # Atualiza cada item, preservando flag de email se existir
            for idx, item in enumerate(items):
                # Regra especial: Ignora OBSERVATION com "Registro criado"
                tipo = item.get('type', 'UNKNOWN')
                observation_description = item.get('observationDescription', '')
                if tipo == 'OBSERVATION' and observation_description and observation_description.strip() == 'Registro criado':
                    logger.debug(f"[HistoricoManager] Item OBSERVATION 'Registro criado' ignorado na atualização (não será salvo)")
                    continue
                
                secao_item = f'ITEM_{idx + 1}'
                if secao_item not in config:
                    config.add_section(secao_item)
                
                # Preserva flag de email se já existir
                email_enviado_existente = False
                if config.has_option(secao_item, 'email_enviado'):
                    email_enviado_existente = config.getboolean(secao_item, 'email_enviado', fallback=False)
                
                # Informações básicas do item
                data_item = item.get('date', '')
                usuario = item.get('user', {}).get('name', 'Sistema')
                usuario_code = item.get('user', {}).get('code', '')
                
                config.set(secao_item, 'tipo', tipo)
                config.set(secao_item, 'data', data_item)
                config.set(secao_item, 'usuario', usuario)
                config.set(secao_item, 'usuario_code', usuario_code)
                
                # Obtém stateName (presente em todos os tipos)
                state_name = item.get('state', {}).get('stateName', '')
                if state_name:
                    config.set(secao_item, 'state_name', state_name)
                
                # Obtém observationDescription (pode aparecer em qualquer tipo)
                observation_description = item.get('observationDescription')
                #logger.info(f"[HistoricoManager] Observation Description: {observation_description}")
                if observation_description and observation_description.strip():
                    config.set(secao_item, 'observation_description', observation_description)
                elif config.has_option(secao_item, 'observation_description'):
                    # Remove observation_description se não existir mais no item
                    config.remove_option(secao_item, 'observation_description')
                
                # Informações específicas por tipo
                if tipo == 'OBSERVATION':
                    config.set(secao_item, 'observation_id', str(item.get('observationId', '')))
                    # Remove descricao se existir (duplicado de observation_description)
                    if config.has_option(secao_item, 'descricao'):
                        config.remove_option(secao_item, 'descricao')
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                elif tipo == 'ATTACHMENT':
                    config.set(secao_item, 'attachment_id', str(item.get('attachmentId', '')))
                    config.set(secao_item, 'descricao', item.get('attachmentDescription', ''))
                    config.set(secao_item, 'attachment_version', str(item.get('attachmentVersion', '')))
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                elif tipo == 'MOVEMENT':
                    config.set(secao_item, 'movement_sequence', str(item.get('movementSequence', '')))
                    estado_origem = item.get('state', {}).get('stateName', '')
                    estado_destino = item.get('targetState', {}).get('stateName', '')
                    config.set(secao_item, 'estado_origem', estado_origem)
                    config.set(secao_item, 'estado_destino', estado_destino)
                    # Remove descricao se existir (duplicado de observation_description)
                    if config.has_option(secao_item, 'descricao'):
                        config.remove_option(secao_item, 'descricao')
                    
                    # Responsáveis (chosenAssignees)
                    responsaveis = item.get('chosenAssignees', [])
                    responsaveis_nomes = [r.get('name', '') for r in responsaveis if r.get('name')]
                    if responsaveis_nomes:
                        config.set(secao_item, 'responsaveis', ', '.join(responsaveis_nomes))
                    elif config.has_option(secao_item, 'responsaveis'):
                        # Remove responsáveis se não existirem mais
                        config.remove_option(secao_item, 'responsaveis')
                
                # Preserva ou cria flag de email
                if not config.has_option(secao_item, 'email_enviado'):
                    config.set(secao_item, 'email_enviado', 'false')
                else:
                    # Mantém valor existente
                    config.set(secao_item, 'email_enviado', str(email_enviado_existente).lower())
            
            # Salva dados completos em uma seção única
            if 'DADOS_COMPLETOS' not in config:
                config.add_section('DADOS_COMPLETOS')
            
            historico_json = json.dumps(novo_historico, ensure_ascii=False, indent=2)
            config.set('DADOS_COMPLETOS', 'historico_json', historico_json)
            
            # Salva no Google Drive
            sucesso = self._salvar_config_no_drive(config, nome_arquivo)
            
            if sucesso:
                logger.info(f"[HistoricoManager] Histórico do chamado {process_instance_id} atualizado com sucesso no Drive")
                return True
            else:
                logger.error(f"[HistoricoManager] Falha ao atualizar histórico do chamado {process_instance_id} no Drive")
                return False
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao atualizar histórico do chamado {process_instance_id}: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoManager] Traceback: {traceback.format_exc()}")
            return False
    
    def comparar_historicos(
        self,
        historico_antigo: Dict[str, Any],
        historico_novo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compara dois históricos e identifica diferenças
        
        Args:
            historico_antigo: Histórico anterior
            historico_novo: Histórico novo
            
        Returns:
            Dicionário com informações sobre as diferenças:
            - tem_atualizacoes: bool
            - novos_items: Lista de novos itens
            - total_items_antigo: int
            - total_items_novo: int
        """
        try:
            items_antigos = historico_antigo.get('items', [])
            items_novos = historico_novo.get('items', [])
            
            total_antigo = len(items_antigos)
            total_novo = len(items_novos)
            
            # Se o total aumentou, há novos itens
            # A API do Fluig retorna os itens mais recentes primeiro, então os novos itens
            # são os primeiros da lista (índices 0 até total_novo - total_antigo - 1)
            if total_novo > total_antigo:
                quantidade_novos = total_novo - total_antigo
                novos_items = items_novos[:quantidade_novos]
                return {
                    'tem_atualizacoes': True,
                    'novos_items': novos_items,
                    'total_items_antigo': total_antigo,
                    'total_items_novo': total_novo,
                    'quantidade_novos': quantidade_novos
                }
            
            # Compara item por item para detectar mudanças
            # (pode haver mudanças mesmo sem aumento no total)
            if total_antigo != total_novo:
                return {
                    'tem_atualizacoes': True,
                    'novos_items': [],
                    'total_items_antigo': total_antigo,
                    'total_items_novo': total_novo,
                    'quantidade_novos': 0
                }
            
            # Compara conteúdo dos itens (pode haver atualizações em itens existentes)
            # Por simplicidade, consideramos que se os totais são iguais, não há atualizações
            # (mas pode ser melhorado para comparar conteúdo)
            return {
                'tem_atualizacoes': False,
                'novos_items': [],
                'total_items_antigo': total_antigo,
                'total_items_novo': total_novo,
                'quantidade_novos': 0
            }
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao comparar históricos: {str(e)}")
            return {
                'tem_atualizacoes': False,
                'novos_items': [],
                'total_items_antigo': 0,
                'total_items_novo': 0,
                'quantidade_novos': 0,
                'erro': str(e)
            }

    def obter_email_remetente(self, process_instance_id: int) -> Optional[str]:
        """
        Obtém o email do remetente salvo nos metadados do Google Drive
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            
        Returns:
            Email do remetente ou None se não encontrado
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            config = self._ler_config_do_drive(nome_arquivo)
            
            if config and 'METADADOS' in config and config.has_option('METADADOS', 'email_remetente'):
                return config.get('METADADOS', 'email_remetente')
            return None
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao obter email do remetente: {str(e)}")
            return None
    
    def marcar_itens_como_enviados(
        self,
        process_instance_id: int,
        indices_items: List[int]
    ) -> bool:
        """
        Marca itens do histórico como já enviados por email
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            indices_items: Lista de índices dos itens que foram enviados (baseado na posição no array, 0-indexed)
            
        Returns:
            True se marcou com sucesso, False caso contrário
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            config = self._ler_config_do_drive(nome_arquivo)
            
            if not config:
                logger.warning(f"[HistoricoManager] Arquivo não existe no Drive para marcar itens como enviados: {nome_arquivo}")
                return False
            
            # Os itens são salvos invertidos (mais antigo = ITEM_1, mais recente = ITEM_N)
            # Então precisamos converter o índice original para o índice invertido
            # Obtém o total de itens do metadado ou conta as seções ITEM_*
            total_items = 0
            if 'METADADOS' in config and config.has_option('METADADOS', 'total_items'):
                total_items = config.getint('METADADOS', 'total_items')
            else:
                # Fallback: conta as seções ITEM_* e pega o maior número
                secoes_item = [sec for sec in config.sections() if sec.startswith('ITEM_')]
                if secoes_item:
                    numeros = []
                    for sec in secoes_item:
                        try:
                            num = int(sec.replace('ITEM_', ''))
                            numeros.append(num)
                        except ValueError:
                            continue
                    total_items = max(numeros) if numeros else len(secoes_item)
            
            if total_items == 0:
                logger.warning(f"[HistoricoManager] Não foi possível determinar o total de itens para chamado {process_instance_id}")
                return False
            
            # Marca cada item como enviado
            # Converte índice original (da API) para índice invertido (no arquivo)
            for indice_original in indices_items:
                # idx_invertido = total_items - 1 - idx_original
                indice_invertido = total_items - 1 - indice_original
                secao_item = f'ITEM_{indice_invertido + 1}'
                if config.has_section(secao_item):
                    config.set(secao_item, 'email_enviado', 'true')
                else:
                    logger.warning(f"[HistoricoManager] Seção {secao_item} não encontrada para marcar como enviado (índice original: {indice_original}, total_items: {total_items})")
            
            # Salva no Google Drive
            sucesso = self._salvar_config_no_drive(config, nome_arquivo)
            
            if sucesso:
                logger.debug(f"[HistoricoManager] {len(indices_items)} item(ns) marcado(s) como enviado(s) para chamado {process_instance_id}")
                return True
            else:
                logger.error(f"[HistoricoManager] Falha ao salvar histórico atualizado no Drive")
                return False
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao marcar itens como enviados: {str(e)}")
            return False
    
    def obter_itens_nao_enviados(
        self,
        process_instance_id: int,
        historico_completo: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Obtém todos os itens do histórico que ainda não foram enviados por email
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            historico_completo: Dicionário com o histórico completo (items, hasNext, etc.)
            
        Returns:
            Lista de itens que ainda não foram enviados (com email_enviado = false)
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            config = self._ler_config_do_drive(nome_arquivo)
            
            if not config:
                # Se arquivo não existe no Drive, todos os itens são novos e não foram enviados
                return historico_completo.get('items', [])
            
            items = historico_completo.get('items', [])
            total_items = len(items)
            itens_nao_enviados = []
            
            # Os itens são salvos invertidos (mais antigo = ITEM_1, mais recente = ITEM_N)
            # Então precisamos inverter a ordem para fazer a correspondência correta
            items_invertidos = list(reversed(items))
            
            # Verifica cada item pela sua seção
            for idx, item in enumerate(items_invertidos):
                secao_item = f'ITEM_{idx + 1}'
                
                # Se a seção não existe ou email_enviado é false, adiciona à lista
                if not config.has_section(secao_item):
                    # Item novo, não foi enviado
                    itens_nao_enviados.append(item)
                else:
                    # Verifica flag de email
                    email_enviado = config.getboolean(secao_item, 'email_enviado', fallback=False)
                    if not email_enviado:
                        itens_nao_enviados.append(item)
            
            # Retorna os itens na ordem original (mais recentes primeiro)
            # Inverte novamente para manter a ordem original da API
            return list(reversed(itens_nao_enviados))
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao obter itens não enviados: {str(e)}")
            # Em caso de erro, retorna todos os itens
            return historico_completo.get('items', [])
    
    def _itens_iguais(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """
        Compara dois itens do histórico para verificar se são iguais
        
        Args:
            item1: Primeiro item
            item2: Segundo item
            
        Returns:
            True se são iguais, False caso contrário
        """
        # Compara por tipo e ID único
        tipo1 = item1.get('type')
        tipo2 = item2.get('type')
        
        if tipo1 != tipo2:
            return False
        
        # Compara por ID específico do tipo
        if tipo1 == 'OBSERVATION':
            return item1.get('observationId') == item2.get('observationId')
        elif tipo1 == 'ATTACHMENT':
            return item1.get('attachmentId') == item2.get('attachmentId')
        elif tipo1 == 'MOVEMENT':
            # Para MOVEMENT, compara por movementSequence e data
            return (item1.get('movementSequence') == item2.get('movementSequence') and
                    item1.get('date') == item2.get('date'))
        
        return False
    
    def obter_indices_itens_nao_enviados(
        self,
        process_instance_id: int,
        historico_completo: Dict[str, Any]
    ) -> List[int]:
        """
        Obtém os índices (0-indexed) dos itens que ainda não foram enviados por email
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            historico_completo: Dicionário com o histórico completo
            
        Returns:
            Lista de índices (0-indexed) dos itens não enviados
        """
        try:
            nome_arquivo = self._get_nome_arquivo_historico(process_instance_id)
            
            config = self._ler_config_do_drive(nome_arquivo)
            
            if not config:
                # Se arquivo não existe no Drive, todos os itens são novos
                return list(range(len(historico_completo.get('items', []))))
            
            items = historico_completo.get('items', [])
            total_items = len(items)
            indices_nao_enviados = []
            
            # Os itens são salvos invertidos (mais antigo = ITEM_1, mais recente = ITEM_N)
            # Então precisamos inverter a ordem para fazer a correspondência correta
            items_invertidos = list(reversed(items))
            
            # Verifica cada item pela sua seção (na ordem invertida)
            for idx_invertido, item in enumerate(items_invertidos):
                secao_item = f'ITEM_{idx_invertido + 1}'
                
                # Calcula o índice original (antes da inversão)
                # idx_invertido = total_items - 1 - idx_original
                # idx_original = total_items - 1 - idx_invertido
                idx_original = total_items - 1 - idx_invertido
                
                # Se a seção não existe ou email_enviado é false, adiciona o índice original
                if not config.has_section(secao_item):
                    # Item novo, não foi enviado
                    indices_nao_enviados.append(idx_original)
                else:
                    # Verifica flag de email
                    email_enviado = config.getboolean(secao_item, 'email_enviado', fallback=False)
                    if not email_enviado:
                        indices_nao_enviados.append(idx_original)
            
            return indices_nao_enviados
            
        except Exception as e:
            logger.error(f"[HistoricoManager] Erro ao obter índices dos itens não enviados: {str(e)}")
            return []