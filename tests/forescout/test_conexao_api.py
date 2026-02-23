"""
Script de teste para realizar conexão com a API do Forescout

Este teste verifica se é possível conectar à API do Forescout utilizando
as credenciais configuradas nas variáveis de ambiente:
- FORESCOUT_HOST: Host do servidor Forescout
- FORESCOUT_USER: Usuário para autenticação
- FORESCOUT_PASS: Senha para autenticação

A URL será construída automaticamente usando HTTPS (https://FORESCOUT_HOST).

Documentação: https://docs.forescout.com/
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
import base64

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import requests
from requests.auth import HTTPBasicAuth
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def test_conexao_forescout(
    url: Optional[str] = None,
    host: Optional[str] = None,
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
    endpoint_teste: str = "/api/hosts",
    tentar_endpoint_alternativo: bool = True
) -> bool:
    """
    Testa a conexão com a API do Forescout utilizando autenticação básica.
    
    Args:
        url: URL base da API do Forescout (se None, será construída a partir de FORESCOUT_HOST)
        host: Host do servidor Forescout (se None, usa FORESCOUT_HOST do .env)
             Se URL não for fornecida, será construída a partir do host usando HTTPS
        usuario: Usuário para autenticação (se None, usa FORESCOUT_USER do .env)
        senha: Senha para autenticação (se None, usa FORESCOUT_PASS do .env)
        endpoint_teste: Endpoint para testar a conexão (padrão: /api/hosts)
        tentar_endpoint_alternativo: Se True, tenta /api/version se o endpoint falhar (padrão: True)
    
    Returns:
        True se a conexão foi bem-sucedida (mesmo que o endpoint não exista, mas autenticação funcionou),
        False caso contrário
    """
    print("\n" + "=" * 80)
    print("TESTE: CONEXÃO COM API FORESCOUT")
    print("=" * 80 + "\n")
    
    # Obtém credenciais das variáveis de ambiente ou parâmetros
    host_forescout = host or getattr(ConfigEnvSetings, 'FORESCOUT_HOST', '')
    usuario_teste = usuario or getattr(ConfigEnvSetings, 'FORESCOUT_USER', '')
    senha_teste = senha or getattr(ConfigEnvSetings, 'FORESCOUT_PASS', '')
    
    # Constrói URL a partir do HOST
    if url:
        url_base = url.rstrip('/')
    elif host_forescout:
        # Remove protocolo se estiver presente no host
        host_limpo = host_forescout.replace('https://', '').replace('http://', '').strip('/')
        # Constrói URL usando HTTPS por padrão
        url_base = f"https://{host_limpo}"
        print(f"[INFO] URL construída a partir de FORESCOUT_HOST: {url_base}")
    else:
        print("[ERRO] Host do Forescout não configurado")
        print("[INFO] Configure FORESCOUT_HOST no arquivo .env")
        print("       Exemplo: FORESCOUT_HOST=forescout.example.com")
        return False
    
    if not usuario_teste:
        print("[ERRO] Usuário do Forescout não configurado")
        print("[INFO] Configure FORESCOUT_USER no arquivo .env")
        return False
    
    if not senha_teste:
        print("[ERRO] Senha do Forescout não configurada")
        print("[INFO] Configure FORESCOUT_PASS no arquivo .env")
        return False
    
    # Remove barra final da URL se existir
    url_base = url_base.rstrip('/')
    
    # Monta URL completa do endpoint
    url_completa = f"{url_base}{endpoint_teste}"
    
    print(f"Host: {host_forescout or 'N/A'}")
    print(f"URL Base: {url_base}")
    print(f"Endpoint: {endpoint_teste}")
    print(f"URL Completa: {url_completa}")
    print(f"Usuário: {usuario_teste}")
    print(f"Senha: {'*' * len(senha_teste)}")
    print()
    
    try:
        # Configura headers padrão
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Tenta autenticação básica (método mais comum)
        print("1. Tentando autenticação básica (HTTP Basic Auth)...")
        logger.info(f"[test_conexao_forescout] Tentando conectar à API do Forescout: {url_completa}")
        
        auth = HTTPBasicAuth(usuario_teste, senha_teste)
        
        # Faz requisição GET para testar a conexão
        resposta = requests.get(
            url_completa,
            auth=auth,
            headers=headers,
            timeout=30,
            verify=True  # Verifica certificado SSL (ajuste para False se necessário)
        )
        
        print(f"   Status Code: {resposta.status_code}")
        print(f"   Headers de Resposta: {dict(resposta.headers)}\n")
        
        # Processa resposta
        if resposta.status_code == 200:
            print("[OK] Conexão bem-sucedida!")
            try:
                dados = resposta.json()
                print("\nResposta JSON:")
                print(json.dumps(dados, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(dados, indent=2, ensure_ascii=False)) > 1000:
                    print("... (resposta truncada)")
            except json.JSONDecodeError:
                print(f"\nResposta (texto): {resposta.text[:500]}")
            
            print("\n" + "=" * 80)
            print("[OK] Teste de conexão concluído com sucesso!")
            print("=" * 80 + "\n")
            logger.info("[test_conexao_forescout] Conexão com API do Forescout bem-sucedida")
            return True
            
        elif resposta.status_code == 401:
            print("[ERRO] Falha na autenticação (401 Unauthorized)")
            print("[INFO] Verifique se as credenciais FORESCOUT_USER e FORESCOUT_PASS estão corretas")
            print(f"Resposta: {resposta.text[:500]}")
            
            # Tenta método alternativo: autenticação via token
            print("\n2. Tentando autenticação via token (método alternativo)...")
            return testar_autenticacao_token(url_base, usuario_teste, senha_teste, endpoint_teste)
            
        elif resposta.status_code == 403:
            print("[ERRO] Acesso negado (403 Forbidden)")
            print("[INFO] O usuário pode não ter permissões suficientes")
            print(f"Resposta: {resposta.text[:500]}")
            return False
            
        elif resposta.status_code == 404:
            print("[AVISO] Endpoint não encontrado (404)")
            print(f"[INFO] O endpoint '{endpoint_teste}' pode não existir")
            
            # Mostra o conteúdo da resposta para ajudar no debug
            try:
                resposta_json = resposta.json()
                print(f"Resposta do servidor: {json.dumps(resposta_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"Resposta do servidor (texto): {resposta.text[:500]}")
            
            # Verifica se recebeu cookies (indica que autenticação pode estar funcionando)
            cookies_recebidos = 'Set-Cookie' in resposta.headers or 'JSESSIONID' in str(resposta.headers)
            if cookies_recebidos:
                print("\n[INFO] ✓ Cookies recebidos (JSESSIONID) - autenticação funcionando!")
                print("[INFO] O problema é apenas que o endpoint não existe")
                print("[INFO] Consulte a documentação do Forescout para encontrar o endpoint correto")
                
                # Se já tentou o endpoint alternativo ou não deve tentar, considera sucesso parcial
                if not tentar_endpoint_alternativo or endpoint_teste == "/api/hosts":
                    print("\n" + "=" * 80)
                    print("[OK] Conexão e autenticação bem-sucedidas!")
                    print("[AVISO] Endpoint não encontrado - verifique a documentação da API")
                    print("=" * 80 + "\n")
                    logger.info("[test_conexao_forescout] Autenticação funcionou, mas endpoint não existe")
                    return True  # Considera sucesso - autenticação funcionou
            
            # Tenta endpoint alternativo apenas se ainda não tentou e não é o mesmo endpoint
            if tentar_endpoint_alternativo and endpoint_teste != "/api/hosts":
                print("\n[INFO] Tentando endpoint alternativo: /api/hosts")
                return test_conexao_forescout(
                    url=url_base,
                    host=host_forescout,
                    usuario=usuario_teste,
                    senha=senha_teste,
                    endpoint_teste="/api/hosts",
                    tentar_endpoint_alternativo=False  # Evita loop infinito
                )
            else:
                if not cookies_recebidos:
                    print("\n[ERRO] Endpoint alternativo também retornou 404 ou já foi tentado")
                    print("[INFO] Verifique a documentação da API do Forescout para o endpoint correto")
                    return False
                else:
                    # Já retornou True acima se cookies foram recebidos
                    return True
            
        else:
            print(f"[ERRO] Requisição falhou com status {resposta.status_code}")
            print(f"Resposta: {resposta.text[:1000]}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"[ERRO] Erro de SSL: {str(e)}")
        print("[INFO] Se estiver usando certificado auto-assinado, pode ser necessário")
        print("       ajustar a verificação SSL no código")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"[ERRO] Erro de conexão: {str(e)}")
        print("[INFO] Verifique se a URL está correta e se o servidor está acessível")
        return False
        
    except requests.exceptions.Timeout:
        print("[ERRO] Timeout na requisição")
        print("[INFO] O servidor pode estar demorando muito para responder")
        return False
        
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"[test_conexao_forescout] Erro: {str(e)}")
        return False


def testar_autenticacao_token(
    url_base: str,
    usuario: str,
    senha: str,
    endpoint_teste: str
) -> bool:
    """
    Tenta autenticação via token (método alternativo).
    
    Algumas APIs do Forescout podem usar autenticação via token em vez de Basic Auth.
    """
    try:
        # Endpoint comum para obter token
        token_endpoint = f"{url_base}/api/login"
        
        print(f"   Tentando obter token em: {token_endpoint}")
        
        # Tenta fazer login para obter token
        payload = {
            "username": usuario,
            "password": senha
        }
        
        resposta_token = requests.post(
            token_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
            verify=True
        )
        
        if resposta_token.status_code == 200:
            dados_token = resposta_token.json()
            token = dados_token.get("token") or dados_token.get("access_token") or dados_token.get("accessToken")
            
            if token:
                print(f"   [OK] Token obtido com sucesso")
                
                # Usa token para fazer requisição ao endpoint de teste
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                resposta = requests.get(
                    f"{url_base}{endpoint_teste}",
                    headers=headers,
                    timeout=30,
                    verify=True
                )
                
                if resposta.status_code == 200:
                    print("[OK] Conexão bem-sucedida usando token!")
                    print("\n" + "=" * 80)
                    print("[OK] Teste de conexão concluído com sucesso!")
                    print("=" * 80 + "\n")
                    return True
                else:
                    print(f"[ERRO] Falha ao acessar endpoint com token: {resposta.status_code}")
                    return False
            else:
                print("[ERRO] Token não encontrado na resposta")
                return False
        else:
            print(f"[ERRO] Falha ao obter token: {resposta_token.status_code}")
            print(f"Resposta: {resposta_token.text[:500]}")
            return False
            
    except Exception as e:
        print(f"[AVISO] Método de autenticação via token falhou: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Testa conexão com a API do Forescout usando FORESCOUT_HOST/URL, FORESCOUT_USER e FORESCOUT_PASS"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL base da API do Forescout (se não fornecido, será construída a partir de FORESCOUT_HOST)"
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Host do servidor Forescout (se não fornecido, usa FORESCOUT_HOST do .env)"
    )
    parser.add_argument(
        "--usuario",
        type=str,
        help="Usuário para autenticação (se não fornecido, usa FORESCOUT_USER do .env)"
    )
    parser.add_argument(
        "--senha",
        type=str,
        help="Senha para autenticação (se não fornecido, usa FORESCOUT_PASS do .env)"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="/api/hosts",
        help="Endpoint para testar a conexão (padrão: /api/hosts)"
    )
    
    args = parser.parse_args()
    
    print("\nIniciando teste de conexão com API do Forescout...\n")
    
    sucesso = test_conexao_forescout(
        url=args.url,
        host=args.host,
        usuario=args.usuario,
        senha=args.senha,
        endpoint_teste=args.endpoint
    )
    
    if sucesso:
        print("\n[OK] Teste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\n[ERRO] Teste falhou! Verifique os logs acima.\n")
        sys.exit(1)
