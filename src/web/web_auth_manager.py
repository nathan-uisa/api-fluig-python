"""Módulo centralizado para gerenciar autenticação e cookies do Fluig"""
import time
import base64
import json as json_lib
import threading
import requests
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from src.utilitarios_centrais.logger import logger
from src.web.web_login_fluig import fazer_login_fluig
from src.web.web_cookies import (
    carregar_cookies,
    verificar_cookies_validos,
    limpar_cookies,
    salvar_cookies,
    cookies_para_requests,
    obter_cookies
)
from src.modelo_dados.modelo_settings import ConfigEnvSetings

# Configurações de renovação automática
TEMPO_ANTECEDENCIA_RENOVACAO = 300  # Renovar 5 minutos antes de expirar (em segundos)
INTERVALO_VERIFICACAO = 60  # Verificar a cada 60 segundos
TIMEOUT_KEEPALIVE = 30  # Timeout para requisição keepAlive

# Dicionário para armazenar sessões ativas sendo monitoradas
_sessoes_ativas: Dict[str, Dict[str, Any]] = {}
_lock_sessoes = threading.Lock()
_thread_renovacao: Optional[threading.Thread] = None
_parar_renovacao = threading.Event()


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


def _obter_url_base(ambiente: str) -> str:
    """Obtém a URL base do Fluig para o ambiente especificado"""
    if ambiente.upper() == "PRD":
        return ConfigEnvSetings.URL_FLUIG_PRD
    elif ambiente.upper() == "QLD":
        return ConfigEnvSetings.URL_FLUIG_QLD
    else:
        raise ValueError(f"Ambiente inválido: {ambiente}")


def _gerar_chave_sessao(ambiente: str, usuario: Optional[str]) -> str:
    """Gera uma chave única para identificar a sessão"""
    usuario_safe = usuario or "default"
    return f"{ambiente.upper()}_{usuario_safe}"


def obter_tempo_expiracao_jwt(cookies: List[Dict]) -> Optional[int]:
    """
    Obtém o tempo restante em segundos até a expiração do JWT
    
    Args:
        cookies: Lista de cookies
    
    Returns:
        Segundos até expiração ou None se não conseguir determinar
    """
    try:
        for cookie in cookies:
            if cookie.get('name') == 'jwt.token':
                jwt_value = cookie.get('value', '')
                if jwt_value:
                    jwt_exp = extrair_exp_jwt(jwt_value)
                    if jwt_exp:
                        tempo_restante = jwt_exp - time.time()
                        return int(tempo_restante) if tempo_restante > 0 else 0
        return None
    except Exception as e:
        logger.debug(f"[obter_tempo_expiracao_jwt] Erro: {str(e)}")
        return None


def renovar_sessao_keepalive(
    cookies: List[Dict], 
    ambiente: str = "PRD",
    usuario: Optional[str] = None
) -> Optional[List[Dict]]:
    """
    Renova a sessão do Fluig via navegador aberto (mais seguro) ou endpoint keepAlive (fallback)
    
    Prioriza renovação via navegador aberto. Se não houver navegador aberto, usa keepAlive.
    
    Args:
        cookies: Lista de cookies atuais
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário para identificar os cookies
    
    Returns:
        Lista de cookies atualizados ou None se falhou
    """
    # Primeiro tenta renovar via navegador aberto (mais seguro)
    try:
        from src.web.web_driver_manager import renovar_cookies_do_navegador
        cookies_navegador = renovar_cookies_do_navegador(ambiente, usuario)
        
        if cookies_navegador:
            tempo_restante = obter_tempo_expiracao_jwt(cookies_navegador)
            if tempo_restante:
                logger.info(f"[renovar_sessao_keepalive] Sessão renovada via navegador! JWT válido por mais {tempo_restante // 60} minutos")
            else:
                logger.info("[renovar_sessao_keepalive] Sessão renovada via navegador com sucesso")
            return cookies_navegador
    except Exception as e:
        logger.debug(f"[renovar_sessao_keepalive] Falha ao renovar via navegador, tentando keepAlive: {str(e)}")
    
    # Fallback: usa endpoint keepAlive se navegador não estiver disponível
    try:
        url_base = _obter_url_base(ambiente)
        timestamp = int(time.time() * 1000)
        url = f"{url_base}/portal/api/rest/session/keepAlive?space=&_={timestamp}"
        
        # Converte cookies para formato requests
        cookies_dict = cookies_para_requests(cookies)
        
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/json; charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        logger.info(f"[renovar_sessao_keepalive] Renovando sessão via keepAlive para {ambiente}, usuário: {usuario}")
        
        response = requests.get(
            url, 
            cookies=cookies_dict, 
            headers=headers,
            timeout=TIMEOUT_KEEPALIVE
        )
        
        if response.status_code != 200:
            logger.warning(f"[renovar_sessao_keepalive] Status {response.status_code} - Resposta: {response.text}")
            return None
        
        # Verifica se a resposta é válida
        if response.text.strip() not in ['"ok"', 'ok']:
            logger.warning(f"[renovar_sessao_keepalive] Resposta inesperada: {response.text}")
            return None
        
        # Extrai novos cookies da resposta
        novos_cookies_response = response.cookies.get_dict()
        
        if not novos_cookies_response:
            logger.debug("[renovar_sessao_keepalive] Nenhum cookie novo na resposta, mantendo atuais")
            return cookies
        
        # Atualiza cookies existentes com os novos valores
        cookies_atualizados = _atualizar_cookies(cookies, novos_cookies_response)
        
        # Salva os cookies atualizados
        if salvar_cookies(cookies_atualizados, ambiente, usuario):
            tempo_restante = obter_tempo_expiracao_jwt(cookies_atualizados)
            if tempo_restante:
                logger.info(f"[renovar_sessao_keepalive] Sessão renovada via keepAlive! JWT válido por mais {tempo_restante // 60} minutos")
            else:
                logger.info("[renovar_sessao_keepalive] Sessão renovada via keepAlive com sucesso")
            return cookies_atualizados
        else:
            logger.warning("[renovar_sessao_keepalive] Falha ao salvar cookies atualizados")
            return cookies_atualizados
            
    except requests.exceptions.Timeout:
        logger.error("[renovar_sessao_keepalive] Timeout na requisição keepAlive")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"[renovar_sessao_keepalive] Erro de requisição: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[renovar_sessao_keepalive] Erro ao renovar sessão: {str(e)}")
        return None


def _atualizar_cookies(cookies_atuais: List[Dict], novos_valores: Dict[str, str]) -> List[Dict]:
    """
    Atualiza lista de cookies com novos valores
    
    Args:
        cookies_atuais: Lista de cookies atual
        novos_valores: Dicionário com novos valores de cookies
    
    Returns:
        Lista de cookies atualizada
    """
    cookies_atualizados = []
    cookies_atualizados_nomes = set()
    
    for cookie in cookies_atuais:
        nome = cookie.get('name', '')
        if nome in novos_valores:
            # Atualiza o valor do cookie existente
            cookie_atualizado = cookie.copy()
            cookie_atualizado['value'] = novos_valores[nome]
            
            # Se for jwt.token, atualiza também a expiração baseada no novo JWT
            if nome == 'jwt.token':
                novo_exp = extrair_exp_jwt(novos_valores[nome])
                if novo_exp:
                    cookie_atualizado['expiry'] = novo_exp
                    
            cookies_atualizados.append(cookie_atualizado)
            cookies_atualizados_nomes.add(nome)
        else:
            cookies_atualizados.append(cookie)
            cookies_atualizados_nomes.add(nome)
    
    # Adiciona cookies novos que não existiam
    for nome, valor in novos_valores.items():
        if nome not in cookies_atualizados_nomes:
            novo_cookie = {
                'name': nome,
                'value': valor,
                'domain': '.uisa.com.br',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            cookies_atualizados.append(novo_cookie)
    
    return cookies_atualizados


def _verificar_e_renovar_sessoes():
    """
    Thread que verifica periodicamente e renova sessões ativas antes de expirarem
    Usa navegador aberto diretamente para renovação, sem carregar cookies do arquivo
    """
    logger.info("[_verificar_e_renovar_sessoes] Thread de renovação automática iniciada")
    
    while not _parar_renovacao.is_set():
        try:
            with _lock_sessoes:
                sessoes_para_renovar = list(_sessoes_ativas.items())
            
            for chave, sessao in sessoes_para_renovar:
                try:
                    ambiente = sessao.get('ambiente', 'PRD')
                    usuario = sessao.get('usuario')
                    
                    # Verifica se há driver/navegador ativo
                    from src.web.web_driver_manager import obter_driver_ativo, renovar_cookies_do_navegador
                    driver = obter_driver_ativo(ambiente, usuario)
                    
                    if not driver:
                        logger.debug(f"[_verificar_e_renovar_sessoes] Sem driver ativo para {chave}, removendo da lista")
                        with _lock_sessoes:
                            _sessoes_ativas.pop(chave, None)
                        continue
                    
                    # Obtém cookies diretamente do navegador para verificar expiração
                    try:
                        cookies_navegador = obter_cookies(driver)
                        if not cookies_navegador:
                            logger.debug(f"[_verificar_e_renovar_sessoes] Não foi possível obter cookies do navegador para {chave}")
                            continue
                        
                        # Verifica tempo restante
                        tempo_restante = obter_tempo_expiracao_jwt(cookies_navegador)
                        
                        if tempo_restante is None:
                            logger.debug(f"[_verificar_e_renovar_sessoes] Não foi possível obter tempo de expiração para {chave}")
                            continue
                        
                        # Se está próximo de expirar, renova via navegador
                        if tempo_restante <= TEMPO_ANTECEDENCIA_RENOVACAO:
                            logger.info(f"[_verificar_e_renovar_sessoes] Sessão {chave} expira em {tempo_restante}s, renovando via navegador...")
                            
                            novos_cookies = renovar_cookies_do_navegador(ambiente, usuario)
                            
                            if novos_cookies:
                                logger.info(f"[_verificar_e_renovar_sessoes] Sessão {chave} renovada com sucesso via navegador")
                            else:
                                logger.warning(f"[_verificar_e_renovar_sessoes] Falha ao renovar sessão {chave} via navegador, será necessário re-login")
                                # Remove da lista para forçar re-login na próxima operação
                                with _lock_sessoes:
                                    _sessoes_ativas.pop(chave, None)
                        else:
                            minutos_restantes = tempo_restante // 60
                            logger.debug(f"[_verificar_e_renovar_sessoes] Sessão {chave} válida por mais {minutos_restantes} minutos")
                    
                    except Exception as e:
                        logger.warning(f"[_verificar_e_renovar_sessoes] Erro ao verificar cookies do navegador para {chave}: {str(e)}")
                        # Remove sessão se navegador não está mais acessível
                        with _lock_sessoes:
                            _sessoes_ativas.pop(chave, None)
                        
                except Exception as e:
                    logger.error(f"[_verificar_e_renovar_sessoes] Erro ao verificar sessão {chave}: {str(e)}")
            
            # Aguarda próximo ciclo de verificação
            _parar_renovacao.wait(timeout=INTERVALO_VERIFICACAO)
            
        except Exception as e:
            logger.error(f"[_verificar_e_renovar_sessoes] Erro no loop de renovação: {str(e)}")
            _parar_renovacao.wait(timeout=INTERVALO_VERIFICACAO)
    
    logger.info("[_verificar_e_renovar_sessoes] Thread de renovação automática encerrada")


def iniciar_renovacao_automatica():
    """
    Inicia a thread de renovação automática de cookies
    
    Deve ser chamada na inicialização da aplicação (ex: main.py)
    """
    global _thread_renovacao
    
    with _lock_sessoes:
        if _thread_renovacao is not None and _thread_renovacao.is_alive():
            logger.debug("[iniciar_renovacao_automatica] Thread já está em execução")
            return
        
        _parar_renovacao.clear()
        _thread_renovacao = threading.Thread(
            target=_verificar_e_renovar_sessoes,
            name="FluigSessionRenewal",
            daemon=True
        )
        _thread_renovacao.start()
        logger.info("[iniciar_renovacao_automatica] Renovação automática de cookies iniciada")


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


def registrar_sessao_ativa(ambiente: str = "PRD", usuario: Optional[str] = None):
    """
    Registra uma sessão para ser monitorada e renovada automaticamente
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Nome do usuário
    """
    chave = _gerar_chave_sessao(ambiente, usuario)
    
    with _lock_sessoes:
        _sessoes_ativas[chave] = {
            'ambiente': ambiente,
            'usuario': usuario,
            'registrado_em': time.time()
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
            ambiente = sessao.get('ambiente', 'PRD')
            usuario = sessao.get('usuario')
            cookies = carregar_cookies(ambiente, usuario)
            
            tempo_restante = None
            if cookies:
                tempo_restante = obter_tempo_expiracao_jwt(cookies)
            
            status[chave] = {
                'ambiente': ambiente,
                'usuario': usuario,
                'tempo_restante_segundos': tempo_restante,
                'tempo_restante_minutos': tempo_restante // 60 if tempo_restante else None,
                'registrado_em': datetime.fromtimestamp(sessao.get('registrado_em', 0)).isoformat()
            }
        
        return {
            'sessoes_ativas': len(status),
            'intervalo_verificacao_segundos': INTERVALO_VERIFICACAO,
            'antecedencia_renovacao_segundos': TEMPO_ANTECEDENCIA_RENOVACAO,
            'thread_ativa': _thread_renovacao is not None and _thread_renovacao.is_alive(),
            'sessoes': status
        }


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
    tenta renovar via keepAlive. Se falhar, realiza login automaticamente.
    
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
                registrar_sessao_ativa(ambiente, usuario)
                return (True, cookies)
            return (False, None)
        

        if not verificar_cookies_validos(ambiente, usuario):
            logger.info("[garantir_autenticacao] Cookies não encontrados, realizando login...")
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario)
                return (True, cookies)
            return (False, None)
        

        cookies = carregar_cookies(ambiente, usuario)
        if not cookies:
            logger.warning("[garantir_autenticacao] Erro ao carregar cookies, realizando login...")
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario)
                return (True, cookies)
            return (False, None)

        if verificar_expiracao_cookies(cookies):
            # Verifica se está próximo de expirar e tenta renovar proativamente
            tempo_restante = obter_tempo_expiracao_jwt(cookies)
            if tempo_restante and tempo_restante <= TEMPO_ANTECEDENCIA_RENOVACAO:
                logger.info(f"[garantir_autenticacao] JWT expira em {tempo_restante}s, tentando renovar via keepAlive...")
                novos_cookies = renovar_sessao_keepalive(cookies, ambiente, usuario)
                if novos_cookies:
                    logger.info("[garantir_autenticacao] Sessão renovada via keepAlive")
                    registrar_sessao_ativa(ambiente, usuario)
                    return (True, novos_cookies)
                else:
                    logger.warning("[garantir_autenticacao] Falha no keepAlive, cookies ainda válidos")
            
            logger.info(f"[garantir_autenticacao] Cookies válidos para ambiente {ambiente}, usuário: {usuario}")
            registrar_sessao_ativa(ambiente, usuario)
            return (True, cookies)
        else:
            # Cookies expirados - tenta renovar via keepAlive primeiro
            logger.warning("[garantir_autenticacao] Cookies expirados, tentando renovar via keepAlive...")
            novos_cookies = renovar_sessao_keepalive(cookies, ambiente, usuario)
            
            if novos_cookies and verificar_expiracao_cookies(novos_cookies):
                logger.info("[garantir_autenticacao] Sessão recuperada via keepAlive!")
                registrar_sessao_ativa(ambiente, usuario)
                return (True, novos_cookies)
            
            # keepAlive falhou, faz login completo
            logger.warning("[garantir_autenticacao] keepAlive falhou, realizando login completo...")
            limpar_cookies(ambiente, usuario)
            if realizar_login(ambiente, usuario, senha):
                cookies = carregar_cookies(ambiente, usuario)
                registrar_sessao_ativa(ambiente, usuario)
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
        
        # MODIFICADO: Remover comentário quando o driver for fechado automaticamente
        #driver.quit()
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

