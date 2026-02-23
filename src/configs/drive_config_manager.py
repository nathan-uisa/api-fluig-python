"""
Gerenciador de configurações no Google Drive
Sincroniza arquivos de configuração entre o sistema local e o Google Drive
"""
import io
from pathlib import Path
from typing import Optional, Dict, List
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.modelo_dados.modelo_settings import ConfigEnvSetings
from src.utilitarios_centrais.logger import logger


class DriveConfigManager:
    """Gerencia o upload e download de configurações no Google Drive"""
    
    def __init__(self):
        """Inicializa o gerenciador de configurações do Drive"""
        self.service = None
        self.base_folder_id = None
        self._inicializar_servico()
        self._obter_pasta_configs()
    
    def _inicializar_servico(self):
        """Inicializa o serviço do Google Drive"""
        try:
            logger.debug("[DriveConfigManager] Criando serviço do Google Drive...")
            
            credenciais_info = {
                "type": ConfigEnvSetings.TYPE,
                "project_id": ConfigEnvSetings.PROJECT_ID,
                "private_key_id": ConfigEnvSetings.PRIVCATE_JEY_ID,
                "private_key": ConfigEnvSetings.PRIVATE_KEY.replace('\\n', '\n'),
                "client_email": ConfigEnvSetings.CLIENT_EMAIL,
                "client_id": ConfigEnvSetings.CLIENT_ID,
                "auth_uri": ConfigEnvSetings.AUTH_URI,
                "token_uri": ConfigEnvSetings.TOKEN_URI,
                "auth_provider_x509_cert_url": ConfigEnvSetings.AUTH_PROVIDER_X509_CERT_URL,
                "client_x509_cert_url": ConfigEnvSetings.CLIENT_X509_CERT_URL,
                "universe_domain": ConfigEnvSetings.UNIVERSE_DOMAIN
            }
            
            credentials = service_account.Credentials.from_service_account_info(
                credenciais_info,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            # Se houver usuário configurado para delegação, usa ele
            if hasattr(ConfigEnvSetings, 'GMAIL_DELEGATE_USER') and ConfigEnvSetings.GMAIL_DELEGATE_USER:
                credentials = credentials.with_subject(ConfigEnvSetings.GMAIL_DELEGATE_USER)
            
            self.service = build('drive', 'v3', credentials=credentials)
            logger.debug("[DriveConfigManager] Serviço do Google Drive criado com sucesso")
            
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao criar serviço do Google Drive: {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            self.service = None
    
    def _obter_pasta_configs(self):
        """Obtém o ID da pasta de configurações no Drive"""
        try:
            # Tenta obter da variável de ambiente
            if hasattr(ConfigEnvSetings, 'FOLDER_ID_DRIVE_CONFIGS') and ConfigEnvSetings.FOLDER_ID_DRIVE_CONFIGS:
                self.base_folder_id = ConfigEnvSetings.FOLDER_ID_DRIVE_CONFIGS
                logger.debug(f"[DriveConfigManager] Usando pasta de configurações: {self.base_folder_id}")
                return
            
            # Se não configurado, usa a pasta geral do Drive (se existir)
            if hasattr(ConfigEnvSetings, 'FOLDER_ID_DRIVE') and ConfigEnvSetings.FOLDER_ID_DRIVE:
                self.base_folder_id = ConfigEnvSetings.FOLDER_ID_DRIVE
                logger.debug(f"[DriveConfigManager] Usando pasta geral do Drive: {self.base_folder_id}")
                return
            
            logger.warning("[DriveConfigManager] Nenhuma pasta do Drive configurada")
            self.base_folder_id = None
            
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao obter pasta de configurações: {str(e)}")
            self.base_folder_id = None
    
    def _criar_pasta_se_nao_existir(self, nome_pasta: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Cria uma pasta no Drive se ela não existir
        
        Args:
            nome_pasta: Nome da pasta a criar
            parent_id: ID da pasta pai (None para pasta raiz)
            
        Returns:
            ID da pasta criada ou existente, None em caso de erro
        """
        if not self.service:
            logger.error("[DriveConfigManager] Serviço do Drive não inicializado")
            return None
        
        try:
            # Busca pasta existente
            query = f"name='{nome_pasta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            else:
                query += " and 'root' in parents"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                logger.debug(f"[DriveConfigManager] Pasta '{nome_pasta}' já existe (ID: {folder_id})")
                return folder_id
            
            # Cria pasta se não existir
            file_metadata = {
                'name': nome_pasta,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"[DriveConfigManager] Pasta '{nome_pasta}' criada (ID: {folder_id})")
            return folder_id
            
        except HttpError as e:
            logger.error(f"[DriveConfigManager] Erro HTTP ao criar/buscar pasta '{nome_pasta}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao criar/buscar pasta '{nome_pasta}': {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            return None
    
    def _buscar_arquivo_por_nome(self, nome_arquivo: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        Busca um arquivo no Drive pelo nome
        
        Args:
            nome_arquivo: Nome do arquivo a buscar
            folder_id: ID da pasta onde buscar (None para buscar em todas)
            
        Returns:
            ID do arquivo encontrado ou None
        """
        if not self.service:
            return None
        
        try:
            query = f"name='{nome_arquivo}' and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime)",
                pageSize=1
            ).execute()
            
            # Valida se results é um dicionário
            if not isinstance(results, dict):
                logger.error(f"[DriveConfigManager] Resposta inesperada ao buscar arquivo '{nome_arquivo}': tipo {type(results)}")
                return None
            
            files = results.get('files', [])
            if files and isinstance(files, list) and len(files) > 0:
                arquivo = files[0]
                if isinstance(arquivo, dict):
                    return arquivo.get('id')
            
            return None
            
        except HttpError as e:
            logger.error(f"[DriveConfigManager] Erro HTTP ao buscar arquivo '{nome_arquivo}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao buscar arquivo '{nome_arquivo}': {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            return None
    
    def upload_config(self, caminho_local: Path, nome_arquivo_drive: Optional[str] = None, 
                     subpasta: Optional[str] = None) -> bool:
        """
        Faz upload de um arquivo de configuração para o Drive
        
        Args:
            caminho_local: Caminho do arquivo local
            nome_arquivo_drive: Nome do arquivo no Drive (None para usar o mesmo nome)
            subpasta: Nome da subpasta onde salvar (ex: 'user_configs')
            
        Returns:
            True se upload foi bem-sucedido, False caso contrário
        """
        if not self.service:
            logger.warning("[DriveConfigManager] Serviço do Drive não disponível - pulando upload")
            return False
        
        if not self.base_folder_id:
            logger.warning("[DriveConfigManager] Pasta do Drive não configurada - pulando upload")
            return False
        
        if not caminho_local.exists():
            logger.warning(f"[DriveConfigManager] Arquivo local não existe: {caminho_local}")
            return False
        
        try:
            # Lê o conteúdo do arquivo
            with open(caminho_local, 'rb') as f:
                conteudo = f.read()
            
            nome_arquivo = nome_arquivo_drive or caminho_local.name
            
            # Determina a pasta de destino
            pasta_destino_id = self.base_folder_id
            if subpasta:
                pasta_destino_id = self._criar_pasta_se_nao_existir(subpasta, self.base_folder_id)
                if not pasta_destino_id:
                    logger.error(f"[DriveConfigManager] Não foi possível criar/acessar subpasta '{subpasta}'")
                    return False
            
            # Busca se arquivo já existe
            arquivo_id = self._buscar_arquivo_por_nome(nome_arquivo, pasta_destino_id)
            
            media = MediaIoBaseUpload(
                io.BytesIO(conteudo),
                mimetype='text/plain',
                resumable=True
            )
            
            if arquivo_id:
                # Atualiza arquivo existente
                # Para atualização, não podemos usar 'parents' diretamente
                file_metadata = {
                    'name': nome_arquivo
                }
                
                # Se precisar mover o arquivo para outra pasta, usa addParents/removeParents
                if pasta_destino_id:
                    # Obtém os pais atuais do arquivo
                    arquivo_atual = self.service.files().get(
                        fileId=arquivo_id,
                        fields='parents'
                    ).execute()
                    pais_atuais = arquivo_atual.get('parents', [])
                    
                    # Se o arquivo não está na pasta correta, move ele
                    if pasta_destino_id not in pais_atuais:
                        # Remove dos pais antigos e adiciona ao novo
                        self.service.files().update(
                            fileId=arquivo_id,
                            addParents=pasta_destino_id,
                            removeParents=','.join(pais_atuais) if pais_atuais else None,
                            fields='id'
                        ).execute()
                
                # Atualiza o conteúdo do arquivo
                file = self.service.files().update(
                    fileId=arquivo_id,
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"[DriveConfigManager] Arquivo '{nome_arquivo}' atualizado no Drive (ID: {arquivo_id})")
            else:
                # Cria novo arquivo
                file_metadata = {
                    'name': nome_arquivo
                }
                if pasta_destino_id:
                    file_metadata['parents'] = [pasta_destino_id]
                
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                arquivo_id = file.get('id')
                logger.info(f"[DriveConfigManager] Arquivo '{nome_arquivo}' enviado para o Drive (ID: {arquivo_id})")
            
            return True
            
        except HttpError as e:
            logger.error(f"[DriveConfigManager] Erro HTTP ao fazer upload de '{caminho_local}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao fazer upload de '{caminho_local}': {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            return False
    
    def download_config(self, nome_arquivo: str, caminho_local: Path, 
                       subpasta: Optional[str] = None) -> bool:
        """
        Faz download de um arquivo de configuração do Drive
        
        Args:
            nome_arquivo: Nome do arquivo no Drive
            caminho_local: Caminho onde salvar o arquivo localmente
            subpasta: Nome da subpasta onde buscar (ex: 'user_configs')
            
        Returns:
            True se download foi bem-sucedido, False caso contrário
        """
        if not self.service:
            logger.warning("[DriveConfigManager] Serviço do Drive não disponível - pulando download")
            return False
        
        if not self.base_folder_id:
            logger.warning("[DriveConfigManager] Pasta do Drive não configurada - pulando download")
            return False
        
        try:
            # Determina a pasta de origem
            pasta_origem_id = self.base_folder_id
            if subpasta:
                pasta_origem_id = self._criar_pasta_se_nao_existir(subpasta, self.base_folder_id)
                if not pasta_origem_id:
                    logger.warning(f"[DriveConfigManager] Subpasta '{subpasta}' não encontrada")
                    return False
            
            # Busca o arquivo
            arquivo_id = self._buscar_arquivo_por_nome(nome_arquivo, pasta_origem_id)
            if not arquivo_id:
                logger.warning(f"[DriveConfigManager] Arquivo '{nome_arquivo}' não encontrado no Drive")
                return False
            
            # Faz download
            request = self.service.files().get_media(fileId=arquivo_id)
            conteudo = io.BytesIO()
            downloader = MediaIoBaseDownload(conteudo, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Salva arquivo localmente
            caminho_local.parent.mkdir(parents=True, exist_ok=True)
            with open(caminho_local, 'wb') as f:
                f.write(conteudo.getvalue())
            
            logger.info(f"[DriveConfigManager] Arquivo '{nome_arquivo}' baixado do Drive para {caminho_local}")
            return True
            
        except HttpError as e:
            logger.error(f"[DriveConfigManager] Erro HTTP ao fazer download de '{nome_arquivo}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao fazer download de '{nome_arquivo}': {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            return False
    
    def listar_configs(self, subpasta: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Lista todos os arquivos de configuração no Drive
        
        Args:
            subpasta: Nome da subpasta onde listar (None para pasta raiz)
            
        Returns:
            Lista de dicionários com informações dos arquivos
        """
        if not self.service:
            return []
        
        if not self.base_folder_id:
            return []
        
        try:
            pasta_id = self.base_folder_id
            if subpasta:
                pasta_id = self._criar_pasta_se_nao_existir(subpasta, self.base_folder_id)
                if not pasta_id:
                    return []
            
            results = self.service.files().list(
                q=f"'{pasta_id}' in parents and trashed=false",
                fields="files(id, name, modifiedTime, size)",
                pageSize=100
            ).execute()
            
            arquivos = []
            for file in results.get('files', []):
                arquivos.append({
                    'id': file.get('id'),
                    'nome': file.get('name'),
                    'modificado': file.get('modifiedTime', ''),
                    'tamanho': file.get('size', '0')
                })
            
            return arquivos
            
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao listar arquivos: {str(e)}")
            return []
    
    def ler_config_do_drive(self, nome_arquivo: str, subpasta: Optional[str] = None) -> Optional[str]:
        """
        Lê conteúdo de um arquivo de configuração diretamente do Drive
        
        Args:
            nome_arquivo: Nome do arquivo no Drive
            subpasta: Nome da subpasta onde buscar (ex: 'user_configs')
            
        Returns:
            Conteúdo do arquivo como string ou None se não encontrado
        """
        if not self.service:
            return None
        
        if not self.base_folder_id:
            return None
        
        try:
            # Determina a pasta de origem
            pasta_origem_id = self.base_folder_id
            if subpasta:
                pasta_origem_id = self._criar_pasta_se_nao_existir(subpasta, self.base_folder_id)
                if not pasta_origem_id:
                    return None
            
            # Busca o arquivo
            arquivo_id = self._buscar_arquivo_por_nome(nome_arquivo, pasta_origem_id)
            if not arquivo_id:
                return None
            
            # Faz download
            request = self.service.files().get_media(fileId=arquivo_id)
            conteudo = io.BytesIO()
            downloader = MediaIoBaseDownload(conteudo, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Retorna conteúdo como string
            return conteudo.getvalue().decode('utf-8')
            
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao ler arquivo '{nome_arquivo}' do Drive: {str(e)}")
            return None
    
    def salvar_config_no_drive(self, conteudo: str, nome_arquivo: str, subpasta: Optional[str] = None) -> bool:
        """
        Salva conteúdo de configuração diretamente no Drive
        
        Args:
            conteudo: Conteúdo do arquivo como string
            nome_arquivo: Nome do arquivo no Drive
            subpasta: Nome da subpasta onde salvar (ex: 'user_configs')
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if not self.service:
            return False
        
        if not self.base_folder_id:
            return False
        
        try:
            # Determina a pasta de destino
            pasta_destino_id = self.base_folder_id
            if subpasta:
                pasta_destino_id = self._criar_pasta_se_nao_existir(subpasta, self.base_folder_id)
                if not pasta_destino_id:
                    return False
            
            # Converte conteúdo para bytes
            conteudo_bytes = conteudo.encode('utf-8')
            
            # Busca se arquivo já existe
            arquivo_id = self._buscar_arquivo_por_nome(nome_arquivo, pasta_destino_id)
            
            media = MediaIoBaseUpload(
                io.BytesIO(conteudo_bytes),
                mimetype='text/plain',
                resumable=True
            )
            
            if arquivo_id:
                # Atualiza arquivo existente
                file_metadata = {
                    'name': nome_arquivo
                }
                
                # Se precisar mover o arquivo para outra pasta, usa addParents/removeParents
                if pasta_destino_id:
                    # Obtém os pais atuais do arquivo
                    arquivo_atual = self.service.files().get(
                        fileId=arquivo_id,
                        fields='parents'
                    ).execute()
                    pais_atuais = arquivo_atual.get('parents', [])
                    
                    # Se o arquivo não está na pasta correta, move ele
                    if pasta_destino_id not in pais_atuais:
                        # Remove dos pais antigos e adiciona ao novo
                        self.service.files().update(
                            fileId=arquivo_id,
                            addParents=pasta_destino_id,
                            removeParents=','.join(pais_atuais) if pais_atuais else None,
                            fields='id'
                        ).execute()
                
                # Atualiza o conteúdo do arquivo
                file = self.service.files().update(
                    fileId=arquivo_id,
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"[DriveConfigManager] Arquivo '{nome_arquivo}' atualizado no Drive (ID: {arquivo_id})")
            else:
                # Cria novo arquivo
                file_metadata = {
                    'name': nome_arquivo
                }
                if pasta_destino_id:
                    file_metadata['parents'] = [pasta_destino_id]
                
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                arquivo_id = file.get('id')
                logger.info(f"[DriveConfigManager] Arquivo '{nome_arquivo}' criado no Drive (ID: {arquivo_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao salvar arquivo '{nome_arquivo}' no Drive: {str(e)}")
            import traceback
            logger.debug(f"[DriveConfigManager] Traceback: {traceback.format_exc()}")
            return False


# Instância global
_drive_config_manager = None


def get_drive_config_manager() -> Optional[DriveConfigManager]:
    """
    Retorna a instância global do gerenciador de configurações do Drive
    Retorna None se a sincronização estiver desabilitada ou houver erro
    Agora é obrigatório ter DRIVE_SYNC_ENABLED=true para o sistema funcionar
    """
    global _drive_config_manager
    
    # Verifica se sincronização está habilitada (obrigatório agora)
    if hasattr(ConfigEnvSetings, 'DRIVE_SYNC_ENABLED'):
        sync_enabled = ConfigEnvSetings.DRIVE_SYNC_ENABLED.lower() in ('true', '1', 'yes')
        if not sync_enabled:
            logger.warning("[DriveConfigManager] DRIVE_SYNC_ENABLED=false - Sistema requer Google Drive habilitado")
            return None
    
    if _drive_config_manager is None:
        try:
            _drive_config_manager = DriveConfigManager()
            if not _drive_config_manager.service:
                logger.error("[DriveConfigManager] Falha ao criar serviço do Google Drive")
                _drive_config_manager = None
        except Exception as e:
            logger.error(f"[DriveConfigManager] Erro ao inicializar: {str(e)}")
            _drive_config_manager = None
    
    return _drive_config_manager


def sincronizar_configuracoes_inicial():
    """
    Função desabilitada - não sincroniza mais arquivos locais
    Sistema agora usa apenas Google Drive
    """
    logger.debug("[DriveConfigManager] Sincronização inicial desabilitada - sistema usa apenas Google Drive")
