

import os 
from dotenv import load_dotenv
from auth.fluig_request import FLUIG

load_dotenv()
URL_CONSULTA = os.getenv("URL_CONSULTA")
print(URL_CONSULTA)

class FluigDataset:
    def __init__(self):
        self.fluig = FLUIG()
    
    def Dataset_colleague(self, USER):
        print("Dataset_colleague")
        if '@' in USER:
            parametro = {
                'datasetId': 'colleague',
                'filterFields': f'mail,{USER}'
            }
        else:
            parametro = {
                'datasetId': 'colleague',
                'filterFields': f'colleagueName,{USER}'
            }

        resposta = self.fluig.FluigDatasets(parametro)
        return resposta

    def Dataset_aprovadores(self, USER):
        print("Dataset_aprovadores")
        if '@' in USER:
            parametro = {
                'datasetId': 'ds_aprovadores',
                'filterFields': f'Email,{USER}'
            }
        else:
            parametro = {
                'datasetId': 'ds_aprovadores',
                'filterFields': f'Nome,{USER}'
            }

        resposta = self.fluig.FluigDatasets(parametro)
        return resposta

    def Dataset_funcionarios(self, USER):
        print("Dataset_funcionarios")
        if '@' in USER:
            parametro = {
                'datasetId': 'ds_funcionarios',
                'filterFields': f'Email,{USER}'
            }
        else:
            parametro = {
                'datasetId': 'ds_funcionarios',
                'filterFields': f'Chapa,{USER}'
            }
        resposta = self.fluig.FluigDatasets(parametro)
        return resposta