from pydantic import BaseModel




class XPathsFluig(BaseModel):
    usuario: set[str] = {'//*[@id="username"]','//*[@id="emailAddress"]','/html/body/div[1]/div/div[2]/form/div[1]/div/input'}
    senha: set[str] = {'//*[@id="password"]'}
    botao_login: set[str] = {'//*[@id="login_btn"]/p','//button[@type="submit"]','//input[@type="submit"]','//button[contains(text(), "Entrar")]','//button[contains(text(), "Login")]','//button[contains(text(), "Acessar")]','//button[contains(text(), "Log in")]','//button[contains(text(), "Login")]','//button[contains(text(), "Acessar")]'}


class DetalhesChamado(BaseModel):
    process_instance_id: int

class DetalhesServicos(BaseModel):
    id_servico: str

class AnexoBase64(BaseModel):
    """Modelo para anexo em base64"""
    nome: str
    conteudo_base64: str  # Conteúdo do arquivo em base64

class AberturaChamado(BaseModel):
    titulo: str
    descricao: str
    usuario: str
    telefone: str | None = None
    anexos: list[AnexoBase64] | None = None  # Lista de anexos em base64

class AberturaChamadoEmail(BaseModel):
    titulo: str
    descricao: str
    usuario: str
    telefone: str | None = None
    anexos: list[AnexoBase64] | None = None  # Lista de anexos em base64

# Dados para a rota fluig/chamado/abrir-classificado
class AberturaChamadoClassificado(BaseModel):
    titulo: str
    descricao: str
    usuario: str
    telefone: str | None = None
    servico: str
    anexos: list[AnexoBase64] | None = None  # Lista de anexos em base64


class DadosEmail(BaseModel):
    Email: str
    Assunto: str
    Corpo: str
    Telefone: str | None = None

class Datasets(BaseModel):
    dataset_id: str
    user: str

def DatasetConfig():
    return {
        'colleague': {
            'datasetId': 'colleague',
            'campo_email': 'mail',
            'campo_nome': 'colleagueName',
            'campo_currentProject': 'currentProject',
            'nome_dataset': 'colleague',
            'url': '/api/public/ecm/dataset/search'
        },
        'ds_aprovadores': {
            'datasetId': 'ds_aprovadores',
            'campo_email': 'Email',
            'campo_nome': 'Nome',
            'nome_dataset': 'aprovadores',
            'url': '/api/public/ecm/dataset/search'
        },
        'ds_funcionarios': {
            'datasetId': 'ds_funcionarios',
            'campo_email': 'Email',
            'campo_nome': 'Chapa',
            'nome_dataset': 'funcionarios',
            'url': '/api/public/ecm/dataset/search'
        }
        
    }
