#!/usr/bin/env python3
"""Verificador independente para rateio-condominio-fracoes sem importar o pacote de produção."""

import argparse
import csv
import hashlib
import io
import json
import os
import sqlite3
import sys
import zipfile
from fractions import Fraction
from pathlib import Path


def verificar_pacote_zip(caminho_zip: Path) -> bool:
    print(f"=== Auditoria Independente: {caminho_zip.name} ===")

    if not caminho_zip.exists():
        print(f"[ERRO] Arquivo ZIP não encontrado: {caminho_zip}", file=sys.stderr)
        return False

    with zipfile.ZipFile(caminho_zip, "r") as zf:
        nomes = set(zf.namelist())
        arquivos_obrigatorios = {
            "entrada.json",
            "rateio.json",
            "resumo-unidades.csv",
            "despesas-detalhadas.csv",
            "medicoes-hidrometros.csv",
            "relatorio-fechamento.md",
            "painel-rateio.svg",
            "SHA256SUMS",
        }
        faltantes = arquivos_obrigatorios - nomes
        if faltantes:
            print(f"[ERRO] Arquivos obrigatórios ausentes no ZIP: {faltantes}", file=sys.stderr)
            return False

        # 1. Conferência de SHA256SUMS
        raw_sha = zf.read("SHA256SUMS").decode("utf-8")
        for linha in raw_sha.strip().splitlines():
            partes = linha.strip().split(maxsplit=1)
            if len(partes) != 2:
                continue
            hash_esperado, nome_arq = partes
            if nome_arq == "SHA256SUMS":
                continue
            conteudo = zf.read(nome_arq)
            hash_real = hashlib.sha256(conteudo).hexdigest()
            if hash_esperado != hash_real:
                print(f"[ERRO] Hash SHA-256 divergente para '{nome_arq}': esperado {hash_esperado}, obtido {hash_real}", file=sys.stderr)
                return False
        print("  ✓ Integridade criptográfica SHA-256 verificada com sucesso em todos os artefatos.")

        # 2. Carregamento da entrada original e cálculo independente das frações
        entrada = json.loads(zf.read("entrada.json").decode("utf-8"))
        unidades = entrada.get("unidades", [])
        soma_fracoes = Fraction(0, 1)
        for u in unidades:
            num = u["fracao_ideal_numerador"]
            den = u["fracao_ideal_denominador"]
            soma_fracoes += Fraction(num, den)

        if soma_fracoes != Fraction(1, 1):
            print(f"[ERRO] Soma das frações ideais na entrada divergente de 1: {soma_fracoes}", file=sys.stderr)
            return False
        print(f"  ✓ Frações ideais da entrada somam exatamente 1/1 ({len(unidades)} unidades).")

        # 3. Auditoria relacional via SQLite em memória a partir dos CSVs
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # Tabela resumo_unidades
        cursor.execute("""
            CREATE TABLE resumo_unidades (
                unidade_id TEXT PRIMARY KEY,
                fracao_ideal TEXT,
                percentual TEXT,
                cota_ordinaria_centavos INTEGER,
                cota_ordinaria_formatada TEXT,
                total_fundos_centavos INTEGER,
                total_fundos_formatado TEXT,
                total_medicoes_centavos INTEGER,
                total_medicoes_formatado TEXT,
                total_geral_centavos INTEGER,
                total_geral_formatado TEXT
            )
        """)

        csv_unidades_texto = zf.read("resumo-unidades.csv").decode("utf-8")
        leitor = csv.reader(io.StringIO(csv_unidades_texto))
        cabecalho = next(leitor)
        idx_uid = cabecalho.index("unidade_id")
        idx_frac = cabecalho.index("fracao_ideal")
        idx_pct = cabecalho.index("percentual")
        idx_ord = cabecalho.index("cota_ordinaria_centavos")
        idx_ord_fmt = cabecalho.index("cota_ordinaria_formatada")
        idx_tot_fundo = cabecalho.index("total_fundos_centavos")
        idx_tot_fundo_fmt = cabecalho.index("total_fundos_formatado")
        idx_tot_med = cabecalho.index("total_medicoes_centavos")
        idx_tot_med_fmt = cabecalho.index("total_medicoes_formatado")
        idx_tot_geral = cabecalho.index("total_geral_centavos")
        idx_tot_geral_fmt = cabecalho.index("total_geral_formatado")

        for row in leitor:
            cursor.execute("""
                INSERT INTO resumo_unidades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row[idx_uid], row[idx_frac], row[idx_pct],
                int(row[idx_ord]), row[idx_ord_fmt],
                int(row[idx_tot_fundo]), row[idx_tot_fundo_fmt],
                int(row[idx_tot_med]), row[idx_tot_med_fmt],
                int(row[idx_tot_geral]), row[idx_tot_geral_fmt],
            ))

        # Tabela despesas
        cursor.execute("""
            CREATE TABLE despesas (
                natureza TEXT,
                id TEXT,
                descricao TEXT,
                categoria_ou_tipo TEXT,
                valor_centavos INTEGER,
                valor_formatado TEXT
            )
        """)
        csv_despesas_texto = zf.read("despesas-detalhadas.csv").decode("utf-8")
        leitor_d = csv.reader(io.StringIO(csv_despesas_texto))
        next(leitor_d)
        for row in leitor_d:
            cursor.execute("INSERT INTO despesas VALUES (?, ?, ?, ?, ?, ?)", (
                row[0], row[1], row[2], row[3], int(row[4]), row[5]
            ))

        # Tabela medicoes
        cursor.execute("""
            CREATE TABLE medicoes (
                servico TEXT,
                unidade_id TEXT,
                leitura_anterior INTEGER,
                leitura_atual INTEGER,
                consumo_medido INTEGER,
                unidade_medida TEXT,
                valor_individual_centavos INTEGER,
                valor_area_comum_centavos INTEGER,
                total_servico_centavos INTEGER,
                total_servico_formatado TEXT
            )
        """)
        csv_medicoes_texto = zf.read("medicoes-hidrometros.csv").decode("utf-8")
        leitor_m = csv.reader(io.StringIO(csv_medicoes_texto))
        next(leitor_m)
        for row in leitor_m:
            cursor.execute("INSERT INTO medicoes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                row[0], row[1], int(row[2]), int(row[3]), int(row[4]),
                row[5], int(row[6]), int(row[7]), int(row[8]), row[9]
            ))

        conn.commit()

        # 4. Verificação de Conservação Matemática Estrita
        cursor.execute("SELECT SUM(cota_ordinaria_centavos), SUM(total_fundos_centavos), SUM(total_medicoes_centavos), SUM(total_geral_centavos) FROM resumo_unidades")
        soma_ord, soma_fundos, soma_med, soma_geral_unidades = cursor.fetchone()

        cursor.execute("SELECT SUM(valor_centavos) FROM despesas WHERE natureza = 'ORDINARIA'")
        total_desp_ordinarias = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(valor_centavos) FROM despesas WHERE natureza = 'FUNDO'")
        total_desp_fundos = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(total_servico_centavos) FROM medicoes")
        total_medicoes_tabela = cursor.fetchone()[0] or 0

        print(f"  • Total Ordinárias: Cobrado = {soma_ord} centavos | Despesas = {total_desp_ordinarias} centavos")
        if soma_ord != total_desp_ordinarias:
            print(f"[ERRO] Conservação de despesas ordinárias violada: {soma_ord} != {total_desp_ordinarias}", file=sys.stderr)
            return False

        print(f"  • Total Fundos: Cobrado = {soma_fundos} centavos | Despesas = {total_desp_fundos} centavos")
        if soma_fundos != total_desp_fundos:
            print(f"[ERRO] Conservação de fundos violada: {soma_fundos} != {total_desp_fundos}", file=sys.stderr)
            return False

        print(f"  • Total Medições: Cobrado = {soma_med} centavos | Medições = {total_medicoes_tabela} centavos")
        if soma_med != total_medicoes_tabela:
            print(f"[ERRO] Conservação de medições violada: {soma_med} != {total_medicoes_tabela}", file=sys.stderr)
            return False

        total_despesas_geral = total_desp_ordinarias + total_desp_fundos + total_medicoes_tabela
        if soma_geral_unidades != total_despesas_geral:
            print(f"[ERRO] Fechamento global divergente: {soma_geral_unidades} != {total_despesas_geral}", file=sys.stderr)
            return False

        # Verifica consistência interna de cada linha
        cursor.execute("""
            SELECT unidade_id, cota_ordinaria_centavos + total_fundos_centavos + total_medicoes_centavos, total_geral_centavos
            FROM resumo_unidades
            WHERE (cota_ordinaria_centavos + total_fundos_centavos + total_medicoes_centavos) != total_geral_centavos
        """)
        linhas_divergentes = cursor.fetchall()
        if linhas_divergentes:
            print(f"[ERRO] Linhas com soma interna inconsistente: {linhas_divergentes}", file=sys.stderr)
            return False

        print(f"  ✓ Fechamento exato confirmado: {soma_geral_unidades} centavos auditados e validados.")
        print("=== Auditoria Independente APROVADA com 100% de sucesso! ===")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditor independente de rateio condominial.")
    parser.add_argument("arquivo_zip", nargs="?", default="", help="Caminho do pacote ZIP a ser auditado (opcional)")
    args = parser.parse_args()

    if args.arquivo_zip:
        sucesso = verificar_pacote_zip(Path(args.arquivo_zip))
        return 0 if sucesso else 1

    # Se nenhum argumento for fornecido, executa ciclo completo autônomo usando subprocess
    import tempfile
    import subprocess
    print("Nenhum arquivo ZIP fornecido. Gerando pacote de demonstração para auto-auditoria...")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "exemplo-fechamento.zip"
        cmd = [
            sys.executable,
            "-m",
            "rateio_condominio_fracoes",
            "processar",
            "-i",
            "exemplos/condominio_edificio_horizonte.json",
            "-z",
            str(zip_path),
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[ERRO] Falha ao gerar pacote de demonstração: {res.stderr}", file=sys.stderr)
            return 1
        sucesso = verificar_pacote_zip(zip_path)
        return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
