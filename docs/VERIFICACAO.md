# Verificação Independente e Prova Matemática — rateio-condominio-fracoes

Este documento descreve os fundamentos matemáticos e o processo de auditoria independente do **rateio-condominio-fracoes**.

---

## 1. O Problema do Arredondamento Condominial

Na gestão de condomínios, a lei brasileira (Código Civil, art. 1.336, I) determina que cada condômino deve contribuir na proporção de sua **fração ideal**, salvo convenção em contrário.

Entretanto, as moedas têm menor unidade indivisível: o **centavo** ($0,01$ Real ou 1 centavo inteiro).
Quando o total de despesas a ratear $T$ multiplicado pela fração ideal $w_i = \frac{n_i}{d_i}$ resulta em um número fracionário de centavos:

$$q_i = T \times \frac{n_i}{d_i}$$

Se utilizarmos arredondamento ingênuo (como `round()`) para cada unidade isoladamente, a soma das cobranças frequentemente diverge do total de despesas aprovadas:

$$\sum_{i=1}^N \text{round}(q_i) \neq T$$

Isso cria sobras ou faltas crônicas de centavos no fechamento do caixa e contabilidade do condomínio.

---

## 2. Solução Matemática: Algoritmo dos Maiores Restos (Hare-Niemeyer / Hamilton)

Para eliminar qualquer divergência, utilizamos o método dos maiores restos com ordenação lexicográfica estável:

1. Calcula-se a quota ideal exata em números racionais:
   $$q_i = \frac{T \times w_i}{\sum w} \in \mathbb{Q}$$
2. Determina-se a parte inteira preliminar de centavos:
   $$c_i = \lfloor q_i \rfloor$$
3. Calcula-se o resto fracionário de cada unidade:
   $$r_i = q_i - c_i \quad (0 \le r_i < 1)$$
4. A soma preliminar é $S = \sum_{i=1}^N c_i$. O total de centavos indivisíveis restantes a distribuir é:
   $$R = T - S \quad (0 \le R < N)$$
5. As unidades são ordenadas pelos seguintes critérios decrescentes estritos:
   - Maior resto fracionário $r_i$
   - Maior peso $w_i$ (desempate 1)
   - Identificador lexicográfico $u_i$ em ordem alfabética crescente (desempate determinístico)
6. As primeiras $R$ unidades da lista ordenada recebem $+1$ centavo.

### Teorema da Conservação
$$\sum_{i=1}^N \text{cota\_final}_i = \sum_{i=1}^N c_i + R = S + (T - S) = T$$

A igualdade é uma identidade estrita, sem nenhum centavo ganho ou perdido.

---

## 3. Auditoria Relacional com `tools/verify_independent.py`

O script `tools/verify_independent.py` audita o arquivo ZIP sem importar o código-fonte da aplicação:

1. **Conferência de Hash:** Recalcula o SHA-256 de todos os membros do pacote e confronta com o `SHA256SUMS`.
2. **Validação das Frações:** Carrega o `entrada.json` e confere com aritmética racional pura que a soma das frações ideais fecha exatamente em $1/1$.
3. **Carga em SQLite em Memória:** Insere as tabelas `resumo-unidades.csv`, `despesas-detalhadas.csv` e `medicoes-hidrometros.csv` em tabelas relacionais independentes.
4. **Verificação de Balanço:** Executa consultas SQL `SUM()` e garante que:
   - `SUM(cota_ordinaria_centavos) == SUM(despesas_ordinarias)`
   - `SUM(total_fundos_centavos) == SUM(despesas_fundos)`
   - `SUM(total_medicoes_centavos) == SUM(medicoes_hidrometros)`
   - `SUM(total_geral_centavos) == total_geral_despesas`
   - Para cada linha, `cota_ordinaria + total_fundos + total_medicoes == total_geral`.

Se qualquer discrepância de 1 centavo for detectada, o verificador emite erro e encerra com código `1`.
