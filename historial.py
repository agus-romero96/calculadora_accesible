"""
Historial de operaciones.

Guarda los resultados correctos (ResultadoOperacion) en orden cronológico para
volver a verlos, reutilizar su entrada, copiarlos o exportarlos todos juntos.
Si se le da una ruta, se guarda en disco tras cada cambio y se recupera al abrir
la calculadora (ruta_historial(), junto a la configuración).
"""
import base64
import json
import os
from typing import List, Optional

import serializacion
from exportar import nombre_operacion, resultado_corto
from configuracion import ruta_configuracion
from i18n import tr
from puente import OPERACIONES, ResultadoOperacion

LARGO_MAXIMO_RESUMEN = 80
VERSION_ARCHIVO = 1


def ruta_historial() -> str:
    return os.path.join(os.path.dirname(ruta_configuracion()), "historial.json")


class Historial:
    # Límite para que una sesión muy larga no crezca sin control (se descartan las más antiguas)
    MAXIMO = 200

    def __init__(self, ruta: Optional[str] = None):
        self.ruta = ruta  # None: solo en memoria (pruebas)
        self._entradas: List[ResultadoOperacion] = []  # de la más antigua a la más reciente
        if ruta:
            self._entradas = cargar(ruta)[-self.MAXIMO:]

    def agregar(self, res: ResultadoOperacion) -> None:
        if res.es_error:
            return
        self._entradas.append(res)
        del self._entradas[:-self.MAXIMO]
        self._guardar()

    def entradas(self) -> List[ResultadoOperacion]:
        """Copia de las operaciones, de la más antigua a la más reciente."""
        return list(self._entradas)

    def numero(self, res: ResultadoOperacion) -> int:
        """Número de la operación (1 = la más antigua), el mismo que en el historial exportado."""
        return next(i for i, r in enumerate(self._entradas, 1) if r is res)

    def eliminar(self, res: ResultadoOperacion) -> None:
        self._entradas = [r for r in self._entradas if r is not res]
        self._guardar()

    def vaciar(self) -> None:
        self._entradas.clear()
        self._guardar()

    def __len__(self) -> int:
        return len(self._entradas)

    def _guardar(self) -> None:
        if self.ruta:
            guardar(self._entradas, self.ruta)


# ---------------------------------------------------------
# Archivo del historial
# ---------------------------------------------------------
# JSON con los textos legibles; los objetos SymPy (valor, expresión, planteamiento)
# van serializados con pickle en base64 (serializacion.py). Se usa pickle y no srepr porque
# el planteamiento está sin evaluar ("1/6 + 1/3", Eq(y, y)) y hay que recuperarlo tal cual.
# El archivo está en la carpeta del propio usuario, como la configuración.

# Alias: el pickler "sin evaluar" está en serializacion.py (también lo usa el proceso de cálculo).
# _sin_evaluar debe seguir aquí: los historiales guardados antes del cambio lo nombran
# como "historial._sin_evaluar" dentro del pickle.
_Pickler = serializacion._Pickler
_sin_evaluar = serializacion._sin_evaluar


def _a_pickle(objeto) -> str:
    return base64.b64encode(serializacion.a_bytes(objeto)).decode("ascii")


def _de_pickle(texto: str):
    return serializacion.de_bytes(base64.b64decode(texto))


def _a_dict(res: ResultadoOperacion) -> dict:
    try:
        objetos = _a_pickle({"valor": res.valor, "expresion": res.expresion,
                             "planteamiento": res.planteamiento})
    except Exception:
        objetos = None  # una entrada que no se puede serializar no impide guardar las demás
    return {
        "operacion": res.operacion, "entrada": res.entrada, "texto": res.texto,
        "parametros": res.parametros, "mas_constante": res.mas_constante,
        "idioma": res.idioma, "fecha": res.fecha, "sympy": objetos,
    }


def _de_dict(datos: dict) -> ResultadoOperacion:
    if datos["operacion"] not in OPERACIONES:
        raise ValueError(datos["operacion"])
    try:
        objetos = _de_pickle(datos["sympy"]) if datos.get("sympy") else {}
    except Exception:
        # Por ejemplo, tras actualizar SymPy: se conserva el texto (se puede ver, reutilizar y
        # exportar), aunque sin las fórmulas para LaTeX/MathML
        objetos = {}
    return ResultadoOperacion(
        operacion=datos["operacion"], entrada=datos["entrada"], texto=datos["texto"],
        parametros=dict(datos.get("parametros") or {}), mas_constante=bool(datos.get("mas_constante")),
        idioma=datos["idioma"], fecha=datos["fecha"],
        valor=objetos.get("valor"), expresion=objetos.get("expresion"),
        planteamiento=objetos.get("planteamiento"))


def guardar(entradas: List[ResultadoOperacion], ruta: str) -> None:
    """Escribe el historial en disco. Si no se puede, la calculadora sigue funcionando."""
    try:
        contenido = json.dumps({"version": VERSION_ARCHIVO, "entradas": [_a_dict(r) for r in entradas]},
                               ensure_ascii=False, indent=1)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        # Escritura atómica: si se corta a medias, el historial anterior queda intacto
        temporal = ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            f.write(contenido)
        os.replace(temporal, ruta)
    except Exception:
        pass


def cargar(ruta: str) -> List[ResultadoOperacion]:
    """Lee el historial guardado; las entradas dañadas se descartan y un archivo ilegible da []."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        if datos.get("version") != VERSION_ARCHIVO:
            return []
        entradas = datos["entradas"]
    except Exception:
        return []
    resultado = []
    for datos_entrada in entradas:
        try:
            resultado.append(_de_dict(datos_entrada))
        except Exception:
            continue
    return resultado


def describir(res: ResultadoOperacion, numero: int) -> str:
    """Una línea para la lista del historial: número, operación, entrada y resultado."""
    resultado = resultado_corto(res)
    if len(resultado) > LARGO_MAXIMO_RESUMEN:
        resultado = resultado[:LARGO_MAXIMO_RESUMEN] + "…"
    return tr("{numero}. {operacion}: {entrada} → {resultado}",
              numero=numero, operacion=nombre_operacion(res),
              entrada=res.entrada.replace("\n", "; "), resultado=resultado)
