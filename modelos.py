from typing import Optional


class ModeloItem:
    def __init__(
            self,
            id: Optional[int] = None,
            nome: Optional[str] = None,
            medida: Optional[str] = None,
            categoria: Optional[str] = None,
            path: Optional[str] = None
        ) -> None:
        self.id = id
        self.nome = nome
        self.medida = medida
        self.categoria = categoria
        self.path = path

    def __str__(self):
        return f"{self.id}, {self.nome}, {self.medida}, {self.categoria}, {self.path}"


class ModeloFornecedor:
    def __init__(
            self,
            id: Optional[int] = None,
            nome: Optional[str] = None,
            telefone: Optional[str] = None,
            responsavel: Optional[str] = None,
            logradouro: Optional[str] = None,
            numero: Optional[int] = None,
            bairro: Optional[str] = None,
            cep: Optional[str] = None,
            cidade: Optional[str] = None,
            estado: Optional[str] = None
        ):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.responsavel = responsavel
        self.logradouro = logradouro
        self.numero = numero
        self.bairro = bairro
        self.cep = cep
        self.cidade = cidade
        self.estado = estado