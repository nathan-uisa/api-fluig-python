from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rotas import rt_abertura_de_chamado
import uvicorn
#from utils.logger import logger
app = FastAPI(title="FastAPI Auth App", version="1.0.0")

app.include_router(rt_abertura_de_chamado.router)


@app.get("/")
async def root(request: Request):
    return ("☺☻")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=9080,
        reload=True,
        log_level="info"
    )

