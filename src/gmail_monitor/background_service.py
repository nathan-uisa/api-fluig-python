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
        self._interval = getattr(ConfigEnvSetings, 'GMAIL_CHECK_INTERVAL', 1) * 60  # Converte minutos para segundos
    
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


def iniciar_monitoramento_gmail():
    """Inicia o monitoramento de emails em background"""
    global _gmail_background_service
    
    # Verifica se o serviço está habilitado
    gmail_enabled = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower()
    if gmail_enabled not in ('true', '1', 'yes'):
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
