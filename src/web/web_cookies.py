"""Módulo para gerenciar cookies do navegador"""
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from src.utilitarios_centrais.logger import logger


def obter_cookies(driver: WebDriver) -> Optional[List[Dict]]:
    """
    Obtém todos os cookies do navegador
    
    Args:
        driver: Instância do WebDriver
    
    Returns:
        Lista de cookies ou None em caso de erro
    """
    try:
        cookies = driver.get_cookies()
        logger.info(f"[obter_cookies] {len(cookies)} cookies obtidos")
        return cookies
    except Exception as e:
        logger.error(f"[obter_cookies] Erro ao obter cookies: {str(e)}")
        return None


def salvar_cookies(cookies: List[Dict], ambiente: str = "PRD", usuario: str = None) -> bool:
    """
    Salva cookies em arquivo JSON na pasta src/json/
    
    Args:
        cookies: Lista de cookies
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário para identificar os cookies
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        # src/web/web_cookies.py -> src/web/ -> src/ -> src/json/
        src_dir = Path(__file__).parent.parent
        json_dir = src_dir / "json"
        json_dir.mkdir(exist_ok=True)
        
        # Inclui usuário no nome do arquivo se fornecido
        if usuario:
            # Remove caracteres especiais do usuário para usar no nome do arquivo
            usuario_safe = usuario.replace('@', '_').replace('.', '_').replace('/', '_')
            arquivo = json_dir / f"cookies_{usuario_safe}_{ambiente.lower()}.json"
        else:
            arquivo = json_dir / f"cookies_{ambiente.lower()}.json"
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[salvar_cookies] Cookies salvos em: {arquivo}")
        return True
    except Exception as e:
        logger.error(f"[salvar_cookies] Erro ao salvar cookies: {str(e)}")
        return False


def carregar_cookies(ambiente: str = "PRD", usuario: str = None) -> Optional[List[Dict]]:
    """
    Carrega cookies de arquivo JSON da pasta src/json/
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário para identificar os cookies
    
    Returns:
        Lista de cookies ou None se não encontrado
    """
    try:
        # src/web/web_cookies.py -> src/web/ -> src/ -> src/json/
        src_dir = Path(__file__).parent.parent
        
        # Inclui usuário no nome do arquivo se fornecido
        if usuario:
            # Remove caracteres especiais do usuário para usar no nome do arquivo
            usuario_safe = usuario.replace('@', '_').replace('.', '_').replace('/', '_')
            arquivo = src_dir / "json" / f"cookies_{usuario_safe}_{ambiente.lower()}.json"
        else:
            arquivo = src_dir / "json" / f"cookies_{ambiente.lower()}.json"
        
        if not arquivo.exists():
            logger.warning(f"[carregar_cookies] Arquivo de cookies não encontrado: {arquivo}")
            return None
        
        with open(arquivo, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        logger.info(f"[carregar_cookies] {len(cookies)} cookies carregados")
        return cookies
    except Exception as e:
        logger.error(f"[carregar_cookies] Erro ao carregar cookies: {str(e)}")
        return None


def cookies_para_requests(cookies: List[Dict]) -> Dict[str, str]:
    """
    Converte cookies do formato Selenium para formato requests
    
    Args:
        cookies: Lista de cookies do Selenium
    
    Returns:
        Dicionário de cookies para requests
    """
    try:
        cookies_dict = {}
        for cookie in cookies:
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies_dict[name] = value
        
        logger.info(f"[cookies_para_requests] {len(cookies_dict)} cookies convertidos")
        return cookies_dict
    except Exception as e:
        logger.error(f"[cookies_para_requests] Erro ao converter cookies: {str(e)}")
        return {}


def verificar_cookies_validos(ambiente: str = "PRD", usuario: str = None) -> bool:
    """
    Verifica se existem cookies salvos na pasta src/json/
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário para identificar os cookies
    
    Returns:
        True se cookies existem, False caso contrário
    """
    try:
        # src/web/web_cookies.py -> src/web/ -> src/ -> src/json/
        src_dir = Path(__file__).parent.parent
        
        # Inclui usuário no nome do arquivo se fornecido
        if usuario:
            # Remove caracteres especiais do usuário para usar no nome do arquivo
            usuario_safe = usuario.replace('@', '_').replace('.', '_').replace('/', '_')
            arquivo = src_dir / "json" / f"cookies_{usuario_safe}_{ambiente.lower()}.json"
        else:
            arquivo = src_dir / "json" / f"cookies_{ambiente.lower()}.json"
        
        return arquivo.exists()
    except Exception:
        return False


def verificar_expiracao_cookie(cookie: Dict) -> bool:
    """
    Verifica se um cookie específico está válido pela data de expiração
    
    Args:
        cookie: Dicionário com dados do cookie
    
    Returns:
        True se cookie está válido, False caso contrário
    """
    try:
        expira = cookie.get('expiry')
        
        # Se não tem expiração, considerar válido (cookie de sessão)
        if not expira:
            return True
        
        # Verifica se expirou
        agora = time.time()
        return expira > agora
    except Exception:
        return False


def limpar_cookies(ambiente: str = "PRD", usuario: str = None) -> bool:
    """
    Remove arquivo de cookies da pasta src/json/
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário para identificar os cookies
    
    Returns:
        True se removeu com sucesso, False caso contrário
    """
    try:
        # src/web/web_cookies.py -> src/web/ -> src/ -> src/json/
        src_dir = Path(__file__).parent.parent
        
        # Inclui usuário no nome do arquivo se fornecido
        if usuario:
            # Remove caracteres especiais do usuário para usar no nome do arquivo
            usuario_safe = usuario.replace('@', '_').replace('.', '_').replace('/', '_')
            arquivo = src_dir / "json" / f"cookies_{usuario_safe}_{ambiente.lower()}.json"
        else:
            arquivo = src_dir / "json" / f"cookies_{ambiente.lower()}.json"
        
        if arquivo.exists():
            arquivo.unlink()
            logger.info(f"[limpar_cookies] Cookies removidos: {arquivo}")
            return True
        else:
            logger.warning(f"[limpar_cookies] Arquivo não encontrado: {arquivo}")
            return False
    except Exception as e:
        logger.error(f"[limpar_cookies] Erro ao limpar cookies: {str(e)}")
        return False

