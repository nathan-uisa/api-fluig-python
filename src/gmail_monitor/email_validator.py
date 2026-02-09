"""
Módulo para validação de emails
"""
from typing import Dict
from src.utilitarios_centrais.logger import logger
from src.modelo_dados.modelo_settings import ConfigEnvSetings


def _obter_blacklist_emails() -> list:
    """
    Obtém a lista de emails bloqueados da variável BLACK_LIST_EMAILS
    
    Returns:
        Lista de emails bloqueados (em minúsculas)
    """
    try:
        blacklist_str = getattr(ConfigEnvSetings, 'BLACK_LIST_EMAILS', '')
        if not blacklist_str or not blacklist_str.strip():
            return []
        
        # Converte string separada por vírgulas em lista
        blacklist = [e.strip().lower() for e in blacklist_str.split(',') if e.strip()]
        return blacklist
    except Exception as e:
        logger.error(f"[email_validator] Erro ao obter BLACK_LIST_EMAILS: {str(e)}")
        return []


def validar_email_uisa(email: str) -> Dict[str, any]:
    """
    Valida se o email é permitido para processamento
    
    Args:
        email: Email a ser validado
        
    Returns:
        Dict com 'valido' (bool), 'mensagem' (str ou None) e 'is_blacklist' (bool)
        - is_blacklist: True se o email está na BLACK_LIST_EMAILS (deve apenas passar, não marcar como processado)
    """
    if not email or not isinstance(email, str):
        return {"valido": False, "mensagem": "Email inválido/vazio", "is_blacklist": False}
    
    email_lower = email.lower().strip()
    
    # Verifica BLACK_LIST_EMAILS primeiro (se configurada)
    blacklist_emails = _obter_blacklist_emails()
    if blacklist_emails and email_lower in blacklist_emails:
        logger.info(f"[email_validator] Email bloqueado pela BLACK_LIST_EMAILS: {email_lower}")
        return {"valido": False, "mensagem": "Email na lista de bloqueados (BLACK_LIST_EMAILS)", "is_blacklist": True}
    
    # Verifica domínio UISA
    if not email_lower.endswith("@uisa.com.br"):
        return {"valido": False, "mensagem": "Domínio não permitido", "is_blacklist": False}
    
    # Lista de emails de sistema bloqueados (hardcoded)
    emails_sistema_bloqueados = [
        "fluig@uisa.com.br",
        "noreply@uisa.com.br",
        "no-reply@uisa.com.br",
        "sistema@uisa.com.br",
        "automacao@uisa.com.br"
    ]
    
    if email_lower in emails_sistema_bloqueados:
        return {"valido": False, "mensagem": "Email de sistema bloqueado", "is_blacklist": False}
    
    return {"valido": True, "mensagem": None, "is_blacklist": False}


def extrair_email_remetente(email_from: str) -> str:
    """
    Extrai apenas o email do remetente (remove o nome <email>)
    
    Args:
        email_from: String no formato "Nome <email@dominio.com>" ou apenas "email@dominio.com"
        
    Returns:
        Email limpo
    """
    import re
    match = re.search(r'<([^>]+)>', email_from)
    if match:
        return match.group(1)
    return email_from.strip()
