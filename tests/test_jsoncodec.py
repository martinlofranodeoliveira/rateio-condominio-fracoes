"""Testes do codec JSON estrito e canônico."""

import unittest

from rateio_condominio_fracoes.errors import (
    ERR_JSON_BOM_PROIBIDO,
    ERR_JSON_CHAVE_DUPLICADA,
    ERR_JSON_FLOAT_PROIBIDO,
    ERR_JSON_INVALIDO,
    ERR_JSON_PROFUNDIDADE_EXCEDIDA,
    ERR_JSON_TAMANHO_EXCEDIDO,
    ErroCodificacaoJSON,
)
from rateio_condominio_fracoes.jsoncodec import (
    codificar_json_canonico,
    decodificar_json_estrito,
)


class TestJsonCodec(unittest.TestCase):
    def test_decodificacao_valida_bytes(self):
        dados = b'{"nome": "Condominio", "centavos": 150000, "itens": [1, 2, 3]}'
        res = decodificar_json_estrito(dados)
        self.assertEqual(res["nome"], "Condominio")
        self.assertEqual(res["centavos"], 150000)
        self.assertEqual(res["itens"], [1, 2, 3])

    def test_decodificacao_valida_str(self):
        dados = '{"ativo": true, "taxa": 5}'
        res = decodificar_json_estrito(dados)
        self.assertTrue(res["ativo"])
        self.assertEqual(res["taxa"], 5)

    def test_rejeicao_float(self):
        dados = b'{"valor": 12.34}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_FLOAT_PROIBIDO)

    def test_rejeicao_float_em_lista(self):
        dados = b'{"valores": [10, 20, 30.5]}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_FLOAT_PROIBIDO)

    def test_rejeicao_bom_bytes(self):
        dados = b'\xef\xbb\xbf{"teste": 1}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_BOM_PROIBIDO)

    def test_rejeicao_bom_str(self):
        dados = '\ufeff{"teste": 1}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_BOM_PROIBIDO)

    def test_rejeicao_chave_duplicada(self):
        dados = b'{"chave": 1, "chave": 2}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_CHAVE_DUPLICADA)

    def test_rejeicao_profundidade_excessiva(self):
        profundo = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        # Testa limite customizado ou normal
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            # Cria 35 níveis de aninhamento
            json_profundo = '{"n":' * 35 + '1' + '}' * 35
            decodificar_json_estrito(json_profundo.encode("utf-8"))
        self.assertEqual(ctx.exception.codigo, ERR_JSON_PROFUNDIDADE_EXCEDIDA)

    def test_rejeicao_tamanho_excedido(self):
        dados = b'{"a": 1}'
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados, limite_bytes=5)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_TAMANHO_EXCEDIDO)

    def test_rejeicao_sintaxe_invalida(self):
        dados = b'{"invalido": '
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(dados)
        self.assertEqual(ctx.exception.codigo, ERR_JSON_INVALIDO)

    def test_rejeicao_tipo_nao_bytes_nem_str(self):
        with self.assertRaises(ErroCodificacaoJSON) as ctx:
            decodificar_json_estrito(12345)  # type: ignore
        self.assertEqual(ctx.exception.codigo, ERR_JSON_INVALIDO)

    def test_codificacao_canonica_estavel(self):
        d1 = {"z": 1, "a": 2, "m": [3, 2, 1]}
        d2 = {"a": 2, "m": [3, 2, 1], "z": 1}
        s1 = codificar_json_canonico(d1)
        s2 = codificar_json_canonico(d2)
        self.assertEqual(s1, s2)
        self.assertTrue(s1.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
