"""
Actualizaciones (actualizador.py), sin red: _abrir se sustituye por respuestas simuladas
de la API de GitHub y de la descarga del instalador.
"""
import hashlib
import io
import json
import os
import re

import pytest

import actualizador as act
from _version import __version__

INSTALADOR = b"MZ" + b"instalador de prueba " * 10000  # unos 200 KB: varios bloques


def release(etiqueta="v9.0.0", contenido=INSTALADOR, digest=True, nombre=None, **extra):
    """Respuesta de GitHub para /releases/latest con el instalador adjunto."""
    nombre = nombre or f"setup-calculadora-accesible-{etiqueta}.exe"
    activo = {
        "name": nombre, "size": len(contenido),
        "browser_download_url": f"https://github.com/x/y/releases/download/{etiqueta}/{nombre}",
        "digest": "sha256:" + hashlib.sha256(contenido).hexdigest() if digest else None,
    }
    datos = {"tag_name": etiqueta, "body": "- Novedad", "html_url": f"https://github.com/x/y/releases/tag/{etiqueta}",
             "assets": [{"name": "codigo.zip", "size": 1, "browser_download_url": "https://x/codigo.zip"}, activo]}
    datos.update(extra)
    return datos


class Respuesta(io.BytesIO):
    def __init__(self, datos: bytes):
        super().__init__(datos)
        self.headers = {"Content-Length": str(len(datos))}


@pytest.fixture
def servidor(monkeypatch):
    """Sustituye la red: rutas[url] = bytes a devolver o excepción a lanzar."""
    rutas = {}

    def abrir(url):
        respuesta = rutas[url]
        if isinstance(respuesta, Exception):
            raise respuesta
        return Respuesta(respuesta)

    monkeypatch.setattr(act, "_abrir", abrir)
    return rutas


# ---------------- Versiones ----------------

@pytest.mark.parametrize("texto, tupla", [
    ("v1.3.0", (1, 3, 0)), ("1.10.2", (1, 10, 2)), ("v2.0", (2, 0, 0)), (" v1.4.0 ", (1, 4, 0)),
    ("v1.4.0-beta", None), ("latest", None), ("", None), (None, None),
])
def test_version_tupla(texto, tupla):
    assert act.version_tupla(texto) == tupla


@pytest.mark.parametrize("remota, local, nueva", [
    ("v1.4.0", "1.3.0", True), ("v1.10.0", "1.9.0", True),  # numérica, no alfabética
    ("v1.3.0", "1.3.0", False), ("v1.2.9", "1.3.0", False), ("v2.0", "1.99.99", True),
    ("v1.4.0-rc1", "1.3.0", False),
])
def test_es_mas_nueva(remota, local, nueva):
    assert act.es_mas_nueva(remota, local) is nueva


def test_version_actual_valida():
    assert act.version_tupla(__version__) is not None


# ---------------- Consultar la última versión ----------------

def test_interpretar_release():
    a = act.interpretar(release("v1.4.0"))
    assert a.version == "1.4.0"
    assert a.notas == "- Novedad"
    assert a.nombre_instalador == "setup-calculadora-accesible-v1.4.0.exe"  # no el .zip
    assert a.tamano == len(INSTALADOR)
    assert a.sha256 == hashlib.sha256(INSTALADOR).hexdigest()


def test_interpretar_release_sin_instalador_ni_digest():
    datos = release("v1.4.0", digest=False)
    assert act.interpretar(datos).sha256 is None
    datos["assets"] = datos["assets"][:1]
    sin_instalador = act.interpretar(datos)
    assert sin_instalador.url_instalador is None and sin_instalador.pagina.endswith("v1.4.0")


def test_etiqueta_no_valida():
    with pytest.raises(act.ErrorActualizacion):
        act.interpretar(release("ultima"))


def test_patron_coincide_con_el_instalador_de_compilar():
    """compilar.py nombra el instalador así; si cambia, el actualizador no lo encontraría."""
    fuente = open(os.path.join(os.path.dirname(act.__file__), "compilar.py"), encoding="utf-8").read()
    plantilla = re.search(r'f"(setup-calculadora-accesible-v\{__version__\}\.exe)"', fuente).group(1)
    assert act.PATRON_INSTALADOR.match(plantilla.replace("{__version__}", "1.4.0"))


def test_buscar_actualizacion(servidor):
    servidor[act.URL_ULTIMA] = json.dumps(release("v9.0.0")).encode()
    assert act.buscar_actualizacion("1.3.0").version == "9.0.0"
    assert act.buscar_actualizacion("9.0.0") is None


def test_respuesta_no_json(servidor):
    servidor[act.URL_ULTIMA] = b"<html>"
    with pytest.raises(act.ErrorActualizacion):
        act.buscar_actualizacion()


def test_sin_conexion(servidor):
    servidor[act.URL_ULTIMA] = act.ErrorActualizacion("sin red")
    with pytest.raises(act.ErrorActualizacion):
        act.buscar_actualizacion()


def test_abrir_traduce_los_errores_de_red(monkeypatch):
    import urllib.error

    def falla(*a, **k):
        raise urllib.error.URLError("getaddrinfo failed")

    monkeypatch.setattr(act.urllib.request, "urlopen", falla)
    with pytest.raises(act.ErrorActualizacion, match="getaddrinfo"):
        act._abrir(act.URL_ULTIMA)


# ---------------- Descargar ----------------

def preparar(servidor, contenido=INSTALADOR, **kwargs):
    a = act.interpretar(release("v9.0.0", **kwargs))
    servidor[a.url_instalador] = contenido
    return a


def test_descargar_verifica_y_devuelve_la_ruta(servidor, tmp_path):
    a = preparar(servidor)
    avances = []
    ruta = act.descargar(a, str(tmp_path), progreso=lambda d, t: avances.append((d, t)) or True)
    assert open(ruta, "rb").read() == INSTALADOR
    assert os.path.basename(ruta) == "setup-calculadora-accesible-v9.0.0.exe"
    assert len(avances) > 1 and avances[-1] == (len(INSTALADOR), len(INSTALADOR))
    assert os.listdir(tmp_path) == [os.path.basename(ruta)]  # sin el .part


def test_descarga_alterada_se_rechaza(servidor, tmp_path):
    a = preparar(servidor, contenido=INSTALADOR[:-1] + b"X")
    with pytest.raises(act.ErrorActualizacion, match="SHA-256"):
        act.descargar(a, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_descarga_incompleta_se_rechaza(servidor, tmp_path):
    a = preparar(servidor, contenido=INSTALADOR[:1000])
    with pytest.raises(act.ErrorActualizacion, match="incompleta"):
        act.descargar(a, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_sin_digest_se_comprueba_el_tamano(servidor, tmp_path):
    a = preparar(servidor, digest=False)
    assert open(act.descargar(a, str(tmp_path)), "rb").read() == INSTALADOR


def test_cancelar_la_descarga(servidor, tmp_path):
    a = preparar(servidor)
    with pytest.raises(act.DescargaCancelada):
        act.descargar(a, str(tmp_path), progreso=lambda d, t: d < 100000)
    assert os.listdir(tmp_path) == []


def test_conexion_cortada(servidor, tmp_path, monkeypatch):
    a = preparar(servidor)

    class Cortada(Respuesta):
        def read(self, n=-1):
            raise ConnectionResetError("cortada")

    monkeypatch.setattr(act, "_abrir", lambda url: Cortada(b""))
    with pytest.raises(act.ErrorActualizacion, match="cortada"):
        act.descargar(a, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_solo_https(tmp_path):
    a = act.Actualizacion("9.0.0", "", "", url_instalador="http://ejemplo/setup.exe",
                          nombre_instalador="setup.exe")
    with pytest.raises(act.ErrorActualizacion, match="https"):
        act.descargar(a, str(tmp_path))


def test_sin_instalador(tmp_path):
    with pytest.raises(act.ErrorActualizacion):
        act.descargar(act.Actualizacion("9.0.0", "", ""), str(tmp_path))


# ---------------- Instalar ----------------

def test_instalar_lanza_el_instalador_en_modo_silencioso(monkeypatch):
    llamadas = []
    monkeypatch.setattr(act.os, "startfile", lambda ruta, arguments: llamadas.append((ruta, arguments)),
                        raising=False)
    act.instalar("C:\\tmp\\setup.exe")
    ruta, argumentos = llamadas[0]
    assert ruta == "C:\\tmp\\setup.exe"
    assert "/SILENT" in argumentos and "/ACTUALIZAR=1" in argumentos


def test_permiso_rechazado(monkeypatch):
    def rechazar(ruta, arguments):
        raise OSError(1223, "La operación fue cancelada por el usuario")

    monkeypatch.setattr(act.os, "startfile", rechazar, raising=False)
    with pytest.raises(act.ErrorActualizacion, match="cancelada"):
        act.instalar("setup.exe")


def test_el_instalador_vuelve_a_abrir_la_calculadora():
    """setup_script.iss reconoce el parámetro /ACTUALIZAR=1 que pasa instalar()."""
    iss = open(os.path.join(os.path.dirname(act.__file__), "setup_script.iss"), encoding="utf-8").read()
    assert "{param:ACTUALIZAR|0}" in iss and "Check: EsActualizacion" in iss
