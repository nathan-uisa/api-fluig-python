

# A Rota para Terceiros (MOVIT) está descontinuada, mas será mantida porque vai saber.

from fastapi import APIRouter, Depends, HTTPException, Path
from src.auth.auth_api import Auth_API_KEY
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificadoMovit
from src.utilitarios_centrais.logger import logger
from src.terceiro.movit_core import MovitCore


rt_terceiro = APIRouter(prefix="/terceiros/{provider}", tags=["terceiros"])

def validar_provider(provider: str) -> str:
    """Valida o provider"""
    provider_lower = provider.lower()
    if provider_lower not in ["movit"]:
        raise HTTPException(status_code=400, detail=f"Provider inválido: {provider}. Use 'movit'")
    return provider_lower


@rt_terceiro.post("/chamados/abrir-classificado")
async def AberturaDeChamadosMovit(
    Item: AberturaChamadoClassificadoMovit,
    provider: str = Path(..., description="Provider terceiro (movit)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Abre um chamado classificado no Fluig para terceiros
    
    Esta rota sempre utiliza o fake user (secops-soc@movti.com.br) para montar o payload.
    """
    provider_validado = validar_provider(provider)
    try:
        logger.info(f"[AberturaDeChamadosMovit] Iniciando abertura de chamado {provider_validado} - Título: {Item.titulo}")
        
        if provider_validado == "movit":
            movit_core = MovitCore(ambiente="PRD")
            resposta = movit_core.AberturaDeChamado(tipo_chamado="classificado", Item=Item)
        else:
            raise HTTPException(status_code=400, detail=f"Provider {provider_validado} não implementado")
        
        if not resposta.get('sucesso'):
            logger.error(f"[AberturaDeChamadosMovit] Falha ao abrir chamado - Status: {resposta.get('status_code')}")
            raise HTTPException(
                status_code=resposta.get('status_code', 500),
                detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
            )
        dados = resposta.get('dados', {})
        process_instance_id = None
        
        if dados and isinstance(dados, dict):
            process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
        
        if process_instance_id:
            logger.info(f"[AberturaDeChamadosMovit] Chamado aberto com sucesso - ID: {process_instance_id}")
            return process_instance_id
        else:
            logger.error(f"[AberturaDeChamadosMovit] Chamado aberto mas processInstanceId não encontrado na resposta")
            logger.debug(f"[AberturaDeChamadosMovit] Dados recebidos: {dados}")
            raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamadosMovit] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")