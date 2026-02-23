"""
Rotas para processos genéricos do Fluig
Permite iniciar qualquer processo/formulário do Fluig com payload genérico
"""
from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, File, Form, Request, Header
from src.auth.auth_api import Auth_API_KEY
from src.fluig.fluig_core import FluigCore
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelos_fluig import AnexoBase64
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from pydantic import BaseModel, field_validator, model_validator
from typing import Dict, Any, List, Optional, Union
import base64

rt_fluig_processos = APIRouter(prefix="/api/v1/fluig/{ambiente}/processos", tags=["fluig-processos"])

def validar_ambiente(ambiente: str) -> str:
    """Valida e normaliza o ambiente"""
    ambiente_upper = ambiente.upper()
    if ambiente_upper not in ["PRD", "QLD"]:
        raise HTTPException(status_code=400, detail=f"Ambiente inválido: {ambiente}. Use 'prd' ou 'qld'")
    return ambiente_upper

class ProcessoRequest(BaseModel):
    """Modelo para requisição de início de processo genérico
    
    Aceita dois formatos:
    1. Com wrapper: {"payload": {...}}
    2. Direto: {...} (todo o body é o payload)
    """
    payload: Dict[str, Any]
    
    @model_validator(mode='before')
    @classmethod
    def validate_payload(cls, data):
        """Aceita payload diretamente ou dentro de um objeto 'payload'"""
        if isinstance(data, dict):
            # Se tem campo "payload", usa ele
            if "payload" in data:
                return data
            # Se não tem, assume que todo o dict é o payload
            else:
                return {"payload": data}
        return data
    
    class Config:
        json_schema_extra = {
            "example": {
                "targetState": "0",
                "subProcessTargetState": "0",
                "targetAssignee": "566a4fc82d69...",
                "formFields": {
                    "ds_titulo": "Exemplo",
                    "ds_chamado": "Descrição do exemplo"
                }
            }
        }

@rt_fluig_processos.post("/iniciar")
async def iniciar_processo_fluig(
    dados: ProcessoRequest,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    process_id: str = Header(..., alias="X-Process-Id", description="ID ou nome do processo no Fluig (ex: 'Abertura de Chamados')"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Inicia um processo genérico no Fluig
    
    Este endpoint permite iniciar qualquer processo ou formulário configurado no Fluig,
    utilizando um payload genérico e flexível.
    
    **Funcionalidades:**
    - Inicia qualquer processo/formulário do Fluig
    - Aceita payload customizado conforme a estrutura do processo
    - Retorna o número da instância do processo criado (processInstanceId)
    - Suporta todos os campos e configurações do processo
    
    **Payload:**
    - O payload deve seguir a estrutura esperada pelo processo específico
    - Inclui informações como versão, modo de gerenciamento, usuário da tarefa, etc.
    - Campos específicos do processo devem ser incluídos conforme a configuração
    
    Args:
        dados: Objeto contendo:
            - payload: Dicionário com todos os dados necessários para iniciar o processo
        ambiente: Ambiente do Fluig onde o processo será iniciado (prd ou qld)
        process_id: ID ou nome do processo (fornecido via header X-Process-Id)
    
    Returns:
        dict: Resposta contendo:
            - sucesso: Indica se o processo foi iniciado com sucesso
            - process_id: ID do processo iniciado
            - process_instance_id: Número da instância do processo criado
    """
    ambiente_validado = validar_ambiente(ambiente)
    
    try:
        logger.info(f"[iniciar_processo_fluig] Iniciando processo - ProcessId: {process_id}, Ambiente: {ambiente_validado}")
        
        # Valida process_id
        if not process_id or not process_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Header X-Process-Id é obrigatório e não pode estar vazio"
            )
        
        # Valida payload
        if not dados.payload:
            raise HTTPException(
                status_code=400,
                detail="payload é obrigatório e não pode estar vazio"
            )
        
        # Inicializa FluigCore
        fluig = FluigCore(ambiente=ambiente_validado)
        
        # Inicia o processo
        resultado = fluig.IniciarProcesso(
            process_id=process_id,
            payload=dados.payload
        )
        
        if resultado["sucesso"]:
            logger.info(f"[iniciar_processo_fluig] Processo iniciado com sucesso - ProcessInstanceId: {resultado.get('process_instance_id')}")
            return {
                "sucesso": True,
                "process_id": process_id,
                "process_instance_id": resultado.get("process_instance_id")
            }
        else:
            logger.error(f"[iniciar_processo_fluig] Erro ao iniciar processo - Status: {resultado['status_code']}")
            logger.error(f"[iniciar_processo_fluig] Resposta: {resultado.get('texto', resultado.get('dados'))}")
            raise HTTPException(
                status_code=resultado["status_code"],
                detail={
                    "erro": "Erro ao iniciar processo no Fluig",
                    "dados": resultado.get("dados"),
                    "texto": resultado.get("texto", "")
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[iniciar_processo_fluig] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[iniciar_processo_fluig] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar requisição: {str(e)}"
        )

class UploadArquivoRequest(BaseModel):
    """Modelo para requisição de upload de arquivo"""
    arquivos: List[AnexoBase64]
    colleague_id: str | None = None  # Opcional, usa padrão se não informado
    
    class Config:
        json_schema_extra = {
            "example": {
                "arquivos": [
                    {
                        "nome": "documento.pdf",
                        "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
                    }
                ],
                "colleague_id": "12345"
            }
        }

@rt_fluig_processos.post("/upload")
async def upload_arquivo_fluig(
    dados: UploadArquivoRequest,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Faz upload de arquivo(s) no ECM do Fluig sem criar processo
    
    Este endpoint permite fazer upload de arquivos diretamente no repositório ECM (Enterprise
    Content Management) do Fluig, sem necessidade de criar ou anexar a um processo existente.
    
    **Retorno:**
    - Retorna resumo com total de arquivos, sucessos e erros
    - Detalhes de cada arquivo processado (sucesso ou erro)
    
    Args:
        dados: Objeto contendo:
            - arquivos: Lista de objetos com 'nome' e 'conteudo_base64'
            - colleague_id: ID do colaborador (opcional, usa padrão do ambiente se não informado)
        ambiente: Ambiente do Fluig onde os arquivos serão armazenados (prd ou qld)
    
    Returns:
        dict: Resposta contendo:
            - sucesso: Indica se todos os arquivos foram enviados com sucesso
            - total_arquivos: Total de arquivos processados
            - arquivos_enviados: Quantidade de arquivos enviados com sucesso
            - arquivos_com_erro: Quantidade de arquivos que falharam
            - detalhes: Objeto com listas de arquivos enviados e erros
    """
    ambiente_validado = validar_ambiente(ambiente)
    
    try:
        logger.info(f"[upload_arquivo_fluig] Iniciando upload de arquivo(s) - Ambiente: {ambiente_validado}")
        
        # Valida arquivos
        if not dados.arquivos or len(dados.arquivos) == 0:
            raise HTTPException(
                status_code=400,
                detail="arquivos é obrigatório e não pode estar vazio"
            )
        
        # Determina colleague_id (usa padrão se não informado)
        if dados.colleague_id:
            colleague_id = dados.colleague_id
        else:
            # Usa USER_COLLEAGUE_ID baseado no ambiente
            if ambiente_validado == "PRD":
                colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID
            else:  # QLD
                colleague_id = ConfigEnvSetings.USER_COLLEAGUE_ID_QLD
        
        logger.info(f"[upload_arquivo_fluig] Usando colleague_id: {colleague_id}")
        
        # Inicializa FluigCore
        fluig = FluigCore(ambiente=ambiente_validado)
        
        # Processa cada arquivo
        arquivos_enviados = []
        arquivos_com_erro = []
        
        for arquivo in dados.arquivos:
            try:
                logger.info(f"[upload_arquivo_fluig] Processando arquivo: {arquivo.nome}")
                
                # Valida nome do arquivo
                if not arquivo.nome or not arquivo.nome.strip():
                    logger.warning(f"[upload_arquivo_fluig] Arquivo sem nome, pulando...")
                    arquivos_com_erro.append({
                        "nome": arquivo.nome or "sem_nome",
                        "erro": "Nome do arquivo não fornecido"
                    })
                    continue
                
                # Valida conteúdo base64
                if not arquivo.conteudo_base64 or not arquivo.conteudo_base64.strip():
                    logger.warning(f"[upload_arquivo_fluig] Arquivo {arquivo.nome} sem conteúdo, pulando...")
                    arquivos_com_erro.append({
                        "nome": arquivo.nome,
                        "erro": "Conteúdo do arquivo não fornecido"
                    })
                    continue
                
                # Decodifica base64
                try:
                    conteudo_bytes = base64.b64decode(arquivo.conteudo_base64)
                    logger.info(f"[upload_arquivo_fluig] Arquivo {arquivo.nome} decodificado - {len(conteudo_bytes)} bytes")
                except Exception as e:
                    logger.error(f"[upload_arquivo_fluig] Erro ao decodificar base64 do arquivo {arquivo.nome}: {str(e)}")
                    arquivos_com_erro.append({
                        "nome": arquivo.nome,
                        "erro": f"Erro ao decodificar base64: {str(e)}"
                    })
                    continue
                
                # Faz upload do arquivo
                resultado_upload = fluig.upload_arquivo_fluig(
                    arquivo_bytes=conteudo_bytes,
                    nome_arquivo=arquivo.nome,
                    colleague_id=colleague_id
                )
                
                if resultado_upload:
                    logger.info(f"[upload_arquivo_fluig] Arquivo {arquivo.nome} enviado com sucesso")
                    arquivos_enviados.append({
                        "nome": arquivo.nome,
                        "tamanho_bytes": len(conteudo_bytes),
                        "dados": resultado_upload
                    })
                else:
                    logger.error(f"[upload_arquivo_fluig] Falha ao enviar arquivo {arquivo.nome}")
                    arquivos_com_erro.append({
                        "nome": arquivo.nome,
                        "erro": "Falha no upload (resposta vazia)"
                    })
                    
            except Exception as e:
                logger.error(f"[upload_arquivo_fluig] Erro ao processar arquivo {arquivo.nome}: {str(e)}")
                import traceback
                logger.debug(f"[upload_arquivo_fluig] Traceback: {traceback.format_exc()}")
                arquivos_com_erro.append({
                    "nome": arquivo.nome,
                    "erro": str(e)
                })
        
        # Monta resposta
        total_arquivos = len(dados.arquivos)
        sucesso_total = len(arquivos_enviados) == total_arquivos
        
        resposta = {
            "sucesso": sucesso_total,
            "total_arquivos": total_arquivos,
            "arquivos_enviados": len(arquivos_enviados),
            "arquivos_com_erro": len(arquivos_com_erro),
            "detalhes": {
                "enviados": arquivos_enviados,
                "erros": arquivos_com_erro
            }
        }
        
        if sucesso_total:
            logger.info(f"[upload_arquivo_fluig] Todos os {total_arquivos} arquivo(s) foram enviados com sucesso")
            return resposta
        else:
            logger.warning(f"[upload_arquivo_fluig] Upload parcial: {len(arquivos_enviados)}/{total_arquivos} arquivo(s) enviados")
            # Retorna 207 (Multi-Status) se houver sucessos parciais
            if len(arquivos_enviados) > 0:
                return resposta
            else:
                # Se nenhum arquivo foi enviado, retorna erro
                raise HTTPException(
                    status_code=500,
                    detail={
                        "erro": "Nenhum arquivo foi enviado com sucesso",
                        "detalhes": arquivos_com_erro
                    }
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[upload_arquivo_fluig] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[upload_arquivo_fluig] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar requisição: {str(e)}"
        )

class AnexarArquivoRequest(BaseModel):
    """Modelo para requisição de anexo de arquivo a processo/chamado"""
    process_id: str
    process_instance_id: int  # Número do chamado
    arquivos: List[AnexoBase64]
    task_user_id: str | None = None  # ID do usuário da tarefa (opcional)
    colleague_id: str | None = None  # ID do colaborador (opcional)
    attached_user: str = "Infra Automação"  # Nome do usuário que anexou (opcional)
    
    class Config:
        json_schema_extra = {
            "example": {
                "process_id": "Abertura de Chamados",
                "process_instance_id": 657984,
                "arquivos": [
                    {
                        "nome": "documento.pdf",
                        "conteudo_base64": "JVBERi0xLjQKJeLjz9MKMy..."
                    }
                ]
            }
        }

@rt_fluig_processos.post("/anexar-upload")
async def anexar_arquivo_processo_upload(
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY),
    process_id: str = Form(..., description="ID/Nome do processo (ex: 'Abertura de Chamados')"),
    process_instance_id: str = Form(..., description="Número do chamado (processInstanceId)"),
    arquivos: List[UploadFile] = File(..., description="Arquivo(s) para anexar ao chamado")
):
    """
    Anexa arquivo(s) brutos a um processo/chamado existente no Fluig
    
    Este endpoint permite anexar arquivos diretamente a um processo ou chamado existente no Fluig,
    utilizando multipart/form-data.
    
    **Funcionalidades:**
    - Upload e anexo de múltiplos arquivos em uma única requisição
    - Arquivos enviados como multipart/form-data (formato bruto)
    - Obtenção automática de detalhes da atividade (versão, movimento, atividade)
    - Processamento individual de cada arquivo
    
    Args:
        ambiente: Ambiente do Fluig onde o chamado está localizado (prd ou qld)
        process_id: ID ou nome do processo (ex: "Abertura de Chamados")
        process_instance_id: Número do chamado/processo (processInstanceId)
        arquivos: Lista de arquivos brutos para anexar (multipart/form-data)
    
    Returns:
        dict: Resposta contendo:
            - sucesso: Indica se todos os arquivos foram anexados com sucesso
            - process_id: ID do processo
            - process_instance_id: Número do chamado
            - total_arquivos: Total de arquivos processados
            - arquivos_anexados: Quantidade de arquivos anexados com sucesso
            - arquivos_com_erro: Quantidade de arquivos que falharam
            - detalhes: Objeto contendo:
                - anexados: Lista de objetos com informações dos arquivos anexados:
                    - documentId: ID do documento no Fluig (ou 0 se não disponível)
                    - fileName: Nome do arquivo anexado
                    - fullPath: Caminho completo do arquivo no Fluig (geralmente "BPM")
                - erros: Lista de objetos com informações dos arquivos que falharam
    """
    ambiente_validado = validar_ambiente(ambiente)
    
    try:
        # Limpa e valida process_id
        process_id = process_id.strip() if process_id else ""
        if not process_id:
            raise HTTPException(
                status_code=400,
                detail="process_id é obrigatório e não pode estar vazio"
            )
        
        # Limpa e converte process_instance_id para inteiro
        try:
            process_instance_id = int(process_instance_id.strip()) if isinstance(process_instance_id, str) else int(process_instance_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail=f"process_instance_id deve ser um número válido. Valor recebido: '{process_instance_id}'"
            )
        
        if process_instance_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="process_instance_id deve ser um número maior que zero"
            )
        
        logger.info(f"[anexar_arquivo_processo_upload] Iniciando anexo de arquivo(s) - ProcessId: {process_id}, ProcessInstanceId: {process_instance_id}, Ambiente: {ambiente_validado}, Total arquivos: {len(arquivos)}")
        
        # Validações
        if not arquivos or len(arquivos) == 0:
            raise HTTPException(
                status_code=400,
                detail="arquivos é obrigatório e não pode estar vazio"
            )
        
        # Determina IDs padrão (sempre usa ADMIN_COLLEAGUE_ID)
        task_user_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
        colleague_id = task_user_id
        
        # Converte arquivos brutos para formato interno
        arquivos_para_processar = []
        for arquivo_bruto in arquivos:
            if arquivo_bruto.filename:
                conteudo = await arquivo_bruto.read()
                arquivos_para_processar.append({
                    "nome": arquivo_bruto.filename,
                    "conteudo_bytes": conteudo
                })
        
        if len(arquivos_para_processar) == 0:
            raise HTTPException(
                status_code=400,
                detail="Nenhum arquivo válido fornecido"
            )
        
        # Inicializa FluigCore
        fluig = FluigCore(ambiente=ambiente_validado)
        
        # Obtém detalhes da atividade automaticamente para processVersion, movementSequence e attachedActivity
        logger.info(f"[anexar_arquivo_processo_upload] Obtendo detalhes da atividade para processInstanceId: {process_instance_id}")
        detalhes_atividade = fluig.obter_detalhes_atividade(process_instance_id=process_instance_id)
        
        if not detalhes_atividade:
            logger.warning(f"[anexar_arquivo_processo_upload] Não foi possível obter detalhes da atividade, usando valores padrão")
            process_version = 57
            movement_sequence = 3
            activity_name = "Aguardando Classificação"
        else:
            items = detalhes_atividade.get('items', [])
            if not items:
                logger.warning(f"[anexar_arquivo_processo_upload] Nenhuma atividade encontrada, usando valores padrão")
                process_version = 57
                movement_sequence = 3
                activity_name = "Aguardando Classificação"
            else:
                # Busca a atividade ativa (active: true) ou usa a última
                atividade_ativa = None
                for item in items:
                    if item.get('active', False):
                        atividade_ativa = item
                        break
                
                # Se não encontrar atividade ativa, usa a última
                if not atividade_ativa:
                    atividade_ativa = items[-1]
                    logger.info(f"[anexar_arquivo_processo_upload] Nenhuma atividade ativa encontrada, usando a última atividade")
                
                process_version = atividade_ativa.get('processVersion')
                movement_sequence = atividade_ativa.get('movementSequence')
                activity_name = atividade_ativa.get('state', {}).get('stateName', 'Aguardando Classificação')
                
                logger.info(f"[anexar_arquivo_processo_upload] Valores obtidos automaticamente - Process Version: {process_version}, Movement Sequence: {movement_sequence}, Activity Name: {activity_name}")
                
                # Usa valores padrão se não foram obtidos
                if process_version is None:
                    process_version = 57
                    logger.warning(f"[anexar_arquivo_processo_upload] Process Version não encontrado, usando padrão: {process_version}")
                
                if movement_sequence is None:
                    movement_sequence = 3
                    logger.warning(f"[anexar_arquivo_processo_upload] Movement Sequence não encontrado, usando padrão: {movement_sequence}")
                
                if activity_name is None:
                    activity_name = "Aguardando Classificação"
                    logger.warning(f"[anexar_arquivo_processo_upload] Activity Name não encontrado, usando padrão: {activity_name}")
        
        # Processa cada arquivo
        arquivos_anexados = []
        arquivos_com_erro = []
        
        for arquivo_info in arquivos_para_processar:
            nome_arquivo = arquivo_info["nome"]
            conteudo_bytes = arquivo_info["conteudo_bytes"]
            
            try:
                logger.info(f"[anexar_arquivo_processo_upload] Processando arquivo: {nome_arquivo}")
                
                # Faz upload do arquivo primeiro
                try:
                    logger.info(f"[anexar_arquivo_processo_upload] Fazendo upload do arquivo {nome_arquivo} primeiro...")
                    
                    resultado_upload = fluig.upload_arquivo_fluig(
                        arquivo_bytes=conteudo_bytes,
                        nome_arquivo=nome_arquivo,
                        colleague_id=colleague_id
                    )
                    
                    if not resultado_upload or not resultado_upload.get("sucesso"):
                        erro_upload = resultado_upload.get("erro", "Falha no upload") if resultado_upload else "Falha no upload (resposta vazia)"
                        logger.error(f"[anexar_arquivo_processo_upload] Falha no upload do arquivo {nome_arquivo}: {erro_upload}")
                        arquivos_com_erro.append({
                            "nome": nome_arquivo,
                            "erro": f"Falha no upload: {erro_upload}"
                        })
                        continue
                    
                    # O endpoint /ecm/upload não retorna document_id diretamente
                    # Usamos document_id=None para que o método use documentId: 0 no payload
                    document_id = resultado_upload.get("document_id")
                    logger.info(f"[anexar_arquivo_processo_upload] Upload do arquivo {nome_arquivo} concluído - DocumentID: {document_id if document_id else '0 (será usado no payload)'}")
                    
                except Exception as e:
                    logger.error(f"[anexar_arquivo_processo_upload] Erro ao fazer upload do arquivo {nome_arquivo}: {str(e)}")
                    import traceback
                    logger.debug(f"[anexar_arquivo_processo_upload] Traceback: {traceback.format_exc()}")
                    arquivos_com_erro.append({
                        "nome": nome_arquivo,
                        "erro": f"Erro no upload: {str(e)}"
                    })
                    continue
                
                # Agora anexa o arquivo ao chamado usando saveAttachments
                # Se document_id não estiver disponível, o método usará documentId: 0
                resultado_anexo = fluig.AnexarArquivoProcesso(
                    process_id=process_id,
                    process_instance_id=process_instance_id,
                    nome_arquivo=nome_arquivo,
                    document_id=document_id,  # Pode ser None ou 0, o método trata isso
                    version=process_version,
                    current_movto=movement_sequence,
                    task_user_id=task_user_id,
                    colleague_id=colleague_id,
                    attached_activity=activity_name
                )
                
                if resultado_anexo.get("sucesso"):
                    logger.info(f"[anexar_arquivo_processo_upload] Arquivo {nome_arquivo} anexado com sucesso ao chamado {process_instance_id}")
                    # Extrai fullPath da resposta se disponível, caso contrário usa padrão
                    dados_resposta = resultado_anexo.get("dados", {})
                    content = dados_resposta.get("content", {})
                    attachments = content.get("attachments", []) if isinstance(content, dict) else []
                    full_path = "BPM"  # Valor padrão
                    if attachments and len(attachments) > 0:
                        full_path = attachments[0].get("fullPath", "BPM")
                    
                    arquivos_anexados.append({
                        "documentId": document_id if document_id else 0,
                        "fileName": nome_arquivo,
                        "fullPath": full_path
                    })
                else:
                    erro_msg = resultado_anexo.get("erro") or resultado_anexo.get("texto", "Erro desconhecido")
                    logger.error(f"[anexar_arquivo_processo_upload] Falha ao anexar arquivo {nome_arquivo}: {erro_msg}")
                    arquivos_com_erro.append({
                        "nome": nome_arquivo,
                        "erro": erro_msg,
                        "status_code": resultado_anexo.get("status_code")
                    })
                    
            except Exception as e:
                logger.error(f"[anexar_arquivo_processo_upload] Erro ao processar arquivo {nome_arquivo}: {str(e)}")
                import traceback
                logger.debug(f"[anexar_arquivo_processo_upload] Traceback: {traceback.format_exc()}")
                arquivos_com_erro.append({
                    "nome": nome_arquivo,
                    "erro": str(e)
                })
        
        # Monta resposta
        total_arquivos = len(arquivos_para_processar)
        sucesso_total = len(arquivos_anexados) == total_arquivos
        
        resposta = {
            "sucesso": sucesso_total,
            "process_id": process_id,
            "process_instance_id": process_instance_id,
            "total_arquivos": total_arquivos,
            "arquivos_anexados": len(arquivos_anexados),
            "arquivos_com_erro": len(arquivos_com_erro),
            "detalhes": {
                "anexados": arquivos_anexados,
                "erros": arquivos_com_erro
            }
        }
        
        if sucesso_total:
            logger.info(f"[anexar_arquivo_processo_upload] Todos os {total_arquivos} arquivo(s) foram anexados com sucesso ao chamado {process_instance_id}")
            return resposta
        else:
            logger.warning(f"[anexar_arquivo_processo_upload] Anexo parcial: {len(arquivos_anexados)}/{total_arquivos} arquivo(s) anexados")
            # Retorna resposta mesmo com erros parciais
            if len(arquivos_anexados) > 0:
                return resposta
            else:
                # Se nenhum arquivo foi anexado, retorna erro
                raise HTTPException(
                    status_code=500,
                    detail={
                        "erro": "Nenhum arquivo foi anexado com sucesso",
                        "detalhes": arquivos_com_erro
                    }
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[anexar_arquivo_processo_upload] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[anexar_arquivo_processo_upload] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar requisição: {str(e)}"
        )

@rt_fluig_processos.post("/anexar")
async def anexar_arquivo_processo(
    dados: AnexarArquivoRequest,
    ambiente: str = Path(..., description="Ambiente do Fluig (prd ou qld)"),
    api_key: str = Depends(Auth_API_KEY)
):
    """
    Anexa arquivo(s) codificados em base64 a um processo/chamado existente no Fluig
    
    Este endpoint permite anexar arquivos a um processo ou chamado existente no Fluig,
    utilizando arquivos codificados em base64 dentro de um payload JSON.
    
    **Funcionalidades:**
    - Upload e anexo de múltiplos arquivos em uma única requisição
    - Arquivos enviados em formato base64 dentro de JSON
    - Processamento individual de cada arquivo
    
    Args:
        dados: Objeto JSON contendo:
            - process_id: ID ou nome do processo
            - process_instance_id: Número do chamado/processo
            - arquivos: Lista de objetos com 'nome' e 'conteudo_base64'
        ambiente: Ambiente do Fluig onde o chamado está localizado (prd ou qld)
    
    Returns:
        dict: Resposta contendo:
            - sucesso: Indica se todos os arquivos foram anexados com sucesso
            - process_id: ID do processo
            - process_instance_id: Número do chamado
            - total_arquivos: Total de arquivos processados
            - arquivos_anexados: Quantidade de arquivos anexados com sucesso
            - arquivos_com_erro: Quantidade de arquivos que falharam
            - detalhes: Objeto contendo:
                - anexados: Lista de objetos com informações dos arquivos anexados:
                    - documentId: ID do documento no Fluig (ou 0 se não disponível)
                    - fileName: Nome do arquivo anexado
                    - fullPath: Caminho completo do arquivo no Fluig (geralmente "BPM")
                - erros: Lista de objetos com informações dos arquivos que falharam
    """
    ambiente_validado = validar_ambiente(ambiente)
    
    try:
        logger.info(f"[anexar_arquivo_processo] Iniciando anexo de arquivo(s) - ProcessId: {dados.process_id}, ProcessInstanceId: {dados.process_instance_id}, Ambiente: {ambiente_validado}")
        
        # Validações
        if not dados.process_id or not dados.process_id.strip():
            raise HTTPException(
                status_code=400,
                detail="process_id é obrigatório e não pode estar vazio"
            )
        
        if not dados.process_instance_id or dados.process_instance_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="process_instance_id é obrigatório e deve ser um número válido"
            )
        
        if not dados.arquivos or len(dados.arquivos) == 0:
            raise HTTPException(
                status_code=400,
                detail="arquivos é obrigatório e não pode estar vazio"
            )
        
        # Determina IDs padrão se não informados
        if not dados.task_user_id:
            dados.task_user_id = ConfigEnvSetings.ADMIN_COLLEAGUE_ID
        
        if not dados.colleague_id:
            dados.colleague_id = dados.task_user_id
        
        # Converte arquivos base64 para formato interno
        arquivos_para_processar = []
        for arquivo in dados.arquivos:
            if arquivo.nome and arquivo.conteudo_base64:
                try:
                    conteudo_bytes = base64.b64decode(arquivo.conteudo_base64)
                    arquivos_para_processar.append({
                        "nome": arquivo.nome,
                        "conteudo_bytes": conteudo_bytes
                    })
                except Exception as e:
                    logger.warning(f"[anexar_arquivo_processo] Erro ao decodificar base64 do arquivo {arquivo.nome}: {str(e)}")
                    continue
        
        if len(arquivos_para_processar) == 0:
            raise HTTPException(
                status_code=400,
                detail="Nenhum arquivo válido fornecido"
            )
        
        logger.info(f"[anexar_arquivo_processo] Total de arquivos para processar: {len(arquivos_para_processar)}")
        
        # Inicializa FluigCore
        fluig = FluigCore(ambiente=ambiente_validado)
        
        # Obtém detalhes da atividade automaticamente para processVersion, movementSequence e attachedActivity
        logger.info(f"[anexar_arquivo_processo] Obtendo detalhes da atividade para processInstanceId: {dados.process_instance_id}")
        detalhes_atividade = fluig.obter_detalhes_atividade(process_instance_id=dados.process_instance_id)
        
        if not detalhes_atividade:
            logger.warning(f"[anexar_arquivo_processo] Não foi possível obter detalhes da atividade, usando valores padrão")
            process_version = 57
            movement_sequence = 3
            activity_name = "Aguardando Classificação"
        else:
            items = detalhes_atividade.get('items', [])
            if not items:
                logger.warning(f"[anexar_arquivo_processo] Nenhuma atividade encontrada, usando valores padrão")
                process_version = 57
                movement_sequence = 3
                activity_name = "Aguardando Classificação"
            else:
                # Busca a atividade ativa (active: true) ou usa a última
                atividade_ativa = None
                for item in items:
                    if item.get('active', False):
                        atividade_ativa = item
                        break
                
                # Se não encontrar atividade ativa, usa a última
                if not atividade_ativa:
                    atividade_ativa = items[-1]
                    logger.info(f"[anexar_arquivo_processo] Nenhuma atividade ativa encontrada, usando a última atividade")
                
                # Obtém valores automaticamente da atividade
                process_version = atividade_ativa.get('processVersion')
                movement_sequence = atividade_ativa.get('movementSequence')
                activity_name = atividade_ativa.get('state', {}).get('stateName', 'Aguardando Classificação')
                
                logger.info(f"[anexar_arquivo_processo] Valores obtidos automaticamente - Process Version: {process_version}, Movement Sequence: {movement_sequence}, Activity Name: {activity_name}")
                
                # Usa valores padrão se não foram obtidos
                if process_version is None:
                    process_version = 57
                    logger.warning(f"[anexar_arquivo_processo] Process Version não encontrado, usando padrão: {process_version}")
                
                if movement_sequence is None:
                    movement_sequence = 3
                    logger.warning(f"[anexar_arquivo_processo] Movement Sequence não encontrado, usando padrão: {movement_sequence}")
                
                if activity_name is None:
                    activity_name = "Aguardando Classificação"
                    logger.warning(f"[anexar_arquivo_processo] Activity Name não encontrado, usando padrão: {activity_name}")
        
        # Processa cada arquivo
        arquivos_anexados = []
        arquivos_com_erro = []
        
        for arquivo_info in arquivos_para_processar:
            nome_arquivo = arquivo_info["nome"]
            conteudo_bytes = arquivo_info["conteudo_bytes"]
            
            try:
                logger.info(f"[anexar_arquivo_processo] Processando arquivo: {nome_arquivo}")
                
                # Faz upload do arquivo primeiro
                try:
                    logger.info(f"[anexar_arquivo_processo] Fazendo upload do arquivo {nome_arquivo} primeiro...")
                    
                    resultado_upload = fluig.upload_arquivo_fluig(
                        arquivo_bytes=conteudo_bytes,
                        nome_arquivo=nome_arquivo,
                        colleague_id=dados.colleague_id
                    )
                    
                    if not resultado_upload or not resultado_upload.get("sucesso"):
                        erro_upload = resultado_upload.get("erro", "Falha no upload") if resultado_upload else "Falha no upload (resposta vazia)"
                        logger.error(f"[anexar_arquivo_processo] Falha no upload do arquivo {nome_arquivo}: {erro_upload}")
                        arquivos_com_erro.append({
                            "nome": nome_arquivo,
                            "erro": f"Falha no upload: {erro_upload}"
                        })
                        continue
                    
                    # O endpoint /ecm/upload não retorna document_id diretamente
                    # Usamos document_id=None para que o método use documentId: 0 no payload
                    document_id = resultado_upload.get("document_id")
                    logger.info(f"[anexar_arquivo_processo] Upload do arquivo {nome_arquivo} concluído - DocumentID: {document_id if document_id else '0 (será usado no payload)'}")
                    
                except Exception as e:
                    logger.error(f"[anexar_arquivo_processo] Erro ao fazer upload do arquivo {nome_arquivo}: {str(e)}")
                    import traceback
                    logger.debug(f"[anexar_arquivo_processo] Traceback: {traceback.format_exc()}")
                    arquivos_com_erro.append({
                        "nome": nome_arquivo,
                        "erro": f"Erro no upload: {str(e)}"
                    })
                    continue
                
                # Agora anexa o arquivo ao chamado usando saveAttachments
                # Se document_id não estiver disponível, o método usará documentId: 0
                resultado_anexo = fluig.AnexarArquivoProcesso(
                    process_id=dados.process_id,
                    process_instance_id=dados.process_instance_id,
                    nome_arquivo=nome_arquivo,
                    document_id=document_id,  # Pode ser None ou 0, o método trata isso
                    version=process_version,
                    current_movto=movement_sequence,
                    task_user_id=dados.task_user_id,
                    colleague_id=dados.colleague_id,
                    attached_user=dados.attached_user,
                    attached_activity=activity_name
                )
                
                if resultado_anexo.get("sucesso"):
                    logger.info(f"[anexar_arquivo_processo] Arquivo {nome_arquivo} anexado com sucesso ao chamado {dados.process_instance_id}")
                    # Extrai fullPath da resposta se disponível, caso contrário usa padrão
                    dados_resposta = resultado_anexo.get("dados", {})
                    content = dados_resposta.get("content", {})
                    attachments = content.get("attachments", []) if isinstance(content, dict) else []
                    full_path = "BPM"  # Valor padrão
                    if attachments and len(attachments) > 0:
                        full_path = attachments[0].get("fullPath", "BPM")
                    
                    arquivos_anexados.append({
                        "documentId": document_id if document_id else 0,
                        "fileName": nome_arquivo,
                        "fullPath": full_path
                    })
                else:
                    erro_msg = resultado_anexo.get("erro") or resultado_anexo.get("texto", "Erro desconhecido")
                    logger.error(f"[anexar_arquivo_processo] Falha ao anexar arquivo {nome_arquivo}: {erro_msg}")
                    arquivos_com_erro.append({
                        "nome": nome_arquivo,
                        "erro": erro_msg,
                        "status_code": resultado_anexo.get("status_code")
                    })
                    
            except Exception as e:
                logger.error(f"[anexar_arquivo_processo] Erro ao processar arquivo {nome_arquivo}: {str(e)}")
                import traceback
                logger.debug(f"[anexar_arquivo_processo] Traceback: {traceback.format_exc()}")
                arquivos_com_erro.append({
                    "nome": nome_arquivo,
                    "erro": str(e)
                })
        
        # Monta resposta
        total_arquivos = len(arquivos_para_processar)
        sucesso_total = len(arquivos_anexados) == total_arquivos
        
        resposta = {
            "sucesso": sucesso_total,
            "process_id": dados.process_id,
            "process_instance_id": dados.process_instance_id,
            "total_arquivos": total_arquivos,
            "arquivos_anexados": len(arquivos_anexados),
            "arquivos_com_erro": len(arquivos_com_erro),
            "detalhes": {
                "anexados": arquivos_anexados,
                "erros": arquivos_com_erro
            }
        }
        
        if sucesso_total:
            logger.info(f"[anexar_arquivo_processo] Todos os {total_arquivos} arquivo(s) foram anexados com sucesso ao chamado {dados.process_instance_id}")
            return resposta
        else:
            logger.warning(f"[anexar_arquivo_processo] Anexo parcial: {len(arquivos_anexados)}/{total_arquivos} arquivo(s) anexados")
            # Retorna resposta mesmo com erros parciais
            if len(arquivos_anexados) > 0:
                return resposta
            else:
                # Se nenhum arquivo foi anexado, retorna erro
                raise HTTPException(
                    status_code=500,
                    detail={
                        "erro": "Nenhum arquivo foi anexado com sucesso",
                        "detalhes": arquivos_com_erro
                    }
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[anexar_arquivo_processo] Erro inesperado: {str(e)}")
        import traceback
        logger.debug(f"[anexar_arquivo_processo] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar requisição: {str(e)}"
        )
