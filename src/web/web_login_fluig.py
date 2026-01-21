"""Módulo para realizar login no Fluig via navegador"""
import time
from typing import Optional, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utilitarios_centrais.logger import logger
from src.web.web_driver import ConfigurarDriver
from src.web.web_cookies import obter_cookies, salvar_cookies
from src.modelo_dados.modelo_settings import ConfigEnvSetings


def fazer_login_fluig(ambiente: str = "PRD", usuario: str = None, senha: str = None) -> Optional[Any]:
    """
    Realiza login no Fluig via navegador e salva cookies
    
    Args:
        ambiente: Ambiente ('PRD' ou 'QLD')
        usuario: Usuário para login (se None, usa FLUIG_ADMIN_USER)
        senha: Senha para login (se None, usa FLUIG_ADMIN_PASS)
    
    Returns:
        WebDriver se login bem-sucedido, None caso contrário
    """
    driver = None
    try:
        # Seleciona URL baseado no ambiente
        ambiente_upper = ambiente.upper()
        if ambiente_upper == "QLD":
            url_fluig = ConfigEnvSetings.URL_FLUIG_QLD
            ambiente_log = "QLD"
        else:
            url_fluig = ConfigEnvSetings.URL_FLUIG_PRD
            ambiente_log = "PRD"
        
        # Usa credenciais fornecidas ou padrão
        if not usuario:
            usuario = ConfigEnvSetings.FLUIG_ADMIN_USER
        if not senha:
            senha = ConfigEnvSetings.FLUIG_ADMIN_PASS
        
        if not usuario or not senha:
            logger.error("[fazer_login_fluig] Credenciais não configuradas")
            return None
        
        logger.info(f"[fazer_login_fluig] Iniciando login no Fluig {ambiente_log} - URL: {url_fluig}")
        driver = ConfigurarDriver(headless=False)
        driver.get(url_fluig)
        
        wait = WebDriverWait(driver, 20)
        

        logger.info("[fazer_login_fluig] Preenchendo campo de usuário...")
        xpaths_usuario = [
            "//input[@id='username']",
            "//input[@name='username']",
            "//input[@type='text']",
            "//input[@placeholder*='usuário' or @placeholder*='user']"
        ]
        
        campo_usuario = None
        for xpath in xpaths_usuario:
            try:
                campo_usuario = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                logger.info(f"[fazer_login_fluig] Campo usuário encontrado: {xpath}")
                break
            except TimeoutException:
                continue
        
        if not campo_usuario:
            logger.error("[fazer_login_fluig] Campo de usuário não encontrado")
            driver.quit()
            return None
        
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)
        
        # Aguarda e preenche campo de senha
        logger.info("[fazer_login_fluig] Preenchendo campo de senha...")
        xpaths_senha = [
            "//input[@id='password']",
            "//input[@name='password']",
            "//input[@type='password']"
        ]
        
        campo_senha = None
        for xpath in xpaths_senha:
            try:
                campo_senha = driver.find_element(By.XPATH, xpath)
                if campo_senha.is_displayed():
                    logger.info(f"[fazer_login_fluig] Campo senha encontrado: {xpath}")
                    break
            except NoSuchElementException:
                continue
        
        if not campo_senha:
            logger.error("[fazer_login_fluig] Campo de senha não encontrado")
            driver.quit()
            return None
        
        campo_senha.clear()
        campo_senha.send_keys(senha)
        

        logger.info("[fazer_login_fluig] Procurando botão de login...")
        time.sleep(1)
        
        xpaths_botao = [
            "//button[@type='submit']",
            "//input[@type='submit']",
            "//button[contains(text(), 'Entrar')]",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Acessar')]",
            "//button[contains(@class, 'login')]"
        ]
        
        botao_login = None
        for xpath in xpaths_botao:
            try:
                botao_login = driver.find_element(By.XPATH, xpath)
                if botao_login.is_displayed() and botao_login.is_enabled():
                    logger.info(f"[fazer_login_fluig] Botão encontrado: {xpath}")
                    break
            except NoSuchElementException:
                continue
        
        if not botao_login:
            logger.error("[fazer_login_fluig] Botão de login não encontrado")
            driver.quit()
            return None
        
        botao_login.click()
        logger.info("[fazer_login_fluig] Botão clicado, aguardando redirecionamento...")
        

        time.sleep(5)
        

        if 'login' in driver.current_url.lower() or 'signin' in driver.current_url.lower():
            logger.warning("[fazer_login_fluig] Ainda na página de login - credenciais inválidas")
            driver.quit()
            return None
        
        logger.info(f"[fazer_login_fluig] Login bem-sucedido! URL: {driver.current_url}")
        time.sleep(3)
        

        logger.info("[fazer_login_fluig] Obtendo cookies...")
        cookies = obter_cookies(driver)
        
        if cookies:
            salvar_cookies(cookies, ambiente, usuario)
            logger.info(f"[fazer_login_fluig] Cookies salvos para usuário {usuario} no ambiente {ambiente}")
            return driver
        else:
            logger.warning("[fazer_login_fluig] Nenhum cookie obtido")
            driver.quit()
            return None
            
    except TimeoutException:
        logger.error("[fazer_login_fluig] Timeout ao aguardar elementos")
        if driver:
            driver.quit()
        return None
    except Exception as e:
        logger.error(f"[fazer_login_fluig] Erro: {str(e)}")
        if driver:
            driver.quit()
        return None

