from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from src.utilitarios_centrais.logger import logger
from src.rotas import rt_fluig_chamados, rt_fluig_servicos, rt_fluig_datasets, rt_terceiro
from src.rotas.webapp import rt_login, rt_chamado

import uvicorn

app = FastAPI(title="API Fluig", version="2.0.0", description="API REST para integração com Fluig - Padronizada para Sensedia")

# Configurar sessões para o webapp
app.add_middleware(SessionMiddleware, secret_key="sua-chave-secreta-aqui-altere-em-producao")

# Montar arquivos estáticos e templates do webapp
app.mount("/static", StaticFiles(directory="src/site/static"), name="static")

# Registra rotas padronizadas com prefixo /api/v1
app.include_router(rt_fluig_chamados.rt_fluig_chamados, prefix="/api/v1")
app.include_router(rt_fluig_servicos.rt_fluig_servicos, prefix="/api/v1")
app.include_router(rt_fluig_datasets.rt_fluig_datasets, prefix="/api/v1")
app.include_router(rt_terceiro.rt_terceiro, prefix="/api/v1")

# Registra rotas do webapp (sem prefixo para manter compatibilidade)
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
        host="127.0.0.1",
        port=3000,
        reload=True,
        log_level="info"
    )
