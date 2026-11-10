# Especificação de Formato — rateio-condominio-fracoes

Este documento detalha o formato canônico de entrada e as estruturas geradas pelo **rateio-condominio-fracoes**.

---

## 1. Entrada Canônica (JSON UTF-8)

O arquivo de entrada deve ser codificado em **UTF-8 estrito** sem BOM (*Byte Order Mark*), com tamanho máximo de 10 MiB e profundidade máxima de aninhamento de 32 níveis. Valores em moeda devem ser expressos estritamente em **centavos inteiros** (`int`), e volumes em **litros ou $m^3$ inteiros** (`int`). O uso de números de ponto flutuante (`float`) é terminantemente proibido e resulta na falha com código `JSON_FLOAT_PROIBIDO`.

### Estrutura Raiz

```json
{
  "condominio": {
    "nome": "string (obrigatório)",
    "competencia": "string YYYY-MM (obrigatório)"
  },
  "unidades": [
    {
      "id": "string (obrigatório, único)",
      "fracao_ideal_numerador": "int > 0 (obrigatório)",
      "fracao_ideal_denominador": "int > 0 (obrigatório)",
      "bloco": "string (opcional)",
      "proprietario": "string (opcional)",
      "isenta_fundo_obras": "bool (opcional, padrão false)",
      "isenta_fundo_reserva": "bool (opcional, padrão false)"
    }
  ],
  "despesas_ordinarias": [
    {
      "id": "string (obrigatório, único)",
      "descricao": "string (obrigatório)",
      "categoria": "string (pessoal, manutencao, consumo, seguros, administracao, materiais, etc.)",
      "valor_centavos": "int >= 0 (obrigatório)"
    }
  ],
  "fundos": [
    {
      "id": "string (obrigatório, único)",
      "descricao": "string (obrigatório)",
      "tipo": "string ('percentual_ordinarias' | 'valor_fixo_global' | 'cota_fixa_por_unidade')",
      "percentual_numerador": "int > 0 (obrigatório se tipo for percentual_ordinarias)",
      "percentual_denominador": "int > 0 (obrigatório se tipo for percentual_ordinarias)",
      "valor_centavos": "int >= 0 (obrigatório se tipo for valor_fixo_global)",
      "valor_por_unidade_centavos": "int >= 0 (obrigatório se tipo for cota_fixa_por_unidade)"
    }
  ],
  "medicoes": [
    {
      "servico": "string ('agua' | 'gas')",
      "unidade_medida": "string ('m3' | 'litros')",
      "valor_fatura_concessionaria_centavos": "int >= 0",
      "consumo_fatura": "int >= soma das leituras individuais",
      "leituras": [
        {
          "unidade_id": "string (referência a unidades.id)",
          "leitura_anterior": "int >= 0",
          "leitura_atual": "int >= leitura_anterior"
        }
      ]
    }
  ]
}
```

### Regras de Validação do Negócio

1. **Soma das Frações Ideais:**
   $$\sum_{u \in \text{unidades}} \frac{\text{numerador}_u}{\text{denominador}_u} \equiv 1$$
   Qualquer divergência é rejeitada com código `FRACAO_SOMA_INVALIDA`.
2. **Consistência de Hidrômetros:**
   Para cada leitura, $\text{leitura\_atual} \ge \text{leitura\_anterior}$.
   O volume medido na fatura deve ser maior ou igual à soma das medições individuais:
   $$\text{consumo\_fatura} \ge \sum \text{consumo\_individual}$$
   A diferença é tratada como consumo de área comum e rateada pelas frações ideais.

---

## 2. Artefatos de Saída

Ao executar o comando `processar`, os seguintes artefatos são gerados de forma determinística:

1. `resumo-unidades.csv`: Tabela consolidada com ID, fração ideal, percentual, cota ordinária, fundos, medições e total geral por unidade.
2. `despesas-detalhadas.csv`: Listagem de cada despesa ordinária e fundo rateado.
3. `medicoes-hidrometros.csv`: Leituras de medidores com decomposição de valor individual e cota de área comum.
4. `relatorio-fechamento.md`: Demonstrativo analítico com tabelas de balancete e resumo de arrecadação.
5. `painel-rateio.svg`: Painel vetorial analítico em resolução 1440×900 com resumo financeiro e gráficos das unidades.
6. `rateio.json`: Memória de cálculo estruturada para integração com sistemas de retaguarda.
7. `SHA256SUMS`: Manifesto criptográfico SHA-256 de todos os artefatos gerados.
8. `exemplo-rateio.zip`: Pacote ZIP determinístico com garantia de não sobrescrita atômica.
