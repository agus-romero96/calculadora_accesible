"""
Compila la Calculadora Accesible y genera el instalador de Windows.

    python compilar.py                   # todo: pruebas, ejecutable, autoprueba, instalador
    python compilar.py --sin-pruebas     # omite la suite de pytest
    python compilar.py --sin-instalador  # solo el ejecutable (sin Inno Setup)
    python compilar.py --salida DIR      # carpeta del instalador (por defecto: Output)

Pasos (se detiene en el primer fallo):
  1. Ejecuta la suite de pruebas (pytest).
  2. Compila el ejecutable con cx_Freeze (setup.py) en build/CalculadoraAccesible.
  3. Ejecuta el .exe compilado con --autoprueba para comprobar que el empaquetado
     incluyó todo lo necesario (SymPy carga módulos de forma dinámica).
  4. Genera el instalador con Inno Setup, pasándole la versión de _version.py.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from _version import __version__

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_BUILD = os.path.join(RAIZ, "build", "CalculadoraAccesible")
EXE = os.path.join(CARPETA_BUILD, "CalculadoraAccesible.exe")
RUTAS_ISCC = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def paso(n: int, texto: str) -> None:
    print(f"\n=== {n}. {texto} ===", flush=True)


def ejecutar(cmd, **kwargs) -> None:
    resultado = subprocess.run(cmd, cwd=RAIZ, **kwargs)
    if resultado.returncode != 0:
        sys.exit(f"\nERROR: el comando terminó con código {resultado.returncode}: {' '.join(cmd)}")


def tamano_mb(carpeta: str) -> float:
    total = 0
    for base, _, archivos in os.walk(carpeta):
        total += sum(os.path.getsize(os.path.join(base, a)) for a in archivos)
    return total / 1024 / 1024


def buscar_iscc():
    return shutil.which("ISCC") or next((r for r in RUTAS_ISCC if os.path.exists(r)), None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sin-pruebas", action="store_true", help="no ejecutar pytest")
    parser.add_argument("--sin-instalador", action="store_true", help="no generar el instalador")
    parser.add_argument("--salida", default=os.path.join(RAIZ, "Output"), help="carpeta del instalador")
    args = parser.parse_args()

    print(f"Calculadora Accesible v{__version__}")

    if not args.sin_pruebas:
        paso(1, "Pruebas (pytest)")
        ejecutar([sys.executable, "-X", "utf8", "-m", "pytest", "tests", "-q"])

    paso(2, "Ejecutable (cx_Freeze)")
    if os.path.isdir(CARPETA_BUILD):
        shutil.rmtree(CARPETA_BUILD)  # evita restos de compilaciones anteriores
    ejecutar([sys.executable, "setup.py", "build_exe"], stdout=subprocess.DEVNULL)
    print(f"Ejecutable: {EXE} ({tamano_mb(CARPETA_BUILD):.0f} MB)")

    paso(3, "Autoprueba del ejecutable compilado")
    with tempfile.TemporaryDirectory() as tmp:
        informe = os.path.join(tmp, "autoprueba.txt")
        codigo = subprocess.run([EXE, "--autoprueba", informe], timeout=300).returncode
        if os.path.exists(informe):
            with open(informe, encoding="utf-8") as f:
                print(f.read().rstrip())
        if codigo != 0:
            sys.exit("\nERROR: el ejecutable compilado no pasó la autoprueba. "
                     "Probablemente falta un módulo: revise 'excludes' en setup.py.")

    if args.sin_instalador:
        print("\nListo (sin instalador).")
        return

    paso(4, "Instalador (Inno Setup)")
    iscc = buscar_iscc()
    if not iscc:
        sys.exit("ERROR: no se encontró ISCC.exe (Inno Setup 6). Instálelo o use --sin-instalador.")
    salida = os.path.abspath(args.salida)
    instalador = os.path.join(salida, f"setup-calculadora-accesible-v{__version__}.exe")
    if os.path.exists(instalador):
        print(f"Aviso: se reemplaza el instalador existente {instalador}")
    ejecutar([iscc, "/Q", f"/DMyAppVersion={__version__}", f"/O{salida}", "setup_script.iss"])
    print(f"Instalador: {instalador} ({os.path.getsize(instalador) / 1024 / 1024:.0f} MB)")
    print("\nListo.")


if __name__ == "__main__":
    main()
