"""Módulo de exceções e códigos de erro do rateio condominial."""

from typing import Optional


class RateioError(Exception):
    """Exceção base para todas as falhas de domínio e validação."""

    def __init__(self, codigo: str, mensagem: str, detalhe: Optional[dict] = None) -> None:
        super().__init__(f"[{codigo}] {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhe = detalhe or {}


class ErroCodificacaoJSON(RateioError):
    """Falhas na decodificação ou validação estrita do JSON."""
    pass


class ErroValidacaoEntrada(RateioError):
    """Inconsistência nos dados de entrada (unidades, despesas, medições)."""
    pass


class ErroExecucao(RateioError):
    """Falhas durante o processamento, geração de relatórios ou arquivos."""
    pass


# Constantes de códigos de erro
ERR_JSON_INVALIDO = "JSON_INVALIDO"
ERR_JSON_FLOAT_PROIBIDO = "JSON_FLOAT_PROIBIDO"
ERR_JSON_CHAVE_DUPLICADA = "JSON_CHAVE_DUPLICADA"
ERR_JSON_PROFUNDIDADE_EXCEDIDA = "JSON_PROFUNDIDADE_EXCEDIDA"
ERR_JSON_BOM_PROIBIDO = "JSON_BOM_PROIBIDO"
ERR_JSON_TAMANHO_EXCEDIDO = "JSON_TAMANHO_EXCEDIDO"

ERR_UNIDADE_VAZIA = "UNIDADE_VAZIA"
ERR_UNIDADE_DUPLICADA = "UNIDADE_DUPLICADA"
ERR_FRACAO_INVALIDA = "FRACAO_INVALIDA"
ERR_FRACAO_SOMA_INVALIDA = "FRACAO_SOMA_INVALIDA"
ERR_DESPESA_VAZIA = "DESPESA_VAZIA"
ERR_DESPESA_DUPLICADA = "DESPESA_DUPLICADA"
ERR_VALOR_INVALIDO = "VALOR_INVALIDO"
ERR_LEITURA_INCONSISTENTE = "LEITURA_INCONSISTENTE"
ERR_FATURA_CONSUMO_INSUFICIENTE = "FATURA_CONSUMO_INSUFICIENTE"
ERR_FUNDO_INVALIDO = "FUNDO_INVALIDO"
ERR_ARQUIVO_EXISTENTE = "ARQUIVO_EXISTENTE"
