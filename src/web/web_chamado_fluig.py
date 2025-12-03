"""Módulo para buscar detalhes de chamados do Fluig"""
import json
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
import requests

from src.utilitarios_centrais.logger import logger
from src.web.web_cookies import (
    carregar_cookies,
    cookies_para_requests
)
from src.modelo_dados.modelo_settings import ConfigEnvSetings


def obter_detalhes_chamado(
    process_instance_id: int,
    ambiente: str = "PRD",
    task_user_id: Optional[str] = None,
    cookies_list: Optional[List[Dict]] = None,
    usuario: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Obtém detalhes de um chamado do Fluig
    
    Args:
        process_instance_id: ID da instância do processo
        ambiente: Ambiente ('PRD' ou 'QLD')
        task_user_id: ID do usuário da tarefa (opcional, usa ADMIN_COLLEAGUE_ID se não fornecido)
        cookies_list: Lista de cookies (opcional, carrega do arquivo se não fornecido)
        usuario: Usuário para carregar cookies específicos (opcional)
    
    Returns:
        Dados JSON com detalhes do chamado ou None
    """
    try:

        if cookies_list is None:
            cookies_list = carregar_cookies(ambiente, usuario)
        
        if not cookies_list:
            logger.warning(f"[obter_detalhes_chamado] Nenhum cookie encontrado para {ambiente}")
            return None

        cookies_dict = cookies_para_requests(cookies_list)
        
        if not cookies_dict:
            logger.error("[obter_detalhes_chamado] Nenhum cookie válido")
            return None

        if not task_user_id:
            ambiente_upper = ambiente.upper()
            if ambiente_upper == "QLD":
                task_user_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
                logger.debug(f"[obter_detalhes_chamado] Usando USER_COLLEAGUE_ID_QLD para ambiente QLD")
            else:
                task_user_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
                logger.debug(f"[obter_detalhes_chamado] Usando ADMIN_COLLEAGUE_ID para ambiente PRD")
        
        if not task_user_id:
            logger.error(f"[obter_detalhes_chamado] task_user_id não configurado para ambiente {ambiente}")
            return None
        
        logger.debug(f"[obter_detalhes_chamado] task_user_id configurado: {task_user_id}")

        if ambiente == "PRD":
            base_url = ConfigEnvSetings.URL_FLUIG_PRD
        elif ambiente == "QLD":
            base_url = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            logger.error(f"[obter_detalhes_chamado] Ambiente inválido: {ambiente}")
            return None
        
        parsed_url = urlparse(base_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        url = f"{base_url}/ecm/api/rest/ecm/workflowView/findDetailsMyRequests"

        payload = {
            "processInstanceId": process_instance_id,
            "taskUserId": task_user_id
        }
        

        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'pt-BR,pt;q=0.9',
            'content-type': 'application/json; charset=UTF-8',
            'origin': base_url,
            'referer': f'{base_url}/portal/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        logger.info(f"[obter_detalhes_chamado] Buscando detalhes do chamado {process_instance_id}...")
        logger.debug(f"[obter_detalhes_chamado] URL: {url}")
        logger.debug(f"[obter_detalhes_chamado] Payload: {payload}")
        
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies_dict,
            json=payload,
            timeout=30
        )
        
        logger.info(f"[obter_detalhes_chamado] Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"[obter_detalhes_chamado] Detalhes obtidos com sucesso")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"[obter_detalhes_chamado] Erro ao decodificar JSON: {str(e)}")
                logger.debug(f"[obter_detalhes_chamado] Resposta: {response.text[:500]}")
                return None
        else:
            logger.error(f"[obter_detalhes_chamado] Erro HTTP {response.status_code}")
            logger.error(f"[obter_detalhes_chamado] Resposta do servidor: {response.text[:500]}")
            
            if response.status_code in [401, 403]:
                logger.warning("[obter_detalhes_chamado] Cookies podem ter expirado")
            elif response.status_code == 500:
                logger.warning(f"[obter_detalhes_chamado] Erro interno do servidor. Verifique se o chamado existe e se o taskUserId ({task_user_id}) tem permissão para acessá-lo")
            
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[obter_detalhes_chamado] Erro na requisição: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[obter_detalhes_chamado] Erro inesperado: {str(e)}")
        return None

