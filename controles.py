import asyncio
from datetime import datetime
import flet as ft
from typing import Optional, Union

from acessorios import BancoDeDados
import querys_app6 as q6
from modelos import ModeloFornecedor, ModeloItem


class LogProduto:
    def __init__(self) -> None:
        self.bd = BancoDeDados("db_app6.db")

    async def criar_log(
            self,
            id_produto: int,
            id_fornecedor: int,
            preco: float,
            quantidade: str,
            data_operacao: str,
            marca: str,
            desconto: float
        ) -> None:
        preco_op = self.calcular_preco_operacao(preco, quantidade, desconto)
        await self.bd.execute(
            q6.criar_log,
            (id_produto, id_fornecedor, preco, quantidade, preco_op, data_operacao, marca, desconto)
        )

    def calcular_preco_operacao(self, preco: float, quantidade: str, desconto: float) -> float:
        return float(preco) * float(quantidade) - float(desconto)


class ControleLog:
    def __init__(self, id_log: int, visualizacao: ft.Control) -> None:
        self.id_log = id_log
        self.visualizacao = visualizacao
        self.bd = BancoDeDados("db_app6.db")

    async def apagar_log_compra(self) -> None:
        print(f"apagando log ed id: {self.id_log}")
        await self.bd.execute(q6.apagar_log, (self.id_log,))
        await self.visualizacao.atualizar_dados()


class ControleFornecedor:
    def __init__(
        self,
        modelo: Optional[ModeloFornecedor]=None,
        visualizacao: Optional[ft.Control]=None
    ) -> None:
        self.modelo = modelo
        self.visualizacao = visualizacao
        self.bd = BancoDeDados("db_app6.db")

    @property
    def nome(self):
        return self.modelo.nome.title()

    async def adicionar_fornecedor(self) -> None:
        try:
            self.visualizacao.salvando()
            await self.bd.execute(
                q6.adicionar_fornecedor,
                (
                    self.modelo.nome,
                    self.modelo.telefone,
                    self.modelo.responsavel,
                    self.modelo.logradouro,
                    self.modelo.numero,
                    self.modelo.bairro,
                    self.formatar_cep(self.modelo.cep),
                    self.modelo.cidade,
                    self.modelo.estado
                )
            )
        except Exception as e:
            self.visualizacao.generico(ft.Icons.ERROR, "Houve um erro ao salvar")
        else:
            self.visualizacao.salvo()
            await asyncio.sleep(1)
        finally:
            self.visualizacao.limpar()

    async def buscar_fornecedores_relacao(self, id_item: int) -> list:
        return await self.bd.fetch_all(q6.buscar_relacao_produto_fornecedor, (id_item,))
    
    async def obter_fornecedores(self) -> None:
        return await self.bd.fetch_all(q6.obter_fornecedores)
    
    async def apagar_fornecedor(self) -> None:
        await self.bd.execute(q6.apagar_fornecedor, (self.modelo.id,))
        await self.visualizacao.atualizar_grade()
    
    def formatar_cep(self, cep: str) -> str:
        return cep.replace("-", "")


class ControleItem:
    def __init__(self, modelo: ModeloItem, visualizacao: ft.Control) -> None:
        self.modelo = modelo
        self.visualizacao = visualizacao
        self.bd = BancoDeDados("db_app6.db")

    @property
    def id(self) -> int:
        return self.modelo.id
    
    @property
    def medida(self) -> str:
        return self.modelo.medida
    
    @property
    def nome(self) -> str:
        return self.modelo.nome.title()
    
    async def obter_medida(self) -> list:
        return await self.bd.fetch_one(q6.obter_medida_produto, (self.modelo.id,))

    async def criar_item(self) -> None:
        try:
            self.visualizacao[1].salvando()
            item_id = await self.bd.execute_return_id(q6.cadastrar_produto, (self.modelo.nome, self.modelo.medida, self.modelo.categoria))
        except Exception as e:
            self.visualizacao[1].generico(ft.Icons.ERROR, "Houve um erro ao salvar")
        else:
            await self.criar_registro_consumo(item_id)
            self.visualizacao[1].salvo()
            await asyncio.sleep(1)
            await self.visualizacao[0].atualizar_grade()
        finally:
            self.visualizacao[1].limpar()

    async def criar_registro_consumo(self, item_id: int) -> None:
        for dia in range(1, 8):
            await self.bd.execute(q6.criar_registro_consumo, (item_id, dia))

    async def apagar_item(self) -> None:
        await self.bd.execute(q6.apagar_resgistro_produto, (self.modelo.id,))
        await self.visualizacao.atualizar_grade()

    async def salvar_log_compra(
            self,
            fornecedor: str,
            preco: float,
            quantidade: str,
            data: str,
            marca: str,
            desconto: float
        ) -> None:
        if all([quantidade, fornecedor, marca, preco, data]):
            try:
                quantidade = self.formatar_valor(quantidade)
                preco = float(self.formatar_valor(preco))
                data_formatada = datetime.strptime(data, "%d-%m-%Y").strftime('%Y-%m-%d')
                self.visualizacao.dialogo.salvando()
                await LogProduto().criar_log(self.modelo.id, fornecedor, preco, quantidade, data_formatada, marca, desconto)
            except Exception as e:
                print(e)
                self.visualizacao.dialogo.generico(ft.Icons.ERROR, "Houve um erro ao salvar")
                await asyncio.sleep(1)
            else:
                self.visualizacao.dialogo.salvo()
                await asyncio.sleep(1)
            finally:
                self.visualizacao.dialogo.limpar()
        else:
            await self.visualizacao.mostrar_erro_campo_vazio()

    async def buscar_fornecedores_relacao(self) -> list:
        return await ControleFornecedor().buscar_fornecedores_relacao(self.modelo.id)
    
    async def criar_relacao_produto_fornecedor(self, fornecedor_id: int, marca: str, preco: float) -> None:
        marca_formatada = marca if marca else "-"
        preco_formatado = self.formatar_valor(preco)
        await self.bd.execute(
            q6.criar_relacao_produto_fornecedor,
            (self.modelo.id, fornecedor_id, preco_formatado, marca_formatada)
            )
        await self.visualizacao.atualizar_tabela()

    async def obter_fornecedores(self) -> list:
        return await ControleFornecedor().obter_fornecedores()
    
    async def apagar_relacao_produto_fornecedor(self, id_relacao: int) -> None:
        await self.bd.execute(q6.apagar_relacao_produto_fornecedor, (id_relacao,))
        await self.visualizacao.atualizar_tabela()
    
    async def atualizar_preco_relacao(self, preco: float, id_relacao: int) -> None:
        preco = self.formatar_valor(preco)
        await self.bd.execute(q6.atualizar_preco_relacao, (preco, id_relacao))
        await self.visualizacao.atualizar_tabela()

    async def atualizar_consumo(self, consumo: str, dia_semana: int) -> None:
        consumo = self.formatar_valor(consumo)
        await self.bd.execute(q6.atualizar_consumo_produto, (consumo, self.modelo.id, dia_semana))
        await self.visualizacao.atualizar_tabela()

    async def obter_dados_consumo(self) -> list:
        return await self.bd.fetch_all(q6.obter_dados_consumo, (self.modelo.id,))
    
    async def obter_dados_infos(self) -> list:
        return await self.bd.fetch_one(q6.obter_dados_infos, (self.modelo.id,))
    
    async def inserir_valores_infos(self, armazenamento: str, dias: int) -> None:
        armazenamento = self.formatar_valor(armazenamento)
        await self.bd.execute(q6.inserir_valores_infos, (self.modelo.id, armazenamento, dias, armazenamento, dias))

    def formatar_valor(self, valor: Union[int, float]) -> str:
        return str(valor).replace(".", "").replace(",", ".")
    

class ControleGradeItem:
    def __init__(self, pagina: ft.Control) -> None:
        self.pagina = pagina

    async def atualizar_grade(self) -> None:
        await self.pagina.criar_cards_itens()

    def filtrar(self, item: str) -> None:
        self.pagina.filtrar(item)

    def fitrar_categoria(self, categoria: str) -> None:
        self.pagina.filtrar_categoria(categoria)


class ControleGradeFornecedor:
    def __init__(self, pagina: ft.Control) -> None:
        self.pagina = pagina

    async def atualizar_grade(self) -> None:
        await self.pagina.criar_cards_fornecedores()


class ControlePagina:
    def __init__(self, pagina_pricipal: ft.Control, barra_menu_voltar: ft.Control) -> None:
        self.pagina_principal = pagina_pricipal
        self.barra_menu_voltar = barra_menu_voltar

    def atualizar_pagina(self, conteudo: ft.Control) -> None:
        self.pagina_principal.atualizar_conteudo(conteudo)

    def adicionar_label_barra(self, label: str) -> None:
        self.barra_menu_voltar.title = ft.Text(label)
        self.barra_menu_voltar.update()

    def add_acao_barra(self, acao: ft.Control) -> None:
        self.barra_menu_voltar.actions.append(
            acao
        )
        self.barra_menu_voltar.update()

    def alterar_para_barra_voltar(self) -> None:
        self.pagina_principal.page.appbar = self.barra_menu_voltar
        self.pagina_principal.page.update()


class ControleVisualizacao:
    def __init__(self, visualizacoes: list) -> None:
        self.visualizacoes = visualizacoes

    def __getitem__(self, indice: int) -> ft.Control:
        return self.visualizacoes[indice]
