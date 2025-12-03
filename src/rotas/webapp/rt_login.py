from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import urllib.parse
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelo_settings import ConfigEnvSetings

router = APIRouter()
templates = Jinja2Templates(directory="src/site/templates")

valid_domains = ['uisa.com.br']


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})


def _construir_redirect_uri(request: Request) -> str:
    """
    Constrói a URI de redirecionamento dinamicamente baseada na URL da requisição.
    Funciona tanto para localhost quanto para produção.
    Detecta HTTPS corretamente mesmo quando atrás de um proxy reverso (Google Cloud Run).
    """
    url = request.url
    hostname = url.hostname or ""
    
    # PRIORIDADE 1: Forçar HTTPS para Google Cloud Run (run.app)
    # Isso é crítico pois o proxy interno usa HTTP, mas externamente é HTTPS
    if hostname and "run.app" in hostname:
        scheme = "https"
        base_url = f"https://{hostname}"
        logger.info(f"[Redirect URI] Forçando HTTPS para Google Cloud Run - hostname: {hostname}")
    
    # PRIORIDADE 2: Localhost sempre HTTP
    elif hostname in ["127.0.0.1", "localhost"]:
        scheme = "http"
        if url.port and url.port != 80:
            base_url = f"http://{hostname}:{url.port}"
        else:
            base_url = f"http://{hostname}"
        logger.info(f"[Redirect URI] Usando HTTP para localhost - hostname: {hostname}")
    
    # PRIORIDADE 3: Verificar header X-Forwarded-Proto (usado por proxies)
    elif request.headers.get("X-Forwarded-Proto", "").lower() == "https":
        scheme = "https"
        base_url = f"https://{hostname}"
        logger.info(f"[Redirect URI] Usando HTTPS via X-Forwarded-Proto header - hostname: {hostname}")
    
    # PRIORIDADE 4: Verificar header Forwarded (padrão RFC 7239)
    elif request.headers.get("Forwarded", ""):
        forwarded_header = request.headers.get("Forwarded", "")
        forwarded_proto = None
        for part in forwarded_header.split(","):
            if "proto=" in part.lower():
                forwarded_proto = part.split("proto=")[-1].strip().strip('"').lower()
                break
        
        if forwarded_proto == "https":
            scheme = "https"
            base_url = f"https://{hostname}"
            logger.info(f"[Redirect URI] Usando HTTPS via Forwarded header - hostname: {hostname}")
        else:
            scheme = "http"
            if url.port and url.port != 80:
                base_url = f"http://{hostname}:{url.port}"
            else:
                base_url = f"http://{hostname}"
    
    # PRIORIDADE 5: Usar o scheme da URL (fallback)
    else:
        scheme = url.scheme
        if scheme == "https":
            base_url = f"https://{hostname}"
        elif url.port and url.port != 80:
            base_url = f"http://{hostname}:{url.port}"
        else:
            base_url = f"http://{hostname}"
        logger.warning(f"[Redirect URI] Usando scheme da URL como fallback: {scheme} - hostname: {hostname}")
    
    # Construir a URI de callback completa
    redirect_uri = f"{base_url}/login/google/callback"
    
    # Log detalhado para debug
    logger.info(f"[Redirect URI] URI construída: {redirect_uri}")
    logger.debug(f"[Redirect URI] Detalhes - scheme: {scheme}, hostname: {hostname}, "
                 f"X-Forwarded-Proto: {request.headers.get('X-Forwarded-Proto', 'N/A')}, "
                 f"Forwarded: {request.headers.get('Forwarded', 'N/A')}, "
                 f"url.scheme: {url.scheme}, url.port: {url.port}")
    
    return redirect_uri


@router.get("/login/google")
async def login_google(request: Request):
    """Inicia o processo de login com Google"""
    # Construir redirect URI dinamicamente a partir da URL da requisição
    redirect_uri = _construir_redirect_uri(request)
    
    GOOGLE_CLIENT_ID = ConfigEnvSetings.GOOGLE_CLIENT_ID
    GOOGLE_AUTH_URI = ConfigEnvSetings.GOOGLE_AUTH_URI or 'https://accounts.google.com/o/oauth2/auth'
    
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'openid email profile',
        'response_type': 'code',
        'access_type': 'offline'
    }
    
    auth_url = GOOGLE_AUTH_URI + '?' + urllib.parse.urlencode(params)
    
    # Log detalhado para debug do redirect_uri_mismatch
    logger.info(f"Iniciando autenticação Google")
    logger.info(f"⚠️ Redirect URI sendo enviada ao Google: {redirect_uri}")
    logger.info(f"URL da requisição original: {request.url}")
    logger.info(f"X-Forwarded-Proto header: {request.headers.get('X-Forwarded-Proto', 'N/A')}")
    logger.warning(f"⚠️ CERTIFIQUE-SE de que esta URI está configurada no Google Console: {redirect_uri}")
    
    return RedirectResponse(url=auth_url)


@router.get("/login/google/callback")
async def google_callback(request: Request):
    """Processa a resposta do Google OAuth"""
    # Construir redirect URI dinamicamente (deve ser a mesma usada na requisição inicial)
    redirect_uri = _construir_redirect_uri(request)
    
    GOOGLE_CLIENT_ID = ConfigEnvSetings.GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET = ConfigEnvSetings.GOOGLE_CLIENT_SECRET
    GOOGLE_TOKEN_URI = ConfigEnvSetings.GOOGLE_TOKEN_URI or 'https://oauth2.googleapis.com/token'
    
    code = request.query_params.get('code')
    if not code:
        logger.warning("Falha na autenticação com Google: código não recebido")
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Falha na autenticação com Google"}
        )
    
    # Trocar código por token
    
    token_data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    logger.debug(f"Trocando código por token - Redirect URI: {redirect_uri}")
    
    try:
        response = requests.post(GOOGLE_TOKEN_URI, data=token_data)
        response.raise_for_status()
        token_info = response.json()
        
        if 'access_token' not in token_info:
            logger.warning("Falha na autenticação: token não recebido")
            return templates.TemplateResponse(
                "login.html", 
                {"request": request, "error": "Falha na autenticação com Google"}
            )
        
        # Obter informações do usuário
        headers = {'Authorization': f"Bearer {token_info['access_token']}"}
        user_response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        # Verificar domínio
        domain_user = user_data['email'].split('@')[-1]
        if domain_user not in valid_domains:
            logger.warning(f"Acesso negado para domínio: {domain_user}")
            return templates.TemplateResponse(
                "login.html", 
                {"request": request, "error": "Acesso negado: domínio não autorizado"}
            )
        
        # Salvar na sessão
        request.session['user'] = {
            'email': user_data['email'],
            'name': user_data.get('name', ''),
            'picture': user_data.get('picture', '')
        }
        
        logger.info(f"Usuário Google autenticado: {user_data['email']}")
        return RedirectResponse(url="/chamado", status_code=303)
        
    except requests.RequestException as e:
        logger.error(f"Erro na autenticação Google: {str(e)}")
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Erro ao processar autenticação"}
        )


@router.get("/logout")
async def logout(request: Request):
    """Faz logout do usuário"""
    request.session.pop('user', None)
    logger.info("Logout realizado")
    return RedirectResponse(url="/login")

