#!/usr/bin/env python
# Web Services API to eyeSight function library
# author: spollock@forescout.com

# Copyright © 2020 Forescout Technologies, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import json
import ssl
import urllib.request
from pathlib import Path
from typing import Optional

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger

# Obtém configurações das variáveis de ambiente
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
    
    ctpwstring = f"username={usuario}&password={senha}"
    
    return base_url, ctpwstring

# Inicializa configuração
try:
    base_url, CTPWSTRING = obter_configuracao()
except Exception as e:
    print(f"[ERRO] Erro ao obter configuração: {str(e)}")
    print("[INFO] Configure FORESCOUT_HOST/URL, FORESCOUT_USER e FORESCOUT_PASS no arquivo .env")
    base_url = None
    CTPWSTRING = None

headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'charset': 'utf-8',
    'User-Agent': "FSCT/7.20.2020",
    }

# Create ssl context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# --- Functions ---


# Return JWT from Counteract
def getToken():
    launch_url = base_url + "/login"
    payload = CTPWSTRING

    try:
        request = urllib.request.Request(launch_url, headers=headers, data=bytes(payload, 'utf-8'))
        resp = urllib.request.urlopen(request, context=ctx)
        return(resp.read().decode("utf-8"))

    except Exception as err:
        print("getToken() ERROR: " + str(err))


# Pull all hosts from CounterACT
def getHosts(token):
    launch_url = base_url + "/hosts"
    headers["Authorization"] = token

    try:
        request = urllib.request.Request(launch_url, headers=headers)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return(request_response)

    except Exception as err:
        print("getHosts() ERROR:" + str(err))


# Pull all policies from CounterACT
def getPolicies(token):
    launch_url = base_url + "/policies"
    headers["Authorization"] = token

    try:
        request = urllib.request.Request(launch_url, headers=headers)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return(request_response)

    except Exception as err:
        print("getPolicies() ERROR:" + str(err))


# Find policy ID with policy name
def getPoliciesMainID(token, policyname):
    # Pull all policies from CounterACT
    policies = getPolicies(token)

    # Find policy ID of a rule named "HVAC", will return the first if there are multiple
    for rule in policies["policies"]:
        for ruleid in rule["rules"]:
            if policyname in ruleid["name"]:
                return(ruleid["ruleId"])


# Get all Host fields
def getHostFields(token):
    launch_url = base_url + "/hostfields"
    headers["Authorization"] = token

    try:
        request = urllib.request.Request(launch_url, headers=headers)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return(request_response)

    except Exception as err:
        print("getPolicies() ERROR:" + str(err))


# Get all properites for a host
def getHostProps(token, ip):
    launch_url = base_url + "/hosts/ip/" + ip
    headers["Authorization"] = token

    try:
        request = urllib.request.Request(launch_url, headers=headers)
        resp = urllib.request.urlopen(request, context=ctx)
        request_response = json.loads(resp.read())
        return(request_response)

    except Exception as err:
        print("getPolicies() ERROR:" + str(err))

if __name__ == "__main__":
    import argparse
    
    if not base_url or not CTPWSTRING:
        print("[ERRO] Configuração não disponível. Verifique as variáveis de ambiente.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Testa funções da API do Forescout CounterACT"
    )
    parser.add_argument(
        "--funcao",
        type=str,
        choices=["token", "hosts", "policies", "hostfields", "hostprops", "all"],
        default="all",
        help="Função a executar (padrão: all)"
    )
    parser.add_argument(
        "--ip",
        type=str,
        help="IP do host para getHostProps (requerido se --funcao=hostprops)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("TESTE: API FORESCOUT COUNTERACT")
    print("=" * 80 + "\n")
    
    try:
        # Obtém token
        print("1. Obtendo token...")
        token = getToken()
        if not token:
            print("[ERRO] Falha ao obter token")
            sys.exit(1)
        print(f"[OK] Token obtido: {token[:50]}...")
        
        if args.funcao in ["token", "all"]:
            print(f"\nToken completo: {token}")
        
        # Executa funções conforme solicitado
        if args.funcao in ["hosts", "all"]:
            print("\n2. Obtendo hosts...")
            hosts = getHosts(token)
            if hosts:
                print(f"[OK] Hosts obtidos: {len(hosts.get('hosts', []))} hosts encontrados")
                print(json.dumps(hosts, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(hosts, indent=2, ensure_ascii=False)) > 1000:
                    print("... (resposta truncada)")
        
        if args.funcao in ["policies", "all"]:
            print("\n3. Obtendo policies...")
            policies = getPolicies(token)
            if policies:
                print(f"[OK] Policies obtidas")
                print(json.dumps(policies, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(policies, indent=2, ensure_ascii=False)) > 1000:
                    print("... (resposta truncada)")
        
        if args.funcao in ["hostfields", "all"]:
            print("\n4. Obtendo host fields...")
            host_fields = getHostFields(token)
            if host_fields:
                print("[OK] Host fields obtidos")
                print(json.dumps(host_fields, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(host_fields, indent=2, ensure_ascii=False)) > 1000:
                    print("... (resposta truncada)")
        
        if args.funcao in ["hostprops", "all"]:
            ip_teste = args.ip or "172.16.0.115"
            if args.funcao == "hostprops" and not args.ip:
                print("[ERRO] --ip é obrigatório quando --funcao=hostprops")
                sys.exit(1)
            
            print(f"\n5. Obtendo propriedades do host {ip_teste}...")
            host_props = getHostProps(token, ip_teste)
            if host_props:
                print(f"[OK] Propriedades do host {ip_teste} obtidas")
                print(json.dumps(host_props, indent=2, ensure_ascii=False)[:1000])
                if len(json.dumps(host_props, indent=2, ensure_ascii=False)) > 1000:
                    print("... (resposta truncada)")
        
        print("\n" + "=" * 80)
        print("[OK] Teste concluído com sucesso!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)