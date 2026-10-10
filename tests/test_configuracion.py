"""
Preferencias (configuracion.py): valores por defecto, que se guardan sin perder las
demás, y que un archivo dañado o imposible de escribir no impide usar la calculadora.
"""
import json

import pytest

import configuracion as cfg
import i18n


@pytest.fixture(autouse=True)
def appdata(tmp_path, monkeypatch):
    """Cada prueba con su propia carpeta APPDATA (no toca la configuración del usuario)."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_valores_por_defecto():
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_PASOS
    assert cfg.leer(cfg.BUSCAR_ACTUALIZACIONES) is True
    assert cfg.leer(cfg.VERSION_OMITIDA) is None
    assert cfg.leer(cfg.IDIOMA) is None


def test_guardar_y_leer():
    cfg.guardar(cfg.MODO_RESPUESTA, cfg.MODO_RESULTADO)
    cfg.guardar(cfg.BUSCAR_ACTUALIZACIONES, False)
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_RESULTADO
    assert cfg.leer(cfg.BUSCAR_ACTUALIZACIONES) is False


def test_guardar_conserva_las_demas_preferencias():
    i18n.guardar_idioma("en")
    cfg.guardar(cfg.MODO_RESPUESTA, cfg.MODO_RESULTADO)
    assert i18n.idioma_guardado() == "en"
    datos = json.loads(open(cfg.ruta_configuracion(), encoding="utf-8").read())
    assert datos == {"idioma": "en", "modo_respuesta": "resultado"}


def test_config_de_versiones_anteriores_se_sigue_leyendo(appdata):
    # Hasta ahora config.json solo tenía el idioma, escrito por i18n
    carpeta = appdata / "CalculadoraAccesible"
    carpeta.mkdir()
    (carpeta / "config.json").write_text('{"idioma": "en"}', encoding="utf-8")
    assert i18n.idioma_guardado() == "en"
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_PASOS


@pytest.mark.parametrize("contenido", ["{dañado", "[1, 2]", '{"modo_respuesta": "otro"}'])
def test_archivo_danado_o_valor_invalido_da_el_valor_por_defecto(appdata, contenido):
    carpeta = appdata / "CalculadoraAccesible"
    carpeta.mkdir()
    (carpeta / "config.json").write_text(contenido, encoding="utf-8")
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_PASOS
    cfg.guardar(cfg.MODO_RESPUESTA, cfg.MODO_RESULTADO)  # y se puede volver a guardar
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_RESULTADO


def test_no_poder_guardar_no_es_un_error(appdata):
    (appdata / "CalculadoraAccesible").write_text("", encoding="utf-8")  # la "carpeta" es un archivo
    cfg.guardar(cfg.MODO_RESPUESTA, cfg.MODO_RESULTADO)
    assert cfg.leer(cfg.MODO_RESPUESTA) == cfg.MODO_PASOS


def test_i18n_conserva_ruta_configuracion():
    assert i18n.ruta_configuracion() == cfg.ruta_configuracion()
