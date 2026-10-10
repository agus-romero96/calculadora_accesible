"""La autoprueba del ejecutable compilado debe pasar también desde el código fuente."""
import autoprueba


def test_autoprueba_desde_codigo_fuente(tmp_path):
    informe = tmp_path / "informe.txt"
    assert autoprueba.ejecutar(str(informe)) == 0
    contenido = informe.read_text(encoding="utf-8")
    assert "FAIL" not in contenido
    assert contenido.rstrip().endswith("16/16 correctas")
