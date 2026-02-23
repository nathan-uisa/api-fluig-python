"""
Script de teste para abertura de chamado no Fluig com anexo usando OAuth 1.0

Endpoint: /process-management/api/v2/processes/{processId}/start
processId: "Abertura de Chamados"

Fluxo:
1. Abre chamado usando OAuth 1.0
2. Faz upload do arquivo requirements.txt usando OAuth 1.0
3. Anexa o arquivo ao chamado usando OAuth 1.0
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, quote
import json

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.fluig.fluig_requests import RequestsFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def montar_payload_teste(usuario: str) -> Dict[str, Any]:
    """
    Monta um payload de teste simples para abertura de chamado.

    IMPORTANTE: Este payload é apenas para testes / homologação.
    Ajuste os campos conforme a necessidade do processo real.
    """
    return {
        "targetState": "0",
        "subProcessTargetState": "0",
        "targetAssignee": "f91b4d01ddc24241b2e1915657bebcd4",
        "formFields": {
            "ds_chamado": "Teste de chamado com anexo via OAuth 1.0",
            "nm_emitente": "Nathan Renner de Azevedo",
            "h_solicitante": "f91b4d01ddc24241b2e1915657bebcd4",
            "ds_cargo": "Assistente de Tecnologia da Informação",
            "NomeRegistrador": "nathan.azevedo@uisa.com.br",
            "ds_email_sol": "nathan.azevedo@uisa.com.br",
            "ds_secao": "Sistemas",
            "num_cr_elab": "110051404",
            "ds_empresa": "USINASITAMARATI",
            "ch_sap": "0",
            "num_tel_contato": "5565996345425",
            "ds_titulo": "Teste: Chamado com anexo (OAuth 1.0)",
            "dt_abertura": "19/11/2025 20: 11",
            "UsuarioAtendido": "Nathan Renner de Azevedo"
        }
    }


def montar_payload_anexar_arquivo(process_instance_id: int, nome_arquivo: str, admin_colleague_id: str, version: int = 57, current_movto: int = 3) -> Dict[str, Any]:
    """
    Monta payload para anexar arquivo ao chamado usando OAuth 1.0
    """
    return {
        "processId": "Abertura de Chamados",
        "version": version,
        "managerMode": False,
        "taskUserId": admin_colleague_id,
        "processInstanceId": process_instance_id,
        "isDigitalSigned": False,
        "selectedState": 5,
        "attachments": [
            {
                "id": 1,
                "fullPath": "BPM",
                "droppedZipZone": False,
                "name": nome_arquivo,
                "newAttach": True,
                "description": nome_arquivo,
                "documentId": 0,
                "attachedUser": "Infra Automação",
                "attachedActivity": "Aguardando Classificação",
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
                "iconClass": "fluigicon-file-upload",
                "iconUrl": False,
                "colleagueId": admin_colleague_id
            }
        ],
        "currentMovto": current_movto
    }


def ler_arquivo_requirements() -> Tuple[bytes, str]:
    """
    Lê o arquivo requirements.txt do diretório raiz do projeto
    
    Returns:
        Tupla (conteudo_bytes, nome_arquivo)
    """
    root_dir = Path(__file__).parent.parent.parent
    arquivo_path = root_dir / "requirements.txt"
    
    if not arquivo_path.exists():
        raise FileNotFoundError(f"Arquivo requirements.txt não encontrado em: {arquivo_path}")
    
    with open(arquivo_path, 'rb') as f:
        conteudo = f.read()
    
    return conteudo, "requirements.txt"


def test_abrir_chamado_com_anexo_oauth(
    ambiente: str = "PRD",
    process_id: str = "Abertura de Chamados",
    usuario: Optional[str] = None,
) -> bool:
    """
    Testa a abertura de chamado com anexo usando OAuth 1.0 (CK, CS, TK, TS).
    
    Fluxo:
    1. Abre chamado usando endpoint v2 com OAuth 1.0
    2. Faz upload do arquivo requirements.txt usando OAuth 1.0
    3. Anexa o arquivo ao chamado usando OAuth 1.0

    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_id: ID do processo no Fluig (padrão: "Abertura de Chamados")
        usuario: Usuário responsável pelo chamado (apenas para preencher campos de teste)
    """
    print("\n" + "=" * 80)
    print("TESTE: ABERTURA DE CHAMADO COM ANEXO (OAuth 1.0)")
    print("=" * 80 + "\n")

    usuario_teste = usuario or ConfigEnvSetings.FLUIG_ADMIN_USER

    print(f"Ambiente: {ambiente}")
    print(f"Process ID: {process_id}")
    print(f"Usuário teste (nm_emitente/ds_email_sol): {usuario_teste}")
    print()

    try:
        # Inicializa cliente com OAuth 1.0
        requests_fluig = RequestsFluig(ambiente=ambiente)

        # Determina URL base a partir das configs
        if ambiente.upper() == "PRD":
            base_url_raw = ConfigEnvSetings.URL_FLUIG_PRD
        elif ambiente.upper() == "QLD":
            base_url_raw = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            print(f"[ERRO] Ambiente inválido: {ambiente}")
            return False

        parsed_url = urlparse(base_url_raw)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # ==========================================
        # ETAPA 1: Abrir chamado
        # ==========================================
        print("\n" + "-" * 80)
        print("ETAPA 1: Abrindo chamado no Fluig")
        print("-" * 80 + "\n")

        # Monta URL do endpoint v2
        encoded_process_id = quote(process_id, safe="")
        url_abrir = f"{base_url}/process-management/api/v2/processes/{encoded_process_id}/start"

        print(f"URL: {url_abrir}\n")

        # Monta payload de teste
        payload = montar_payload_teste(usuario_teste)

        print("Payload de teste:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()

        # Faz requisição POST usando OAuth 1.0 (via RequestsFluig)
        print("Enviando requisição POST com OAuth 1.0...")
        resposta_abrir = requests_fluig.RequestTipoPOST(url_abrir, payload)

        print(f"\nStatus Code: {resposta_abrir.status_code}")
        print(f"Headers de resposta: {dict(resposta_abrir.headers)}\n")

        # Processa resposta
        if resposta_abrir.status_code != 200:
            print(f"[ERRO] Falha ao abrir chamado - Status: {resposta_abrir.status_code}")
            print(f"Resposta (texto): {resposta_abrir.text[:1500]}")
            return False

        try:
            dados_abrir = resposta_abrir.json()
            print("[OK] Chamado aberto com sucesso!")
            print("\nResposta JSON:")
            print(json.dumps(dados_abrir, indent=2, ensure_ascii=False))

            # Extrai processInstanceId
            process_instance_id = dados_abrir.get("processInstanceId") or dados_abrir.get("requestId")
            if not process_instance_id:
                print("\n[ERRO] processInstanceId não encontrado na resposta")
                return False

            print(f"\n[INFO] Chamado criado com processInstanceId: {process_instance_id}")
        except json.JSONDecodeError:
            print("[ERRO] Resposta não é JSON válido.")
            print(f"Resposta (texto): {resposta_abrir.text[:1000]}")
            return False

        # ==========================================
        # ETAPA 2: Upload do arquivo
        # ==========================================
        print("\n" + "-" * 80)
        print("ETAPA 2: Fazendo upload do arquivo requirements.txt")
        print("-" * 80 + "\n")

        # Lê o arquivo requirements.txt
        try:
            arquivo_bytes, nome_arquivo = ler_arquivo_requirements()
            print(f"[INFO] Arquivo lido: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
        except Exception as e:
            print(f"[ERRO] Falha ao ler arquivo requirements.txt: {str(e)}")
            return False

        # Obtém ADMIN_COLLEAGUE_ID
        admin_colleague_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
        if not admin_colleague_id or admin_colleague_id == "":
            print("[ERRO] ADMIN_COLLEAGUE_ID não configurado")
            return False

        print(f"[INFO] Usando Colleague ID: {admin_colleague_id}")

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
        except json.JSONDecodeError:
            print("[ERRO] Resposta do upload não é JSON válido.")
            print(f"Resposta (texto): {resposta_upload.text[:1000]}")
            return False

        # ==========================================
        # ETAPA 3: Anexar arquivo ao chamado
        # ==========================================
        print("\n" + "-" * 80)
        print("ETAPA 3: Anexando arquivo ao chamado")
        print("-" * 80 + "\n")

        # URL do endpoint saveAttachments
        url_anexar = f"{base_url}/ecm/api/rest/ecm/workflowView/saveAttachments"

        # Monta payload para anexar arquivo
        payload_anexar = montar_payload_anexar_arquivo(
            process_instance_id=process_instance_id,
            nome_arquivo=nome_arquivo,
            admin_colleague_id=admin_colleague_id
        )

        print("Payload para anexar arquivo:")
        print(json.dumps(payload_anexar, indent=2, ensure_ascii=False))
        print()

        # Headers para anexar arquivo
        # Nota: O RequestsFluig já tem headers padrão, mas para saveAttachments
        # precisamos de headers específicos. Vamos usar OAuth 1.0 diretamente.
        from src.auth.auth_fluig import AutenticarFluig
        auth, _ = AutenticarFluig(ambiente)
        
        headers_anexar = {
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }

        print(f"URL Anexar: {url_anexar}")
        print("Enviando requisição para anexar arquivo com OAuth 1.0...")

        import requests
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
                print(f"\n[OK] Arquivo {nome_arquivo} anexado com sucesso ao chamado {process_instance_id}")
            else:
                print(f"\n[AVISO] Resposta sem confirmação explícita de anexo, mas status 200")
        except json.JSONDecodeError:
            print("[ERRO] Resposta não é JSON válido.")
            print(f"Resposta (texto): {resposta_anexar.text[:1000]}")
            return False

        # ==========================================
        # RESUMO FINAL
        # ==========================================
        print("\n" + "=" * 80)
        print("[OK] Teste concluído com sucesso!")
        print("=" * 80)
        print(f"\nResumo:")
        print(f"  - Chamado criado: processInstanceId = {process_instance_id}")
        print(f"  - Arquivo enviado: {nome_arquivo} ({len(arquivo_bytes)} bytes)")
        print(f"  - Arquivo anexado ao chamado com sucesso")
        print("=" * 80 + "\n")
        return True

    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        print("[ERRO] Teste falhou!")
        print("=" * 80 + "\n")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Testa abertura de chamado com anexo no Fluig usando OAuth 1.0"
    )
    parser.add_argument(
        "--ambiente",
        type=str,
        default="PRD",
        choices=["PRD", "QLD"],
        help="Ambiente do Fluig (PRD ou QLD)",
    )
    parser.add_argument(
        "--process-id",
        "--process_id",
        type=str,
        default="Abertura de Chamados",
        help='ID do processo (padrão: "Abertura de Chamados")',
    )
    parser.add_argument(
        "--usuario",
        type=str,
        help="Usuário para preencher campos de teste (se não fornecido, usa FLUIG_ADMIN_USER)",
    )

    args = parser.parse_args()

    print("\nIniciando teste de abertura de chamado com anexo via OAuth 1.0...\n")

    sucesso = test_abrir_chamado_com_anexo_oauth(
        ambiente=args.ambiente,
        process_id=args.process_id,
        usuario=args.usuario,
    )

    if sucesso:
        print("\nTeste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\nTeste falhou!\n")
        sys.exit(1)
