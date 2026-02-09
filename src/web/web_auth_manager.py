"""Módulo centralizado para gerenciar autenticação e cookies do Fluig"""
import threading
from typing import Optional, List, Dict, Tuple
from src.utilitarios_centrais.logger import logger
from src.web.web_login_fluig import fazer_login_fluig
from src.web.web_cookies import (
    carregar_cookies,
    verificar_cookies_validos,
    limpar_cookies,
)
from src.modelo_dados.modelo_settings import ConfigEnvSetings

# Configuração de renovação de cookies
INTERVALO_RENOVACAO = 10 * 60  # 10 minutos em segundos

# Controle das threads
_lock = threading.Lock()
_thread_renovacao: Optional[threading.Thread] = None
_parar_renovacao = threading.Event()
_login_em_andamento = {}  # Dicionário para rastrear logins em andamento por usuário
_lock_login = threading.Lock()  # Lock para proteger logins simultâneos


def _obter_url_base(ambiente: str) -> str:
    """Obtém a URL base do Fluig para o ambiente especificado"""
    if ambiente.upper() == "PRD":
        return ConfigEnvSetings.URL_FLUIG_PRD
    elif ambiente.upper() == "QLD":
        return ConfigEnvSetings.URL_FLUIG_QLD
    else:
        raise ValueError(f"Ambiente inválido: {ambiente}")


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
    driver = None
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
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False


def _fazer_login_thread(ambiente: str, usuario: str, senha: str):
    """
    Executa o login em uma thread separada para não bloquear o processo principal
    """
    chave_login = f"{ambiente}_{usuario}"
    
    # Verifica se já existe um login em andamento para este usuário
    with _lock_login:
        if chave_login in _login_em_andamento and _login_em_andamento[chave_login]:
            logger.warning(f"[_fazer_login_thread] Login já em andamento para {usuario} no ambiente {ambiente}. Pulando...")
            return
        _login_em_andamento[chave_login] = True
    
    try:
        logger.info(f"[_fazer_login_thread] Iniciando login em thread para {usuario} no ambiente {ambiente}")
        sucesso = realizar_login(ambiente, usuario, senha)
        if sucesso:
            logger.info(f"[_fazer_login_thread] Login concluído com sucesso para {usuario}")
        else:
            logger.error(f"[_fazer_login_thread] Login falhou para {usuario}")
    except Exception as e:
        logger.error(f"[_fazer_login_thread] Erro: {str(e)}")
        import traceback
        logger.error(f"[_fazer_login_thread] Traceback: {traceback.format_exc()}")
    finally:
        # Remove a flag de login em andamento
        with _lock_login:
            _login_em_andamento[chave_login] = False


def _renovar_cookies_periodicamente():
    """
    Thread que renova cookies a cada 10 minutos para o usuário admin configurado
    (FLUIG_ADMIN_USER)
    """
    logger.info("[_renovar_cookies_periodicamente] Thread de renovação de cookies iniciada")
    
    # Lista de usuários a serem monitorados (apenas FLUIG_ADMIN_USER)
    usuarios = [
        {
            'usuario': ConfigEnvSetings.FLUIG_ADMIN_USER,
            'senha': ConfigEnvSetings.FLUIG_ADMIN_PASS,
            'ambiente': 'PRD'
        }
    ]
    
    while not _parar_renovacao.is_set():
        try:
            threads_login = []
            
            for config in usuarios:
                if _parar_renovacao.is_set():
                    break
                
                usuario = config['usuario']
                senha = config['senha']
                ambiente = config['ambiente']
                
                # Verifica se já existe login em andamento antes de iniciar novo
                chave_login = f"{ambiente}_{usuario}"
                with _lock_login:
                    if chave_login in _login_em_andamento and _login_em_andamento[chave_login]:
                        logger.info(f"[_renovar_cookies_periodicamente] Login já em andamento para {usuario}, aguardando...")
                        continue
                
                logger.info(f"[_renovar_cookies_periodicamente] Renovando cookies para {usuario}...")
                
                # Executa login em thread separada para não bloquear
                thread_login = threading.Thread(
                    target=_fazer_login_thread,
                    args=(ambiente, usuario, senha),
                    name=f"Login_{usuario}"
                )
                thread_login.start()
                threads_login.append(thread_login)
                
                # Pequeno delay entre inícios de threads para evitar sobrecarga
                import time
                time.sleep(2)
            
            # Aguarda todas as threads de login completarem (timeout de 5 minutos cada)
            # Timeout aumentado para ambiente Docker/Cloud Run que pode ser mais lento
            for thread in threads_login:
                thread.join(timeout=300)  # 5 minutos
                if thread.is_alive():
                    logger.warning(f"[_renovar_cookies_periodicamente] Login {thread.name} excedeu o timeout de 5 minutos")
                    # Não mata a thread, apenas registra o warning - ela pode completar depois
            
            # Aguarda próximo ciclo de renovação (10 minutos)
            logger.info(f"[_renovar_cookies_periodicamente] Próxima renovação em {INTERVALO_RENOVACAO // 60} minutos")
            _parar_renovacao.wait(timeout=INTERVALO_RENOVACAO)
            
        except Exception as e:
            logger.error(f"[_renovar_cookies_periodicamente] Erro no loop de renovação: {str(e)}")
            _parar_renovacao.wait(timeout=60)  # Em caso de erro, aguarda 1 minuto
    
    logger.info("[_renovar_cookies_periodicamente] Thread de renovação de cookies encerrada")


def iniciar_login_automatico():
    """
    Inicia a thread de renovação automática de cookies
    
    Deve ser chamada na inicialização da aplicação
    """
    global _thread_renovacao
    
    with _lock:
        if _thread_renovacao is not None and _thread_renovacao.is_alive():
            logger.warning("[iniciar_login_automatico] Thread já está em execução. Ignorando nova inicialização.")
            return
        
        # Limpa flags de login em andamento
        with _lock_login:
            _login_em_andamento.clear()
        
        _parar_renovacao.clear()
        _thread_renovacao = threading.Thread(
            target=_renovar_cookies_periodicamente,
            name="FluigCookieRenewal",
            daemon=True
        )
        _thread_renovacao.start()
        logger.info("[iniciar_login_automatico] Renovação automática de cookies iniciada (intervalo: 10 minutos)")


def parar_login_automatico():
    """
    Para a thread de renovação automática de cookies
    """
    global _thread_renovacao
    
    _parar_renovacao.set()
    
    if _thread_renovacao is not None:
        _thread_renovacao.join(timeout=5)
        logger.info("[parar_login_automatico] Thread de renovação de cookies encerrada")
        _thread_renovacao = None


def garantir_autenticacao(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Garante que há autenticação válida para o ambiente
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        forcar_login: Se True, força novo login mesmo com cookies válidos
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
    
    Returns:
        Tupla (sucesso: bool, cookies: Optional[List[Dict]])
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
        
        logger.info(f"[garantir_autenticacao] Cookies válidos para ambiente {ambiente}, usuário: {usuario}")
        return (True, cookies)
            
    except Exception as e:
        logger.error(f"[garantir_autenticacao] Erro ao garantir autenticação: {str(e)}")
        return (False, None)


def obter_cookies_validos(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Optional[List[Dict]]:
    """
    Obtém cookies válidos, realizando login se necessário
    
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
