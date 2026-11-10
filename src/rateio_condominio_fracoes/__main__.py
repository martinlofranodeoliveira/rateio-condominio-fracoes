"""Ponto de entrada quando executado via python -m rateio_condominio_fracoes."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
