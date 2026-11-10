# Documentação da API Python — rateio-condominio-fracoes

O pacote disponibiliza funções determinísticas e tipadas para consumo em código Python 3.11+.

---

## 1. Importação Principal

```python
from rateio_condominio_fracoes import (
    validar_e_processar_rateio,
    decodificar_json_estrito,
    codificar_json_canonico,
    distribuir_por_maiores_restos,
    formatar_moeda_centavos,
    formatar_fracao_percentual,
    ResultadoRateio,
    BalanceteFechamento,
    ResultadoUnidade,
)
```

---

## 2. Funções Principais

### `validar_e_processar_rateio(dados: dict) -> ResultadoRateio`
Valida o dicionário de entrada, calcula as quotas das despesas ordinárias, aplica fundos com elegibilidade, rateia faturas de concessionárias com hidrometria e área comum, e consolida o balancete final.

```python
dados = {
    "condominio": {"nome": "Edifício Solar", "competencia": "2026-11"},
    "unidades": [
        {"id": "AP-01", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
        {"id": "AP-02", "fracao_ideal_numerador": 1, "fracao_ideal_denominador": 2},
    ],
    "despesas_ordinarias": [
        {"id": "D1", "descricao": "Portaria", "categoria": "pessoal", "valor_centavos": 200000}
    ]
}

resultado = validar_e_processar_rateio(dados)
print(resultado.balancete.conciliado)  # True
print(resultado.unidades["AP-01"].cota_ordinaria_centavos)  # 100000
```

### `distribuir_por_maiores_restos(total_centavos: int, unidades_pesos: List[Tuple[str, Fraction]]) -> Dict[str, int]`
Distribui qualquer valor inteiro em centavos pelo algoritmo de Hamilton / Hare-Niemeyer garantindo conservação estrita e desempate determinístico.

```python
from fractions import Fraction

pesos = [("U1", Fraction(1, 3)), ("U2", Fraction(1, 3)), ("U3", Fraction(1, 3))]
dist = distribuir_por_maiores_restos(100, pesos)
# dist -> {"U1": 34, "U2": 33, "U3": 33}
# sum(dist.values()) == 100
```

### `formatar_moeda_centavos(centavos: int) -> str`
Converte valor inteiro em centavos para string formatada em moeda brasileira:
```python
formatar_moeda_centavos(150000)  # "R$ 1.500,00"
formatar_moeda_centavos(-75)     # "-R$ 0,75"
```

### `formatar_fracao_percentual(fracao: Fraction, casas: int = 4) -> str`
Converte `fractions.Fraction` para percentual formatado com casas decimais configuráveis usando apenas aritmética inteira:
```python
formatar_fracao_percentual(Fraction(45231, 1000000), casas=4)  # "4,5231%"
```

---

## 3. Estruturas de Dados

- `ResultadoRateio`: Objeto consolidado contendo `balancete`, `unidades`, `despesas_ordinarias`, `fundos`, `medicoes` e `consumos_area_comum`.
- `BalanceteFechamento`: Dados gerais do condomínio, total de ordinárias, fundos, medições, total arrecadado, diferença e flag `conciliado`.
- `ResultadoUnidade`: Detalhes da unidade, fração ideal, cota ordinária, dicionário de fundos, medições e total geral da cota.
