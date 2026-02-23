"""
Serviço em background para monitoramento periódico de emails
"""
import threading
import time
from typing import Optional
from src.gmail_monitor.gmail_service import GmailMonitorService
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


class GmailMonitorBackgroundService:
    """
    Serviço em background que executa o monitoramento de emails periodicamente
    """
    
    def __init__(self):
        self.gmail_monitor: Optional[GmailMonitorService] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        # Tenta carregar do arquivo de configuração, senão usa do .env
        interval_minutes = self._obter_gmail_check_interval()
        self._interval = interval_minutes * 60  # Converte minutos para segundos
    
    def _obter_gmail_check_interval(self) -> int:
        """Obtém o intervalo de verificação do arquivo de configuração ou .env"""
        try:
            from src.configs.config_manager import get_config_manager_gerais
            config_manager = get_config_manager_gerais()
            configs = config_manager.carregar_configuracao()
            interval_str = configs.get('gmail_check_interval', '')
            if interval_str and interval_str.strip():
                return int(interval_str)
        except Exception as e:
            logger.warning(f"[gmail_background] Erro ao carregar intervalo do arquivo de configuração: {str(e)}")
        
        # Fallback para .env
        return getattr(ConfigEnvSetings, 'GMAIL_CHECK_INTERVAL', 1)
    
    def iniciar(self):
        """Inicia o serviço de monitoramento em background"""
        if self._running:
            logger.warning("[gmail_background] Serviço já está em execução")
            return
        
        try:
            logger.info(f"[gmail_background] Iniciando monitoramento de emails (intervalo: {self._interval/60} minutos)...")
            self.gmail_monitor = GmailMonitorService()
            self._running = True
            
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            
            logger.info("[gmail_background] Monitoramento de emails iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"[gmail_background] Erro ao iniciar monitoramento: {str(e)}")
            import traceback
            logger.debug(f"[gmail_background] Traceback: {traceback.format_exc()}")
            self._running = False
    
    def parar(self):
        """Para o serviço de monitoramento"""
        if not self._running:
            logger.warning("[gmail_background] Serviço não está em execução")
            return
        
        try:
            logger.info("[gmail_background] Parando monitoramento de emails...")
            self._running = False
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            
            logger.info("[gmail_background] Monitoramento de emails parado")
            
        except Exception as e:
            logger.error(f"[gmail_background] Erro ao parar monitoramento: {str(e)}")
    
    def _loop(self):
        """Loop principal do monitoramento"""
        while self._running:
            try:
                # Verifica se o monitoramento está habilitado antes de processar
                if not _obter_gmail_monitor_enabled():
                    logger.info("[gmail_background] Monitoramento desabilitado - aguardando próximo ciclo")
                    time.sleep(self._interval)
                    continue
                
                # Recarrega intervalo antes de cada ciclo (pode ter sido alterado)
                novo_intervalo = self._obter_gmail_check_interval()
                if novo_intervalo != self._interval / 60:
                    logger.info(f"[gmail_background] Intervalo atualizado: {self._interval/60} -> {novo_intervalo} minutos")
                    self._interval = novo_intervalo * 60
                
                if self.gmail_monitor:
                    self.gmail_monitor.processar_emails()
                else:
                    logger.error("[gmail_background] GmailMonitorService não inicializado")
                    break
                
                # Aguarda o intervalo configurado
                time.sleep(self._interval)
                
            except Exception as e:
                logger.error(f"[gmail_background] Erro no loop de monitoramento: {str(e)}")
                import traceback
                logger.debug(f"[gmail_background] Traceback: {traceback.format_exc()}")
                # Continua mesmo em caso de erro, aguardando o próximo ciclo
                time.sleep(self._interval)
    
    def reiniciar(self):
        """Reinicia o serviço de monitoramento (para e inicia novamente)"""
        logger.info("[gmail_background] Reiniciando monitoramento de emails...")
        self.parar()
        # Aguarda um pouco para garantir que o serviço parou completamente
        time.sleep(2)
        # Recarrega configurações antes de reiniciar
        self._interval = self._obter_gmail_check_interval() * 60
        self.iniciar()
    
    def processar_agora(self):
        """Força o processamento imediato de emails (útil para testes)"""
        if not self.gmail_monitor:
            self.gmail_monitor = GmailMonitorService()
        
        try:
            self.gmail_monitor.processar_emails()
        except Exception as e:
            logger.error(f"[gmail_background] Erro ao processar emails: {str(e)}")
            raise


# Instância global do serviço
_gmail_background_service: Optional[GmailMonitorBackgroundService] = None


def _obter_gmail_monitor_enabled() -> bool:
    """Obtém o status de habilitação do monitoramento do arquivo de configuração ou .env"""
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        configs = config_manager.carregar_configuracao()
        enabled_str = configs.get('gmail_monitor_enabled', '')
        if enabled_str and enabled_str.strip():
            return enabled_str.lower() in ('true', '1', 'yes')
    except Exception as e:
        logger.warning(f"[gmail_background] Erro ao carregar status do arquivo de configuração: {str(e)}")
    
    # Fallback para .env
    gmail_enabled = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower()
    return gmail_enabled in ('true', '1', 'yes')


def iniciar_monitoramento_gmail():
    """Inicia o monitoramento de emails em background"""
    global _gmail_background_service
    
    # Verifica se o serviço está habilitado
    if not _obter_gmail_monitor_enabled():
        logger.info("[gmail_background] Serviço de monitoramento de emails desabilitado (GMAIL_MONITOR_ENABLED=false)")
        return
    
    if _gmail_background_service is None:
        _gmail_background_service = GmailMonitorBackgroundService()
    _gmail_background_service.iniciar()


def parar_monitoramento_gmail():
    """Para o monitoramento de emails"""
    global _gmail_background_service
    if _gmail_background_service:
        _gmail_background_service.parar()

def reiniciar_monitoramento_gmail():
    """Reinicia o monitoramento de emails (recarrega configurações)"""
    global _gmail_background_service
    if _gmail_background_service and _gmail_background_service._running:
        _gmail_background_service.reiniciar()
    elif _obter_gmail_monitor_enabled():
        # Se não está rodando mas está habilitado, inicia
        iniciar_monitoramento_gmail()
