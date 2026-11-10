# Guia de Interoperabilidade — rateio-condominio-fracoes

Este documento orienta a integração do **rateio-condominio-fracoes** com sistemas de gestão condominial, ERPs contábeis, emissores de boletos/Pix e planilhas eletrônicas.

---

## 1. Integração com ERPs e Sistemas Financeiros

O artefato `rateio.json` gerado na execução disponibiliza a memória de cálculo completa indexada por `unidade_id`, compatível com importação direta via REST API, Webhooks ou rotinas de lote (CRON).

### Exemplo de Consumo em Python

```python
import json
from pathlib import Path

dados = json.loads(Path("rateio.json").read_text(encoding="utf-8"))
balancete = dados["balancete"]

print(f"Competência: {balancete['competencia']}")
print(f"Total arrecadado: {balancete['total_geral_arrecadado_centavos']} centavos")

for uid, info in dados["unidades"].items():
    print(f"Unidade {uid}: cota total = R$ {info['total_geral_centavos'] / 100:.2f}")
```

---

## 2. Emissão de Boletos e Cobranças Bancárias

Para emissão de boletos registrados (CNAB 240 / CNAB 400) ou cobranças Pix dinâmico:

1. O campo `total_geral_centavos` de `resumo-unidades.csv` corresponde exatamente ao valor nominal do título bancário (valor em centavos exigido pelas APIs bancárias de Febraban, Banco do Brasil, Itaú, Bradesco, Santander e Caixa).
2. O demonstrativo de cálculo discriminado por rubrica (`cota_ordinaria_formatada`, `total_fundos_formatado`, `total_medicoes_formatado`) pode ser injetado diretamente nas linhas de instrução e corpo do boleto para transparência total ao condômino.

---

## 3. Segurança em Planilhas Eletrônicas (Excel, LibreOffice, Google Sheets)

Os relatórios exportados em formato CSV contam com proteção nativa contra injeção de fórmulas (*CSV/Formula Injection*). Se qualquer identificador de unidade, descrição de despesa ou texto iniciar com os caracteres `=`, `+`, `-`, `@`, `\t` ou `\r`, o valor é automaticamente prefixado com apóstrofo `'`, impedindo a execução arbitrária de macros ou comandos DDE no computador do operador.

---

## 4. Integração via Linha de Comando (CLI)

O utilitário pode ser executado em pipelines de CI/CD ou agendadores de tarefas do sistema operacional:

```bash
# Validação antes do fechamento
rateio-condominio-fracoes verificar -i entrada.json

# Processamento e exportação de todos os artefatos
rateio-condominio-fracoes processar \
  -i entrada.json \
  -d ./fechamento-2026-11 \
  -z ./fechamento-2026-11/pacote-fechamento.zip
```
