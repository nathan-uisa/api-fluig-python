
# Isso também não é mais necessário porém será mantido


from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
from src.fluig_requests.requests import RequestsFluig
from src.web.web_cookies import cookies_para_requests
from src.web.web_auth_manager import garantir_autenticacao


class MovitCore():
    def __init__(self, ambiente: str = "PRD"):
        """                                                                                   
        Inicializa a classe MovitCore
        
        Args:
            ambiente: Ambiente ('PRD' ou 'QLD')
        """
        logger.info(f"[MovitCore] Inicializando - Ambiente: {ambiente}")
        self.ambiente = ambiente
        self.requests = RequestsFluig(ambiente)
        if ambiente == "PRD":
            self.url_base = ConfigEnvSetings.URL_FLUIG_PRD
            logger.debug(f"[MovitCore] URL base PRD configurada: {self.url_base}")
        elif ambiente == "QLD":
            self.url_base = ConfigEnvSetings.URL_FLUIG_QLD
            logger.debug(f"[MovitCore] URL base QLD configurada: {self.url_base}")
        else:
            logger.error(f"[MovitCore] Ambiente inválido: {ambiente}")
            raise ValueError(f"Ambiente inválido: {ambiente}")
        
        logger.info(f"[MovitCore] Instância criada com sucesso")
    
    def AberturaDeChamado(self, tipo_chamado: str, Item: any):
        """
        Abre um chamado no Fluig para Movit
        
        Args:
            tipo_chamado: Tipo de chamado ('classificado' ou 'normal')
            Item: Objeto AberturaChamadoClassificadoMovit com dados do chamado
        """
        logger.info(f"[MovitCore.AberturaDeChamado] Iniciando abertura de chamado - Tipo: {tipo_chamado}")
        url = self.url_base + "/process-management/api/v2/processes/Abertura%20de%20Chamados/start"
        
        # Obtém autenticação
        usuario = ConfigEnvSetings.FLUIG_USER_NAME
        senha = ConfigEnvSetings.FLUIG_USER_PASS
        sucesso, cookies_list = garantir_autenticacao(ambiente=self.ambiente, usuario=usuario, senha=senha)
        if not sucesso or not cookies_list:
            logger.error("[MovitCore.AberturaDeChamado] Falha ao garantir autenticação")
            raise ValueError("[MovitCore.AberturaDeChamado] Falha ao garantir autenticação")

        cookies_dict = cookies_para_requests(cookies_list)
        if not cookies_dict:
            logger.error("[MovitCore.AberturaDeChamado] Falha ao converter cookies")
            raise ValueError("[MovitCore.AberturaDeChamado] Falha ao converter cookies")

        from src.utilitarios_centrais.payloads import PayloadChamadoMovtiClassificado
        
        if tipo_chamado == "classificado":
            payload = PayloadChamadoMovtiClassificado(Item, ambiente=self.ambiente)
            if not payload:
                logger.error("[MovitCore.AberturaDeChamado] Falha ao montar payload do chamado classificado")
                raise ValueError("[MovitCore.AberturaDeChamado] Falha ao montar payload do chamado classificado")
        else:
            logger.error(f"[MovitCore.AberturaDeChamado] Tipo de chamado inválido: {tipo_chamado}")
            raise ValueError(f"[MovitCore.AberturaDeChamado] Tipo de chamado inválido: {tipo_chamado}")
        
        logger.info(f"[MovitCore.AberturaDeChamado] Enviando requisição POST para: {url}")
        resposta = self.requests.RequestTipoPostCookies(url, payload, cookies_dict)
        resultado = {
            "status_code": resposta.status_code,
            "sucesso": resposta.status_code == 200
        }
        
        try:
            resultado["dados"] = resposta.json()
            logger.info(f"[MovitCore.AberturaDeChamado] Resposta processada com sucesso - Status: {resposta.status_code}")
        except Exception as e:
            logger.warning(f"[MovitCore.AberturaDeChamado] Erro ao processar JSON da resposta: {str(e)}")
            resultado["dados"] = None
            resultado["texto"] = resposta.text[:500] if resposta.text else ""
        
        return resultado

