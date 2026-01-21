"""Módulo centralizado para gerenciar autenticação e cookies do Fluig"""
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from src.utilitarios_centrais.logger import logger
from src.web.web_login_fluig import fazer_login_fluig
from src.web.web_cookies import (
    carregar_cookies,
    verificar_cookies_validos,
    limpar_cookies
)
from src.modelo_dados.modelo_settings import ConfigEnvSetings

# Configurações de renovação automática
INTERVALO_LOGIN_AUTOMATICO = 180  # Fazer login a cada 20 minutos (em segundos)

# Dicionário para armazenar sessões ativas sendo monitoradas
_sessoes_ativas: Dict[str, Dict[str, Any]] = {}
_lock_sessoes = threading.Lock()
_thread_renovacao: Optional[threading.Thread] = None
_parar_renovacao = threading.Event()

# Dicionário para rastrear logins em execução (evita múltiplos logins simultâneos para mesma sessão)
_logins_em_execucao: Dict[str, Dict[str, Any]] = {}
_lock_logins = threading.Lock()


def _gerar_chave_sessao(ambiente: str, usuario: Optional[str]) -> str:
    """Gera uma chave única para identificar a sessão"""
    usuario_safe = usuario or "default"
    return f"{ambiente.upper()}_{usuario_safe}"


def _renovar_sessoes_periodicamente():
    """
    Thread que faz login automaticamente a cada 20 minutos para todas as sessões ativas
    """
    logger.info("[_renovar_sessoes_periodicamente] Thread de renovação automática iniciada")
    
    while not _parar_renovacao.is_set():
        try:
            with _lock_sessoes:
                sessoes_para_renovar = list(_sessoes_ativas.items())
            
            for chave, sessao in sessoes_para_renovar:
                try:
                    ambiente = sessao.get('ambiente', 'PRD')
                    usuario = sessao.get('usuario')
                    senha = sessao.get('senha')
                    
                    # Se senha não estiver na sessão, usa as configurações padrão
                    if not senha:
                        senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
                    if not usuario:
                        usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
                    
                    logger.info(f"[_renovar_sessoes_periodicamente] Renovando login para {chave}...")
                    
                    if realizar_login(ambiente, usuario, senha, em_thread=True):
                        logger.info(f"[_renovar_sessoes_periodicamente] Login renovado com sucesso para {chave}")
                        # Atualiza tempo de registro
                        with _lock_sessoes:
                            if chave in _sessoes_ativas:
                                _sessoes_ativas[chave]['ultimo_login'] = time.time()
                    else:
                        logger.error(f"[_renovar_sessoes_periodicamente] Falha ao renovar login para {chave}")
                        
                except Exception as e:
                    logger.error(f"[_renovar_sessoes_periodicamente] Erro ao renovar sessão {chave}: {str(e)}")
            
            # Aguarda 20 minutos antes do próximo ciclo
            _parar_renovacao.wait(timeout=INTERVALO_LOGIN_AUTOMATICO)
            
        except Exception as e:
            logger.error(f"[_renovar_sessoes_periodicamente] Erro no loop de renovação: {str(e)}")
            _parar_renovacao.wait(timeout=INTERVALO_LOGIN_AUTOMATICO)
    
    logger.info("[_renovar_sessoes_periodicamente] Thread de renovação automática encerrada")


def iniciar_renovacao_automatica():
    """
    Inicia a thread de renovação automática de cookies
    
    Faz login automaticamente a cada 20 minutos para todas as sessões ativas.
    Deve ser chamada na inicialização da aplicação (ex: main.py)
    """
    global _thread_renovacao
    
    with _lock_sessoes:
        if _thread_renovacao is not None and _thread_renovacao.is_alive():
            logger.debug("[iniciar_renovacao_automatica] Thread já está em execução")
            return
        
        _parar_renovacao.clear()
        _thread_renovacao = threading.Thread(
            target=_renovar_sessoes_periodicamente,
            name="FluigSessionRenewal",
            daemon=True
        )
        _thread_renovacao.start()
        logger.info(f"[iniciar_renovacao_automatica] Renovação automática iniciada (login a cada {INTERVALO_LOGIN_AUTOMATICO // 60} minutos)")


def parar_renovacao_automatica():
    """
    Para a thread de renovação automática
    
    Pode ser chamada no shutdown da aplicação
    """
    global _thread_renovacao
    
    _parar_renovacao.set()
    
    if _thread_renovacao is not None:
        _thread_renovacao.join(timeout=5)
        logger.info("[parar_renovacao_automatica] Thread de renovação encerrada")
        _thread_renovacao = None


def registrar_sessao_ativa(ambiente: str = "PRD", usuario: Optional[str] = None, senha: Optional[str] = None):
    """
    Registra uma sessão para ser monitorada e renovada automaticamente
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
        senha: Senha do usuário (opcional, se None usa FLUIG_ADMIN_PASS)
    """
    chave = _gerar_chave_sessao(ambiente, usuario)
    
    with _lock_sessoes:
        _sessoes_ativas[chave] = {
            'ambiente': ambiente,
            'usuario': usuario,
            'senha': senha,
            'registrado_em': time.time(),
            'ultimo_login': time.time()
        }
    
    logger.debug(f"[registrar_sessao_ativa] Sessão {chave} registrada para renovação automática")


def remover_sessao_ativa(ambiente: str = "PRD", usuario: Optional[str] = None):
    """
    Remove uma sessão do monitoramento automático
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
    """
    chave = _gerar_chave_sessao(ambiente, usuario)
    
    with _lock_sessoes:
        if chave in _sessoes_ativas:
            del _sessoes_ativas[chave]
            logger.debug(f"[remover_sessao_ativa] Sessão {chave} removida do monitoramento")


def obter_status_sessoes() -> Dict[str, Any]:
    """
    Retorna o status de todas as sessões ativas
    
    Returns:
        Dicionário com informações das sessões ativas
    """
    with _lock_sessoes:
        status = {}
        for chave, sessao in _sessoes_ativas.items():
            status[chave] = {
                'ambiente': sessao.get('ambiente', 'PRD'),
                'usuario': sessao.get('usuario'),
                'registrado_em': datetime.fromtimestamp(sessao.get('registrado_em', 0)).isoformat(),
                'ultimo_login': datetime.fromtimestamp(sessao.get('ultimo_login', 0)).isoformat() if sessao.get('ultimo_login') else None
            }
        
        return {
            'sessoes_ativas': len(status),
            'intervalo_login_minutos': INTERVALO_LOGIN_AUTOMATICO // 60,
            'thread_ativa': _thread_renovacao is not None and _thread_renovacao.is_alive(),
            'sessoes': status
        }


def garantir_autenticacao(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Garante que há autenticação válida para o ambiente
    
    Verifica cookies existentes e válidos. Se não houver ou estiverem expirados,
    realiza login automaticamente em thread separada para não bloquear outros processos.
    
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
        
        chave = _gerar_chave_sessao(ambiente, usuario)

        if forcar_login:
            logger.info("[garantir_autenticacao] Forçando novo login em thread...")
            limpar_cookies(ambiente, usuario)
            if realizar_login(ambiente, usuario, senha, em_thread=True):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario, senha)
                return (True, cookies)
            return (False, None)

        # Verifica se existem cookies válidos
        if not verificar_cookies_validos(ambiente, usuario):
            logger.info("[garantir_autenticacao] Cookies não encontrados ou inválidos, realizando login em thread...")
            if realizar_login(ambiente, usuario, senha, em_thread=True):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario, senha)
                return (True, cookies)
            return (False, None)

        # Cookies existem e estão válidos
        cookies = carregar_cookies(ambiente, usuario)
        if cookies:
            logger.info(f"[garantir_autenticacao] Cookies válidos para ambiente {ambiente}, usuário: {usuario}")
            registrar_sessao_ativa(ambiente, usuario, senha)
            return (True, cookies)
        else:
            logger.warning("[garantir_autenticacao] Erro ao carregar cookies, realizando login em thread...")
            if realizar_login(ambiente, usuario, senha, em_thread=True):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario, senha)
                return (True, cookies)
            return (False, None)
            
    except Exception as e:
        logger.error(f"[garantir_autenticacao] Erro ao garantir autenticação: {str(e)}")
        return (False, None)


def _realizar_login_thread(ambiente: str, usuario: str, senha: str, chave: str, evento: threading.Event, resultado: Dict[str, Any]):
    """
    Executa login em uma thread separada
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Usuário para login
        senha: Senha para login
        chave: Chave da sessão
        evento: Event para sinalizar quando o login terminar
        resultado: Dicionário para armazenar o resultado (sucesso e cookies)
    """
    try:
        logger.info(f"[_realizar_login_thread] Iniciando login em thread para ambiente {ambiente}, usuário: {usuario}")
        driver = fazer_login_fluig(ambiente, usuario, senha)
        
        if not driver:
            logger.error("[_realizar_login_thread] Falha ao realizar login")
            resultado['sucesso'] = False
            resultado['cookies'] = None
            evento.set()
            return

        driver.quit()
        cookies = carregar_cookies(ambiente, usuario)
        resultado['sucesso'] = True
        resultado['cookies'] = cookies
        logger.info("[_realizar_login_thread] Login concluído com sucesso em thread")
        evento.set()
        
    except Exception as e:
        logger.error(f"[_realizar_login_thread] Erro ao realizar login: {str(e)}")
        resultado['sucesso'] = False
        resultado['cookies'] = None
        evento.set()
    finally:
        # Remove do dicionário de logins em execução
        with _lock_logins:
            _logins_em_execucao.pop(chave, None)


def realizar_login(ambiente: str = "PRD", usuario: str = None, senha: str = None, em_thread: bool = True) -> bool:
    """
    Realiza login no Fluig e salva cookies
    
    Pode ser executado em thread separada para não bloquear outros processos.
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
        em_thread: Se True, executa login em thread separada (padrão: True)
    
    Returns:
        True se login foi bem-sucedido, False caso contrário
    """
    if not em_thread:
        # Execução síncrona (comportamento antigo, apenas para compatibilidade)
        try:
            logger.info(f"[realizar_login] Iniciando login síncrono para ambiente {ambiente}, usuário: {usuario}")
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
    
    # Execução em thread
    chave = _gerar_chave_sessao(ambiente, usuario)
    
    # Verifica se já existe um login em execução para esta sessão
    with _lock_logins:
        if chave in _logins_em_execucao:
            logger.debug(f"[realizar_login] Login já em execução para {chave}, aguardando conclusão...")
            evento_existente = _logins_em_execucao[chave]['evento']
            evento_existente.wait(timeout=300)  # Aguarda até 5 minutos
            
            with _lock_logins:
                if chave in _logins_em_execucao:
                    resultado_existente = _logins_em_execucao[chave]['resultado']
                    return resultado_existente.get('sucesso', False)
        
        # Cria nova thread para login
        evento = threading.Event()
        resultado = {'sucesso': False, 'cookies': None}
        _logins_em_execucao[chave] = {
            'evento': evento,
            'resultado': resultado
        }
    
    # Inicia thread de login
    thread_login = threading.Thread(
        target=_realizar_login_thread,
        args=(ambiente, usuario or ConfigEnvSetings.FLUIG_ADMIN_USER, 
              senha or ConfigEnvSetings.FLUIG_ADMIN_PASS, chave, evento, resultado),
        name=f"LoginThread-{chave}",
        daemon=True
    )
    thread_login.start()
    
    # Aguarda conclusão do login (com timeout de 5 minutos)
    evento.wait(timeout=300)
    
    with _lock_logins:
        if chave in _logins_em_execucao:
            sucesso = resultado.get('sucesso', False)
            return sucesso
    
    return resultado.get('sucesso', False)


def obter_cookies_validos(ambiente: str = "PRD", forcar_login: bool = False, usuario: str = None, senha: str = None) -> Optional[List[Dict]]:
    """
    Obtém cookies válidos, realizando login se necessário
    
    Esta é a função principal que deve ser usada para garantir autenticação.
    Ela verifica cookies existentes e faz login se necessário.
    
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
