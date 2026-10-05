import sys
from cx_Freeze import setup, Executable

# Import the version from our own file
from _version import __version__

# Define the base for the executable.
# "Win32GUI" is used for a GUI application on Windows.
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# List of files and directories to include in the build
# We need to explicitly include our math modules
include_files = [
    'aritmetica.py',
    'parser_matematico.py',
    'puente.py',
    'algebra/',
    'calculo/',
    '_version.py',
    'LICENSE',
    'README.md'
]

# Build options
# We need to make sure sympy and wx are included
build_exe_options = {
    "packages": ["wx", "sympy"],
    "include_files": include_files,
    "excludes": ["tkinter", "unittest"], # Exclude packages we don't need
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],
}

setup(
    name="Calculadora Accesible",
    version=__version__,
    description="Una calculadora científica y accesible con capacidades simbólicas.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, target_name="CalculadoraAccesible.exe")]
)
