import os
import sys

import pytest

# Los módulos del proyecto viven en la raíz del repositorio (no es un paquete instalable)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Las pruebas comparan con los textos del código, no con locales/es.json (editable).
# Antes de importar i18n; el proceso de cálculo lo hereda.
os.environ["CALCULADORA_TEXTOS_ORIGEN"] = "1"

from puente import CoreMatematico  # noqa: E402


@pytest.fixture(scope="session")
def core():
    return CoreMatematico()


def primera_linea(texto: str) -> str:
    return texto.splitlines()[0]
