"""Módulo centralizado para gerenciar autenticação e cookies do Fluig"""
import time
import base64
import json as json_lib
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from src.utilitarios_centrais.logger import logger
from src.web.web_login_fluig import fazer_login_fluig
from src.web.web_cookies import (
    carregar_cookies,
    verificar_cookies_validos,
    limpar_cookies
)


def extrair_exp_jwt(jwt_token: str) -> Optional[int]:
    """
    Extrai o timestamp de expiração (exp) de um JWT
    
    Args:
        jwt_token: Token JWT completo
    
    Returns:
        Timestamp de expiração ou None se não conseguir decodificar
    """
    try:

        parts = jwt_token.split('.')
        if len(parts) < 2:
            return None
        

        payload_encoded = parts[1]
        
  
        padding = len(payload_encoded) % 4
        if padding:
            payload_encoded += '=' * (4 - padding)

        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json_lib.loads(payload_decoded)

        exp = payload.get('exp')
        if exp:
            return int(exp)
        return None
        
    except Exception as e:
        logger.debug(f"[extrair_exp_jwt] Erro ao extrair exp do JWT: {str(e)}")
        return None


def verificar_expiracao_cookies(cookies: List[Dict]) -> bool:
    """
    Verifica se os cookies estão válidos baseado na data de expiração
    
    Verifica tanto o expiry do cookie quanto o exp do JWT (se presente).
    Usa o menor valor entre os dois para determinar se está expirado.
    
    Args:
        cookies: Lista de cookies
    
    Returns:
        True se cookies estão válidos, False caso contrário
    """
    try:
        if not cookies:
            logger.warning("[verificar_expiracao_cookies] Nenhum cookie fornecido")
            return False
        
        agora = time.time()
        cookies_importantes = ['JSESSIONID', 'JSESSIONIDSSO']
        cookies_encontrados = {nome: False for nome in cookies_importantes}
        jwt_exp = None

        for cookie in cookies:
            nome = cookie.get('name', '')
            if nome == 'jwt.token':
                jwt_value = cookie.get('value', '')
                if jwt_value:
                    jwt_exp = extrair_exp_jwt(jwt_value)
                    if jwt_exp:
                        logger.debug(f"[verificar_expiracao_cookies] JWT exp encontrado: {datetime.fromtimestamp(jwt_exp)}")
                    break

        if jwt_exp:
            if jwt_exp <= agora:
                logger.warning(f"[verificar_expiracao_cookies] JWT expirado em {datetime.fromtimestamp(jwt_exp)}")
                return False
            else:
                tempo_restante_jwt = jwt_exp - agora
                horas_restantes_jwt = tempo_restante_jwt / 3600
                logger.debug(f"[verificar_expiracao_cookies] JWT válido por mais {horas_restantes_jwt:.2f} horas")
        

        for cookie in cookies:
            nome = cookie.get('name', '')
            expira = cookie.get('expiry')
            

            if nome in cookies_importantes:
                cookies_encontrados[nome] = True
                
 
                if not expira:
                    logger.debug(f"[verificar_expiracao_cookies] Cookie {nome} sem expiração (sessão)")

                    continue

                if expira <= agora:
                    logger.warning(f"[verificar_expiracao_cookies] Cookie {nome} expirado (expiry: {datetime.fromtimestamp(expira)})")
                    return False
 
                if jwt_exp:
                    expiracao_mais_proxima = min(expira, jwt_exp)
                    if expiracao_mais_proxima <= agora:
                        logger.warning(f"[verificar_expiracao_cookies] Autenticação expirada (JWT exp: {datetime.fromtimestamp(jwt_exp)}, Cookie expiry: {datetime.fromtimestamp(expira)})")
                        return False
                    
                    tempo_restante = expiracao_mais_proxima - agora
                    horas_restantes = tempo_restante / 3600
                    logger.debug(f"[verificar_expiracao_cookies] Cookie {nome} válido por mais {horas_restantes:.2f} horas (expira em: {datetime.fromtimestamp(expiracao_mais_proxima)})")
                else:
                    tempo_restante = expira - agora
                    horas_restantes = tempo_restante / 3600
                    logger.debug(f"[verificar_expiracao_cookies] Cookie {nome} válido por mais {horas_restantes:.2f} horas")
        
        cookies_validos = sum(cookies_encontrados.values())
        if cookies_validos > 0:
            if jwt_exp:
                logger.info(f"[verificar_expiracao_cookies] {cookies_validos} cookie(s) importante(s) válido(s) - JWT expira em {datetime.fromtimestamp(jwt_exp)}")
            else:
                logger.info(f"[verificar_expiracao_cookies] {cookies_validos} cookie(s) importante(s) válido(s)")
            return True
        else:
            logger.warning("[verificar_expiracao_cookies] Nenhum cookie importante encontrado")
            return False
            
    except Exception as e:
        logger.error(f"[verificar_expiracao_cookies] Erro ao verificar expiração: {str(e)}")
        return False


def garantir_autenticacao(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Garante que há autenticação válida para o ambiente
    
    Verifica cookies existentes e válidos. Se não houver ou estiverem expirados,
    realiza login automaticamente.
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        forcar_login: Se True, força novo login mesmo com cookies válidos
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
    
    Returns:
        Tupla (sucesso: bool, cookies: Optional[List[Dict]])
        - sucesso: True se autenticação está válida, False caso contrário
        - cookies: Lista de cookies válidos ou None
    """
    try:
        logger.info(f"[garantir_autenticacao] Verificando autenticação para ambiente {ambiente}, usuário: {usuario}")
        

        if forcar_login:
            logger.info("[garantir_autenticacao] Forçando novo login...")
            limpar_cookies(ambiente, usuario)
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                return (True, cookies)
            return (False, None)
        

        if not verificar_cookies_validos(ambiente, usuario):
            logger.info("[garantir_autenticacao] Cookies não encontrados, realizando login...")
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                return (True, cookies)
            return (False, None)
        

        cookies = carregar_cookies(ambiente, usuario)
        if not cookies:
            logger.warning("[garantir_autenticacao] Erro ao carregar cookies, realizando login...")
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                return (True, cookies)
            return (False, None)

        if verificar_expiracao_cookies(cookies):
            logger.info(f"[garantir_autenticacao] Cookies válidos para ambiente {ambiente}, usuário: {usuario}")
            return (True, cookies)
        else:
            logger.warning("[garantir_autenticacao] Cookies expirados, realizando novo login...")
            limpar_cookies(ambiente, usuario)
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                return (True, cookies)
            return (False, None)
            
    except Exception as e:
        logger.error(f"[garantir_autenticacao] Erro ao garantir autenticação: {str(e)}")
        return (False, None)


def realizar_login(ambiente: str = "PRD", usuario: str = None, senha: str = None) -> bool:
    """
    Realiza login no Fluig e salva cookies
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
    
    Returns:
        True se login foi bem-sucedido, False caso contrário
    """
    try:
        logger.info(f"[realizar_login] Iniciando login para ambiente {ambiente}, usuário: {usuario}")
        driver = fazer_login_fluig(ambiente, usuario, senha)
        
        if not driver:
            logger.error("[realizar_login] Falha ao realizar login")
            return False
        

        driver.quit()
        logger.info("[realizar_login] Login concluído com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"[realizar_login] Erro ao realizar login: {str(e)}")
        return False


def obter_cookies_validos(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Optional[List[Dict]]:
    """
    Obtém cookies válidos, realizando login se necessário
    
    Esta é a função principal que deve ser usada para garantir autenticação.
    Ela verifica cookies existentes, valida expiração (incluindo JWT) e faz login se necessário.
    Carrega cookies APENAS UMA VEZ.
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        forcar_login: Se True, força novo login mesmo com cookies válidos
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
    
    Returns:
        Lista de cookies válidos ou None se falhou
    """
    try:

        sucesso, cookies = garantir_autenticacao(ambiente, forcar_login, usuario, senha)
        
        if not sucesso or not cookies:
            logger.error(f"[obter_cookies_validos] Falha ao garantir autenticação para {ambiente}, usuário: {usuario}")
            return None
        
        logger.info(f"[obter_cookies_validos] {len(cookies)} cookies válidos obtidos para {ambiente}, usuário: {usuario}")
        return cookies
        
    except Exception as e:
        logger.error(f"[obter_cookies_validos] Erro ao obter cookies válidos: {str(e)}")
        return None

