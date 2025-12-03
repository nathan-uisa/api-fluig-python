import requests,os
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger

def IA(prompt):
    if not prompt:
        logger.error("IA: Prompt não fornecido ou vazio")
        return Exception("Prompt não pode ser vazio")
    
    logger.info("IA: Iniciando processamento com IA")
    logger.debug(f"IA: Prompt recebido (primeiros 100 caracteres): {prompt[:100]}...")
    
    try:
        IA_KEYS = ConfigEnvSetings.IA_KEYS.split(',')
        IA_MODELS = ConfigEnvSetings.IA_MODELS.split(',')
    except Exception as e:
        logger.error(f"IA: Erro ao carregar configurações - Erro: {str(e)}")
        return Exception(f"Erro ao carregar configurações da IA: {str(e)}")
    
    if not IA_KEYS or not IA_MODELS:
        logger.error("IA: Chaves ou modelos não configurados")
        return Exception("Chaves ou modelos da IA não configurados")
    
    ultimo_erro = None
    tentativas = 0
    
    for key in IA_KEYS:
        for model in IA_MODELS:
            tentativas += 1
            logger.debug(f"IA: Tentativa {tentativas} - Modelo: {model}")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            headers = {'Content-Type': 'application/json'}
            
            try:
                http_response = requests.post(url, headers=headers, json=payload, timeout=30)
                response_code = http_response.status_code
                
                if response_code == 200:
                    json_response = http_response.json()
                    text_response = json_response['candidates'][0]['content']['parts'][0]['text']
                    logger.info(f"IA: Processamento bem-sucedido - Modelo: {model}, Tentativa: {tentativas}")
                    return text_response
                else:
                    ultimo_erro = f"Status {response_code}: {http_response.text[:200]}"
                    logger.warning(f"IA: Erro na requisição - Modelo: {model}, Status: {response_code}")
                    continue
            except requests.exceptions.RequestException as e:
                ultimo_erro = str(e)
                logger.warning(f"IA: Erro de requisição - Modelo: {model}, Erro: {str(e)}")
                continue
            except (KeyError, IndexError, TypeError) as e:
                ultimo_erro = f"Erro ao processar resposta: {str(e)}"
                logger.warning(f"IA: Erro ao processar resposta - Modelo: {model}, Erro: {str(e)}")
                continue
    
    logger.error(f"IA: Todas as tentativas falharam - Total: {tentativas}, Último erro: {ultimo_erro}")
    return Exception(f"Erro no processamento da IA após {tentativas} tentativas: {ultimo_erro}")