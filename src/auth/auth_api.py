from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger

API_KEY_NAME = ConfigEnvSetings.API_NAME
API_KEY = ConfigEnvSetings.API_KEY

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def Auth_API_KEY(api_key: str = Security(api_key_header)):
    logger.debug(f"Auth_API_KEY: Verificando autenticação - Header: {API_KEY_NAME}")
    
    if not API_KEY:
        logger.error("Auth_API_KEY: API Key não configurada no servidor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key não configurada no servidor"
        )
    
    if not api_key:
        logger.warning(f"Auth_API_KEY: API Key não fornecida no header {API_KEY_NAME}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key não fornecida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != API_KEY:
        logger.warning(f"Auth_API_KEY: Tentativa de acesso com API Key inválida")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    logger.debug("Auth_API_KEY: Autenticação bem-sucedida")
    return api_key

