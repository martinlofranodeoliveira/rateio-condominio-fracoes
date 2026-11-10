"""Testes do módulo de relatórios, CSV, Markdown, SVG e ZIP determinístico."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from rateio_condominio_fracoes.core import validar_e_processar_rateio
from rateio_condominio_fracoes.errors import ERR_ARQUIVO_EXISTENTE, ErroExecucao
from rateio_condominio_fracoes.reports import (
    gerar_csv_despesas_detalhadas,
    gerar_csv_medicoes_hidrometros,
    gerar_csv_resumo_unidades,
    gerar_painel_svg,
    gerar_relatorio_markdown,
    publicar_pacote_zip,
    sanitizar_campo_csv,
)


class TestReports(unittest.TestCase):
    def setUp(self):
        self.dados_base = {
            "condominio": {"nome": "Condomínio Alvorada", "competencia": "2026-11"},
            "unidades": [
                {"id": "U101", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
                {"id": "=MALICIOSA", "fracao_ideal_numerador": 50, "fracao_ideal_denominador": 100},
            ],
            "despesas_ordinarias": [
                {"id": "+DESP-INJETADA", "descricao": "@Formula perigosa", "categoria": "-financeiro", "valor_centavos": 10000},
            ],
            "fundos": [
                {"id": "FR", "descricao": "Fundo Reserva", "tipo": "valor_fixo_global", "valor_centavos": 2000},
            ],
            "medicoes": [
                {
                    "servico": "agua",
                    "unidade_medida": "m3",
                    "valor_fatura_concessionaria_centavos": 5000,
                    "consumo_fatura": 10,
                    "leituras": [
                        {"unidade_id": "U101", "leitura_anterior": 0, "leitura_atual": 4},
                        {"unidade_id": "=MALICIOSA", "leitura_anterior": 0, "leitura_atual": 6},
                    ],
                }
            ],
        }
        self.resultado = validar_e_processar_rateio(self.dados_base)

    def test_sanitizacao_formula_injection(self):
        self.assertEqual(sanitizar_campo_csv("=1+1"), "'=1+1")
        self.assertEqual(sanitizar_campo_csv("+SOMAR()"), "'+SOMAR()")
        self.assertEqual(sanitizar_campo_csv("-123"), "'-123")
        self.assertEqual(sanitizar_campo_csv("@cmd"), "'@cmd")
        self.assertEqual(sanitizar_campo_csv("\ttab"), "'\ttab")
        self.assertEqual(sanitizar_campo_csv("Texto normal"), "Texto normal")
        self.assertEqual(sanitizar_campo_csv(12345), "12345")

    def test_geracao_csv_resumo_unidades(self):
        csv_texto = gerar_csv_resumo_unidades(self.resultado)
        self.assertIn("unidade_id", csv_texto)
        self.assertIn("cota_ordinaria_centavos", csv_texto)
        self.assertIn("'=MALICIOSA", csv_texto)  # Sanitizado contra injeção de fórmulas!

    def test_geracao_csv_despesas_detalhadas(self):
        csv_texto = gerar_csv_despesas_detalhadas(self.resultado)
        self.assertIn("natureza", csv_texto)
        self.assertIn("'+DESP-INJETADA", csv_texto)
        self.assertIn("'@Formula perigosa", csv_texto)
        self.assertIn("'-financeiro", csv_texto)

    def test_geracao_csv_medicoes_hidrometros(self):
        csv_texto = gerar_csv_medicoes_hidrometros(self.resultado)
        self.assertIn("servico", csv_texto)
        self.assertIn("consumo_medido", csv_texto)
        self.assertIn("'=MALICIOSA", csv_texto)

    def test_geracao_relatorio_markdown(self):
        md = gerar_relatorio_markdown(self.resultado)
        self.assertIn("Demonstrativo de Rateio Condominial — Condomínio Alvorada", md)
        self.assertIn("CONCILIADO (100% EXATO)", md)
        self.assertIn("Balancete Consolidado", md)
        self.assertIn("Resumo das Unidades", md)
        self.assertIn("LOFRANO TECNOLOGIA", md)

    def test_geracao_painel_svg(self):
        svg = gerar_painel_svg(self.resultado)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))
        self.assertIn('width="1440"', svg)
        self.assertIn('height="900"', svg)
        self.assertIn("Condomínio Alvorada", svg)
        self.assertIn("TOTAL RATEADO", svg)

    def test_publicar_pacote_zip_sucesso(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_zip = Path(tmpdir) / "teste.zip"
            arquivos = {
                "relatorio.txt": b"Conteudo do relatorio",
                "dados.json": b'{"ok": 1}',
            }
            publicar_pacote_zip(caminho_zip, arquivos)
            self.assertTrue(caminho_zip.exists())

            with zipfile.ZipFile(caminho_zip, "r") as zf:
                self.assertEqual(set(zf.namelist()), {"relatorio.txt", "dados.json"})
                self.assertEqual(zf.read("relatorio.txt"), b"Conteudo do relatorio")

    def test_publicar_pacote_zip_impede_sobrescrita(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho_zip = Path(tmpdir) / "existente.zip"
            caminho_zip.write_bytes(b"ja existe")

            with self.assertRaises(ErroExecucao) as ctx:
                publicar_pacote_zip(caminho_zip, {"a.txt": b"123"})
            self.assertEqual(ctx.exception.codigo, ERR_ARQUIVO_EXISTENTE)


if __name__ == "__main__":
    unittest.main()
