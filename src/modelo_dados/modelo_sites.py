from pydantic import BaseModel, EmailStr
from typing import Optional


class PayloadFuncionario(BaseModel):
    """Payload para buscar dados do funcionário na API"""
    Email: EmailStr


class DadosChamado(BaseModel):
    """Modelo para criação de chamado via API"""
    Usuario: EmailStr
    Titulo: str
    Descricao: str


class DadosFuncionario(BaseModel):
    """Modelo para dados retornados da API de funcionário"""
    Nome: Optional[str] = None
    Email: Optional[str] = None
    Telefone: Optional[str] = None
    Função: Optional[str] = None
    Seção: Optional[str] = None
    Empresa: Optional[str] = None
    Centro_Custo: Optional[str] = None
    Chapa: Optional[str] = None
    Gerencia: Optional[str] = None
    Email_Pessoal: Optional[str] = None
    CNPJ_Empresa: Optional[str] = None
    Codigo_Pessoa: Optional[str] = None
    Data_Admissao: Optional[str] = None
    SearchField: Optional[str] = None
    Codigo_Empresa: Optional[str] = None
    CPF: Optional[str] = None
    Data_Nascimento: Optional[str] = None
    Codigo_Secao: Optional[str] = None
    Codigo_Equipe: Optional[str] = None
    Codigo_Função: Optional[str] = None
    
    class Config:
        extra = "ignore"
        populate_by_name = True


class DadosFuncionarioForm(BaseModel):
    """Modelo para dados formatados do funcionário usados no formulário"""
    elaborador: str
    solicitante: str
    data_abertura: str
    telefone_contato: str
    cargo: str
    secao: str
    empresa: str
    centro_custo: str
    chapa: Optional[str] = None
    gerencia: Optional[str] = None
    email: str

