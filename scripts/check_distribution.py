#!/usr/bin/env python3
"""Verificador de distribuição (wheel e sdist) para rateio-condominio-fracoes."""

import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


def inspecionar_wheel(caminho_whl: Path) -> None:
    print(f"-> Inspecionando Wheel: {caminho_whl.name}")
    with zipfile.ZipFile(caminho_whl, "r") as zf:
        membros = zf.namelist()
        print(f"   Total de arquivos no wheel: {len(membros)}")
        arquivos_obrigatorios = [
            "rateio_condominio_fracoes/__init__.py",
            "rateio_condominio_fracoes/core.py",
            "rateio_condominio_fracoes/errors.py",
            "rateio_condominio_fracoes/jsoncodec.py",
            "rateio_condominio_fracoes/reports.py",
            "rateio_condominio_fracoes/cli.py",
            "rateio_condominio_fracoes/__main__.py",
        ]
        for arq in arquivos_obrigatorios:
            if arq not in membros:
                raise RuntimeError(f"Arquivo obrigatório ausente no wheel: {arq}")
    print("   ✓ Wheel estruturado corretamente.")


def inspecionar_sdist(caminho_sdist: Path) -> None:
    print(f"-> Inspecionando sdist: {caminho_sdist.name}")
    with tarfile.open(caminho_sdist, "r:gz") as tf:
        nomes = tf.getnames()
        print(f"   Total de arquivos no sdist: {len(nomes)}")
        raiz = nomes[0].split("/")[0]
        arquivos_esperados = [
            f"{raiz}/pyproject.toml",
            f"{raiz}/LICENSE",
            f"{raiz}/README.md",
            f"{raiz}/src/rateio_condominio_fracoes/core.py",
        ]
        for arq in arquivos_esperados:
            if arq not in nomes:
                raise RuntimeError(f"Arquivo esperado ausente no sdist: {arq}")
    print("   ✓ sdist estruturado corretamente.")


def testar_instalacao_isolada(caminho_whl: Path) -> None:
    print("-> Testando execução da CLI fora da árvore de código...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Testa chamada direta do arquivo empacotado sem PYTHONPATH
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        cmd = [
            sys.executable,
            "-c",
            f"""
import sys, zipfile, tempfile
with zipfile.ZipFile('{caminho_whl.resolve()}', 'r') as zf:
    zf.extractall('{tmpdir}')
sys.path.insert(0, '{tmpdir}')
import rateio_condominio_fracoes
print('Importado com sucesso:', rateio_condominio_fracoes.__version__)
from rateio_condominio_fracoes.core import formatar_moeda_centavos
print('Formatacao:', formatar_moeda_centavos(150000))
assert formatar_moeda_centavos(150000) == 'R$ 1.500,00'
""",
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stderr, file=sys.stderr)
            raise RuntimeError("Falha no teste isolado de importação.")
        print(f"   {res.stdout.strip()}")
    print("   ✓ Execução isolada confirmada.")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Verificador de distribuição.")
    parser.add_argument("--dist", default="dist", help="Diretório onde estão os pacotes compilados")
    args = parser.parse_args()

    dist_dir = Path(args.dist)
    if not dist_dir.exists():
        print(f"Erro: diretório '{dist_dir}' não encontrado.", file=sys.stderr)
        return 1

    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))

    if not wheels or not sdists:
        print("Erro: wheel ou sdist ausente em dist/.", file=sys.stderr)
        return 1

    try:
        inspecionar_wheel(wheels[0])
        inspecionar_sdist(sdists[0])
        testar_instalacao_isolada(wheels[0])
        print("✓ Distribuição auditada com 100% de sucesso!")
        return 0
    except Exception as err:
        print(f"Falha na verificação de distribuição: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
