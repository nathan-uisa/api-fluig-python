from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigEnv(BaseSettings):
    
    WHITE_LIST_DOMAINS: str
    BLACK_LIST_EMAILS: str
    EMAILS_LIST:str
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
    
    MOVIT_USER_COLLEAGUE_ID: str
    
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
    FOLDER_ID_DRIVE: str
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
ConfigEnvSetings = ConfigEnv()