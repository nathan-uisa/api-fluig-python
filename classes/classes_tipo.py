from pydantic import BaseModel

class DadosChamado(BaseModel):
    Titulo: str
    Descricao: str 
    Usuario: str

