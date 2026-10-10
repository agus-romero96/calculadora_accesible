"""
Traducción de la interfaz y de los resultados.

El idioma de origen es el español: los textos se escriben en español en el código y
el catálogo locales/<idioma>.json da su traducción. El texto del código es solo la
clave: también el español tiene su catálogo (locales/es.json), para corregir o
mejorar la redacción sin tocar el código. Si falta una traducción, se muestra el
texto del código (nunca falla).

Uso:
    from i18n import tr, N_

    tr("Grado del numerador: {grado}", grado=3)   # traduce y rellena
    NOMBRE = N_("Regla del Producto")               # solo marca (se traduce al mostrar)
    tr(NOMBRE)

Por qué "tr" y no "_" (la convención de gettext): el código usa "_" como variable
descartable (num, _ = ...), y eso ocultaría la función de traducción.

N_ marca textos que se guardan sin traducir porque también se usan como
identificadores (por ejemplo, nombres de estrategia que se comparan en el código)
y se traducen solo al mostrarlos. tests/test_i18n.py recoge los textos de tr("...")
y N_("...") del código fuente y comprueba que todos tengan traducción; para añadir
a locales/es.json los textos nuevos, ejecute  python -X utf8 catalogos.py .

Las pruebas y la autoprueba comparan con los textos del código, no con los de
es.json (que el usuario puede cambiar): con la variable de entorno
CALCULADORA_TEXTOS_ORIGEN=1 no se carga es.json. Se hereda en el proceso de cálculo.
"""
import json
import os
import sys
from typing import Dict

import configuracion
# Se conserva aquí por compatibilidad (la configuración antes vivía en este módulo)
from configuracion import ruta_configuracion  # noqa: F401

IDIOMA_ORIGEN = "es"
IDIOMAS = {"es": "Español", "en": "English"}
# Idioma en que wxWidgets escribe sus propios textos: no necesita catálogo.
IDIOMA_WX_ORIGEN = "en"

# Variable de entorno: usar los textos del código en lugar de locales/es.json
TEXTOS_ORIGEN = "CALCULADORA_TEXTOS_ORIGEN"


def carpeta_recursos() -> str:
    """Carpeta de la aplicación: junto al .exe si está compilada, si no la del código."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def carpeta_locales() -> str:
    return os.path.join(carpeta_recursos(), "locales")


def catalogos_wx() -> list:
    """Idiomas cuyo catálogo de wxWidgets (wx/locale/<idioma>) hay que incluir en el ejecutable."""
    return [codigo for codigo in IDIOMAS if codigo != IDIOMA_WX_ORIGEN]


def ruta_catalogo(codigo: str) -> str:
    return os.path.join(carpeta_locales(), f"{codigo}.json")


def cargar_catalogo(codigo: str) -> Dict[str, str]:
    """
    Catálogo de un idioma. El del español es opcional: si falta, está dañado (por
    ejemplo, tras editarlo a mano) o se pide CALCULADORA_TEXTOS_ORIGEN, se usan los
    textos del código. El de otro idioma debe existir (si no, iniciar_idioma vuelve al español).
    """
    if codigo == IDIOMA_ORIGEN:
        if os.environ.get(TEXTOS_ORIGEN):
            return {}
        try:
            with open(ruta_catalogo(codigo), encoding="utf-8") as f:
                catalogo = json.load(f)
            return {k: v for k, v in catalogo.items() if isinstance(k, str) and isinstance(v, str)}
        except Exception:
            return {}
    with open(ruta_catalogo(codigo), encoding="utf-8") as f:
        return json.load(f)


_idioma = IDIOMA_ORIGEN
# Cargado ya al importar: el proceso de cálculo empieza en español sin llamar a establecer_idioma
_catalogo: Dict[str, str] = cargar_catalogo(IDIOMA_ORIGEN)


def establecer_idioma(codigo: str) -> None:
    global _idioma, _catalogo
    if codigo not in IDIOMAS:
        raise ValueError(f"Idioma no disponible: {codigo}")
    _catalogo = cargar_catalogo(codigo)
    _idioma = codigo


def idioma_actual() -> str:
    return _idioma


def tr(texto: str, **valores) -> str:
    """Traduce texto al idioma actual y rellena los {marcadores} con valores."""
    traducido = _catalogo.get(texto, texto)
    if not valores:
        return traducido
    try:
        return traducido.format(**valores)
    except (KeyError, IndexError, ValueError):
        # Traducción con un marcador mal escrito (los catálogos se editan a mano):
        # se muestra el texto del código antes que fallar a mitad de un cálculo
        return texto.format(**valores)


def N_(texto: str) -> str:
    """Marca un texto para traducir más tarde con tr(texto). Devuelve el texto tal cual."""
    return texto


# ---------------------------------------------------------
# Preferencia guardada y detección del idioma del sistema
# ---------------------------------------------------------

def detectar_idioma_sistema() -> str:
    """Español si Windows está en español; inglés en cualquier otro caso."""
    try:
        import ctypes
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "es" if (langid & 0x3FF) == 0x0A else "en"  # 0x0A = LANG_SPANISH
    except Exception:
        import locale
        nombre = (locale.getlocale()[0] or "").lower()
        return "es" if nombre.startswith(("es", "spanish")) else "en"


def idioma_guardado():
    codigo = configuracion.leer(configuracion.IDIOMA)
    return codigo if codigo in IDIOMAS else None


def guardar_idioma(codigo: str) -> None:
    # Si no se puede guardar, la calculadora sigue funcionando (configuracion.guardar no falla)
    configuracion.guardar(configuracion.IDIOMA, codigo)


def iniciar_idioma() -> str:
    """Idioma al arrancar la aplicación: el guardado o, la primera vez, el del sistema."""
    codigo = idioma_guardado() or detectar_idioma_sistema()
    try:
        establecer_idioma(codigo)
    except Exception:
        establecer_idioma(IDIOMA_ORIGEN)
    return idioma_actual()
