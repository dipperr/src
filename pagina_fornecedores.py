import flet as ft

from acessorios import BancoDeDados
from modelos import ModeloFornecedor
from controles import ControleGradeFornecedor, ControleFornecedor
import querys_app6 as q6


class JanelaInfoFornecedor(ft.AlertDialog):
    def __init__(self, fornecedor: ModeloFornecedor) -> None:
        super().__init__(modal=True)
        self.fornecedor = fornecedor
        self.actions = [
            ft.TextButton(
                content=ft.Text(value="Sair", color=ft.Colors.BLACK87),
                on_click=lambda e: self.page.close(self),
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.RED_100})
            )
        ]
        self.criar_conteudo()

    def criar_entradas(self) -> None:
        self.entradas = [
            ft.TextField(value=self.fornecedor.nome, label="Nome", width=290, border="underline", disabled=True),
            ft.TextField(value=self.fornecedor.telefone, label="Telefone", width=200, border="underline"),
            ft.TextField(value=self.fornecedor.responsavel, label="Responsavel", width=290, border="underline"),
            ft.TextField(value=self.fornecedor.logradouro, label="Logradouro", width=350, border="underline"),
            ft.TextField(value=self.fornecedor.numero, label="Numero", width=140, border="underline"),
            ft.TextField(value=self.fornecedor.bairro, label="Bairro", width=350, border="underline"),
            ft.TextField(value=self.fornecedor.cep, label="Cep", width=140, border="underline"),
            ft.TextField(value=self.fornecedor.cidade, label="Cidade", width=350, border="underline"),
            ft.TextField(value=self.fornecedor.estado, label="Estado", width=140, border="underline"),
        ]

    def criar_conteudo(self) -> None:
        self.criar_entradas()
        self.content = ft.Container(
            ft.Column([
                ft.Row([self.entradas[0], self.entradas[1]]),
                ft.Row([self.entradas[2]]),
                ft.Divider(),
                ft.Row([self.entradas[3], self.entradas[4]]),
                ft.Row([self.entradas[5], self.entradas[6]]),
                ft.Row([self.entradas[7], self.entradas[8]])
            ]),
            height=300, width=500
        )


class JanelaRemoverFornecedor(ft.AlertDialog):
    def __init__(self, controle: ControleFornecedor) -> None:
        super().__init__(modal=True)
        self.controle = controle
        self.title = ft.Text(value="Por favor confirme")
        self.content = ft.Column([
            ft.Text(value="Deseja realmente excluir o fornecedor", size=15),
            ft.Text(value=f"{self.controle.nome}", size=15)
        ], height=60)
        self.actions = [
            ft.TextButton(
                content=ft.Text(value="Sim", color=ft.Colors.BLACK87), 
                on_click=self.sim,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.GREEN_100})
            ),
            ft.TextButton(
                content=ft.Text(value="Não", color=ft.Colors.BLACK87),
                on_click=self.nao,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.RED_100})
            )
        ]

    async def sim(self, e: ft.ControlEvent) -> None:
        await self.controle.apagar_fornecedor()
        self.fechar_janela()

    def nao(self, e: ft.ControlEvent) -> None:
        self.fechar_janela()

    def fechar_janela(self) -> None:
        self.page.close(self)


class CartaoFornecedor(ft.Card):
    def __init__(
            self,
            fornecedor: ModeloFornecedor,
            controle_grade: ControleGradeFornecedor
        ) -> None:
        super().__init__(color=ft.Colors.BLUE_100, elevation=5)
        self.fornecedor = fornecedor
        self.controle_grade = controle_grade
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.menu_botoes = ft.Row([
            self.criar_botao(
                icon=ft.Icons.DELETE,
                tooltip="Apagar",
                on_click=self.abrir_janela_remover
            ),
            self.criar_botao(
                icon=ft.Icons.INFO,
                tooltip="Infos",
                on_click=self.abrir_infos
            )
        ], spacing=5, alignment=ft.MainAxisAlignment.END)

        self.content = ft.Container(
            content=ft.Column([
                ft.Text(
                    value=self.fornecedor.nome.title(),
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    weight=ft.FontWeight.W_600,
                    size=17
                ),
                ft.Row([
                    self.menu_botoes,
                ], alignment=ft.MainAxisAlignment.END)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.only(left=10, right=10, top=10, bottom=5)
        )

    def criar_botao(self, content=None, icon=None, tooltip=None, on_click=None) -> ft.IconButton:
        return ft.IconButton(
            content=content,
            icon=icon,
            icon_color=ft.Colors.BLACK,
            tooltip=tooltip,
            on_click=on_click,
            visible=True,
            icon_size=20
        )

    def abrir_infos(self, e: ft.ControlEvent) -> None:
        janela = JanelaInfoFornecedor(self.fornecedor)
        self.page.open(janela)

    def abrir_janela_remover(self, e: ft.ControlEvent) -> None:
        controle = ControleFornecedor(self.fornecedor, self.controle_grade)
        janela = JanelaRemoverFornecedor(controle)
        self.page.open(janela)


class PaginaFornecedores(ft.Container):
    def __init__(self) -> None:
        super().__init__(expand=True)
        self.bd = BancoDeDados("db_app6.db")
        self.criar_grade_fornecedores()
        self.content = self.grade_fornecedores

    def criar_grade_fornecedores(self) -> None:
        self.grade_fornecedores = ft.GridView(
            expand=1,
            max_extent=215,
            child_aspect_ratio=2,
            spacing=10,
            run_spacing=10,
        )

    async def criar_cards_fornecedores(self) -> None:
        itens = await self.bd.fetch_all(q6.obter_dados_fornecedores)
        self.grade_fornecedores.controls = [
            CartaoFornecedor(ModeloFornecedor(*item), ControleGradeFornecedor(self))
            for item in itens
        ]
        self.grade_fornecedores.update()

    def did_mount(self) -> None:
        return self.page.run_task(self.criar_cards_fornecedores)
    