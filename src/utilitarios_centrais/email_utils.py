import re
from typing import Dict, Optional
from src.utilitarios_centrais.logger import logger


def extrair_titulo_descricao_ia(resposta_ia: str) -> Optional[Dict[str, str]]:
    """
    Extrai título e descrição do retorno da IA
    
    Formato esperado: #SIM#. &Título& ... &Descrição& ...
    
    Args:
        resposta_ia: Resposta da IA contendo título e descrição
    
    Returns:
        Dicionário com 'titulo' e 'descricao' ou None se não conseguir extrair
    """
    try:
        logger.info(f"[extrair_titulo_descricao_ia] Processando resposta da IA...")
        texto = resposta_ia.replace("#SIM#", "").strip()
        padrao_titulo = r'&Título&\s*(.+?)\s*&Descrição&'
        match_titulo = re.search(padrao_titulo, texto, re.DOTALL | re.IGNORECASE)
        
        if match_titulo:
            titulo = match_titulo.group(1).strip()
            padrao_descricao = r'&Descrição&\s*(.+?)(?:\s*$|\s*&)'
            match_descricao = re.search(padrao_descricao, texto, re.DOTALL | re.IGNORECASE)
            
            if match_descricao:
                descricao = match_descricao.group(1).strip()
            else:
                indice_descricao = texto.upper().find('&DESCRIÇÃO&')
                if indice_descricao != -1:
                    descricao = texto[indice_descricao + len('&DESCRIÇÃO&'):].strip()
                else:
                    logger.warning("[extrair_titulo_descricao_ia] Não foi possível extrair descrição")
                    return None
            
            logger.info(f"[extrair_titulo_descricao_ia] Título e descrição extraídos com sucesso")
            return {
                'titulo': titulo,
                'descricao': descricao
            }
        else:
            logger.warning("[extrair_titulo_descricao_ia] Padrão de título não encontrado na resposta da IA")
            return None
            
    except Exception as e:
        logger.error(f"[extrair_titulo_descricao_ia] Erro ao extrair título e descrição: {str(e)}")
        import traceback
        logger.debug(f"[extrair_titulo_descricao_ia] Traceback: {traceback.format_exc()}")
        return None

