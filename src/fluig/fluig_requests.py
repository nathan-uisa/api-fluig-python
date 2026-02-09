from src.auth.auth_fluig import AutenticarFluig
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger
import requests

"""
    Classe para fazer requisições HTTP para o Fluig
"""
class RequestsFluig():
    def __init__(self, ambiente: str = "PRD"):
        self.auth, self.headers = AutenticarFluig(ambiente)
        if ambiente == "PRD":
            self.url = ConfigEnvSetings.URL_FLUIG_PRD
        elif ambiente == "QLD":
            self.url = ConfigEnvSetings.URL_FLUIG_QLD
        else:
            raise ValueError(f"Ambiente inválido: {ambiente}")
        pass
    
    def RequestTipoGET(self,url: str, PARAMETROS: dict):
        """
            Usado para os Datasets
        """
        logger.info(f"[RequestsFluig] RequestTipoGET - URL: {url}")
        resposta = requests.get(url, headers=self.headers, auth=self.auth, params=PARAMETROS, timeout=15)
        logger.info(f"[RequestsFluig] RequestTipoGET - Status Code: {resposta.status_code}")
        logger.info(f"[RequestsFluig] RequestTipoGET - Text: {resposta.text}")
        return resposta

    def RequestTipoPOST(self,url: str, PARAMETROS: dict):
        """
        """
        logger.info(f"[RequestsFluig] RequestTipoPOST - URL: {url}")
        resposta = requests.post(url, headers=self.headers, auth=self.auth, json=PARAMETROS, timeout=15)
        logger.info(f"[RequestsFluig] RequestTipoPOST - Status Code: {resposta.status_code}")
        logger.info(f"[RequestsFluig] RequestTipoPOST - Text: {resposta.text}")
        return resposta
        
    def RequestTipoPostCookies(self,url: str, PARAMETROS: dict, cookies: dict):
        """
            Usado para abertura dos Chamados em geral 
        """
        logger.info(f"[RequestsFluig] RequestTipoPostCookies - URL: {url}")
        resposta = requests.post(url, headers=self.headers, auth=self.auth, json=PARAMETROS, cookies=cookies, timeout=15)
        logger.info(f"[RequestsFluig] RequestTipoPostCookies - Status Code: {resposta.status_code}")
        logger.info(f"[RequestsFluig] RequestTipoPostCookies - Text: {resposta.text}")
        return resposta
