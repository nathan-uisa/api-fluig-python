"""
Script de teste para obter policies da API do Forescout

Este teste realiza uma requisição GET para /api/policies utilizando
as credenciais configuradas nas variáveis de ambiente:
- FORESCOUT_HOST: Host do servidor Forescout
- FORESCOUT_USER: Usuário para autenticação
- FORESCOUT_PASS: Senha para autenticação

Documentação: https://docs.forescout.com/
"""
import sys
from pathlib import Path
from typing import Optional
import json
import ssl
import urllib.request
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def obter_token(base_url: str, usuario: str, senha: str) -> Optional[str]:
    """
    Obtém token JWT da API do Forescout através de /api/login.
    
    Args:
        base_url: URL base da API (ex: https://forescout.example.com/api)
        usuario: Usuário para autenticação
        senha: Senha para autenticação
    
    Returns:
        Token JWT se bem-sucedido, None caso contrário
    """
    launch_url = base_url + "/login"
    payload = f"username={usuario}&password={senha}"
    
    headers_login = {
        'Content-Type': "application/x-www-form-urlencoded",
        'charset': 'utf-8',
        'User-Agent': "FSCT/7.20.2020",
    }
    
    # Create ssl context
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        request = urllib.request.Request(launch_url, headers=headers_login, data=bytes(payload, 'utf-8'))
        resp = urllib.request.urlopen(request, context=ctx)
        token = resp.read().decode("utf-8")
        return token
    except Exception as err:
        print(f"getToken() ERROR: {str(err)}")
        logger.error(f"[test_get_policies] Erro ao obter token: {str(err)}")
        return None


def test_get_policies(
    url: Optional[str] = None,
    host: Optional[str] = None,
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
    output_file: Optional[str] = None
) -> bool:
    """
    Testa a obtenção de policies da API do Forescout usando autenticação via token JWT.
    
    Args:
        url: URL base da API do Forescout (se None, será construída a partir de FORESCOUT_HOST)
        host: Host do servidor Forescout (se None, usa FORESCOUT_HOST do .env)
             Se URL não for fornecida, será construída a partir do host usando HTTPS
        usuario: Usuário para autenticação (se None, usa FORESCOUT_USER do .env)
        senha: Senha para autenticação (se None, usa FORESCOUT_PASS do .env)
        output_file: Caminho do arquivo JSON de saída (se None, salva em tests/forescout/output/policies_TIMESTAMP.json)
    
    Returns:
        True se a requisição foi bem-sucedida, False caso contrário
    """
    print("\n" + "=" * 80)
    print("TESTE: GET /api/policies - FORESCOUT")
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
    
    # Remove barra final da URL se existir e remove /api se presente
    url_base = url_base.rstrip('/')
    if url_base.endswith('/api'):
        url_base = url_base[:-4]
    
    # Monta URL base da API
    base_url = url_base + "/api"
    
    print(f"Host: {host_forescout or 'N/A'}")
    print(f"URL Base: {url_base}")
    print(f"Base URL API: {base_url}")
    print(f"Usuário: {usuario_teste}")
    print(f"Senha: {'*' * len(senha_teste)}")
    print()
    
    try:
        # Obtém token JWT
        print("1. Obtendo token JWT...")
        logger.info(f"[test_get_policies] Obtendo token de autenticação")
        token = obter_token(base_url, usuario_teste, senha_teste)
        
        if not token:
            print("[ERRO] Falha ao obter token de autenticação")
            return False
        
        print(f"[OK] Token obtido: {token[:50]}...")
        
        # Configura headers para requisição de policies
        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'charset': 'utf-8',
            'User-Agent': "FSCT/7.20.2020",
            'Authorization': token
        }
        
        # Monta URL completa do endpoint
        endpoint = "/policies"
        launch_url = base_url + endpoint
        
        print(f"\n2. Enviando requisição GET para {endpoint}...")
        logger.info(f"[test_get_policies] Tentando obter policies: {launch_url}")
        
        # Create ssl context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Faz requisição GET
        request = urllib.request.Request(launch_url, headers=headers)
        resp = urllib.request.urlopen(request, context=ctx)
        
        status_code = resp.getcode()
        print(f"Status Code: {status_code}")
        print(f"Headers de Resposta: {dict(resp.headers)}\n")
        
        # Processa resposta
        if status_code == 200:
            print("[OK] Requisição bem-sucedida!")
            try:
                response_data = resp.read()
                dados = json.loads(response_data)
                
                # Extrai informações úteis
                policies = dados.get("policies", [])
                total_policies = len(policies)
                
                print(f"\n{'='*80}")
                print(f"TOTAL DE POLICIES ENCONTRADAS: {total_policies}")
                print(f"{'='*80}\n")
                
                if total_policies > 0:
                    print("LISTA DE TODAS AS POLICIES:")
                    print("-" * 80)
                    
                    # Lista todas as policies com seus nomes e IDs
                    for i, policy in enumerate(policies, 1):
                        policy_name = policy.get("name", "N/A")
                        policy_id = policy.get("id", "N/A")
                        policy_type = policy.get("type", "N/A")
                        
                        # Tenta obter informações adicionais se disponíveis
                        policy_desc = policy.get("description", "")
                        if policy_desc:
                            policy_desc = f" - {policy_desc[:50]}"
                        
                        print(f"{i:4d}. {policy_name}")
                        print(f"      ID: {policy_id} | Tipo: {policy_type}{policy_desc}")
                        print()
                    
                    print("-" * 80)
                    print(f"\nResumo: {total_policies} policies listadas acima")
                
                # Salva resultado em arquivo JSON
                if output_file:
                    output_path = Path(output_file)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_dir = Path(__file__).parent / "output"
                    output_dir.mkdir(exist_ok=True)
                    output_path = output_dir / f"policies_{timestamp}.json"
                
                # Prepara dados para salvar
                resultado_json = {
                    "timestamp": datetime.now().isoformat(),
                    "total_policies": total_policies,
                    "policies": policies,
                    "metadata": {
                        "url": launch_url,
                        "usuario": usuario_teste,
                        "host": host_forescout or url_base
                    }
                }
                
                # Salva arquivo JSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(resultado_json, f, indent=2, ensure_ascii=False)
                
                print(f"\n{'='*80}")
                print(f"ARQUIVO JSON SALVO: {output_path.absolute()}")
                print(f"{'='*80}\n")
                
                # Mostra estrutura completa se solicitado ou se houver poucas policies
                print(f"\n{'='*80}")
                print("ESTRUTURA JSON COMPLETA:")
                print(f"{'='*80}")
                print(json.dumps(dados, indent=2, ensure_ascii=False))
                
            except json.JSONDecodeError:
                print(f"\n[AVISO] Resposta não é JSON válido")
                response_data = resp.read()
                print(f"Resposta (texto): {response_data.decode('utf-8')[:1000]}")
            
            print("\n" + "=" * 80)
            print("[OK] Teste concluído com sucesso!")
            print("=" * 80 + "\n")
            logger.info("[test_get_policies] Policies obtidas com sucesso")
            return True
            
        elif status_code == 401:
            print("[ERRO] Falha na autenticação (401 Unauthorized)")
            print("[INFO] Verifique se as credenciais FORESCOUT_USER e FORESCOUT_PASS estão corretas")
            response_data = resp.read()
            print(f"Resposta: {response_data.decode('utf-8')[:500]}")
            return False
            
        elif status_code == 403:
            print("[ERRO] Acesso negado (403 Forbidden)")
            print("[INFO] O usuário pode não ter permissões suficientes para acessar policies")
            response_data = resp.read()
            print(f"Resposta: {response_data.decode('utf-8')[:500]}")
            return False
            
        elif status_code == 404:
            print("[ERRO] Endpoint não encontrado (404)")
            print(f"[INFO] O endpoint '{endpoint}' pode não existir nesta versão da API")
            response_data = resp.read()
            print(f"Resposta: {response_data.decode('utf-8')[:500]}")
            return False
            
        else:
            print(f"[ERRO] Requisição falhou com status {status_code}")
            response_data = resp.read()
            print(f"Resposta: {response_data.decode('utf-8')[:1000]}")
            return False
            
    except urllib.error.HTTPError as e:
        print(f"[ERRO] Erro HTTP: {str(e)}")
        print(f"Status Code: {e.code}")
        try:
            error_response = e.read().decode('utf-8')
            print(f"Resposta: {error_response[:500]}")
        except:
            pass
        logger.error(f"[test_get_policies] Erro HTTP: {str(e)}")
        return False
        
    except urllib.error.URLError as e:
        print(f"[ERRO] Erro de conexão: {str(e)}")
        print("[INFO] Verifique se a URL está correta e se o servidor está acessível")
        logger.error(f"[test_get_policies] Erro de conexão: {str(e)}")
        return False
        
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"[test_get_policies] Erro: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Testa GET /api/policies da API do Forescout"
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
        "--output",
        type=str,
        help="Caminho do arquivo JSON de saída (se não fornecido, salva em tests/forescout/output/policies_TIMESTAMP.json)"
    )
    
    args = parser.parse_args()
    
    print("\nIniciando teste de GET /api/policies...\n")
    
    sucesso = test_get_policies(
        url=args.url,
        host=args.host,
        usuario=args.usuario,
        senha=args.senha,
        output_file=args.output
    )
    
    if sucesso:
        print("\n[OK] Teste finalizado com sucesso!\n")
        sys.exit(0)
    else:
        print("\n[ERRO] Teste falhou! Verifique os logs acima.\n")
        sys.exit(1)
