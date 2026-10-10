"""
Pasos de una explicación de cálculo (derivadas, integrales) y su texto.

Un paso tiene un título y, según el motor que lo genera:
  - una descripción y una fórmula (integrales), o
  - el desglose de una regla (derivadas), una línea por parte, en este orden:
      Regla:        la regla general, antes de aplicarla
      En este caso: qué parte de la expresión es cada pieza de la regla
      (cálculo)     la sustitución y las cuentas intermedias, una por línea
      Queda:        la expresión tras el paso
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from i18n import tr


@dataclass(frozen=True)
class PasoCalculo:
    titulo: str
    descripcion: str = ""
    expresion_matematica: str = ""
    regla: str = ""
    partes: str = ""
    calculo: Tuple[str, ...] = ()
    queda: str = ""


def texto_paso(numero: int, paso: PasoCalculo) -> str:
    """El paso numerado; cada línea añadida va sangrada para leerla con las flechas."""
    lineas: List[str] = [f"{numero}. {tr(paso.titulo)}."]
    if paso.descripcion:
        lineas[0] += f" {tr(paso.descripcion)}"
    if paso.expresion_matematica:
        lineas.append(tr("[Fórmula]: {formula}", formula=paso.expresion_matematica))
    if paso.regla:
        lineas.append(tr("Regla: {regla}", regla=paso.regla))
    if paso.partes:
        lineas.append(tr("En este caso: {partes}", partes=paso.partes))
    lineas.extend(paso.calculo)
    if paso.queda:
        lineas.append(tr("Queda: {expresion}", expresion=paso.queda))
    return "\n   ".join(lineas)
