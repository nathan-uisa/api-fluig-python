"""Configuração automatizada do ChromeDriver."""
import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

try:
    from src.utilitarios_centrais.logger import logger
except ImportError:  # fallback para execuções isoladas
    logger = logging.getLogger(__name__)


def ConfigurarDriver(headless: bool = True):
    """
    Configura e retorna uma instância do ChromeDriver automaticamente compatível
    com o SO e a versão do Google Chrome instalada.
    """
    try:
        # Detecta se está rodando em Docker ou Cloud Run
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('K_SERVICE') or os.environ.get('DOCKER_CONTAINER')
        
        if is_docker or os.environ.get('K_SERVICE'):
            logger.info("[ConfigurarDriver] Ambiente Docker/Cloud Run detectado. Forçando modo headless.")
            headless = True

        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless=new')
        
        # Opções essenciais para Docker/containers
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-software-rasterizer')
        
        # Opções adicionais para estabilidade em containers
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # Para ambientes sem display
        if is_docker:
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--remote-debugging-address=0.0.0.0')
        else:
            chrome_options.add_argument('--remote-debugging-pipe')

        chrome_options.add_argument('--window-size=1920,1080')
        
        # Estratégia de carregamento de página
        chrome_options.page_load_strategy = 'normal'

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        logger.info(f"[ConfigurarDriver] Inicializando ChromeDriver (headless={headless})")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        logger.info("[ConfigurarDriver] ChromeDriver configurado com sucesso.")
        return driver
    except Exception as e:
        logger.error(f"[ConfigurarDriver] Erro crítico ao configurar ChromeDriver: {str(e)}")
        raise

