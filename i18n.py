"""
Traducción de la interfaz y de los resultados.

El idioma de origen es el español: los textos se escriben en español en el código y
el catálogo locales/<idioma>.json da su traducción. Si falta una traducción, se
muestra el texto en español (nunca falla).

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
y N_("...") del código fuente y comprueba que todos tengan traducción.
"""
import json
import os
import sys
from typing import Dict

IDIOMA_ORIGEN = "es"
IDIOMAS = {"es": "Español", "en": "English"}

_idioma = IDIOMA_ORIGEN
_catalogo: Dict[str, str] = {}


def carpeta_recursos() -> str:
    """Carpeta de la aplicación: junto al .exe si está compilada, si no la del código."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def carpeta_locales() -> str:
    return os.path.join(carpeta_recursos(), "locales")


def cargar_catalogo(codigo: str) -> Dict[str, str]:
    if codigo == IDIOMA_ORIGEN:
        return {}
    with open(os.path.join(carpeta_locales(), f"{codigo}.json"), encoding="utf-8") as f:
        return json.load(f)


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
    return traducido.format(**valores) if valores else traducido


def N_(texto: str) -> str:
    """Marca un texto para traducir más tarde con tr(texto). Devuelve el texto tal cual."""
    return texto


# ---------------------------------------------------------
# Preferencia guardada y detección del idioma del sistema
# ---------------------------------------------------------

def ruta_configuracion() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "CalculadoraAccesible", "config.json")


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
    try:
        with open(ruta_configuracion(), encoding="utf-8") as f:
            codigo = json.load(f).get("idioma")
        return codigo if codigo in IDIOMAS else None
    except Exception:
        return None


def guardar_idioma(codigo: str) -> None:
    ruta = ruta_configuracion()
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        config = {}
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                config = json.load(f)
        config["idioma"] = codigo
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # no poder guardar la preferencia no debe impedir usar la calculadora


def iniciar_idioma() -> str:
    """Idioma al arrancar la aplicación: el guardado o, la primera vez, el del sistema."""
    codigo = idioma_guardado() or detectar_idioma_sistema()
    try:
        establecer_idioma(codigo)
    except Exception:
        establecer_idioma(IDIOMA_ORIGEN)
    return idioma_actual()
