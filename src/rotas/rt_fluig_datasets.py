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
    Consulta dados de um dataset específico no Fluig
    
    Este endpoint permite buscar e recuperar informações armazenadas em datasets
    do Fluig.
    
    **Funcionalidades:**
    - Consulta de dados de qualquer dataset configurado no Fluig
    - Filtragem por usuário específico quando aplicável
    - Retorno estruturado dos dados do dataset
    
    Args:
        Item: Objeto contendo:
            - dataset_id: Identificador único do dataset no Fluig
            - user: Usuário para filtrar os dados (quando aplicável)
        ambiente: Ambiente do Fluig onde o dataset está localizado (prd ou qld)
    
    Returns:
        dict: Dados do dataset consultado, estruturados conforme a configuração do dataset
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

