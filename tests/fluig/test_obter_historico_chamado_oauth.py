"""
Script de teste para obter histórico de um chamado no Fluig usando OAuth 1.0

IMPORTANTE: Este teste usa exclusivamente autenticação OAuth 1.0 (CK, CS, TK, TS)
e não utiliza cookies ou autenticação via navegador.
"""
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import requests

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_core import FluigCore
from src.fluig.fluig_requests import RequestsFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def test_obter_historico_chamado_oauth(
    ambiente: str = "PRD",
    process_instance_id: int = 694107,
    page: int = 1,
    page_size: int = 1000
):
    """
    Testa a obtenção do histórico de um chamado usando o endpoint GET 
    /process-management/api/v2/requests/{processInstanceId}/histories
    com autenticação OAuth 1.0
    
    IMPORTANTE: Usa exclusivamente OAuth 1.0 (CK, CS, TK, TS) - não utiliza cookies
    
    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_instance_id: ID da instância do processo (número do chamado)
        page: Número da página (padrão: 1)
        page_size: Quantidade de registros por página (padrão: 1000)
    """
    print("\n" + "="*80)
    print("TESTE: OBTER HISTÓRICO DE CHAMADO NO FLUIG (OAuth 1.0)")
    print("="*80 + "\n")
    
    print(f"Ambiente: {ambiente}")
    print(f"Process Instance ID: {process_instance_id}")
    print(f"Page: {page}")
    print(f"Page Size: {page_size}")
    print()
    
    try:
        # Inicializa FluigCore para obter URL base
        fluig_core = FluigCore(ambiente=ambiente)
        url_base = fluig_core.url_base
        
        # Monta parâmetros da query string
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        # Monta URL do endpoint com parâmetros já na query string
        # Isso garante que o OAuth 1.0 assine corretamente a URL completa
        endpoint = f"/process-management/api/v2/requests/{process_instance_id}/histories"
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
        
        # Adiciona header accept
        headers = requests_fluig.headers.copy()
        headers['accept'] = 'application/json; charset=UTF-8'
        
        # Faz requisição GET usando OAuth 1.0 
        # Passa URL completa sem params separados para garantir assinatura correta
        print("Enviando requisição GET com OAuth 1.0...")
        logger.info(f"[test_obter_historico_chamado_oauth] Fazendo requisição GET para {url} usando OAuth 1.0")
        logger.debug(f"[test_obter_historico_chamado_oauth] Parâmetros: {params}")
        logger.debug(f"[test_obter_historico_chamado_oauth] Autenticação: OAuth 1.0")
        
        # Usa requests diretamente com OAuth 1.0, passando URL completa sem params separados
        resposta = requests.get(url, headers=headers, auth=requests_fluig.auth, timeout=15)
        
        print(f"\nStatus Code: {resposta.status_code}")
        print(f"Response Headers: {dict(resposta.headers)}\n")
        
        logger.info(f"[test_obter_historico_chamado_oauth] Status Code: {resposta.status_code}")
        
        # Processa resposta
        if resposta.status_code == 200:
            print("[OK] Requisição bem-sucedida!")
            
            # Tenta parsear como JSON
            try:
                import json
                from datetime import datetime
                resultado = resposta.json()
                logger.info(f"[test_obter_historico_chamado_oauth] Resposta JSON recebida com sucesso")
                
                # Exibe informações resumidas
                if isinstance(resultado, dict):
                    items = resultado.get("items", [])
                    total_items = len(items)
                    has_next = resultado.get("hasNext", False)
                    
                    print("\n" + "="*80)
                    print("RESUMO DO HISTÓRICO")
                    print("="*80)
                    print(f"Total de itens: {total_items}")
                    print(f"Tem próxima página: {'Sim' if has_next else 'Não'}")
                    
                    # Conta itens por tipo
                    tipos_contagem = {}
                    for item in items:
                        tipo = item.get("type", "UNKNOWN")
                        tipos_contagem[tipo] = tipos_contagem.get(tipo, 0) + 1
                    
                    if tipos_contagem:
                        print("\nContagem por tipo:")
                        for tipo, count in sorted(tipos_contagem.items()):
                            print(f"  - {tipo}: {count}")
                    
                    # Exibe resumo dos itens (ordenado por movimento: mais antigo primeiro)
                    if items:
                        print("\n" + "-"*80)
                        print("HISTÓRICO DO CHAMADO (do mais antigo para o mais recente):")
                        print("-"*80)
                        
                        # Ordena itens por movimento sequence (crescente) e depois por data (crescente)
                        # Para MOVEMENT, ordena por movementSequence
                        # Para outros tipos, ordena por data
                        def ordenar_item(item):
                            tipo = item.get("type", "")
                            if tipo == "MOVEMENT":
                                mov_seq = item.get("movementSequence", 0)
                                data_str = item.get("date", "")
                                # Retorna tupla: (movementSequence, timestamp)
                                try:
                                    if data_str:
                                        dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                                        timestamp = dt.timestamp()
                                    else:
                                        timestamp = 0
                                except:
                                    timestamp = 0
                                return (mov_seq, timestamp)
                            else:
                                # Para outros tipos, ordena por data
                                data_str = item.get("date", "")
                                try:
                                    if data_str:
                                        dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                                        timestamp = dt.timestamp()
                                    else:
                                        timestamp = 0
                                except:
                                    timestamp = 0
                                # Usa movementSequence como segundo critério se disponível
                                mov_seq = item.get("movementSequence", 999999)
                                return (mov_seq, timestamp)
                        
                        # Ordena itens (mais antigo primeiro)
                        items_ordenados = sorted(items, key=ordenar_item)
                        
                        # Mostra os primeiros 10 itens (mais antigos)
                        items_para_exibir = items_ordenados[:10]
                        
                        for idx, item in enumerate(items_para_exibir, 1):
                            tipo = item.get("type", "UNKNOWN")
                            data_str = item.get("date", "")
                            usuario = item.get("user", {})
                            usuario_nome = usuario.get("name", "N/A")
                            
                            # Formata data
                            try:
                                if data_str:
                                    # Tenta parsear a data
                                    dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                                    data_formatada = dt.strftime("%d/%m/%Y %H:%M:%S")
                                else:
                                    data_formatada = "N/A"
                            except:
                                data_formatada = data_str[:19] if data_str else "N/A"
                            
                            print(f"\n[{idx}] Tipo: {tipo} | Data: {data_formatada} | Usuário: {usuario_nome}")
                            
                            # Informações específicas por tipo
                            if tipo == "OBSERVATION":
                                obs_desc = item.get("observationDescription", "N/A")
                                obs_id = item.get("observationId", "N/A")
                                mov_seq = item.get("movementSequence", "N/A")
                                print(f"     Observação ID: {obs_id} | Movimento: {mov_seq}")
                                print(f"     Descrição: {obs_desc}")
                            
                            elif tipo == "ATTACHMENT":
                                att_desc = item.get("attachmentDescription", "N/A")
                                att_id = item.get("attachmentId", "N/A")
                                att_vers = item.get("attachmentVersion", "N/A")
                                mov_seq = item.get("movementSequence", "N/A")
                                print(f"     Anexo ID: {att_id} | Versão: {att_vers} | Movimento: {mov_seq}")
                                print(f"     Arquivo: {att_desc}")
                            
                            elif tipo == "MOVEMENT":
                                state = item.get("state", {})
                                target_state = item.get("targetState", {})
                                state_name = state.get("stateName", "N/A")
                                target_name = target_state.get("stateName", "N/A")
                                mov_seq = item.get("movementSequence", "N/A")
                                obs_desc = item.get("observationDescription", "")
                                
                                print(f"     Movimento: {mov_seq} | De: {state_name} → Para: {target_name}")
                                if obs_desc:
                                    print(f"     Descrição: {obs_desc}")
                                
                                # Mostra assignees se houver
                                chosen_assignees = item.get("chosenAssignees", [])
                                if chosen_assignees:
                                    assignees_nomes = [a.get("name", "N/A") for a in chosen_assignees[:3]]
                                    print(f"     Responsáveis: {', '.join(assignees_nomes)}")
                                    if len(chosen_assignees) > 3:
                                        print(f"     ... e mais {len(chosen_assignees) - 3}")
                        
                        if total_items > 10:
                            print(f"\n... e mais {total_items - 10} evento(s) posterior(es) (mais recentes)")
                    
                    print("\n" + "="*80)
                
            except Exception as e:
                print(f"\n[AVISO] Não foi possível parsear como JSON: {str(e)}")
                print(f"Resposta (texto): {resposta.text[:1000]}")
                logger.debug(f"[test_obter_historico_chamado_oauth] Resposta não é JSON válido: {resposta.text[:500]}")
            
            print("\n" + "="*80)
            print("[OK] Teste concluído com sucesso!")
            print("="*80 + "\n")
            return True
        else:
            print(f"[ERRO] Requisição falhou com status {resposta.status_code}")
            print(f"Resposta: {resposta.text[:1000]}")
            logger.error(f"[test_obter_historico_chamado_oauth] Erro na requisição: Status {resposta.status_code}, Resposta: {resposta.text[:500]}")
            print("\n" + "="*80)
            print("[ERRO] Teste falhou!")
            print("="*80 + "\n")
            return False
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"[test_obter_historico_chamado_oauth] Erro durante o teste: {str(e)}", exc_info=True)
        print("\n" + "="*80)
        print("[ERRO] Teste falhou!")
        print("="*80 + "\n")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Testa obtenção de histórico de chamado no Fluig usando endpoint histories com OAuth 1.0'
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
        default=657984,
        help='ID da instância do processo (número do chamado)'
    )
    parser.add_argument(
        '--page',
        type=int,
        default=1,
        help='Número da página (padrão: 1)'
    )
    parser.add_argument(
        '--page-size',
        '--page_size',
        type=int,
        default=1000,
        help='Quantidade de registros por página (padrão: 1000)'
    )
    
    args = parser.parse_args()
    
    # Solicita process_instance_id no terminal
    process_instance_id = None
    if args.process_instance_id and args.process_instance_id != 657984:
        # Se foi fornecido via argumento e não é o padrão, usa ele
        process_instance_id = args.process_instance_id
        print(f"\nProcess Instance ID informado via argumento: {process_instance_id}")
    else:
        # Solicita no terminal
        try:
            while True:
                entrada = input("\nDigite o Process Instance ID (número do chamado): ").strip()
                if entrada:
                    try:
                        process_instance_id = int(entrada)
                        break
                    except ValueError:
                        print("[ERRO] Por favor, digite um número válido.")
                else:
                    print("[ERRO] Process Instance ID é obrigatório.")
        except KeyboardInterrupt:
            print("\n\nOperação cancelada pelo usuário.")
            sys.exit(1)
    
    print("\nIniciando teste de obtenção de histórico de chamado com OAuth 1.0...\n")
    
    sucesso = test_obter_historico_chamado_oauth(
        ambiente=args.ambiente,
        process_instance_id=process_instance_id,
        page=args.page,
        page_size=args.page_size
    )
    
    if sucesso:
        print("\nTeste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\nTeste falhou!\n")
        sys.exit(1)
