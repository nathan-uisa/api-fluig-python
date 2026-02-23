import openpyxl
import configparser
import os
import re

# PATH_TO_TEMP na raiz do projeto (mantido para compatibilidade)
PATH_TO_TEMP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp.txt')

def obter_caminho_temp_por_email(email: str) -> str:
    """
    Gera o caminho do arquivo temporário baseado no email do usuário.
    Sanitiza o email para usar como nome de arquivo.
    
    Args:
        email: Email do usuário (ex: "usuario@exemplo.com")
    
    Returns:
        Caminho completo do arquivo temporário (ex: "temp_usuario_exemplo_com.txt")
    """
    if not email:
        return PATH_TO_TEMP
    
    # Sanitizar email: remover caracteres especiais e substituir por underscore
    email_sanitizado = re.sub(r'[^a-zA-Z0-9]', '_', email.lower())
    # Limitar tamanho para evitar nomes muito longos
    if len(email_sanitizado) > 50:
        email_sanitizado = email_sanitizado[:50]
    
    nome_arquivo = f"temp_{email_sanitizado}.txt"
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), nome_arquivo)

class Planilha:
    def __init__(self, caminho_arquivo, email_usuario: str = None):
        self.caminho_arquivo = caminho_arquivo
        self.email_usuario = email_usuario
        self.path_to_temp = obter_caminho_temp_por_email(email_usuario) if email_usuario else PATH_TO_TEMP
        self.workbook = None
        self.sheet = None
        self.config = configparser.ConfigParser()
        self.config_temp()

    def config_temp(self):
        temp_dir = os.path.dirname(self.path_to_temp)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        if os.path.exists(self.path_to_temp):
            try:
                os.remove(self.path_to_temp)
            except Exception as e:
                return False
        try:
            with open(self.path_to_temp, 'w', encoding='utf-8') as f:
                f.write('')
        except Exception as e:
            return False
        self.config = configparser.ConfigParser()
        
    def carregar_planilha(self):
        self.workbook = openpyxl.load_workbook(self.caminho_arquivo)
        self.sheet = self.workbook.active
        self.config_temp()

    def criar_base_chamados(self):
        self.config_temp()
        self.carregar_planilha()
        linhas_processadas = 0
        celulas_processadas = 0
        try:
            for row in self.sheet.iter_rows():
                if not any(cell.value for cell in row):
                    continue
                linha_num = str(row[0].row)
                self.config.add_section(linha_num)
                

                for cell in row:
                    if cell.value is not None:
                        coluna_letra = str(cell.column_letter)
                        valor_celula = str(cell.value)

                        self.config.set(linha_num, coluna_letra, valor_celula)
                        celulas_processadas += 1
                linhas_processadas += 1
            

            with open(self.path_to_temp, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return len(self.config.sections())
            
        except Exception as e:
            return False
    
    def limpar_arquivo_temporario(self):
        try:
            if os.path.exists(self.path_to_temp):
                os.remove(self.path_to_temp)
            self.config = configparser.ConfigParser()
        except Exception as e:
            return False
    
    def verificar_arquivo_temporario(self):
        if os.path.exists(self.path_to_temp):
            try:
                self.config.read(self.path_to_temp)
                secoes = len(self.config.sections())
                return True
            except Exception as e:
                return False
        else:
            return False

