"""
Script para buscar todos os dispositivos (hosts) associados a uma regra/política específica do Forescout
"""
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import ssl
import urllib.request
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


def obter_configuracao():
    """Obtém configuração do Forescout das variáveis de ambiente"""
    host = getattr(ConfigEnvSetings, 'FORESCOUT_HOST', '')
    usuario = getattr(ConfigEnvSetings, 'FORESCOUT_USER', '')
    senha = getattr(ConfigEnvSetings, 'FORESCOUT_PASS', '')
    
    if not host:
        raise ValueError("FORESCOUT_HOST deve ser configurado")
    
    # Remove protocolo se estiver presente no host
    host_limpo = host.replace('https://', '').replace('http://', '').strip('/')
    # Constrói URL usando HTTPS por padrão
    url_base = f"https://{host_limpo}"
    
    # Remove /api se já estiver presente
    if url_base.endswith('/api'):
        url_base = url_base[:-4]
    
    base_url = url_base + "/api"
    
    if not usuario or not senha:
        raise ValueError("FORESCOUT_USER e FORESCOUT_PASS devem ser configurados")
    
    return base_url, usuario, senha, url_base


# Headers globais (mesma estrutura do test_forescout_counteract.py)
headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'charset': 'utf-8',
    'User-Agent': "FSCT/7.20.2020",
}

# Create ssl context (mesma estrutura do test_forescout_counteract.py)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def obter_token(base_url: str, usuario: str, senha: str) -> Optional[str]:
    """Obtém token JWT da API do Forescout (mesma autenticação do test_forescout_counteract.py)"""
    launch_url = base_url + "/login"
    # Usa o mesmo formato do test_forescout_counteract.py
    payload = f"username={usuario}&password={senha}"
    
    try:
        request = urllib.request.Request(launch_url, headers=headers, data=bytes(payload, 'utf-8'))
        resp = urllib.request.urlopen(request, context=ctx)
        token = resp.read().decode("utf-8")
        return token
    except Exception as err:
        print(f"getToken() ERROR: {str(err)}")
        logger.error(f"[test_hosts_by_rule] Erro ao obter token: {str(err)}")
        return None


def get_all_hosts(token: str, base_url: str) -> Optional[Dict]:
    """Busca todos os hosts da API (mesma autenticação do test_forescout_counteract.py)"""
    launch_url = base_url + "/hosts"
    # Usa headers global e adiciona Authorization (mesma estrutura do test_forescout_counteract.py)
    headers_request = headers.copy()
    headers_request["Authorization"] = token
    
    try:
        request = urllib.request.Request(launch_url, headers=headers_request)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return request_response
    except Exception as err:
        print(f"getHosts() ERROR: {str(err)}")
        logger.error(f"[test_hosts_by_rule] Erro ao obter hosts: {str(err)}")
        return None


def filtrar_hosts_por_regras(hosts_data: Dict, rule_ids: List[int], policy_id: Optional[int] = None) -> List[Dict]:
    """
    Filtra hosts que estão associados a uma ou mais regras específicas.
    
    Args:
        hosts_data: Dados dos hosts retornados pela API
        rule_ids: Lista de IDs de regras para filtrar
        policy_id: ID da política (opcional, para verificação adicional)
    
    A estrutura dos hosts pode variar, então verificamos diferentes campos possíveis:
    - host.rules
    - host.policies
    - host.ruleIds
    - host.policyIds
    - host.activePolicies
    """
    hosts_filtrados = []
    hosts_list = hosts_data.get("hosts", [])
    
    print(f"   Analisando {len(hosts_list)} hosts...")
    print(f"   Procurando por {len(rule_ids)} regras: {rule_ids}")
    if policy_id:
        print(f"   Policy ID: {policy_id}")
    
    for host in hosts_list:
        encontrado = False
        regras_encontradas = []
        
        # Verifica diferentes estruturas possíveis
        # 1. Verifica em rules (array de objetos ou IDs)
        host_rules = host.get("rules", [])
        if host_rules:
            for rule in host_rules:
                rule_id_encontrado = None
                if isinstance(rule, dict):
                    rule_id_encontrado = rule.get("ruleId") or rule.get("id")
                elif isinstance(rule, (int, str)):
                    rule_id_encontrado = int(rule) if isinstance(rule, str) else rule
                
                if rule_id_encontrado and rule_id_encontrado in rule_ids:
                    encontrado = True
                    regras_encontradas.append(rule_id_encontrado)
        
        # 2. Verifica em policies (array de objetos)
        if not encontrado:
            host_policies = host.get("policies", [])
            if host_policies:
                for policy in host_policies:
                    if isinstance(policy, dict):
                        # Verifica se é a política correta
                        if policy_id and policy.get("policyId") == policy_id:
                            encontrado = True
                            break
                        # Verifica ruleId diretamente na policy
                        policy_rule_id = policy.get("ruleId")
                        if policy_rule_id and policy_rule_id in rule_ids:
                            encontrado = True
                            regras_encontradas.append(policy_rule_id)
                            break
                        # Verifica em rules dentro da policy
                        rules_in_policy = policy.get("rules", [])
                        for rule in rules_in_policy:
                            rule_id_encontrado = None
                            if isinstance(rule, dict):
                                rule_id_encontrado = rule.get("ruleId") or rule.get("id")
                            elif isinstance(rule, (int, str)):
                                rule_id_encontrado = int(rule) if isinstance(rule, str) else rule
                            
                            if rule_id_encontrado and rule_id_encontrado in rule_ids:
                                encontrado = True
                                regras_encontradas.append(rule_id_encontrado)
                                break
                        if encontrado:
                            break
        
        # 3. Verifica em ruleIds (array de IDs)
        if not encontrado:
            host_rule_ids = host.get("ruleIds", [])
            if host_rule_ids:
                for host_rule_id in host_rule_ids:
                    if host_rule_id in rule_ids:
                        encontrado = True
                        regras_encontradas.append(host_rule_id)
                        break
        
        # 4. Verifica em policyIds
        if not encontrado and policy_id:
            host_policy_ids = host.get("policyIds", [])
            if host_policy_ids and policy_id in host_policy_ids:
                encontrado = True
        
        # 5. Verifica em activePolicies
        if not encontrado:
            active_policies = host.get("activePolicies", [])
            if active_policies:
                for policy in active_policies:
                    if isinstance(policy, dict):
                        # Verifica policyId
                        if policy_id and policy.get("policyId") == policy_id:
                            encontrado = True
                            break
                        # Verifica ruleId
                        policy_rule_id = policy.get("ruleId")
                        if policy_rule_id and policy_rule_id in rule_ids:
                            encontrado = True
                            regras_encontradas.append(policy_rule_id)
                            break
                        # Verifica em rules
                        rules = policy.get("rules", [])
                        for rule in rules:
                            rule_id_encontrado = None
                            if isinstance(rule, dict):
                                rule_id_encontrado = rule.get("ruleId") or rule.get("id")
                            elif isinstance(rule, (int, str)):
                                rule_id_encontrado = int(rule) if isinstance(rule, str) else rule
                            
                            if rule_id_encontrado and rule_id_encontrado in rule_ids:
                                encontrado = True
                                regras_encontradas.append(rule_id_encontrado)
                                break
                        if encontrado:
                            break
        
        # 6. Verifica campos genéricos que possam conter os ruleIds
        if not encontrado:
            # Procura em todos os campos do host
            for key, value in host.items():
                if key.lower() in ['ruleid', 'rule_id', 'active_rule_id']:
                    if value in rule_ids:
                        encontrado = True
                        regras_encontradas.append(value)
                        break
                elif isinstance(value, list):
                    for item in value:
                        if item in rule_ids:
                            encontrado = True
                            regras_encontradas.append(item)
                            break
                    if encontrado:
                        break
        
        if encontrado:
            # Adiciona informações sobre quais regras foram encontradas
            host_copy = host.copy()
            host_copy["_regras_encontradas"] = list(set(regras_encontradas))
            hosts_filtrados.append(host_copy)
    
    return hosts_filtrados


# Política específica para buscar dispositivos
POLICY_CONFIG = {
    "policyId": -1130357740697360362,
    "name": "2.0.1 Quarentena Dispositivos Não Corporativos ( VLAN - 72 )",
    "description": "Politica de quarentena para maquinas não corporativas",
    "rules": [
        {
            "ruleId": -8326517543176762089,
            "name": "Windows cabeado não autorizado- VLAN <edit VLAN>",
            "description": ""
        },
        {
            "ruleId": 6042875332702618231,
            "name": "Outros dispostivos cabeado não autorizado - VLAN <edit VLAN>",
            "description": ""
        },
        {
            "ruleId": -2968208790240287639,
            "name": "Unathorized Wireless \"MOBILE DIVERSOS\",\"ARMAZEM\"",
            "description": ""
        },
        {
            "ruleId": -295320114661600483,
            "name": "Unathorized Wirelles   Windows",
            "description": "\t\t"
        },
        {
            "ruleId": -3484513709115142445,
            "name": "Unathorized Wireless Others",
            "description": ""
        },
        {
            "ruleId": 7552470889114441172,
            "name": "Unknown Device Location",
            "description": ""
        }
    ]
}


def buscar_dispositivos_por_policy(
    policy_id: Optional[int] = None,
    policy_name: Optional[str] = None,
    rule_ids: Optional[List[int]] = None,
    output_file: Optional[str] = None
) -> bool:
    """
    Busca todos os dispositivos associados a uma política específica e suas regras.
    
    Args:
        policy_id: ID da política (policyId)
        policy_name: Nome da política (opcional, apenas para exibição)
        rule_ids: Lista de IDs de regras para filtrar (se None, busca todas as regras da política)
        output_file: Caminho do arquivo JSON de saída
    """
    print("\n" + "=" * 80)
    print("BUSCAR DISPOSITIVOS POR POLÍTICA/REGRAS")
    print("=" * 80 + "\n")
    
    # Usa a política configurada se não fornecida
    if not policy_id:
        policy_id = POLICY_CONFIG["policyId"]
        policy_name = POLICY_CONFIG["name"]
        rule_ids = [rule["ruleId"] for rule in POLICY_CONFIG["rules"]]
        print("[INFO] Usando política configurada no código:")
        print(f"       Policy ID: {policy_id}")
        print(f"       Policy Name: {policy_name}")
        print(f"       Total de regras: {len(rule_ids)}")
    elif not rule_ids:
        # Se policy_id foi fornecido mas não rule_ids, busca as regras
        print("1. Buscando regras da política...")
        try:
            base_url_temp, usuario_temp, senha_temp, _ = obter_configuracao()
            policies_data = get_policies(base_url_temp, usuario_temp, senha_temp)
            if policies_data:
                for policy in policies_data.get("policies", []):
                    if policy.get("policyId") == policy_id:
                        rule_ids = [rule.get("ruleId") for rule in policy.get("rules", [])]
                        print(f"[OK] Encontradas {len(rule_ids)} regras na política:")
                        for rule in policy.get("rules", []):
                            print(f"   - {rule.get('name')} (ID: {rule.get('ruleId')})")
                        break
        except:
            pass
    
    # Se ainda não tem rule_ids, usa da configuração
    if not rule_ids:
        rule_ids = [rule["ruleId"] for rule in POLICY_CONFIG["rules"]]
        print("[INFO] Usando regras da política configurada:")
        for rule in POLICY_CONFIG["rules"]:
            print(f"   - {rule['name']} (ID: {rule['ruleId']})")
    
    try:
        base_url, usuario, senha, url_base = obter_configuracao()
    except Exception as e:
        print(f"[ERRO] Erro ao obter configuração: {str(e)}")
        print("[INFO] Configure FORESCOUT_HOST/URL, FORESCOUT_USER e FORESCOUT_PASS no arquivo .env")
        return False
    
    print(f"\nPolicy ID: {policy_id}")
    if policy_name:
        print(f"Policy Name: {policy_name}")
    print(f"Rule IDs: {rule_ids}")
    print(f"URL Base: {url_base}")
    print(f"Base URL API: {base_url}")
    print()
    
    # Obtém token
    print(f"\n2. Obtendo token JWT...")
    logger.info(f"[test_hosts_by_rule] Obtendo token de autenticação")
    token = obter_token(base_url, usuario, senha)
    
    if not token:
        print("[ERRO] Falha ao obter token")
        return False
    
    print(f"[OK] Token obtido: {token[:50]}...")
    
    # Busca todos os hosts
    print("\n3. Buscando todos os hosts...")
    logger.info(f"[test_hosts_by_rule] Buscando todos os hosts")
    hosts_data = get_all_hosts(token, base_url)
    
    if not hosts_data:
        print("[ERRO] Falha ao obter hosts")
        return False
    
    hosts_list = hosts_data.get("hosts", [])
    total_hosts = len(hosts_list)
    print(f"[OK] {total_hosts} hosts encontrados no total")
    
    # Filtra hosts pelas regras
    print(f"\n4. Filtrando hosts pelas regras da política...")
    logger.info(f"[test_hosts_by_rule] Filtrando hosts pela política {policy_id} e regras {rule_ids}")
    hosts_filtrados = filtrar_hosts_por_regras(hosts_data, rule_ids, policy_id)
    total_filtrados = len(hosts_filtrados)
    
    print(f"[OK] {total_filtrados} dispositivos encontrados associados à política/regras")
    
    if total_filtrados > 0:
        print("\n" + "=" * 80)
        print("DISPOSITIVOS ENCONTRADOS:")
        print("=" * 80 + "\n")
        
        # Agrupa por regra encontrada
        hosts_por_regra = {}
        for host in hosts_filtrados:
            regras = host.get("_regras_encontradas", [])
            for regra_id in regras:
                if regra_id not in hosts_por_regra:
                    hosts_por_regra[regra_id] = []
                hosts_por_regra[regra_id].append(host)
        
        for i, host in enumerate(hosts_filtrados, 1):
            ip = host.get("ip", "N/A")
            mac = host.get("mac", "N/A")
            hostname = host.get("hostname", host.get("name", "N/A"))
            os = host.get("os", host.get("operatingSystem", "N/A"))
            vendor = host.get("vendor", "N/A")
            regras_encontradas = host.get("_regras_encontradas", [])
            
            print(f"{i:4d}. IP: {ip}")
            print(f"      MAC: {mac}")
            print(f"      Hostname: {hostname}")
            print(f"      OS: {os}")
            print(f"      Vendor: {vendor}")
            print(f"      Regras encontradas: {regras_encontradas}")
            print()
        
        # Mostra resumo por regra
        print("\n" + "-" * 80)
        print("RESUMO POR REGRA:")
        print("-" * 80)
        for regra_id, hosts_regra in hosts_por_regra.items():
            print(f"  Regra ID {regra_id}: {len(hosts_regra)} dispositivos")
    else:
        print("\n[AVISO] Nenhum dispositivo encontrado associado a esta política/regras")
        print("[INFO] Isso pode significar que:")
        print("       - Nenhum dispositivo está atualmente associado a estas regras")
        print("       - A estrutura dos hosts pode ser diferente do esperado")
        print("       - Verifique a estrutura real dos hosts executando: python tests/forescout/test_forescout_counteract.py --funcao hosts")
    
    # Salva resultado em JSON
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"hosts_policy_{policy_id}_{timestamp}.json"
    
    resultado_json = {
        "timestamp": datetime.now().isoformat(),
        "policy_id": policy_id,
        "policy_name": policy_name,
        "rule_ids": rule_ids,
        "total_hosts_found": total_filtrados,
        "total_hosts_total": total_hosts,
        "hosts": hosts_filtrados,
        "metadata": {
            "url": base_url + "/hosts",
            "usuario": usuario,
            "host": url_base
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f"ARQUIVO JSON SALVO: {output_path.absolute()}")
    print(f"{'='*80}\n")
    
    logger.info(f"[test_hosts_by_rule] Busca concluída: {total_filtrados} hosts encontrados para política {policy_id}")
    return True


def get_policies(base_url: str, usuario: str, senha: str) -> Optional[Dict]:
    """Busca todas as policies da API (mesma autenticação do test_forescout_counteract.py)"""
    token = obter_token(base_url, usuario, senha)
    if not token:
        return None
    
    launch_url = base_url + "/policies"
    # Usa headers global e adiciona Authorization
    headers_request = headers.copy()
    headers_request["Authorization"] = token
    
    try:
        request = urllib.request.Request(launch_url, headers=headers_request)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return request_response
    except Exception as err:
        print(f"getPolicies() ERROR: {str(err)}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Busca dispositivos associados à política de quarentena configurada no código"
    )
    parser.add_argument(
        "--policy-id",
        type=int,
        help="ID da política (policyId) - se não fornecido, usa a política configurada no código"
    )
    parser.add_argument(
        "--policy-name",
        type=str,
        help="Nome da política (opcional, apenas para exibição)"
    )
    parser.add_argument(
        "--rule-ids",
        type=str,
        help="IDs das regras separados por vírgula (opcional, se não fornecido usa as regras da política configurada) - ex: -8326517543176762089,6042875332702618231"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Caminho do arquivo JSON de saída (se não fornecido, salva em tests/forescout/output/hosts_policy_POLICYID_TIMESTAMP.json)"
    )
    
    args = parser.parse_args()
    
    # Processa rule_ids se fornecido
    rule_ids = None
    if args.rule_ids:
        try:
            rule_ids = [int(rid.strip()) for rid in args.rule_ids.split(',')]
        except ValueError:
            print("[ERRO] --rule-ids deve conter números separados por vírgula")
            sys.exit(1)
    
    print("\nIniciando busca de dispositivos por política...\n")
    print("[INFO] Política configurada:")
    print(f"       Policy ID: {POLICY_CONFIG['policyId']}")
    print(f"       Policy Name: {POLICY_CONFIG['name']}")
    print(f"       Regras: {len(POLICY_CONFIG['rules'])} regras configuradas\n")
    
    sucesso = buscar_dispositivos_por_policy(
        policy_id=args.policy_id,
        policy_name=args.policy_name,
        rule_ids=rule_ids,
        output_file=args.output
    )
    
    if sucesso:
        print("\n[OK] Busca concluída com sucesso!\n")
        sys.exit(0)
    else:
        print("\n[ERRO] Busca falhou!\n")
        sys.exit(1)
