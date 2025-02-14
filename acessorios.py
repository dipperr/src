import aiosqlite
import flet as ft
from typing import Optional
import requests

class BancoDeDados:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def execute(self, query: str, params: tuple = None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            if params:
                await db.execute(query, params)
            else:
                await db.execute(query)
            await db.commit()

    async def execute_return_id(self, query: str, params: tuple = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            if params:
                async with db.execute(query, params) as cursor:
                    last_id = cursor.lastrowid
            else:
                async with db.execute(query) as cursor:
                    last_id = cursor.lastrowid
            await db.commit()
        return last_id

    async def fetch_all(self, query: str, params: tuple = None) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params or ()) as cursor:
                return await cursor.fetchall()

    async def fetch_one(self, query: str, params: tuple = None) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params or ()) as cursor:
                return await cursor.fetchone()


class Utilidades:
    @staticmethod
    def encurtar_medida(medida: str) -> str:
        _dict_medida = {
            "quilograma": "Kg",
            "unidade": "U",
            "litro": "L"
        }
        return _dict_medida[medida]

    @staticmethod
    def encurtar_nome(nome: str, tamanho: int) -> str:
        return nome[:tamanho]
    
    @staticmethod
    def formatar_preco(preco: str) -> str:
        return preco.replace(".", "").replace(",", ".")


class Dialogo(ft.Container):
    def __init__(self) -> None:
        super().__init__(
            width=250,
            height=120,
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=ft.border_radius.all(10),
            opacity=1,
            visible=False,
            alignment=ft.alignment.center
        )

    def atualizar_conteudo(self, icon: Optional[str], texto: str) -> None:
        elementos = []
        if icon:
            elementos.append(ft.Icon(name=icon))
        elementos.append(ft.Text(value=texto))
        self.content = ft.Row(elementos, alignment=ft.MainAxisAlignment.CENTER)
        self.visivel(True)
        self.update()

    def salvando(self) -> None:
        self.visivel(True)
        self.content = ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2),
            ft.Text(value="Salvando")
        ], alignment=ft.MainAxisAlignment.CENTER)
        self.update()

    def salvo(self) -> None:
        self.atualizar_conteudo(ft.Icons.CHECK, "Salvo")

    def buscando(self) -> None:
        self.content = ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2),
            ft.Text(value="Buscando")
        ], alignment=ft.MainAxisAlignment.CENTER)
        self.update()

    def visivel(self, visivel: bool):
        self.visible = visivel

    def limpar(self) -> None:
        self.content = None
        self.visivel(False)
        self.update()

    def generico(self, icon: Optional[str], texto: str) -> None:
        self.atualizar_conteudo(icon, texto)


class BuscarCep:
    def __init__(self) -> None:
        self.url = "https://brasilapi.com.br/api/cep/v1/{}"

    def obter_dados(self, cep: str) -> dict:
        response = requests.get(self.url.format(self.formatar_cep(cep)))
    
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {}
        else:
            return {}
        
    def formatar_cep(self, cep: str) -> str:
        return cep.replace("-", "")


class JanelaNotificacao(ft.AlertDialog):
    def __init__(self, mensagem: str, icone: str) -> None:
        super().__init__()
        self.content = ft.Container(
            ft.Row([
                ft.Text(mensagem, size=20, weight=ft.FontWeight.W_500),
                ft.Icon(icone)
            ]),
            padding=ft.padding.all(20)
        )
