"""
Gerenciador de templates de chamados por usuário usando ConfigParser
Salva e carrega templates de título e descrição de chamados
Agora usa apenas Google Drive (não salva arquivos locais)
"""
import configparser
import io
import os
from pathlib import Path
from typing import Optional, Dict
from src.utilitarios_centrais.logger import logger


class UserTemplateManager:
    """Gerencia os templates de chamados por usuário"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Inicializa o gerenciador de templates
        
        Args:
            base_path: Caminho base para a pasta de templates (padrão: src/configs/user_configs)
        """
        if base_path is None:
            current_dir = Path(__file__).parent
            base_path = current_dir / "user_configs"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[UserTemplateManager] Inicializado - Pasta de templates: {self.base_path}")
    
    def _get_template_file(self, email: str) -> Path:
        """
        Retorna o caminho do arquivo de template para um usuário
        
        Args:
            email: Email do usuário
        
        Returns:
            Path do arquivo de template
        """
        # Normaliza o email para usar como nome de arquivo
        email_normalizado = email.strip().lower().replace('@', '_at_').replace('.', '_')
        return self.base_path / f"template_{email_normalizado}.ini"
    
    def salvar_template(
        self,
        email: str,
        nome_template: str,
        titulo: str,
        descricao: str
    ) -> bool:
        """
        Salva um template de chamado para um usuário com um nome específico
        Salva diretamente no Google Drive (não salva localmente)
        
        Args:
            email: Email do usuário
            nome_template: Nome do template (identificador único)
            titulo: Título do chamado
            descricao: Descrição do chamado
        
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.error("[UserTemplateManager] Google Drive não disponível - não é possível salvar template")
                return False
            
            # Normaliza o email para nome de arquivo
            email_normalizado = email.strip().lower().replace('@', '_at_').replace('.', '_')
            nome_arquivo = f"template_{email_normalizado}.ini"
            
            # Carrega configuração existente do Drive
            config = configparser.ConfigParser()
            conteudo_drive = drive_manager.ler_config_do_drive(nome_arquivo, subpasta='user_configs')
            
            if conteudo_drive:
                config.read_string(conteudo_drive)
            
            # Normaliza o nome do template para usar como seção
            nome_secao = f"TEMPLATE_{nome_template.strip().upper().replace(' ', '_').replace('-', '_')}"
            
            # Cria ou atualiza seção do template
            if nome_secao not in config:
                config.add_section(nome_secao)
            
            config.set(nome_secao, 'nome', nome_template)
            config.set(nome_secao, 'email', email)
            config.set(nome_secao, 'titulo', titulo)
            config.set(nome_secao, 'descricao', descricao)
            
            # Converte para string e salva no Drive
            output = io.StringIO()
            config.write(output)
            conteudo = output.getvalue()
            
            sucesso = drive_manager.salvar_config_no_drive(conteudo, nome_arquivo, subpasta='user_configs')
            
            if sucesso:
                logger.info(f"[UserTemplateManager] Template '{nome_template}' salvo com sucesso no Drive para {email}")
                return True
            else:
                logger.error(f"[UserTemplateManager] Erro ao salvar template '{nome_template}' no Drive")
                return False
            
        except Exception as e:
            logger.error(f"[UserTemplateManager] Erro ao salvar template '{nome_template}' para {email}: {str(e)}")
            import traceback
            logger.debug(f"[UserTemplateManager] Traceback: {traceback.format_exc()}")
            return False
    
    def carregar_template(self, email: str, nome_template: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Carrega um template de chamado de um usuário do Google Drive
        
        Args:
            email: Email do usuário
            nome_template: Nome do template a carregar (opcional, se None retorna o primeiro)
        
        Returns:
            Dicionário com nome, titulo e descricao ou None se não encontrado
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug(f"[UserTemplateManager] Google Drive não disponível - não é possível carregar template")
                return None
            
            # Normaliza o email para nome de arquivo
            email_normalizado = email.strip().lower().replace('@', '_at_').replace('.', '_')
            nome_arquivo = f"template_{email_normalizado}.ini"
            
            # Carrega do Drive
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo, subpasta='user_configs')
            
            if not conteudo:
                logger.debug(f"[UserTemplateManager] Template não encontrado no Drive para {email}")
                return None
            
            config = configparser.ConfigParser()
            config.read_string(conteudo)
            
            # Se nome_template foi especificado, busca esse template específico
            if nome_template:
                nome_secao = f"TEMPLATE_{nome_template.strip().upper().replace(' ', '_').replace('-', '_')}"
                if nome_secao in config:
                    section = config[nome_secao]
                    template = {
                        'nome': section.get('nome', nome_template),
                        'titulo': section.get('titulo', ''),
                        'descricao': section.get('descricao', '')
                    }
                    logger.info(f"[UserTemplateManager] Template '{nome_template}' carregado com sucesso para {email}")
                    return template
                else:
                    logger.warning(f"[UserTemplateManager] Template '{nome_template}' não encontrado para {email}")
                    return None
            
            # Se não especificado, retorna o primeiro template encontrado (compatibilidade)
            for secao_nome in config.sections():
                if secao_nome.startswith('TEMPLATE_'):
                    section = config[secao_nome]
                    template = {
                        'nome': section.get('nome', secao_nome.replace('TEMPLATE_', '')),
                        'titulo': section.get('titulo', ''),
                        'descricao': section.get('descricao', '')
                    }
                    logger.info(f"[UserTemplateManager] Template carregado com sucesso para {email}")
                    return template
            
            logger.warning(f"[UserTemplateManager] Nenhum template encontrado para {email}")
            return None
            
        except Exception as e:
            logger.error(f"[UserTemplateManager] Erro ao carregar template para {email}: {str(e)}")
            import traceback
            logger.debug(f"[UserTemplateManager] Traceback: {traceback.format_exc()}")
            return None
    
    def listar_templates(self, email: str) -> list:
        """
        Lista todos os templates de um usuário do Google Drive
        
        Args:
            email: Email do usuário
        
        Returns:
            Lista de dicionários com nome, titulo e descricao de cada template
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug(f"[UserTemplateManager] Google Drive não disponível - não é possível listar templates")
                return []
            
            # Normaliza o email para nome de arquivo
            email_normalizado = email.strip().lower().replace('@', '_at_').replace('.', '_')
            nome_arquivo = f"template_{email_normalizado}.ini"
            
            # Carrega do Drive
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo, subpasta='user_configs')
            
            if not conteudo:
                logger.debug(f"[UserTemplateManager] Nenhum template encontrado no Drive para {email}")
                return []
            
            config = configparser.ConfigParser()
            config.read_string(conteudo)
            
            templates = []
            for secao_nome in config.sections():
                if secao_nome.startswith('TEMPLATE_'):
                    section = config[secao_nome]
                    templates.append({
                        'nome': section.get('nome', secao_nome.replace('TEMPLATE_', '')),
                        'titulo': section.get('titulo', ''),
                        'descricao': section.get('descricao', '')
                    })
            
            logger.info(f"[UserTemplateManager] {len(templates)} template(s) encontrado(s) para {email}")
            return templates
            
        except Exception as e:
            logger.error(f"[UserTemplateManager] Erro ao listar templates para {email}: {str(e)}")
            import traceback
            logger.debug(f"[UserTemplateManager] Traceback: {traceback.format_exc()}")
            return []
    
    def excluir_template(self, email: str, nome_template: str) -> bool:
        """
        Exclui um template específico de um usuário do Google Drive
        
        Args:
            email: Email do usuário
            nome_template: Nome do template a excluir
        
        Returns:
            True se excluiu com sucesso, False caso contrário
        """
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.error("[UserTemplateManager] Google Drive não disponível - não é possível excluir template")
                return False
            
            # Normaliza o email para nome de arquivo
            email_normalizado = email.strip().lower().replace('@', '_at_').replace('.', '_')
            nome_arquivo = f"template_{email_normalizado}.ini"
            
            # Carrega do Drive
            conteudo = drive_manager.ler_config_do_drive(nome_arquivo, subpasta='user_configs')
            
            if not conteudo:
                logger.warning(f"[UserTemplateManager] Template não existe no Drive para {email}")
                return False
            
            config = configparser.ConfigParser()
            config.read_string(conteudo)
            
            nome_secao = f"TEMPLATE_{nome_template.strip().upper().replace(' ', '_').replace('-', '_')}"
            
            if nome_secao not in config:
                logger.warning(f"[UserTemplateManager] Template '{nome_template}' não encontrado para {email}")
                return False
            
            config.remove_section(nome_secao)
            
            # Se não há mais templates, não salva arquivo vazio (deixa no Drive para histórico)
            if len(config.sections()) > 0:
                # Salva arquivo atualizado no Drive
                output = io.StringIO()
                config.write(output)
                conteudo_atualizado = output.getvalue()
                
                sucesso = drive_manager.salvar_config_no_drive(conteudo_atualizado, nome_arquivo, subpasta='user_configs')
                
                if sucesso:
                    logger.info(f"[UserTemplateManager] Template '{nome_template}' excluído com sucesso do Drive para {email}")
                    return True
                else:
                    logger.error(f"[UserTemplateManager] Erro ao salvar template atualizado no Drive")
                    return False
            else:
                # Arquivo vazio - remove do Drive seria ideal, mas por enquanto apenas loga
                logger.info(f"[UserTemplateManager] Template '{nome_template}' excluído. Arquivo ficou vazio (mantido no Drive)")
                return True
            
        except Exception as e:
            logger.error(f"[UserTemplateManager] Erro ao excluir template '{nome_template}' para {email}: {str(e)}")
            return False


def get_user_template_manager() -> UserTemplateManager:
    """Retorna a instância global do gerenciador de templates"""
    global _template_manager
    if '_template_manager' not in globals():
        _template_manager = UserTemplateManager()
    return _template_manager
