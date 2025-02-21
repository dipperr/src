import flet as ft
from collections import defaultdict
from typing import Optional, Callable, List
from datetime import date

from acessorios import BancoDeDados, Dialogo, Utilidades
from modelos import ModeloItem
from controles import ControleGradeItem, ControlePagina, ControleItem
from pagina_config_itens import PaginaConfigItem
import querys_app6 as q6


class JanelaEntrada(ft.AlertDialog):
    def __init__(self, item: ModeloItem) -> None:
        super().__init__(
            title=ft.Text(value=f"Entrada ({item.nome.title()})", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            modal=True
        )
        self.item = item
        self.fornecedores = defaultdict(list)
        self.dialogo = Dialogo()
        self.controle_item: ControleItem = None
        self.preco_cadastrado = 0
        self.relacao_id = 0
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.criar_botoes()
        self.criar_entradas()

        self.content = ft.Stack(
            [
                ft.Container(
                    ft.Column([
                        ft.Row([self.entradas[1], self.entradas[2]]),
                        ft.Row([
                            self.entradas[0],
                            self.entradas[3],
                            self.entradas[4]
                        ])
                    ], spacing=30),
                expand=True),
                self.dialogo
            ],
            width=500,
            height=180,
            alignment=ft.alignment.center
        )
        self.actions = [self.botoes[0], self.botoes[1]]

    def criar_entradas(self) -> None:
        # date.today().strftime("%d-%m-%Y")
        self.entradas = [
            ft.TextField(
                label="Quantidade",
                width=180,
                border="underline",
                suffix_text=f"({Utilidades.encurtar_medida(self.item.medida)})"
            ),
            self.criar_dropdown(
                label="Fornecedor",
                options=[],
                width=280,
                on_change=self.buscar_marca
            ),
            self.criar_dropdown(
                label="Marca",
                options=[],
                width=200,
                on_change=self.buscar_preco
            ),
            ft.TextField(label="Preço", width=145, border="underline", prefix_text="R$ "),
            ft.TextField(label="Data Compra", value=date.today().strftime("%d-%m-%Y"), border="underline", width=150)
        ]

        for entrada in self.entradas:
            entrada.on_focus = self.alterar_para_cor_padrao

    def criar_dropdown(
        self,
        label: str,
        options: List[str],
        width: int,
        value: Optional[str]=None,
        on_change: Optional[Callable[[ft.ControlEvent], None]]=None,
        disabled: bool=False
    ) -> ft.Dropdown:
        return ft.Dropdown(
            width=width,
            label=label,
            options=[
                ft.dropdown.Option(o)
                for o in options
            ],
            value=value,
            border="underline",
            on_change=on_change,
            disabled=disabled
        )

    def criar_botoes(self) -> None:
        self.botoes = [
            ft.TextButton(
                text="Salvar",
                on_click=self.salvar_log_entrada,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.GREEN_100})
            ),
            ft.TextButton(
                text="Cancelar",
                on_click=self.cancelar,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.RED_100})
            )
        ]

    def buscar_preco(self, e: ft.ControlEvent) -> None:
        for dados in self.fornecedores[int(self.entradas[1].value)]:
            if dados["marca"] == self.entradas[2].value:
                self.relacao_id = dados["r_id"]
                self.preco_cadastrado = dados["preco"]
                self.entradas[3].value = str(dados["preco"]).replace(".", ",")
                self.entradas[3].update()

    def buscar_marca(self, e: ft.ControlEvent) -> None:
        self.acoes_marca()
        dados = self.fornecedores[int(e.data)]
        for dado in dados:
            self.entradas[2].options.append(
                ft.dropdown.Option(dado["marca"])
            )
        self.entradas[2].update()

        if len(dados) == 1:
            self.acao_sem_marca(dados[0])

    def acoes_marca(self) -> None:
        self.entradas[2].options.clear()
        self.entradas[2].value = None
        self.entradas[3].value = None
        self.entradas[3].update()

    def acao_sem_marca(self, dados: list) -> None:
        self.relacao_id = dados["r_id"]
        self.preco_cadastrado = dados["preco"]
        self.entradas[2].value = dados["marca"]
        self.entradas[3].value = str(dados["preco"]).replace(".", ",")
        self.entradas[3].update()
        self.entradas[2].update()

    async def salvar_log_entrada(self, e: ft.ControlEvent) -> None:
        if self.controle_item is not None:
            menor_preco = self.menor_preco()
            await self.controle_item.salvar_log_compra(
                self.relacao_id,
                self.entradas[1].value,
                self.preco_cadastrado,
                self.entradas[3].value,
                self.entradas[0].value,
                self.entradas[2].value,
                self.entradas[4].value,
                menor_preco
            )
            self.limpar_campos()

    def menor_preco(self) -> float:
        return min(
            [
                item["preco"] for _, lista in self.fornecedores.items()
                for item in lista
            ]
        )

    def limpar_campos(self) -> None:
        for entrada in self.entradas[:-1]:
            entrada.value = None
            entrada.update()

    async def mostrar_erro_campo_vazio(self) -> None:
        for entrada in self.entradas[:-1]:
            if not entrada.value:
                entrada.label_style = ft.TextStyle(color=ft.Colors.RED)
                entrada.update()

    def alterar_para_cor_padrao(self, e: ft.ControlEvent) -> None:
        e.control.label_style = ft.TextStyle(color=None)
        e.control.update()

    def cancelar(self, e: ft.ControlEvent) -> None:
        self.page.close(self)

    async def buscar_fornecedores(self) -> None:
        fornecedores = await self.controle_item.buscar_fornecedores_relacao()
        if fornecedores:
            fornecedores_dict = {}
            for fornecedor in fornecedores:
                fornecedores_dict.update({fornecedor[1]: fornecedor[2]})
                self.fornecedores[fornecedor[1]].append(
                    {
                        "r_id": fornecedor[0],
                        "nome": fornecedor[2],
                        "preco": fornecedor[3],
                        "marca": fornecedor[4]
                    }
                )
                
            for k, v in fornecedores_dict.items():
                self.entradas[1].options.append(
                    ft.dropdown.Option(key=k, text=v)
                )

            self.entradas[1].update()

    def definir_controle(self, controle: ControleItem) -> None:
        self.controle_item = controle

    def did_mount(self):
        self.page.run_task(self.buscar_fornecedores)


class JanelaRemoverProduto(ft.AlertDialog):
    def __init__(self, controle: ControleItem) -> None:
        super().__init__(modal=True)
        self.controle = controle
        self.title = ft.Text(value="Por favor confirme")
        self.content = ft.Text(value=f"Deseja realmente excluir o item {self.controle.nome}?", size=15)
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
        await self.controle.apagar_item()
        self.fechar_janela()

    def nao(self, e: ft.ControlEvent) -> None:
        self.fechar_janela()

    def fechar_janela(self) -> None:
        self.page.close(self)


class CartaoItem(ft.Card):
    def __init__(
            self,
            item: ModeloItem,
            controle_grade: ControleGradeItem,
            controle_pagina: ControlePagina
        ) -> None:
        super().__init__(color=ft.Colors.BLUE_100, elevation=5)
        self._dict_medida = {
            "quilograma": "Kg",
            "litro": "L",
            "unidade": "U"
        }
        self.item = item
        self.controle_grade = controle_grade
        self.controle_pagina = controle_pagina
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.menu_botoes = ft.Row([
            self.criar_botao(
                icon=ft.Icons.DELETE,
                tooltip="Apagar",
                on_click=self.abrir_janela_remover
            ),
            self.criar_botao(
                icon=ft.Icons.SETTINGS_ROUNDED,
                tooltip="Configurações",
                on_click=self.abrir_configuracoes_item
            ),
            self.criar_botao(
                icon=ft.Icons.ARROW_UPWARD_ROUNDED,
                tooltip="Entrada",
                on_click=self.abrir_janela_entrada
            )
        ])

        self.content = ft.Container(
            content=ft.Column([
                ft.Container(
                    ft.Image(
                        src=self.item.path if self.item.path is not None else "imagens/image-slash.png",
                        width=50,
                        height=50,
                        border_radius=ft.border_radius.all(50)
                    ), alignment=ft.alignment.center
                ),
                ft.Container(
                    ft.Text(
                        value=self.item.nome.title(),
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.W_600,
                        size=17
                    ), alignment=ft.alignment.center
                ),
                ft.Container(
                    self.menu_botoes,
                    alignment=ft.alignment.center
                )
            ]),
            padding=ft.padding.only(left=5, right=5, top=10, bottom=5),
            alignment=ft.alignment.center,
            border_radius=ft.border_radius.all(15)
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
    
    def abrir_janela_entrada(self, e: ft.ControlEvent) -> None:
        janela = JanelaEntrada(self.item)
        controle = ControleItem(self.item, janela)
        janela.definir_controle(controle)
        self.page.open(janela)

    def abrir_configuracoes_item(self, e: ft.ControlEvent) -> None:
        pagina = PaginaConfigItem(self.item, self.controle_pagina)
        self.controle_pagina.alterar_para_barra_voltar()
        self.controle_pagina.adicionar_label_barra(self.item.nome.title())
        self.controle_pagina.add_acao_barra(
            pagina.botoes_calendario()
            )
        self.controle_pagina.atualizar_pagina(
            pagina
        )

    def abrir_janela_remover(self, e: ft.ControlEvent) -> None:
        controle = ControleItem(self.item, self.controle_grade)
        janela = JanelaRemoverProduto(controle)
        self.page.open(janela)

    def did_mount(self):
        ...


class PaginaItens(ft.Container):
    def __init__(self, controle_pagina: ControlePagina) -> None:
        super().__init__(expand=True)
        self.controle_pagina = controle_pagina
        self.bd = BancoDeDados("db_app6.db")
        self.criar_grade_itens()
        self.content = self.grade_itens

    def criar_grade_itens(self) -> None:
        self.grade_itens = ft.GridView(
            expand=1,
            max_extent=170,
            child_aspect_ratio=1,
            spacing=10,
            run_spacing=10,
        )

    async def criar_cards_itens(self) -> None:
        itens = await self.bd.fetch_all(q6.selecionar_produtos)
        self.content = self.grade_itens

        self.grade_itens.controls = [
            CartaoItem(ModeloItem(*item), ControleGradeItem(self), self.controle_pagina)
            for item in itens
        ]
        self.grade_itens.update()

    def filtrar(self, nome_item: str) -> None:
        if isinstance(nome_item, str):
            nome_item_lower = nome_item.lower()
            for cartao in self.grade_itens.controls:
                cartao.visible = cartao.item.nome.lower().startswith(nome_item_lower)
        self.grade_itens.update()

    def filtrar_categoria(self, categoria: str) -> None:
        cat_loger = categoria.lower()
        for cartao in self.grade_itens.controls:
                cartao.visible = (cartao.item.categoria.lower() == cat_loger) if cat_loger != "todos" else True
        self.grade_itens.update()