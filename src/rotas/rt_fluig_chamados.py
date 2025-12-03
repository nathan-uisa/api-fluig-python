from fastapi import APIRouter, Depends, HTTPException, Path
from src.auth.auth_api import Auth_API_KEY
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificado, DetalhesChamado, AberturaChamado, AberturaChamadoEmail
from src.web.web_chamado_fluig import obter_detalhes_chamado
from src.web.web_auth_manager import obter_cookies_validos
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.fluig.fluig_core import FluigCore
from src.utilitarios_centrais.google_drive_utils import baixar_arquivo_drive

rt_fluig_chamados = APIRouter(prefix="/fluig/{ambiente}/chamados", tags=["fluig-chamados"])

def validar_ambiente(ambiente: str) -> str:
    """Valida e normaliza o ambiente"""
    ambiente_upper = ambiente.upper()
    if ambiente_upper not in ["PRD", "QLD"]:
        raise HTTPException(status_code=400, detail=f"Ambiente inválido: {ambiente}. Use 'prd' ou 'qld'")
    return ambiente_upper

def obter_colleague_id(ambiente: str) -> str:
    """Obtém o colleague ID baseado no ambiente"""
    if ambiente == "PRD":
        return ConfigEnvSetings.USER_COLLEAGUE_ID
    else:  # QLD
        return ConfigEnvSetings.USER_COLLEAGUE_ID_QLD

@rt_fluig_chamados.post("/abrir")
async def AberturaDeChamados(
    Item: AberturaChamado,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Abre um chamado sem classificação no Fluig
    Suporta anexos do Google Drive através do campo anexos_ids
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamados] Iniciando abertura de chamado - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        
        # 1. Validar e baixar anexos do Google Drive (se houver)
        arquivos_baixados = []
        if Item.anexos_ids and len(Item.anexos_ids) > 0:
            logger.info(f"[Anexos] Iniciando download de {len(Item.anexos_ids)} arquivo(s) do Google Drive")
            for file_id in Item.anexos_ids:
                try:
                    conteudo_bytes, nome_arquivo = baixar_arquivo_drive(file_id)
                    if conteudo_bytes and nome_arquivo:
                        arquivos_baixados.append({
                            'bytes': conteudo_bytes,
                            'nome': nome_arquivo,
                            'file_id': file_id
                        })
                        logger.info(f"[Anexos] Arquivo {file_id} baixado com sucesso: {nome_arquivo}")
                    else:
                        logger.warning(f"[Anexos] Falha ao baixar arquivo {file_id} - continuando sem anexo")
                except Exception as e:
                    logger.error(f"[Anexos] Erro ao processar anexo {file_id}: {str(e)} - continuando sem anexo")
        
        # 2. Abrir chamado normalmente
        fluig_core = FluigCore(ambiente=ambiente_validado)
        resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=Item)
        
        if resposta.get('sucesso'):
            dados = resposta.get('dados', {})
            process_instance_id = None

            if dados and isinstance(dados, dict):
                process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
            
            if process_instance_id:
                logger.info(f"[AberturaDeChamados] Chamado aberto com sucesso - ID: {process_instance_id}")
                
                # 3. Se houver anexos e chamado foi criado, anexar arquivos
                if arquivos_baixados and process_instance_id:
                    logger.info(f"[Anexos] Iniciando anexo de {len(arquivos_baixados)} arquivo(s) ao chamado {process_instance_id}")
                    
                    colleague_id = obter_colleague_id(ambiente_validado)
                    
                    if not colleague_id or colleague_id == "":
                        logger.error(f"[Anexos] Colleague ID não configurado para ambiente {ambiente_validado} - não será possível fazer upload/anexar arquivos")
                    else:
                        logger.info(f"[Anexos] Usando Colleague ID: {colleague_id} para upload")
                        # Para cada arquivo, faz upload e anexa ao chamado
                        for arquivo in arquivos_baixados:
                            try:
                                logger.info(f"[Anexos] Fazendo upload do arquivo: {arquivo['nome']}")
                                resultado_upload = fluig_core.upload_arquivo_fluig(
                                    arquivo_bytes=arquivo['bytes'],
                                    nome_arquivo=arquivo['nome'],
                                    colleague_id=colleague_id
                                )
                                
                                if resultado_upload:
                                    logger.info(f"[Anexos] Upload do arquivo {arquivo['nome']} realizado com sucesso")
                                    
                                    # Anexa ao chamado
                                    logger.info(f"[Anexos] Anexando arquivo {arquivo['nome']} ao chamado {process_instance_id}")
                                    sucesso_anexo = fluig_core.anexar_arquivo_chamado(
                                        process_instance_id=process_instance_id,
                                        nome_arquivo=arquivo['nome']
                                    )
                                    
                                    if sucesso_anexo:
                                        logger.info(f"[Anexos] Arquivo {arquivo['nome']} anexado ao chamado {process_instance_id}")
                                    else:
                                        logger.error(f"[Anexos] Falha ao anexar arquivo {arquivo['nome']} ao chamado {process_instance_id}")
                                else:
                                    logger.error(f"[Anexos] Falha no upload do arquivo {arquivo['nome']}")
                                    
                            except Exception as e:
                                logger.error(f"[Anexos] Erro ao processar anexo {arquivo['nome']}: {str(e)} - continuando com próximo arquivo")
                                import traceback
                                logger.debug(f"[Anexos] Traceback: {traceback.format_exc()}")
                
                return process_instance_id
            else:
                logger.error(f"[AberturaDeChamados] Chamado aberto mas processInstanceId não encontrado na resposta")
                logger.debug(f"[AberturaDeChamados] Dados recebidos: {dados}")
                raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
        else:
            logger.error(f"[AberturaDeChamados] Falha ao abrir chamado - Status: {resposta.get('status_code')}")
            raise HTTPException(
                status_code=resposta.get('status_code', 500),
                detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamados] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[AberturaDeChamados] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@rt_fluig_chamados.post("/abrir-classificado")
async def AberturaDeChamadosClassificado(
    Item: AberturaChamadoClassificado,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Abre um chamado classificado no Fluig
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamadosClassificado] Iniciando abertura de chamado classificado - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        
        fluig_core = FluigCore(ambiente=ambiente_validado)
        resposta = fluig_core.AberturaDeChamado(tipo_chamado="classificado", Item=Item)
                
        if not resposta.get('sucesso'):
            logger.error(f"[AberturaDeChamadosClassificado] Falha ao abrir chamado - Status: {resposta.get('status_code')}")
            raise HTTPException(
                status_code=resposta.get('status_code', 500),
                detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
            )
        
        # processInstanceId - Número do Chamado
        dados = resposta.get('dados', {})
        process_instance_id = None
        if dados and isinstance(dados, dict):
            process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
        

        if process_instance_id:
            logger.info(f"[AberturaDeChamadosClassificado] Chamado aberto com sucesso - ID: {process_instance_id}")
            return process_instance_id
        else:
            logger.error(f"[AberturaDeChamadosClassificado] Chamado aberto mas processInstanceId não encontrado na resposta")
            logger.debug(f"[AberturaDeChamadosClassificado] Dados recebidos: {dados}")
            raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamadosClassificado] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@rt_fluig_chamados.post("/classificar")
async def ClassificarChamado(
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Classifica um chamado no Fluig
    """
    validar_ambiente(ambiente)
    # TODO: Implementar lógica de classificação
    pass

@rt_fluig_chamados.post("/detalhes")
async def BuscarDetalhesChamado(
    Item: DetalhesChamado,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Obtém os detalhes de um chamado do Fluig
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[BuscarDetalhesChamado] Buscando detalhes do chamado {Item.process_instance_id} - Ambiente: {ambiente_validado}")
        
        # Usa FLUIG_ADMIN_USER para rotas de chamados
        if ambiente_validado == "PRD":
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
        else:  # QLD
            usuario = ConfigEnvSetings.FLUIG_USER_NAME_QLD
            senha = ConfigEnvSetings.FLUIG_USER_PASS_QLD

        cookies = obter_cookies_validos(ambiente_validado, forcar_login=False, usuario=usuario, senha=senha)
        
        if not cookies:
            logger.error("[BuscarDetalhesChamado] Falha ao obter autenticação válida")
            raise HTTPException(status_code=500, detail="Falha ao obter autenticação válida no Fluig")

        logger.info(f"[BuscarDetalhesChamado] Buscando detalhes...")
        detalhes = obter_detalhes_chamado(
            process_instance_id=Item.process_instance_id,
            ambiente=ambiente_validado,
            cookies_list=cookies,
            usuario=usuario
        )
        
        if not detalhes:
            logger.error("[BuscarDetalhesChamado] Falha ao obter detalhes do chamado")
            raise HTTPException(status_code=500, detail="Falha ao obter detalhes do chamado")
        
        logger.info(f"[BuscarDetalhesChamado] Detalhes obtidos com sucesso")
        return detalhes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BuscarDetalhesChamado] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@rt_fluig_chamados.post("/email/abrir")
async def AberturaDeChamadosEmail(
    Item: AberturaChamadoEmail,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Abre um chamado via email
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamadosEmail] Iniciando abertura de chamado via email - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        # TODO: Implementar lógica de abertura via email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamadosEmail] Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

