"""Interface de linha de comando (CLI) para o rateio condominial."""

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Dict

from . import __version__
from .core import formatar_moeda_centavos, validar_e_processar_rateio
from .errors import RateioError
from .jsoncodec import codificar_json_canonico, decodificar_json_estrito
from .reports import (
    gerar_csv_despesas_detalhadas,
    gerar_csv_medicoes_hidrometros,
    gerar_csv_resumo_unidades,
    gerar_dicionario_resultado,
    gerar_painel_svg,
    gerar_relatorio_markdown,
    publicar_pacote_zip,
)

EXEMPLO_CANONICO = {
    "condominio": {
        "nome": "Edifício Residencial Horizonte",
        "competencia": "2026-11",
    },
    "unidades": [
        {"id": "APTO-101", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Ana Lima"},
        {"id": "APTO-102", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Bruno Castro"},
        {"id": "APTO-201", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Carla Dias"},
        {"id": "APTO-202", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Diego Souza"},
        {"id": "APTO-301", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Eduardo Silva"},
        {"id": "APTO-302", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Fernanda Rosa"},
        {"id": "APTO-401", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Gabriel Melo"},
        {"id": "APTO-402", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Helena Prado"},
        {"id": "APTO-501", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Igor Santos"},
        {"id": "APTO-502", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Juliana Costa"},
        {"id": "APTO-601", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Katia Moreira"},
        {"id": "APTO-602", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Lucas Rocha"},
        {"id": "APTO-701", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Mariana Ribeiro"},
        {"id": "APTO-702", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Nelson Pires"},
        {"id": "APTO-801", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Otavio Farias"},
        {"id": "APTO-802", "fracao_ideal_numerador": 45231, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Patricia Gomes"},
        {"id": "COB-901", "fracao_ideal_numerador": 138152, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Quintino Alcantara"},
        {"id": "COB-902", "fracao_ideal_numerador": 138152, "fracao_ideal_denominador": 1000000, "bloco": "A", "proprietario": "Renata Vianna"},
    ],
    "despesas_ordinarias": [
        {"id": "DESP-01", "descricao": "Folha de Pagamento Portaria e Limpeza", "categoria": "pessoal", "valor_centavos": 1850000},
        {"id": "DESP-02", "descricao": "Encargos Sociais e Benefícios", "categoria": "pessoal", "valor_centavos": 740000},
        {"id": "DESP-03", "descricao": "Contrato de Manutenção de Elevadores", "categoria": "manutencao", "valor_centavos": 235000},
        {"id": "DESP-04", "descricao": "Energia Elétrica Áreas Comuns", "categoria": "consumo", "valor_centavos": 348920},
        {"id": "DESP-05", "descricao": "Seguro Predial Contra Incêndio", "categoria": "seguros", "valor_centavos": 89450},
        {"id": "DESP-06", "descricao": "Honorários de Administração e Software", "categoria": "administracao", "valor_centavos": 180000},
        {"id": "DESP-07", "descricao": "Produtos de Limpeza e Jardinagem", "categoria": "materiais", "valor_centavos": 95400},
    ],
    "fundos": [
        {"id": "FUNDO-RESERVA", "descricao": "Fundo de Reserva Ordinário (5%)", "tipo": "percentual_ordinarias", "percentual_numerador": 5, "percentual_denominador": 100},
        {"id": "FUNDO-OBRAS", "descricao": "Fundo de Obras para Modernização dos Portões", "tipo": "valor_fixo_global", "valor_centavos": 350000},
    ],
    "medicoes": [
        {
            "servico": "agua",
            "unidade_medida": "m3",
            "valor_fatura_concessionaria_centavos": 465890,
            "consumo_fatura": 320,
            "leituras": [
                {"unidade_id": "APTO-101", "leitura_anterior": 140, "leitura_atual": 154},
                {"unidade_id": "APTO-102", "leitura_anterior": 98, "leitura_atual": 110},
                {"unidade_id": "APTO-201", "leitura_anterior": 210, "leitura_atual": 228},
                {"unidade_id": "APTO-202", "leitura_anterior": 155, "leitura_atual": 169},
                {"unidade_id": "APTO-301", "leitura_anterior": 300, "leitura_atual": 315},
                {"unidade_id": "APTO-302", "leitura_anterior": 80, "leitura_atual": 92},
                {"unidade_id": "APTO-401", "leitura_anterior": 190, "leitura_atual": 208},
                {"unidade_id": "APTO-402", "leitura_anterior": 115, "leitura_atual": 126},
                {"unidade_id": "APTO-501", "leitura_anterior": 250, "leitura_atual": 268},
                {"unidade_id": "APTO-502", "leitura_anterior": 130, "leitura_atual": 144},
                {"unidade_id": "APTO-601", "leitura_anterior": 175, "leitura_atual": 189},
                {"unidade_id": "APTO-602", "leitura_anterior": 105, "leitura_atual": 118},
                {"unidade_id": "APTO-701", "leitura_anterior": 220, "leitura_atual": 236},
                {"unidade_id": "APTO-702", "leitura_anterior": 140, "leitura_atual": 152},
                {"unidade_id": "APTO-801", "leitura_anterior": 185, "leitura_atual": 201},
                {"unidade_id": "APTO-802", "leitura_anterior": 160, "leitura_atual": 174},
                {"unidade_id": "COB-901", "leitura_anterior": 410, "leitura_atual": 435},
                {"unidade_id": "COB-902", "leitura_anterior": 380, "leitura_atual": 402},
            ],
        },
        {
            "servico": "gas",
            "unidade_medida": "m3",
            "valor_fatura_concessionaria_centavos": 198540,
            "consumo_fatura": 140,
            "leituras": [
                {"unidade_id": "APTO-101", "leitura_anterior": 50, "leitura_atual": 56},
                {"unidade_id": "APTO-102", "leitura_anterior": 40, "leitura_atual": 45},
                {"unidade_id": "APTO-201", "leitura_anterior": 72, "leitura_atual": 80},
                {"unidade_id": "APTO-202", "leitura_anterior": 60, "leitura_atual": 67},
                {"unidade_id": "APTO-301", "leitura_anterior": 95, "leitura_atual": 102},
                {"unidade_id": "APTO-302", "leitura_anterior": 35, "leitura_atual": 40},
                {"unidade_id": "APTO-401", "leitura_anterior": 68, "leitura_atual": 76},
                {"unidade_id": "APTO-402", "leitura_anterior": 45, "leitura_atual": 50},
                {"unidade_id": "APTO-501", "leitura_anterior": 80, "leitura_atual": 88},
                {"unidade_id": "APTO-502", "leitura_anterior": 55, "leitura_atual": 61},
                {"unidade_id": "APTO-601", "leitura_anterior": 62, "leitura_atual": 69},
                {"unidade_id": "APTO-602", "leitura_anterior": 48, "leitura_atual": 53},
                {"unidade_id": "APTO-701", "leitura_anterior": 70, "leitura_atual": 78},
                {"unidade_id": "APTO-702", "leitura_anterior": 52, "leitura_atual": 58},
                {"unidade_id": "APTO-801", "leitura_anterior": 65, "leitura_atual": 72},
                {"unidade_id": "APTO-802", "leitura_anterior": 58, "leitura_atual": 65},
                {"unidade_id": "COB-901", "leitura_anterior": 110, "leitura_atual": 122},
                {"unidade_id": "COB-902", "leitura_anterior": 100, "leitura_atual": 111},
            ],
        },
    ],
}


def cmd_versao(_args: argparse.Namespace) -> int:
    print(f"rateio-condominio-fracoes {__version__}")
    return 0


def cmd_exemplo(args: argparse.Namespace) -> int:
    saida_str = codificar_json_canonico(EXEMPLO_CANONICO)
    if args.saida:
        p = Path(args.saida)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(saida_str, encoding="utf-8")
        print(f"Exemplo canônico gravado em: {p}")
    else:
        sys.stdout.write(saida_str)
    return 0


def cmd_verificar(args: argparse.Namespace) -> int:
    caminho = Path(args.entrada)
    if not caminho.exists():
        print(f"Erro: arquivo de entrada não encontrado: {caminho}", file=sys.stderr)
        return 1

    dados = decodificar_json_estrito(caminho.read_bytes())
    resultado = validar_e_processar_rateio(dados)
    b = resultado.balancete
    print(f"✓ Entrada válida e consistente.")
    print(f"  Condomínio: {b.nome_condominio}")
    print(f"  Competência: {b.competencia}")
    print(f"  Unidades: {b.total_unidades}")
    print(f"  Total a arrecadar: {formatar_moeda_centavos(b.total_geral_arrecadado_centavos)}")
    print(f"  Diferença de arredondamento: {b.diferenca_fechamento_centavos} centavos (100% conservativo)")
    return 0


def cmd_resumo(args: argparse.Namespace) -> int:
    caminho = Path(args.entrada)
    if not caminho.exists():
        print(f"Erro: arquivo de entrada não encontrado: {caminho}", file=sys.stderr)
        return 1

    dados = decodificar_json_estrito(caminho.read_bytes())
    resultado = validar_e_processar_rateio(dados)
    md = gerar_relatorio_markdown(resultado)
    sys.stdout.write(md)
    return 0


def cmd_processar(args: argparse.Namespace) -> int:
    caminho_entrada = Path(args.entrada)
    if not caminho_entrada.exists():
        print(f"Erro: arquivo de entrada não encontrado: {caminho_entrada}", file=sys.stderr)
        return 1

    dados_bytes = caminho_entrada.read_bytes()
    dados = decodificar_json_estrito(dados_bytes)
    resultado = validar_e_processar_rateio(dados)

    csv_unidades = gerar_csv_resumo_unidades(resultado)
    csv_despesas = gerar_csv_despesas_detalhadas(resultado)
    csv_medicoes = gerar_csv_medicoes_hidrometros(resultado)
    rel_md = gerar_relatorio_markdown(resultado)
    painel_svg = gerar_painel_svg(resultado)
    resultado_json = codificar_json_canonico(gerar_dicionario_resultado(resultado))

    # Criação dos artefatos
    arquivos_zip: Dict[str, bytes] = {
        "entrada.json": dados_bytes,
        "rateio.json": resultado_json.encode("utf-8"),
        "resumo-unidades.csv": csv_unidades.encode("utf-8"),
        "despesas-detalhadas.csv": csv_despesas.encode("utf-8"),
        "medicoes-hidrometros.csv": csv_medicoes.encode("utf-8"),
        "relatorio-fechamento.md": rel_md.encode("utf-8"),
        "painel-rateio.svg": painel_svg.encode("utf-8"),
    }

    # Gera SHA256SUMS interno para o pacote
    linhas_sha = []
    for nome in sorted(arquivos_zip.keys()):
        h = hashlib.sha256(arquivos_zip[nome]).hexdigest()
        linhas_sha.append(f"{h}  {nome}")
    arquivos_zip["SHA256SUMS"] = ("\n".join(linhas_sha) + "\n").encode("utf-8")

    # Gravação no diretório de saída
    if args.saida_dir:
        dir_saida = Path(args.saida_dir)
        dir_saida.mkdir(parents=True, exist_ok=True)
        for nome, conteudo in arquivos_zip.items():
            (dir_saida / nome).write_bytes(conteudo)
        print(f"Artefatos analíticos gravados em: {dir_saida}")

    # Gravação do pacote ZIP determinístico
    if args.zip:
        caminho_zip = Path(args.zip)
        caminho_zip.parent.mkdir(parents=True, exist_ok=True)
        publicar_pacote_zip(caminho_zip, arquivos_zip)
        print(f"Pacote ZIP determinístico publicado em: {caminho_zip}")

    b = resultado.balancete
    print(f"✓ Rateio concluído com sucesso: {formatar_moeda_centavos(b.total_geral_arrecadado_centavos)} ({b.total_unidades} unidades).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rateio-condominio-fracoes",
        description="Rateio condominial determinístico por fração ideal e conservação exata de centavos.",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    # Subcomando versao
    sub_ver = subparsers.add_parser("versao", help="Exibe a versão do pacote")
    sub_ver.set_defaults(func=cmd_versao)

    # Subcomando exemplo
    sub_ex = subparsers.add_parser("exemplo", help="Emite o modelo canônico de entrada JSON")
    sub_ex.add_argument("--saida", "-o", help="Caminho do arquivo de saída (opcional)")
    sub_ex.set_defaults(func=cmd_exemplo)

    # Subcomando verificar
    sub_chk = subparsers.add_parser("verificar", help="Valida os dados de entrada e frações ideais")
    sub_chk.add_argument("--entrada", "-i", required=True, help="Arquivo JSON de entrada")
    sub_chk.set_defaults(func=cmd_verificar)

    # Subcomando resumo
    sub_res = subparsers.add_parser("resumo", help="Exibe resumo do balancete em Markdown no terminal")
    sub_res.add_argument("--entrada", "-i", required=True, help="Arquivo JSON de entrada")
    sub_res.set_defaults(func=cmd_resumo)

    # Subcomando processar
    sub_proc = subparsers.add_parser("processar", help="Processa o rateio e gera relatórios, CSV e ZIP")
    sub_proc.add_argument("--entrada", "-i", required=True, help="Arquivo JSON de entrada")
    sub_proc.add_argument("--saida-dir", "-d", help="Diretório para salvar os artefatos gerados")
    sub_proc.add_argument("--zip", "-z", help="Caminho para criar o arquivo ZIP consolidado")
    sub_proc.set_defaults(func=cmd_processar)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RateioError as err:
        print(f"Erro [{err.codigo}]: {err.mensagem}", file=sys.stderr)
        return 2
    except Exception as err:
        print(f"Erro inesperado: {err}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
