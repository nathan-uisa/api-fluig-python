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
    """
    # Obter a URL base da requisição
    url = request.url
    scheme = url.scheme
    hostname = url.hostname
    
    # Construir a URL base (com porta se necessário)
    if url.port and ((scheme == "http" and url.port != 80) or (scheme == "https" and url.port != 443)):
        base_url = f"{scheme}://{hostname}:{url.port}"
    else:
        base_url = f"{scheme}://{hostname}"
    
    # Construir a URI de callback completa
    redirect_uri = f"{base_url}/login/google/callback"
    
    logger.debug(f"Redirect URI construída: {redirect_uri}")
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
    logger.info(f"Iniciando autenticação Google - Redirect URI: {redirect_uri}")
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

