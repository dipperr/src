import flet as ft
import plotly.graph_objects as go
from flet.plotly_chart import PlotlyChart
import locale
import pandas as pd
from datetime import datetime, timedelta
from typing import Callable
from abc import ABC, abstractmethod

from acessorios import Utilidades, BancoDeDados
import querys_app6 as q6


locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
pd.set_option('display.max_columns', None)

class Graficos:
    def total_categoria(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=df["preco_operacao"], y=df["categoria"], orientation="h", text=df["preco_operacao"])
        )

        fig.update_traces(textfont_size=20)
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            showlegend=False,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#f2f3fa"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            barcornerradius=30,
            width=1000
        )
        return PlotlyChart(fig, expand=True)
    
    def serie_categoria(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        for cat in df["categoria"].unique():
            df_fil = df[df["categoria"] == cat]
            fig.add_trace(
                go.Scatter(x=df_fil["data_operacao"], y=df_fil["preco_operacao"], mode="lines+markers", name=cat)
            )

        fig.update_xaxes(tickformat="%d-%m-%y")
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            width=1000,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=20))
        )
        return PlotlyChart(fig, expand=True)

    def serie_total(self, df: pd.DataFrame) -> PlotlyChart:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["preco_operacao"]))

        fig.update_xaxes(tickformat="%d-%m-%y")
        fig.update_layout(
            margin=dict(t=5,l=10,b=10,r=10),
            paper_bgcolor="#f2f3fa",
            plot_bgcolor="#f2f3fa",
            width=1150,
            yaxis=dict(tickfont=dict(size=20), gridcolor="#747575"),
            xaxis=dict(tickfont=dict(size=20), gridcolor="#747575")
        )
        return PlotlyChart(fig, expand=True)


class OperadorDados:
    def total_categoria(self, df: pd.DataFrame) -> pd.DataFrame:
        categorias = df.groupby('categoria')['preco_operacao'].sum()
        categorias = categorias.to_frame().reset_index().sort_values("preco_operacao").round(2)
        categorias["categoria"] = categorias["categoria"].str.slice(0, 7)
        return categorias
    
    def serie_categoria(self, df: pd.DataFrame) -> pd.DataFrame:
        freq = self.definir_frequencia(df)
        _df =  (
            df
            .sort_values("data_operacao")
            .groupby("categoria")
            .apply(lambda x: x.set_index("data_operacao")
                .resample(freq)
                .agg({
                    "preco_operacao": "sum"
                })
                .ffill(),
                include_groups=False
            )
            .reset_index()
        )
        return _df[_df["preco_operacao"] > 0]

    def serie_total(self, df: pd.DataFrame) -> pd.DataFrame:
        freq = self.definir_frequencia(df)
        _df =  (
            df
            .sort_values("data_operacao")
            .set_index("data_operacao")
            .resample(freq)
            .agg({"preco_operacao": "sum"})
            .ffill()
        )
        return _df[_df["preco_operacao"] > 0]

    def dados_tabela(self, df: pd.DataFrame, categoria: str) -> pd.DataFrame:
        def calcular_perda(grupo):
            return grupo['preco_operacao'].sum() - (grupo['quantidade'] * grupo['menor_valor']).sum() + grupo['saving'].sum()

        df_fil = df[df["categoria"] == categoria]
        df_group = (
            df_fil.groupby(['nome_produto', 'medida'])
            .agg(
                quantidade=("quantidade", "sum"),
                preco_operacao=("preco_operacao", "sum"),
                saving=("saving", "sum")
            )
            .reset_index()
        )
        df_perda = df_fil.groupby('nome_produto').apply(calcular_perda, include_groups=False).reset_index(name='perda')
        df_perda["perda"] = df_perda["perda"].clip(lower=0)
        df_merge = pd.merge(df_group, df_perda, on="nome_produto", how="left")
        return df_merge
    
    def definir_frequencia(self, df: pd.DataFrame) -> str:
        dias = (df["data_operacao"].max() - df["data_operacao"].min()).days
        if dias < 29:
            freq = "D"
        elif dias < 90:
            freq = "W"
        else:
            freq = "ME"
        return freq

    def estatisticas_cartoes(self, dados: pd.DataFrame) -> list:
        dados["quantidade"] = pd.to_numeric(dados["quantidade"])
        total_valor = dados["preco_operacao"].sum()
        qtd_x_menor_preco = dados["quantidade"] * dados["menor_valor"]
        perda = dados["preco_operacao"].sum() - qtd_x_menor_preco.sum() + dados["saving"].sum()
        saving = dados["saving"].sum()
        return (total_valor, perda, saving)



class AreaGrafico(ft.Card, ABC):
    def __init__(self):
        super().__init__(expand=True, elevation=5)
        self.graficos = Graficos()
        self.operador_dados = OperadorDados()
        self.area = ft.Container(
            ft.ProgressRing(),
            alignment=ft.alignment.center,
            border_radius=ft.border_radius.all(15)
        )
        self.content = self.area

    @abstractmethod
    def criar_grafico(self, df: pd.DataFrame) -> None:
        ...


class GraficoTotalCategoria(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        categorias = self.operador_dados.total_categoria(df)
        self.area.content = ft.Stack([
            self.graficos.total_categoria(categorias),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Valor gasto por categoria"), 
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class GraficoSerieCategoria(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.serie_categoria(df)
        self.area.content = ft.Stack([
            self.graficos.serie_categoria(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Evolução do valor gasto por categoria"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class GraficoSerieTotal(AreaGrafico):
    def __init__(self) -> None:
        super().__init__()

    def criar_grafico(self, df: pd.DataFrame) -> None:
        dados = self.operador_dados.serie_total(df)
        self.area.content = ft.Stack([
            self.graficos.serie_total(dados),
            ft.Row([
                ft.Container(
                    ft.Icon(ft.Icons.INFO_OUTLINE, tooltip="Evolução do valor gasto"),
                    padding=ft.padding.all(5)
                )
            ], alignment=ft.MainAxisAlignment.END)
        ], expand=True)
        self.area.update()


class TabelaDashboard(ft.DataTable):
    def __init__(self) -> None:
        super().__init__(
            col=12,
            column_spacing=30,
            columns=[
                ft.DataColumn(ft.Text("Nome")),
                ft.DataColumn(ft.Text("Quantidade")),
                ft.DataColumn(ft.Text("Valor Gasto"), on_sort=self.ordernar_dados),
                ft.DataColumn(ft.Text("Perda")),
                ft.DataColumn(ft.Text("Saving"))
            ],
            sort_column_index=2,
            sort_ascending=False,
            heading_row_height=40
        )

    def atualizar_linhas(self, dados: pd.DataFrame) -> None:
        self.dados = dados
        self.dados.sort_values("preco_operacao", ascending=self.sort_ascending, inplace=True)
        self.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(row["nome_produto"], max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                    ft.DataCell(ft.Text(self.formatar_quantidade(row["quantidade"], row["medida"]))),
                    ft.DataCell(ft.Text(locale.currency(row["preco_operacao"], grouping=True))),
                    ft.DataCell(ft.Text(locale.currency(row["perda"], grouping=True))),
                    ft.DataCell(ft.Text(locale.currency(row["saving"], grouping=True)))
                ]
            )
            for i, row in self.dados.iterrows()
        ]
        self.update()

    def ordernar_dados(self, e: ft.ControlEvent) -> None:
        self.sort_ascending = not self.sort_ascending
        self.atualizar_linhas(self.dados)

    def formatar_quantidade(self, qtd: str, medida: str) -> str:
        qtd_f =  int(qtd) if medida == "unidade" else locale.format_string("%.3f", qtd, grouping=True)
        return f"{qtd_f} {Utilidades.encurtar_medida(medida)}"
        

class PaginaDashboard(ft.Container):
    def __init__(self) -> None:
        super().__init__(expand=True)
        self.area_grafico_total_categoria = GraficoTotalCategoria()
        self.area_grafico_serie_categoria = GraficoSerieCategoria()
        self.area_grafico_serie_total = GraficoSerieTotal()
        self.tabela = TabelaDashboard()
        self.data_fim = datetime.now()
        self.data_inicio = self.data_fim - timedelta(180)
        self.text_intervalo_data = ft.Text(
            f"{self.data_inicio.strftime("%d-%m-%Y")} - {self.data_fim.strftime("%d-%m-%Y")}",
            size=20,
            height=ft.FontWeight.W_500
        )
    
    def criar_estrutura(self) -> None:
        self.text_total_gasto = ft.Text("R$ 00,00", size=17, weight=ft.FontWeight.W_500)
        self.text_perdas = ft.Text("R$ 00,00", size=17, weight=ft.FontWeight.W_500)
        self.text_saving = ft.Text("R$ 00,00", size=17, weight=ft.FontWeight.W_500)
        self.botao_filtro = ft.PopupMenuButton(icon=ft.Icons.FILTER_ALT, tooltip="Categorias")
        self.content = ft.ResponsiveRow([
            ft.Column([
                ft.ResponsiveRow([
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Row([
                                    ft.Text("Valor Gasto", size=20, weight=ft.FontWeight.W_500),
                                    ft.Icon(ft.Icons.ATTACH_MONEY_ROUNDED, size=20, color=ft.Colors.GREEN)
                                ]),
                                self.text_total_gasto
                            ], spacing=5),
                            padding=ft.padding.only(top=5, left=20, bottom=5)
                        ),
                        col=4, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Row([
                                    ft.Text("Saving", size=20, weight=ft.FontWeight.W_500),
                                    ft.Icon(ft.Icons.ARROW_UPWARD_ROUNDED, size=20, color=ft.Colors.GREEN)
                                ]),
                                self.text_saving
                            ], spacing=5),
                            padding=ft.padding.only(top=5, left=20, bottom=5)
                        ),
                        col=4, elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column([
                                ft.Row([
                                    ft.Text("Perdas", size=20, weight=ft.FontWeight.W_500),
                                    ft.Icon(ft.Icons.ARROW_DOWNWARD_ROUNDED, size=20, color=ft.Colors.RED)
                                ]),
                                self.text_perdas
                            ], spacing=5),
                            padding=ft.padding.only(top=5, left=20, bottom=5)
                        ),
                        col=4, elevation=5
                    )
                ]),
                ft.Card(
                    ft.Container(
                        ft.Stack([
                            ft.Column([
                                ft.ResponsiveRow([
                                    self.tabela
                                ])
                            ], scroll=ft.ScrollMode.ALWAYS),
                            ft.Row([
                                self.botao_filtro
                            ], alignment=ft.MainAxisAlignment.END)
                        ], expand=True), expand=True, padding=ft.padding.only(bottom=10)
                    ), expand=True, elevation=5
                ),
                ft.Container(
                    self.area_grafico_serie_total, expand=True
                )
            ], col=6, spacing=5),
            ft.Column([
                self.area_grafico_total_categoria,
                self.area_grafico_serie_categoria
            ], col=6, spacing=5)
        ])
        self.update()

    def botoes_calendario(self):
        self.filtro_periodo = self.filtro_periodo = ft.PopupMenuButton(
            items=[
                ft.PopupMenuItem(text=label, checked=bool(ativo), on_click=self.filtrar_por_periodo)
                for label, ativo in zip(["Mês", "Trimestre", "Semestre", "Tudo"], [0, 0, 1, 0])
            ],
            icon=ft.Icons.FILTER_ALT
        )
        return ft.Row(
            [
                self.text_intervalo_data,
                ft.Row([
                    ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="Inicio", on_click=self.abrir_calendario_inicio),
                    ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="Fim", on_click=self.abrir_calendario_fim),
                    self.filtro_periodo
                ])
            ],
            alignment=ft.MainAxisAlignment.END
        )

    async def filtrar_por_periodo(self, e: ft.ControlEvent) -> None:
        for item in self.filtro_periodo.items:
            item.checked = item.text == e.control.text
            item.update()
        if e.control.text != "Tudo":
            await self.selecionar_data_periodo(e.control.text)
        else:
            await self.ler_todos_dados()
        self.atualizar_texto_intervalo_data()

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
        self.atualizar_texto_intervalo_data()
        await self.ler_dados()

    def atualizar_texto_intervalo_data(self) -> None:
        self.text_intervalo_data.value = f"{self.data_inicio.strftime("%d-%m-%Y")} - {self.data_fim.strftime("%d-%m-%Y")}"
        self.text_intervalo_data.update()

    def atualizar_cards(self) -> None:
        oper_dados = OperadorDados()
        total_valor, perda, saving = oper_dados.estatisticas_cartoes(self.df.copy())
        self.text_total_gasto.value = locale.currency(total_valor, grouping=True)
        self.atualizar_valor(self.text_total_gasto, locale.currency(total_valor, grouping=True))
        self.atualizar_valor(self.text_perdas, locale.currency(perda, grouping=True))
        self.atualizar_valor(self.text_saving, locale.currency(saving, grouping=True))

    def atualizar_valor(self, atributo, valor: int):
        atributo.value = valor
        atributo.update()

    def adicionar_categorias_botao(self) -> None:
        categorias = self.df["categoria"].unique()
        self.botao_filtro.items = [
            ft.PopupMenuItem(value, height=40, on_click=self.acao_atualizar_tabela)
            for value in categorias
        ]
        self.botao_filtro.update()
        self.atualizar_tabela(categorias[0])

    def acao_atualizar_tabela(self, e: ft.ControlEvent) -> None:
        self.atualizar_tabela(e.control.text)

    def atualizar_tabela(self, categoria: str) -> None:
        dados_transformados = OperadorDados().dados_tabela(self.df, categoria)
        self.tabela.atualizar_linhas(dados_transformados)

    def criar_grafico(self) -> None:
        self.area_grafico_total_categoria.criar_grafico(self.df)
        self.area_grafico_serie_categoria.criar_grafico(self.df)
        self.area_grafico_serie_total.criar_grafico(self.df)

    async def ler_dados(self) -> None:
        db = BancoDeDados("db_app6.db")
        dados = await db.fetch_all(q6.obter_logs_para_dash, (self.data_inicio.strftime("%Y-%m-%d"), self.data_fim.strftime("%Y-%m-%d")))
        if dados:
            self.criar_df(dados)
            self.atualizar_cards()
            self.criar_grafico()
            self.adicionar_categorias_botao()

    async def ler_todos_dados(self) -> None:
        db = BancoDeDados("db_app6.db")
        dados = await db.fetch_all(q6.obter_todos_logs_para_dash)

        if dados:
            self.criar_df(dados)
            self.atualizar_cards()
            self.criar_grafico()
            self.adicionar_categorias_botao()

        self.data_inicio = self.df["data_operacao"].min()
        self.data_fim = self.df["data_operacao"].max()

    def criar_df(self, dados: list) -> None:
        self.df = pd.DataFrame(
            dados,
            columns=[
                "nome_produto",
                "categoria",
                "medida",
                "quantidade",
                "data_operacao",
                "preco",
                "preco_operacao",
                "saving",
                "menor_valor"
            ]
        )
        self.df["data_operacao"] = pd.to_datetime(self.df["data_operacao"])
        self.df["quantidade"] = pd.to_numeric(self.df["quantidade"])
    
    async def criar_dash(self) -> None:
        self.criar_estrutura()
        await self.ler_dados()

    def did_mount(self) -> None:
        self.page.run_task(self.criar_dash)