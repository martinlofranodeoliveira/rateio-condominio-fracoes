"""Testes unitários e matemáticos do motor de rateio condominial."""

import unittest
from fractions import Fraction

from rateio_condominio_fracoes.core import (
    distribuir_por_maiores_restos,
    formatar_fracao_percentual,
    formatar_moeda_centavos,
    validar_e_processar_rateio,
)
from rateio_condominio_fracoes.errors import (
    ERR_DESPESA_DUPLICADA,
    ERR_DESPESA_VAZIA,
    ERR_FATURA_CONSUMO_INSUFICIENTE,
    ERR_FRACAO_INVALIDA,
    ERR_FRACAO_SOMA_INVALIDA,
    ERR_FUNDO_INVALIDO,
    ERR_LEITURA_INCONSISTENTE,
    ERR_UNIDADE_DUPLICADA,
    ERR_UNIDADE_VAZIA,
    ERR_VALOR_INVALIDO,
    ErroValidacaoEntrada,
)


class TestCore(unittest.TestCase):
    def test_formatar_moeda_centavos_positivo(self):
        self.assertEqual(formatar_moeda_centavos(0), "R$ 0,00")
        self.assertEqual(formatar_moeda_centavos(5), "R$ 0,05")
        self.assertEqual(formatar_moeda_centavos(99), "R$ 0,99")
        self.assertEqual(formatar_moeda_centavos(100), "R$ 1,00")
        self.assertEqual(formatar_moeda_centavos(15023), "R$ 150,23")
        self.assertEqual(formatar_moeda_centavos(123456789), "R$ 1.234.567,89")

    def test_formatar_moeda_centavos_negativo(self):
        self.assertEqual(formatar_moeda_centavos(-50), "-R$ 0,50")
        self.assertEqual(formatar_moeda_centavos(-150000), "-R$ 1.500,00")

    def test_formatar_fracao_percentual(self):
        self.assertEqual(formatar_fracao_percentual(Fraction(1, 2)), "50,0000%")
        self.assertEqual(formatar_fracao_percentual(Fraction(1, 4)), "25,0000%")
        self.assertEqual(formatar_fracao_percentual(Fraction(45231, 1000000)), "4,5231%")
        self.assertEqual(formatar_fracao_percentual(Fraction(1, 3), casas=2), "33,33%")
        self.assertEqual(formatar_fracao_percentual(Fraction(2, 3), casas=2), "66,67%")

    def test_distribuicao_maiores_restos_exata(self):
        # 100 centavos entre 3 unidades de frações iguais (1/3 cada)
        # 100 / 3 = 33 com resto 1
        # Primeira unidade pelo critério lexicográfico ganha 34, outras 33
        pesos = [("U1", Fraction(1, 3)), ("U2", Fraction(1, 3)), ("U3", Fraction(1, 3))]
        res = distribuir_por_maiores_restos(100, pesos)
        self.assertEqual(sum(res.values()), 100)
        self.assertEqual(res["U1"], 34)
        self.assertEqual(res["U2"], 33)
        self.assertEqual(res["U3"], 33)

    def test_distribuicao_maiores_restos_com_pesos_diferentes(self):
        # Total: 1000 centavos
        # Pesos: U1 = 1/2 (500), U2 = 3/10 (300), U3 = 2/10 (200)
        pesos = [("U1", Fraction(1, 2)), ("U2", Fraction(3, 10)), ("U3", Fraction(2, 10))]
        res = distribuir_por_maiores_restos(1000, pesos)
        self.assertEqual(res["U1"], 500)
        self.assertEqual(res["U2"], 300)
        self.assertEqual(res["U3"], 200)
        self.assertEqual(sum(res.values()), 1000)

    def test_distribuicao_maiores_restos_zero_centavos(self):
        pesos = [("U1", Fraction(1, 2)), ("U2", Fraction(1, 2))]
        res = distribuir_por_maiores_restos(0, pesos)
        self.assertEqual(res, {"U1": 0, "U2": 0})

    def test_distribuicao_maiores_restos_erro_negativo(self):
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            distribuir_por_maiores_restos(-10, [("U1", Fraction(1, 1))])
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_distribuicao_maiores_restos_erro_sem_unidades(self):
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            distribuir_por_maiores_restos(100, [])
        self.assertEqual(ctx.exception.codigo, ERR_UNIDADE_VAZIA)

    def test_distribuicao_maiores_restos_erro_peso_zero(self):
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            distribuir_por_maiores_restos(100, [("U1", Fraction(0, 1))])
        self.assertEqual(ctx.exception.codigo, ERR_FRACAO_INVALIDA)

    def test_validacao_processamento_sucesso_completo(self):
        entrada = {
            "condominio": {"nome": "Residencial Teste", "competencia": "2026-11"},
            "unidades": [
                {"id": "U101", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
                {"id": "U102", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
            ],
            "despesas_ordinarias": [
                {"id": "D1", "descricao": "Portaria", "categoria": "pessoal", "valor_centavos": 100000},
                {"id": "D2", "descricao": "Luz", "categoria": "consumo", "valor_centavos": 50001},
            ],
            "fundos": [
                {"id": "FR", "descricao": "Reserva", "tipo": "percentual_ordinarias", "percentual_numerador": 10, "percentual_denominador": 100},
                {"id": "FO", "descricao": "Obras", "tipo": "valor_fixo_global", "valor_centavos": 20000},
            ],
            "medicoes": [
                {
                    "servico": "agua",
                    "unidade_medida": "m3",
                    "valor_fatura_concessionaria_centavos": 30000,
                    "consumo_fatura": 30,
                    "leituras": [
                        {"unidade_id": "U101", "leitura_anterior": 10, "leitura_atual": 20},
                        {"unidade_id": "U102", "leitura_anterior": 5, "leitura_atual": 10},
                    ],
                }
            ],
        }
        res = validar_e_processar_rateio(entrada)
        b = res.balancete
        self.assertTrue(b.conciliado)
        self.assertEqual(b.diferenca_fechamento_centavos, 0)
        self.assertEqual(b.total_unidades, 2)
        self.assertEqual(b.total_despesas_ordinarias_centavos, 150001)

        # Ordinárias: 150001 distribuído meio a meio
        # 150001 / 2 = 75000 resto 1. U101 ganha 75001, U102 ganha 75000
        self.assertEqual(res.unidades["U101"].cota_ordinaria_centavos, 75001)
        self.assertEqual(res.unidades["U102"].cota_ordinaria_centavos, 75000)

        # Fundo reserva: 10% de 150001 = 15000 centavos (meio para cima)
        # Distribuído meio a meio: 7500 para cada
        self.assertEqual(res.unidades["U101"].fundos_centavos["FR"], 7500)
        self.assertEqual(res.unidades["U102"].fundos_centavos["FR"], 7500)

        # Fundo obras: 20000 fixo = 10000 para cada
        self.assertEqual(res.unidades["U101"].fundos_centavos["FO"], 10000)
        self.assertEqual(res.unidades["U102"].fundos_centavos["FO"], 10000)

        # Água: consumo fatura 30 m³, individual: U101=10, U102=5. Área comum = 30 - 15 = 15 m³
        # Peso U101 = 10 + 15 * 0.5 = 17.5 m³
        # Peso U102 = 5 + 15 * 0.5 = 12.5 m³
        # Proporção: U101 = 17.5/30 = 7/12, U102 = 12.5/30 = 5/12
        # Fatura = 30000. U101 = 30000 * 7/12 = 17500. U102 = 30000 * 5/12 = 12500
        self.assertEqual(res.unidades["U101"].medicoes_detalhe["agua"]["total_centavos"], 17500)
        self.assertEqual(res.unidades["U102"].medicoes_detalhe["agua"]["total_centavos"], 12500)

        # Total individual:
        # U101: 75001 + 17500 (fundos) + 17500 (agua) = 110001
        # U102: 75000 + 17500 (fundos) + 12500 (agua) = 105000
        # Soma = 215001
        self.assertEqual(res.unidades["U101"].total_geral_centavos, 110001)
        self.assertEqual(res.unidades["U102"].total_geral_centavos, 105000)
        self.assertEqual(b.total_geral_arrecadado_centavos, 215001)
        self.assertEqual(b.total_geral_despesas_centavos, 215001)

    def test_rejeicao_soma_fracao_diferente_de_um(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 40, "fracao_ideal_denominador": 100},
                {"id": "U2", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
            ]
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_FRACAO_SOMA_INVALIDA)

    def test_rejeicao_unidade_duplicada(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
                {"id": "U1", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
            ]
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_UNIDADE_DUPLICADA)

    def test_rejeicao_unidade_sem_id(self):
        entrada = {
            "unidades": [
                {"id": "", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
            ]
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_UNIDADE_VAZIA)

    def test_rejeicao_despesa_duplicada(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "despesas_ordinarias": [
                {"id": "D1", "valor_centavos": 100},
                {"id": "D1", "valor_centavos": 200},
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_DESPESA_DUPLICADA)

    def test_rejeicao_despesa_valor_negativo(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "despesas_ordinarias": [
                {"id": "D1", "valor_centavos": -50},
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_VALOR_INVALIDO)

    def test_rejeicao_leitura_atual_menor_que_anterior(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 100,
                    "consumo_fatura": 50,
                    "leituras": [{"unidade_id": "U1", "leitura_anterior": 100, "leitura_atual": 90}],
                }
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_LEITURA_INCONSISTENTE)

    def test_rejeicao_fatura_com_volume_menor_que_leituras(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 100,
                    "consumo_fatura": 5,
                    "leituras": [{"unidade_id": "U1", "leitura_anterior": 0, "leitura_atual": 10}],
                }
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_FATURA_CONSUMO_INSUFICIENTE)

    def test_fundo_cota_fixa_por_unidade(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
            ],
            "fundos": [
                {"id": "TX_EXTRA", "tipo": "cota_fixa_por_unidade", "valor_por_unidade_centavos": 5000},
            ],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.unidades["U1"].fundos_centavos["TX_EXTRA"], 5000)
        self.assertEqual(res.unidades["U2"].fundos_centavos["TX_EXTRA"], 5000)
        self.assertEqual(res.balancete.total_fundos_centavos, 10000)

    def test_isencao_de_fundo_obras(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2, "isenta_fundo_obras": True},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2, "isenta_fundo_obras": False},
            ],
            "fundos": [
                {"id": "FUNDO-OBRAS", "tipo": "valor_fixo_global", "valor_centavos": 10000},
            ],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.unidades["U1"].fundos_centavos["FUNDO-OBRAS"], 0)
        self.assertEqual(res.unidades["U2"].fundos_centavos["FUNDO-OBRAS"], 10000)

    def test_unidade_unica_recebe_cem_por_cento(self):
        entrada = {
            "unidades": [{"id": "CASA-UNICA", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "despesas_ordinarias": [{"id": "D1", "valor_centavos": 99999}],
            "fundos": [{"id": "F1", "tipo": "valor_fixo_global", "valor_centavos": 11111}],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 22222,
                    "consumo_fatura": 50,
                    "leituras": [{"unidade_id": "CASA-UNICA", "leitura_anterior": 10, "leitura_atual": 60}],
                }
            ],
        }
        res = validar_e_processar_rateio(entrada)
        u = res.unidades["CASA-UNICA"]
        self.assertEqual(u.cota_ordinaria_centavos, 99999)
        self.assertEqual(u.total_fundos_centavos, 11111)
        self.assertEqual(u.medicoes_detalhe["agua"]["total_centavos"], 22222)
        self.assertEqual(u.total_geral_centavos, 99999 + 11111 + 22222)
        self.assertTrue(res.balancete.conciliado)

    def test_despesas_zeradas(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
            ],
            "despesas_ordinarias": [],
            "fundos": [],
            "medicoes": [],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.balancete.total_geral_arrecadado_centavos, 0)
        self.assertTrue(res.balancete.conciliado)

    def test_medicao_consumo_zero_com_tarifa_minima_fatura(self):
        # Nenhuma unidade consumiu nada (ex: prédio recém entregue), mas a concessionária cobrou taxa mínima fixa de R$ 150,00
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
            ],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 15000,
                    "consumo_fatura": 0,
                    "leituras": [
                        {"unidade_id": "U1", "leitura_anterior": 100, "leitura_atual": 100},
                        {"unidade_id": "U2", "leitura_anterior": 50, "leitura_atual": 50},
                    ],
                }
            ],
        }
        res = validar_e_processar_rateio(entrada)
        # Taxa mínima dividida meio a meio pelas frações ideais
        self.assertEqual(res.unidades["U1"].medicoes_detalhe["agua"]["total_centavos"], 7500)
        self.assertEqual(res.unidades["U2"].medicoes_detalhe["agua"]["total_centavos"], 7500)
        self.assertEqual(res.balancete.total_medicoes_centavos, 15000)

    def test_escala_cem_unidades_conservacao_estrita(self):
        n = 100
        unidades = [
            {"id": f"APTO-{i:03d}", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": n}
            for i in range(1, n + 1)
        ]
        # 333.333 centavos não é divisível por 100 (3333 por unidade, sobram 33 centavos)
        # O algoritmo dos maiores restos deve distribuir exatamente 1 centavo a mais para 33 unidades
        entrada = {
            "unidades": unidades,
            "despesas_ordinarias": [{"id": "D1", "valor_centavos": 333333}],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.balancete.total_geral_arrecadado_centavos, 333333)
        self.assertTrue(res.balancete.conciliado)
        valores = [u.cota_ordinaria_centavos for u in res.unidades.values()]
        self.assertEqual(valores.count(3334), 33)
        self.assertEqual(valores.count(3333), 67)

    def test_fundo_com_isencao_reserva(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2, "isenta_fundo_reserva": True},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2, "isenta_fundo_reserva": False},
            ],
            "despesas_ordinarias": [{"id": "D1", "valor_centavos": 20000}],
            "fundos": [
                {"id": "FUNDO-RESERVA", "tipo": "percentual_ordinarias", "percentual_numerador": 10, "percentual_denominador": 100},
            ],
        }
        res = validar_e_processar_rateio(entrada)
        # Total fundo = 10% de 20000 = 2000. U1 é isenta de reserva, logo U2 arca com os 2000 elegíveis
        self.assertEqual(res.unidades["U1"].fundos_centavos["FUNDO-RESERVA"], 0)
        self.assertEqual(res.unidades["U2"].fundos_centavos["FUNDO-RESERVA"], 2000)

    def test_multiplas_despesas_e_valores_grandes(self):
        # 1 bilhão de centavos (R$ 10.000.000,00)
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 3},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 3},
                {"id": "U3", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 3},
            ],
            "despesas_ordinarias": [
                {"id": "D1", "valor_centavos": 500000000},
                {"id": "D2", "valor_centavos": 500000001},
            ],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.balancete.total_geral_despesas_centavos, 1000000001)
        self.assertEqual(res.balancete.total_geral_arrecadado_centavos, 1000000001)
        self.assertTrue(res.balancete.conciliado)

    def test_leituras_com_unidades_sem_medicao_assumem_zero(self):
        entrada = {
            "unidades": [
                {"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
                {"id": "U2", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
            ],
            "medicoes": [
                {
                    "servico": "gas",
                    "valor_fatura_concessionaria_centavos": 1000,
                    "consumo_fatura": 10,
                    "leituras": [{"unidade_id": "U1", "leitura_anterior": 0, "leitura_atual": 10}],
                }
            ],
        }
        res = validar_e_processar_rateio(entrada)
        self.assertEqual(res.unidades["U2"].medicoes_detalhe["gas"]["consumo"], 0)
        self.assertTrue(res.balancete.conciliado)

    def test_rejeicao_leitura_com_unidade_nao_cadastrada(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 100,
                    "consumo_fatura": 10,
                    "leituras": [{"unidade_id": "FANTASMA", "leitura_anterior": 0, "leitura_atual": 10}],
                }
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_UNIDADE_VAZIA)

    def test_rejeicao_leitura_duplicada_para_mesma_unidade(self):
        entrada = {
            "unidades": [{"id": "U1", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 1}],
            "medicoes": [
                {
                    "servico": "agua",
                    "valor_fatura_concessionaria_centavos": 100,
                    "consumo_fatura": 20,
                    "leituras": [
                        {"unidade_id": "U1", "leitura_anterior": 0, "leitura_atual": 10},
                        {"unidade_id": "U1", "leitura_anterior": 10, "leitura_atual": 20},
                    ],
                }
            ],
        }
        with self.assertRaises(ErroValidacaoEntrada) as ctx:
            validar_e_processar_rateio(entrada)
        self.assertEqual(ctx.exception.codigo, ERR_UNIDADE_DUPLICADA)


if __name__ == "__main__":
    unittest.main()
