"""
Monitor de histórico de chamados

Este módulo monitora periodicamente os chamados abertos via email
e verifica se houve atualizações nos históricos.
"""
import time
import threading
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.fluig.fluig_core import FluigCore
from src.utilitarios_centrais.logger import logger
from .historico_manager import HistoricoManager
from src.gmail_monitor.email_sender import enviar_email, criar_template_email_atualizacao


class HistoricoMonitor:
    """
    Monitora atualizações nos históricos de chamados abertos via email
    
    Verifica a cada intervalo configurado (padrão: 1 hora) se houve
    atualizações nos chamados monitorados.
    """
    
    def __init__(
        self,
        intervalo_minutos: float = 60.0,
        historico_manager: Optional[HistoricoManager] = None
    ):
        """
        Inicializa o monitor de histórico
        
        Args:
            intervalo_minutos: Intervalo em minutos entre verificações (padrão: 60.0)
            historico_manager: Instância do HistoricoManager (cria nova se None)
        """
        self.intervalo_minutos = intervalo_minutos
        self.intervalo_segundos = intervalo_minutos * 60
        
        if historico_manager is None:
            self.historico_manager = HistoricoManager()
        else:
            self.historico_manager = historico_manager
        
        self._rodando = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(f"[HistoricoMonitor] Inicializado - Intervalo: {intervalo_minutos} minuto(s)")
    
    def verificar_atualizacoes_chamado(
        self,
        process_instance_id: int,
        ambiente: str = "PRD"
    ) -> Dict[str, Any]:
        """
        Verifica se há atualizações no histórico de um chamado específico
        
        Args:
            process_instance_id: ID da instância do processo (número do chamado)
            ambiente: Ambiente do Fluig (PRD ou QLD)
            
        Returns:
            Dicionário com resultado da verificação:
            - sucesso: bool
            - tem_atualizacoes: bool
            - novos_items: Lista de novos itens (se houver)
            - erro: Mensagem de erro (se houver)
        """
        try:
            logger.info(f"[HistoricoMonitor] Verificando atualizações do chamado {process_instance_id}...")
            
            # Lê histórico salvo
            historico_antigo = self.historico_manager.ler_historico(process_instance_id)
            
            if historico_antigo is None:
                logger.warning(f"[HistoricoMonitor] Histórico antigo não encontrado para chamado {process_instance_id}")
                return {
                    'sucesso': False,
                    'tem_atualizacoes': False,
                    'novos_items': [],
                    'erro': 'Histórico antigo não encontrado'
                }
            
            # Obtém histórico atual do Fluig
            fluig_core = FluigCore(ambiente=ambiente)
            historico_novo = fluig_core.obter_historico_chamado(process_instance_id)
            
            if historico_novo is None:
                logger.error(f"[HistoricoMonitor] Erro ao obter histórico atual do chamado {process_instance_id}")
                return {
                    'sucesso': False,
                    'tem_atualizacoes': False,
                    'novos_items': [],
                    'erro': 'Erro ao obter histórico atual do Fluig'
                }
            
            # Compara históricos
            comparacao = self.historico_manager.comparar_historicos(
                historico_antigo,
                historico_novo
            )
            
            # Atualiza histórico salvo (sempre atualiza para manter estrutura organizada)
            self.historico_manager.atualizar_historico(
                    process_instance_id,
                    historico_novo,
                    ambiente
                )
                
            # Verifica itens com email_enviado = false e envia email
            itens_nao_enviados = self.historico_manager.obter_itens_nao_enviados(
                process_instance_id,
                historico_novo
            )
            
            # Se há itens não enviados, envia email de notificação
            if itens_nao_enviados:
                email_remetente = self.historico_manager.obter_email_remetente(process_instance_id)
                
                if email_remetente:
                    try:
                        link = f"https://fluig.uisa.com.br/portal/p/1/pageworkflowview?app_ecm_workflowview_detailsProcessInstanceID={process_instance_id}"
                        
                        # Cria template HTML
                        html_template = criar_template_email_atualizacao(
                            process_instance_id,
                            link,
                            itens_nao_enviados,
                            email_remetente
                        )
                        
                        # Usa o gerenciador de fluxo para processar os itens
                        from src.historico_monitor.historico_fluxo import HistoricoFluxoManager
                        fluxo_manager = HistoricoFluxoManager()
                        itens_processados = fluxo_manager.processar_itens(itens_nao_enviados[:10])
                        
                        # Corpo em texto plano baseado nos itens processados
                        itens_texto = []
                        for item_processado in itens_processados:
                            tipo = item_processado.get('tipo', 'UNKNOWN')
                            descricao = item_processado.get('descricao_principal', '')
                            mostrar_observacao = item_processado.get('mostrar_observacao', False)
                            observation_description = item_processado.get('observation_description', '')
                            mostrar_responsaveis = item_processado.get('mostrar_responsaveis', False)
                            responsaveis = item_processado.get('responsaveis', '')
                            usuario = item_processado.get('usuario', 'Sistema')
                            
                            linha_item = f"- {tipo}: {descricao}"
                            
                            # Adiciona responsáveis se necessário
                            if mostrar_responsaveis and responsaveis:
                                linha_item += f"\n  Responsáveis: {responsaveis}"
                            
                            # Adiciona comentário se necessário
                            if mostrar_observacao and observation_description:
                                linha_item += f"\n  Comentário: {observation_description} (por {usuario})"
                            
                            itens_texto.append(linha_item)
                        
                        itens_texto_str = "\n".join(itens_texto)
                        corpo_texto = f"Nova(s) atualização(ões) no chamado #{process_instance_id}\n\n{itens_texto_str}\n\nLink: {link}"
                        
                        # Verifica se há anexos para baixar
                        anexos = []
                        for item in itens_nao_enviados:
                            if item.get('type') == 'ATTACHMENT':
                                attachment_description = item.get('attachmentDescription', '')
                                if attachment_description:
                                    try:
                                        logger.info(f"[HistoricoMonitor] Baixando anexo '{attachment_description}' do chamado {process_instance_id}...")
                                        conteudo_anexo = fluig_core.baixar_anexo_chamado(
                                            process_instance_id,
                                            attachment_description
                                        )
                                        
                                        if conteudo_anexo:
                                            # Determina tipo MIME baseado na extensão
                                            extensao = attachment_description.lower().split('.')[-1] if '.' in attachment_description else ''
                                            tipos_imagem = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
                                            tipo_mime = tipos_imagem.get(extensao, 'application/octet-stream')
                                            
                                            # Se for imagem, adiciona como inline com CID
                                            if tipo_mime.startswith('image/'):
                                                # Gera CID único usando a mesma lógica do fluxo_manager
                                                import hashlib
                                                attachment_id = item.get('attachmentId', '')
                                                cid_base = f"{attachment_id}_{attachment_description}" if attachment_id else attachment_description
                                                cid_hash = hashlib.md5(cid_base.encode()).hexdigest()[:8]
                                                cid = f"anexo_{cid_hash}"
                                                
                                                anexos.append({
                                                    'nome': attachment_description,
                                                    'conteudo': conteudo_anexo,
                                                    'tipo': tipo_mime,
                                                    'cid': cid
                                                })
                                                logger.info(f"[HistoricoMonitor] Anexo '{attachment_description}' baixado e preparado para envio (CID: {cid})")
                                            else:
                                                # Anexo não-imagem
                                                anexos.append({
                                                    'nome': attachment_description,
                                                    'conteudo': conteudo_anexo,
                                                    'tipo': tipo_mime
                                                })
                                                logger.info(f"[HistoricoMonitor] Anexo '{attachment_description}' baixado e preparado para envio")
                                        else:
                                            logger.warning(f"[HistoricoMonitor] Falha ao baixar anexo '{attachment_description}' do chamado {process_instance_id}")
                                    except Exception as e:
                                        logger.error(f"[HistoricoMonitor] Erro ao baixar anexo '{attachment_description}': {str(e)}")
                                        import traceback
                                        logger.debug(f"[HistoricoMonitor] Traceback: {traceback.format_exc()}")
                        
                        # Envia email
                        sucesso_envio = enviar_email(
                            email_remetente,
                            f"Atualização no Chamado #{process_instance_id}",
                            corpo_texto,
                            html=html_template,
                            anexos=anexos if anexos else None
                        )
                        
                        if sucesso_envio:
                            logger.info(
                                f"[HistoricoMonitor] Email de atualização enviado para {email_remetente} "
                                f"(chamado {process_instance_id}, {len(itens_nao_enviados)} item(ns))"
                            )
                            
                            # Marca itens como enviados
                            indices = self.historico_manager.obter_indices_itens_nao_enviados(
                                process_instance_id,
                                historico_novo
                            )
                            
                            if indices:
                                self.historico_manager.marcar_itens_como_enviados(
                                    process_instance_id,
                                    indices
                                )
                        else:
                            logger.warning(
                                f"[HistoricoMonitor] Falha ao enviar email de atualização para {email_remetente} "
                                f"(chamado {process_instance_id})"
                            )
                    except Exception as e:
                        logger.error(
                            f"[HistoricoMonitor] Erro ao enviar email de atualização para chamado {process_instance_id}: {str(e)}"
                        )
                        import traceback
                        logger.debug(f"[HistoricoMonitor] Traceback: {traceback.format_exc()}")
                else:
                    logger.warning(
                        f"[HistoricoMonitor] Email do remetente não encontrado para chamado {process_instance_id} - "
                        "não será enviada notificação"
                    )
            
            # Retorna resultado
                return {
                    'sucesso': True,
                'tem_atualizacoes': comparacao.get('tem_atualizacoes', False),
                    'novos_items': comparacao.get('novos_items', []),
                'itens_enviados': len(itens_nao_enviados) if itens_nao_enviados else 0,
                    'quantidade_novos': comparacao.get('quantidade_novos', 0),
                    'total_items_antigo': comparacao.get('total_items_antigo', 0),
                    'total_items_novo': comparacao.get('total_items_novo', 0)
                }
        except Exception as e:
            logger.error(f"[HistoricoMonitor] Erro ao verificar atualizações do chamado {process_instance_id}: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoMonitor] Traceback: {traceback.format_exc()}")
            return {
                'sucesso': False,
                'tem_atualizacoes': False,
                'novos_items': [],
                'erro': str(e)
            }
    
    def verificar_todos_chamados(self, ambiente: str = "PRD") -> Dict[str, Any]:
        """
        Verifica atualizações em todos os chamados monitorados
        
        Args:
            ambiente: Ambiente do Fluig (PRD ou QLD)
            
        Returns:
            Dicionário com resumo da verificação:
            - total_chamados: int
            - chamados_com_atualizacoes: int
            - chamados_verificados: int
            - chamados_com_erro: int
            - detalhes: Lista com detalhes de cada chamado
        """
        try:
            logger.info("[HistoricoMonitor] Iniciando verificação de todos os chamados monitorados...")
            
            # Lista todos os chamados monitorados
            chamados = self.historico_manager.listar_chamados_monitorados()
            
            if not chamados:
                logger.info("[HistoricoMonitor] Nenhum chamado monitorado encontrado")
                return {
                    'total_chamados': 0,
                    'chamados_com_atualizacoes': 0,
                    'chamados_verificados': 0,
                    'chamados_com_erro': 0,
                    'detalhes': []
                }
            
            logger.info(f"[HistoricoMonitor] Verificando {len(chamados)} chamado(s) monitorado(s)...")
            
            chamados_com_atualizacoes = 0
            chamados_verificados = 0
            chamados_com_erro = 0
            detalhes = []
            
            for process_instance_id in chamados:
                try:
                    # Verifica se o email do remetente está na lista de exclusão
                    email_remetente = self.historico_manager.obter_email_remetente(process_instance_id)
                    
                    if email_remetente and self.historico_manager._email_excluido_do_historico(email_remetente):
                        logger.debug(f"[HistoricoMonitor] Chamado {process_instance_id} excluído do monitoramento (email: {email_remetente})")
                        continue
                    
                    resultado = self.verificar_atualizacoes_chamado(process_instance_id, ambiente)
                    
                    if resultado.get('sucesso'):
                        chamados_verificados += 1
                        if resultado.get('tem_atualizacoes'):
                            chamados_com_atualizacoes += 1
                    else:
                        chamados_com_erro += 1
                    
                    detalhes.append({
                        'process_instance_id': process_instance_id,
                        'sucesso': resultado.get('sucesso', False),
                        'tem_atualizacoes': resultado.get('tem_atualizacoes', False),
                        'quantidade_novos': resultado.get('quantidade_novos', 0),
                        'erro': resultado.get('erro')
                    })
                    
                except Exception as e:
                    logger.error(f"[HistoricoMonitor] Erro ao verificar chamado {process_instance_id}: {str(e)}")
                    chamados_com_erro += 1
                    detalhes.append({
                        'process_instance_id': process_instance_id,
                        'sucesso': False,
                        'tem_atualizacoes': False,
                        'erro': str(e)
                    })
            
            logger.info(
                f"[HistoricoMonitor] Verificação concluída: "
                f"{chamados_verificados} verificado(s), "
                f"{chamados_com_atualizacoes} com atualizações, "
                f"{chamados_com_erro} com erro"
            )
            
            return {
                'total_chamados': len(chamados),
                'chamados_com_atualizacoes': chamados_com_atualizacoes,
                'chamados_verificados': chamados_verificados,
                'chamados_com_erro': chamados_com_erro,
                'detalhes': detalhes
            }
            
        except Exception as e:
            logger.error(f"[HistoricoMonitor] Erro ao verificar todos os chamados: {str(e)}")
            import traceback
            logger.debug(f"[HistoricoMonitor] Traceback: {traceback.format_exc()}")
            return {
                'total_chamados': 0,
                'chamados_com_atualizacoes': 0,
                'chamados_verificados': 0,
                'chamados_com_erro': 1,
                'detalhes': [],
                'erro': str(e)
            }
    
    def _loop_verificacao(self, ambiente: str = "PRD"):
        """
        Loop principal de verificação (executado em thread separada)
        
        Args:
            ambiente: Ambiente do Fluig (PRD ou QLD)
        """
        logger.info(f"[HistoricoMonitor] Loop de verificação iniciado - Intervalo: {self.intervalo_minutos} minuto(s)")
        
        while not self._stop_event.is_set():
            try:
                # Verifica se o monitoramento está habilitado antes de processar
                historico_enabled = self._verificar_monitor_enabled()
                if not historico_enabled:
                    logger.info("[HistoricoMonitor] Monitoramento desabilitado - aguardando próximo ciclo")
                    if self._stop_event.wait(timeout=self.intervalo_segundos):
                        break
                    continue
                
                # Recarrega intervalo antes de cada ciclo (pode ter sido alterado)
                novo_intervalo = self._obter_intervalo_atual()
                if novo_intervalo != self.intervalo_minutos:
                    logger.info(f"[HistoricoMonitor] Intervalo atualizado: {self.intervalo_minutos} -> {novo_intervalo} minuto(s)")
                    self.intervalo_minutos = novo_intervalo
                    self.intervalo_segundos = novo_intervalo * 60
                
                # Verifica todos os chamados
                resultado = self.verificar_todos_chamados(ambiente)
                
                logger.info(
                    f"[HistoricoMonitor] Verificação periódica concluída: "
                    f"{resultado.get('chamados_com_atualizacoes', 0)} chamado(s) com atualizações"
                )
                
                # Aguarda intervalo ou até receber sinal de parada
                if self._stop_event.wait(timeout=self.intervalo_segundos):
                    # Recebeu sinal de parada
                    break
                    
            except Exception as e:
                logger.error(f"[HistoricoMonitor] Erro no loop de verificação: {str(e)}")
                # Em caso de erro, aguarda um tempo menor antes de tentar novamente
                if self._stop_event.wait(timeout=300):  # 5 minutos
                    break
        
        logger.info("[HistoricoMonitor] Loop de verificação finalizado")
    
    def iniciar_monitoramento(self, ambiente: str = "PRD", em_background: bool = True):
        """
        Inicia o monitoramento periódico de históricos
        
        Args:
            ambiente: Ambiente do Fluig (PRD ou QLD)
            em_background: Se True, executa em thread separada (padrão: True)
        """
        if self._rodando:
            logger.warning("[HistoricoMonitor] Monitoramento já está em execução")
            return
        
        self._rodando = True
        self._stop_event.clear()
        
        if em_background:
            # Executa em thread separada
            self._thread = threading.Thread(
                target=self._loop_verificacao,
                args=(ambiente,),
                daemon=True,
                name="HistoricoMonitor"
            )
            self._thread.start()
            logger.info("[HistoricoMonitor] Monitoramento iniciado em background")
        else:
            # Executa no thread atual (bloqueante)
            logger.info("[HistoricoMonitor] Monitoramento iniciado no thread atual")
            self._loop_verificacao(ambiente)
    
    def parar_monitoramento(self):
        """
        Para o monitoramento periódico
        """
        if not self._rodando:
            logger.warning("[HistoricoMonitor] Monitoramento não está em execução")
            return
        
        logger.info("[HistoricoMonitor] Parando monitoramento...")
        self._stop_event.set()
        self._rodando = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("[HistoricoMonitor] Thread de monitoramento não finalizou a tempo")
            else:
                logger.info("[HistoricoMonitor] Monitoramento parado com sucesso")
    
    def esta_rodando(self) -> bool:
        """
        Verifica se o monitoramento está em execução
        
        Returns:
            True se está rodando, False caso contrário
        """
        return self._rodando

    def _verificar_monitor_enabled(self) -> bool:
        """Verifica se o monitoramento está habilitado (sem importação circular)"""
        try:
            from src.configs.config_manager import get_config_manager_gerais
            config_manager = get_config_manager_gerais()
            configs = config_manager.carregar_configuracao()
            enabled_str = configs.get('historico_monitor_enabled', '')
            if enabled_str and enabled_str.strip():
                return enabled_str.lower() in ('true', '1', 'yes')
        except Exception as e:
            logger.warning(f"[HistoricoMonitor] Erro ao verificar status: {str(e)}")
        
        # Fallback para .env
        from src.modelo_dados.modelo_settings import ConfigEnvSetings
        historico_enabled = getattr(ConfigEnvSetings, 'HISTORICO_MONITOR_ENABLED', 'true').lower()
        return historico_enabled in ('true', '1', 'yes')
    
    def _obter_intervalo_atual(self) -> float:
        """Obtém o intervalo atual das configurações em minutos (sem importação circular)"""
        try:
            from src.configs.config_manager import get_config_manager_gerais
            config_manager = get_config_manager_gerais()
            configs = config_manager.carregar_configuracao()
            intervalo_str = configs.get('historico_check_interval_minutes', '')
            if intervalo_str and intervalo_str.strip():
                return float(intervalo_str)
        except Exception as e:
            logger.warning(f"[HistoricoMonitor] Erro ao obter intervalo: {str(e)}")
        
        # Fallback para .env (60 minutos = 1 hora padrão)
        from src.modelo_dados.modelo_settings import ConfigEnvSetings
        return float(getattr(ConfigEnvSetings, 'HISTORICO_CHECK_INTERVAL_MINUTES', 60.0))