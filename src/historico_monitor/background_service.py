"""
Serviço em background para monitoramento periódico de histórico de chamados
"""
from typing import Optional
from src.historico_monitor.historico_monitor import HistoricoMonitor
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


class HistoricoMonitorBackgroundService:
    """
    Serviço em background que executa o monitoramento de histórico de chamados periodicamente
    """
    
    def __init__(self, intervalo_minutos: float = 60.0, ambiente: str = "PRD"):
        """
        Inicializa o serviço de monitoramento
        
        Args:
            intervalo_minutos: Intervalo em minutos entre verificações (padrão: 60.0)
            ambiente: Ambiente do Fluig (PRD ou QLD)
        """
        self.intervalo_minutos = intervalo_minutos
        self.ambiente = ambiente
        self.monitor: Optional[HistoricoMonitor] = None
    
    def iniciar(self):
        """Inicia o serviço de monitoramento em background"""
        try:
            logger.info(
                f"[historico_background] Iniciando monitoramento de histórico de chamados "
                f"(intervalo: {self.intervalo_minutos} minuto(s), ambiente: {self.ambiente})..."
            )
            
            if self.monitor is None:
                self.monitor = HistoricoMonitor(intervalo_minutos=self.intervalo_minutos)
            
            self.monitor.iniciar_monitoramento(ambiente=self.ambiente, em_background=True)
            
            logger.info("[historico_background] Monitoramento de histórico de chamados iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"[historico_background] Erro ao iniciar monitoramento: {str(e)}")
            import traceback
            logger.debug(f"[historico_background] Traceback: {traceback.format_exc()}")
    
    def parar(self):
        """Para o serviço de monitoramento"""
        try:
            logger.info("[historico_background] Parando monitoramento de histórico de chamados...")
            
            if self.monitor:
                self.monitor.parar_monitoramento()
            
            logger.info("[historico_background] Monitoramento de histórico de chamados parado")
            
        except Exception as e:
            logger.error(f"[historico_background] Erro ao parar monitoramento: {str(e)}")
    
    def reiniciar(self):
        """Reinicia o serviço de monitoramento (para e inicia novamente)"""
        import time
        logger.info("[historico_background] Reiniciando monitoramento de histórico de chamados...")
        self.parar()
        # Aguarda um pouco para garantir que o serviço parou completamente
        time.sleep(2)
        # Recarrega configurações antes de reiniciar
        self.intervalo_minutos = _obter_historico_intervalo_minutos()
        self.ambiente = _obter_historico_ambiente()
        # Recria o monitor com novas configurações
        self.monitor = None
        self.iniciar()


# Instância global do serviço
_historico_background_service: Optional[HistoricoMonitorBackgroundService] = None


def _obter_historico_monitor_enabled() -> bool:
    """Obtém o status de habilitação do monitoramento do arquivo de configuração ou .env"""
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        configs = config_manager.carregar_configuracao()
        enabled_str = configs.get('historico_monitor_enabled', '')
        if enabled_str and enabled_str.strip():
            return enabled_str.lower() in ('true', '1', 'yes')
    except Exception as e:
        logger.warning(f"[historico_background] Erro ao carregar status do arquivo de configuração: {str(e)}")
    
    # Fallback para .env (padrão: habilitado)
    historico_enabled = getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower()
    return historico_enabled in ('true', '1', 'yes')


def _obter_historico_intervalo_minutos() -> float:
    """Obtém o intervalo de verificação em minutos do arquivo de configuração ou .env"""
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        configs = config_manager.carregar_configuracao()
        intervalo_str = configs.get('historico_check_interval_minutes', '')
        if intervalo_str and intervalo_str.strip():
            return float(intervalo_str)
    except Exception as e:
        logger.warning(f"[historico_background] Erro ao carregar intervalo do arquivo de configuração: {str(e)}")
    
    # Fallback para .env (padrão: 60 minutos = 1 hora)
    return float(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_MINUTES', 60.0))


def _obter_historico_ambiente() -> str:
    """Obtém o ambiente do Fluig para monitoramento"""
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        configs = config_manager.carregar_configuracao()
        ambiente = configs.get('historico_monitor_ambiente', '')
        if ambiente and ambiente.strip():
            return ambiente.upper()
    except Exception as e:
        logger.warning(f"[historico_background] Erro ao carregar ambiente do arquivo de configuração: {str(e)}")
    
    # Fallback para .env (padrão: PRD)
    ambiente = getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_AMBIENTE', 'PRD')
    return ambiente.upper() if isinstance(ambiente, str) else 'PRD'


def iniciar_monitoramento_historico():
    """Inicia o monitoramento de histórico de chamados em background"""
    global _historico_background_service
    
    # Verifica se o serviço está habilitado
    if not _obter_historico_monitor_enabled():
        logger.info("[historico_background] Serviço de monitoramento de histórico desabilitado (HISTORICO_MONITOR_ENABLED=false)")
        return
    
    if _historico_background_service is None:
        intervalo_minutos = _obter_historico_intervalo_minutos()
        ambiente = _obter_historico_ambiente()
        _historico_background_service = HistoricoMonitorBackgroundService(
            intervalo_minutos=intervalo_minutos,
            ambiente=ambiente
        )
    _historico_background_service.iniciar()


def parar_monitoramento_historico():
    """Para o monitoramento de histórico de chamados"""
    global _historico_background_service
    if _historico_background_service:
        _historico_background_service.parar()

def reiniciar_monitoramento_historico():
    """Reinicia o monitoramento de histórico de chamados (recarrega configurações)"""
    global _historico_background_service
    if _historico_background_service and _historico_background_service.monitor and _historico_background_service.monitor.esta_rodando():
        _historico_background_service.reiniciar()
    elif _obter_historico_monitor_enabled():
        # Se não está rodando mas está habilitado, inicia
        iniciar_monitoramento_historico()
