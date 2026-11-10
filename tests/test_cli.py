"""Testes da interface de linha de comando (CLI)."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from rateio_condominio_fracoes.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_versao(self):
        f = io.StringIO()
        with patch("sys.argv", ["rateio-condominio-fracoes", "versao"]):
            with redirect_stdout(f):
                codigo = main()
        self.assertEqual(codigo, 0)
        self.assertIn("rateio-condominio-fracoes 1.0.0", f.getvalue())

    def test_cli_exemplo_stdout(self):
        f = io.StringIO()
        with patch("sys.argv", ["rateio-condominio-fracoes", "exemplo"]):
            with redirect_stdout(f):
                codigo = main()
        self.assertEqual(codigo, 0)
        dados = json.loads(f.getvalue())
        self.assertIn("condominio", dados)
        self.assertIn("unidades", dados)

    def test_cli_exemplo_arquivo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arq_saida = Path(tmpdir) / "exemplo.json"
            with patch("sys.argv", ["rateio-condominio-fracoes", "exemplo", "--saida", str(arq_saida)]):
                with redirect_stdout(io.StringIO()):
                    codigo = main()
            self.assertEqual(codigo, 0)
            self.assertTrue(arq_saida.exists())
            dados = json.loads(arq_saida.read_text(encoding="utf-8"))
            self.assertIn("unidades", dados)

    def test_cli_verificar_sucesso(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arq_in = Path(tmpdir) / "in.json"
            # Cria exemplo primeiro
            with patch("sys.argv", ["rateio-condominio-fracoes", "exemplo", "-o", str(arq_in)]):
                main()

            f = io.StringIO()
            with patch("sys.argv", ["rateio-condominio-fracoes", "verificar", "-i", str(arq_in)]):
                with redirect_stdout(f):
                    codigo = main()
            self.assertEqual(codigo, 0)
            self.assertIn("Entrada válida e consistente", f.getvalue())

    def test_cli_verificar_arquivo_inexistente(self):
        f_err = io.StringIO()
        with patch("sys.argv", ["rateio-condominio-fracoes", "verificar", "-i", "/tmp/inexistente_12345.json"]):
            with redirect_stderr(f_err):
                codigo = main()
        self.assertEqual(codigo, 1)

    def test_cli_resumo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arq_in = Path(tmpdir) / "in.json"
            with patch("sys.argv", ["rateio-condominio-fracoes", "exemplo", "-o", str(arq_in)]):
                main()

            f = io.StringIO()
            with patch("sys.argv", ["rateio-condominio-fracoes", "resumo", "-i", str(arq_in)]):
                with redirect_stdout(f):
                    codigo = main()
            self.assertEqual(codigo, 0)
            self.assertIn("Demonstrativo de Rateio Condominial", f.getvalue())

    def test_cli_processar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arq_in = Path(tmpdir) / "in.json"
            with patch("sys.argv", ["rateio-condominio-fracoes", "exemplo", "-o", str(arq_in)]):
                main()

            dir_saida = Path(tmpdir) / "saida"
            zip_saida = Path(tmpdir) / "fechamento.zip"

            with patch("sys.argv", [
                "rateio-condominio-fracoes", "processar",
                "-i", str(arq_in),
                "-d", str(dir_saida),
                "-z", str(zip_saida),
            ]):
                with redirect_stdout(io.StringIO()):
                    codigo = main()

            self.assertEqual(codigo, 0)
            self.assertTrue(zip_saida.exists())
            self.assertTrue((dir_saida / "resumo-unidades.csv").exists())
            self.assertTrue((dir_saida / "despesas-detalhadas.csv").exists())
            self.assertTrue((dir_saida / "medicoes-hidrometros.csv").exists())
            self.assertTrue((dir_saida / "relatorio-fechamento.md").exists())
            self.assertTrue((dir_saida / "painel-rateio.svg").exists())


if __name__ == "__main__":
    unittest.main()
