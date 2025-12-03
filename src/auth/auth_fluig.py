from src.modelo_dados.modelo_settings import ConfigEnvSetings
from requests_oauthlib import OAuth1


def AutenticarFluig(AMBIENTE: str):
    """
    Autentica no Fluig usando OAuth1
    
    Args:
        AMBIENTE: Ambiente ('PRD' ou 'QLD')
    
    Returns:
        Tupla (auth, headers) com autenticação OAuth1 e headers
    """
    if AMBIENTE == 'PRD':
        auth = OAuth1(ConfigEnvSetings.CK, ConfigEnvSetings.CS, ConfigEnvSetings.TK, ConfigEnvSetings.TS)
    elif AMBIENTE == 'QLD':
        auth = OAuth1(ConfigEnvSetings.CK_QLD, ConfigEnvSetings.CS_QLD, ConfigEnvSetings.TK_QLD, ConfigEnvSetings.TS_QLD)
    else:
        raise ValueError(f"Ambiente inválido: {AMBIENTE}")
    
    headers = {'Content-Type': 'application/json; charset=UTF-8'}
    return auth, headers