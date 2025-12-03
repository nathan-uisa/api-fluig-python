from fastapi import APIRouter, Depends, HTTPException, Path
from src.auth.auth_api import Auth_API_KEY
from src.modelo_dados.modelos_fluig import Datasets
from src.utilitarios_centrais.logger import logger
from src.fluig.fluig_core import FluigCore

rt_fluig_datasets = APIRouter(prefix="/fluig/{ambiente}/datasets", tags=["fluig-datasets"])

def validar_ambiente(ambiente: str) -> str:
    """Valida e normaliza o ambiente"""
    ambiente_upper = ambiente.upper()
    if ambiente_upper not in ["PRD", "QLD"]:
        raise HTTPException(status_code=400, detail=f"Ambiente inválido: {ambiente}. Use 'prd' ou 'qld'")
    return ambiente_upper

@rt_fluig_datasets.post("/buscar")
async def BuscarDataset(
    Item: Datasets,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Busca dados em um dataset do Fluig
    
    Args:
        Item: Objeto Datasets contendo dataset_id e user
        ambiente: Ambiente do Fluig (prd ou qld)
    
    Returns:
        Dados do dataset encontrados
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[BuscarDataset] Iniciando busca - Dataset: {Item.dataset_id}, User: {Item.user}, Ambiente: {ambiente_validado}")
        
        fluig_core = FluigCore(ambiente=ambiente_validado)
        resultado = fluig_core.Dataset_config(dataset_id=Item.dataset_id, user=Item.user)
        
        logger.info(f"[BuscarDataset] Busca concluída com sucesso")
        return resultado
        
    except ValueError as e:
        logger.error(f"[BuscarDataset] Erro de validação: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[BuscarDataset] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

