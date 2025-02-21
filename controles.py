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
            preco_cadastrado: str,
            preco_compra: float,
            quantidade: str,
            data_operacao: str,
            marca: str,
            menor_preco: float
        ) -> None:
        preco_operacao = self.calcular_preco_operacao(preco_compra, quantidade)
        saving = self.calcular_saving(preco_cadastrado, quantidade, preco_operacao)
        await self.bd.execute(
            q6.criar_log,
            (id_produto, id_fornecedor, preco_compra, quantidade, preco_operacao, data_operacao, marca, saving, menor_preco)
        )

    async def criar_log_item_variavel(
        self,
        nome: str,
        marca: str,
        id_fornecedor: int,
        preco: float,
        medida: str,
        quantidade: str,
        categoria: str,
        data: str
    ) -> None:
        preco_operacao = self.calcular_preco_operacao(preco, quantidade)
        await self.bd.execute(
            q6.criar_log_item_variavel,
            (id_fornecedor, nome, medida, preco, quantidade, categoria, marca, data, preco_operacao)
        )

    def calcular_preco_operacao(self, preco: float, quantidade: str) -> float:
        total = preco * float(quantidade)
        return round(total, 2)
    
    def calcular_saving(self, preco_cadastrado: float, quantidade: str, preco_operacao: float) -> float:
        total_com_preco_cadastrado = float(preco_cadastrado) * float(quantidade)
        total = total_com_preco_cadastrado - preco_operacao
        return round(total, 2)


class ControleLog:
    def __init__(self, id_log: int, visualizacao: ft.Control) -> None:
        self.id_log = id_log
        self.visualizacao = visualizacao
        self.bd = BancoDeDados("db_app6.db")

    async def apagar_log_compra(self) -> None:
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
            relacao_id: int,
            fornecedor: str,
            preco_cadastrado: str,
            preco_compra: str,
            quantidade: str,
            marca: str,
            data: str,
            menor_preco: float
        ) -> None:
        if all([quantidade, fornecedor, marca, preco_cadastrado, preco_compra, data]):
            try:
                quantidade, preco_compra, data_formatada = self.formatar_valores(quantidade, preco_compra, data)
                aumentou = await self.verificar_aumento_preco(relacao_id, preco_cadastrado, preco_compra)
                if aumentou:
                    self.visualizacao.dialogo.generico(
                        ft.Icons.INFO_OUTLINE_ROUNDED,
                        "O preço desse produto aumentou\ne será atualizado automaticamente."
                    )
                    await asyncio.sleep(4)
                    self.visualizacao.dialogo.limpar()
                    
                    if menor_preco == preco_cadastrado:
                        menor_preco = preco_compra

                    preco_cadastrado = preco_compra

                self.visualizacao.dialogo.salvando()
                await LogProduto().criar_log(
                    self.modelo.id, fornecedor, preco_cadastrado, preco_compra, quantidade, data_formatada, marca, menor_preco
                )
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

    async def salvar_log_compra_item_variavel(
            self,
            nome: str,
            marca: str,
            id_fornecedor: int,
            preco: float,
            medida: str,
            quantidade: str,
            categoria: str,
            data: str
        ) -> None:
        if all([nome, id_fornecedor, preco, medida, quantidade, categoria, data]):
            if not marca:
                marca = "-"
            try:
                quantidade, preco, data = self.formatar_valores(quantidade, preco, data)

                self.visualizacao.dialogo.salvando()
                await LogProduto().criar_log_item_variavel(
                    nome, marca, id_fornecedor, preco, medida, quantidade, categoria, data
                )
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

    async def verificar_aumento_preco(self, relacao_id: int, preco_cadastrado: str, preco_compra: str):
        if preco_compra > preco_cadastrado:
            await self.bd.execute(q6.atualizar_preco_relacao, (preco_compra, relacao_id))
            return True
        return False

    def formatar_valores(self, quantidade, preco_compra, data):
        _quantidade = self.formatar_valor(quantidade)
        _preco_compra = float(self.formatar_valor(preco_compra))
        _data_formatada = datetime.strptime(data, "%d-%m-%Y").strftime('%Y-%m-%d')
        return _quantidade, _preco_compra, _data_formatada

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
    
    async def inserir_valores_infos(
            self,
            armazenamento: str,
            dias: int,
            qtd_media: int,
            freq: int,
            preco_medio: int,
            perdas: int,
            path: str
        ) -> None:
        armazenamento = self.formatar_valor(armazenamento)
        variaveis = [armazenamento, dias, qtd_media, freq, preco_medio, perdas, path]
        await self.bd.execute(
            q6.inserir_valores_infos, (
                self.modelo.id, *variaveis, *variaveis
            )
        )

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
        self.atualizar_grade_itens = False

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
