"""
Gerenciador de configurações usando configparser
Salva e carrega configurações da aba Personalizar Chamado
Agora usa apenas Google Drive (não salva arquivos locais)
"""
import configparser
import io
import os
from pathlib import Path
from typing import Optional, Dict
from src.utilitarios_centrais.logger import logger

# Caminho do arquivo de configuração
CONFIG_FILE = Path(__file__).parent / "personalizar_chamado.ini"


class ConfigManager:
    """Gerencia as configurações de personalização de chamados"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Inicializa o gerenciador de configurações
        
        Args:
            config_file: Caminho do arquivo de configuração (opcional)
        """
        self.config_file = config_file or CONFIG_FILE
        self.config = configparser.ConfigParser()
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """Garante que o arquivo de configuração existe no Drive (não cria localmente)"""
        # Não cria arquivo local - apenas verifica se existe no Drive
        pass
    
    def _load_config(self):
        """Carrega o arquivo de configuração do Google Drive"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug("[ConfigManager] Google Drive não disponível - usando configuração vazia")
                return
            
            nome_arquivo = self.config_file.name
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo)
            
            if conteudo:
                self.config.read_string(conteudo)
            else:
                logger.debug(f"[ConfigManager] Arquivo '{nome_arquivo}' não encontrado no Drive")
        except Exception as e:
            logger.debug(f"[ConfigManager] Erro ao carregar do Drive: {str(e)}")
    
    def _save_config(self):
        """Salva o arquivo de configuração no Google Drive (não salva localmente)"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.error("[ConfigManager] Google Drive não disponível - não é possível salvar configuração")
                return
            
            nome_arquivo = self.config_file.name
            
            # Converte configuração para string
            output = io.StringIO()
            self.config.write(output)
            conteudo = output.getvalue()
            
            # Salva no Drive
            drive_manager.salvar_config_no_drive(conteudo, nome_arquivo)
            
        except Exception as e:
            logger.error(f"[ConfigManager] Erro ao salvar configuração no Drive: {str(e)}")
            import traceback
            logger.debug(f"[ConfigManager] Traceback: {traceback.format_exc()}")
    
    def _normalizar_email_secao(self, email: str) -> str:
        """
        Normaliza o email para ser usado como nome de seção no INI
        Substitui caracteres especiais que não são permitidos em nomes de seção
        
        Args:
            email: Email do usuário
            
        Returns:
            Email normalizado para uso como nome de seção
        """
        # ConfigParser permite @ e . em nomes de seção, mas vamos garantir que está limpo
        return email.strip().lower()
    
    def salvar_configuracao(
        self,
        email_solicitante: str,
        usuario_responsavel: Optional[str] = None,
        servico_id: Optional[str] = None,
        servico: Optional[str] = None,
        ds_grupo_servico: Optional[str] = None,
        item_servico: Optional[str] = None,
        urg_alta: Optional[str] = None,
        urg_media: Optional[str] = None,
        urg_baixa: Optional[str] = None,
        ds_resp_servico: Optional[str] = None,
        ds_tipo: Optional[str] = None,
        ds_urgencia: Optional[str] = None,
        equipe_responsavel: Optional[str] = None,
        status: Optional[str] = None,
        solicitante: Optional[str] = None
    ) -> bool:
        """
        Salva as configurações de personalização de chamado (configurações globais)
        Usa o email_solicitante do campo do formulário como identificador
        
        Args:
            email_solicitante: Email solicitante para personalização (usado como identificador da seção)
            usuario_responsavel: Usuário responsável pelo chamado
            servico_id: ID do serviço selecionado
            servico: Nome do serviço
            ds_grupo_servico: Grupo de serviço
            item_servico: Item de serviço
            urg_alta: Urgência alta
            urg_media: Urgência média
            urg_baixa: Urgência baixa
            ds_resp_servico: Responsável pelo serviço
            ds_tipo: Tipo de chamado
            ds_urgencia: Urgência
            equipe_responsavel: Equipe responsável
            status: Status do chamado
            solicitante: Solicitante
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            if not email_solicitante or not email_solicitante.strip():
                print("Erro: email_solicitante é obrigatório para identificar a configuração")
                return False
            
            self._load_config()
            
            # Normaliza o email para usar como nome de seção
            secao_nome = self._normalizar_email_secao(email_solicitante)
            
            # Cria a seção se não existir
            if secao_nome not in self.config:
                self.config[secao_nome] = {}
            
            section = self.config[secao_nome]
            
            # Salva o email_solicitante como identificador (mantém 'email' para compatibilidade)
            section['email'] = email_solicitante
            section['email_solicitante'] = email_solicitante
            if usuario_responsavel is not None:
                section['usuario_responsavel'] = usuario_responsavel
            if servico_id is not None:
                section['servico_id'] = servico_id
            if servico is not None:
                section['servico'] = servico
            if ds_grupo_servico is not None:
                section['ds_grupo_servico'] = ds_grupo_servico
            if item_servico is not None:
                section['item_servico'] = item_servico
            if urg_alta is not None:
                section['urg_alta'] = urg_alta
            if urg_media is not None:
                section['urg_media'] = urg_media
            if urg_baixa is not None:
                section['urg_baixa'] = urg_baixa
            if ds_resp_servico is not None:
                section['ds_resp_servico'] = ds_resp_servico
            if ds_tipo is not None:
                section['ds_tipo'] = ds_tipo
            if ds_urgencia is not None:
                section['ds_urgencia'] = ds_urgencia
            if equipe_responsavel is not None:
                section['equipe_responsavel'] = equipe_responsavel
            if status is not None:
                section['status'] = status
            if solicitante is not None:
                section['solicitante'] = solicitante
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Erro ao salvar configuração: {str(e)}")
            return False
    
    def carregar_configuracao(self, email: Optional[str] = None) -> Dict[str, str]:
        """
        Carrega as configurações salvas
        
        Args:
            email: Email para identificar a configuração (opcional, se não fornecido retorna a primeira encontrada)
            
        Returns:
            Dicionário com as configurações salvas
        """
        try:
            self._load_config()
            
            # Se email fornecido, busca configuração específica
            if email:
                secao_nome = self._normalizar_email_secao(email)
                if secao_nome in self.config:
                    section = self.config[secao_nome]
                    # Retorna email_solicitante se existir, senão usa 'email' (compatibilidade)
                    email_solicitante = section.get('email_solicitante', section.get('email', ''))
                    return {
                        'email': email_solicitante,  # Mantém para compatibilidade
                        'email_solicitante': email_solicitante,
                        'usuario_responsavel': section.get('usuario_responsavel', ''),
                        'servico_id': section.get('servico_id', ''),
                        'servico': section.get('servico', ''),
                        'ds_grupo_servico': section.get('ds_grupo_servico', ''),
                        'item_servico': section.get('item_servico', ''),
                        'urg_alta': section.get('urg_alta', ''),
                        'urg_media': section.get('urg_media', ''),
                        'urg_baixa': section.get('urg_baixa', ''),
                        'ds_resp_servico': section.get('ds_resp_servico', ''),
                        'ds_tipo': section.get('ds_tipo', ''),
                        'ds_urgencia': section.get('ds_urgencia', ''),
                        'equipe_responsavel': section.get('equipe_responsavel', ''),
                        'status': section.get('status', ''),
                        'solicitante': section.get('solicitante', '')
                    }
                return {}
            
            # Se não fornecido, retorna a primeira configuração encontrada (compatibilidade)
            for secao_nome in self.config.sections():
                # Ignora seção GERAIS (agora em arquivo separado)
                if secao_nome.upper() == 'GERAIS':
                    continue
                if '@' in secao_nome or secao_nome.startswith('usuario_'):
                    section = self.config[secao_nome]
                    # Retorna email_solicitante se existir, senão usa 'email' (compatibilidade)
                    email_solicitante = section.get('email_solicitante', section.get('email', ''))
                    return {
                        'email': email_solicitante,  # Mantém para compatibilidade
                        'email_solicitante': email_solicitante,
                        'usuario_responsavel': section.get('usuario_responsavel', ''),
                        'servico_id': section.get('servico_id', ''),
                        'servico': section.get('servico', ''),
                        'ds_grupo_servico': section.get('ds_grupo_servico', ''),
                        'item_servico': section.get('item_servico', ''),
                        'urg_alta': section.get('urg_alta', ''),
                        'urg_media': section.get('urg_media', ''),
                        'urg_baixa': section.get('urg_baixa', ''),
                        'ds_resp_servico': section.get('ds_resp_servico', ''),
                        'ds_tipo': section.get('ds_tipo', ''),
                        'ds_urgencia': section.get('ds_urgencia', ''),
                        'equipe_responsavel': section.get('equipe_responsavel', ''),
                        'status': section.get('status', ''),
                        'solicitante': section.get('solicitante', '')
                    }
            
            return {}
            
        except Exception as e:
            print(f"Erro ao carregar configuração: {str(e)}")
            return {}
    
    def listar_todas_configuracoes(self) -> list:
        """
        Lista todas as configurações salvas retornando email, serviço e usuário responsável
        
        Returns:
            Lista de dicionários com email, serviço e usuario_responsavel de cada configuração
        """
        try:
            self._load_config()
            
            lista_configs = []
            
            for secao_nome in self.config.sections():
                # Ignora seção GERAIS (agora em arquivo separado)
                if secao_nome.upper() == 'GERAIS':
                    continue
                # Ignora seções que não são emails (como seções de sistema)
                if '@' in secao_nome:
                    section = self.config[secao_nome]
                    # Usa email_solicitante se existir, senão usa 'email' (compatibilidade)
                    email = section.get('email_solicitante', section.get('email', secao_nome))
                    servico = section.get('servico', '')
                    usuario_responsavel = section.get('usuario_responsavel', '')
                    if email:  # Só adiciona se tiver email
                        lista_configs.append({
                            'email': email,  # Mantém 'email' para compatibilidade com o frontend
                            'servico': servico,
                            'usuario_responsavel': usuario_responsavel
                        })
            
            return lista_configs
            
        except Exception as e:
            print(f"Erro ao listar configurações: {str(e)}")
            return []
    
    def excluir_configuracao(self, email: str) -> bool:
        """
        Exclui uma configuração salva
        
        Args:
            email: Email para identificar a configuração a ser excluída
            
        Returns:
            True se excluiu com sucesso, False caso contrário
        """
        try:
            if not email or not email.strip():
                print("Erro: email é obrigatório para excluir a configuração")
                return False
            
            self._load_config()
            
            # Normaliza o email para usar como nome de seção
            secao_nome = self._normalizar_email_secao(email)
            
            # Verifica se a seção existe
            if secao_nome not in self.config:
                print(f"Configuração não encontrada para email: {email}")
                return False
            
            # Remove a seção
            self.config.remove_section(secao_nome)
            
            # Salva o arquivo
            self._save_config()
            
            print(f"Configuração excluída com sucesso para email: {email}")
            return True
            
        except Exception as e:
            print(f"Erro ao excluir configuração: {str(e)}")
            return False
    


# Instância global do gerenciador
_config_manager = None
_config_manager_gerais = None


def get_config_manager() -> ConfigManager:
    """Retorna a instância global do gerenciador de configurações de personalização"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


class ConfigManagerGerais:
    """Gerencia as configurações gerais do sistema"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Inicializa o gerenciador de configurações gerais
        
        Args:
            config_file: Caminho do arquivo de configuração (opcional)
        """
        if config_file is None:
            config_file = Path(__file__).parent / "configuracoes_gerais.ini"
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """Garante que o arquivo de configuração existe no Drive (não cria localmente)"""
        # Não cria arquivo local - apenas verifica se existe no Drive
        pass
    
    def _load_config(self):
        """Carrega o arquivo de configuração do Google Drive"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug("[ConfigManagerGerais] Google Drive não disponível - usando configuração vazia")
                return
            
            nome_arquivo = self.config_file.name
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo)
            
            if conteudo:
                self.config.read_string(conteudo)
            else:
                logger.debug(f"[ConfigManagerGerais] Arquivo '{nome_arquivo}' não encontrado no Drive")
        except Exception as e:
            logger.debug(f"[ConfigManagerGerais] Erro ao carregar do Drive: {str(e)}")
    
    def _save_config(self):
        """Salva o arquivo de configuração no Google Drive (não salva localmente)"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.error("[ConfigManagerGerais] Google Drive não disponível - não é possível salvar configuração")
                return False
            
            nome_arquivo = self.config_file.name
            
            # Converte configuração para string
            output = io.StringIO()
            self.config.write(output)
            conteudo = output.getvalue()
            
            # Salva no Drive
            sucesso = drive_manager.salvar_config_no_drive(conteudo, nome_arquivo)
            if sucesso:
                logger.info(f"[ConfigManagerGerais] Configurações salvas com sucesso no Drive: {nome_arquivo}")
            else:
                logger.error(f"[ConfigManagerGerais] Falha ao salvar configurações no Drive: {nome_arquivo}")
            return sucesso
            
        except Exception as e:
            logger.error(f"[ConfigManagerGerais] Erro ao salvar configuração no Drive: {str(e)}")
            import traceback
            logger.debug(f"[ConfigManagerGerais] Traceback: {traceback.format_exc()}")
            return False
    
    def salvar_configuracao(
        self, 
        gmail_check_interval: Optional[int] = None,
        gmail_monitor_enabled: Optional[str] = None,
        black_list_emails: Optional[str] = None,
        emails_list: Optional[str] = None,
        historico_check_interval_minutes: Optional[float] = None,
        historico_check_interval_hours: Optional[float] = None,
        historico_monitor_enabled: Optional[str] = None,
        historico_exclude_emails: Optional[str] = None,
        email_deduplication_patterns: Optional[str] = None,
        email_deduplication_emails: Optional[str] = None
    ) -> bool:
        """
        Salva configurações gerais do sistema
        
        Args:
            gmail_check_interval: Intervalo em minutos para verificação de emails
            gmail_monitor_enabled: "true" ou "false" para habilitar/desabilitar monitoramento
            black_list_emails: String com emails separados por vírgula
            emails_list: String com emails separados por vírgula para usar FakeUser
            historico_check_interval_minutes: Intervalo em minutos para verificação de histórico
            historico_monitor_enabled: "true" ou "false" para habilitar/desabilitar monitoramento de histórico
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            self._load_config()
            
            # Cria seção de configurações gerais se não existir
            secao_geral = 'GERAIS'
            if secao_geral not in self.config:
                self.config[secao_geral] = {}
            
            section = self.config[secao_geral]
            
            if gmail_check_interval is not None:
                section['gmail_check_interval'] = str(gmail_check_interval)
            
            if gmail_monitor_enabled is not None:
                section['gmail_monitor_enabled'] = gmail_monitor_enabled.lower()
            
            if black_list_emails is not None:
                section['black_list_emails'] = black_list_emails.strip()
            
            if emails_list is not None:
                section['emails_list'] = emails_list.strip()
            
            if historico_check_interval_minutes is not None:
                section['historico_check_interval_minutes'] = str(historico_check_interval_minutes)
            
            if historico_check_interval_hours is not None:
                section['historico_check_interval_hours'] = str(historico_check_interval_hours)
            
            if historico_monitor_enabled is not None:
                section['historico_monitor_enabled'] = historico_monitor_enabled.lower()
            
            if historico_exclude_emails is not None:
                section['historico_exclude_emails'] = historico_exclude_emails.strip()
            
            if email_deduplication_patterns is not None:
                section['email_deduplication_patterns'] = email_deduplication_patterns.strip()
            
            if email_deduplication_emails is not None:
                section['email_deduplication_emails'] = email_deduplication_emails.strip()
            
            sucesso = self._save_config()
            if sucesso:
                logger.info("[ConfigManagerGerais] Configurações de deduplicação salvas: patterns e emails")
            return sucesso if sucesso is not None else True
            
        except Exception as e:
            print(f"Erro ao salvar configuração geral: {str(e)}")
            return False
    
    def carregar_configuracao(self) -> Dict[str, str]:
        """
        Carrega as configurações gerais do sistema
        Se não houver configuração salva, retorna valores padrão do .env
        
        Returns:
            Dicionário com as configurações gerais
        """
        try:
            self._load_config()
            
            secao_geral = 'GERAIS'
            if secao_geral not in self.config:
                # Retorna valores padrão do .env
                from src.modelo_dados.modelo_settings import ConfigEnvSetings
                return {
                    'gmail_check_interval': str(getattr(ConfigEnvSetings, 'GMAIL_CHECK_INTERVAL', 1)),
                    'gmail_monitor_enabled': getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower(),
                    'black_list_emails': getattr(ConfigEnvSetings, 'BLACK_LIST_EMAILS', ''),
                    'emails_list': getattr(ConfigEnvSetings, 'EMAILS_LIST', ''),
                    'historico_check_interval_minutes': str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_MINUTES', 60.0)),
                    'historico_check_interval_hours': str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_HOURS', 1.0)),
                    'historico_monitor_enabled': getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower(),
                    'historico_exclude_emails': getattr(ConfigEnvSetings, 'HISTORICO_EXCLUDE_EMAILS', ''),
                    'email_deduplication_patterns': getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_PATTERNS', ''),
                    'email_deduplication_emails': getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_EMAILS', '')
                }
            
            section = self.config[secao_geral]
            
            # Se não houver valor salvo, usa padrão do .env
            from src.modelo_dados.modelo_settings import ConfigEnvSetings
            return {
                'gmail_check_interval': section.get('gmail_check_interval') or str(getattr(ConfigEnvSetings, 'GMAIL_CHECK_INTERVAL', 1)),
                'gmail_monitor_enabled': section.get('gmail_monitor_enabled') or getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower(),
                'black_list_emails': section.get('black_list_emails') or getattr(ConfigEnvSetings, 'BLACK_LIST_EMAILS', ''),
                'emails_list': section.get('emails_list') or getattr(ConfigEnvSetings, 'EMAILS_LIST', ''),
                'historico_check_interval_minutes': section.get('historico_check_interval_minutes') or str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_MINUTES', 60.0)),
                'historico_check_interval_hours': section.get('historico_check_interval_hours') or str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_HOURS', 1.0)),
                'historico_monitor_enabled': section.get('historico_monitor_enabled') or getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower(),
                'historico_exclude_emails': section.get('historico_exclude_emails') or getattr(ConfigEnvSetings, 'HISTORICO_EXCLUDE_EMAILS', ''),
                'email_deduplication_patterns': section.get('email_deduplication_patterns') or getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_PATTERNS', ''),
                'email_deduplication_emails': section.get('email_deduplication_emails') or getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_EMAILS', '')
            }
            
        except Exception as e:
            print(f"Erro ao carregar configuração geral: {str(e)}")
            # Retorna valores padrão em caso de erro
            try:
                from src.modelo_dados.modelo_settings import ConfigEnvSetings
                return {
                    'gmail_check_interval': str(getattr(ConfigEnvSetings, 'GMAIL_CHECK_INTERVAL', 1)),
                    'gmail_monitor_enabled': getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower(),
                    'black_list_emails': getattr(ConfigEnvSetings, 'BLACK_LIST_EMAILS', ''),
                    'emails_list': getattr(ConfigEnvSetings, 'EMAILS_LIST', ''),
                    'historico_check_interval_minutes': str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_MINUTES', 60.0)),
                    'historico_check_interval_hours': str(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_HOURS', 1.0)),
                    'historico_monitor_enabled': getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower(),
                    'historico_exclude_emails': getattr(ConfigEnvSetings, 'HISTORICO_EXCLUDE_EMAILS', ''),
                    'email_deduplication_patterns': getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_PATTERNS', ''),
                    'email_deduplication_emails': getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_EMAILS', '')
                }
            except:
                return {}


def get_config_manager_gerais() -> ConfigManagerGerais:
    """Retorna a instância global do gerenciador de configurações gerais"""
    global _config_manager_gerais
    if _config_manager_gerais is None:
        _config_manager_gerais = ConfigManagerGerais()
    return _config_manager_gerais
