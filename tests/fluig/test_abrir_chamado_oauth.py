"""
Script de teste para abertura de chamado no Fluig usando OAuth 1.0

Endpoint: /process-management/api/v2/processes/{processId}/start
processId: "Abertura de Chamados"
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
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
            "ds_chamado": "DescriçãodoChamado",
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
            "ds_titulo": "TítulodoChamado",
            "dt_abertura": "19/11/2025 20: 11",
            "UsuarioAtendido": "Nathan Renner de Azevedo"
        }
    }


def test_abrir_chamado_oauth(
    ambiente: str = "PRD",
    process_id: str = "Abertura de Chamados",
    usuario: Optional[str] = None,
) -> bool:
    """
    Testa a abertura de chamado usando o endpoint v2 /process-management/api/v2/processes/{processId}/start
    com autenticação OAuth 1.0 (CK, CS, TK, TS).

    Args:
        ambiente: Ambiente do Fluig ('PRD' ou 'QLD')
        process_id: ID do processo no Fluig (padrão: "Abertura de Chamados")
        usuario: Usuário responsável pelo chamado (apenas para preencher campos de teste)
    """
    print("\n" + "=" * 80)
    print("TESTE: ABERTURA DE CHAMADO (ENDPOINT V2 - OAuth 1.0)")
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

        # Monta URL do endpoint v2
        encoded_process_id = quote(process_id, safe="")
        url = f"{base_url}/process-management/api/v2/processes/{encoded_process_id}/start"

        print(f"URL: {url}\n")

        # Monta payload de teste
        payload = montar_payload_teste(usuario_teste)

        print("Payload de teste:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()

        # Faz requisição POST usando OAuth 1.0 (via RequestsFluig)
        print("Enviando requisição POST com OAuth 1.0...")
        resposta = requests_fluig.RequestTipoPOST(url, payload)

        print(f"\nStatus Code: {resposta.status_code}")
        print(f"Headers de resposta: {dict(resposta.headers)}\n")

        # Processa resposta
        if resposta.status_code == 200:
            try:
                dados = resposta.json()
                print("[OK] Requisição bem-sucedida!")
                print("\nResposta JSON:")
                print(json.dumps(dados, indent=2, ensure_ascii=False))

                # Tenta extrair processInstanceId, se existir
                process_instance_id = dados.get("processInstanceId") or dados.get("requestId")
                if process_instance_id:
                    print(f"\n[INFO] Chamado criado com processInstanceId: {process_instance_id}")
            except json.JSONDecodeError:
                print("[AVISO] Resposta não é JSON válido.")
                print(f"Resposta (texto): {resposta.text[:1000]}")

            print("\n" + "=" * 80)
            print("[OK] Teste concluído com sucesso!")
            print("=" * 80 + "\n")
            return True
        else:
            print(f"[ERRO] Requisição falhou com status {resposta.status_code}")
            print(f"Resposta (texto): {resposta.text[:1500]}")
            print("\n" + "=" * 80)
            print("[ERRO] Teste falhou!")
            print("=" * 80 + "\n")
            return False

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
        description="Testa abertura de chamado no Fluig usando endpoint v2 com OAuth 1.0"
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

    print("\nIniciando teste de abertura de chamado via OAuth 1.0...\n")

    sucesso = test_abrir_chamado_oauth(
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

