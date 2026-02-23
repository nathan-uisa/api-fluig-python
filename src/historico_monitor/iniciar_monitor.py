"""
Script para iniciar o monitoramento de histórico de chamados

Este script inicia o monitoramento periódico de históricos de chamados
abertos via email, verificando atualizações a cada 1 hora (configurável).
"""
import sys
import signal
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.historico_monitor.historico_monitor import HistoricoMonitor
from src.utilitarios_centrais.logger import logger


def main():
    """
    Função principal para iniciar o monitoramento
    """
    # Configurações
    ambiente = "PRD"  # Pode ser configurado via variável de ambiente
    intervalo_horas = 1.0  # Verifica a cada 1 hora
    
    print("\n" + "="*80)
    print("MONITOR DE HISTÓRICO DE CHAMADOS")
    print("="*80)
    print(f"Ambiente: {ambiente}")
    print(f"Intervalo de verificação: {intervalo_horas} hora(s)")
    print("="*80 + "\n")
    
    # Cria monitor
    monitor = HistoricoMonitor(intervalo_horas=intervalo_horas)
    
    # Handler para encerramento gracioso
    def signal_handler(sig, frame):
        print("\n\nRecebido sinal de interrupção. Encerrando monitoramento...")
        monitor.parar_monitoramento()
        print("Monitoramento encerrado.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Inicia monitoramento em background
        monitor.iniciar_monitoramento(ambiente=ambiente, em_background=True)
        
        print(f"[OK] Monitoramento iniciado com sucesso!")
        print(f"[INFO] Verificando atualizações a cada {intervalo_horas} hora(s)")
        print(f"[INFO] Pressione Ctrl+C para parar o monitoramento\n")
        
        # Mantém o script rodando
        while monitor.esta_rodando():
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nInterrupção pelo usuário. Encerrando monitoramento...")
        monitor.parar_monitoramento()
        print("Monitoramento encerrado.")
    except Exception as e:
        logger.error(f"[iniciar_monitor] Erro durante o monitoramento: {str(e)}")
        import traceback
        logger.debug(f"[iniciar_monitor] Traceback: {traceback.format_exc()}")
        monitor.parar_monitoramento()
        sys.exit(1)


if __name__ == "__main__":
    main()
