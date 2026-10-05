"""
Compilación del ejecutable con cx_Freeze.

No lo ejecute directamente: use  python compilar.py  (compila, verifica el
ejecutable con --autoprueba y genera el instalador). Ver guia_compilacion.txt.
"""
import os
import sys

import wx
from cx_Freeze import Executable, setup

from _version import __version__
from i18n import catalogos_wx

# Carpeta de salida fija (no depende de la versión de Python); setup_script.iss la usa.
CARPETA_BUILD = "build/CalculadoraAccesible"

# "Win32GUI": aplicación de ventana, sin consola que interfiera con NVDA.
base = "Win32GUI" if sys.platform == "win32" else None

build_exe_options = {
    "build_exe": CARPETA_BUILD,
    # cx_Freeze sigue los imports desde main.py; se nombran los paquetes propios
    # y las dependencias para que se incluyan completos.
    "packages": ["wx", "sympy", "mpmath", "algebra", "calculo"],
    # SymPy importa estas librerías de forma OPCIONAL si están instaladas en la máquina
    # que compila (gráficos, numpy, etc.). La calculadora no las usa y ocupaban más de
    # 100 MB del ejecutable. La autoprueba (--autoprueba) verifica que no hacen falta.
    "excludes": [
        "tkinter", "unittest", "pytest", "_pytest",
        "numpy", "scipy", "matplotlib", "PIL", "pandas",
        "numba", "llvmlite",  # llvmlite.dll sola ocupaba 102 MB
        "IPython", "jedi", "notebook", "ipykernel",
        "cryptography", "bcrypt", "fontTools", "contourpy",
        "pygments", "docutils", "sphinx",
        # Herramientas del entorno de desarrollo, no de la calculadora
        "lief", "pip", "setuptools", "redis", "jinja2", "requests", "urllib3",
        "psutil", "filelock", "win32ui", "win32com", "pythonwin", "sqlite3",
    ],
    # Archivos junto al ejecutable (el código fuente ya va compilado dentro de
    # lib/library.zip; no se copian los .py):
    #  - locales/: traducciones de la calculadora y ayuda (F1) en cada idioma.
    #  - wx_locale/: catálogo de wxWidgets para los botones de sus diálogos
    #    (Aceptar/Cancelar), uno por idioma de i18n.IDIOMAS. Dentro del zip
    #    wxWidgets no podría leerlo.
    "include_files": [
        "LICENSE", "README.md", "CHANGELOG.md", "locales",
    ] + [
        (os.path.join(os.path.dirname(wx.__file__), "locale", codigo), os.path.join("wx_locale", codigo))
        for codigo in catalogos_wx()
    ],
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],
}

setup(
    name="Calculadora Accesible",
    version=__version__,
    description="Calculadora científica y accesible con capacidades simbólicas.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, target_name="CalculadoraAccesible.exe")],
)
