import openpyxl
import configparser
import os

# PATH_TO_TEMP na raiz do projeto
PATH_TO_TEMP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp.txt')

class Planilha:
    def __init__(self, caminho_arquivo):
        self.caminho_arquivo = caminho_arquivo
        self.workbook = None
        self.sheet = None
        self.config = configparser.ConfigParser()
        self.config_temp()

    def config_temp(self):
        temp_dir = os.path.dirname(PATH_TO_TEMP)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        if os.path.exists(PATH_TO_TEMP):
            try:
                os.remove(PATH_TO_TEMP)
            except Exception as e:
                return False
        try:
            with open(PATH_TO_TEMP, 'w', encoding='utf-8') as f:
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
            

            with open(PATH_TO_TEMP, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return len(self.config.sections())
            
        except Exception as e:
            return False
    
    def limpar_arquivo_temporario(self):
        try:
            if os.path.exists(PATH_TO_TEMP):
                os.remove(PATH_TO_TEMP)
            self.config = configparser.ConfigParser()
        except Exception as e:
            return False
    
    def verificar_arquivo_temporario(self):
        if os.path.exists(PATH_TO_TEMP):
            try:
                self.config.read(PATH_TO_TEMP)
                secoes = len(self.config.sections())
                return True
            except Exception as e:
                return False
        else:
            return False

