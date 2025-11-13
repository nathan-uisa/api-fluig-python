from requests_oauthlib import OAuth1
import os,dotenv,requests
dotenv.load_dotenv()

class FLUIG:
    def __init__(self):
        self.auth = OAuth1(os.getenv('CK'), os.getenv('CS'), os.getenv('TK'), os.getenv('TS'))
        self.headers = {'Content-Type': 'application/json; charset=UTF-8'}
        self.URL=os.getenv('URL_CHAMADO_PRD')
        self.URL_CONSULTA=os.getenv('URL_CONSULTA')

    def FluigDatasets(self,PARAMETROS):
        print("FluigDatasets")
        resposta =  requests.get(self.URL_CONSULTA, headers=self.headers, auth=self.auth, params=PARAMETROS, timeout=15)
        resposta.raise_for_status()
        return resposta.json()

    def FluigRequestQLD(self,PARAMETROS):
        print("FluigRequestQLD")
        auth_QLD = OAuth1(os.getenv('CK_QLD'), os.getenv('CS_QLD'), os.getenv('TK_QLD'), os.getenv('TS_QLD'))
        try:
            resposta = requests.post(os.getenv('URL_CHAMADO_QLD'), headers=self.headers, auth=auth_QLD, json=PARAMETROS, timeout=15)
            resposta.raise_for_status()
            return resposta.json()
        except requests.RequestException as e:
            return None
        
    def FluigRequestPRD(self,PARAMETROS):
        print("FluigRequestPRD")
        try:
            resposta = requests.post(self.URL, headers=self.headers, auth=self.auth, json=PARAMETROS, timeout=15)
            resposta.raise_for_status()
            return resposta.json()
        except requests.RequestException as e:
            return None