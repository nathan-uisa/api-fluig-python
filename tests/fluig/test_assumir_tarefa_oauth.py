"""
Script de teste para assumir uma tarefa no Fluig usando OAuth 1.0

IMPORTANTE: Este teste usa exclusivamente autenticação OAuth 1.0 (CK, CS, TK, TS)
e não utiliza cookies ou autenticação via navegador.
"""
import sys
from pathlib import Path
from typing import Optional
import time
from urllib.parse import urlencode
import requests

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_core import FluigCore
from src.fluig.fluig_requests import RequestsFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def test_assumir_tarefa_oauth(
    ambiente: str = "PRD",
    process_instance_id: int = 694090,
    task_user_id: str = "f91b4d01ddc24241b2e1915657bebcd4",
    current_movto: int = 3,
    thread_sequence: int = 0,
    colleague_id: str = "Pool:Group:ITSM_TODOS"
):
    """
    Testa a assunção de uma tarefa usando o endpoint GET /ecm/api/rest/ecm/workflowView/takeTask
    com autenticação OAuth 1.0
    
    IMPORTANTE: Usa exclusivamente OAuth 1.0 (CK, CS, TK, TS) - não utiliza cookies
    
    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_instance_id: ID da instância do processo
        task_user_id: ID do usuário da tarefa (pode ser email ou colleagueId)
        current_movto: Movimento atual
        thread_sequence: Sequência da thread (padrão: 0)
        colleague_id: ID do colega/grupo (ex: "Pool:Group:ITSM_TODOS")
    """
    print("\n" + "="*80)
    print("TESTE: ASSUMIR TAREFA NO FLUIG (OAuth 1.0)")
    print("="*80 + "\n")
    
    print(f"Ambiente: {ambiente}")
    print(f"Process Instance ID: {process_instance_id}")
    print(f"Task User ID: {task_user_id}")
    print(f"Current Movto: {current_movto}")
    print(f"Thread Sequence: {thread_sequence}")
    print(f"Colleague ID: {colleague_id}")
    print()
    
    try:
        # Inicializa FluigCore para obter URL base
        fluig_core = FluigCore(ambiente=ambiente)
        url_base = fluig_core.url_base
        
        # Monta parâmetros da query string
        params = {
            "processInstanceId": process_instance_id,
            "taskUserId": task_user_id,
            "currentMovto": current_movto,
            "threadSequence": thread_sequence,
            "colleagueId": colleague_id,
            "_": int(time.time() * 1000)  # Timestamp para cache busting
        }
        
        # Monta URL do endpoint com parâmetros já na query string
        # Isso garante que o OAuth 1.0 assine corretamente a URL completa
        endpoint = "/ecm/api/rest/ecm/workflowView/takeTask"
        query_string = urlencode(params, doseq=True)
        url = f"{url_base}{endpoint}?{query_string}"
        
        print(f"URL completa: {url}")
        print(f"Parâmetros:")
        for key, value in params.items():
            print(f"   {key}: {value}")
        print()
        
        # Inicializa RequestsFluig com OAuth 1.0
        print("Inicializando autenticação OAuth 1.0...")
        requests_fluig = RequestsFluig(ambiente)
        print(f"[OK] Autenticação OAuth 1.0 configurada para ambiente {ambiente}")
        print(f"[OK] Usando apenas OAuth 1.0 (CK, CS, TK, TS)\n")
        
        # Faz requisição GET usando OAuth 1.0
        # Passa URL completa sem params separados para garantir assinatura correta
        print("Enviando requisição GET com OAuth 1.0...")
        logger.info(f"[test_assumir_tarefa_oauth] Fazendo requisição GET para {url} usando OAuth 1.0")
        logger.debug(f"[test_assumir_tarefa_oauth] Parâmetros: {params}")
        logger.debug(f"[test_assumir_tarefa_oauth] Autenticação: OAuth 1.0")
        
        # Usa requests diretamente com OAuth 1.0, passando URL completa sem params separados
        import requests
        resposta = requests.get(url, headers=requests_fluig.headers, auth=requests_fluig.auth, timeout=15)
        
        print(f"\nStatus Code: {resposta.status_code}")
        print(f"Response Headers: {dict(resposta.headers)}\n")
        
        logger.info(f"[test_assumir_tarefa_oauth] Status Code: {resposta.status_code}")
        
        # Processa resposta
        if resposta.status_code == 200:
            print("[OK] Requisição bem-sucedida!")
            print(f"\nResposta (texto): {resposta.text[:1000]}")
            
            # Tenta parsear como JSON se possível
            try:
                import json
                resultado = resposta.json()
                print("\nResposta (JSON):")
                print(json.dumps(resultado, indent=2, ensure_ascii=False))
                logger.info(f"[test_assumir_tarefa_oauth] Resposta JSON: {resultado}")
            except Exception as e:
                print(f"\n[AVISO] Não foi possível parsear como JSON: {str(e)}")
                logger.debug(f"[test_assumir_tarefa_oauth] Resposta não é JSON válido: {resposta.text[:500]}")
            
            print("\n" + "="*80)
            print("[OK] Teste concluído com sucesso!")
            print("="*80 + "\n")
            return True
        else:
            print(f"[ERRO] Requisição falhou com status {resposta.status_code}")
            print(f"Resposta: {resposta.text[:1000]}")
            logger.error(f"[test_assumir_tarefa_oauth] Erro na requisição: Status {resposta.status_code}, Resposta: {resposta.text[:500]}")
            print("\n" + "="*80)
            print("[ERRO] Teste falhou!")
            print("="*80 + "\n")
            return False
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"[test_assumir_tarefa_oauth] Erro durante o teste: {str(e)}", exc_info=True)
        print("\n" + "="*80)
        print("[ERRO] Teste falhou!")
        print("="*80 + "\n")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Testa assunção de tarefa no Fluig usando endpoint takeTask com OAuth 1.0'
    )
    parser.add_argument(
        '--ambiente', 
        type=str, 
        default='PRD', 
        choices=['PRD', 'QLD'],
        help='Ambiente do Fluig (PRD ou QLD)'
    )
    parser.add_argument(
        '--process-instance-id',
        '--process_instance_id',
        type=int,
        default=694085,
        help='ID da instância do processo'
    )
    parser.add_argument(
        '--task-user-id',
        '--task_user_id',
        type=str,
        default='f91b4d01ddc24241b2e1915657bebcd4',
        help='ID do usuário da tarefa (pode ser email ou colleagueId)'
    )
    parser.add_argument(
        '--current-movto',
        '--current_movto',
        type=int,
        default=3,
        help='Movimento atual'
    )
    parser.add_argument(
        '--thread-sequence',
        '--thread_sequence',
        type=int,
        default=0,
        help='Sequência da thread - padrão: 0'
    )
    parser.add_argument(
        '--colleague-id',
        '--colleague_id',
        type=str,
        default='Pool:Group:ITSM_TODOS',
        help='ID do colega/grupo (ex: Pool:Group:ITSM_TODOS)'
    )
    
    args = parser.parse_args()
    
    print("\nIniciando teste de assunção de tarefa com OAuth 1.0...\n")
    
    sucesso = test_assumir_tarefa_oauth(
        ambiente=args.ambiente,
        process_instance_id=args.process_instance_id,
        task_user_id=args.task_user_id,
        current_movto=args.current_movto,
        thread_sequence=args.thread_sequence,
        colleague_id=args.colleague_id
    )
    
    if sucesso:
        print("\nTeste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\nTeste falhou!\n")
        sys.exit(1)
