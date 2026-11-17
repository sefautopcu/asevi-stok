import ast
from pathlib import Path


def _app_tema_tercih_fonksiyonunu_yukle():
    app_yolu = Path(__file__).resolve().parents[1] / "app.py"
    agac = ast.parse(app_yolu.read_text(encoding="utf-8"))
    fonksiyon = next(
        dugum for dugum in agac.body
        if isinstance(dugum, ast.FunctionDef)
        and dugum.name == "_tema_tercihini_yukle"
    )
    modul = ast.fix_missing_locations(ast.Module(body=[fonksiyon], type_ignores=[]))
    ad_alani = {}
    exec(compile(modul, str(app_yolu), "exec"), ad_alani)
    return ad_alani["_tema_tercihini_yukle"]


def test_tema_cookie_preference_survives_reload():
    tema_yukle = _app_tema_tercih_fonksiyonunu_yukle()

    assert tema_yukle("Arctic") == "Arctic"
    assert tema_yukle("Dark") == "Dark"
    assert tema_yukle("") == "Dark"
    assert tema_yukle("unknown") == "Dark"
