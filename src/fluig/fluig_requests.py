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
    
    def RequestTipoGET(self,url: str, PARAMETROS: dict, logar_conteudo: bool = True):
        """
            Usado para os Datasets
            
        Args:
            url: URL da requisição
            PARAMETROS: Parâmetros da query string
            logar_conteudo: Se True, loga o conteúdo da resposta (padrão: True)
        """
        logger.info(f"[RequestsFluig] RequestTipoGET - URL: {url}")
        resposta = requests.get(url, headers=self.headers, auth=self.auth, params=PARAMETROS, timeout=15)
        logger.info(f"[RequestsFluig] RequestTipoGET - Status Code: {resposta.status_code}")
        
        if logar_conteudo:
            # Verifica se é conteúdo binário (imagens, PDFs, etc.)
            content_type = resposta.headers.get('Content-Type', '')
            is_binary = False
            
            if content_type:
                is_binary = any(tipo in content_type.lower() for tipo in [
                    'image/', 'application/octet-stream', 'application/pdf', 
                    'application/zip', 'application/x-zip', 'video/', 'audio/'
                ])
            
            if is_binary:
                # Para arquivos binários, loga apenas informações sobre o arquivo
                tamanho = len(resposta.content)
                if tamanho < 1024:
                    tamanho_formatado = f"{tamanho} bytes"
                elif tamanho < 1024 * 1024:
                    tamanho_formatado = f"{tamanho / 1024:.2f} KB"
                else:
                    tamanho_formatado = f"{tamanho / (1024 * 1024):.2f} MB"
                logger.info(f"[RequestsFluig] RequestTipoGET - Conteúdo binário (Content-Type: {content_type}, Tamanho: {tamanho_formatado})")
            else:
                # Para conteúdo de texto, loga normalmente (limita a 500 caracteres)
                try:
                    texto = resposta.text[:500] if len(resposta.text) > 500 else resposta.text
                    logger.info(f"[RequestsFluig] RequestTipoGET - Text: {texto}")
                except Exception:
                    # Se falhar ao converter para texto, pode ser binário
                    tamanho = len(resposta.content)
                    logger.info(f"[RequestsFluig] RequestTipoGET - Conteúdo não-texto (Tamanho: {tamanho} bytes)")
        
        return resposta

    def RequestTipoPOST(self, url: str, PARAMETROS: dict, headers_extra: dict = None):
        """
        Faz requisição POST usando OAuth 1.0
        
        Args:
            url: URL da requisição
            PARAMETROS: Dicionário com os parâmetros do body (JSON)
            headers_extra: Dicionário opcional com headers adicionais a serem mesclados
        """
        logger.info(f"[RequestsFluig] RequestTipoPOST - URL: {url}")
        
        # Mescla headers padrão com headers extras se fornecidos
        headers_finais = self.headers.copy()
        if headers_extra:
            headers_finais.update(headers_extra)
        
        resposta = requests.post(url, headers=headers_finais, auth=self.auth, json=PARAMETROS, timeout=15)
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
    
    def RequestTipoPOSTMultipart(self, url: str, files: dict, data: dict, timeout: int = 60):
        """
        Faz requisição POST com multipart/form-data usando OAuth 1.0
        
        Args:
            url: URL da requisição
            files: Dicionário com arquivos para upload (formato requests)
            data: Dicionário com dados adicionais
            timeout: Timeout da requisição em segundos
            
        Returns:
            Resposta da requisição
        """
        logger.info(f"[RequestsFluig] RequestTipoPOSTMultipart - URL: {url}")
        # Para multipart/form-data, não deve definir Content-Type manualmente
        # O requests define automaticamente com boundary
        headers_multipart = {}
        resposta = requests.post(
            url,
            files=files,
            data=data,
            headers=headers_multipart,
            auth=self.auth,
            timeout=timeout
        )
        logger.info(f"[RequestsFluig] RequestTipoPOSTMultipart - Status Code: {resposta.status_code}")
        logger.info(f"[RequestsFluig] RequestTipoPOSTMultipart - Text: {resposta.text[:500]}")
        return resposta