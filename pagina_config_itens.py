import flet as ft
import locale
from datetime import datetime, timedelta
import numpy as np
from abc import ABC, abstractmethod
from typing import Union, Callable
import pandas as pd
from flet.plotly_chart import PlotlyChart
import plotly.graph_objects as go
import unicodedata

from acessorios import BancoDeDados, Utilidades, JanelaNotificacao
from controles import ControleLog, ControleItem
from modelos import ModeloItem
import querys_app6 as q6


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")


class ControlePagina:
    def __init__(self, pagina) -> None:
        self.pagina = pagina

    async def ler_dados(self) -> None:
        await self.pagina.ler_dados()


class JanelaRemover(ft.AlertDialog, ABC):
    def __init__(self, controle: Union[ControleItem, ControleLog]) -> None:
        super().__init__(modal=True)
        self.controle = controle
        self.title = ft.Text(value="Por favor confirme")
        self.content = ft.Text(value="Deseja realmente excluir o registro?", size=15)
        self.actions = [
            ft.TextButton(
                content=ft.Text(value="Sim", color=ft.colors.BLACK87), 
                on_click=self.sim,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.colors.GREEN_100})
            ),
            ft.TextButton(
                content=ft.Text(value="Não", color=ft.colors.BLACK87),
                on_click=self.nao,
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.colors.RED_100})
            )
        ]
    @abstractmethod
    async def sim(self, e: ft.ControlEvent) -> None:
        ...

    def nao(self, e: ft.ControlEvent) -> None:
        self.fechar_janela()

    def fechar_janela(self) -> None:
        self.page.close(self)


class JanelaEdicao(ft.AlertDialog, ABC):
    def __init__(self, controle: ControleItem) -> None:
        super().__init__(modal=True)
        self.controle = controle
        self.field_valor = ft.TextField(label="Valor", width=200, prefix_text="R$ ")
        self.content = ft.Row([
            self.field_valor
        ])
        self.actions = [
            ft.TextButton(text="Atualizar", on_click=self.atualizar),
            ft.TextButton(text="Cancelar", on_click=lambda e: self.page.close(self))
        ]

    @abstractmethod
    async def atualizar(self, e: ft.ControlEvent) -> None:
        ...


class JanelaAddFornecedorProduto(ft.AlertDialog):
    def __init__(self, controle:ControleItem) -> None:
        super().__init__(modal=True)
        self.controle = controle
        self.fornecedores = {}
        self.title = ft.Text(value="Adicionar Fornecedor")
        self.actions = [
            ft.TextButton(text="Adicionar", on_click=self.salvar_relacao),
            ft.TextButton(text="Cancelar", on_click=lambda e: self.page.close(self))
        ]
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.entradas = [
            ft.Dropdown(
                label="Nome",
                options=None,
                width=250
            ),
            ft.TextField(label="Marca", width=200),
            ft.TextField(label="Preço", width=150, prefix_text="R$ ")
        ]
        self.content = ft.Column([
            ft.Row([
                self.entradas[0],
                self.entradas[1]
            ]),
            ft.Row([
                self.entradas[2]
            ])
        ],
        width=460,
        height=150)

    async def obter_lista_fornecedores(self) -> None:
        fornecedores = await self.controle.obter_fornecedores()
        for fornecedor in fornecedores:
            self.adicionar_opcao_dropdown(fornecedor[0], fornecedor[1])
            self.fornecedores.update({fornecedor[0]: fornecedor[1]})

    def adicionar_opcao_dropdown(self, id: int, nome: str) -> None:
        self.entradas[0].options.append(
            ft.dropdown.Option(key=id, text=nome)
        )
        self.update()

    async def salvar_relacao(self, e: ft.ControlEvent) -> None:
        await self.controle.criar_relacao_produto_fornecedor(
            self.entradas[0].value,
            self.entradas[1].value,
            self.entradas[2].value
        )
    
    def did_mount(self) -> None:
        self.page.run_task(self.obter_lista_fornecedores)


class JanelaRemoverFornecedor(JanelaRemover):
    def __init__(self, controle: ControleItem, id_relacao: int) -> None:
        super().__init__(controle)
        self.id_relacao = id_relacao

    async def sim(self, e: ft.ControlEvent) -> None:
        await self.controle.apagar_relacao_produto_fornecedor(self.id_relacao)
        self.fechar_janela()


class JanelaRemoverLog(JanelaRemover):
    def __init__(self, controle: ControleLog) -> None:
        super().__init__(controle)

    async def sim(self, e: ft.ControlEvent) -> None:
        await self.controle.apagar_log_compra()
        self.fechar_janela()


class JanelaEdicaoPrecoFornecedor(JanelaEdicao):
    def __init__(self, controle: ControleItem, id_relacao: int) -> None:
        super().__init__(controle)
        self.id_relacao = id_relacao

    async def atualizar(self, e: ft.ControlEvent) -> None:
        valor = self.field_valor.value
        await self.controle.atualizar_preco_relacao(valor, self.id_relacao)
        self.page.close(self)


class JanelaEdicaoConsumo(JanelaEdicao):
    def __init__(self, controle: ControleItem, dia_semana: int) -> None:
        super().__init__(controle)
        self.dia_semana = dia_semana

    async def atualizar(self, e: ft.ControlEvent) -> None:
        valor = self.field_valor.value
        await self.controle.atualizar_consumo(valor, self.dia_semana)
        self.page.close(self)


class TabelaFornecedor(ft.DataTable):
    def __init__(self) -> None:
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text(value="Fornecedor")),
                ft.DataColumn(ft.Text(value="Marca")),
                ft.DataColumn(ft.Text(value="Preço"), on_sort=self.ordenar_tabela),
                ft.DataColumn(ft.Text(value="Excluir"))
            ],
            rows=[],
            col=12,
            column_spacing=30,
            sort_column_index=2,
            sort_ascending=True,
            heading_row_height=40
        )
        self.controle = None

    def adicionar_fornecedor(self, id_relacao, fornecedor_id, nome: str, preco: float, marca: str) -> None:
        async def deletar_ao_clicar(e: ft.ControlEvent, id_relacao: int=id_relacao) -> None:
            await self.deletar_relacao_produto_fornecedor(id_relacao)

        def editar_ao_clicar(e: ft.ControlEvent, id_relacao: int=id_relacao) -> None:
            self.editar(id_relacao)

        self.rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(value=nome[:15].title(), overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, tooltip=nome.title())),
                    ft.DataCell(ft.Text(value=marca[:10].title(), overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, tooltip=marca.title())),
                    ft.DataCell(ft.Text(value=locale.currency(preco, grouping=True)), show_edit_icon=True, on_tap=editar_ao_clicar),
                    ft.DataCell(
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            on_click=deletar_ao_clicar
                        )
                    )
                ]
            )
        )
        self.update()

    async def deletar_relacao_produto_fornecedor(self, id_relacao: int) -> None:
        janela = JanelaRemoverFornecedor(self.controle, id_relacao)
        self.page.open(janela)

    async def obter_dados_relacao(self) -> None:
        self.dados = await self.controle.buscar_fornecedores_relacao()
        if self.dados:
            dados_ordenados = self.ordernar_dados(self.dados)
            for dado in dados_ordenados:
                self.adicionar_fornecedor(*dado)
        else:
            self.update()

    def ordernar_dados(self, dados: list) -> list:
        return sorted(dados, key=lambda x: x[3], reverse=not self.sort_ascending)
    
    def ordenar_tabela(self, e: ft.ControlEvent) -> None:
        self.sort_ascending = not self.sort_ascending
        dados_ordenados = self.ordernar_dados(self.dados)
        self.rows.clear()
        for dado in dados_ordenados:
                self.adicionar_fornecedor(*dado)

    async def atualizar_tabela(self) -> None:
        self.rows.clear()
        await self.obter_dados_relacao()

    def editar(self, id_relacao: int) -> None:
        janela = JanelaEdicaoPrecoFornecedor(self.controle, id_relacao)
        self.page.open(janela)

    def definir_controle(self, controle: ControleItem) -> None:
        self.controle = controle


class CartaoFornecedores(ft.Card):
    def __init__(self, item: ModeloItem) -> None:
        super().__init__(expand=True, elevation=5)
        self.item = item
        self.tabela = TabelaFornecedor()
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.content=ft.Container(
            content=ft.Column([
                ft.Container(
                    ft.Row([
                        ft.Text(value="Fornecedores", size=17),
                        ft.IconButton(icon=ft.Icons.PERSON_ADD_ROUNDED, on_click=self.abrir_janela_add)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding = ft.padding.symmetric(horizontal=10, vertical=5)
                ),
                ft.Divider(height=6),
                ft.Container(
                    ft.Column([
                        ft.ResponsiveRow([
                            self.tabela
                        ])
                    ],scroll=ft.ScrollMode.ALWAYS),
                    expand=True
                )
            ], spacing=1), padding=ft.padding.only(bottom=10)
        )
    
    def abrir_janela_add(self, e: ft.ControlEvent) -> None:
        controle = ControleItem(self.item, self.tabela)
        janela = JanelaAddFornecedorProduto(controle)
        self.page.open(janela)

    async def montar_tabela(self) -> None:
        controle = ControleItem(self.item, self.tabela)
        self.tabela.definir_controle(controle)
        await self.tabela.obter_dados_relacao()

    def did_mount(self) -> None:
        self.page.run_task(self.montar_tabela)


class TabelaLogProduto(ft.DataTable):
    def __init__(self, item: ModeloItem, controle_pagina: ControlePagina) -> None:
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text(value="Id"), visible=False),
                ft.DataColumn(ft.Text(value="Data"), on_sort=self.ordenar_tabela),
                ft.DataColumn(ft.Text(value="Fornecedor")),
                ft.DataColumn(ft.Text(value="Marca")),
                ft.DataColumn(ft.Text(value="Quantidade")),
                ft.DataColumn(ft.Text(value="Preco")),
                ft.DataColumn(ft.Text(value="Desconto")),
                ft.DataColumn(ft.Text(value="Valor Operação")),
                ft.DataColumn(ft.Text(value="Apagar"))
            ],
            rows=[],
            col=12,
            column_spacing=30,
            sort_column_index=0,
            sort_ascending=False,
            heading_row_height=40
        )
        self.item = item
        self.controle_pagina = controle_pagina

    def adicionar_registros(self, dados: list) -> None:
        if dados:
            self.rows.clear()
            self.dados = self.ordernar_dados(dados)
            for dado in self.dados:
                self.adicionar_linha(dado)
            self.update()

    def adicionar_linha(self, dado: list) -> None:
        async def deletar_ao_clicar(e, id=dado[0]):
            await self.apagar_registro(id)

        self.rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(dado[0]), visible=False),
                    ft.DataCell(ft.Text(datetime.strptime(dado[1], "%Y-%m-%d").strftime("%d-%m-%Y"))),
                    ft.DataCell(ft.Text(dado[2][:15], overflow=ft.TextOverflow.ELLIPSIS)),
                    ft.DataCell(ft.Text(dado[6][:15])),
                    ft.DataCell(ft.Text(f"{dado[3].replace(".", ",")} {Utilidades.encurtar_medida(self.item.medida)}")),
                    ft.DataCell(ft.Text(locale.currency(dado[4], grouping=True))),
                    ft.DataCell(ft.Text(locale.currency(dado[7], grouping=True))),
                    ft.DataCell(ft.Text(locale.currency(dado[5], grouping=True))),
                    ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, on_click=deletar_ao_clicar))
                ]
            )
        )

    def ordenar_tabela(self, e: ft.ControlEvent) -> None:
        self.sort_ascending = not self.sort_ascending
        self.rows.clear()
        self.adicionar_registros(self.dados)

    def ordernar_dados(self, dados: list) -> list:
        return sorted(dados, key=lambda x: datetime.strptime(x[1], "%Y-%m-%d"), reverse=not self.sort_ascending)

    async def atualizar_dados(self) -> None:
        await self.controle_pagina.ler_dados()

    async def apagar_registro(self, id: int) -> None:
        controle = ControleLog(id, self)
        janela = JanelaRemoverLog(controle)
        self.page.open(janela)


class TabelaConsumo(ft.DataTable):
    def __init__(self) -> None:
        super().__init__(
            columns=[
                ft.DataColumn(ft.Text(value="Dia")),
                ft.DataColumn(ft.Text(value="Consumo"))
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(value=dia)),
                        ft.DataCell(
                            ft.Text(value="0"),
                            show_edit_icon=True,
                            on_tap=self.abrir_janela_edicao,
                            data=i
                        )
                    ]
                )
                for i, dia in enumerate(["Segunda-Feira", "Terça-Feira", "Quarta-Feira", "Quinta-Feira", "Sexta-Feira", "Sábado", "Domingo"], start=1)
            ],
            col=12,
            heading_row_height=40
        )
        self.controle = None

    def adicionar_registro(self, dados: list) -> None:
        medida = Utilidades.encurtar_medida(self.controle.medida)
        for dado in dados:
            for row in self.rows:
                if int(row.cells[1].data) == int(dado[0]):
                    row.cells[1].content.value = f"{self.formatar_quantidade(dado[1])} {medida}"
                    row.update()

    def formatar_quantidade(self, quantidade: str) -> str:
        return quantidade.replace(".", ",")

    def abrir_janela_edicao(self, e: ft.ControlEvent) -> None:
        janela = JanelaEdicaoConsumo(self.controle, e.control.data)
        self.page.open(janela)

    async def ler_consumo(self) -> None:
        resultado = await self.controle.obter_dados_consumo()
        if resultado:
            self.adicionar_registro(resultado)

    async def atualizar_tabela(self) -> None:
        await self.ler_consumo()

    def definir_controle(self, controle: ControleItem):
        self.controle = controle


class Acondicionamento(ft.Container):
    def __init__(self) -> None:
        super().__init__(
            padding=ft.padding.only(left=10, top=30, right=10, bottom=10)
        )
        self.controle = None
        self.field_armazenamento = ft.TextField(label="Capacidade", width=205, border="underline")
        self.field_dias = ft.TextField(label="Dias Máximo", width=200, suffix_text="Dias", border="underline")
        self.content = ft.Column([
            ft.Row([
                self.field_armazenamento,
                self.field_dias
            ]),
            ft.Row([
                ft.IconButton(ft.Icons.SAVE, on_click=self.salvar_infos)
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=30)

    async def salvar_infos(self, e: ft.ControlEvent) -> None:
        await self.controle.inserir_valores_infos(self.field_armazenamento.value, self.field_dias.value)
        self.page.open(JanelaNotificacao("Valores Salvos", ft.icons.CHECK))

    def atualizar_valores(self, dados: list) -> None:
        if dados:
            self.field_armazenamento.value = self.formatar_quantidade(dados[0])
            self.field_dias.value = dados[1]

            self.field_armazenamento.update()
            self.field_dias.update()

    def formatar_quantidade(self, quantidade: str) -> str:
        return quantidade.replace(".", ",")

    async def ler_dados(self) -> None:
        resultado = await self.controle.obter_dados_infos()
        self.atualizar_valores(resultado)

    def configuracoes(self) -> None:
        self.field_armazenamento.suffix_text = Utilidades.encurtar_medida(self.controle.medida)
        self.field_armazenamento.update()

    def definir_controle(self, controle: ControleItem) -> None:
        self.controle = controle
        self.configuracoes()


class CartaoEspecificacoes(ft.Card):
    def __init__(self, item: ModeloItem) -> None:
        super().__init__(expand=True, elevation=5)
        self.item = item
        self.tabela = TabelaConsumo()
        self.acondicionamento = Acondicionamento()
        self.content = ft.Container(
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Consumo",
                        content=ft.Container(
                            ft.Column([
                                ft.ResponsiveRow([
                                    self.tabela
                                ])
                            ],scroll=ft.ScrollMode.ALWAYS),
                            padding=ft.padding.only(bottom=10), expand=True
                        )
                    ),
                    ft.Tab(
                        text="Acondicionamento",
                        content=self.acondicionamento
                    )
                ],
                expand=True
            )
        )

    def definir_controles(self) -> None:
        self.tabela.definir_controle(ControleItem(self.item, self.tabela))
        self.acondicionamento.definir_controle(ControleItem(self.item, None))

    async def ler_dados(self) -> None:
        self.definir_controles()
        await self.tabela.ler_consumo()
        await self.acondicionamento.ler_dados()

    def did_mount(self) -> None:
        self.page.run_task(self.ler_dados)


class Graficos:
    def serie_preco_operacao(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["preco_operacao"]))

        fig.update_xaxes(tickformat="%d-%m-%y")
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            width=900,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575")
        )
        return PlotlyChart(fig, expand=True)
    
    def serie_preco_medio(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["preco"]))

        fig.update_xaxes(tickformat="%d-%m-%y")
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            width=900,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575")
        )
        return PlotlyChart(fig, expand=True)
    
    def serie_quantidade(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["quantidade"]))

        fig.update_xaxes(tickformat="%d-%m-%y")
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            width=900,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575")
        )
        return PlotlyChart(fig, expand=True)
    
    def barras_fornecedor(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=df["preco_operacao"], y=df.index, orientation="h", text=df["preco_operacao"])
        )

        fig.update_traces(textfont_size=20)
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            showlegend=False,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#f2f3fa"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            barcornerradius=15,
            width=900
        )
        return PlotlyChart(fig, expand=True)


class OperadorDados:
    def preco_operacao(self, df: pd.DataFrame) -> pd.DataFrame:
        freq = self.definir_frequencia(df)
        return df.set_index("data_operacao").resample(freq).agg({"preco_operacao": "sum"}).ffill()
    
    def preco_medio(self, df: pd.DataFrame) -> pd.DataFrame:
        freq = self.definir_frequencia(df)
        return df.set_index("data_operacao").resample(freq).agg({"preco": "mean"}).ffill()
    
    def quantidade(self, df: pd.DataFrame) -> pd.DataFrame:
        freq = self.definir_frequencia(df)
        df["quantidade"] = pd.to_numeric(df["quantidade"])
        return df.set_index("data_operacao").resample(freq).agg({"quantidade": "sum"}).ffill()
    
    def preco_operacao_por_fornecedor(self, df: pd.DataFrame) -> pd.DataFrame:
        df["fornecedor"] = df["fornecedor"].apply(self.__verificar_prefixo)
        df_group = df.groupby("fornecedor").agg({"preco_operacao": "sum"})
        df_group = df_group.round(2)
        df_group.sort_values("preco_operacao", inplace=True)
        return df_group
    
    def __verificar_prefixo(self, palavra):
        palavra_normalizada = unicodedata.normalize("NFKD", palavra)
        palavra_sem_acentos = palavra_normalizada.encode('ASCII', 'ignore').decode('ASCII')
        palavras = ("supermercado", "mercado", "hortifruti", "sacolao", "hidroponia")
        for p in palavras:
            if palavra_sem_acentos.startswith(p):
                palavra = palavra[palavra_sem_acentos.find(p) + len(p):]
        return palavra
    
    def definir_frequencia(self, df: pd.DataFrame) -> str:
        dias = (df["data_operacao"].max() - df["data_operacao"].min()).days
        if dias <= 31:
            freq = "D"
        elif dias <= 90:
            freq = "W"
        else:
            freq = "ME"
        return freq


class AreaGrafico(ft.Card, ABC):
    def __init__(self):
        super().__init__(expand=True, elevation=5)
        self.graficos = Graficos()
        self.operador_dados = OperadorDados()
        self.area = ft.Container(
            ft.ProgressRing(),
            alignment=ft.alignment.center,
            expand=True,
            border_radius=ft.border_radius.all(15)
        )
        self.content = self.area

    @abstractmethod
    def criar_grafico(self, df: pd.DataFrame) -> None:
        ...


class GraficoSeriePrecoOperacao(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.preco_operacao(df)
        self.area.content = ft.Stack([
            self.graficos.serie_preco_operacao(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Evolução Do Preço da Operação"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class GraficoSeriePrecoMedio(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.preco_medio(df)
        self.area.content = ft.Stack([
            self.graficos.serie_preco_medio(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Evolução Do Preço"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class GraficoSerieQuantidade(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.quantidade(df)
        self.area.content = ft.Stack([
            self.graficos.serie_quantidade(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Evolução Da Quantidade"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class GraficoBarrasPrecoOperacaoFornecedor(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.preco_operacao_por_fornecedor(df)
        self.area.content = ft.Stack([
            self.graficos.barras_fornecedor(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Preço Operaçao Por Fornecedor"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class PainelDashboard(ft.AlertDialog):
    def __init__(self, df: pd.DataFrame):
        super().__init__(modal=True)
        self.df = df
        self.grafico_serie_preco_operacao = GraficoSeriePrecoOperacao()
        self.grafico_serie_preco_medio = GraficoSeriePrecoMedio()
        self.grafico_serie_quantidade = GraficoSerieQuantidade()
        self.barras_preco_operacao_fornecedor = GraficoBarrasPrecoOperacaoFornecedor()
        self.content = ft.Container(
            content=ft.ResponsiveRow([
                ft.Column([
                    self.grafico_serie_preco_operacao,
                    self.grafico_serie_quantidade
                ], col=6),
                ft.Column([
                    self.grafico_serie_preco_medio,
                    self.barras_preco_operacao_fornecedor
                ], col=6)
            ]), expand=True, width=1000
        )
        self.actions = [
            ft.TextButton(
                content=ft.Text(value="Fechar", color=ft.Colors.BLACK87),
                on_click=lambda e: self.page.close(self),
                style=ft.ButtonStyle(bgcolor={ft.ControlState.HOVERED: ft.Colors.RED_100})
            )
        ]

    def did_mount(self):
        self.grafico_serie_preco_operacao.criar_grafico(self.df)
        self.grafico_serie_preco_medio.criar_grafico(self.df)
        self.grafico_serie_quantidade.criar_grafico(self.df)
        self.barras_preco_operacao_fornecedor.criar_grafico(self.df)


class PaginaConfigItem(ft.Container):
    def __init__(self, item: ModeloItem) -> None:
        super().__init__(expand=True)
        self.item = item
        self.data_fim = datetime.now()
        self.data_inicio = self.data_fim - timedelta(180)
        self.tabela_log = TabelaLogProduto(self.item, ControlePagina(self))
        self.criar_conteudo()

    def criar_conteudo(self) -> None:
        self.criar_variaveis_textos()
        self.content = ft.ResponsiveRow([
            ft.Column([
                CartaoFornecedores(self.item),
                CartaoEspecificacoes(self.item)
            ], col=4, spacing=5),
            ft.Column([
                ft.ResponsiveRow([
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Text("Frequência", size=15, height=ft.FontWeight.W_400),
                                self.frequencia
                            ]),
                            padding=ft.padding.only(top=10, left=10, bottom=10, right=10)
                        ),
                        col=2, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Text("Qtd. Média", size=15, height=ft.FontWeight.W_400),
                                self.qtd_media
                            ]),
                            padding=ft.padding.only(top=10, left=10, bottom=10)
                        ),
                        col=2, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Text("Preço Médio", size=15, height=ft.FontWeight.W_400),
                                self.preco_medio
                            ]),
                            padding=ft.padding.only(top=10, left=10, bottom=10)
                        ),
                        col=2, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Text("Qtd. Total", size=15, height=ft.FontWeight.W_400),
                                self.qtd_total
                            ]),
                            padding=ft.padding.only(top=10, left=10, bottom=10)
                        ),
                        col=2, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Text("Valor Total", size=15, height=ft.FontWeight.W_400),
                                self.valor_total
                            ]),
                            padding=ft.padding.only(top=10, left=10, bottom=10)
                        ),
                        col=2, elevation=5
                    ),
                    ft.Container(
                        ft.Row([
                                ft.IconButton(ft.Icons.DASHBOARD_ROUNDED, on_click=self.abrir_painel_dash)
                            ], alignment=ft.MainAxisAlignment.END
                        ),
                        col=2, padding=ft.padding.only(bottom=10)
                    )
                ]),
                ft.Card(
                    ft.Container(
                        ft.Column([
                            ft.ResponsiveRow([
                                self.tabela_log
                            ])
                        ], scroll=ft.ScrollMode.ALWAYS),
                        padding=ft.padding.only(top=5, bottom=10), expand=True
                    ), expand=True, elevation=5
                )
            ], col=8, spacing=5)
        ])

    def botoes_calendario(self):
        self.filtro_periodo = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text=label, checked=bool(ativo), on_click=self.filtrar_por_periodo)
                for label, ativo in zip(["Mês", "Trimestre", "Semestre", "Tudo"], [0, 0, 1, 0])
            ],
            icon=ft.Icons.FILTER_ALT
        )
        return ft.Row([
            ft.IconButton(
                ft.Icons.CALENDAR_MONTH,
                on_click=self.abrir_calendario_inicio,
                tooltip="Inicio"
            ),
            ft.IconButton(
                ft.Icons.CALENDAR_MONTH,
                on_click=self.abrir_calendario_fim,
                tooltip="Fim"
            ),
            self.filtro_periodo
        ],
        alignment=ft.MainAxisAlignment.END,
        spacing=5
        )

    async def filtrar_por_periodo(self, e: ft.ControlEvent) -> None:
        for item in self.filtro_periodo.items:
            item.checked = item.text == e.control.text
            item.update()
        if e.control.text != "Tudo":
            await self.selecionar_data_periodo(e.control.text)
        else:
            await self.ler_todos_dados()

    async def selecionar_data_periodo(self, periodo: str) -> None:
        self.data_fim = datetime.now()
        match periodo:
            case "Mês":
                self.data_inicio = self.data_fim - timedelta(30)
            case "Trimestre":
                self.data_inicio = self.data_fim - timedelta(90)
            case "Semestre":
                self.data_inicio = self.data_fim - timedelta(180)
        
        await self.ler_dados()

    def criar_variaveis_textos(self) -> None:
        self.frequencia = ft.Text("0 Dias")
        self.qtd_media = ft.Text("0")
        self.preco_medio = ft.Text("0")
        self.qtd_total = ft.Text("0")
        self.valor_total = ft.Text("0")

    def criar_calendario(self, data: datetime, on_change: Callable) -> ft.DatePicker:
        return ft.DatePicker(
            first_date=datetime(year=2021, month=1, day=1),
            last_date=datetime(year=2030, month=12, day=31),
            value=data,
            on_change=on_change,
            confirm_text="Definir"
        )

    def abrir_calendario_inicio(self, e: ft.ControlEvent) -> None:
        self.page.open(self.criar_calendario(self.data_inicio, self.selecionar_data_inicio))

    def abrir_calendario_fim(self, e: ft.ControlEvent) -> None:
        self.page.open(self.criar_calendario(self.data_fim, self.selecionar_data_fim))

    def selecionar_data_inicio(self, e: ft.ControlEvent) -> None:
        self.data_inicio = e.control.value

    async def selecionar_data_fim(self, e: ft.ControlEvent) -> None:
        self.data_fim = e.control.value
        await self.ler_dados()

    def atualizar_tabela(self, dados: list) -> None:
        self.tabela_log.adicionar_registros(dados)

    def atualizar_cartoes(self, dados: list) -> None:
        frequencia, qtd_media, preco_medio, qtd_total, valor_total = self.transformar_dados_cartoes(dados)
        medida = Utilidades.encurtar_medida(self.item.medida)
        self.atualizar_valor(self.frequencia, f"{int(frequencia)} Dias")
        self.atualizar_valor(self.qtd_media, self.formatar_quantidade(qtd_media, medida))
        self.atualizar_valor(self.preco_medio, f"{locale.currency(round(preco_medio, 2), grouping=True)}")
        self.atualizar_valor(self.qtd_total, self.formatar_quantidade(qtd_total, medida))
        self.atualizar_valor(self.valor_total, f"{locale.currency(round(valor_total, 2), grouping=True)}")

    def transformar_dados_cartoes(self, dados: list) -> tuple:
        array = np.array([list(dado[3:6]) for dado in dados], dtype=float)
        array_data = np.sort(np.array([dado[1] for dado in dados], dtype="datetime64"))

        qtd_media = np.mean(array[:, 0])
        preco_medio = np.mean(array[:, 1])
        qtd_total = np.sum(array[:, 0])
        valor_total = np.sum(array[:, 2])

        diff_data = np.diff(array_data)
        frequencia = (np.mean(diff_data) / np.timedelta64(1, 'D')) if diff_data.size > 0 else 0

        return frequencia, qtd_media, preco_medio, qtd_total, valor_total

    def atualizar_valor(self, atributo, valor: int):
        atributo.value = valor
        atributo.update()

    def formatar_quantidade(self, valor: float, medida: str) -> str:
        if medida == "U":
            valor = f"{int(valor)} {medida}"
        else:
            valor = f"{str(round(valor, 3)).replace(".", ",")} {medida}"
        return valor
    
    def abrir_painel_dash(self, e):
        try:
            self.page.open(PainelDashboard(self.df))
        except Exception as e:
            print(e)

    async def ler_dados(self) -> None:
        bd = BancoDeDados("db_app6.db")
        dados = await bd.fetch_all(
            q6.obter_logs,
            (self.item.id, self.data_inicio.strftime("%Y-%m-%d"), self.data_fim.strftime("%Y-%m-%d"))
        )
        if dados:
            self.atualizar_tabela(dados)
            self.atualizar_cartoes(dados)
            self.criar_data_frame(dados)

    async def ler_todos_dados(self) -> None:
        bd = BancoDeDados("db_app6.db")
        dados = await bd.fetch_all(
            q6.obter_todos_logs,
            (self.item.id,)
        )
        if dados:
            self.atualizar_tabela(dados)
            self.atualizar_cartoes(dados)
            self.criar_data_frame(dados)

        self.data_inicio = self.df["data_operacao"].min()
        self.data_fim = self.df["data_operacao"].max()

    def criar_data_frame(self, dados):
        self.df = pd.DataFrame(
            dados,
            columns=[
                "id",
                "data_operacao",
                "fornecedor",
                "quantidade",
                "preco",
                "preco_operacao",
                "marca",
                "desconto"
            ]
        )
        self.df["data_operacao"] = pd.to_datetime(self.df["data_operacao"])

    def did_mount(self) -> None:
        self.page.run_task(self.ler_dados)
