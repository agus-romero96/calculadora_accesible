"""
Mantenimiento de los catálogos de traducción (locales/<idioma>.json).

    python -X utf8 catalogos.py              # sincroniza es.json e informa de en.json
    python -X utf8 catalogos.py --comprobar  # solo informa (código 1 si falta algo)

Los textos se escriben en español en el código, con tr("...") o N_("..."), y ese
texto es la clave de todos los catálogos:
  - es.json: la redacción que se muestra en español. Al sincronizar se añaden los
    textos nuevos (con el mismo texto del código, para editarlo después) y se quitan
    los que el código ya no usa. Lo que ya está editado no se toca.
  - en.json (y cualquier otro idioma): la traducción hay que escribirla a mano;
    aquí solo se listan las que faltan o sobran.

tests/test_i18n.py usa textos_marcados() para comprobar que los catálogos están completos.
"""
import argparse
import ast
import json
import os
import sys

from i18n import IDIOMA_ORIGEN, IDIOMAS, ruta_catalogo

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETAS_CODIGO = ["", "algebra", "calculo", os.path.join("calculo", "lim_estrategias")]
# Herramientas de desarrollo, no de la calculadora
EXCLUIR = {"setup.py", "compilar.py", "tests_limites.py", "catalogos.py"}


def archivos_codigo():
    for carpeta in CARPETAS_CODIGO:
        base = os.path.join(RAIZ, carpeta)
        for nombre in sorted(os.listdir(base)):
            if nombre.endswith(".py") and nombre not in EXCLUIR:
                yield os.path.join(base, nombre)


def textos_marcados() -> dict:
    """Primer argumento literal de cada llamada tr("...") o N_("...") del código -> archivo."""
    textos = {}
    for ruta in archivos_codigo():
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                    and nodo.func.id in ("tr", "N_") and nodo.args
                    and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str)):
                textos.setdefault(nodo.args[0].value, os.path.relpath(ruta, RAIZ))
    return textos


def leer(codigo: str) -> dict:
    ruta = ruta_catalogo(codigo)
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir(codigo: str, catalogo: dict) -> None:
    # Mismo formato que en.json: ordenado y legible, con tildes sin escapar
    with open(ruta_catalogo(codigo), "w", encoding="utf-8", newline="\n") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def sincronizar_origen(textos: dict) -> tuple:
    """Añade a es.json los textos nuevos y quita los que ya no se usan. Devuelve (añadidos, quitados)."""
    actual = leer(IDIOMA_ORIGEN)
    anadidos = sorted(set(textos) - set(actual))
    quitados = sorted(set(actual) - set(textos))
    nuevo = {texto: actual.get(texto, texto) for texto in textos}
    if anadidos or quitados:
        escribir(IDIOMA_ORIGEN, nuevo)
    return anadidos, quitados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--comprobar", action="store_true", help="no modificar es.json; solo informar")
    args = parser.parse_args()

    textos = textos_marcados()
    pendiente = False

    if args.comprobar:
        actual = leer(IDIOMA_ORIGEN)
        anadidos, quitados = sorted(set(textos) - set(actual)), sorted(set(actual) - set(textos))
        verbo_anadir, verbo_quitar = "Faltan en", "Sobran en"
        pendiente = bool(anadidos or quitados)
    else:
        anadidos, quitados = sincronizar_origen(textos)
        verbo_anadir, verbo_quitar = "Añadidos a", "Quitados de"
    for verbo, lista in ((verbo_anadir, anadidos), (verbo_quitar, quitados)):
        if lista:
            print(f"{verbo} {IDIOMA_ORIGEN}.json ({len(lista)}):")
            for texto in lista:
                print(f"  {texto!r}")

    for codigo in IDIOMAS:
        if codigo == IDIOMA_ORIGEN:
            continue
        catalogo = leer(codigo)
        faltan = sorted(set(textos) - set(catalogo))
        sobran = sorted(set(catalogo) - set(textos))
        for titulo, lista in ((f"Sin traducir en {codigo}.json", faltan), (f"Sobran en {codigo}.json", sobran)):
            if lista:
                pendiente = True
                print(f"{titulo} ({len(lista)}):")
                for texto in lista:
                    print(f"  {texto!r}  ({textos.get(texto, 'sin uso')})")

    if not pendiente and not anadidos and not quitados:
        print(f"Catálogos al día: {len(textos)} textos.")
    return 1 if pendiente else 0


if __name__ == "__main__":
    sys.exit(main())
