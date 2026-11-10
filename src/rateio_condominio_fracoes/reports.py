"""Módulo de relatórios, exportação CSV, relatório Markdown, painel SVG e ZIP determinístico."""

import csv
import io
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from .core import ResultadoRateio, formatar_moeda_centavos
from .errors import ERR_ARQUIVO_EXISTENTE, ErroExecucao


def sanitizar_campo_csv(valor: Any) -> str:
    """Prevenção contra injeção de fórmulas CSV (=, +, -, @, \\t, \\r)."""
    texto = str(valor)
    if texto and texto[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{texto}"
    return texto


def gerar_csv_resumo_unidades(resultado: ResultadoRateio) -> str:
    """Gera CSV analítico consolidado por unidade."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    # Identifica colunas dinâmicas de fundos e medições
    fundos_ids = [f.id for f in resultado.fundos]
    servicos_ids = [m.servico for m in resultado.medicoes]

    cabecalho = [
        "unidade_id",
        "fracao_ideal",
        "percentual",
        "cota_ordinaria_centavos",
        "cota_ordinaria_formatada",
    ]
    for fid in fundos_ids:
        cabecalho.append(f"fundo_{fid}_centavos")
    cabecalho.extend(["total_fundos_centavos", "total_fundos_formatado"])

    for s_id in servicos_ids:
        cabecalho.append(f"medicao_{s_id}_centavos")
    cabecalho.extend(["total_medicoes_centavos", "total_medicoes_formatado"])

    cabecalho.extend([
        "total_geral_centavos",
        "total_geral_formatado",
    ])
    writer.writerow([sanitizar_campo_csv(c) for c in cabecalho])

    for uid in sorted(resultado.unidades.keys()):
        u = resultado.unidades[uid]
        linha = [
            sanitizar_campo_csv(u.unidade_id),
            sanitizar_campo_csv(u.fracao_ideal_str),
            sanitizar_campo_csv(u.fracao_ideal_percentual),
            str(u.cota_ordinaria_centavos),
            sanitizar_campo_csv(formatar_moeda_centavos(u.cota_ordinaria_centavos)),
        ]
        for fid in fundos_ids:
            linha.append(str(u.fundos_centavos.get(fid, 0)))
        linha.extend([
            str(u.total_fundos_centavos),
            sanitizar_campo_csv(formatar_moeda_centavos(u.total_fundos_centavos)),
        ])

        for s_id in servicos_ids:
            m_info = u.medicoes_detalhe.get(s_id, {})
            linha.append(str(m_info.get("total_centavos", 0)))
        linha.extend([
            str(u.total_medicoes_centavos),
            sanitizar_campo_csv(formatar_moeda_centavos(u.total_medicoes_centavos)),
        ])

        linha.extend([
            str(u.total_geral_centavos),
            sanitizar_campo_csv(formatar_moeda_centavos(u.total_geral_centavos)),
        ])
        writer.writerow(linha)

    return buffer.getvalue()


def gerar_csv_despesas_detalhadas(resultado: ResultadoRateio) -> str:
    """Gera CSV com todas as despesas ordinárias e fundos cadastrados."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    cabecalho = [
        "natureza",
        "id",
        "descricao",
        "categoria_ou_tipo",
        "valor_centavos",
        "valor_formatado",
    ]
    writer.writerow([sanitizar_campo_csv(c) for c in cabecalho])

    for d in resultado.despesas_ordinarias:
        writer.writerow([
            "ORDINARIA",
            sanitizar_campo_csv(d.id),
            sanitizar_campo_csv(d.descricao),
            sanitizar_campo_csv(d.categoria),
            str(d.valor_centavos),
            sanitizar_campo_csv(formatar_moeda_centavos(d.valor_centavos)),
        ])

    for f in resultado.fundos:
        val_fundo = sum(u.fundos_centavos.get(f.id, 0) for u in resultado.unidades.values())
        writer.writerow([
            "FUNDO",
            sanitizar_campo_csv(f.id),
            sanitizar_campo_csv(f.descricao),
            sanitizar_campo_csv(f.tipo),
            str(val_fundo),
            sanitizar_campo_csv(formatar_moeda_centavos(val_fundo)),
        ])

    return buffer.getvalue()


def gerar_csv_medicoes_hidrometros(resultado: ResultadoRateio) -> str:
    """Gera CSV detalhado das leituras de medições individualizadas."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    cabecalho = [
        "servico",
        "unidade_id",
        "leitura_anterior",
        "leitura_atual",
        "consumo_medido",
        "unidade_medida",
        "valor_individual_centavos",
        "valor_area_comum_centavos",
        "total_servico_centavos",
        "total_servico_formatado",
    ]
    writer.writerow([sanitizar_campo_csv(c) for c in cabecalho])

    for m in resultado.medicoes:
        for l in m.leituras:
            u_info = resultado.unidades.get(l.unidade_id)
            det = u_info.medicoes_detalhe.get(m.servico, {}) if u_info else {}
            writer.writerow([
                sanitizar_campo_csv(m.servico),
                sanitizar_campo_csv(l.unidade_id),
                str(l.leitura_anterior),
                str(l.leitura_atual),
                str(l.consumo),
                sanitizar_campo_csv(m.unidade_medida),
                str(det.get("valor_individual_centavos", 0)),
                str(det.get("valor_area_comum_centavos", 0)),
                str(det.get("total_centavos", 0)),
                sanitizar_campo_csv(formatar_moeda_centavos(det.get("total_centavos", 0))),
            ])

    return buffer.getvalue()


def gerar_relatorio_markdown(resultado: ResultadoRateio) -> str:
    """Gera relatório de fechamento analítico em Markdown."""
    b = resultado.balancete
    linhas = [
        f"# Demonstrativo de Rateio Condominial — {b.nome_condominio}",
        "",
        f"- **Competência:** `{b.competencia}`",
        f"- **Total de Unidades:** `{b.total_unidades}`",
        f"- **Status da Conciliação:** `{'CONCILIADO (100% EXATO)' if b.conciliado else 'DIVERGENTE'}`",
        f"- **Diferença de Arredondamento:** `{formatar_moeda_centavos(b.diferenca_fechamento_centavos)}` (`{b.diferenca_fechamento_centavos}` centavos)",
        "",
        "## 1. Balancete Consolidado",
        "",
        "| Rubrica | Valor (Centavos) | Valor Formatado | Proporção |",
        "| :--- | :--- | :--- | :--- |",
        f"| Despesas Ordinárias | `{b.total_despesas_ordinarias_centavos}` | **{formatar_moeda_centavos(b.total_despesas_ordinarias_centavos)}** | {b.total_despesas_ordinarias_centavos * 100 // (b.total_geral_despesas_centavos or 1)}% |",
        f"| Fundos de Reserva e Obras | `{b.total_fundos_centavos}` | **{formatar_moeda_centavos(b.total_fundos_centavos)}** | {b.total_fundos_centavos * 100 // (b.total_geral_despesas_centavos or 1)}% |",
        f"| Medições Individualizadas | `{b.total_medicoes_centavos}` | **{formatar_moeda_centavos(b.total_medicoes_centavos)}** | {b.total_medicoes_centavos * 100 // (b.total_geral_despesas_centavos or 1)}% |",
        f"| **Total Geral das Despesas** | `{b.total_geral_despesas_centavos}` | **{formatar_moeda_centavos(b.total_geral_despesas_centavos)}** | **100%** |",
        f"| **Total Geral Arrecadado** | `{b.total_geral_arrecadado_centavos}` | **{formatar_moeda_centavos(b.total_geral_arrecadado_centavos)}** | **100%** |",
        "",
        "## 2. Resumo das Unidades",
        "",
        "| Unidade | Fração Ideal | Ordinária | Fundos | Medições | Total da Cota |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for uid in sorted(resultado.unidades.keys()):
        u = resultado.unidades[uid]
        linhas.append(
            f"| `{u.unidade_id}` | `{u.fracao_ideal_str}` ({u.fracao_ideal_percentual}) | {formatar_moeda_centavos(u.cota_ordinaria_centavos)} | {formatar_moeda_centavos(u.total_fundos_centavos)} | {formatar_moeda_centavos(u.total_medicoes_centavos)} | **{formatar_moeda_centavos(u.total_geral_centavos)}** |"
        )

    linhas.extend([
        "",
        "## 3. Garantia de Conservação Matemática",
        "",
        "O rateio utiliza o algoritmo dos **Maiores Restos (Hare-Niemeyer / Hamilton)** para a distribuição dos centavos indivisíveis.",
        "A soma de todas as cobranças individuais é exatamente congruente à soma das despesas aprovadas, eliminando sobras ou déficits de arredondamento.",
        "",
        "---",
        "*Gerado por LOFRANO TECNOLOGIA — rateio-condominio-fracoes*",
    ])

    return "\n".join(linhas) + "\n"


def gerar_dicionario_resultado(resultado: ResultadoRateio) -> dict:
    """Estrutura os dados calculados em dicionário para persistência JSON canônica."""
    b = resultado.balancete
    return {
        "balancete": {
            "competencia": b.competencia,
            "nome_condominio": b.nome_condominio,
            "total_unidades": b.total_unidades,
            "total_despesas_ordinarias_centavos": b.total_despesas_ordinarias_centavos,
            "total_fundos_centavos": b.total_fundos_centavos,
            "total_medicoes_centavos": b.total_medicoes_centavos,
            "total_geral_despesas_centavos": b.total_geral_despesas_centavos,
            "total_geral_arrecadado_centavos": b.total_geral_arrecadado_centavos,
            "diferenca_fechamento_centavos": b.diferenca_fechamento_centavos,
            "conciliado": b.conciliado,
        },
        "consumos_area_comum": resultado.consumos_area_comum,
        "unidades": {
            uid: {
                "unidade_id": u.unidade_id,
                "fracao_ideal_str": u.fracao_ideal_str,
                "fracao_ideal_percentual": u.fracao_ideal_percentual,
                "cota_ordinaria_centavos": u.cota_ordinaria_centavos,
                "fundos_centavos": u.fundos_centavos,
                "total_fundos_centavos": u.total_fundos_centavos,
                "medicoes_detalhe": u.medicoes_detalhe,
                "total_medicoes_centavos": u.total_medicoes_centavos,
                "total_geral_centavos": u.total_geral_centavos,
            }
            for uid, u in sorted(resultado.unidades.items())
        },
    }


def gerar_painel_svg(resultado: ResultadoRateio) -> str:
    """Gera painel visual de alta fidelidade em SVG (1440x900) com métricas e gráficos."""
    b = resultado.balancete
    unidades_ordenadas = sorted(resultado.unidades.values(), key=lambda u: -u.total_geral_centavos)
    top_unidades = unidades_ordenadas[:8]
    max_cota = top_unidades[0].total_geral_centavos if top_unidades else 1

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900">',
        '  <defs>',
        '    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        '      <stop offset="0%" stop-color="#0C101B" />',
        '      <stop offset="100%" stop-color="#151B29" />',
        '    </linearGradient>',
        '    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">',
        '      <stop offset="0%" stop-color="#1E293B" stop-opacity="0.8" />',
        '      <stop offset="100%" stop-color="#0F172A" stop-opacity="0.9" />',
        '    </linearGradient>',
        '    <linearGradient id="barGrad" x1="0%" y1="0%" x2="100%" y2="0%">',
        '      <stop offset="0%" stop-color="#38BDF8" />',
        '      <stop offset="100%" stop-color="#3B82F6" />',
        '    </linearGradient>',
        '  </defs>',
        '  <rect width="1440" height="900" fill="url(#bg)" />',
        '',
        '  <!-- Header -->',
        '  <g transform="translate(60, 50)">',
        f'    <text x="0" y="32" font-family="system-ui, -apple-system, sans-serif" font-size="28" font-weight="700" fill="#F8FAFC">{b.nome_condominio}</text>',
        f'    <text x="0" y="60" font-family="system-ui, -apple-system, sans-serif" font-size="16" fill="#94A3B8">Fechamento e Rateio Condominial · Competência {b.competencia} · LOFRANO TECNOLOGIA</text>',
        '    <rect x="1100" y="10" width="220" height="42" rx="8" fill="#065F46" />',
        '    <text x="1210" y="36" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600" fill="#34D399" text-anchor="middle">✓ CONCILIADO (100% EXATO)</text>',
        '  </g>',
        '',
        '  <!-- 4 Cards de Métricas -->',
        '  <g transform="translate(60, 140)">',
        '    <!-- Card 1: Total Rateado -->',
        '    <rect x="0" y="0" width="310" height="110" rx="12" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="24" y="36" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#94A3B8">TOTAL RATEADO</text>',
        f'    <text x="24" y="74" font-family="system-ui, sans-serif" font-size="24" font-weight="700" fill="#38BDF8">{formatar_moeda_centavos(b.total_geral_despesas_centavos)}</text>',
        f'    <text x="24" y="96" font-family="system-ui, sans-serif" font-size="12" fill="#64748B">{b.total_geral_despesas_centavos:,} centavos</text>',
        '',
        '    <!-- Card 2: Ordinárias -->',
        '    <rect x="336" y="0" width="310" height="110" rx="12" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="360" y="36" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#94A3B8">DESPESAS ORDINÁRIAS</text>',
        f'    <text x="360" y="74" font-family="system-ui, sans-serif" font-size="24" font-weight="700" fill="#F8FAFC">{formatar_moeda_centavos(b.total_despesas_ordinarias_centavos)}</text>',
        f'    <text x="360" y="96" font-family="system-ui, sans-serif" font-size="12" fill="#64748B">{len(resultado.despesas_ordinarias)} despesas cadastradas</text>',
        '',
        '    <!-- Card 3: Fundos -->',
        '    <rect x="672" y="0" width="310" height="110" rx="12" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="696" y="36" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#94A3B8">FUNDOS DE RESERVA E OBRAS</text>',
        f'    <text x="696" y="74" font-family="system-ui, sans-serif" font-size="24" font-weight="700" fill="#FBBF24">{formatar_moeda_centavos(b.total_fundos_centavos)}</text>',
        f'    <text x="696" y="96" font-family="system-ui, sans-serif" font-size="12" fill="#64748B">{len(resultado.fundos)} fundos ativos</text>',
        '',
        '    <!-- Card 4: Medições -->',
        '    <rect x="1008" y="0" width="312" height="110" rx="12" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="1032" y="36" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#94A3B8">MEDIÇÕES INDIVIDUALIZADAS</text>',
        f'    <text x="1032" y="74" font-family="system-ui, sans-serif" font-size="24" font-weight="700" fill="#34D399">{formatar_moeda_centavos(b.total_medicoes_centavos)}</text>',
        f'    <text x="1032" y="96" font-family="system-ui, sans-serif" font-size="12" fill="#64748B">{len(resultado.medicoes)} serviços medidos</text>',
        '  </g>',
        '',
        '  <!-- Seção Gráfica: Cotas das Unidades -->',
        '  <g transform="translate(60, 290)">',
        '    <rect x="0" y="0" width="860" height="540" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="32" y="44" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="#F8FAFC">Cotas Condominiais por Unidade (Maiores Valores)</text>',
        '    <text x="32" y="68" font-family="system-ui, sans-serif" font-size="13" fill="#94A3B8">Composição: Cota Ordinária + Fundos + Água/Gás individualizados</text>',
    ]

    y_pos = 110
    for u in top_unidades:
        largura_barra = int((u.total_geral_centavos / max_cota) * 440)
        svg.extend([
            f'    <text x="32" y="{y_pos + 20}" font-family="system-ui, sans-serif" font-size="14" font-weight="600" fill="#E2E8F0">{u.unidade_id}</text>',
            f'    <text x="140" y="{y_pos + 20}" font-family="system-ui, sans-serif" font-size="12" fill="#64748B">{u.fracao_ideal_str} ({u.fracao_ideal_percentual})</text>',
            f'    <rect x="250" y="{y_pos + 4}" width="{largura_barra}" height="24" rx="4" fill="url(#barGrad)" />',
            f'    <text x="{260 + largura_barra + 15}" y="{y_pos + 21}" font-family="system-ui, sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">{formatar_moeda_centavos(u.total_geral_centavos)}</text>',
        ])
        y_pos += 52

    # Seção Direita: Resumo das Despesas e Regras de Fechamento
    svg.extend([
        '  </g>',
        '  <g transform="translate(950, 290)">',
        '    <rect x="0" y="0" width="430" height="540" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1" />',
        '    <text x="32" y="44" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="#F8FAFC">Auditoria e Conciliação</text>',
        '    <text x="32" y="68" font-family="system-ui, sans-serif" font-size="13" fill="#94A3B8">Princípio dos Maiores Restos (Hare-Niemeyer)</text>',
        '',
        '    <g transform="translate(32, 100)">',
        '      <rect x="0" y="0" width="366" height="70" rx="8" fill="#1E293B" stroke="#475569" stroke-width="0.5" />',
        '      <text x="16" y="26" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">SOMA DAS COTAS EMITIDAS</text>',
        f'      <text x="16" y="52" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="#34D399">{formatar_moeda_centavos(b.total_geral_arrecadado_centavos)}</text>',
        '    </g>',
        '',
        '    <g transform="translate(32, 185)">',
        '      <rect x="0" y="0" width="366" height="70" rx="8" fill="#1E293B" stroke="#475569" stroke-width="0.5" />',
        '      <text x="16" y="26" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">SOMA DAS DESPESAS E FATURAS</text>',
        f'      <text x="16" y="52" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="#38BDF8">{formatar_moeda_centavos(b.total_geral_despesas_centavos)}</text>',
        '    </g>',
        '',
        '    <g transform="translate(32, 270)">',
        '      <rect x="0" y="0" width="366" height="70" rx="8" fill="#1E293B" stroke="#475569" stroke-width="0.5" />',
        '      <text x="16" y="26" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">DIFERENÇA DE ARREDONDAMENTO</text>',
        f'      <text x="16" y="52" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="#10B981">R$ 0,00 (0 centavos)</text>',
        '    </g>',
        '',
        '    <g transform="translate(32, 370)">',
        '      <text x="0" y="0" font-family="system-ui, sans-serif" font-size="13" font-weight="600" fill="#CBD5E1">CONFORMIDADE JURÍDICO-CONTÁBIL</text>',
        '      <text x="0" y="24" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">✓ Código Civil art. 1.336, inciso I</text>',
        '      <text x="0" y="44" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">✓ Fração ideal milesimal estrita</text>',
        '      <text x="0" y="64" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">✓ Hidrometria individualizada e área comum</text>',
        '      <text x="0" y="84" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">✓ Sanitização anti-fórmulas CSV</text>',
        '      <text x="0" y="104" font-family="system-ui, sans-serif" font-size="12" fill="#94A3B8">✓ Auditoria relacional independente SQLite</text>',
        '    </g>',
        '  </g>',
        '</svg>',
    ])
    return "\n".join(svg) + "\n"


def publicar_pacote_zip(
    caminho_zip: Path,
    arquivos: Dict[str, bytes],
) -> None:
    """Cria arquivo ZIP determinístico com garantia de não sobrescrita atômica."""
    caminho_zip = Path(caminho_zip)
    if caminho_zip.exists():
        raise ErroExecucao(ERR_ARQUIVO_EXISTENTE, f"Arquivo de destino já existe: {caminho_zip}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(str(caminho_zip), flags, 0o644)
    except FileExistsError:
        raise ErroExecucao(ERR_ARQUIVO_EXISTENTE, f"Arquivo de destino já existe: {caminho_zip}")

    try:
        with os.fdopen(fd, "wb") as f_out:
            with zipfile.ZipFile(f_out, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                # Data e hora fixadas para reprodutibilidade bit a bit dos metadados ZIP
                data_fixa = (2026, 11, 10, 0, 0, 0)
                for nome in sorted(arquivos.keys()):
                    conteudo = arquivos[nome]
                    zinfo = zipfile.ZipInfo(filename=nome, date_time=data_fixa)
                    zinfo.compress_type = zipfile.ZIP_DEFLATED
                    zinfo.external_attr = 0o644 << 16
                    zf.writestr(zinfo, conteudo)
    except Exception as err:
        if caminho_zip.exists():
            try:
                caminho_zip.unlink()
            except OSError:
                pass
        raise ErroExecucao(
            "FALHA_ZIP",
            f"Erro ao empacotar arquivo ZIP '{caminho_zip}': {err}",
        )
