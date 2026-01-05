"""Gerenciador de drivers que mantém navegadores abertos para renovação de cookies"""
import threading
from typing import Optional, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from src.utilitarios_centrais.logger import logger
from src.web.web_cookies import obter_cookies, salvar_cookies

# Dicionário global para armazenar drivers ativos por ambiente e usuário
_drivers_ativos: Dict[str, WebDriver] = {}
_lock_drivers = threading.Lock()


def _gerar_chave_driver(ambiente: str, usuario: Optional[str]) -> str:
    """Gera uma chave única para identificar o driver"""
    usuario_safe = usuario or "default"
    return f"{ambiente.upper()}_{usuario_safe}"


def obter_driver_ativo(ambiente: str = "PRD", usuario: Optional[str] = None) -> Optional[WebDriver]:
    """
    Obtém o driver ativo para o ambiente e usuário especificados
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
    
    Returns:
        WebDriver se existe e está ativo, None caso contrário
    """
    chave = _gerar_chave_driver(ambiente, usuario)
    
    with _lock_drivers:
        driver = _drivers_ativos.get(chave)
        
        if driver:
            # Verifica se o driver ainda está ativo (não foi fechado)
            try:
                # Tenta obter a URL atual para verificar se o driver está funcionando
                driver.current_url
                logger.debug(f"[obter_driver_ativo] Driver ativo encontrado para {chave}")
                return driver
            except Exception as e:
                logger.warning(f"[obter_driver_ativo] Driver encontrado mas inativo para {chave}: {str(e)}")
                # Remove driver inativo
                _drivers_ativos.pop(chave, None)
                return None
        
        return None


def registrar_driver(driver: WebDriver, ambiente: str = "PRD", usuario: Optional[str] = None) -> bool:
    """
    Registra um driver para ser mantido aberto
    
    Args:
        driver: Instância do WebDriver
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
    
    Returns:
        True se registrado com sucesso, False caso contrário
    """
    if not driver:
        logger.error("[registrar_driver] Driver não fornecido")
        return False
    
    chave = _gerar_chave_driver(ambiente, usuario)
    
    with _lock_drivers:
        # Se já existe um driver para esta chave, fecha o anterior
        driver_anterior = _drivers_ativos.get(chave)
        if driver_anterior:
            try:
                driver_anterior.quit()
                logger.info(f"[registrar_driver] Driver anterior fechado para {chave}")
            except Exception as e:
                logger.warning(f"[registrar_driver] Erro ao fechar driver anterior: {str(e)}")
        
        _drivers_ativos[chave] = driver
        logger.info(f"[registrar_driver] Driver registrado para {chave}")
        return True


def renovar_cookies_do_navegador(ambiente: str = "PRD", usuario: Optional[str] = None) -> Optional[list]:
    """
    Renova cookies extraindo diretamente do navegador aberto
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
    
    Returns:
        Lista de cookies atualizados ou None se falhou
    """
    driver = obter_driver_ativo(ambiente, usuario)
    
    if not driver:
        logger.warning(f"[renovar_cookies_do_navegador] Nenhum driver ativo encontrado para {ambiente}, {usuario}")
        return None
    
    try:
        # Verifica se o navegador ainda está na página do Fluig
        url_atual = driver.current_url
        
        # Se não estiver na página do Fluig, navega para ela
        ambiente_upper = ambiente.upper()
        from src.modelo_dados.modelo_settings import ConfigEnvSetings
        if ambiente_upper == "QLD":
            url_fluig = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            url_fluig = ConfigEnvSetings.URL_FLUIG_PRD
        
        if url_fluig not in url_atual:
            logger.info(f"[renovar_cookies_do_navegador] Navegando para {url_fluig} para manter sessão ativa")
            driver.get(url_fluig)
            import time
            time.sleep(2)  # Aguarda página carregar
        
        # Extrai cookies do navegador
        cookies = obter_cookies(driver)
        
        if cookies:
            # Salva os cookies atualizados
            if salvar_cookies(cookies, ambiente, usuario):
                logger.info(f"[renovar_cookies_do_navegador] Cookies renovados com sucesso do navegador para {ambiente}, {usuario}")
                return cookies
            else:
                logger.warning(f"[renovar_cookies_do_navegador] Falha ao salvar cookies renovados")
                return cookies
        
        logger.warning(f"[renovar_cookies_do_navegador] Nenhum cookie obtido do navegador")
        return None
        
    except Exception as e:
        logger.error(f"[renovar_cookies_do_navegador] Erro ao renovar cookies do navegador: {str(e)}")
        return None


def remover_driver(ambiente: str = "PRD", usuario: Optional[str] = None, fechar: bool = True) -> bool:
    """
    Remove e opcionalmente fecha um driver
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
        fechar: Se True, fecha o driver antes de remover
    
    Returns:
        True se removido com sucesso, False caso contrário
    """
    chave = _gerar_chave_driver(ambiente, usuario)
    
    with _lock_drivers:
        driver = _drivers_ativos.pop(chave, None)
        
        if driver:
            if fechar:
                try:
                    driver.quit()
                    logger.info(f"[remover_driver] Driver fechado e removido para {chave}")
                except Exception as e:
                    logger.warning(f"[remover_driver] Erro ao fechar driver: {str(e)}")
            else:
                logger.info(f"[remover_driver] Driver removido (sem fechar) para {chave}")
            return True
        
        logger.debug(f"[remover_driver] Nenhum driver encontrado para {chave}")
        return False


def fechar_todos_drivers():
    """Fecha todos os drivers ativos"""
    with _lock_drivers:
        drivers_para_fechar = list(_drivers_ativos.items())
        _drivers_ativos.clear()
    
    for chave, driver in drivers_para_fechar:
        try:
            driver.quit()
            logger.info(f"[fechar_todos_drivers] Driver fechado: {chave}")
        except Exception as e:
            logger.warning(f"[fechar_todos_drivers] Erro ao fechar driver {chave}: {str(e)}")
    
    logger.info(f"[fechar_todos_drivers] Todos os drivers fechados")


def obter_status_drivers() -> Dict[str, Any]:
    """
    Retorna o status de todos os drivers ativos
    
    Returns:
        Dicionário com informações dos drivers
    """
    with _lock_drivers:
        status = {}
        for chave, driver in _drivers_ativos.items():
            try:
                url = driver.current_url
                titulo = driver.title
                status[chave] = {
                    'url': url,
                    'titulo': titulo,
                    'ativo': True
                }
            except Exception as e:
                status[chave] = {
                    'url': None,
                    'titulo': None,
                    'ativo': False,
                    'erro': str(e)
                }
        
        return {
            'total_drivers': len(status),
            'drivers': status
        }
