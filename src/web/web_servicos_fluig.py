"""Módulo para buscar serviços do Fluig usando OAuth 1.0"""
import json
import time
import urllib.parse
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
import requests

from src.utilitarios_centrais.logger import logger
from src.fluig.fluig_requests import RequestsFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings


def obter_servicos_fluig(
    ambiente: str = "PRD", 
    limit: int = 300, 
    offset: int = 0, 
    orderby: str = 'servico_ASC',
    cookies_list: Optional[List[Dict]] = None
) -> Optional[Dict[str, Any]]:
    """
    Obtém lista de serviços do Fluig usando cookies
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        limit: Limite de resultados
        offset: Offset para paginação
        orderby: Ordenação
        cookies_list: Lista de cookies (opcional, carrega se não fornecido)
    
    Returns:
        Dados JSON com serviços ou None
    """
    try:
        # Carrega cookies se não foram fornecidos
        if cookies_list is None:
            cookies_list = carregar_cookies(ambiente)
            if not cookies_list:
                logger.warning(f"[obter_servicos_fluig] Nenhum cookie encontrado para {ambiente}")
                return None
        
        # Converte cookies para formato requests
        cookies_dict = cookies_para_requests(cookies_list)
        
        if not cookies_dict:
            logger.error("[obter_servicos_fluig] Nenhum cookie válido")
            return None
        
        # Parâmetros do dataset
        dataset_params = {
            "searchField": "servico",
            "filterFields": [],
            "resultFields": ["servico", "documentid"],
            "datasetId": "ITSM_Catalogo_Servico"
        }
        
        # Codifica JSON para URL
        dataset_json = json.dumps(dataset_params)
        dataset_encoded = urllib.parse.quote(dataset_json)
        
        # Determina URL base
        if ambiente == "PRD":
            base_url = ConfigEnvSetings.URL_FLUIG_PRD
        elif ambiente == "QLD":
            base_url = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            logger.error(f"[obter_servicos_fluig] Ambiente inválido: {ambiente}")
            return None
        
        parsed_url = urlparse(base_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        url = f"{base_url}/ecm/api/rest/ecm/dataset/datasetZoom/{dataset_encoded}"
        
        # Parâmetros da query
        timestamp = int(time.time() * 1000)
        params = {
            'limit': limit,
            'offset': offset,
            'orderby': orderby,
            '_': timestamp
        }
        
        # Headers
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': f'{base_url}/webdesk/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        logger.info(f"[obter_servicos_fluig] Fazendo requisição para {ambiente}...")
        
        response = requests.get(url, headers=headers, cookies=cookies_dict, params=params, timeout=30)
        
        logger.info(f"[obter_servicos_fluig] Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                total = len(data.get('content', [])) if isinstance(data, dict) else 0
                logger.info(f"[obter_servicos_fluig] {total} serviços obtidos")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"[obter_servicos_fluig] Erro ao decodificar JSON: {str(e)}")
                return None
        else:
            # Se recebeu 401 ou 403, tenta renovar cookies e fazer nova tentativa
            if response.status_code in [401, 403]:
                logger.warning(f"[obter_servicos_fluig] Erro de autenticação (HTTP {response.status_code})")
                logger.info(f"[obter_servicos_fluig] Tentando renovar autenticação...")
                
                # Força novo login através do gerenciador de autenticação
                sucesso, cookies_list_novos = garantir_autenticacao(ambiente, forcar_login=True)
                if sucesso and cookies_list_novos:
                    logger.info(f"[obter_servicos_fluig] Autenticação renovada, tentando novamente...")
                    cookies_dict = cookies_para_requests(cookies_list_novos)
                    
                    # Segunda tentativa com novos cookies
                    response = requests.get(url, headers=headers, cookies=cookies_dict, params=params, timeout=30)
                    logger.info(f"[obter_servicos_fluig] Status da segunda requisição: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            total = len(data.get('content', [])) if isinstance(data, dict) else 0
                            logger.info(f"[obter_servicos_fluig] {total} serviços obtidos após renovar autenticação")
                            return data
                        except json.JSONDecodeError as e:
                            logger.error(f"[obter_servicos_fluig] Erro ao decodificar JSON na segunda tentativa: {str(e)}")
                            logger.error(f"[obter_servicos_fluig] Resposta: {response.text[:500]}")
                            return None
                else:
                    logger.error(f"[obter_servicos_fluig] Falha ao renovar autenticação para {ambiente}")
                    logger.error(f"[obter_servicos_fluig] Resposta do servidor: {response.text[:500]}")
                    return None
            
            # Outros erros HTTP
            logger.error(f"[obter_servicos_fluig] Erro HTTP {response.status_code}")
            logger.error(f"[obter_servicos_fluig] Resposta do servidor: {response.text[:500]}")
            
            if response.status_code == 404:
                logger.warning(f"[obter_servicos_fluig] Recurso não encontrado")
            elif response.status_code == 500:
                logger.error(f"[obter_servicos_fluig] Erro interno do servidor Fluig")
            elif response.status_code >= 400:
                logger.error(f"[obter_servicos_fluig] Erro do cliente (4xx) ou servidor (5xx)")
            
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[obter_servicos_fluig] Erro na requisição: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[obter_servicos_fluig] Erro inesperado: {str(e)}")
        return None


def _fazer_requisicao_detalhes_servico(
    document_id_int: int,
    base_url: str,
    requests_fluig: RequestsFluig,
    ambiente: str
) -> Optional[requests.Response]:
    """
    Faz a requisição para obter detalhes do serviço usando OAuth 1.0
    
    Args:
        document_id_int: ID do documento como inteiro
        base_url: URL base do Fluig
        requests_fluig: Instância de RequestsFluig com OAuth 1.0 configurado
        ambiente: Ambiente ('PRD' ou 'QLD')
    
    Returns:
        Response da requisição ou None em caso de erro
    """
    try:
        url = f"{base_url}/api/public/ecm/dataset/datasets/"
        
        # Payload da requisição
        payload = {
            "name": "ITSM_Catalogo_Servico",
            "fields": None,
            "constraints": [
                {
                    "_field": "documentid",
                    "_initialValue": document_id_int,
                    "_finalValue": document_id_int,
                    "_type": 1
                }
            ],
            "order": None
        }
        
        logger.debug(f"[_fazer_requisicao_detalhes_servico] URL: {url}")
        logger.debug(f"[_fazer_requisicao_detalhes_servico] Payload: {payload}")
        
        # Usa RequestTipoPOST que utiliza OAuth 1.0
        response = requests_fluig.RequestTipoPOST(url, payload)
        
        return response
        
    except requests.exceptions.Timeout:
        logger.error(f"[_fazer_requisicao_detalhes_servico] Timeout na requisição após 30 segundos")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[_fazer_requisicao_detalhes_servico] Erro de conexão: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[_fazer_requisicao_detalhes_servico] Erro na requisição: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[_fazer_requisicao_detalhes_servico] Erro inesperado: {str(e)}")
        return None


def obter_detalhes_servico_fluig(
    document_id: str,
    ambiente: str = "PRD",
    cookies_list: Optional[List[Dict]] = None  # Deprecated: mantido para compatibilidade, não é mais usado
) -> Optional[Dict[str, Any]]:
    """
    Obtém detalhes de um serviço específico do Fluig usando OAuth 1.0
    
    IMPORTANTE: Esta função agora usa exclusivamente OAuth 1.0 (CK, CS, TK, TS)
    e não depende mais de cookies ou login via browser.
    
    Args:
        document_id: ID do documento do serviço (documentid)
        ambiente: Ambiente ('PRD' ou 'QLD')
        cookies_list: DEPRECATED - não é mais usado, mantido apenas para compatibilidade
    
    Returns:
        Dados JSON com detalhes do serviço ou None
    """
    try:
        logger.info(f"[obter_detalhes_servico_fluig] Usando autenticação OAuth 1.0")
        
        # Converte document_id para int
        try:
            document_id_int = int(document_id)
        except ValueError:
            logger.error(f"[obter_detalhes_servico_fluig] ID do serviço inválido: '{document_id}' (deve ser numérico)")
            return None
        
        # Determina URL base
        if ambiente == "PRD":
            base_url = ConfigEnvSetings.URL_FLUIG_PRD
        elif ambiente == "QLD":
            base_url = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            logger.error(f"[obter_detalhes_servico_fluig] Ambiente inválido: '{ambiente}' (deve ser 'PRD' ou 'QLD')")
            return None
        
        parsed_url = urlparse(base_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        logger.info(f"[obter_detalhes_servico_fluig] Buscando detalhes do serviço {document_id} no ambiente {ambiente}...")
        
        # Inicializa RequestsFluig com OAuth 1.0
        requests_fluig = RequestsFluig(ambiente=ambiente)
        
        # Faz requisição usando OAuth 1.0
        response = _fazer_requisicao_detalhes_servico(document_id_int, base_url, requests_fluig, ambiente)
        
        if not response:
            logger.error(f"[obter_detalhes_servico_fluig] Falha ao fazer requisição")
            return None
        
        logger.info(f"[obter_detalhes_servico_fluig] Status da requisição: {response.status_code}")
        
        # Processa resposta
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Verifica se há conteúdo válido
                if not data or 'content' not in data:
                    logger.warning(f"[obter_detalhes_servico_fluig] Resposta sem conteúdo válido")
                    logger.debug(f"[obter_detalhes_servico_fluig] Resposta completa: {json.dumps(data, indent=2)[:500]}")
                    return None
                
                logger.info(f"[obter_detalhes_servico_fluig] Detalhes do serviço {document_id} obtidos com sucesso")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"[obter_detalhes_servico_fluig] Erro ao decodificar JSON da resposta: {str(e)}")
                logger.error(f"[obter_detalhes_servico_fluig] Resposta recebida (primeiros 500 chars): {response.text[:500]}")
                return None
        else:
            # Outros erros HTTP
            logger.error(f"[obter_detalhes_servico_fluig] Erro HTTP {response.status_code}")
            logger.error(f"[obter_detalhes_servico_fluig] Resposta do servidor: {response.text[:500]}")
            
            if response.status_code == 404:
                logger.warning(f"[obter_detalhes_servico_fluig] Serviço com ID {document_id} não encontrado")
            elif response.status_code == 500:
                logger.error(f"[obter_detalhes_servico_fluig] Erro interno do servidor Fluig")
            elif response.status_code >= 400:
                logger.error(f"[obter_detalhes_servico_fluig] Erro do cliente (4xx) ou servidor (5xx)")
            
            return None
            
    except Exception as e:
        logger.error(f"[obter_detalhes_servico_fluig] Erro inesperado ao obter detalhes do serviço {document_id}: {str(e)}", exc_info=True)
        return None

