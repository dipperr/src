buscar_relacao_produto_fornecedor = """
SELECT relacao.id, fornecedor.id, fornecedor.nome, relacao.preco, relacao.marca
FROM relacao_produto_fornecedor AS relacao
INNER JOIN fornecedor ON relacao.id_fornecedor = fornecedor.id
WHERE relacao.id_produto = ?;
"""

criar_log = """
INSERT INTO log_compra_produtos(id_produto, id_fornecedor, preco, quantidade, preco_operacao, data_operacao, marca, desconto)
VALUES(?, ?, ?, ?, ?, ?, ?, ?);
"""

apagar_log = "DELETE FROM log_compra_produtos WHERE id = ?;"

cadastrar_produto = "INSERT INTO produto(nome, medida, categoria) VALUES(?, ?, ?);"

criar_registro_consumo = "INSERT INTO consumo_dia(id_produto, valor, dia_semana) VALUES(?, '0', ?);"

apagar_resgistro_produto = "DELETE FROM produto WHERE id = ?;"

criar_relacao_produto_fornecedor = """
INSERT INTO relacao_produto_fornecedor(id_produto, id_fornecedor, preco, marca) VALUES(?, ?, ?, ?);
"""

obter_fornecedores = "SELECT id, nome FROM fornecedor;"

atualizar_preco_relacao = "UPDATE relacao_produto_fornecedor SET preco = ? WHERE id = ?;"

apagar_relacao_produto_fornecedor = "DELETE FROM relacao_produto_fornecedor WHERE id = ?;"

atualizar_consumo_produto = "UPDATE consumo_dia SET valor = ? WHERE id_produto = ? AND dia_semana = ?;"

obter_dados_consumo = "SELECT dia_semana, valor FROM consumo_dia WHERE id_produto = ?;"

obter_dados_infos = "SELECT armazenamento, validade FROM infos_produto WHERE produto_id = ?;"

inserir_valores_infos = """
INSERT INTO infos_produto(produto_id, armazenamento, validade)
VALUES(?, ?, ?)
ON CONFLICT(produto_id)
DO UPDATE SET armazenamento = ?, validade = ?;
"""

obter_logs = """
SELECT log.id, log.data_operacao, fornecedor.nome, log.quantidade, log.preco, log.preco_operacao, log.marca, log.desconto
FROM log_compra_produtos AS log
INNER JOIN fornecedor ON log.id_fornecedor = fornecedor.id
WHERE log.id_produto = ? AND date(log.data_operacao) BETWEEN date(?) AND date(?);
"""

obter_todos_logs = """
SELECT log.id, log.data_operacao, fornecedor.nome, log.quantidade, log.preco, log.preco_operacao, log.marca, log.desconto
FROM log_compra_produtos AS log
INNER JOIN fornecedor ON log.id_fornecedor = fornecedor.id
WHERE log.id_produto = ?;
"""

adicionar_fornecedor = """
INSERT INTO fornecedor(nome, telefone, responsavel, logradouro, numero, bairro, cep, cidade, estado)
VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?);"""

selecionar_produtos = "SELECT * FROM produto ORDER BY nome ASC;"

obter_medida_produto = "SELECT medida FROM produto WHERE id = ?;"

obter_dados_fornecedores = "SELECT * FROM fornecedor;"

obter_logs_para_dash = """
SELECT p.nome AS nome_produto, p.categoria, p.medida, l.quantidade, l.data_operacao, l.preco, l.preco_operacao
FROM log_compra_produtos AS l
INNER JOIN produto AS p ON l.id_produto = p.id
INNER JOIN fornecedor AS f ON l.id_fornecedor = f.id
WHERE date(l.data_operacao)
BETWEEN date(?) AND date(?);
"""

obter_todos_logs_para_dash = """
SELECT p.nome AS nome_produto, p.categoria, p.medida, l.quantidade, l.data_operacao, l.preco, l.preco_operacao
FROM log_compra_produtos AS l
INNER JOIN produto AS p ON l.id_produto = p.id
INNER JOIN fornecedor AS f ON l.id_fornecedor = f.id;
"""

apagar_fornecedor = "DELETE FROM fornecedor WHERE id = ?;"
