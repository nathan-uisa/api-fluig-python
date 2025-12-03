"""Utilitários para operações com arquivos JSON"""
import json
from pathlib import Path
from src.utilitarios_centrais.logger import logger


def salvar_servicos_json(servicos: dict, ambiente: str = "PRD") -> str:
    """
    Salva a lista de serviços em arquivo JSON na pasta src/json/
    
    Args:
        servicos: Dicionário com os serviços obtidos
        ambiente: Ambiente ('PRD' ou 'QLD')
    
    Returns:
        Caminho do arquivo salvo
    """
    try:
        # src/utilitarios_centrais/json_utils.py -> src/utilitarios_centrais/ -> src/ -> src/json/
        src_dir = Path(__file__).parent.parent
        json_dir = src_dir / "json"
        json_dir.mkdir(exist_ok=True)
        arquivo = json_dir / f"servicos_{ambiente.lower()}.json"
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(servicos, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[salvar_servicos_json] Serviços salvos em: {arquivo}")
        return str(arquivo)
    except Exception as e:
        logger.error(f"[salvar_servicos_json] Erro ao salvar serviços: {str(e)}")
        raise


def salvar_detalhes_servico_json(detalhes: dict, id_servico: str, ambiente: str = "PRD") -> str:
    """
    Salva os detalhes de um serviço em arquivo JSON na pasta src/json/services/
    
    Args:
        detalhes: Dicionário com os detalhes do serviço
        id_servico: ID do serviço
        ambiente: Ambiente ('PRD' ou 'QLD')
    
    Returns:
        Caminho do arquivo salvo
    """
    try:
        # src/utilitarios_centrais/json_utils.py -> src/utilitarios_centrais/ -> src/ -> src/json/services/
        src_dir = Path(__file__).parent.parent
        json_dir = src_dir / "json" / "services"
        json_dir.mkdir(parents=True, exist_ok=True)

        arquivo = json_dir / f"servico_detalhes_{id_servico}_{ambiente.lower()}.json"

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(detalhes, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[salvar_detalhes_servico_json] Detalhes do serviço salvos em: {arquivo}")
        return str(arquivo)
    except Exception as e:
        logger.error(f"[salvar_detalhes_servico_json] Erro ao salvar detalhes: {str(e)}")
        raise

