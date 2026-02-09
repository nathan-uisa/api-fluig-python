from datetime import datetime
from typing import Dict, Any, Optional
from src.modelo_dados.modelos_fluig import (
    AberturaChamado,
    AberturaChamadoClassificado,
)
from src.fluig.fluig_core import FluigCore
from src.web.web_servicos_fluig import obter_detalhes_servico_fluig
from src.web.web_auth_manager import obter_cookies_validos
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.utilitarios_centrais.fake_user import FakeUser


def _email_na_lista_fakeuser(email: str) -> bool:
    """
    Verifica se o email está na lista EMAILS_LIST do .env
    
    Args:
        email: Email do solicitante
    
    Returns:
        True se o email está na lista, False caso contrário
    """
    try:
        emails_list_str = ConfigEnvSetings.EMAILS_LIST
        if not emails_list_str or not emails_list_str.strip():
            return False
        
        # Converte string separada por vírgulas em lista
        emails_list = [e.strip().lower() for e in emails_list_str.split(',') if e.strip()]
        
        return email.lower().strip() in emails_list
    except Exception as e:
        logger.error(f"[_email_na_lista_fakeuser] Erro ao verificar email: {str(e)}")
        return False


def PayloadChamadoNormal(Item: AberturaChamado, ambiente: str = "PRD", usuario_atendido: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Monta payload básico para abertura de chamado sem classificação

    {
	"targetState": "0",
	"subProcessTargetState": "0",
	"targetAssignee": "d3cecd6b3ce049e9923c588b657d99da",
	"formFields": {
		"ds_chamado": "DescriçãodoChamado",
		"nm_emitente": "FabriciodosSantosSilvadeCarvalho",
		"h_solicitante": "d3cecd6b3ce049e9923c588b657d99da",
		"ds_cargo": "AssistentedeTecnologiadaInformação",
		"NomeRegistrador": "fabricio.carvalho@uisa.com.br",
		"ds_email_sol": "fabricio.carvalho@uisa.com.br",
		"ds_secao": "Sistemas",
		"num_cr_elab": "110051404",
		"ds_empresa": "USINASITAMARATI",
		"ch_sap": "0", 
		"num_tel_contato": "5565996345425",
		"ds_titulo": "TítulodoChamado",
		"dt_abertura": "19/11/2025 20: 11",
		"UsuarioAtendido": "Fabricio dos Santos Silva de Carvalho"
	}
}
    
    Args:
        Item: Objeto AberturaChamado com dados do chamado
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario_atendido: Nome do usuário atendido (opcional)
    """
    try:
        logger.info(f"[PayloadChamadoNormal] Iniciando montagem - Usuário: {Item.usuario}, UsuarioAtendido: {usuario_atendido}")

        # Verifica se o email está na lista de FakeUser
        usar_fake_user = _email_na_lista_fakeuser(Item.usuario)
        
        if usar_fake_user:
            logger.info(f"[PayloadChamadoNormal] Email '{Item.usuario}' encontrado na EMAILS_LIST - utilizando FakeUser")
            fake_user_data = FakeUser()
            fake_content = fake_user_data.get('content', {})
            
            if not fake_content:
                logger.error(f"[PayloadChamadoNormal] FakeUser não retornou dados")
                return None
            
            colleague_id = fake_content.get('colleagueId', '')
            target_assignee = fake_content.get('targetAssignee', colleague_id)
            colleague_name = fake_content.get('Nome', '')
            colleague_email = fake_content.get('Email', '')
            
            if not colleague_id:
                logger.error(f"[PayloadChamadoNormal] colleagueId não encontrado no FakeUser")
                return None
            
            logger.info(f"[PayloadChamadoNormal] Dados do FakeUser obtidos - ID: {colleague_id}, Nome: {colleague_name}")
        else:
            fluig_core = FluigCore(ambiente=ambiente)

            # Busca dados do usuário no dataset colleague
            dados_colleague = fluig_core.Dataset_config(dataset_id="colleague", user=Item.usuario)
            if hasattr(dados_colleague, "status_code") or not dados_colleague.get("content"):
                logger.error(f"[PayloadChamadoNormal] Usuário '{Item.usuario}' não encontrado no dataset colleague")
                return None

            content_colleague = dados_colleague.get("content", [])
            if isinstance(content_colleague, list):
                colleague_data = content_colleague[0]
            else:
                colleague_data = content_colleague.get("values", [{}])[0]

            colleague_id = colleague_data.get("colleagueId", "")
            colleague_name = colleague_data.get("colleagueName", Item.usuario)
            colleague_email = colleague_data.get("mail", Item.usuario)
            target_assignee = colleague_id

            if not colleague_id:
                logger.error(f"[PayloadChamadoNormal] colleagueId não encontrado para '{Item.usuario}'")
                return None

        telefone_contato = Item.telefone.strip() if Item.telefone and Item.telefone.strip() else "65"
        dt_abertura = datetime.now().strftime("%d/%m/%Y %H:%M")

        form_fields = {
            "num_tel_contato": telefone_contato,
            "ds_titulo": Item.titulo,
            "ds_chamado": Item.descricao,
            "nm_emitente": colleague_name,
            "NomeRegistrador": colleague_name,
            "h_solicitante": colleague_id,
            "email_solicitante": colleague_email,
            "ds_email_sol": colleague_email,
            "status": "0",
            "dt_abertura": dt_abertura,
            "ch_sap": "0"
        }
        
        # Adicionar UsuarioAtendido se fornecido
        if usuario_atendido and usuario_atendido.strip():
            form_fields["UsuarioAtendido"] = usuario_atendido.strip()
            logger.info(f"[PayloadChamadoNormal] UsuarioAtendido adicionado: {usuario_atendido}")

        payload = {
            "targetState": "0",
            "subProcessTargetState": "0",
            "targetAssignee": target_assignee,
            "formFields": form_fields
        }

        logger.info("[PayloadChamadoNormal] Payload montado com sucesso")
        logger.info(f"[PayloadChamadoNormal] Payload: {payload}")
        return payload

    except Exception as e:
        logger.error(f"[PayloadChamadoNormal] Erro inesperado ao montar payload: {str(e)}")
        import traceback

        logger.debug(f"[PayloadChamadoNormal] Traceback: {traceback.format_exc()}")
        return None


def PayloadChamadoClassificado(Item: AberturaChamadoClassificado, ambiente: str = "PRD", usuario_atendido: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Monta payload para abertura de chamado classificado no Fluig
    
    Se o email do solicitante estiver na lista EMAILS_LIST do .env,
    utiliza FakeUser() para os dados do solicitante.
    
    Busca informações necessárias de:
    - Dataset colleague: dados do usuário solicitante (ou FakeUser se na lista)
    - Dataset ds_funcionarios: dados do funcionário (ou FakeUser se na lista)
    - Detalhes do serviço: informações do serviço solicitado
    
    Args:
        Item: Objeto AberturaChamadoClassificado com dados do chamado
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario_atendido: Nome do usuário atendido (opcional)
    
    Returns:
        Dicionário com payload formatado ou None em caso de erro
    """
    try:
        logger.info(f"[PayloadChamadoClassificado] Iniciando montagem de payload - Usuário: {Item.usuario}, Serviço: {Item.servico}")

        usuario_auth = ConfigEnvSetings.FLUIG_ADMIN_USER
        senha_auth = ConfigEnvSetings.FLUIG_ADMIN_PASS
        cookies = obter_cookies_validos(ambiente, forcar_login=False, usuario=usuario_auth, senha=senha_auth)
        
        if not cookies:
            logger.error("[PayloadChamadoClassificado] Falha ao obter autenticação válida")
            return None
        
        # Verifica se o email está na lista de FakeUser
        usar_fake_user = _email_na_lista_fakeuser(Item.usuario)

        if usar_fake_user:
            logger.info(f"[PayloadChamadoClassificado] Email '{Item.usuario}' encontrado na EMAILS_LIST - utilizando FakeUser")
            fake_user_data = FakeUser()
            fake_content = fake_user_data.get('content', {})
            
            if not fake_content:
                logger.error(f"[PayloadChamadoClassificado] FakeUser não retornou dados")
                return None

            colleague_id = fake_content.get('colleagueId', '')
            target_assignee = fake_content.get('targetAssignee', colleague_id)
            colleague_name = fake_content.get('Nome', '')
            colleague_email = fake_content.get('Email', '')
            
            if not colleague_id:
                logger.error(f"[PayloadChamadoClassificado] colleagueId não encontrado no FakeUser")
                return None
            
            if not target_assignee:
                logger.warning(f"[PayloadChamadoClassificado] targetAssignee não encontrado no FakeUser - usando colleagueId")
                target_assignee = colleague_id
            
            logger.info(f"[PayloadChamadoClassificado] Dados do FakeUser (colleague) obtidos - ID: {colleague_id}, targetAssignee: {target_assignee}, Nome: {colleague_name}")
            
            # Dados do funcionário também vêm do FakeUser
            ds_cargo = fake_content.get('Função', '')
            ds_secao = fake_content.get('Seção', '')
            num_cr_elab = fake_content.get('Centro_Custo', '')
            ds_empresa = fake_content.get('Empresa', '')
            logger.info(f"[PayloadChamadoClassificado] Dados do FakeUser (funcionário) obtidos - Cargo: {ds_cargo}, Seção: {ds_secao}")
        else:
            logger.info(f"[PayloadChamadoClassificado] Buscando dados do usuário no dataset colleague...")
            fluig_core = FluigCore(ambiente=ambiente)
            dados_colleague = fluig_core.Dataset_config(dataset_id="colleague", user=Item.usuario)
            

            if hasattr(dados_colleague, 'status_code'):
                logger.error(f"[PayloadChamadoClassificado] Erro ao buscar dados do colleague - Status: {dados_colleague.status_code}")
                return None
            
            if not dados_colleague or not dados_colleague.get('content'):
                logger.error(f"[PayloadChamadoClassificado] Usuário '{Item.usuario}' não encontrado no dataset colleague")
                return None
            content = dados_colleague.get('content', [])
            if isinstance(content, list):
                colleague_data = content[0] if content else None
            else:
                colleague_data = content.get('values', [{}])[0] if isinstance(content.get('values'), list) and content.get('values') else None
            
            if not colleague_data:
                logger.error(f"[PayloadChamadoClassificado] Nenhum dado retornado do dataset colleague para '{Item.usuario}'")
                return None
            
            colleague_id = colleague_data.get('colleagueId', '')
            colleague_name = colleague_data.get('colleagueName', '')
            colleague_email = colleague_data.get('mail', '')
            target_assignee = colleague_id
            
            if not colleague_id:
                logger.error(f"[PayloadChamadoClassificado] colleagueId não encontrado para usuário '{Item.usuario}'")
                return None
            
            logger.info(f"[PayloadChamadoClassificado] Dados do colleague obtidos - ID: {colleague_id}, Nome: {colleague_name}")

            logger.info(f"[PayloadChamadoClassificado] Buscando dados do funcionário no dataset ds_funcionarios...")
            dados_funcionarios = fluig_core.Dataset_config(dataset_id="ds_funcionarios", user=Item.usuario)
            
            funcionario_data = None
            if not hasattr(dados_funcionarios, 'status_code') and dados_funcionarios and dados_funcionarios.get('content'):
                content_func = dados_funcionarios.get('content', [])
                if isinstance(content_func, list):
                    funcionario_data = content_func[0] if content_func else None
                else:
                    funcionario_data = content_func.get('values', [{}])[0] if isinstance(content_func.get('values'), list) and content_func.get('values') else None
            
            if not funcionario_data:
                logger.warning(f"[PayloadChamadoClassificado] Funcionário '{Item.usuario}' não encontrado no dataset ds_funcionarios - usando valores padrão")
                ds_cargo = ""
                ds_secao = ""
                num_cr_elab = ""
                ds_empresa = ""
            else:
                ds_cargo = funcionario_data.get('Função', '')
                ds_secao = funcionario_data.get('Seção', '')
                num_cr_elab = funcionario_data.get('Centro de Custo', '')
                ds_empresa = funcionario_data.get('Empresa', '')
                logger.info(f"[PayloadChamadoClassificado] Dados do funcionário obtidos - Cargo: {ds_cargo}, Seção: {ds_secao}")

        logger.info(f"[PayloadChamadoClassificado] Buscando detalhes do serviço ID: {Item.servico}...")
        detalhes_servico = obter_detalhes_servico_fluig(
            document_id=Item.servico,
            ambiente=ambiente,
            cookies_list=cookies
        )
        
        if not detalhes_servico or not detalhes_servico.get('content', {}).get('values'):
            logger.error(f"[PayloadChamadoClassificado] Serviço '{Item.servico}' não encontrado")
            return None
        
        servico_data = detalhes_servico['content']['values'][0]
        grupo_servico = servico_data.get('grupo_servico', '')
        item_servico = servico_data.get('item_servico', '')
        servico = servico_data.get('servico', '')
        urgencia_alta = servico_data.get('urgencia_alta', '')
        urgencia_media = servico_data.get('urgencia_media', '')
        urgencia_baixa = servico_data.get('urgencia_baixa', '')
        ds_responsavel = servico_data.get('ds_responsavel', '')
        equipe_executante = servico_data.get('equipe_executante', '')
        matric_keyuser = servico_data.get('matric_keyuser', '')
        
        logger.info(f"[PayloadChamadoClassificado] Detalhes do serviço obtidos - Serviço: {servico}, Grupo: {grupo_servico}")

        if not servico:
            logger.error(f"[PayloadChamadoClassificado] Campo 'servico' não encontrado nos detalhes do serviço")
            return None

        dt_abertura = datetime.now().strftime("%d/%m/%Y %H:%M")

        telefone_contato = '65'
        if Item.telefone and Item.telefone.strip():
            telefone_contato = Item.telefone.strip()
            logger.info(f"[PayloadChamadoClassificado] Telefone fornecido: {telefone_contato}")
        else:
            logger.info(f"[PayloadChamadoClassificado] Telefone não fornecido ou vazio - usando valor padrão: {telefone_contato}")
        
        # Monta payload
        form_fields = {
            "num_tel_contato": telefone_contato,
            "ds_titulo": Item.titulo,
            "ds_chamado": Item.descricao,
            "nm_emitente": colleague_name,
            "NomeRegistrador": colleague_name,
            "h_solicitante": colleague_id,
            "email_solicitante": colleague_email,
            "ds_email_sol": colleague_email,
            "status": "0",
            "dt_abertura": dt_abertura,
            "ch_sap": "0",
            "acesso": "0",
            "ds_grupo_servico": grupo_servico,
            "ds_item_servico": item_servico,
            "ds_servico": servico,
            "urg_alta": urgencia_alta,
            "urg_media": urgencia_media,
            "urg_baixa": urgencia_baixa,
            "ds_urgencia": "Média",
            "ds_resp_servico": ds_responsavel,
            "ds_equipe_resp": equipe_executante,
            "equipe_resp": "ITSM_TODOS",
            "ds_tipo": "Solicitacao",
            "status_chamado": "Em Atendimento",
            "ds_time_HANA": "Interno",
            "ds_status_HANA": "Pendente",
            "ds_cargo": ds_cargo,
            "KeyUser": matric_keyuser,
            "ds_secao": ds_secao,
            "num_cr_elab": num_cr_elab,
            "fila_resp": "",
            "ds_empresa": ds_empresa
        }
        
        # Adicionar UsuarioAtendido se fornecido
        if usuario_atendido and usuario_atendido.strip():
            form_fields["UsuarioAtendido"] = usuario_atendido.strip()
            logger.info(f"[PayloadChamadoClassificado] UsuarioAtendido adicionado: {usuario_atendido}")
        
        payload = {
            "targetState": "5",
            "targetAssignee": target_assignee,
            "formFields": form_fields
        }
        
        logger.info(f"[PayloadChamadoClassificado] Payload montado com sucesso")
        logger.info(f"[PayloadChamadoClassificado] Payload: {payload}")
        
        return payload
        
    except ValueError as e:
        logger.error(f"[PayloadChamadoClassificado] Erro de validação: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[PayloadChamadoClassificado] Erro inesperado ao montar payload: {str(e)}")
        import traceback
        logger.info(f"[PayloadChamadoClassificado] Traceback: {traceback.format_exc()}")
        return None
