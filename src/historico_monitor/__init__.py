"""
Módulo de gerenciamento de histórico de chamados abertos via email

Este módulo fornece funcionalidades para:
- Salvar histórico de chamados abertos via email
- Monitorar atualizações nos históricos periodicamente
- Detectar mudanças nos chamados
"""

from .historico_manager import HistoricoManager
from .historico_monitor import HistoricoMonitor
from .historico_fluxo import HistoricoFluxoManager
from .background_service import (
    iniciar_monitoramento_historico,
    parar_monitoramento_historico
)

__all__ = [
    'HistoricoManager',
    'HistoricoMonitor',
    'HistoricoFluxoManager',
    'iniciar_monitoramento_historico',
    'parar_monitoramento_historico'
]
