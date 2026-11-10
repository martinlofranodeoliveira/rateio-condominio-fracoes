"""rateio-condominio-fracoes: Rateio condominial determinístico por fração ideal milesimal, hidrômetros individualizados e conservação exata de centavos."""

__version__ = "1.0.0"

from .core import (
    BalanceteFechamento,
    DespesaOrdinaria,
    Fundo,
    LeituraMedicao,
    MedicaoServico,
    ResultadoRateio,
    ResultadoUnidade,
    Unidade,
    distribuir_por_maiores_restos,
    formatar_fracao_percentual,
    formatar_moeda_centavos,
    validar_e_processar_rateio,
)
from .errors import (
    ErroCodificacaoJSON,
    ErroExecucao,
    ErroValidacaoEntrada,
    RateioError,
)
from .jsoncodec import (
    codificar_json_canonico,
    decodificar_json_estrito,
)
from .reports import (
    gerar_csv_despesas_detalhadas,
    gerar_csv_medicoes_hidrometros,
    gerar_csv_resumo_unidades,
    gerar_dicionario_resultado,
    gerar_painel_svg,
    gerar_relatorio_markdown,
    publicar_pacote_zip,
    sanitizar_campo_csv,
)

__all__ = [
    "__version__",
    "RateioError",
    "ErroCodificacaoJSON",
    "ErroValidacaoEntrada",
    "ErroExecucao",
    "Unidade",
    "DespesaOrdinaria",
    "Fundo",
    "LeituraMedicao",
    "MedicaoServico",
    "ResultadoUnidade",
    "BalanceteFechamento",
    "ResultadoRateio",
    "formatar_moeda_centavos",
    "formatar_fracao_percentual",
    "distribuir_por_maiores_restos",
    "validar_e_processar_rateio",
    "decodificar_json_estrito",
    "codificar_json_canonico",
    "sanitizar_campo_csv",
    "gerar_csv_resumo_unidades",
    "gerar_csv_despesas_detalhadas",
    "gerar_csv_medicoes_hidrometros",
    "gerar_relatorio_markdown",
    "gerar_dicionario_resultado",
    "gerar_painel_svg",
    "publicar_pacote_zip",
]
