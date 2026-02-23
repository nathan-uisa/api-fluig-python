"""
Script de teste para anexar arquivo a um chamado existente no Fluig usando OAuth 1.0

Este teste simula o comportamento do endpoint:
/api/v1/fluig/{ambiente}/processos/anexar-upload

Fluxo:
1. Faz upload do arquivo usando OAuth 1.0 (/ecm/upload)
2. Obtém detalhes da atividade para extrair processVersion e movementSequence automaticamente
3. Anexa o arquivo ao chamado usando OAuth 1.0 (saveAttachments)

IMPORTANTE: Este teste usa apenas OAuth 1.0, sem chamar o endpoint da API.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import json
import time

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_requests import RequestsFluig
from src.fluig.fluig_core import FluigCore
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.auth.auth_fluig import AutenticarFluig
import requests


def ler_arquivo_requirements() -> Tuple[bytes, str]:
    """
    Lê o arquivo requirements.txt do projeto para usar no teste.
    
    Returns:
        Tupla com (conteudo_bytes, nome_arquivo)
    """
    root_dir = Path(__file__).parent.parent.parent
    arquivo_path = root_dir / "requirements.txt"
    
    if not arquivo_path.exists():
        # Se não existir requirements.txt, cria um arquivo de teste
        conteudo_teste = b"# Arquivo de teste para anexo\n# Gerado automaticamente pelo teste\n"
        return conteudo_teste, "teste_anexo.txt"
    
    with open(arquivo_path, 'rb') as f:
        conteudo = f.read()
    
    return conteudo, arquivo_path.name


def montar_payload_anexar_arquivo(
    process_id: str,
    process_instance_id: int,
    nome_arquivo: str,
    version: int = 57,
    current_movto: int = 3,
    document_id: int = 0,
    attached_activity: str = "Aguardando Classificação"
) -> Dict[str, Any]:
    """
    Monta payload para anexar arquivo ao chamado usando OAuth 1.0
    
    Args:
        process_id: ID/Nome do processo (ex: "Abertura de Chamados")
        process_instance_id: ID da instância do processo (Número do chamado)
        nome_arquivo: Nome do arquivo
        version: Versão do processo (padrão: 57)
        current_movto: Movimento atual (padrão: 3)
        document_id: ID do documento (padrão: 0 para arquivos enviados via upload)
        attached_activity: Nome da atividade
    """
    # Gera internal_id (timestamp em milissegundos)
    internal_id = int(time.time() * 1000)
    
    return {
        "processId": process_id,
        "version": version,
        "managerMode": False,
        "processInstanceId": process_instance_id,
        "isDigitalSigned": False,
        "selectedState": 5,
        "attachments": [
            {
                "id": 1,
                "fullPath": "BPM",
                "droppedZipZone": False,
                "name": nome_arquivo,
                "internalId": internal_id,
                "newAttach": True,
                "description": nome_arquivo,
                "documentId": document_id,
                "attachedActivity": attached_activity,
                "attachments": [
                    {
                        "attach": False,
                        "principal": True,
                        "fileName": nome_arquivo
                    }
                ],
                "hasOwnSubMenu": True,
                "enablePublish": False,
                "enableEdit": False,
                "enableEditContent": False,
                "fromUpload": True,
                "enableDownload": True,
                "hasMoreOptions": False,
                "deleted": False,
                "iconClass": "fluigicon-file-upload",
                "iconUrl": False
            }
        ],
        "currentMovto": current_movto
    }


def test_anexar_arquivo_upload_oauth(
    ambiente: str = "PRD",
    process_id: str = "Abertura de Chamados",
    process_instance_id: Optional[int] = None,
    nome_arquivo: Optional[str] = None,
    arquivo_bytes: Optional[bytes] = None
) -> bool:
    """
    Testa o anexo de arquivo a um chamado existente usando OAuth 1.0.
    
    Este teste simula o comportamento do endpoint /anexar-upload sem chamar a API.
    Faz upload e anexa o arquivo diretamente usando OAuth 1.0.
    
    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_id: ID do processo no Fluig (padrão: "Abertura de Chamados")
        process_instance_id: ID da instância do processo (Número do chamado). Se None, pede ao usuário.
        nome_arquivo: Nome do arquivo para anexar. Se None, usa requirements.txt
        arquivo_bytes: Conteúdo do arquivo em bytes. Se None, lê requirements.txt
    
    Returns:
        True se o teste passou, False caso contrário
    """
    print("\n" + "=" * 80)
    print("TESTE: ANEXAR ARQUIVO A CHAMADO EXISTENTE (OAuth 1.0)")
    print("=" * 80 + "\n")
    
    print(f"Ambiente: {ambiente}")
    print(f"Process ID: {process_id}")
    
    # Valida ambiente
    if ambiente.upper() not in ["PRD", "QLD"]:
        print(f"[ERRO] Ambiente inválido: {ambiente}. Use 'PRD' ou 'QLD'")
        return False
    
    ambiente = ambiente.upper()
    
    # Obtém process_instance_id se não fornecido
    if not process_instance_id:
        try:
            process_instance_id_input = input("\nDigite o número do chamado (processInstanceId) para anexar o arquivo: ")
            process_instance_id = int(process_instance_id_input.strip())
        except (ValueError, KeyboardInterrupt):
            print("[ERRO] process_instance_id inválido ou cancelado")
            return False
    
    print(f"Process Instance ID: {process_instance_id}")
    print()
    
    # Obtém arquivo para anexar
    if not arquivo_bytes or not nome_arquivo:
        try:
            arquivo_bytes, nome_arquivo = ler_arquivo_requirements()
            print(f"[INFO] Arquivo para anexar: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
        except Exception as e:
            print(f"[ERRO] Falha ao ler arquivo: {str(e)}")
            return False
    else:
        print(f"[INFO] Arquivo para anexar: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
    
    # Obtém ADMIN_COLLEAGUE_ID
    admin_colleague_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
    if not admin_colleague_id or admin_colleague_id == "":
        print("[ERRO] ADMIN_COLLEAGUE_ID não configurado")
        return False
    
    print(f"[INFO] Usando Colleague ID: {admin_colleague_id}")
    print()
    
    try:
        # Inicializa cliente com OAuth 1.0
        requests_fluig = RequestsFluig(ambiente=ambiente)
        base_url = requests_fluig.url
        
        print(f"[INFO] URL Base: {base_url}")
        print()
        
        # ==========================================
        # ETAPA 1: Upload do arquivo
        # ==========================================
        print("-" * 80)
        print("ETAPA 1: Fazendo upload do arquivo")
        print("-" * 80 + "\n")
        
        # URL do endpoint de upload
        url_upload = f"{base_url}/ecm/upload"
        
        # Prepara arquivo para multipart/form-data
        files = {
            'files': (nome_arquivo, arquivo_bytes, 'application/octet-stream')
        }
        
        data = {
            'userId': admin_colleague_id
        }
        
        print(f"URL Upload: {url_upload}")
        print(f"Arquivo: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
        print(f"userId: {admin_colleague_id}\n")
        
        # Faz upload usando OAuth 1.0
        print("Enviando arquivo para upload com OAuth 1.0...")
        resposta_upload = requests_fluig.RequestTipoPOSTMultipart(
            url=url_upload,
            files=files,
            data=data,
            timeout=60
        )
        
        print(f"\nStatus Code: {resposta_upload.status_code}")
        
        if resposta_upload.status_code != 200:
            print(f"[ERRO] Falha no upload - Status: {resposta_upload.status_code}")
            print(f"Resposta (texto): {resposta_upload.text[:1000]}")
            return False
        
        try:
            resultado_upload = resposta_upload.json()
            print("[OK] Upload realizado com sucesso!")
            print("\nResposta JSON:")
            print(json.dumps(resultado_upload, indent=2, ensure_ascii=False))
            
            # Verifica se há erro no conteúdo da resposta
            if 'files' in resultado_upload and len(resultado_upload['files']) > 0:
                primeiro_arquivo = resultado_upload['files'][0]
                if 'error' in primeiro_arquivo:
                    print(f"\n[ERRO] Erro no upload: {primeiro_arquivo['error']}")
                    return False
            else:
                print("\n[AVISO] Resposta do upload não contém 'files'")
        except json.JSONDecodeError:
            print("[ERRO] Resposta do upload não é JSON válido.")
            print(f"Resposta (texto): {resposta_upload.text[:1000]}")
            return False
        
        # ==========================================
        # ETAPA 2: Obter detalhes da atividade para processVersion e movementSequence
        # ==========================================
        print("\n" + "-" * 80)
        print("ETAPA 2: Obtendo detalhes da atividade")
        print("-" * 80 + "\n")
        
        # Inicializa FluigCore para obter detalhes da atividade
        fluig_core = FluigCore(ambiente=ambiente)
        
        print(f"Buscando detalhes das atividades do chamado {process_instance_id}...")
        detalhes_atividade = fluig_core.obter_detalhes_atividade(process_instance_id=process_instance_id)
        
        if not detalhes_atividade:
            print("[ERRO] Não foi possível obter detalhes da atividade")
            return False
        
        # Extrai processVersion e movementSequence
        items = detalhes_atividade.get('items', [])
        if not items:
            print("[ERRO] Nenhuma atividade encontrada para o chamado")
            return False
        
        # Busca a atividade ativa (active: true) ou usa a última
        atividade_ativa = None
        for item in items:
            if item.get('active', False):
                atividade_ativa = item
                break
        
        # Se não encontrar atividade ativa, usa a última
        if not atividade_ativa:
            atividade_ativa = items[-1]
            print("[AVISO] Nenhuma atividade ativa encontrada, usando a última atividade")
        
        process_version = atividade_ativa.get('processVersion')
        movement_sequence = atividade_ativa.get('movementSequence')
        state_name = atividade_ativa.get('state', {}).get('stateName', 'Aguardando Classificação')
        
        print(f"[INFO] Process Version: {process_version}")
        print(f"[INFO] Movement Sequence: {movement_sequence}")
        print(f"[INFO] State Name: {state_name}")
        print()
        
        # ==========================================
        # ETAPA 3: Anexar arquivo ao chamado
        # ==========================================
        print("-" * 80)
        print("ETAPA 3: Anexando arquivo ao chamado")
        print("-" * 80 + "\n")
        
        # URL do endpoint saveAttachments
        url_anexar = f"{base_url}/ecm/api/rest/ecm/workflowView/saveAttachments"
        
        # Monta payload para anexar arquivo usando valores obtidos automaticamente
        # O endpoint /ecm/upload não retorna document_id, então usamos documentId: 0
        payload_anexar = montar_payload_anexar_arquivo(
            process_id=process_id,
            process_instance_id=process_instance_id,
            nome_arquivo=nome_arquivo,
            version=process_version,
            current_movto=movement_sequence,
            document_id=0,  # Usa 0 para arquivos enviados via upload
            attached_activity=state_name
        )
        
        print("Payload para anexar arquivo:")
        print(json.dumps(payload_anexar, indent=2, ensure_ascii=False))
        print()
        
        # Headers para anexar arquivo
        headers_anexar = {
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Obtém autenticação OAuth 1.0
        auth, _ = AutenticarFluig(ambiente)
        
        print(f"URL Anexar: {url_anexar}")
        print("Enviando requisição para anexar arquivo com OAuth 1.0...")
        
        resposta_anexar = requests.post(
            url_anexar,
            json=payload_anexar,
            headers=headers_anexar,
            auth=auth,
            timeout=30
        )
        
        print(f"\nStatus Code: {resposta_anexar.status_code}")
        
        if resposta_anexar.status_code != 200:
            print(f"[ERRO] Falha ao anexar arquivo - Status: {resposta_anexar.status_code}")
            print(f"Resposta (texto): {resposta_anexar.text[:1000]}")
            return False
        
        try:
            resultado_anexar = resposta_anexar.json()
            print("[OK] Arquivo anexado com sucesso!")
            print("\nResposta JSON:")
            print(json.dumps(resultado_anexar, indent=2, ensure_ascii=False))
            
            # Verifica se há erro na resposta
            if resultado_anexar.get("content") == "ERROR" or resultado_anexar.get("message"):
                mensagem_erro = resultado_anexar.get("message", {})
                if isinstance(mensagem_erro, dict):
                    erro_msg = mensagem_erro.get("message", "Erro desconhecido")
                else:
                    erro_msg = str(mensagem_erro)
                print(f"\n[ERRO] Erro retornado pelo Fluig: {erro_msg}")
                return False
            
            # Verifica se anexou com sucesso
            content = resultado_anexar.get("content", {})
            if content and content.get("hasNewAttachment"):
                print("\n[OK] Confirmação: Arquivo anexado com sucesso ao chamado!")
            else:
                print("\n[AVISO] Resposta sem confirmação explícita de anexo, mas status 200")
            
            print("\n" + "=" * 80)
            print("TESTE CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            return True
            
        except json.JSONDecodeError:
            print("[ERRO] Resposta do anexo não é JSON válido.")
            print(f"Resposta (texto): {resposta_anexar.text[:1000]}")
            return False
            
    except Exception as e:
        print(f"\n[ERRO] Erro inesperado durante o teste: {str(e)}")
        import traceback
        print("\nTraceback:")
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    """
    Executa o teste quando o script é chamado diretamente.
    
    Exemplo de uso:
        python tests/fluig/test_anexar_arquivo_upload_oauth.py
        
    Ou com parâmetros:
        python tests/fluig/test_anexar_arquivo_upload_oauth.py PRD 657984
    """
    import sys
    
    ambiente = "PRD"
    process_instance_id = None
    
    if len(sys.argv) > 1:
        ambiente = sys.argv[1].upper()
    
    if len(sys.argv) > 2:
        try:
            process_instance_id = int(sys.argv[2])
        except ValueError:
            print(f"[ERRO] process_instance_id inválido: {sys.argv[2]}")
            sys.exit(1)
    
    sucesso = test_anexar_arquivo_upload_oauth(
        ambiente=ambiente,
        process_instance_id=process_instance_id
    )
    
    sys.exit(0 if sucesso else 1)
