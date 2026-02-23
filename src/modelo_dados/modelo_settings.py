from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigEnv(BaseSettings):
    
    WHITE_LIST_DOMAINS: str
    BLACK_LIST_EMAILS: str

    CK: str
    CS: str
    TK: str
    TS: str
    URL_FLUIG_QLD: str

    CK_QLD: str
    CS_QLD: str
    TK_QLD: str
    TS_QLD: str
    URL_FLUIG_PRD: str


    ADMIN_COLLEAGUE_ID: str
    FLUIG_ADMIN_USER: str
    FLUIG_ADMIN_PASS: str

    USER_COLLEAGUE_ID: str
    FLUIG_USER_NAME: str
    FLUIG_USER_PASS: str

    USER_COLLEAGUE_ID_QLD: str
    FLUIG_USER_NAME_QLD: str
    FLUIG_USER_PASS_QLD: str

    API_KEY: str
    API_NAME: str

    IA_KEYS: str
    IA_MODELS: str
    
    
    # Lista de emails que devem usar FakeUser para abertura de chamados
    # Formato no .env: EMAILS_LIST=email1@dominio.com,email2@dominio.com
    EMAILS_LIST: str = ""
    
    #-----------------------CONTA DE SERVIÇO GOOGLE-----------------------
    TYPE: str
    PROJECT_ID: str
    PRIVCATE_JEY_ID: str
    PRIVATE_KEY: str
    CLIENT_EMAIL: str
    CLIENT_ID: str
    AUTH_URI: str
    TOKEN_URI: str
    AUTH_PROVIDER_X509_CERT_URL: str
    CLIENT_X509_CERT_URL: str
    UNIVERSE_DOMAIN: str

    #-------------------------ID PASTA GOOGLE DRIVE ----------------------
    # ID da pasta do Google Drive para anexos (opcional)
    FOLDER_ID_DRIVE: str = ""
    
    # ID da pasta do Google Drive para configurações do sistema
    # Se não configurado, usa FOLDER_ID_DRIVE como fallback
    FOLDER_ID_DRIVE_CONFIGS: str = ""
    
    # Habilita/desabilita sincronização automática de configurações com Google Drive
    # Valores aceitos: "true", "True", "1" (habilitado) ou "false", "False", "0" (desabilitado)
    # Padrão: "false" (desabilitado - requer configuração manual)
    DRIVE_SYNC_ENABLED: str = "false"
    #-----------------------------------------------------------------------

    #-------------------------GOOGLE OAUTH (Webapp)------------------------
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_PROJECT_ID: str = ""
    GOOGLE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL: str = "https://www.googleapis.com/oauth2/v1/certs"
    GOOGLE_REDIRECT_URIS: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    #-----------------------------------------------------------------------

    #-------------------------API ENDPOINTS (Webapp)-----------------------
    API_ENDPOINT_FUNCIONARIO: str = ""
    API_ENDPOINT_CHAMADO: str = ""
    #-----------------------------------------------------------------------

    #-------------------------GMAIL MONITOR (Monitoramento de Emails)-----
    # Habilita/desabilita o serviço de monitoramento de emails para abrir chamados
    # Valores aceitos: "true", "True", "1" (habilitado) ou "false", "False", "0" (desabilitado)
    # Padrão: "true" (habilitado)
    GMAIL_MONITOR_ENABLED: str = "true"
    
    #-------------------------BROWSER LOGIN (Login via Navegador)-----------
    # Habilita/desabilita o login via navegador (Selenium/ChromeDriver) em todo o projeto
    # Valores aceitos: "true", "True", "1" (habilitado) ou "false", "False", "0" (desabilitado)
    # Padrão: "true" (habilitado)
    # Quando desabilitado, todas as funções que dependem de login via browser retornarão erro
    # Útil para ambientes onde apenas OAuth 1.0 é usado e não há necessidade de cookies
    BROWSER_LOGIN_ENABLED: str = "true"
    
    # Email do usuário para delegação de domínio (opcional)
    # Se não configurado, usa a conta de serviço diretamente
    GMAIL_DELEGATE_USER: str = ""
    
    # Endpoints da API para abertura de chamados
    API_ENDPOINT_CHAMADO_UISA: str = "https://api-fluig-python-186726132534.us-east1.run.app/api/v1/fluig/prd/chamados/abrir"
    API_ENDPOINT_CHAMADO_MOVTI: str = "https://api-fluig-python-186726132534.us-east1.run.app/terceiro/movit/chamado/abrir-classificado"
    
    # Ambiente do Fluig para monitoramento (prd ou qld)
    GMAIL_MONITOR_AMBIENTE: str = "prd"
    
    # Intervalo de verificação de emails (em minutos)
    GMAIL_CHECK_INTERVAL: int = 20
    
    # Lista de emails que devem ser excluídos do monitoramento de histórico
    # Formato no .env: HISTORICO_EXCLUDE_EMAILS=email1@dominio.com,email2@dominio.com
    HISTORICO_EXCLUDE_EMAILS: str = ""
    
    # Intervalo de verificação de histórico (em minutos)
    HISTORICO_CHECK_INTERVAL_MINUTES: float = 60.0
    
    # Intervalo de verificação de histórico (em horas) - alternativa ao minutos
    HISTORICO_CHECK_INTERVAL_HOURS: float = 1.0
    
    # Habilita ou desabilita o monitoramento de histórico
    HISTORICO_MONITOR_ENABLED: str = "true"
    
    # Padrões para deduplicação de emails (regex ou palavras-chave separadas por vírgula)
    # Exemplo: UUID:.*,MAC:.*,Processo ID:.*
    # Ou palavras-chave simples: UUID:,MAC:,Processo ID:
    EMAIL_DEDUPLICATION_PATTERNS: str = ""
    
    # Lista de emails que devem passar pela verificação de deduplicação
    # Se vazio, todos os emails serão verificados. Se preenchido, apenas esses emails serão verificados
    # Formato: EMAIL_DEDUPLICATION_EMAILS=email1@dominio.com,email2@dominio.com
    EMAIL_DEDUPLICATION_EMAILS: str = ""
    #-----------------------------------------------------------------------

    #-------------------------FORESCOUT API (Integração Forescout)---------
    # Credenciais para autenticação na API do Forescout
    # Host do servidor Forescout (ex: forescout.example.com)
    # A URL será construída automaticamente usando HTTPS (https://FORESCOUT_HOST)
    FORESCOUT_HOST: str = ""
    # Usuário para autenticação na API do Forescout
    FORESCOUT_USER: str = ""
    # Senha para autenticação na API do Forescout
    FORESCOUT_PASS: str = ""
    #-----------------------------------------------------------------------

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
ConfigEnvSetings = ConfigEnv()