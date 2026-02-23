"""
Módulo para deduplicação de emails baseado em padrões (regex/palavras-chave)

Este módulo identifica emails duplicados baseado em padrões configuráveis
como UUID, MAC address, ou outras palavras-chave que identificam um processo único.
"""
import re
import json
import io
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from configparser import ConfigParser
from pathlib import Path

from src.utilitarios_centrais.logger import logger


class EmailDeduplicator:
    """
    Gerencia deduplicação de emails baseado em padrões configuráveis
    
    Os padrões podem ser regex ou palavras-chave simples que identificam
    um processo único (ex: UUID: j8j8d1d1, MAC: AABBCCDDEEFF)
    """
    
    def __init__(self):
        """Inicializa o deduplicador"""
        self.padroes_config = None
        self.emails_deduplicacao = []
        self.identificadores_processados = {}
        self._carregar_configuracao()
        self._carregar_identificadores_processados()
    
    def _carregar_configuracao(self):
        """Carrega padrões de deduplicação e lista de emails do Google Drive"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            from src.configs.config_manager import get_config_manager_gerais
            
            # Tenta carregar da configuração geral primeiro
            config_manager = get_config_manager_gerais()
            configs = config_manager.carregar_configuracao()
            padroes_str = configs.get('email_deduplication_patterns', '')
            emails_str = configs.get('email_deduplication_emails', '')
            
            if not padroes_str:
                # Se não encontrou, tenta do .env
                from src.modelo_dados.modelo_settings import ConfigEnvSetings
                padroes_str = getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_PATTERNS', '')
            
            if not emails_str:
                # Se não encontrou, tenta do .env
                from src.modelo_dados.modelo_settings import ConfigEnvSetings
                emails_str = getattr(ConfigEnvSetings, 'EMAIL_DEDUPLICATION_EMAILS', '')
            
            if padroes_str:
                # Padrões podem ser separados por vírgula ou quebra de linha
                padroes = [p.strip() for p in padroes_str.replace('\n', ',').split(',') if p.strip()]
                self.padroes_config = padroes
                logger.debug(f"[EmailDeduplicator] {len(padroes)} padrão(ões) de deduplicação carregado(s)")
            else:
                self.padroes_config = []
                logger.debug("[EmailDeduplicator] Nenhum padrão de deduplicação configurado")
            
            if emails_str:
                # Emails podem ser separados por vírgula
                emails = [e.strip().lower() for e in emails_str.replace('\n', ',').split(',') if e.strip()]
                self.emails_deduplicacao = emails
                logger.debug(f"[EmailDeduplicator] {len(emails)} email(s) configurado(s) para deduplicação")
            else:
                self.emails_deduplicacao = []
                logger.debug("[EmailDeduplicator] Nenhum email configurado para deduplicação - todos os emails serão verificados")
                
        except Exception as e:
            logger.error(f"[EmailDeduplicator] Erro ao carregar configuração: {str(e)}")
            self.padroes_config = []
            self.emails_deduplicacao = []
    
    def _carregar_identificadores_processados(self):
        """Carrega lista de identificadores já processados do Google Drive"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug("[EmailDeduplicator] Google Drive não disponível - não é possível carregar identificadores")
                return
            
            conteudo = drive_manager.ler_config_do_drive('email_identificadores_processados.ini', subpasta='deduplicacao')
            
            if not conteudo:
                logger.debug("[EmailDeduplicator] Nenhum identificador processado encontrado")
                return
            
            config = ConfigParser()
    
            config.optionxform = str
            config.read_string(conteudo)
            
            if 'IDENTIFICADORES' in config:
                for opcao in config.options('IDENTIFICADORES'):
                    identificador = config.get('IDENTIFICADORES', opcao)
                    self.identificadores_processados[opcao] = identificador
            
            logger.debug(f"[EmailDeduplicator] {len(self.identificadores_processados)} identificador(es) processado(s) carregado(s)")
            
        except Exception as e:
            logger.debug(f"[EmailDeduplicator] Erro ao carregar identificadores (pode ser primeira execução): {str(e)}")
            self.identificadores_processados = {}
    
    def _salvar_identificador_processado(self, identificador: str, process_instance_id: Optional[int] = None):
        """Salva um identificador como processado no Google Drive"""
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            
            if not drive_manager:
                logger.debug("[EmailDeduplicator] Google Drive não disponível - não é possível salvar identificador")
                return
            
            # Carrega configuração existente
            conteudo = drive_manager.ler_config_do_drive('email_identificadores_processados.ini', subpasta='deduplicacao')
            
            config = ConfigParser()
           
            config.optionxform = str
            if conteudo:
                config.read_string(conteudo)
            else:
                config.add_section('IDENTIFICADORES')
            
            # Adiciona ou atualiza identificador
            if 'IDENTIFICADORES' not in config:
                config.add_section('IDENTIFICADORES')
            
            # Usa o identificador como chave e salva data/hora e process_instance_id se disponível
            valor = datetime.now().isoformat()
            if process_instance_id:
                valor += f"|process_id:{process_instance_id}"
            
            config.set('IDENTIFICADORES', identificador, valor)
            
            # Salva no Drive
            output = io.StringIO()
            config.write(output)
            conteudo_str = output.getvalue()
            
            drive_manager.salvar_config_no_drive(conteudo_str, 'email_identificadores_processados.ini', subpasta='deduplicacao')
            
            # Atualiza cache local
            self.identificadores_processados[identificador] = valor
            
            logger.debug(f"[EmailDeduplicator] Identificador '{identificador}' salvo como processado")
            
        except Exception as e:
            logger.error(f"[EmailDeduplicator] Erro ao salvar identificador: {str(e)}")
    
    def extrair_identificador(self, assunto: str, corpo: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai identificador único do email baseado nos padrões configurados
        
        Args:
            assunto: Assunto do email
            corpo: Corpo do email
            
        Returns:
            Tupla (identificador, padrao_usado) ou (None, None) se não encontrado
        """
        if not self.padroes_config:
            return (None, None)
        
        # Mantém texto original (case-sensitive) para extração precisa
        texto_completo_original = f"{assunto} {corpo}"
        
        for padrao in self.padroes_config:
            try:
                padrao_limpo = padrao.strip()
                
                # 1. Se o padrão já for um Regex complexo (tiver parênteses de captura)
                if '(' in padrao_limpo and ')' in padrao_limpo:
                    try:
                        regex = re.compile(padrao_limpo, re.IGNORECASE)
                        match = regex.search(texto_completo_original)
                        if match:
                            # Pega o grupo 1 se existir, senão o 0
                            identificador = match.group(1) if match.groups() else match.group(0)
                            if identificador:
                                logger.debug(f"[EmailDeduplicator] Identificador extraído com regex '{padrao}': {identificador}")
                                return (identificador.strip(), padrao_limpo)
                    except re.error:
                        # Se não é regex válido, continua para palavra-chave simples
                        pass
                
                # 2. Se for palavra-chave simples (pegar o valor após o padrão)
                padrao_escaped = re.escape(padrao_limpo)
                
                # Usa raw f-string (rf"") para evitar problemas com escape de barras
                # Se terminar com :, não coloca : opcional de novo
                if padrao_limpo.endswith(':'):
                    regex_busca = rf"{padrao_escaped}\s*([^\s]+)"
                else:
                    regex_busca = rf"{padrao_escaped}\s*:?\s*([^\s]+)"
                
                match = re.search(regex_busca, texto_completo_original, re.IGNORECASE)
                if match and match.groups():
                    identificador = match.group(1).strip()
                    
                    # Evita que o ID seja igual ao padrão (caso de erro na regex)
                    if identificador and identificador.lower() != padrao_limpo.lower():
                        logger.debug(f"[EmailDeduplicator] Regex: '{regex_busca}', Identificador: '{identificador}'")
                        return (identificador, padrao_limpo)
                    else:
                        logger.warning(f"[EmailDeduplicator] Identificador inválido ou igual ao padrão: '{identificador}' (padrão: '{padrao_limpo}')")
                            
            except Exception as e:
                logger.warning(f"[EmailDeduplicator] Erro ao processar padrão '{padrao}': {str(e)}")
                import traceback
                logger.debug(f"[EmailDeduplicator] Traceback: {traceback.format_exc()}")
                continue
        
        return (None, None)
    
    def verificar_duplicado(self, assunto: str, corpo: str, email_remetente: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Verifica se o email é duplicado baseado nos padrões configurados
        
        Args:
            assunto: Assunto do email
            corpo: Corpo do email
            email_remetente: Email do remetente (opcional, para verificar se deve passar pela deduplicação)
            
        Returns:
            Tupla (é_duplicado, identificador, process_instance_id)
            - é_duplicado: True se já foi processado
            - identificador: Identificador extraído
            - process_instance_id: ID do chamado já aberto (se disponível)
        """
        # Se há lista de emails configurada, verifica se o remetente está nela
        # Se a lista estiver vazia, todos os emails serão verificados
        if self.emails_deduplicacao and email_remetente:
            email_remetente_lower = email_remetente.lower().strip()
            if email_remetente_lower not in self.emails_deduplicacao:
                logger.debug(f"[EmailDeduplicator] Email '{email_remetente}' não está na lista de deduplicação - pulando verificação de padrões")
                return (False, None, None)
            else:
                logger.debug(f"[EmailDeduplicator] Email '{email_remetente}' está na lista de deduplicação - verificando padrões")
        elif not self.emails_deduplicacao:
            # Lista vazia = todos os emails são verificados
            logger.debug(f"[EmailDeduplicator] Nenhuma lista de emails configurada - verificando padrões para todos os emails")
        
        identificador, padrao_usado = self.extrair_identificador(assunto, corpo)
        
        if not identificador:
            return (False, None, None)
        
        # Verifica se já foi processado
        if identificador in self.identificadores_processados:
            valor = self.identificadores_processados[identificador]
            # Tenta extrair process_instance_id se disponível
            process_id = None
            if '|process_id:' in valor:
                try:
                    process_id_str = valor.split('|process_id:')[1]
                    process_id = int(process_id_str)
                except (ValueError, IndexError):
                    pass
            
            logger.info(f"[EmailDeduplicator] Email duplicado detectado - Identificador: {identificador}, Process ID: {process_id}")
            return (True, identificador, process_id)
        
        return (False, identificador, None)
    
    def marcar_como_processado(self, assunto: str, corpo: str, process_instance_id: Optional[int] = None):
        """
        Marca email como processado baseado no identificador extraído
        
        Args:
            assunto: Assunto do email
            corpo: Corpo do email
            process_instance_id: ID do chamado aberto (opcional)
        """
        identificador, _ = self.extrair_identificador(assunto, corpo)
        
        if identificador:
            self._salvar_identificador_processado(identificador, process_instance_id)
            logger.info(f"[EmailDeduplicator] Email marcado como processado - Identificador: {identificador}, Process ID: {process_instance_id}")
        else:
            logger.debug("[EmailDeduplicator] Nenhum identificador encontrado - email não será marcado para deduplicação")
