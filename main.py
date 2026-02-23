from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from src.utilitarios_centrais.logger import logger
from src.rotas import rt_fluig_chamados, rt_fluig_servicos, rt_fluig_datasets, rt_fluig_processos
from src.rotas.webapp import rt_login, rt_chamado
from src.web.web_auth_manager import (
    iniciar_login_automatico, 
    parar_login_automatico,
)
from src.gmail_monitor.background_service import (
    iniciar_monitoramento_gmail,
    parar_monitoramento_gmail,
)
from src.historico_monitor.background_service import (
    iniciar_monitoramento_historico,
    parar_monitoramento_historico,
)
from src.modelo_dados.modelo_settings import ConfigEnvSetings

import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("Iniciando renovação automática de cookies do Fluig (intervalo: 20 minutos)...")
    iniciar_login_automatico()
    
    # Verifica se o monitoramento de emails está habilitado
    gmail_enabled = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower()
    if gmail_enabled in ('true', '1', 'yes'):
        logger.info("Iniciando monitoramento de emails do Gmail...")
        iniciar_monitoramento_gmail()
    else:
        logger.info("Monitoramento de emails do Gmail desabilitado (GMAIL_MONITOR_ENABLED=false)")
    
    # Inicia monitoramento de histórico de chamados
    historico_enabled = getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower()
    if historico_enabled in ('true', '1', 'yes'):
        logger.info("Iniciando monitoramento de histórico de chamados...")
        iniciar_monitoramento_historico()
    else:
        logger.info("Monitoramento de histórico de chamados desabilitado (HISTORICO_MONITOR_ENABLED=false)")
    
    # Verifica se Google Drive está configurado (obrigatório agora)
    drive_sync_enabled = getattr(ConfigEnvSetings, 'DRIVE_SYNC_ENABLED', 'false').lower()
    if drive_sync_enabled in ('true', '1', 'yes'):
        logger.info("Sistema configurado para usar apenas Google Drive para configurações")
        try:
            from src.configs.drive_config_manager import get_drive_config_manager
            drive_manager = get_drive_config_manager()
            if drive_manager:
                logger.info("Google Drive disponível - configurações serão lidas/escritas apenas no Drive")
            else:
                logger.warning("Google Drive não disponível - sistema pode não funcionar corretamente")
        except Exception as e:
            logger.warning(f"Erro ao verificar Google Drive: {str(e)}")
    else:
        logger.warning("DRIVE_SYNC_ENABLED=false - Sistema requer Google Drive habilitado para funcionar")
    
    yield
    
    # Shutdown
    # Verifica se o monitoramento de emails está habilitado antes de parar
    gmail_enabled = getattr(ConfigEnvSetings, 'GMAIL_MONITOR_ENABLED', 'true').lower()
    if gmail_enabled in ('true', '1', 'yes'):
        logger.info("Parando monitoramento de emails...")
        parar_monitoramento_gmail()
    else:
        logger.info("Monitoramento de emails já estava desabilitado")
    
    # Para monitoramento de histórico de chamados
    historico_enabled = getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower()
    if historico_enabled in ('true', '1', 'yes'):
        logger.info("Parando monitoramento de histórico de chamados...")
        parar_monitoramento_historico()
    else:
        logger.info("Monitoramento de histórico de chamados já estava desabilitado")
    
    logger.info("Parando renovação automática de cookies...")
    parar_login_automatico()


app = FastAPI(
    title="API Fluig", 
    version="2.0.0", 
    description="API REST para integração com Fluig",
    lifespan=lifespan
)
app.add_middleware(SessionMiddleware, secret_key="CV7uYNpRr2tciYu2s4IEWaikuIAw")
app.mount("/static", StaticFiles(directory="src/site/static"), name="static")


app.include_router(rt_fluig_chamados.rt_fluig_chamados, prefix="/api/v1")
app.include_router(rt_fluig_servicos.rt_fluig_servicos, prefix="/api/v1")
app.include_router(rt_fluig_datasets.rt_fluig_datasets, prefix="/api/v1")
app.include_router(rt_fluig_processos.rt_fluig_processos)
app.include_router(rt_login.router)
app.include_router(rt_chamado.router)


@app.get("/")
async def root(request: Request):
    """Página inicial - redireciona para login do webapp"""
    logger.info(f"Requisição recebida na rota raiz - IP: {request.client.host if request.client else 'N/A'}")
    return RedirectResponse(url="/login")


if __name__ == "__main__":
    logger.info("Iniciando servidor Uvicorn na porta 3000")
    print("-"*60)
    uvicorn.run(
        "main:app",
        host="localhost",
        port=3000,
        reload=True,
        log_level="info"
    )
