"""
Script de teste para assumir uma tarefa no Fluig
"""
import sys
from pathlib import Path
from typing import Optional
import time

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_core import FluigCore
from src.fluig.fluig_requests import RequestsFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.web.web_auth_manager import obter_cookies_validos
from src.web.web_cookies import cookies_para_requests
import requests


def test_assumir_tarefa(
    ambiente: str = "PRD",
    process_instance_id: int = 691616,
    task_user_id: str = "f91b4d01ddc24241b2e1915657bebcd4",
    current_movto: int = 3,
    thread_sequence: int = 0,
    colleague_id: str = "Pool:Group:ITSM_TODOS",
    usuario: Optional[str] = None
):
    """
    Testa a assunção de uma tarefa usando o endpoint GET /ecm/api/rest/ecm/workflowView/takeTask
    
    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_instance_id: ID da instância do processo
        task_user_id: ID do usuário da tarefa
        current_movto: Movimento atual
        thread_sequence: Sequência da thread (padrão: 0)
        colleague_id: ID do colega/grupo (ex: "Pool:Group:ITSM_TODOS")
        usuario: Usuário para autenticação (se None, usa FLUIG_ADMIN_USER)
    """
    print("\n" + "="*80)
    print("TESTE: ASSUMIR TAREFA NO FLUIG")
    print("="*80 + "\n")
    
    print(f"Ambiente: {ambiente}")
    print(f"Usuário: {usuario or ConfigEnvSetings.FLUIG_ADMIN_USER}")
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
        
        # Monta URL do endpoint com parâmetros
        endpoint = "/ecm/api/rest/ecm/workflowView/takeTask"
        url = f"{url_base}{endpoint}"
        
        print(f"URL: {url}")
        print(f"Parâmetros:")
        for key, value in params.items():
            print(f"   {key}: {value}")
        print()
        
        # Obtém cookies válidos
        print("Obtendo cookies válidos...")
        usuario_auth = usuario or ConfigEnvSetings.FLUIG_ADMIN_USER
        cookies_list = obter_cookies_validos(
            ambiente=ambiente,
            forcar_login=False,
            usuario=usuario_auth
        )
        
        if not cookies_list:
            print("[ERRO] Não foi possível obter cookies válidos")
            return False
        
        # Converte cookies para formato requests
        cookies_dict = cookies_para_requests(cookies_list)
        print(f"[OK] {len(cookies_list)} cookies obtidos\n")
        
        # Obtém headers e auth do RequestsFluig
        requests_fluig = RequestsFluig(ambiente)
        headers = requests_fluig.headers.copy()
        headers['accept'] = 'application/json'
        
        # Faz requisição GET
        print("Enviando requisição GET...")
        resposta = requests.get(
            url,
            params=params,
            headers=headers,
            auth=requests_fluig.auth,
            cookies=cookies_dict,
            timeout=30
        )
        
        print(f"\nStatus Code: {resposta.status_code}")
        print(f"Response Headers: {dict(resposta.headers)}\n")
        
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
            except:
                pass
            
            print("\n" + "="*80)
            print("[OK] Teste concluído com sucesso!")
            print("="*80 + "\n")
            return True
        else:
            print(f"[ERRO] Requisição falhou com status {resposta.status_code}")
            print(f"Resposta: {resposta.text[:1000]}")
            print("\n" + "="*80)
            print("[ERRO] Teste falhou!")
            print("="*80 + "\n")
            return False
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80)
        print("[ERRO] Teste falhou!")
        print("="*80 + "\n")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Testa assunção de tarefa no Fluig usando endpoint takeTask'
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
        default=691616,
        help='ID da instância do processo'
    )
    parser.add_argument(
        '--task-user-id',
        '--task_user_id',
        type=str,
        default='f91b4d01ddc24241b2e1915657bebcd4',
        help='ID do usuário da tarefa'
    )
    parser.add_argument(
        '--current-movto',
        '--current_movto',
        type=int,
        default=3,
        help='Movimento atual - padrão: 3'
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
    parser.add_argument(
        '--usuario',
        type=str,
        help='Usuário para autenticação (se não fornecido, usa FLUIG_ADMIN_USER)'
    )
    
    args = parser.parse_args()
    
    print("\nIniciando teste de assunção de tarefa...\n")
    
    sucesso = test_assumir_tarefa(
        ambiente=args.ambiente,
        process_instance_id=args.process_instance_id,
        task_user_id=args.task_user_id,
        current_movto=args.current_movto,
        thread_sequence=args.thread_sequence,
        colleague_id=args.colleague_id,
        usuario=args.usuario
    )
    
    if sucesso:
        print("\nTeste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\nTeste falhou!\n")
        sys.exit(1)
