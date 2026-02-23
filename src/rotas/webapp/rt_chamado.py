from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict
from pydantic import BaseModel
from src.modelo_dados.modelo_sites import DadosFuncionario, DadosFuncionarioForm, DadosChamado, PayloadFuncionario
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificado
import requests
from datetime import datetime, timedelta
from src.utilitarios_centrais.logger import logger
from src.site.planilha import Planilha, PATH_TO_TEMP, obter_caminho_temp_por_email
from src.site.abrir_chamados import AbrirChamados
from src.fluig.fluig_core import FluigCore
from src.web.web_servicos_fluig import obter_detalhes_servico_fluig
from src.utilitarios_centrais.json_utils import salvar_detalhes_servico_json
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.configs.user_template_manager import get_user_template_manager
import os
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

router = APIRouter()
templates = Jinja2Templates(directory="src/site/templates")

# ==================== SISTEMA DE CACHE ====================
# Cache em memória para chamados
_chamados_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()
CACHE_TTL_MINUTES = 5  # Cache válido por 5 minutos

def _gerar_chave_cache(tipo: str, identificador: str) -> str:
    """Gera chave única para o cache"""
    return f"{tipo}:{identificador}"

def _obter_do_cache(chave: str) -> Optional[Dict]:
    """Obtém dados do cache se ainda válidos"""
    with _cache_lock:
        if chave not in _chamados_cache:
            return None
        
        cache_entry = _chamados_cache[chave]
        agora = datetime.now()
        
        # Verifica se cache expirou
        if agora > cache_entry['expira_em']:
            del _chamados_cache[chave]
            logger.debug(f"[Cache] Cache expirado para chave: {chave}")
            return None
        
        logger.debug(f"[Cache] Cache hit para chave: {chave}")
        return cache_entry['dados']

def _salvar_no_cache(chave: str, dados: Dict):
    """Salva dados no cache com TTL"""
    with _cache_lock:
        expira_em = datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)
        _chamados_cache[chave] = {
            'dados': dados,
            'expira_em': expira_em,
            'criado_em': datetime.now()
        }
        logger.debug(f"[Cache] Dados salvos no cache para chave: {chave} (expira em {CACHE_TTL_MINUTES} minutos)")

def _limpar_cache_expirado():
    """Remove entradas expiradas do cache (limpeza periódica)"""
    with _cache_lock:
        agora = datetime.now()
        chaves_remover = [
            chave for chave, entry in _chamados_cache.items()
            if agora > entry['expira_em']
        ]
        for chave in chaves_remover:
            del _chamados_cache[chave]
        if chaves_remover:
            logger.debug(f"[Cache] Removidas {len(chaves_remover)} entradas expiradas do cache")

# ==================== BUSCA PARALELA DE DETALHES ====================
def _buscar_detalhes_paralelo(fluig_core: FluigCore, items: list, max_workers: int = 10) -> list:
    """
    Busca detalhes de múltiplos chamados em paralelo usando ThreadPoolExecutor
    
    Args:
        fluig_core: Instância de FluigCore
        items: Lista de itens de chamados (com processInstanceId)
        max_workers: Número máximo de threads paralelas (padrão: 10)
    
    Returns:
        Lista de chamados com detalhes completos
    """
    chamados_detalhados = []
    
    def buscar_detalhe(item):
        """Função auxiliar para buscar detalhes de um chamado"""
        process_instance_id = item.get('processInstanceId')
        if not process_instance_id:
            return None
        
        try:
            detalhes = fluig_core.obter_detalhes_chamado(
                process_instance_id=process_instance_id,
                usuario=ConfigEnvSetings.FLUIG_ADMIN_USER
            )
            return {
                'item': item,
                'detalhes': detalhes,
                'process_instance_id': process_instance_id,
                'sucesso': True
            }
        except Exception as e:
            logger.error(f"[_buscar_detalhes_paralelo] Erro ao buscar detalhes do chamado {process_instance_id}: {str(e)}")
            return {
                'item': item,
                'detalhes': None,
                'process_instance_id': process_instance_id,
                'sucesso': False,
                'erro': str(e)
            }
    
    # Executa buscas em paralelo
    logger.info(f"[_buscar_detalhes_paralelo] Iniciando busca paralela de {len(items)} chamado(s) com {max_workers} workers")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(buscar_detalhe, item): item for item in items}
        
        for future in as_completed(futures):
            resultado = future.result()
            if not resultado:
                continue
            
            item = resultado['item']
            detalhes = resultado['detalhes']
            process_instance_id = resultado['process_instance_id']
            
            if detalhes:
                chamado_completo = {
                    "processInstanceId": process_instance_id,
                    "processId": item.get('processId', ''),
                    "processDescription": item.get('processDescription', ''),
                    "status": item.get('status', ''),
                    "slaStatus": item.get('slaStatus', ''),
                    "startDate": item.get('startDate', ''),
                    "assignStartDate": item.get('assignStartDate', ''),
                    "requester": item.get('requester', {}),
                    "assignee": item.get('assignee', {}),
                    "state": item.get('state', {}),
                    "detalhes": detalhes
                }
            else:
                # Se não conseguir detalhes, retorna pelo menos os dados básicos
                chamado_completo = {
                    "processInstanceId": process_instance_id,
                    "processId": item.get('processId', ''),
                    "processDescription": item.get('processDescription', ''),
                    "status": item.get('status', ''),
                    "slaStatus": item.get('slaStatus', ''),
                    "startDate": item.get('startDate', ''),
                    "assignStartDate": item.get('assignStartDate', ''),
                    "requester": item.get('requester', {}),
                    "assignee": item.get('assignee', {}),
                    "state": item.get('state', {}),
                    "detalhes": None
                }
            
            chamados_detalhados.append(chamado_completo)
    
    logger.info(f"[_buscar_detalhes_paralelo] Busca paralela concluída: {len(chamados_detalhados)} chamado(s) processado(s)")
    return chamados_detalhados


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


def buscar_colleague_id(email: str, ambiente: str = "PRD") -> Optional[str]:
    """
    Busca o colleagueId pelo email usando o dataset colleague
    
    Args:
        email: Email do funcionário
        ambiente: Ambiente do Fluig (PRD ou QLD), padrão PRD
    
    Returns:
        colleagueId ou None se não encontrar
    """
    if not email or not email.strip():
        return None
    
    email = email.strip()
    
    try:
        logger.info(f"[buscar_colleague_id] Buscando colleagueId - Email: {email}, Ambiente: {ambiente}")
        
        fluig_core = FluigCore(ambiente=ambiente)
        resultado = fluig_core.Dataset_config(dataset_id="colleague", user=email)
        
        # Verificar se a resposta é um objeto Response (erro HTTP)
        if hasattr(resultado, 'status_code'):
            logger.warning(f"[buscar_colleague_id] Erro HTTP {resultado.status_code} ao buscar colleague")
            return None
        
        # Verificar se a resposta é um dicionário com content
        if not resultado or not isinstance(resultado, dict):
            logger.warning(f"[buscar_colleague_id] Resposta inválida do dataset: {type(resultado)}")
            return None
        
        content = resultado.get('content', [])
        if isinstance(content, list) and len(content) > 0:
            colleague_data = content[0]
        elif isinstance(content, dict) and 'values' in content:
            values = content.get('values', [])
            if values and len(values) > 0:
                colleague_data = values[0]
            else:
                logger.warning(f"[buscar_colleague_id] Nenhum colleague encontrado para: {email}")
                return None
        else:
            logger.warning(f"[buscar_colleague_id] Nenhum colleague encontrado para: {email}")
            return None
        
        colleague_id = colleague_data.get('colleagueId', '')
        if colleague_id:
            logger.info(f"[buscar_colleague_id] colleagueId encontrado: {colleague_id}")
            return colleague_id
        else:
            logger.warning(f"[buscar_colleague_id] colleagueId não encontrado no resultado")
            return None
            
    except Exception as e:
        logger.warning(f"[buscar_colleague_id] Erro ao buscar colleagueId: {str(e)}")
        return None


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
        funcionario = buscar_funcionario(email, ambiente="PRD", obrigatorio=True)
        
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
                "user": user
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
                "error": f"Erro inesperado ao processar a solicitação: {str(e)}"
            }
        )


@router.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes(request: Request):
    """Página de configurações"""
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url="/login")
    
    # Verificar se o usuário tem permissão (apenas nathan.azevedo@uisa.com.br)
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    
    if user_email != email_permitido:
        return templates.TemplateResponse(
            "configuracoes.html",
            {
                "request": request,
                "user": user,
                "configs": {},
                "sem_permissao": True
            }
        )
    
    # Carregar primeira configuração salva (configurações globais)
    from src.configs.config_manager import get_config_manager
    config_manager = get_config_manager()
    configs = config_manager.carregar_configuracao()
    
    return templates.TemplateResponse(
        "configuracoes.html",
        {
            "request": request,
            "user": user,
            "configs": configs,
            "sem_permissao": False
        }
    )


@router.post("/configuracoes/salvar", response_class=JSONResponse)
async def salvar_configuracoes(
    request: Request,
    email_solicitante: str = Form(None),
    usuario_responsavel: str = Form(None),
    servico_id: str = Form(None),
    servico: str = Form(None),
    ds_grupo_servico: str = Form(None),
    item_servico: str = Form(None),
    urg_alta: str = Form(None),
    urg_media: str = Form(None),
    urg_baixa: str = Form(None),
    ds_resp_servico: str = Form(None),
    ds_tipo: str = Form(None),
    ds_urgencia: str = Form(None),
    equipe_responsavel: str = Form(None),
    status: str = Form(None),
    solicitante: str = Form(None)
):
    """Salva as configurações de personalização de chamado (configurações globais)"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    # Valida se o email_solicitante foi fornecido (obrigatório para identificar a configuração)
    if not email_solicitante or not email_solicitante.strip():
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "erro": "Email solicitante é obrigatório para salvar a configuração"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        sucesso = config_manager.salvar_configuracao(
            email_solicitante=email_solicitante,
            usuario_responsavel=usuario_responsavel,
            servico_id=servico_id,
            servico=servico,
            ds_grupo_servico=ds_grupo_servico,
            item_servico=item_servico,
            urg_alta=urg_alta,
            urg_media=urg_media,
            urg_baixa=urg_baixa,
            ds_resp_servico=ds_resp_servico,
            ds_tipo=ds_tipo,
            ds_urgencia=ds_urgencia,
            equipe_responsavel=equipe_responsavel,
            status=status,
            solicitante=solicitante
        )
        
        if sucesso:
            return JSONResponse(
                content={"sucesso": True, "mensagem": "Configurações salvas com sucesso!"}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"sucesso": False, "erro": "Erro ao salvar configurações"}
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Erro ao salvar configurações: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.get("/configuracoes/carregar", response_class=JSONResponse)
async def carregar_configuracoes(request: Request, email: Optional[str] = None):
    """Carrega as configurações salvas (configurações globais)"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager
        config_manager = get_config_manager()
        # Se email fornecido na query, carrega configuração específica, senão carrega a primeira
        configs = config_manager.carregar_configuracao(email)
        
        return JSONResponse(
            content={"sucesso": True, "configs": configs}
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Erro ao carregar configurações: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.get("/configuracoes/listar", response_class=JSONResponse)
async def listar_configuracoes(request: Request):
    """Lista todas as configurações salvas (apenas email e serviço)"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager
        config_manager = get_config_manager()
        lista_configs = config_manager.listar_todas_configuracoes()
        
        return JSONResponse(
            content={"sucesso": True, "configuracoes": lista_configs}
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Erro ao listar configurações: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.delete("/configuracoes/excluir", response_class=JSONResponse)
async def excluir_configuracao(request: Request, email: Optional[str] = None):
    """Exclui uma configuração salva"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    # Obter email da query string se não foi fornecido como parâmetro
    if not email:
        email = request.query_params.get('email')
    
    if not email or not email.strip():
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "erro": "Email é obrigatório para excluir a configuração"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager
        config_manager = get_config_manager()
        sucesso = config_manager.excluir_configuracao(email.strip())
        
        if sucesso:
            return JSONResponse(
                content={"sucesso": True, "mensagem": "Configuração excluída com sucesso!"}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"sucesso": False, "erro": "Configuração não encontrada"}
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Erro ao excluir configuração: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.get("/configuracoes/gerais/carregar", response_class=JSONResponse)
async def carregar_configuracoes_gerais(request: Request):
    """Carrega as configurações gerais do sistema"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        configs = config_manager.carregar_configuracao()
        
        return JSONResponse(
            content={"sucesso": True, "configs": configs}
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Erro ao carregar configurações gerais: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.post("/configuracoes/gerais/salvar", response_class=JSONResponse)
async def salvar_configuracoes_gerais(
    request: Request,
    gmail_check_interval: int = Form(None),
    gmail_monitor_enabled: str = Form(None),
    black_list_emails: str = Form(None),
    emails_list: str = Form(None),
    historico_check_interval_minutes: float = Form(None),
    historico_check_interval_hours: float = Form(None),
    historico_monitor_enabled: str = Form(None),
    historico_exclude_emails: str = Form(None),
    email_deduplication_patterns: str = Form(None),
    email_deduplication_emails: str = Form(None)
):
    """Salva as configurações gerais do sistema"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    try:
        from src.configs.config_manager import get_config_manager_gerais
        config_manager = get_config_manager_gerais()
        
        sucesso = config_manager.salvar_configuracao(
            gmail_check_interval=gmail_check_interval,
            gmail_monitor_enabled=gmail_monitor_enabled,
            black_list_emails=black_list_emails,
            emails_list=emails_list,
            historico_check_interval_minutes=historico_check_interval_minutes,
            historico_check_interval_hours=historico_check_interval_hours,
            historico_monitor_enabled=historico_monitor_enabled,
            historico_exclude_emails=historico_exclude_emails,
            email_deduplication_patterns=email_deduplication_patterns,
            email_deduplication_emails=email_deduplication_emails
        )
        
        if sucesso:
            # Reinicia os serviços para aplicar as novas configurações
            try:
                from src.gmail_monitor.background_service import reiniciar_monitoramento_gmail
                from src.historico_monitor.background_service import reiniciar_monitoramento_historico
                
                logger.info("[salvar_configuracoes_gerais] Reiniciando serviços para aplicar novas configurações...")
                reiniciar_monitoramento_gmail()
                reiniciar_monitoramento_historico()
                logger.info("[salvar_configuracoes_gerais] Serviços reiniciados com sucesso")
            except Exception as e:
                logger.warning(f"[salvar_configuracoes_gerais] Erro ao reiniciar serviços: {str(e)} - configurações salvas mas serviços não reiniciados")
                # Não falha o salvamento se houver erro ao reiniciar
            
            return JSONResponse(
                content={"sucesso": True, "mensagem": "Configurações gerais salvas com sucesso! Serviços reiniciados para aplicar as mudanças."}
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"sucesso": False, "erro": "Erro ao salvar configurações gerais"}
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Erro ao salvar configurações gerais: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
        )


@router.post("/configuracoes/gerais/reiniciar-servicos", response_class=JSONResponse)
async def reiniciar_servicos_background(request: Request):
    """Reinicia os serviços em background (Gmail Monitor e Histórico Monitor) para aplicar novas configurações"""
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Verificar permissão
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        return JSONResponse(
            status_code=403,
            content={"sucesso": False, "erro": "Permissão negada: apenas usuários autorizados podem acessar esta funcionalidade"}
        )
    
    try:
        from src.gmail_monitor.background_service import reiniciar_monitoramento_gmail
        from src.historico_monitor.background_service import reiniciar_monitoramento_historico
        
        logger.info("[reiniciar_servicos_background] Reiniciando serviços em background...")
        
        # Reinicia Gmail Monitor
        try:
            reiniciar_monitoramento_gmail()
            logger.info("[reiniciar_servicos_background] Gmail Monitor reiniciado com sucesso")
        except Exception as e:
            logger.error(f"[reiniciar_servicos_background] Erro ao reiniciar Gmail Monitor: {str(e)}")
        
        # Reinicia Histórico Monitor
        try:
            reiniciar_monitoramento_historico()
            logger.info("[reiniciar_servicos_background] Histórico Monitor reiniciado com sucesso")
        except Exception as e:
            logger.error(f"[reiniciar_servicos_background] Erro ao reiniciar Histórico Monitor: {str(e)}")
        
        return JSONResponse(
            content={
                "sucesso": True, 
                "mensagem": "Serviços reiniciados com sucesso! As novas configurações foram aplicadas."
            }
        )
        
    except Exception as e:
        import traceback
        logger.error(f"[reiniciar_servicos_background] Erro ao reiniciar serviços: {str(e)}")
        logger.debug(f"[reiniciar_servicos_background] Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"sucesso": False, "erro": f"Erro inesperado: {str(e)}"}
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
        funcionario = buscar_funcionario(email, ambiente="PRD", obrigatorio=True)
        
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
                    "error": error_msg
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
                        "error": "Apenas arquivos .xlsx são suportados."
                    }
                )
            
            # Salvar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                content = await planilha.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Processar planilha
                planilha_obj = Planilha(tmp_path, email)
                linhas_processadas = planilha_obj.criar_base_chamados()
                
                if not linhas_processadas:
                    os.unlink(tmp_path)
                    return templates.TemplateResponse(
                        "chamado.html",
                        {
                            "request": request,
                            "dados": dados_funcionario.model_dump(),
                            "user": user,
                            "error": "Erro ao processar planilha. Verifique o formato do arquivo."
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
                        "success": mensagem
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
                        "error": f"Erro ao processar planilha: {str(e)}"
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
                        "success": "Chamado criado com sucesso!"
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
                        "error": str(e.detail)
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
                        "error": f"Erro inesperado: {str(e)}"
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
                "error": f"Erro inesperado: {str(e)}"
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
            email = user.get('email')
            planilha_obj = Planilha(tmp_path, email)
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
        # Usar o módulo AbrirChamados para processar
        abrir_chamados = AbrirChamados(email)
        
        # Verificar se temp.txt existe (usando caminho baseado no email)
        path_to_temp = obter_caminho_temp_por_email(email)
        if not os.path.exists(path_to_temp):
            return JSONResponse(
                status_code=400,
                content={
                    "erro": "Arquivo temp.txt não encontrado. Faça upload da planilha primeiro.",
                    "preview": []
                }
            )
        
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
            
            # Buscar detalhes usando OAuth 1.0
            logger.info("[buscar_detalhes_servico] Buscando detalhes usando OAuth 1.0...")
            detalhes = obter_detalhes_servico_fluig(
                document_id=documentid,
                ambiente=ambiente
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


@router.get("/api/chamados/fila")
async def obter_chamados_fila(request: Request):
    """
    Retorna a lista de chamados da fila do usuário logado
    Segue o fluxo: email -> colleagueId -> listar chamados -> detalhes de cada chamado
    Utiliza cache para melhorar performance
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    email = user.get('email')
    if not email:
        return JSONResponse(
            status_code=400,
            content={"sucesso": False, "erro": "Email do usuário não encontrado"}
        )
    
    # Limpar cache expirado periodicamente
    _limpar_cache_expirado()
    
    # Verificar cache
    chave_cache = _gerar_chave_cache('fila', email)
    dados_cache = _obter_do_cache(chave_cache)
    
    if dados_cache:
        logger.info(f"[obter_chamados_fila] Retornando dados do cache para {email}")
        return JSONResponse(
            status_code=200,
            content=dados_cache
        )
    
    try:
        ambiente = "PRD"
        
        # 1. Buscar colleagueId pelo email
        logger.info(f"[obter_chamados_fila] Buscando colleagueId para email: {email}")
        colleague_id = buscar_colleague_id(email, ambiente)
        
        if not colleague_id:
            logger.warning(f"[obter_chamados_fila] colleagueId não encontrado para: {email}")
            resposta_vazia = {"sucesso": True, "chamados": [], "erro": "ColleagueId não encontrado para o usuário"}
            _salvar_no_cache(chave_cache, resposta_vazia)
            return JSONResponse(
                status_code=200,
                content=resposta_vazia
            )
        
        logger.info(f"[obter_chamados_fila] colleagueId encontrado: {colleague_id}")
        
        # 2. Listar chamados usando o colleagueId
        logger.info(f"[obter_chamados_fila] Listando chamados para colleagueId: {colleague_id}")
        fluig_core = FluigCore(ambiente=ambiente)
        chamados_lista = fluig_core.listar_chamados_tasks(
            assignee=colleague_id,
            usuario=ConfigEnvSetings.FLUIG_ADMIN_USER
        )
        
        if not chamados_lista:
            logger.info(f"[obter_chamados_fila] listar_chamados_tasks retornou None ou vazio")
            resposta_vazia = {"sucesso": True, "chamados": []}
            _salvar_no_cache(chave_cache, resposta_vazia)
            return JSONResponse(
                status_code=200,
                content=resposta_vazia
            )
        
        items = chamados_lista.get('items', [])
        if not items:
            resposta_vazia = {"sucesso": True, "chamados": []}
            _salvar_no_cache(chave_cache, resposta_vazia)
            return JSONResponse(
                status_code=200,
                content=resposta_vazia
            )
        
        logger.info(f"[obter_chamados_fila] {len(items)} chamado(s) encontrado(s)")
        
        # 3. Buscar detalhes de cada chamado em paralelo
        chamados_detalhados = _buscar_detalhes_paralelo(fluig_core, items, max_workers=10)
        
        logger.info(f"[obter_chamados_fila] {len(chamados_detalhados)} chamado(s) processado(s) com sucesso")
        
        resposta = {
            "sucesso": True,
            "chamados": chamados_detalhados,
            "total": len(chamados_detalhados)
        }
        
        # Salvar no cache antes de retornar
        _salvar_no_cache(chave_cache, resposta)
        
        return JSONResponse(
            status_code=200,
            content=resposta
        )
        
    except Exception as e:
        logger.error(f"[obter_chamados_fila] Erro ao obter chamados: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "sucesso": False,
                "erro": f"Erro ao obter chamados: {str(e)}"
            }
        )


@router.get("/api/chamados/grupo-itsm-todos")
async def obter_chamados_grupo_itsm_todos(request: Request):
    """
    Retorna a lista de chamados do grupo Pool:Group:ITSM_TODOS
    Com filtros: status=NOT_COMPLETED e slaStatus=ON_TIME
    Utiliza cache para melhorar performance
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(
            status_code=401,
            content={"sucesso": False, "erro": "Usuário não autenticado"}
        )
    
    # Limpar cache expirado periodicamente
    _limpar_cache_expirado()
    
    # Verificar cache (chave fixa para grupo)
    chave_cache = _gerar_chave_cache('grupo', 'ITSM_TODOS')
    dados_cache = _obter_do_cache(chave_cache)
    
    if dados_cache:
        logger.info(f"[obter_chamados_grupo_itsm_todos] Retornando dados do cache")
        return JSONResponse(
            status_code=200,
            content=dados_cache
        )
    
    try:
        ambiente = "PRD"
        assignee_grupo = "Pool:Group:ITSM_TODOS"
        
        # Listar chamados do grupo ITSM_TODOS
        logger.info(f"[obter_chamados_grupo_itsm_todos] Listando chamados do grupo: {assignee_grupo}")
        fluig_core = FluigCore(ambiente=ambiente)
        chamados_lista = fluig_core.listar_chamados_tasks(
            assignee=assignee_grupo,
            status="NOT_COMPLETED",
            sla_status="ON_TIME",
            usuario=ConfigEnvSetings.FLUIG_ADMIN_USER
        )
        
        if not chamados_lista:
            logger.info(f"[obter_chamados_grupo_itsm_todos] listar_chamados_tasks retornou None ou vazio")
            resposta_vazia = {"sucesso": True, "chamados": []}
            _salvar_no_cache(chave_cache, resposta_vazia)
            return JSONResponse(
                status_code=200,
                content=resposta_vazia
            )
        
        items = chamados_lista.get('items', [])
        if not items:
            resposta_vazia = {"sucesso": True, "chamados": []}
            _salvar_no_cache(chave_cache, resposta_vazia)
            return JSONResponse(
                status_code=200,
                content=resposta_vazia
            )
        
        logger.info(f"[obter_chamados_grupo_itsm_todos] {len(items)} chamado(s) encontrado(s)")
        
        # Buscar detalhes de cada chamado em paralelo
        chamados_detalhados = _buscar_detalhes_paralelo(fluig_core, items, max_workers=10)
        
        logger.info(f"[obter_chamados_grupo_itsm_todos] {len(chamados_detalhados)} chamado(s) processado(s) com sucesso")
        
        resposta = {
            "sucesso": True,
            "chamados": chamados_detalhados,
            "total": len(chamados_detalhados)
        }
        
        # Salvar no cache antes de retornar
        _salvar_no_cache(chave_cache, resposta)
        
        return JSONResponse(
            status_code=200,
            content=resposta
        )
        
    except Exception as e:
        logger.error(f"[obter_chamados_grupo_itsm_todos] Erro ao obter chamados: {str(e)}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "sucesso": False,
                "erro": f"Erro ao obter chamados: {str(e)}"
            }
        )


# ==================== ENDPOINTS DE TEMPLATES ====================

@router.post("/chamado/template/salvar", response_class=JSONResponse)
async def salvar_template_chamado(request: Request):
    """
    Salva um template de chamado (título e descrição) para o usuário logado
    """
    try:
        # Verifica se usuário está autenticado
        user = request.session.get('user')
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")
        
        email = user.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email do usuário não encontrado")
        
        # Obtém dados do corpo da requisição
        body = await request.json()
        nome_template = body.get('nome_template', '').strip()
        titulo = body.get('titulo', '').strip()
        descricao = body.get('descricao', '').strip()
        
        if not nome_template:
            raise HTTPException(status_code=400, detail="Nome do template é obrigatório")
        
        if not titulo and not descricao:
            raise HTTPException(status_code=400, detail="Título e descrição não podem estar vazios")
        
        # Salva template
        template_manager = get_user_template_manager()
        sucesso = template_manager.salvar_template(email, nome_template, titulo, descricao)
        
        if sucesso:
            return JSONResponse({
                "sucesso": True,
                "mensagem": "Template salvo com sucesso"
            })
        else:
            raise HTTPException(status_code=500, detail="Erro ao salvar template")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[salvar_template_chamado] Erro: {str(e)}")
        import traceback
        logger.debug(f"[salvar_template_chamado] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar template: {str(e)}")


@router.get("/chamado/template/carregar", response_class=JSONResponse)
async def carregar_template_chamado(request: Request, nome_template: Optional[str] = None):
    """
    Carrega um template de chamado (título e descrição) do usuário logado
    
    Query Parameters:
        nome_template: Nome do template a carregar (opcional)
    """
    try:
        # Verifica se usuário está autenticado
        user = request.session.get('user')
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")
        
        email = user.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email do usuário não encontrado")
        
        # Carrega template
        template_manager = get_user_template_manager()
        template = template_manager.carregar_template(email, nome_template)
        
        if template:
            return JSONResponse({
                "sucesso": True,
                "template": template
            })
        else:
            return JSONResponse({
                "sucesso": False,
                "mensagem": "Nenhum template encontrado",
                "template": None
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[carregar_template_chamado] Erro: {str(e)}")
        import traceback
        logger.debug(f"[carregar_template_chamado] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao carregar template: {str(e)}")


@router.get("/chamado/template/listar", response_class=JSONResponse)
async def listar_templates_chamado(request: Request):
    """
    Lista todos os templates de chamado do usuário logado
    """
    try:
        # Verifica se usuário está autenticado
        user = request.session.get('user')
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")
        
        email = user.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email do usuário não encontrado")
        
        # Lista templates
        template_manager = get_user_template_manager()
        templates = template_manager.listar_templates(email)
        
        return JSONResponse({
            "sucesso": True,
            "templates": templates,
            "total": len(templates)
        })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[listar_templates_chamado] Erro: {str(e)}")
        import traceback
        logger.debug(f"[listar_templates_chamado] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar templates: {str(e)}")


@router.delete("/chamado/template/excluir", response_class=JSONResponse)
async def excluir_template_chamado(request: Request, nome_template: str):
    """
    Exclui um template de chamado do usuário logado
    
    Query Parameters:
        nome_template: Nome do template a excluir
    """
    try:
        # Verifica se usuário está autenticado
        user = request.session.get('user')
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")
        
        email = user.get('email')
        if not email:
            raise HTTPException(status_code=400, detail="Email do usuário não encontrado")
        
        if not nome_template:
            raise HTTPException(status_code=400, detail="Nome do template é obrigatório")
        
        # Exclui template
        template_manager = get_user_template_manager()
        sucesso = template_manager.excluir_template(email, nome_template)
        
        if sucesso:
            return JSONResponse({
                "sucesso": True,
                "mensagem": "Template excluído com sucesso"
            })
        else:
            raise HTTPException(status_code=404, detail="Template não encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[excluir_template_chamado] Erro: {str(e)}")
        import traceback
        logger.debug(f"[excluir_template_chamado] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir template: {str(e)}")


@router.post("/configuracoes/drive/backup", response_class=JSONResponse)
async def fazer_backup_drive(request: Request):
    """
    Faz backup manual de todas as configurações para o Google Drive
    Requer autenticação e permissão de administrador
    """
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    
    # Verificar permissão (apenas administrador)
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        raise HTTPException(status_code=403, detail="Permissão negada: apenas administradores podem fazer backup")
    
    try:
        from src.configs.drive_config_manager import get_drive_config_manager
        from pathlib import Path
        
        drive_manager = get_drive_config_manager()
        if not drive_manager:
            raise HTTPException(
                status_code=503, 
                detail="Sincronização com Google Drive não está disponível. Verifique as configurações."
            )
        
        resultados = {
            'sucesso': True,
            'mensagem': 'Backup manual não é mais necessário - sistema usa apenas Google Drive',
            'arquivos_no_drive': []
        }
        
        # Lista arquivos que já estão no Drive
        arquivos_gerais = drive_manager.listar_configs()
        arquivos_user = drive_manager.listar_configs(subpasta='user_configs')
        
        resultados['arquivos_no_drive'] = {
            'gerais': [f['nome'] for f in arquivos_gerais],
            'user_configs': [f['nome'] for f in arquivos_user]
        }
        
        if resultados['erros']:
            resultados['sucesso'] = False
        
        return JSONResponse(content=resultados)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[fazer_backup_drive] Erro: {str(e)}")
        import traceback
        logger.debug(f"[fazer_backup_drive] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao fazer backup: {str(e)}")


@router.post("/configuracoes/drive/restore", response_class=JSONResponse)
async def restaurar_drive(request: Request):
    """
    Restaura configurações do Google Drive para o sistema local
    Requer autenticação e permissão de administrador
    """
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    
    # Verificar permissão (apenas administrador)
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        raise HTTPException(status_code=403, detail="Permissão negada: apenas administradores podem restaurar")
    
    try:
        from src.configs.drive_config_manager import get_drive_config_manager
        from pathlib import Path
        
        drive_manager = get_drive_config_manager()
        if not drive_manager:
            raise HTTPException(
                status_code=503, 
                detail="Sincronização com Google Drive não está disponível. Verifique as configurações."
            )
        
        resultados = {
            'sucesso': True,
            'mensagem': 'Restauração manual não é mais necessária - sistema lê diretamente do Google Drive',
            'arquivos_no_drive': []
        }
        
        # Lista arquivos que estão no Drive
        arquivos_gerais = drive_manager.listar_configs()
        arquivos_user = drive_manager.listar_configs(subpasta='user_configs')
        
        resultados['arquivos_no_drive'] = {
            'gerais': [f['nome'] for f in arquivos_gerais],
            'user_configs': [f['nome'] for f in arquivos_user]
        }
        
        if resultados['erros']:
            resultados['sucesso'] = False
        
        return JSONResponse(content=resultados)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[restaurar_drive] Erro: {str(e)}")
        import traceback
        logger.debug(f"[restaurar_drive] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao restaurar: {str(e)}")


@router.get("/configuracoes/drive/status", response_class=JSONResponse)
async def status_sincronizacao_drive(request: Request):
    """
    Retorna o status da sincronização com Google Drive
    Requer autenticação e permissão de administrador
    """
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    
    # Verificar permissão (apenas administrador)
    user_email = user.get('email', '').lower().strip()
    email_permitido = 'nathan.azevedo@uisa.com.br'
    if user_email != email_permitido:
        raise HTTPException(status_code=403, detail="Permissão negada: apenas administradores podem verificar status")
    
    try:
        from src.configs.drive_config_manager import get_drive_config_manager
        from src.modelo_dados.modelo_settings import ConfigEnvSetings
        
        drive_manager = get_drive_config_manager()
        
        status = {
            'sincronizacao_habilitada': hasattr(ConfigEnvSetings, 'DRIVE_SYNC_ENABLED') and 
                                       ConfigEnvSetings.DRIVE_SYNC_ENABLED.lower() in ('true', '1', 'yes'),
            'servico_disponivel': drive_manager is not None and drive_manager.service is not None,
            'pasta_configurada': drive_manager.base_folder_id is not None if drive_manager else False,
            'arquivos_no_drive': []
        }
        
        if drive_manager and drive_manager.service:
            # Lista arquivos
            arquivos_gerais = drive_manager.listar_configs()
            arquivos_user = drive_manager.listar_configs(subpasta='user_configs')
            
            status['arquivos_no_drive'] = {
                'gerais': arquivos_gerais,
                'user_configs': arquivos_user
            }
        
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"[status_sincronizacao_drive] Erro: {str(e)}")
        import traceback
        logger.debug(f"[status_sincronizacao_drive] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status: {str(e)}")

