from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from src.utilitarios_centrais.logger import logger
from src.rotas import rt_fluig_chamados, rt_fluig_servicos, rt_fluig_datasets, rt_terceiro
from src.rotas.webapp import rt_login, rt_chamado
from src.web.web_auth_manager import (
    iniciar_renovacao_automatica, 
    parar_renovacao_automatica,
    obter_status_sessoes
)

import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info("Iniciando renovação automática de cookies do Fluig...")
    iniciar_renovacao_automatica()
    yield
    # Shutdown
    logger.info("Parando renovação automática de cookies...")
    parar_renovacao_automatica()
    
    # Fechar todos os navegadores abertos ao encerrar a aplicação
    logger.info("Fechando navegadores abertos...")
    from src.web.web_driver_manager import fechar_todos_drivers
    fechar_todos_drivers()


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
app.include_router(rt_terceiro.rt_terceiro, prefix="/api/v1")
app.include_router(rt_login.router)
app.include_router(rt_chamado.router)


@app.get("/")
async def root(request: Request):
    """Página inicial - redireciona para login do webapp"""
    logger.info(f"Requisição recebida na rota raiz - IP: {request.client.host if request.client else 'N/A'}")
    return RedirectResponse(url="/login")


@app.get("/api/v1/sessoes/status")
async def status_sessoes():
    """Retorna o status das sessões ativas e da renovação automática"""
    return obter_status_sessoes()

if __name__ == "__main__":
    logger.info("Iniciando servidor Uvicorn na porta 3000")
    print("-"*60)
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=3000,
        reload=True,
        log_level="info"
    )
