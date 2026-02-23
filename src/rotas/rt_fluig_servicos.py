"""Rotas para serviços do Fluig"""
from fastapi import APIRouter, Depends, HTTPException, Path
from src.auth.auth_api import Auth_API_KEY
from src.web.web_servicos_fluig import obter_servicos_fluig, obter_detalhes_servico_fluig
from src.web.web_auth_manager import obter_cookies_validos
from src.utilitarios_centrais.logger import logger
from src.utilitarios_centrais.json_utils import salvar_servicos_json, salvar_detalhes_servico_json
from src.modelo_dados.modelos_fluig import DetalhesServicos
from src.modelo_dados.modelo_settings import ConfigEnvSetings

rt_fluig_servicos = APIRouter(prefix="/fluig/{ambiente}/servicos", tags=["fluig-servicos"])

def validar_ambiente(ambiente: str) -> str:
    """Valida e normaliza o ambiente"""
    ambiente_upper = ambiente.upper()
    if ambiente_upper not in ["PRD", "QLD"]:
        raise HTTPException(status_code=400, detail=f"Ambiente inválido: {ambiente}. Use 'prd' ou 'qld'")
    return ambiente_upper

@rt_fluig_servicos.get("")
async def ObterListaServicos(
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    limit: int = 300,
    offset: int = 0,
    orderby: str = "servico_ASC",
    forcar_login: bool = False,
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Obtém a lista completa de serviços disponíveis no Fluig
    
    Este endpoint retorna todos os serviços configurados no sistema Fluig, incluindo
    informações como ID, nome, descrição e outras propriedades relevantes.
    
    **Funcionalidades:**
    - Lista todos os serviços do catálogo de serviços do Fluig
    - Suporta paginação através de limit e offset
    - Permite ordenação personalizada dos resultados
    
    **Parâmetros de paginação:**
    - limit: Quantidade máxima de serviços a retornar (padrão: 300)
    - offset: Número de registros a pular (padrão: 0)
    - orderby: Campo e direção de ordenação (padrão: "servico_ASC")
    
    **Retorno:**
    - Lista de objetos contendo informações de cada serviço
    - Dados salvos automaticamente em arquivo JSON no sistema
    
    Args:
        ambiente: Ambiente do Fluig onde os serviços estão localizados (prd ou qld)
        limit: Quantidade máxima de serviços a retornar (padrão: 300)
        offset: Número de registros a pular para paginação (padrão: 0)
        orderby: Campo e direção de ordenação, formato: "campo_DIRECAO" (padrão: "servico_ASC")
        forcar_login: Força novo login mesmo com cookies válidos (padrão: False)
    
    Returns:
        list: Lista de objetos contendo informações dos serviços do Fluig
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[ObterListaServicos] Iniciando busca de serviços - Ambiente: {ambiente_validado}")

        usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
        senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
        cookies = obter_cookies_validos(ambiente_validado, forcar_login, usuario, senha)
        if not cookies:
            logger.error("[ObterListaServicos] Falha ao obter autenticação válida")
            raise HTTPException(status_code=500, detail="Falha ao obter autenticação válida no Fluig")
        logger.info(f"[ObterListaServicos] Buscando serviços...")
        servicos = obter_servicos_fluig(ambiente_validado, limit, offset, orderby, cookies_list=cookies)
        
        if not servicos:
            logger.error("[ObterListaServicos] Falha ao obter serviços")
            raise HTTPException(status_code=500, detail="Falha ao obter lista de serviços")
        logger.info(f"[ObterListaServicos] Salvando serviços em JSON...")
        arquivo_salvo = salvar_servicos_json(servicos, ambiente_validado)
        
        logger.info(f"[ObterListaServicos] Serviços obtidos e salvos com sucesso - Arquivo: {arquivo_salvo}")
        return servicos
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ObterListaServicos] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@rt_fluig_servicos.post("/detalhes")
async def ObterDetalhesServico(
    Item: DetalhesServicos,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Obtém os detalhes completos de um serviço específico do Fluig
    
    Este endpoint retorna informações detalhadas sobre um serviço específico,
    incluindo categorias, subcategorias, campos personalizados, configurações
    e outras propriedades relevantes.
    
    **Funcionalidades:**
    - Busca detalhes completos de um serviço pelo ID
    - Retorna estrutura completa com categorias e subcategorias
    - Inclui configurações e campos personalizados do serviço
    
    **Retorno:**
    - Objeto contendo todas as informações detalhadas do serviço
    - Dados salvos automaticamente em arquivo JSON no sistema
    
    Args:
        Item: Objeto contendo:
            - id_servico: ID único do serviço no Fluig
        ambiente: Ambiente do Fluig onde o serviço está localizado (prd ou qld)
    
    Returns:
        dict: Objeto contendo todas as informações detalhadas do serviço solicitado
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[ObterDetalhesServico] Buscando detalhes do serviço {Item.id_servico} - Ambiente: {ambiente_validado}")

        usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
        senha = ConfigEnvSetings.FLUIG_ADMIN_PASS

        logger.info(f"[ObterDetalhesServico] Buscando detalhes usando OAuth 1.0...")
        detalhes = obter_detalhes_servico_fluig(
            document_id=Item.id_servico,
            ambiente=ambiente_validado
        )
        
        if not detalhes:
            logger.error("[ObterDetalhesServico] Falha ao obter detalhes do serviço")
            raise HTTPException(status_code=500, detail="Falha ao obter detalhes do serviço")
        logger.info(f"[ObterDetalhesServico] Salvando detalhes em JSON...")
        arquivo_salvo = salvar_detalhes_servico_json(detalhes, Item.id_servico, ambiente_validado)
        
        logger.info(f"[ObterDetalhesServico] Detalhes obtidos e salvos com sucesso - Arquivo: {arquivo_salvo}")
        return detalhes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ObterDetalhesServico] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

