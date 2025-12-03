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

        if os.environ.get('K_SERVICE'):
            logger.info("[ConfigurarDriver] Ambiente Cloud Run detectado. Forçando modo headless.")
            headless = True

        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless=new')
        

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')

        chrome_options.add_argument('--remote-debugging-pipe')
        chrome_options.add_argument('--disable-software-rasterizer')

        chrome_options.add_argument('--window-size=1920,1080')
        

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

