"""Motor de cálculo determinístico de rateio condominial em centavos exatos."""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from .errors import (
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


def formatar_fracao_percentual(fracao: Fraction, casas: int = 4) -> str:
    """Formata fração racional em percentual com casas decimais via aritmética inteira exata."""
    fator = 10 ** casas
    numerador_ampliado = fracao.numerator * 100 * fator
    denominador = fracao.denominator
    inteiro = numerador_ampliado // denominador
    resto = numerador_ampliado % denominador
    if resto * 2 >= denominador:
        inteiro += 1
    parte_inteira = inteiro // fator
    parte_decimal = inteiro % fator
    return f"{parte_inteira},{parte_decimal:0{casas}d}%"


def formatar_moeda_centavos(centavos: int) -> str:
    """Formata valor inteiro em centavos para moeda brasileira (R$ X.XXX,XX)."""
    negativo = centavos < 0
    centavos_abs = abs(centavos)
    reais = centavos_abs // 100
    resto = centavos_abs % 100
    reais_formatados = f"{reais:,}".replace(",", ".")
    sinal = "-" if negativo else ""
    return f"{sinal}R$ {reais_formatados},{resto:02d}"


def distribuir_por_maiores_restos(
    total_centavos: int,
    unidades_pesos: List[Tuple[str, Fraction]],
) -> Dict[str, int]:
    """Distribui centavos exatos pelo algoritmo dos maiores restos (Hare-Niemeyer / Hamilton).

    Garante conservação estrita: sum(resultado.values()) == total_centavos.
    Desempate determinístico:
      1. Maior resto fracionário
      2. Maior peso (fração)
      3. Identificador lexicográfico da unidade (crescente)
    """
    if total_centavos < 0:
        raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, f"Total a distribuir não pode ser negativo: {total_centavos}.")
    if not unidades_pesos:
        if total_centavos == 0:
            return {}
        raise ErroValidacaoEntrada(ERR_UNIDADE_VAZIA, "Não há unidades para distribuição do valor.")

    soma_pesos = sum(peso for _, peso in unidades_pesos)
    if soma_pesos <= 0:
        raise ErroValidacaoEntrada(ERR_FRACAO_INVALIDA, "A soma dos pesos das unidades deve ser estritamente positiva.")

    if total_centavos == 0:
        return {uid: 0 for uid, _ in unidades_pesos}

    preliminares: List[Tuple[str, int, Fraction, Fraction]] = []
    soma_pisos = 0

    for uid, peso in unidades_pesos:
        # Parcela ideal exata em números racionais
        parcela_racional = Fraction(total_centavos * peso, soma_pesos)
        piso = int(parcela_racional.numerator // parcela_racional.denominator)
        resto = parcela_racional - piso
        preliminares.append((uid, piso, resto, peso))
        soma_pisos += piso

    centavos_restantes = total_centavos - soma_pisos
    if centavos_restantes < 0 or centavos_restantes > len(unidades_pesos):
        raise ErroValidacaoEntrada(
            ERR_VALOR_INVALIDO,
            f"Anomalia no cálculo de restos: {centavos_restantes} centavos para {len(unidades_pesos)} unidades.",
        )

    # Ordenação estável: maior resto, maior peso, ID lexicográfico crescente
    ordenados = sorted(
        preliminares,
        key=lambda item: (-item[2], -item[3], item[0]),
    )

    resultado = {}
    beneficiados = set(item[0] for item in ordenados[:centavos_restantes])

    for uid, piso, _, _ in preliminares:
        centavo_extra = 1 if uid in beneficiados else 0
        resultado[uid] = piso + centavo_extra

    if sum(resultado.values()) != total_centavos:
        raise ErroValidacaoEntrada(
            ERR_VALOR_INVALIDO,
            f"Falha de conservação: soma distribuída ({sum(resultado.values())}) != total esperado ({total_centavos}).",
        )

    return resultado


@dataclass(frozen=True)
class Unidade:
    id: str
    fracao_ideal_numerador: int
    fracao_ideal_denominador: int
    bloco: str = ""
    proprietario: str = ""
    isenta_fundo_obras: bool = False
    isenta_fundo_reserva: bool = False

    @property
    def fracao(self) -> Fraction:
        return Fraction(self.fracao_ideal_numerador, self.fracao_ideal_denominador)


@dataclass(frozen=True)
class DespesaOrdinaria:
    id: str
    descricao: str
    categoria: str
    valor_centavos: int


@dataclass(frozen=True)
class Fundo:
    id: str
    descricao: str
    tipo: str  # "percentual_ordinarias", "valor_fixo_global", "cota_fixa_por_unidade"
    percentual_numerador: Optional[int] = None
    percentual_denominador: Optional[int] = None
    valor_centavos: Optional[int] = None
    valor_por_unidade_centavos: Optional[int] = None


@dataclass(frozen=True)
class LeituraMedicao:
    unidade_id: str
    leitura_anterior: int
    leitura_atual: int

    @property
    def consumo(self) -> int:
        return self.leitura_atual - self.leitura_anterior


@dataclass(frozen=True)
class MedicaoServico:
    servico: str  # "agua", "gas"
    unidade_medida: str
    valor_fatura_concessionaria_centavos: int
    consumo_fatura: int
    leituras: List[LeituraMedicao]


@dataclass
class ResultadoUnidade:
    unidade_id: str
    fracao_ideal_str: str
    fracao_ideal_percentual: str
    cota_ordinaria_centavos: int
    fundos_centavos: Dict[str, int] = field(default_factory=dict)
    total_fundos_centavos: int = 0
    medicoes_detalhe: Dict[str, Dict[str, int]] = field(default_factory=dict)
    total_medicoes_centavos: int = 0
    total_geral_centavos: int = 0


@dataclass
class BalanceteFechamento:
    competencia: str
    nome_condominio: str
    total_unidades: int
    total_despesas_ordinarias_centavos: int
    total_fundos_centavos: int
    total_medicoes_centavos: int
    total_geral_despesas_centavos: int
    total_geral_arrecadado_centavos: int
    diferenca_fechamento_centavos: int
    conciliado: bool


@dataclass
class ResultadoRateio:
    balancete: BalanceteFechamento
    unidades: Dict[str, ResultadoUnidade]
    despesas_ordinarias: List[DespesaOrdinaria]
    fundos: List[Fundo]
    medicoes: List[MedicaoServico]
    consumos_area_comum: Dict[str, int]


def validar_e_processar_rateio(dados: dict) -> ResultadoRateio:
    """Valida a estrutura de entrada e processa o rateio completo com garantia de conservação."""
    if not isinstance(dados, dict):
        raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, "Dados de entrada devem ser um objeto JSON.")

    condominio_info = dados.get("condominio", {})
    nome_condominio = str(condominio_info.get("nome", "Condomínio Residencial"))
    competencia = str(condominio_info.get("competencia", "2026-11"))

    # 1. Validação de Unidades
    raw_unidades = dados.get("unidades")
    if not raw_unidades or not isinstance(raw_unidades, list):
        raise ErroValidacaoEntrada(ERR_UNIDADE_VAZIA, "A lista de unidades é obrigatória e não pode estar vazia.")

    unidades_map: Dict[str, Unidade] = {}
    for idx, u_data in enumerate(raw_unidades):
        if not isinstance(u_data, dict):
            raise ErroValidacaoEntrada(ERR_UNIDADE_VAZIA, f"Unidade no índice {idx} inválida.")
        uid = str(u_data.get("id", "")).strip()
        if not uid:
            raise ErroValidacaoEntrada(ERR_UNIDADE_VAZIA, f"Unidade no índice {idx} possui identificador vazio.")
        if uid in unidades_map:
            raise ErroValidacaoEntrada(ERR_UNIDADE_DUPLICADA, f"Unidade duplicada: '{uid}'.")

        num = u_data.get("fracao_ideal_numerador")
        den = u_data.get("fracao_ideal_denominador")
        if not isinstance(num, int) or not isinstance(den, int) or num <= 0 or den <= 0:
            raise ErroValidacaoEntrada(
                ERR_FRACAO_INVALIDA,
                f"Fração ideal da unidade '{uid}' deve ter numerador e denominador inteiros positivos: {num}/{den}.",
            )

        unidades_map[uid] = Unidade(
            id=uid,
            fracao_ideal_numerador=num,
            fracao_ideal_denominador=den,
            bloco=str(u_data.get("bloco", "")).strip(),
            proprietario=str(u_data.get("proprietario", "")).strip(),
            isenta_fundo_obras=bool(u_data.get("isenta_fundo_obras", False)),
            isenta_fundo_reserva=bool(u_data.get("isenta_fundo_reserva", False)),
        )

    # Verifica se a soma das frações ideais é exatamente 1 (1/1)
    soma_fracoes = sum(u.fracao for u in unidades_map.values())
    if soma_fracoes != Fraction(1, 1):
        raise ErroValidacaoEntrada(
            ERR_FRACAO_SOMA_INVALIDA,
            f"A soma das frações ideais ({soma_fracoes}) deve ser exatamente igual a 1 (1/1). Diferença: {soma_fracoes - 1}.",
        )

    # 2. Validação de Despesas Ordinárias
    raw_despesas = dados.get("despesas_ordinarias", [])
    if not isinstance(raw_despesas, list):
        raise ErroValidacaoEntrada(ERR_DESPESA_VAZIA, "Campo 'despesas_ordinarias' deve ser uma lista.")

    despesas_lista: List[DespesaOrdinaria] = []
    despesas_ids = set()
    total_despesas_ordinarias_centavos = 0

    for idx, d_data in enumerate(raw_despesas):
        if not isinstance(d_data, dict):
            raise ErroValidacaoEntrada(ERR_DESPESA_VAZIA, f"Despesa no índice {idx} inválida.")
        did = str(d_data.get("id", "")).strip()
        if not did:
            raise ErroValidacaoEntrada(ERR_DESPESA_VAZIA, f"Despesa no índice {idx} sem ID.")
        if did in despesas_ids:
            raise ErroValidacaoEntrada(ERR_DESPESA_DUPLICADA, f"Despesa ordinária duplicada: '{did}'.")
        despesas_ids.add(did)

        val = d_data.get("valor_centavos")
        if not isinstance(val, int) or val < 0:
            raise ErroValidacaoEntrada(
                ERR_VALOR_INVALIDO,
                f"Valor da despesa '{did}' deve ser um inteiro não-negativo em centavos: {val}.",
            )

        despesa_obj = DespesaOrdinaria(
            id=did,
            descricao=str(d_data.get("descricao", did)),
            categoria=str(d_data.get("categoria", "geral")),
            valor_centavos=val,
        )
        despesas_lista.append(despesa_obj)
        total_despesas_ordinarias_centavos += val

    # 3. Rateio das Despesas Ordinárias por Fração Ideal
    unidades_pesos_ordinarias = [(u.id, u.fracao) for u in unidades_map.values()]
    rateio_ordinarias = distribuir_por_maiores_restos(
        total_despesas_ordinarias_centavos,
        unidades_pesos_ordinarias,
    )

    # 4. Processamento dos Fundos
    raw_fundos = dados.get("fundos", [])
    if not isinstance(raw_fundos, list):
        raise ErroValidacaoEntrada(ERR_FUNDO_INVALIDO, "Campo 'fundos' deve ser uma lista.")

    fundos_lista: List[Fundo] = []
    rateios_fundos: Dict[str, Dict[str, int]] = {}
    total_fundos_geral_centavos = 0

    for idx, f_data in enumerate(raw_fundos):
        if not isinstance(f_data, dict):
            raise ErroValidacaoEntrada(ERR_FUNDO_INVALIDO, f"Fundo no índice {idx} inválido.")
        fid = str(f_data.get("id", "")).strip()
        if not fid:
            raise ErroValidacaoEntrada(ERR_FUNDO_INVALIDO, f"Fundo no índice {idx} sem ID.")

        tipo = str(f_data.get("tipo", "")).strip()
        fundo_obj = Fundo(
            id=fid,
            descricao=str(f_data.get("descricao", fid)),
            tipo=tipo,
            percentual_numerador=f_data.get("percentual_numerador"),
            percentual_denominador=f_data.get("percentual_denominador"),
            valor_centavos=f_data.get("valor_centavos"),
            valor_por_unidade_centavos=f_data.get("valor_por_unidade_centavos"),
        )
        fundos_lista.append(fundo_obj)

        # Determina unidades elegíveis
        if "obras" in fid.lower():
            elegiveis = [u for u in unidades_map.values() if not u.isenta_fundo_obras]
        elif "reserva" in fid.lower():
            elegiveis = [u for u in unidades_map.values() if not u.isenta_fundo_reserva]
        else:
            elegiveis = list(unidades_map.values())

        if not elegiveis:
            rateios_fundos[fid] = {u.id: 0 for u in unidades_map.values()}
            continue

        if tipo == "percentual_ordinarias":
            p_num = fundo_obj.percentual_numerador
            p_den = fundo_obj.percentual_denominador
            if not isinstance(p_num, int) or not isinstance(p_den, int) or p_num < 0 or p_den <= 0:
                raise ErroValidacaoEntrada(
                    ERR_FUNDO_INVALIDO,
                    f"Fundo '{fid}' exige percentual_numerador e percentual_denominador inteiros positivos.",
                )
            # Arredondamento do total do fundo para centavo mais próximo
            total_fundo = (total_despesas_ordinarias_centavos * p_num + p_den // 2) // p_den
            pesos_fundo = [(u.id, u.fracao) for u in elegiveis]
            rateio_f = distribuir_por_maiores_restos(total_fundo, pesos_fundo)
        elif tipo == "valor_fixo_global":
            v_fixo = fundo_obj.valor_centavos
            if not isinstance(v_fixo, int) or v_fixo < 0:
                raise ErroValidacaoEntrada(
                    ERR_FUNDO_INVALIDO,
                    f"Fundo '{fid}' exige valor_centavos inteiro não-negativo.",
                )
            total_fundo = v_fixo
            pesos_fundo = [(u.id, u.fracao) for u in elegiveis]
            rateio_f = distribuir_por_maiores_restos(total_fundo, pesos_fundo)
        elif tipo == "cota_fixa_por_unidade":
            c_unid = fundo_obj.valor_por_unidade_centavos
            if not isinstance(c_unid, int) or c_unid < 0:
                raise ErroValidacaoEntrada(
                    ERR_FUNDO_INVALIDO,
                    f"Fundo '{fid}' exige valor_por_unidade_centavos inteiro não-negativo.",
                )
            rateio_f = {u.id: c_unid for u in elegiveis}
            total_fundo = c_unid * len(elegiveis)
        else:
            raise ErroValidacaoEntrada(
                ERR_FUNDO_INVALIDO,
                f"Tipo de fundo desconhecido: '{tipo}'. Tipos válidos: percentual_ordinarias, valor_fixo_global, cota_fixa_por_unidade.",
            )

        # Completa com 0 para unidades não elegíveis
        distribuicao_completa = {u.id: rateio_f.get(u.id, 0) for u in unidades_map.values()}
        rateios_fundos[fid] = distribuicao_completa
        total_fundos_geral_centavos += total_fundo

    # 5. Processamento das Medições Individualizadas
    raw_medicoes = dados.get("medicoes", [])
    if not isinstance(raw_medicoes, list):
        raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, "Campo 'medicoes' deve ser uma lista.")

    medicoes_lista: List[MedicaoServico] = []
    consumos_area_comum: Dict[str, int] = {}
    total_medicoes_geral_centavos = 0
    # Estrutura: { unidade_id: { servico: { "consumo": int, "valor_individual": int, "valor_comum": int, "total": int } } }
    detalhes_medicoes_unidades: Dict[str, Dict[str, Dict[str, int]]] = {
        uid: {} for uid in unidades_map
    }

    for idx, m_data in enumerate(raw_medicoes):
        if not isinstance(m_data, dict):
            raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, f"Medição no índice {idx} inválida.")

        servico = str(m_data.get("servico", "")).strip().lower()
        unidade_medida = str(m_data.get("unidade_medida", "litros")).strip()
        fatura_centavos = m_data.get("valor_fatura_concessionaria_centavos", 0)
        consumo_fatura = m_data.get("consumo_fatura", 0)

        if not isinstance(fatura_centavos, int) or fatura_centavos < 0:
            raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, f"Fatura de '{servico}' inválida: {fatura_centavos}.")
        if not isinstance(consumo_fatura, int) or consumo_fatura < 0:
            raise ErroValidacaoEntrada(ERR_VALOR_INVALIDO, f"Consumo de fatura de '{servico}' inválido: {consumo_fatura}.")

        raw_leituras = m_data.get("leituras", [])
        leituras_processadas: List[LeituraMedicao] = []
        leituras_vistas = set()
        soma_consumo_individual = 0

        for l_data in raw_leituras:
            l_uid = str(l_data.get("unidade_id", "")).strip()
            if l_uid not in unidades_map:
                raise ErroValidacaoEntrada(ERR_UNIDADE_VAZIA, f"Unidade '{l_uid}' em leitura de '{servico}' não cadastrada.")
            if l_uid in leituras_vistas:
                raise ErroValidacaoEntrada(ERR_UNIDADE_DUPLICADA, f"Leitura duplicada para unidade '{l_uid}' em '{servico}'.")
            leituras_vistas.add(l_uid)

            ant = l_data.get("leitura_anterior", 0)
            atu = l_data.get("leitura_atual", 0)
            if not isinstance(ant, int) or not isinstance(atu, int) or ant < 0 or atu < ant:
                raise ErroValidacaoEntrada(
                    ERR_LEITURA_INCONSISTENTE,
                    f"Leitura inconsistente para '{l_uid}' em '{servico}': anterior={ant}, atual={atu}.",
                )

            leitura_obj = LeituraMedicao(unidade_id=l_uid, leitura_anterior=ant, leitura_atual=atu)
            leituras_processadas.append(leitura_obj)
            soma_consumo_individual += leitura_obj.consumo

        # Preenche unidades sem leitura explícita com consumo 0
        for uid in unidades_map:
            if uid not in leituras_vistas:
                leituras_processadas.append(LeituraMedicao(unidade_id=uid, leitura_anterior=0, leitura_atual=0))

        if consumo_fatura < soma_consumo_individual:
            raise ErroValidacaoEntrada(
                ERR_FATURA_CONSUMO_INSUFICIENTE,
                f"Fatura de '{servico}' com consumo ({consumo_fatura}) inferior à soma das medições individuais ({soma_consumo_individual}).",
            )

        consumo_comum = consumo_fatura - soma_consumo_individual
        consumos_area_comum[servico] = consumo_comum

        # Rateio do serviço com conservação estrita
        # Cada unidade tem peso = consumo_individual + consumo_comum * fracao_ideal
        # Note que soma(peso) = soma_consumo_individual + consumo_comum * 1 = consumo_fatura
        if consumo_fatura == 0:
            # Se não houve consumo medido na fatura, rateia eventual tarifa mínima fixa pelas frações ideais
            pesos_servico = [(u.id, u.fracao) for u in unidades_map.values()]
        else:
            map_consumo_ind = {l.unidade_id: l.consumo for l in leituras_processadas}
            pesos_servico = [
                (u.id, Fraction(map_consumo_ind[u.id]) + Fraction(consumo_comum * u.fracao))
                for u in unidades_map.values()
            ]

        rateio_servico = distribuir_por_maiores_restos(fatura_centavos, pesos_servico)

        # Decomposição em parcela própria e parcela comum para auditoria
        for u in unidades_map.values():
            total_unid_servico = rateio_servico[u.id]
            c_ind = next(l.consumo for l in leituras_processadas if l.unidade_id == u.id)
            if fatura_centavos > 0 and consumo_fatura > 0:
                # Estimativa de parcela própria
                val_proprio = (c_ind * fatura_centavos + consumo_fatura // 2) // consumo_fatura
                if val_proprio > total_unid_servico:
                    val_proprio = total_unid_servico
                val_comum = total_unid_servico - val_proprio
            else:
                val_proprio = 0
                val_comum = total_unid_servico

            detalhes_medicoes_unidades[u.id][servico] = {
                "consumo": c_ind,
                "valor_individual_centavos": val_proprio,
                "valor_area_comum_centavos": val_comum,
                "total_centavos": total_unid_servico,
            }

        medicao_obj = MedicaoServico(
            servico=servico,
            unidade_medida=unidade_medida,
            valor_fatura_concessionaria_centavos=fatura_centavos,
            consumo_fatura=consumo_fatura,
            leituras=leituras_processadas,
        )
        medicoes_lista.append(medicao_obj)
        total_medicoes_geral_centavos += fatura_centavos

    # 6. Consolidação dos Resultados por Unidade
    resultados_unidades: Dict[str, ResultadoUnidade] = {}
    total_geral_arrecadado_centavos = 0

    for uid, u in unidades_map.items():
        cota_ord = rateio_ordinarias[uid]
        f_detalhes = {fid: rateios_fundos[fid][uid] for fid in rateios_fundos}
        tot_fundos = sum(f_detalhes.values())

        m_detalhes = detalhes_medicoes_unidades[uid]
        tot_medicoes = sum(item["total_centavos"] for item in m_detalhes.values())

        tot_geral = cota_ord + tot_fundos + tot_medicoes
        total_geral_arrecadado_centavos += tot_geral

        fracao_pct_str = formatar_fracao_percentual(u.fracao, casas=4)

        resultados_unidades[uid] = ResultadoUnidade(
            unidade_id=uid,
            fracao_ideal_str=f"{u.fracao.numerator}/{u.fracao.denominator}",
            fracao_ideal_percentual=fracao_pct_str,
            cota_ordinaria_centavos=cota_ord,
            fundos_centavos=f_detalhes,
            total_fundos_centavos=tot_fundos,
            medicoes_detalhe=m_detalhes,
            total_medicoes_centavos=tot_medicoes,
            total_geral_centavos=tot_geral,
        )

    # 7. Balancete de Fechamento e Prova de Conciliação
    total_despesas_geral = (
        total_despesas_ordinarias_centavos
        + total_fundos_geral_centavos
        + total_medicoes_geral_centavos
    )
    diferenca = total_geral_arrecadado_centavos - total_despesas_geral
    conciliado = (diferenca == 0)

    balancete = BalanceteFechamento(
        competencia=competencia,
        nome_condominio=nome_condominio,
        total_unidades=len(unidades_map),
        total_despesas_ordinarias_centavos=total_despesas_ordinarias_centavos,
        total_fundos_centavos=total_fundos_geral_centavos,
        total_medicoes_centavos=total_medicoes_geral_centavos,
        total_geral_despesas_centavos=total_despesas_geral,
        total_geral_arrecadado_centavos=total_geral_arrecadado_centavos,
        diferenca_fechamento_centavos=diferenca,
        conciliado=conciliado,
    )

    return ResultadoRateio(
        balancete=balancete,
        unidades=resultados_unidades,
        despesas_ordinarias=despesas_lista,
        fundos=fundos_lista,
        medicoes=medicoes_lista,
        consumos_area_comum=consumos_area_comum,
    )
