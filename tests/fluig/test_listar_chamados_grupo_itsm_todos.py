"""
Script de teste para listar chamados do grupo Pool:Group:ITSM_TODOS no Fluig
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_core import FluigCore
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def test_listar_chamados_grupo_itsm_todos(
    ambiente: str = "PRD", 
    page: int = 1, 
    page_size: int = 1000
):
    """
    Testa a listagem de chamados usando o grupo Pool:Group:ITSM_TODOS
    com os filtros: status=NOT_COMPLETED e slaStatus=ON_TIME
    
    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        page: Número da página
        page_size: Quantidade de registros por página
    """
    print("\n" + "="*80)
    print("TESTE: LISTAR CHAMADOS DO GRUPO ITSM_TODOS (ENDPOINT V2)")
    print("="*80 + "\n")
    
    print(f"Ambiente: {ambiente}")
    print(f"Usuário: {ConfigEnvSetings.FLUIG_ADMIN_USER}")
    print(f"Grupo: Pool:Group:ITSM_TODOS")
    print(f"Status: NOT_COMPLETED")
    print(f"SLA Status: ON_TIME")
    print(f"Página: {page}")
    print(f"Registros por página: {page_size}\n")
    
    try:
        # Define o assignee como o grupo Pool:Group:ITSM_TODOS
        assignee_grupo = "Pool:Group:ITSM_TODOS"
        
        # Lista chamados usando endpoint v2 com o grupo
        print("Buscando chamados do grupo ITSM_TODOS usando endpoint v2...")
        fluig_core = FluigCore(ambiente=ambiente)
        resultado = fluig_core.listar_chamados_tasks(
            assignee=assignee_grupo,
            status="NOT_COMPLETED",
            sla_status="ON_TIME",
            page=page,
            page_size=page_size,
            usuario=ConfigEnvSetings.FLUIG_ADMIN_USER
        )
        
        if not resultado:
            print("[ERRO] Nenhum resultado retornado ou erro na requisição")
            return False
        
        # Exibe informações gerais
        items = resultado.get('items', [])
        has_next = resultado.get('hasNext', False)
        
        print(f"\n[OK] Requisição bem-sucedida!")
        print(f"   Total de registros nesta página: {len(items)}")
        print(f"   Tem próxima página: {has_next}\n")
        
        if len(items) == 0:
            print("[AVISO] Nenhum chamado encontrado para o grupo ITSM_TODOS")
            return True
        
        # Exibe detalhes dos chamados
        print("="*80)
        print("DETALHES DOS CHAMADOS")
        print("="*80 + "\n")
        
        for idx, chamado in enumerate(items, 1):
            process_instance_id = chamado.get('processInstanceId', 'N/A')
            process_id = chamado.get('processId', 'N/A')
            process_description = chamado.get('processDescription', 'N/A')
            movement_sequence = chamado.get('movementSequence', 'N/A')
            status = chamado.get('status', 'N/A')
            sla_status = chamado.get('slaStatus', 'N/A')
            start_date = chamado.get('startDate', 'N/A')
            assign_start_date = chamado.get('assignStartDate', 'N/A')
            
            # Informações do assignee
            assignee = chamado.get('assignee', {})
            assignee_name = assignee.get('name', 'N/A') if assignee else 'N/A'
            assignee_mail = assignee.get('mail', 'N/A') if assignee else 'N/A'
            assignee_id = assignee.get('id', 'N/A') if assignee else 'N/A'
            
            # Informações do requester
            requester = chamado.get('requester', {})
            requester_name = requester.get('name', 'N/A') if requester else 'N/A'
            requester_mail = requester.get('mail', 'N/A') if requester else 'N/A'
            
            # Informações do state
            state = chamado.get('state', {})
            state_name = state.get('stateName', 'N/A') if state else 'N/A'
            state_description = state.get('stateDescription', 'N/A') if state else 'N/A'
            
            print(f"Chamado {idx}:")
            print(f"   ID: {process_instance_id}")
            print(f"   Processo: {process_id}")
            print(f"   Descrição: {process_description}")
            print(f"   Sequência de movimento: {movement_sequence}")
            print(f"   Status: {status}")
            print(f"   SLA Status: {sla_status}")
            print(f"   Data de início: {start_date}")
            print(f"   Data de atribuição: {assign_start_date}")
            print(f"   Responsável ID: {assignee_id}")
            print(f"   Responsável: {assignee_name} ({assignee_mail})")
            print(f"   Solicitante: {requester_name} ({requester_mail})")
            print(f"   Estado: {state_name} - {state_description}")
            print()
        
        print("="*80)
        print("[OK] Teste concluído com sucesso!")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Testa listagem de chamados do grupo Pool:Group:ITSM_TODOS no Fluig (endpoint v2)'
    )
    parser.add_argument(
        '--ambiente', 
        type=str, 
        default='PRD', 
        choices=['PRD', 'QLD'],
        help='Ambiente do Fluig (PRD ou QLD)'
    )
    parser.add_argument(
        '--page', 
        type=int, 
        default=1,
        help='Número da página (padrão: 1)'
    )
    parser.add_argument(
        '--page_size', 
        '--page-size', 
        type=int, 
        default=1000,
        help='Quantidade de registros por página (padrão: 1000)'
    )
    
    args = parser.parse_args()
    
    print("\nIniciando teste de listagem de chamados do grupo ITSM_TODOS (endpoint v2)...\n")
    
    sucesso = test_listar_chamados_grupo_itsm_todos(
        ambiente=args.ambiente,
        page=args.page,
        page_size=args.page_size
    )
    
    if sucesso:
        print("\nTeste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\nTeste falhou!\n")
        sys.exit(1)
