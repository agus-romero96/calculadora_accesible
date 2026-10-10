"""
Actualizaciones automáticas desde las Releases de GitHub.

Publicar una versión nueva no requiere nada más que lo de siempre: crear la Release
en GitHub con la etiqueta vX.Y.Z y adjuntarle el instalador que genera compilar.py
(setup-calculadora-accesible-vX.Y.Z.exe). La calculadora:

  1. consulta la última Release (buscar_actualizacion; las versiones preliminares y
     los borradores no cuentan, GitHub no los devuelve como "latest");
  2. si es más nueva que _version.__version__, la ofrece (main.py);
  3. descarga el instalador a la carpeta temporal, comprobando el tamaño y el SHA-256
     que publica GitHub (descargar);
  4. lo ejecuta en modo silencioso (instalar) y se cierra; el instalador la vuelve a
     abrir al terminar (setup_script.iss, parámetro /ACTUALIZAR=1).

Este módulo no usa wx: la interfaz está en main.py y aquí todo se puede probar.
"""
import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from _version import __version__
from i18n import tr

REPOSITORIO = "agus-romero96/calculadora_accesible"
URL_ULTIMA = f"https://api.github.com/repos/{REPOSITORIO}/releases/latest"
URL_RELEASES = f"https://github.com/{REPOSITORIO}/releases"
# Nombre del instalador que genera compilar.py
PATRON_INSTALADOR = re.compile(r"^setup-calculadora-accesible-v[\w.\-]+\.exe$", re.IGNORECASE)
# Parámetros de Inno Setup: sin preguntas (solo la ventana de progreso), cerrando la
# calculadora si sigue abierta; /ACTUALIZAR=1 hace que el instalador la vuelva a abrir
PARAMETROS_INSTALADOR = "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /ACTUALIZAR=1"
TIEMPO_ESPERA = 15  # segundos sin respuesta antes de dar la consulta o la descarga por fallida
BLOQUE = 64 * 1024


class ErrorActualizacion(Exception):
    """No se pudo consultar o descargar la actualización (sin conexión, archivo dañado...)."""


class DescargaCancelada(Exception):
    pass


@dataclass(frozen=True)
class Actualizacion:
    version: str                 # "1.4.0" (sin la "v" de la etiqueta)
    notas: str                   # descripción de la Release (novedades)
    pagina: str                  # página de la Release en GitHub
    url_instalador: Optional[str] = None  # None: la Release no tiene instalador adjunto
    nombre_instalador: str = ""
    tamano: int = 0
    sha256: Optional[str] = None  # None si GitHub no publica el resumen del archivo


def version_tupla(texto: str) -> Optional[Tuple[int, ...]]:
    """'v1.10.0' -> (1, 10, 0). None si no es una versión X.Y.Z (p. ej. '1.4.0-beta')."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", (texto or "").strip())
    if not m:
        return None
    return tuple(int(parte or 0) for parte in m.groups())


def es_mas_nueva(remota: str, local: str = __version__) -> bool:
    r, l = version_tupla(remota), version_tupla(local)
    return r is not None and l is not None and r > l


def interpretar(datos: dict) -> Actualizacion:
    """La respuesta de la API de GitHub (una Release) como Actualizacion."""
    etiqueta = datos.get("tag_name") or ""
    if version_tupla(etiqueta) is None:
        raise ErrorActualizacion(tr("La versión publicada tiene una etiqueta no válida: {etiqueta}", etiqueta=etiqueta))
    version = etiqueta.lstrip("vV")
    instalador = next((a for a in datos.get("assets") or []
                       if PATRON_INSTALADOR.match(a.get("name") or "")), None)
    campos = {}
    if instalador is not None:
        resumen = instalador.get("digest") or ""  # "sha256:<hex>"
        campos = {
            "url_instalador": instalador.get("browser_download_url"),
            "nombre_instalador": instalador["name"],
            "tamano": int(instalador.get("size") or 0),
            "sha256": resumen[len("sha256:"):].lower() if resumen.startswith("sha256:") else None,
        }
    return Actualizacion(version=version, notas=(datos.get("body") or "").strip(),
                         pagina=datos.get("html_url") or URL_RELEASES, **campos)


def _abrir(url: str):
    """Abre una URL (las pruebas lo sustituyen). Lanza ErrorActualizacion si falla."""
    peticion = urllib.request.Request(url, headers={
        "User-Agent": f"CalculadoraAccesible/{__version__}",
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "*/*",
    })
    try:
        return urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ErrorActualizacion(tr("Todavía no hay versiones publicadas.")) from e
        raise ErrorActualizacion(tr("El servidor respondió con el error {codigo}.", codigo=e.code)) from e
    except (urllib.error.URLError, OSError) as e:
        motivo = getattr(e, "reason", e)
        raise ErrorActualizacion(tr("No hay conexión con GitHub ({motivo}).", motivo=motivo)) from e


def ultima_version() -> Actualizacion:
    """La última Release publicada. Lanza ErrorActualizacion si no se puede consultar."""
    try:
        with _abrir(URL_ULTIMA) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except ErrorActualizacion:
        raise
    except Exception as e:  # respuesta cortada o que no es JSON
        raise ErrorActualizacion(tr("GitHub dio una respuesta no válida ({error}).", error=e)) from e
    return interpretar(datos)


def buscar_actualizacion(version_local: str = __version__) -> Optional[Actualizacion]:
    """La última Release si es más nueva que la instalada; None si ya está al día."""
    ultima = ultima_version()
    return ultima if es_mas_nueva(ultima.version, version_local) else None


def carpeta_descargas() -> str:
    return os.path.join(tempfile.gettempdir(), "CalculadoraAccesible")


def descargar(act: Actualizacion, carpeta: Optional[str] = None,
              progreso: Optional[Callable[[int, int], bool]] = None) -> str:
    """
    Descarga el instalador y devuelve su ruta. progreso(descargado, total) se llama
    tras cada bloque; si devuelve False, se cancela (DescargaCancelada). Comprueba el
    tamaño y, si GitHub lo publica, el SHA-256: un instalador incompleto o alterado no
    se ejecuta nunca.
    """
    if not act.url_instalador:
        raise ErrorActualizacion(tr("La versión publicada no incluye el instalador."))
    if not act.url_instalador.startswith("https://"):
        raise ErrorActualizacion(tr("La dirección del instalador no es segura (no usa https)."))
    carpeta = carpeta or carpeta_descargas()
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, os.path.basename(act.nombre_instalador))
    parcial = destino + ".part"
    resumen = hashlib.sha256()
    descargado = 0
    try:
        with _abrir(act.url_instalador) as respuesta, open(parcial, "wb") as archivo:
            total = act.tamano or int(respuesta.headers.get("Content-Length") or 0)
            while True:
                bloque = respuesta.read(BLOQUE)
                if not bloque:
                    break
                archivo.write(bloque)
                resumen.update(bloque)
                descargado += len(bloque)
                if progreso is not None and progreso(descargado, total) is False:
                    raise DescargaCancelada()
        if act.tamano and descargado != act.tamano:
            raise ErrorActualizacion(tr("La descarga quedó incompleta ({descargado} de {total} bytes).",
                                         descargado=descargado, total=act.tamano))
        if act.sha256 and resumen.hexdigest() != act.sha256:
            raise ErrorActualizacion(tr("El instalador descargado no coincide con el publicado (SHA-256)."))
        os.replace(parcial, destino)
        return destino
    except (ErrorActualizacion, DescargaCancelada):
        _borrar(parcial)
        raise
    except Exception as e:  # conexión cortada a mitad, disco lleno...
        _borrar(parcial)
        raise ErrorActualizacion(tr("No se pudo descargar el instalador ({error}).", error=e)) from e


def _borrar(ruta: str) -> None:
    try:
        os.remove(ruta)
    except OSError:
        pass


def instalar(ruta_instalador: str) -> None:
    """
    Ejecuta el instalador. Windows pide permiso de administrador (UAC); si el usuario
    lo rechaza, lanza ErrorActualizacion y la calculadora sigue abierta. os.startfile
    (ShellExecute) es lo que permite esa elevación; subprocess fallaría.
    """
    try:
        os.startfile(ruta_instalador, arguments=PARAMETROS_INSTALADOR)
    except OSError as e:
        raise ErrorActualizacion(tr("No se pudo iniciar el instalador ({error}).", error=e.strerror or e)) from e
