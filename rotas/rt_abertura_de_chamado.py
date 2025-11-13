from fastapi import APIRouter, Request, Depends
from classes.classes_tipo import DadosChamado
from modulos.datasets import FluigDataset
from auth.fluig_request import FLUIG
from auth.auth_api import Auth_API_KEY
import os, dotenv, requests, datetime
dotenv.load_dotenv()
router = APIRouter()
URL_CHAMADO_QLD = os.getenv("URL_CHAMADO_QLD")


"""
RETURN Dataset_aprovadores
{
	"content": [
		{
			"Código_Função": "3461",
			"Email": "nathan.azevedo@uisa.com.br",
			"Empresa": "USINAS ITAMARATI",
			"Presidente": "JOSE FERNANDO MAZUCA FILHO",
			"Email_Diretor": "rodrigo.goncalves@uisa.com.br",
			"Email_Presidente": "jose.mazuca@uisa.com.br",
			"Função_Diretor": "Diretor de Gente, Inovação e Administração",
			"Chapa": "8004717",
			"Função": "Desenvolvedor JR",
			"Chapa_Gestor": "0892343",
			"Email_Coordenador": "null",
			"Nome": "NATHAN RENNER DE AZEVEDO",
			"Seção": "Sistemas",
			"Email_Gestor": "lucas.silva@uisa.com.br",
			"Função_Coordenador": "null",
			"Chapa_Diretor": "0892106",
			"Coordenador": "null",
			"Gestor": "LUCAS DOS PASSOS SILVA",
			"Chapa_Coordenador": "null",
			"Função_Gestor": "Gerente Tecnologia da Informação",
			"Diretor": "RODRIGO RIBEIRO GONCALVES",
			"Função_Presidente": "Diretor Presidente",
			"Código_Seção": "1.00.17.01.110051404.00.0",
			"Chapa_Presidente": "0892394"
		}
	],
	"message": null
}
"""
"""
RETURN Dataset_colleague
{
	"content": [
		{
			"colleagueName": "Nathan Renner de Azevedo",
			"mail": "nathan.azevedo@uisa.com.br",
			"extensionNr": null,
			"maxPrivateSize": null,
			"groupId": "",
			"userTenantId": "1795",
			"active": "true",
			"login": "nathan.azevedo.uisa.com.br.1",
			"currentProject": "",
			"especializationArea": "",
			"colleagueId": "f91b4d01ddc24241b2e1915657bebcd4",
			"companyId": "1",
			"defaultLanguage": "pt_BR",
			"adminUser": "false",
			"volumeId": null,
			"emailHtml": "true"
		}
	],
	"message": null
}
"""
"""
RETURN Dataset_funcionarios
{
	"content": [
		{
			"Seção": "Sistemas",
			"Código_Função": "3461",
			"Email_Pessoal": "nathan-renner@hotmail.com",
			"Email": "nathan.azevedo@uisa.com.br",
			"Empresa": "USINAS ITAMARATI",
			"Centro_Custo": "110051404.00.0",
			"Gerência": "17.01 - Gerência de Tecnologia da Informação",
			"Telefone": "5565996204906",
			"CNPJ_Empresa": "15.009.178/0001-70",
			"Código_Pessoa": "75471",
			"Chapa": "8004717",
			"Função": "Desenvolvedor JR",
			"Data_Admissão": "2025-10-08 00:00:00.0",
			"SearchField": "8004717 - NATHAN RENNER DE AZEVEDO",
			"Código_Empresa": "1",
			"CPF": "70424905175",
			"Data_Nascimento": "24/05/1998",
			"Nome": "NATHAN RENNER DE AZEVEDO",
			"Código_Seção": "1.00.17.01.110051404.00.0",
			"Código_Equipe": "null"
		}
	],
	"message": null
}
"""
"""
PAYLOAD
{
	"targetState": 0,
	"subProcessTargetState": 0,
	"targetAssignee": "8004717",
	"comment": "CHAMADO TESTE",
	"formFields": 
	{
		"ds_chamado": 				"TESTE-CHAMADO",
		"nm_emitente": 				"Nathan Renner de Azevedo",
		"h_solicitante": 			"8004717",
		"ds_cargo": 					"Desenvolvedor JR",
		"NomeRegistrador": 		"nathan.azevedo@uisa.com.br",
		"ds_email_sol": 			"nathan.azevedo@uisa.com.br",
		"ds_secao":	 					"Sistemas",
		"num_cr_elab": 				"110051404",
		"ds_empresa": 				"USINAS ITAMARATI",
		"ch_sap": 						"0",
		"num_tel_contato": 		"65996204906",
		"ds_titulo": 					"TESTE - TÍTULO",
		"dt_abertura": 				"10/11/2025 18:34"
	}
}
"""


@router.post("/chamado/abrir")
async def AberturaDeChamados(Item: DadosChamado, api_key: str = Depends(Auth_API_KEY)):
    fluig = FLUIG()
    Dataset_colleague_usuario = FluigDataset().Dataset_colleague(Item.Usuario)
    Dataset_funcionarios_usuario = FluigDataset().Dataset_funcionarios(Item.Usuario)
    Dataset_funcionarios_usuario['content'][0]['Código_Seção'] = str(max(map(int,Dataset_funcionarios_usuario['content'][0]['Código_Seção'].split('.'))))
    payload = {
        "targetState": '0',
        "subProcessTargetState": '0',
        "targetAssignee": "8004717",
        "formFields": 
        {
            "ds_chamado": 		Item.Descricao,
            "nm_emitente": 		Dataset_colleague_usuario['content'][0]['colleagueName'],
            "h_solicitante": 	"8004717",
            "ds_cargo": 		Dataset_funcionarios_usuario['content'][0]['Função'],
            "NomeRegistrador": 	Dataset_colleague_usuario['content'][0]['mail'],
            "ds_email_sol": 	Dataset_colleague_usuario['content'][0]['mail'],
            "ds_secao": 		Dataset_funcionarios_usuario['content'][0]['Seção'],
            "num_cr_elab": 		Dataset_funcionarios_usuario['content'][0]['Código_Seção'],
            "ds_empresa": 		Dataset_funcionarios_usuario['content'][0]['Empresa'],
            "ch_sap": 			"0",
            "num_tel_contato": 	Dataset_funcionarios_usuario['content'][0]['Telefone'],
            "ds_titulo": 		Item.Titulo,
            "dt_abertura": 		datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        } 
    }
    print(payload)
    resposta = fluig.FluigRequestQLD(payload)
    return resposta