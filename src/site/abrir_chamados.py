import configparser
import re
import os
from typing import Dict, Optional
from src.utilitarios_centrais.logger import logger
from src.site.planilha import PATH_TO_TEMP
from src.modelo_dados.modelo_sites import DadosChamado
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.modelo_dados.modelos_fluig import AberturaChamadoClassificado
from src.fluig.fluig_core import FluigCore


class AbrirChamados:
    """
    Classe para abrir chamados em sequência usando dados processados de planilha.
    Processa placeholders como <A>, <B>, etc. no título e descrição.
    """
    
    def __init__(self, email_usuario: str):
        """
        Inicializa a classe para abrir chamados.
        
        Args:
            email_usuario: Email do usuário que está criando os chamados
        """
        self.email_usuario = email_usuario
        self.config_planilha = configparser.ConfigParser()
    
    def carregar_dados_temp(self) -> bool:
        """
        Carrega os dados processados do arquivo temp.txt.
        
        Returns:
            True se carregou com sucesso, False caso contrário
        """
        try:
            if not os.path.exists(PATH_TO_TEMP):
                logger.error(f"Arquivo temp.txt não encontrado: {PATH_TO_TEMP}")
                return False
            
            self.config_planilha.read(PATH_TO_TEMP, encoding='utf-8')
            
            if not self.config_planilha.sections():
                logger.warning("Nenhuma seção encontrada no arquivo temp.txt")
                return False
            
            logger.info(f"Dados carregados: {len(self.config_planilha.sections())} linhas encontradas")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados do temp.txt: {str(e)}")
            return False
    
    def substituir_placeholders(self, texto: str, numero_linha: str) -> str:
        """
        Substitui placeholders como <A>, <B>, etc. pelos valores da planilha.
        
        Args:
            texto: Texto com placeholders (ex: "Chamado <A> - <B>")
            numero_linha: Número da linha/seção no config (ex: "1", "2", etc.)
        
        Returns:
            Texto com placeholders substituídos
        """
        if not texto:
            return texto
        
        # Encontrar todos os placeholders no formato <LETRA>
        placeholders = re.findall(r'<([A-Z]+)>', texto.upper())
        texto_processado = texto
        
        for letra in placeholders:
            letra_lower = letra.lower()
            
            # Verificar se a coluna existe na seção
            if self.config_planilha.has_option(numero_linha, letra_lower):
                valor = self.config_planilha.get(numero_linha, letra_lower)
                # Substituir placeholder (case-insensitive)
                texto_processado = re.sub(
                    f'<{letra}>', 
                    valor, 
                    texto_processado, 
                    flags=re.IGNORECASE
                )
            else:
                logger.warning(
                    f"Coluna '{letra_lower}' não encontrada na linha {numero_linha}. "
                    f"Placeholder <{letra}> não será substituído."
                )
        
        return texto_processado
    
    def processar_chamado(self, titulo: str, descricao: str, numero_linha: str) -> Dict:
        """
        Processa um chamado substituindo placeholders pelos valores da planilha.
        
        Args:
            titulo: Título do chamado com placeholders
            descricao: Descrição do chamado com placeholders
            numero_linha: Número da linha/seção no config
        
        Returns:
            Dicionário com título e descrição processados, ou erro se linha não encontrada
        """
        secao = str(numero_linha)
        
        if secao not in self.config_planilha.sections():
            return {
                'titulo': titulo,
                'descricao': descricao,
                'erro': f'Linha {secao} não encontrada'
            }
        
        titulo_processado = self.substituir_placeholders(titulo, secao)
        desc_processada = self.substituir_placeholders(descricao, secao)
        
        return {
            'titulo': titulo_processado,
            'descricao': desc_processada,
        }
    
    def criar_chamado_api(self, titulo: str, descricao: str, servico_id: Optional[str] = None) -> Dict:
        """
        Cria um chamado usando FluigCore diretamente (sem requisição HTTP).
        
        Args:
            titulo: Título do chamado
            descricao: Descrição do chamado
            servico_id: ID do serviço para chamado classificado (opcional)
        
        Returns:
            Dicionário com resultado: {'sucesso': bool, 'mensagem': str, 'dados': dict}
        """
        try:
            ambiente = "PRD"
            
            if servico_id and servico_id.strip():
                # Criar chamado classificado
                payload_chamado = AberturaChamadoClassificado(
                    titulo=titulo,
                    descricao=descricao,
                    usuario=self.email_usuario,
                    telefone=None,
                    servico=servico_id
                )
                
                logger.info(f"[criar_chamado_api] Criando chamado classificado - Serviço: {servico_id}")
                fluig_core = FluigCore(ambiente=ambiente)
                resposta = fluig_core.AberturaDeChamado(tipo_chamado="classificado", Item=payload_chamado)
            else:
                # Criar chamado normal
                payload_chamado = DadosChamado(
                    Usuario=self.email_usuario,
                    Titulo=titulo,
                    Descricao=descricao
                )
                
                logger.info(f"[criar_chamado_api] Criando chamado normal")
                fluig_core = FluigCore(ambiente=ambiente)
                resposta = fluig_core.AberturaDeChamado(tipo_chamado="normal", Item=payload_chamado)
            
            if not resposta.get('sucesso'):
                logger.error(f"[criar_chamado_api] Falha ao abrir chamado - Status: {resposta.get('status_code')}")
                return {
                    'sucesso': False,
                    'mensagem': f"Falha ao abrir chamado: {resposta.get('texto', 'Erro desconhecido')}",
                    'dados': {}
                }
            
            # Obter processInstanceId
            dados = resposta.get('dados', {})
            process_instance_id = None
            if dados and isinstance(dados, dict):
                process_instance_id = dados.get('processInstanceId') or dados.get('process_instance_id')
            
            if process_instance_id:
                logger.info(f"[criar_chamado_api] Chamado criado com sucesso - ID: {process_instance_id}")
                return {
                    'sucesso': True,
                    'mensagem': 'Chamado criado com sucesso',
                    'dados': {'processInstanceId': process_instance_id}
                }
            else:
                logger.error(f"[criar_chamado_api] Chamado criado mas processInstanceId não encontrado")
                return {
                    'sucesso': False,
                    'mensagem': 'processInstanceId não encontrado na resposta do Fluig',
                    'dados': {}
                }
            
        except Exception as e:
            logger.error(f"[criar_chamado_api] Erro inesperado ao criar chamado: {str(e)}")
            import traceback
            logger.debug(f"[criar_chamado_api] Traceback: {traceback.format_exc()}")
            return {
                'sucesso': False,
                'mensagem': f'Erro inesperado: {str(e)}',
                'dados': {}
            }
    
    def abrir_chamados_sequencia(
        self, 
        titulo: str, 
        descricao: str, 
        qtd_chamados: int,
        inicio_linha: int = 1,
        ignorar_primeira_linha: bool = True,
        servico_id: Optional[str] = None
    ) -> Dict:
        """
        Abre múltiplos chamados em sequência usando dados da planilha processada.
        
        Args:
            titulo: Título do chamado com placeholders (ex: "Chamado <A> - <B>")
            descricao: Descrição do chamado com placeholders
            qtd_chamados: Quantidade de chamados a abrir
            inicio_linha: Linha inicial para começar a processar (padrão: 1)
            ignorar_primeira_linha: Se True, ignora a primeira seção (cabeçalho) (padrão: True)
        
        Returns:
            Dicionário com estatísticas: {
                'total_processados': int,
                'sucessos': int,
                'erros': int,
                'detalhes': List[Dict]
            }
        """
        # Carregar dados do temp.txt
        if not self.carregar_dados_temp():
            return {
                'total_processados': 0,
                'sucessos': 0,
                'erros': 1,
                'detalhes': [{
                    'linha': 0,
                    'sucesso': False,
                    'mensagem': 'Erro ao carregar dados do temp.txt'
                }]
            }
        
        secoes = sorted(
            [int(s) for s in self.config_planilha.sections() if s.isdigit()],
            key=int
        )
        
        if not secoes:
            return {
                'total_processados': 0,
                'sucessos': 0,
                'erros': 1,
                'detalhes': [{
                    'linha': 0,
                    'sucesso': False,
                    'mensagem': 'Nenhuma linha válida encontrada no temp.txt'
                }]
            }
        
        # Se ignorar_primeira_linha for True, remover a primeira seção (geralmente é o cabeçalho)
        if ignorar_primeira_linha and secoes:
            primeira_secao = min(secoes)
            secoes = [s for s in secoes if s != primeira_secao]
            logger.info(f"Ignorando primeira linha (seção {primeira_secao}) - cabeçalho da planilha")
        
        # Filtrar seções a partir do início
        secoes_filtradas = [s for s in secoes if s >= inicio_linha]
        
        # Limitar quantidade de chamados
        secoes_processar = secoes_filtradas[:qtd_chamados]
        
        if not secoes_processar:
            return {
                'total_processados': 0,
                'sucessos': 0,
                'erros': 1,
                'detalhes': [{
                    'linha': inicio_linha,
                    'sucesso': False,
                    'mensagem': f'Nenhuma linha encontrada a partir da linha {inicio_linha}'
                }]
            }
        
        logger.info(
            f"Iniciando criação de {len(secoes_processar)} chamado(s) "
            f"a partir da linha {inicio_linha}"
        )
        
        sucessos = 0
        erros = 0
        detalhes = []
        
        # Processar cada linha
        for numero_linha in secoes_processar:
            linha_str = str(numero_linha)
            
            # Processar placeholders
            resultado_processamento = self.processar_chamado(
                titulo, 
                descricao, 
                linha_str
            )
            
            if 'erro' in resultado_processamento:
                erros += 1
                detalhes.append({
                    'linha': numero_linha,
                    'sucesso': False,
                    'mensagem': resultado_processamento['erro']
                })
                logger.warning(
                    f"Linha {numero_linha}: {resultado_processamento['erro']}"
                )
                continue
            
            # Criar chamado usando FluigCore diretamente
            resultado_api = self.criar_chamado_api(
                resultado_processamento['titulo'],
                resultado_processamento['descricao'],
                servico_id=servico_id
            )
            
            if resultado_api['sucesso']:
                sucessos += 1
                process_instance_id = resultado_api['dados'].get('processInstanceId') if resultado_api.get('dados') else None
                detalhes.append({
                    'linha': numero_linha,
                    'sucesso': True,
                    'mensagem': resultado_api['mensagem'],
                    'titulo': resultado_processamento['titulo'],
                    'chamado_id': process_instance_id
                })
            else:
                erros += 1
                detalhes.append({
                    'linha': numero_linha,
                    'sucesso': False,
                    'mensagem': resultado_api['mensagem'],
                    'titulo': resultado_processamento['titulo']
                })
        
        logger.info(
            f"Processamento concluído: {sucessos} sucesso(s), {erros} erro(s)"
        )
        
        return {
            'total_processados': len(secoes_processar),
            'sucessos': sucessos,
            'erros': erros,
            'detalhes': detalhes
        }

