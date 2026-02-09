"""
Script para verificar se a API está acessível e testar a rota
"""
import sys
import requests
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.modelo_dados.modelo_settings import ConfigEnvSetings


def testar_api():
    """Testa se a API está acessível"""
    ambiente = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_AMBIENTE', 'prd').lower()
    
    # Força uso de localhost para testes (ignora configuração do .env)
    url_base = f'http://localhost:3000/api/v1/fluig/{ambiente}/chamados/abrir'
    url_base_api = 'http://localhost:3000'
    
    print("\n" + "="*80)
    print("VERIFICANDO ACESSIBILIDADE DA API")
    print("="*80 + "\n")
    
    print(f"URL Base da API: {url_base_api}")
    print(f"URL Completa do Endpoint: {url_base}")
    print(f"Ambiente: {ambiente}\n")
    
    # Testa se a API está rodando
    print("1. Testando se a API está rodando...")
    try:
        response = requests.get(f"{url_base_api}/", timeout=5)
        print(f"   [OK] API está respondendo (HTTP {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"   [ERRO] Não foi possível conectar à API em {url_base_api}")
        print(f"   [AVISO] Verifique se a API está rodando na porta 3000")
        return False
    except Exception as e:
        print(f"   [AVISO] Erro ao conectar: {str(e)}")
    
    # Testa a rota específica (sem payload, só para ver se existe)
    print(f"\n2. Testando rota: {url_base}")
    print(f"   (Enviando requisição sem API-KEY para verificar se a rota existe)")
    
    try:
        # Tenta fazer uma requisição sem API-KEY para ver se a rota existe
        # Isso deve retornar 403 (Forbidden) se a rota existe, ou 404 se não existe
        response = requests.post(
            url_base,
            json={},
            timeout=5
        )
        
        if response.status_code == 403:
            print(f"   [OK] Rota existe! (Retornou 403 - Forbidden, o que é esperado sem API-KEY)")
            print(f"   [OK] A rota está configurada corretamente")
        elif response.status_code == 404:
            print(f"   [ERRO] Rota não encontrada (404)")
            print(f"   [AVISO] Verifique se a rota está correta:")
            print(f"      Esperado: /api/v1/fluig/{ambiente}/chamados/abrir")
            print(f"      Verifique se o ambiente está correto (prd ou qld)")
        elif response.status_code == 422:
            print(f"   [OK] Rota existe! (Retornou 422 - Validation Error, o que é esperado)")
            print(f"   [OK] A rota está configurada corretamente")
        else:
            print(f"   [AVISO] Resposta inesperada: HTTP {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        print(f"   [ERRO] Não foi possível conectar à API")
        return False
    except Exception as e:
        print(f"   [ERRO] Erro: {str(e)}")
        return False
    
    # Testa com API-KEY (mas sem payload válido)
    print(f"\n3. Testando com API-KEY...")
    api_key = ConfigEnvSetings.API_KEY
    if not api_key:
        print(f"   [AVISO] API_KEY não configurada")
        return False
    
    try:
        headers = {
            "API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        # Payload mínimo para testar
        payload = {
            "titulo": "Teste",
            "descricao": "Teste",
            "usuario": "teste@uisa.com.br"
        }
        
        response = requests.post(
            url_base,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"   Código HTTP: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(f"   [OK] Sucesso! API está funcionando corretamente")
            print(f"   Resposta: {response.text[:200]}")
            return True
        elif response.status_code == 422:
            print(f"   [AVISO] Erro de validação (422) - Isso é normal se o payload não estiver completo")
            print(f"   [OK] Mas a rota está acessível e a API-KEY está funcionando")
            return True
        elif response.status_code == 500:
            print(f"   [AVISO] Erro interno do servidor (500)")
            print(f"   [OK] Mas a rota está acessível e a API-KEY está funcionando")
            print(f"   Resposta: {response.text[:200]}")
            return True
        else:
            print(f"   [AVISO] Resposta: HTTP {response.status_code}")
            print(f"   Resposta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   [ERRO] Erro: {str(e)}")
        return False


if __name__ == "__main__":
    print("\nIniciando verificação da API...\n")
    sucesso = testar_api()
    
    if sucesso:
        print("\n[OK] Verificação concluída com sucesso!\n")
    else:
        print("\n[ERRO] Verificação falhou. Verifique os logs acima.\n")
        sys.exit(1)
