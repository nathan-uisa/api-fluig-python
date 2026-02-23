from fastapi import APIRouter, Depends, HTTPException, Path
from src.auth.auth_api import Auth_API_KEY
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificado, DetalhesChamado, AberturaChamado, AberturaChamadoEmail
from src.web.web_auth_manager import obter_cookies_validos
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.fluig.fluig_core import FluigCore
from src.historico_monitor.historico_manager import HistoricoManager
import base64

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
    Abre um novo chamado no Fluig sem classificação prévia
    
    Este endpoint cria um chamado de suporte no sistema Fluig com os dados fornecidos.
    O chamado será criado sem classificação inicial e poderá ser classificado posteriormente.
    
    **Funcionalidades:**
    - Criação de chamado com título, descrição, usuário e telefone
    - Suporte para anexar múltiplos arquivos em formato base64
    - Processamento automático de anexos após criação do chamado
    
    **Anexos:**
    - Os arquivos devem ser enviados no campo 'anexos' como array de objetos
    - Cada anexo deve conter 'nome' (nome do arquivo) e 'conteudo_base64' (conteúdo em base64)
    - Os anexos são processados automaticamente após a criação do chamado
    
    **Retorno:**
    - Retorna o número do chamado (processInstanceId) em caso de sucesso
    
    Args:
        Item: Objeto contendo os dados do chamado (título, descrição, usuário, telefone, anexos)
        ambiente: Ambiente do Fluig onde o chamado será criado (prd ou qld)
    
    Returns:
        int: Número do chamado criado (processInstanceId)
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamados] Iniciando abertura de chamado - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        
        # 1. Processar anexos diretos (base64)
        arquivos_processados = []
        
        if Item.anexos and len(Item.anexos) > 0:
            logger.info(f"[Anexos] Processando {len(Item.anexos)} anexo(s) em base64")
            for anexo in Item.anexos:
                try:
                    # Decodifica base64
                    conteudo_bytes = base64.b64decode(anexo.conteudo_base64)
                    arquivos_processados.append({
                            'bytes': conteudo_bytes,
                        'nome': anexo.nome
                        })
                    logger.info(f"[Anexos] Anexo {anexo.nome} processado com sucesso ({len(conteudo_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"[Anexos] Erro ao processar anexo {anexo.nome}: {str(e)} - continuando sem anexo")
        
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
                if arquivos_processados and process_instance_id:
                    logger.info(f"[Anexos] Iniciando anexo de {len(arquivos_processados)} arquivo(s) ao chamado {process_instance_id}")
                    
                    colleague_id = obter_colleague_id(ambiente_validado)
                    
                    if not colleague_id or colleague_id == "":
                        logger.error(f"[Anexos] Colleague ID não configurado para ambiente {ambiente_validado} - não será possível fazer upload/anexar arquivos")
                    else:
                        logger.info(f"[Anexos] Usando Colleague ID: {colleague_id} para upload")
                        # Para cada arquivo, faz upload e anexa ao chamado
                        for arquivo in arquivos_processados:
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
    Abre um novo chamado classificado no Fluig
    
    Este endpoint cria um chamado de suporte no sistema Fluig já com classificação prévia.
    O chamado será criado diretamente com serviço, categoria e subcategoria definidos.
    
    **Funcionalidades:**
    - Criação de chamado classificado com serviço, categoria e subcategoria
    - Suporte para anexar múltiplos arquivos em formato base64
    - Processamento automático de anexos após criação do chamado
    - Possibilidade de definir usuário responsável (targetAssignee)
    
    **Anexos:**
    - Os arquivos devem ser enviados no campo 'anexos' como array de objetos
    - Cada anexo deve conter 'nome' (nome do arquivo) e 'conteudo_base64' (conteúdo em base64)
    - Os anexos são processados automaticamente após a criação do chamado
    
    **Retorno:**
    - Retorna o número do chamado (processInstanceId) em caso de sucesso
    
    Args:
        Item: Objeto contendo os dados do chamado classificado (serviço, categoria, subcategoria, usuário, anexos, etc.)
        ambiente: Ambiente do Fluig onde o chamado será criado (prd ou qld)
    
    Returns:
        int: Número do chamado criado (processInstanceId)
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamadosClassificado] Iniciando abertura de chamado classificado - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        
        # 1. Processar anexos diretos (base64)
        arquivos_processados = []
        
        if Item.anexos and len(Item.anexos) > 0:
            logger.info(f"[Anexos] Processando {len(Item.anexos)} anexo(s) em base64")
            for anexo in Item.anexos:
                try:
                    # Decodifica base64
                    conteudo_bytes = base64.b64decode(anexo.conteudo_base64)
                    arquivos_processados.append({
                        'bytes': conteudo_bytes,
                        'nome': anexo.nome
                    })
                    logger.info(f"[Anexos] Anexo {anexo.nome} processado com sucesso ({len(conteudo_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"[Anexos] Erro ao processar anexo {anexo.nome}: {str(e)} - continuando sem anexo")
        
        # 2. Abrir chamado classificado
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
            
            # 3. Se houver anexos e chamado foi criado, anexar arquivos
            if arquivos_processados and process_instance_id:
                logger.info(f"[Anexos] Iniciando anexo de {len(arquivos_processados)} arquivo(s) ao chamado {process_instance_id}")
                
                colleague_id = obter_colleague_id(ambiente_validado)
                
                if not colleague_id or colleague_id == "":
                    logger.error(f"[Anexos] Colleague ID não configurado para ambiente {ambiente_validado} - não será possível fazer upload/anexar arquivos")
                else:
                    logger.info(f"[Anexos] Usando Colleague ID: {colleague_id} para upload")
                    # Para cada arquivo, faz upload e anexa ao chamado
                    for arquivo in arquivos_processados:
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
            logger.error(f"[AberturaDeChamadosClassificado] Chamado aberto mas processInstanceId não encontrado na resposta")
            logger.debug(f"[AberturaDeChamadosClassificado] Dados recebidos: {dados}")
            raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamadosClassificado] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[AberturaDeChamadosClassificado] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

@rt_fluig_chamados.post("/classificar")
async def ClassificarChamado(
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Classifica um chamado existente no Fluig
    
    Este endpoint permite classificar um chamado que foi aberto sem classificação inicial,
    atribuindo serviço, categoria e subcategoria ao chamado.
    
    **Status:**
    - Endpoint em desenvolvimento (TODO)
    
    Args:
        ambiente: Ambiente do Fluig onde o chamado está localizado (prd ou qld)
    
    Returns:
        dict: Resultado da classificação do chamado
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
    Busca e retorna os detalhes completos de um chamado específico no Fluig
    
    Este endpoint recupera todas as informações de um chamado existente, incluindo:
    - Dados básicos do chamado (título, descrição, status, etc.)
    - Informações do solicitante
    - Histórico de movimentações
    - Anexos vinculados
    - Classificação (se aplicável)
    
    **Uso:**
    - Útil para consultar o status e detalhes de um chamado específico
    - Permite acompanhar o andamento de chamados abertos
    
    Args:
        Item: Objeto contendo o número do chamado (process_instance_id)
        ambiente: Ambiente do Fluig onde o chamado está localizado (prd ou qld)
    
    Returns:
        dict: Dicionário contendo todos os detalhes do chamado solicitado
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[BuscarDetalhesChamado] Buscando detalhes do chamado {Item.process_instance_id} - Ambiente: {ambiente_validado}")
        
        # Usa FLUIG_ADMIN_USER para rotas de chamados
        if ambiente_validado == "PRD":
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
        else:  # QLD
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS

        cookies = obter_cookies_validos(ambiente_validado, forcar_login=False, usuario=usuario, senha=senha)
        
        if not cookies:
            logger.error("[BuscarDetalhesChamado] Falha ao obter autenticação válida")
            raise HTTPException(status_code=500, detail="Falha ao obter autenticação válida no Fluig")

        logger.info(f"[BuscarDetalhesChamado] Buscando detalhes...")
        fluig_core = FluigCore(ambiente=ambiente_validado)
        detalhes = fluig_core.obter_detalhes_chamado(
            process_instance_id=Item.process_instance_id,
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
    Abre um novo chamado no Fluig através de requisição simulando email
    
    Este endpoint cria um chamado de suporte no sistema Fluig a partir de dados que
    simulam o recebimento de um email. Útil para integração com sistemas de email
    ou processamento automatizado de mensagens.
    
    **Funcionalidades:**
    - Criação de chamado sem classificação prévia
    - Suporte para anexar múltiplos arquivos em formato base64
    - Processamento automático de anexos após criação do chamado
    - Estrutura simplificada para integração com sistemas de email
    
    **Anexos:**
    - Os arquivos devem ser enviados no campo 'anexos' como array de objetos
    - Cada anexo deve conter 'nome' (nome do arquivo) e 'conteudo_base64' (conteúdo em base64)
    - Os anexos são processados automaticamente após a criação do chamado
    
    **Retorno:**
    - Retorna o número do chamado (processInstanceId) em caso de sucesso
    
    Args:
        Item: Objeto contendo os dados do chamado (título, descrição, usuário, telefone, anexos)
        ambiente: Ambiente do Fluig onde o chamado será criado (prd ou qld)
    
    Returns:
        int: Número do chamado criado (processInstanceId)
    """
    ambiente_validado = validar_ambiente(ambiente)
    try:
        logger.info(f"[AberturaDeChamadosEmail] Iniciando abertura de chamado via email - Usuário: {Item.usuario} - Ambiente: {ambiente_validado}")
        
        # 1. Processar anexos diretos (base64)
        arquivos_processados = []
        
        if Item.anexos and len(Item.anexos) > 0:
            logger.info(f"[Anexos] Processando {len(Item.anexos)} anexo(s) em base64")
            for anexo in Item.anexos:
                try:
                    # Decodifica base64
                    conteudo_bytes = base64.b64decode(anexo.conteudo_base64)
                    arquivos_processados.append({
                        'bytes': conteudo_bytes,
                        'nome': anexo.nome
                    })
                    logger.info(f"[Anexos] Anexo {anexo.nome} processado com sucesso ({len(conteudo_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"[Anexos] Erro ao processar anexo {anexo.nome}: {str(e)} - continuando sem anexo")
        
        # 2. Abrir chamado normalmente (usa AberturaChamado internamente)
        item_chamado = AberturaChamado(
            titulo=Item.titulo,
            descricao=Item.descricao,
            usuario=Item.usuario,
            telefone=Item.telefone,
            anexos=Item.anexos
        )
        
        fluig_core = FluigCore(ambiente=ambiente_validado)
        resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=item_chamado)
        
        if resposta.get('sucesso'):
            dados = resposta.get('dados', {})
            process_instance_id = None

            if dados and isinstance(dados, dict):
                process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
            
            if process_instance_id:
                logger.info(f"[AberturaDeChamadosEmail] Chamado aberto com sucesso - ID: {process_instance_id}")
                
                # 3. Salva histórico inicial do chamado (chamados abertos via email são monitorados)
                try:
                    logger.info(f"[AberturaDeChamadosEmail] Salvando histórico inicial do chamado {process_instance_id}...")
                    historico_manager = HistoricoManager()
                    
                    # Obtém histórico inicial do Fluig
                    historico_inicial = fluig_core.obter_historico_chamado(process_instance_id)
                    
                    if historico_inicial:
                        sucesso_salvamento = historico_manager.salvar_historico(
                            process_instance_id=process_instance_id,
                            historico_data=historico_inicial,
                            ambiente=ambiente_validado,
                            email_remetente=Item.usuario
                        )
                        if sucesso_salvamento:
                            logger.info(f"[AberturaDeChamadosEmail] Histórico inicial do chamado {process_instance_id} salvo com sucesso")
                        else:
                            logger.warning(f"[AberturaDeChamadosEmail] Falha ao salvar histórico inicial do chamado {process_instance_id}")
                    else:
                        logger.warning(f"[AberturaDeChamadosEmail] Não foi possível obter histórico inicial do chamado {process_instance_id}")
                except Exception as e:
                    # Não falha a abertura do chamado se houver erro ao salvar histórico
                    logger.error(f"[AberturaDeChamadosEmail] Erro ao salvar histórico inicial do chamado {process_instance_id}: {str(e)}")
                    import traceback
                    logger.debug(f"[AberturaDeChamadosEmail] Traceback: {traceback.format_exc()}")
                
                # 4. Se houver anexos e chamado foi criado, anexar arquivos
                if arquivos_processados and process_instance_id:
                    logger.info(f"[Anexos] Iniciando anexo de {len(arquivos_processados)} arquivo(s) ao chamado {process_instance_id}")
                    
                    colleague_id = obter_colleague_id(ambiente_validado)
                    
                    if not colleague_id or colleague_id == "":
                        logger.error(f"[Anexos] Colleague ID não configurado para ambiente {ambiente_validado} - não será possível fazer upload/anexar arquivos")
                    else:
                        logger.info(f"[Anexos] Usando Colleague ID: {colleague_id} para upload")
                        # Para cada arquivo, faz upload e anexa ao chamado
                        for arquivo in arquivos_processados:
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
                logger.error(f"[AberturaDeChamadosEmail] Chamado aberto mas processInstanceId não encontrado na resposta")
                logger.debug(f"[AberturaDeChamadosEmail] Dados recebidos: {dados}")
                raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
        else:
            logger.error(f"[AberturaDeChamadosEmail] Falha ao abrir chamado - Status: {resposta.get('status_code')}")
            raise HTTPException(
                status_code=resposta.get('status_code', 500),
                detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AberturaDeChamadosEmail] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[AberturaDeChamadosEmail] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar requisição: {str(e)}")

