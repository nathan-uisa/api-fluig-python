from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel
from src.modelo_dados.modelo_sites import DadosFuncionario, DadosFuncionarioForm, DadosChamado, PayloadFuncionario
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificado
import requests
from datetime import datetime
from src.utilitarios_centrais.logger import logger
from src.site.planilha import Planilha, PATH_TO_TEMP
from src.site.abrir_chamados import AbrirChamados
from src.fluig.fluig_core import FluigCore
from src.web.web_servicos_fluig import obter_detalhes_servico_fluig
from src.web.web_auth_manager import obter_cookies_validos
from src.utilitarios_centrais.json_utils import salvar_detalhes_servico_json
from src.modelo_dados.modelo_settings import ConfigEnvSetings
import os
import tempfile
import json

router = APIRouter()
templates = Jinja2Templates(directory="src/site/templates")


def buscar_funcionario(email_ou_chapa: str, ambiente: str = "PRD", obrigatorio: bool = True) -> Optional[DadosFuncionario]:
    """
    Busca dados do funcionário usando o dataset ds_funcionarios do Fluig
    Aceita email ou chapa como parâmetro de busca
    
    Args:
        email_ou_chapa: Email ou chapa do funcionário
        ambiente: Ambiente do Fluig (PRD ou QLD), padrão PRD
        obrigatorio: Se True, lança ValueError quando não encontrar. Se False, retorna None
    
    Returns:
        DadosFuncionario com os dados do funcionário ou None se não encontrar (quando obrigatorio=False)
    
    Raises:
        ValueError: Se obrigatorio=True e não encontrar o funcionário ou houver erro na busca
    """
    if not email_ou_chapa or not email_ou_chapa.strip():
        if obrigatorio:
            raise ValueError("Email ou chapa não fornecido")
        return None
    
    email_ou_chapa = email_ou_chapa.strip()
    
    try:
        logger.info(f"[buscar_funcionario] Buscando funcionário - Email/Chapa: {email_ou_chapa}, Ambiente: {ambiente}")
        
        fluig_core = FluigCore(ambiente=ambiente)
        resultado = fluig_core.Dataset_config(dataset_id="ds_funcionarios", user=email_ou_chapa)
        
        # Verificar se a resposta é um objeto Response (erro HTTP)
        if hasattr(resultado, 'status_code'):
            status_code = resultado.status_code
            mensagem_erro = None
            if status_code == 502:
                mensagem_erro = "Servidor Fluig temporariamente indisponível. Por favor, tente novamente em alguns instantes."
            elif status_code == 503:
                mensagem_erro = "Serviço Fluig temporariamente indisponível. Por favor, tente novamente em alguns instantes."
            elif status_code == 401:
                mensagem_erro = "Falha de autenticação com o Fluig. Por favor, entre em contato com o suporte."
            elif status_code == 404:
                mensagem_erro = "Recurso não encontrado no Fluig. Por favor, entre em contato com o suporte."
            else:
                mensagem_erro = f"Erro ao conectar com o Fluig (código {status_code}). Por favor, tente novamente ou entre em contato com o suporte."
            
            logger.error(f"[buscar_funcionario] Erro HTTP {status_code} ao buscar funcionário")
            if obrigatorio:
                raise ValueError(mensagem_erro)
            return None
        
        # Verificar se a resposta é um dicionário com content
        if isinstance(resultado, dict) and 'content' in resultado:
            content = resultado.get('content', [])
            
            if not content or len(content) == 0:
                logger.warning(f"[buscar_funcionario] Nenhum funcionário encontrado para: {email_ou_chapa}")
                if obrigatorio:
                    raise ValueError(f"Nenhum funcionário encontrado para: {email_ou_chapa}")
                return None
            
            # Pegar o primeiro resultado
            funcionario_data = content[0]
            logger.info(f"[buscar_funcionario] Funcionário encontrado: {funcionario_data.get('Nome', 'N/A')}")
            
            # Criar instância DadosFuncionario
            funcionario = DadosFuncionario(**funcionario_data)
            return funcionario
        else:
            mensagem_erro = "Resposta inválida do dataset de funcionários. Por favor, entre em contato com o suporte."
            logger.error(f"[buscar_funcionario] Resposta inválida do dataset: {type(resultado)}")
            if obrigatorio:
                raise ValueError(mensagem_erro)
            return None
            
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"[buscar_funcionario] Erro ao buscar funcionário: {str(e)}")
        if obrigatorio:
            raise ValueError(f"Erro ao buscar funcionário: {str(e)}")
        return None


def buscar_funcionario_por_email(email: str, ambiente: str = "PRD") -> DadosFuncionario:
    """
    Busca dados do funcionário usando o dataset ds_funcionarios do Fluig por email
    
    Args:
        email: Email do funcionário
        ambiente: Ambiente do Fluig (PRD ou QLD), padrão PRD
    
    Returns:
        DadosFuncionario com os dados do funcionário
    
    Raises:
        ValueError: Se não encontrar o funcionário ou houver erro na busca
    """
    return buscar_funcionario(email, ambiente, obrigatorio=True)


def buscar_funcionario_por_chapa_ou_email(chapa_ou_email: str, ambiente: str = "PRD") -> Optional[DadosFuncionario]:
    """
    Busca dados do funcionário usando o dataset ds_funcionarios do Fluig
    Aceita email ou chapa como parâmetro de busca
    
    Args:
        chapa_ou_email: Chapa ou email do funcionário
        ambiente: Ambiente do Fluig (PRD ou QLD), padrão PRD
    
    Returns:
        DadosFuncionario com os dados do funcionário ou None se não encontrar
    
    Raises:
        ValueError: Se houver erro na busca (não se não encontrar)
    """
    return buscar_funcionario(chapa_ou_email, ambiente, obrigatorio=False)


def buscar_colleague_name(chapa_ou_email: str, ambiente: str = "PRD") -> Optional[str]:
    """
    Busca o colleagueName formatado do dataset colleague
    Retorna o nome formatado corretamente (primeira letra maiúscula)
    
    Args:
        chapa_ou_email: Chapa ou email do funcionário
        ambiente: Ambiente do Fluig (PRD ou QLD), padrão PRD
    
    Returns:
        Nome formatado (colleagueName) ou None se não encontrar
    """
    if not chapa_ou_email or not chapa_ou_email.strip():
        return None
    
    chapa_ou_email = chapa_ou_email.strip()
    
    try:
        logger.info(f"[buscar_colleague_name] Buscando colleagueName - Chapa/Email: {chapa_ou_email}, Ambiente: {ambiente}")
        
        fluig_core = FluigCore(ambiente=ambiente)
        resultado = fluig_core.Dataset_config(dataset_id="colleague", user=chapa_ou_email)
        
        # Verificar se a resposta é um objeto Response (erro HTTP)
        if hasattr(resultado, 'status_code'):
            logger.warning(f"[buscar_colleague_name] Erro HTTP {resultado.status_code} ao buscar colleague")
            return None
        
        # Verificar se a resposta é um dicionário com content
        if isinstance(resultado, dict) and 'content' in resultado:
            content = resultado.get('content', [])
            
            if not content or len(content) == 0:
                logger.warning(f"[buscar_colleague_name] Nenhum colleague encontrado para: {chapa_ou_email}")
                return None
            
            # Pegar o primeiro resultado
            colleague_data = content[0]
            colleague_name = colleague_data.get('colleagueName', '')
            
            if colleague_name:
                logger.info(f"[buscar_colleague_name] colleagueName encontrado: {colleague_name}")
                return colleague_name
            else:
                logger.warning(f"[buscar_colleague_name] colleagueName não encontrado no resultado")
                return None
        else:
            logger.warning(f"[buscar_colleague_name] Resposta inválida do dataset: {type(resultado)}")
            return None
            
    except Exception as e:
        logger.warning(f"[buscar_colleague_name] Erro ao buscar colleagueName: {str(e)}")
        return None


@router.get("/chamado", response_class=HTMLResponse)
async def chamado(request: Request):
    """Página de chamado com dados do funcionário"""
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url="/login")
    
    email = user.get('email')
    if not email:
        return RedirectResponse(url="/login")
    
    try:
        # Buscar funcionário usando dataset interno do Fluig
        funcionario = buscar_funcionario_por_email(email, ambiente="PRD")
        
        # Criar dados formatados para o formulário
        dados_funcionario = DadosFuncionarioForm(
            elaborador=funcionario.Nome or '',
            solicitante=funcionario.Nome or '',
            data_abertura=datetime.now().strftime('%d/%m/%Y %H:%M'),
            telefone_contato=funcionario.Telefone or '',
            cargo=funcionario.Função or '',
            secao=funcionario.Seção or '',
            empresa=funcionario.Empresa or '',
            centro_custo=funcionario.Centro_Custo or '',
            chapa=funcionario.Chapa,
            gerencia=funcionario.Gerencia,
            email=funcionario.Email or ''
        )
        
        logger.info(f"Dados do funcionário carregados para: {email}")
        
        return templates.TemplateResponse(
            "chamado.html",
            {
                "request": request,
                "dados": dados_funcionario.model_dump(),
                "user": user,
                "versao": "3.1.2"
            }
        )
        
    except ValueError as e:
        logger.error(f"Erro ao buscar dados do funcionário: {str(e)}")
        return templates.TemplateResponse(
            "chamado.html",
            {
                "request": request,
                "dados": None,
                "user": user,
                "error": f"Erro ao carregar dados do funcionário: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return templates.TemplateResponse(
            "chamado.html",
            {
                "request": request,
                "dados": None,
                "user": user,
                "error": f"Erro inesperado ao processar a solicitação: {str(e)}",
                "versao": "3.1.2"
            }
        )


@router.post("/chamado")
async def criar_chamado(
    request: Request,
    ds_titulo: str = Form(...),
    ds_chamado: str = Form(...),
    solicitante: str = Form(None),
    telefone_contato: str = Form(None),
    sap_ibid: str = Form("Não"),
    planilha: UploadFile = File(None),
    qtd_chamados: int = Form(1),
    ignorar_primeira_linha: str = Form("1"),
    ds_grupo_servico: str = Form(None),
    item_servico: str = Form(None),
    servico: str = Form(None),
    servico_id: str = Form(None),
    urg_alta: str = Form(None),
    urg_media: str = Form(None),
    urg_baixa: str = Form(None),
    ds_resp_servico: str = Form(None),
    ds_tipo: str = Form(None),
    ds_urgencia: str = Form(None),
    equipe_responsavel: str = Form(None),
    status: str = Form(None),
    accept: Optional[str] = Header(None)
):
    """Processa criação de chamado(s) - único ou em lote via planilha"""
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url="/login")
    
    email = user.get('email')
    if not email:
        return RedirectResponse(url="/login")
    
    try:
        # Buscar dados do funcionário novamente usando dataset interno do Fluig
        funcionario = buscar_funcionario_por_email(email, ambiente="PRD")
        
        # Validar telefone obrigatório
        # Priorizar telefone preenchido no campo "Telefone de Contato" do formulário
        telefone_final = telefone_contato.strip() if telefone_contato and telefone_contato.strip() else (funcionario.Telefone.strip() if funcionario.Telefone and funcionario.Telefone.strip() else '')
        
        if not telefone_final:
            # Retornar erro se telefone não foi fornecido
            dados_funcionario = DadosFuncionarioForm(
                elaborador=funcionario.Nome or '',
                solicitante=solicitante or funcionario.Nome or '',
                data_abertura=datetime.now().strftime('%d/%m/%Y %H:%M'),
                telefone_contato='',
                cargo=funcionario.Função or '',
                secao=funcionario.Seção or '',
                empresa=funcionario.Empresa or '',
                centro_custo=funcionario.Centro_Custo or '',
                chapa=funcionario.Chapa,
                gerencia=funcionario.Gerencia,
                email=funcionario.Email or ''
            )
            
            error_msg = "O campo Telefone de Contato é obrigatório para abrir um chamado."
            
            # Verificar se é requisição AJAX
            if accept and 'application/json' in accept:
                return JSONResponse(
                    status_code=400,
                    content={
                        "sucesso": False,
                        "erro": error_msg
                    }
                )
            
            return templates.TemplateResponse(
                "chamado.html",
                {
                    "request": request,
                    "dados": dados_funcionario.model_dump(),
                    "user": user,
                    "error": error_msg,
                    "versao": "3.1.2"
                }
            )
        
        # Criar dados formatados para o formulário
        dados_funcionario = DadosFuncionarioForm(
            elaborador=funcionario.Nome or '',
            solicitante=solicitante or funcionario.Nome or '',
            data_abertura=datetime.now().strftime('%d/%m/%Y %H:%M'),
            telefone_contato=telefone_final,
            cargo=funcionario.Função or '',
            secao=funcionario.Seção or '',
            empresa=funcionario.Empresa or '',
            centro_custo=funcionario.Centro_Custo or '',
            chapa=funcionario.Chapa,
            gerencia=funcionario.Gerencia,
            email=funcionario.Email or ''
        )
        
        chamados_criados = 0
        chamados_erro = 0
        
        # Se há planilha, processar em lote
        if planilha and planilha.filename:
            if not planilha.filename.endswith('.xlsx'):
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "error": "Apenas arquivos .xlsx são suportados.",
                        "versao": "3.1.2"
                    }
                )
            
            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                content = await planilha.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Processar planilha
                planilha_obj = Planilha(tmp_path)
                linhas_processadas = planilha_obj.criar_base_chamados()
                
                if not linhas_processadas:
                    os.unlink(tmp_path)
                    return templates.TemplateResponse(
                        "chamado.html",
                        {
                            "request": request,
                            "dados": dados_funcionario.model_dump(),
                            "user": user,
                            "error": "Erro ao processar planilha. Verifique o formato do arquivo.",
                            "versao": "3.1.2"
                        }
                    )
                
                # Usar o novo módulo para abrir chamados em sequência
                ignorar_cabecalho = ignorar_primeira_linha == "1"
                abrir_chamados = AbrirChamados(email)
                resultado = abrir_chamados.abrir_chamados_sequencia(
                    titulo=ds_titulo,
                    descricao=ds_chamado,
                    qtd_chamados=qtd_chamados,
                    inicio_linha=1,
                    ignorar_primeira_linha=ignorar_cabecalho,
                    servico_id=servico_id if servico_id and servico_id.strip() else None,
                    solicitante=solicitante if solicitante and solicitante.strip() else None
                )
                
                chamados_criados = resultado['sucessos']
                chamados_erro = resultado['erros']
                
                # Limpar arquivos temporários
                planilha_obj.limpar_arquivo_temporario()
                os.unlink(tmp_path)
                
                # Verificar se é requisição AJAX
                if accept and 'application/json' in accept:
                    chamados_ids = [d.get('chamado_id') for d in resultado.get('detalhes', []) if d.get('sucesso') and d.get('chamado_id')]
                    return JSONResponse(content={
                        "sucesso": True,
                        "chamados_criados": chamados_criados,
                        "chamados_erro": chamados_erro,
                        "chamados_ids": chamados_ids,
                        "detalhes": resultado.get('detalhes', [])
                    })
                
                mensagem = f"{chamados_criados} chamado(s) criado(s) com sucesso!"
                if chamados_erro > 0:
                    mensagem += f" {chamados_erro} chamado(s) falharam."
                
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "success": mensagem,
                        "versao": "3.1.2"
                    }
                )
                
            except Exception as e:
                logger.error(f"Erro ao processar planilha: {str(e)}")
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "error": f"Erro ao processar planilha: {str(e)}",
                        "versao": "3.1.2"
                    }
                )
        else:
            # Criar chamado único
            try:
                ambiente = "PRD"
                usuario_atendido = None
                
                # Buscar nome do funcionário se solicitante foi fornecido
                # Usar colleagueName do dataset colleague para obter nome formatado corretamente
                if solicitante and solicitante.strip():
                    try:
                        usuario_atendido = buscar_colleague_name(solicitante.strip(), ambiente=ambiente)
                        if usuario_atendido:
                            logger.info(f"[criar_chamado] UsuarioAtendido encontrado (colleagueName): {usuario_atendido}")
                        else:
                            logger.warning(f"[criar_chamado] Colleague não encontrado para solicitante: {solicitante}")
                    except Exception as e:
                        logger.warning(f"[criar_chamado] Erro ao buscar colleagueName por solicitante: {str(e)}")
                
                # Verificar se deve classificar o chamado (se há servico_id preenchido)
                if servico_id and servico_id.strip():
                    # Criar chamado classificado usando a função diretamente
                    payload_chamado = AberturaChamadoClassificado(
                        titulo=ds_titulo,
                        descricao=ds_chamado,
                        usuario=email,
                        telefone=telefone_final,
                        servico=servico_id
                    )
                    
                    logger.info(f"[criar_chamado] Criando chamado classificado - Serviço: {servico_id}, Usuário: {email}")
                    
                    # Chamar diretamente a função FluigCore
                    fluig_core = FluigCore(ambiente=ambiente)
                    resposta = fluig_core.AberturaDeChamado(tipo_chamado="classificado", Item=payload_chamado, usuario_atendido=usuario_atendido)
                    
                    if not resposta.get('sucesso'):
                        logger.error(f"[criar_chamado] Falha ao abrir chamado classificado - Status: {resposta.get('status_code')}")
                        raise HTTPException(
                            status_code=resposta.get('status_code', 500),
                            detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
                        )
                    
                    # Obter processInstanceId
                    dados = resposta.get('dados', {})
                    process_instance_id = None
                    if dados and isinstance(dados, dict):
                        process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
                    
                    if process_instance_id:
                        logger.info(f"[criar_chamado] Chamado classificado criado com sucesso - ID: {process_instance_id}")
                    else:
                        logger.error(f"[criar_chamado] Chamado criado mas processInstanceId não encontrado")
                        raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
                        
                else:
                    # Criar chamado normal
                    payload_chamado = DadosChamado(
                        Usuario=email,
                        Titulo=ds_titulo,
                        Descricao=ds_chamado
                    )
                    
                    logger.info(f"[criar_chamado] Criando chamado normal - Usuário: {email}")
                    
                    # Chamar diretamente a função FluigCore
                    fluig_core = FluigCore(ambiente=ambiente)
                    resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=payload_chamado, usuario_atendido=usuario_atendido)
                    
                    if not resposta.get('sucesso'):
                        logger.error(f"[criar_chamado] Falha ao abrir chamado normal - Status: {resposta.get('status_code')}")
                        raise HTTPException(
                            status_code=resposta.get('status_code', 500),
                            detail=f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}"
                        )
                    
                    # Obter processInstanceId
                    dados = resposta.get('dados', {})
                    process_instance_id = None
                    if dados and isinstance(dados, dict):
                        process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
                    
                    if process_instance_id:
                        logger.info(f"[criar_chamado] Chamado normal criado com sucesso - ID: {process_instance_id}")
                    else:
                        logger.error(f"[criar_chamado] Chamado criado mas processInstanceId não encontrado")
                        raise HTTPException(status_code=500, detail="processInstanceId não encontrado na resposta do Fluig")
                
                # Verificar se é requisição AJAX
                if accept and 'application/json' in accept:
                    return JSONResponse(content={
                        "sucesso": True,
                        "chamado_id": process_instance_id,
                        "mensagem": "Chamado criado com sucesso!"
                    })
                
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "success": "Chamado criado com sucesso!",
                        "versao": "3.1.2"
                    }
                )
            except HTTPException as e:
                logger.error(f"[criar_chamado] Erro HTTP ao criar chamado: {str(e.detail)}")
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "error": str(e.detail),
                        "versao": "3.1.2"
                    }
                )
            except Exception as e:
                logger.error(f"[criar_chamado] Erro inesperado ao criar chamado: {str(e)}")
                import traceback
                logger.debug(f"[criar_chamado] Traceback: {traceback.format_exc()}")
                return templates.TemplateResponse(
                    "chamado.html",
                    {
                        "request": request,
                        "dados": dados_funcionario.model_dump(),
                        "user": user,
                        "error": f"Erro inesperado: {str(e)}",
                        "versao": "3.1.2"
                    }
                )
        
    except ValueError as e:
        logger.error(f"Erro ao buscar dados do funcionário: {str(e)}")
        return templates.TemplateResponse(
            "chamado.html",
            {
                "request": request,
                "dados": None,
                "user": user,
                "error": f"Erro ao carregar dados do funcionário: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        return templates.TemplateResponse(
            "chamado.html",
            {
                "request": request,
                "dados": None,
                "user": user,
                "error": f"Erro inesperado: {str(e)}",
                "versao": "3.1.2"
            }
        )


@router.post("/chamado/carregar-planilha", response_class=JSONResponse)
async def carregar_planilha(request: Request, planilha: UploadFile = File(...)):
    """
    Carrega a planilha e cria o temp.txt imediatamente após o upload
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"erro": "Usuário não autenticado", "sucesso": False}
        )
    
    if not planilha.filename.endswith('.xlsx'):
        return JSONResponse(
            status_code=400,
            content={"erro": "Apenas arquivos .xlsx são suportados.", "sucesso": False}
        )
    
    try:
        # Salvar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await planilha.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Processar planilha e criar temp.txt
            planilha_obj = Planilha(tmp_path)
            planilha_obj.carregar_planilha()  # Isso já cria o temp.txt vazio
            linhas_processadas = planilha_obj.criar_base_chamados()  # Isso preenche o temp.txt
            
            # Limpar arquivo temporário da planilha (mas manter temp.txt)
            os.unlink(tmp_path)
            
            if not linhas_processadas:
                return JSONResponse(
                    status_code=400,
                    content={
                        "erro": "Erro ao processar planilha. Verifique o formato do arquivo.",
                        "sucesso": False
                    }
                )
            
            return JSONResponse(
                content={
                    "sucesso": True,
                    "mensagem": f"Planilha carregada com sucesso! {linhas_processadas} linha(s) processada(s).",
                    "linhas_processadas": linhas_processadas
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar planilha: {str(e)}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return JSONResponse(
                status_code=500,
                content={
                    "erro": f"Erro ao processar planilha: {str(e)}",
                    "sucesso": False
                }
            )
            
    except Exception as e:
        logger.error(f"Erro ao carregar planilha: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "erro": f"Erro ao carregar planilha: {str(e)}",
                "sucesso": False
            }
        )


class PreviewRequest(BaseModel):
    """Modelo para requisição de prévia"""
    titulo: str
    descricao: str
    solicitante: Optional[str] = None
    qtd_chamados: int = 5
    ignorar_primeira_linha: bool = True


@router.post("/chamado/preview", response_class=JSONResponse)
async def preview_chamados(request: Request, preview_data: PreviewRequest):
    """
    Gera prévia dos chamados com placeholders substituídos
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"erro": "Usuário não autenticado"}
        )
    
    email = user.get('email')
    if not email:
        return JSONResponse(
            status_code=401,
            content={"erro": "Email não encontrado na sessão"}
        )
    
    try:
        # Verificar se temp.txt existe
        if not os.path.exists(PATH_TO_TEMP):
            return JSONResponse(
                status_code=400,
                content={
                    "erro": "Arquivo temp.txt não encontrado. Faça upload da planilha primeiro.",
                    "preview": []
                }
            )
        
        # Usar o módulo AbrirChamados para processar
        abrir_chamados = AbrirChamados(email)
        
        if not abrir_chamados.carregar_dados_temp():
            return JSONResponse(
                status_code=400,
                content={
                    "erro": "Erro ao carregar dados do temp.txt",
                    "preview": []
                }
            )
        
        # Obter seções disponíveis
        secoes = sorted(
            [int(s) for s in abrir_chamados.config_planilha.sections() if s.isdigit()],
            key=int
        )
        
        if not secoes:
            return JSONResponse(
                status_code=400,
                content={
                    "erro": "Nenhuma linha válida encontrada no temp.txt",
                    "preview": []
                }
            )
        
        # Se ignorar_primeira_linha for True, remover a primeira seção (cabeçalho)
        if preview_data.ignorar_primeira_linha and secoes:
            primeira_secao = min(secoes)
            secoes = [s for s in secoes if s != primeira_secao]
        
        # Limitar quantidade
        qtd = min(preview_data.qtd_chamados, len(secoes))
        secoes_processar = secoes[:qtd]
        
        preview_items = []
        
        # Processar cada linha
        for numero_linha in secoes_processar:
            linha_str = str(numero_linha)
            resultado = abrir_chamados.processar_chamado(
                preview_data.titulo,
                preview_data.descricao,
                linha_str,
                solicitante=preview_data.solicitante
            )
            
            if 'erro' in resultado:
                preview_items.append({
                    'linha': numero_linha,
                    'titulo': preview_data.titulo,
                    'descricao': preview_data.descricao,
                    'solicitante': preview_data.solicitante or '',
                    'erro': resultado['erro']
                })
            else:
                preview_items.append({
                    'linha': numero_linha,
                    'titulo': resultado['titulo'],
                    'descricao': resultado['descricao'],
                    'solicitante': resultado.get('solicitante', ''),
                    'erro': None
                })
        
        return JSONResponse(
            content={
                "sucesso": True,
                "total_linhas": len(secoes),
                "preview": preview_items
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar prévia: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "erro": f"Erro ao gerar prévia: {str(e)}",
                "preview": []
            }
        )


@router.get("/listar_servicos", response_class=JSONResponse)
async def listar_servicos():
    """
    Retorna a lista de serviços do arquivo servicos_prd.json
    Endpoint interno sem autenticação para uso no webapp
    """
    try:
        # Caminho relativo ao diretório raiz do projeto
        # __file__ está em src/rotas/webapp/rt_chamado.py
        # Precisamos subir 3 níveis para chegar em src/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "json", "servicos_prd.json")
        
        if not os.path.exists(json_path):
            logger.error(f"Arquivo de serviços não encontrado: {json_path}")
            return JSONResponse(
                status_code=404,
                content={"sucesso": False, "erro": "Arquivo de serviços não encontrado"}
            )
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Retornar os serviços com os campos necessários
        if data.get('content') and isinstance(data['content'], list):
            servicos = []
            for servico in data['content']:
                servicos.append({
                    'servico': servico.get('servico', ''),
                    'documentid': str(servico.get('documentid', '')),
                    'grupo_servico': servico.get('grupo_servico', ''),
                    'item_servico': servico.get('item_servico', ''),
                    'numero_documento': str(servico.get('documentid', ''))
                })
            
            logger.info(f"[listar_servicos] {len(servicos)} serviços retornados")
            return JSONResponse(content={"sucesso": True, "servicos": servicos})
        else:
            return JSONResponse(
                status_code=500,
                content={"sucesso": False, "erro": "Formato inválido do arquivo de serviços"}
            )
            
    except Exception as e:
        logger.error(f"Erro ao carregar serviços: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro ao carregar serviços: {str(e)}"}
        )


class BuscarServicoRequest(BaseModel):
    """Modelo para requisição de busca de serviço"""
    nome_servico: str


class BuscarDetalhesServicoRequest(BaseModel):
    """Modelo para requisição de busca de detalhes de serviço por documentid"""
    documentid: str


@router.post("/buscar_servico", response_class=JSONResponse)
async def buscar_servico(request: Request, busca: BuscarServicoRequest):
    """
    Busca os detalhes de um serviço pelo nome
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    try:
        # Primeiro, buscar o documentid do serviço no arquivo servicos_prd.json
        # __file__ está em src/rotas/webapp/rt_chamado.py
        # Precisamos subir 3 níveis para chegar em src/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_dir, "json", "servicos_prd.json")
        
        if not os.path.exists(json_path):
            return JSONResponse(
                status_code=404,
                content={"sucesso": False, "erro": "Arquivo de serviços não encontrado"}
            )
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Encontrar o serviço pelo nome
        servico_encontrado = None
        if data.get('content') and isinstance(data['content'], list):
            for servico in data['content']:
                if servico.get('servico', '').strip() == busca.nome_servico.strip():
                    servico_encontrado = servico
                    break
        
        if not servico_encontrado:
            return JSONResponse(
                status_code=404,
                content={"sucesso": False, "erro": "Serviço não encontrado"}
            )
        
        documentid = str(servico_encontrado.get('documentid', ''))
        
        # Buscar detalhes do serviço usando a API interna
        base_url = str(request.base_url).rstrip('/')
        headers = {
            ConfigEnvSetings.API_NAME: ConfigEnvSetings.API_KEY
        }
        
        response = requests.post(
            f"{base_url}/api/v1/fluig/prd/servicos/detalhes",
            json={"id_servico": documentid},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            detalhes = response.json()
            
            # Processar resposta do serviço
            servico_data = None
            if detalhes.get('content') and detalhes['content'].get('values'):
                servico_data = detalhes['content']['values'][0]
            elif detalhes.get('values'):
                servico_data = detalhes['values'][0]
            else:
                servico_data = detalhes
            
            if servico_data:
                # Retornar dados formatados
                return JSONResponse(content={
                    "sucesso": True,
                    "servico": {
                        "servico": servico_data.get('servico', ''),
                        "documentid": str(servico_data.get('documentid', '')),
                        "grupo_servico": servico_data.get('grupo_servico', ''),
                        "item_servico": servico_data.get('item_servico', ''),
                        "urgencia_alta": servico_data.get('urgencia_alta', ''),
                        "urgencia_media": servico_data.get('urgencia_media', ''),
                        "urgencia_baixa": servico_data.get('urgencia_baixa', ''),
                        "ds_responsavel": servico_data.get('ds_responsavel', ''),
                        "equipe_executante": servico_data.get('equipe_executante', ''),
                        "impacto": servico_data.get('impacto', '')
                    }
                })
            else:
                return JSONResponse(
                    status_code=500,
                    content={"sucesso": False, "erro": "Dados do serviço não encontrados"}
                )
        else:
            return JSONResponse(
                status_code=response.status_code,
                content={"sucesso": False, "erro": f"Erro ao buscar detalhes do serviço: {response.text}"}
            )
            
    except Exception as e:
        logger.error(f"Erro ao buscar serviço: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro ao buscar serviço: {str(e)}"}
        )


@router.post("/buscar_detalhes_servico", response_class=JSONResponse)
async def buscar_detalhes_servico(request: Request, busca: BuscarDetalhesServicoRequest):
    """
    Busca os detalhes de um serviço por documentid.
    Primeiro verifica se o arquivo JSON já existe localmente.
    Se não existir, busca da API e salva o arquivo.
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    try:
        documentid = busca.documentid.strip()
        if not documentid:
            return JSONResponse(
                status_code=400,
                content={"sucesso": False, "erro": "DocumentID não fornecido"}
            )
        
        # Caminho do arquivo JSON local (na pasta services/)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        services_path = os.path.join(base_dir, "json", "services", f"servico_detalhes_{documentid}_prd.json")
        
        # Verificar se o arquivo já existe na pasta services/
        if os.path.exists(services_path):
            logger.info(f"[buscar_detalhes_servico] Arquivo local encontrado: {services_path}")
            with open(services_path, 'r', encoding='utf-8') as f:
                detalhes = json.load(f)
            
            # Processar resposta do serviço
            servico_data = None
            if detalhes.get('content') and detalhes['content'].get('values'):
                servico_data = detalhes['content']['values'][0]
            elif detalhes.get('values'):
                servico_data = detalhes['values'][0]
            else:
                servico_data = detalhes
            
            if servico_data:
                return JSONResponse(content={
                    "sucesso": True,
                    "servico": {
                        "servico": servico_data.get('servico', ''),
                        "documentid": str(servico_data.get('documentid', '')),
                        "grupo_servico": servico_data.get('grupo_servico', ''),
                        "item_servico": servico_data.get('item_servico', ''),
                        "urgencia_alta": servico_data.get('urgencia_alta', ''),
                        "urgencia_media": servico_data.get('urgencia_media', ''),
                        "urgencia_baixa": servico_data.get('urgencia_baixa', ''),
                        "ds_responsavel": servico_data.get('ds_responsavel', ''),
                        "equipe_executante": servico_data.get('equipe_executante', ''),
                        "impacto": servico_data.get('impacto', '')
                    },
                    "fonte": "local"
                })
        
        # Se o arquivo não existe, buscar diretamente da função (sem requisição HTTP interna)
        logger.info(f"[buscar_detalhes_servico] Arquivo local não encontrado, buscando do Fluig: {documentid}")
        
        try:
            ambiente = "PRD"
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
            
            # Obter cookies válidos
            cookies = obter_cookies_validos(ambiente, forcar_login=False, usuario=usuario, senha=senha)
            
            if not cookies:
                logger.error("[buscar_detalhes_servico] Falha ao obter autenticação válida")
                return JSONResponse(
                    status_code=500,
                    content={
                        "sucesso": False,
                        "erro": "Falha ao obter autenticação válida no Fluig"
                    }
                )
            
            # Buscar detalhes diretamente da função
            detalhes = obter_detalhes_servico_fluig(
                document_id=documentid,
                ambiente=ambiente,
                cookies_list=cookies
            )
            
            if not detalhes:
                logger.error("[buscar_detalhes_servico] Falha ao obter detalhes do serviço")
                return JSONResponse(
                    status_code=500,
                    content={
                        "sucesso": False,
                        "erro": "Falha ao obter detalhes do serviço do Fluig"
                    }
                )
            
            # Salvar o arquivo JSON
            logger.info(f"[buscar_detalhes_servico] Salvando detalhes em JSON...")
            arquivo_salvo = salvar_detalhes_servico_json(detalhes, documentid, ambiente)
            logger.info(f"[buscar_detalhes_servico] Detalhes salvos em: {arquivo_salvo}")
            
            # Processar resposta do serviço
            servico_data = None
            if detalhes.get('content') and detalhes['content'].get('values'):
                servico_data = detalhes['content']['values'][0]
            elif detalhes.get('values'):
                servico_data = detalhes['values'][0]
            else:
                servico_data = detalhes
            
            if servico_data:
                return JSONResponse(content={
                    "sucesso": True,
                    "servico": {
                        "servico": servico_data.get('servico', ''),
                        "documentid": str(servico_data.get('documentid', '')),
                        "grupo_servico": servico_data.get('grupo_servico', ''),
                        "item_servico": servico_data.get('item_servico', ''),
                        "urgencia_alta": servico_data.get('urgencia_alta', ''),
                        "urgencia_media": servico_data.get('urgencia_media', ''),
                        "urgencia_baixa": servico_data.get('urgencia_baixa', ''),
                        "ds_responsavel": servico_data.get('ds_responsavel', ''),
                        "equipe_executante": servico_data.get('equipe_executante', ''),
                        "impacto": servico_data.get('impacto', '')
                    },
                    "fonte": "api"
                })
            else:
                return JSONResponse(
                    status_code=500,
                    content={"sucesso": False, "erro": "Dados do serviço não encontrados na resposta"}
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[buscar_detalhes_servico] Erro ao buscar detalhes do serviço {documentid}: {str(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "sucesso": False,
                    "erro": f"Erro ao buscar detalhes do serviço: {str(e)}"
                }
            )
            
    except Exception as e:
        logger.error(f"[buscar_detalhes_servico] Erro inesperado ao buscar detalhes do serviço: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "sucesso": False,
                "erro": f"Erro inesperado ao buscar detalhes do serviço: {str(e)}"
            }
        )

