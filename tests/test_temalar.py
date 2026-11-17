import ast
from pathlib import Path


def _app_tema_tanimlarini_yukle():
    app_yolu = Path(__file__).resolve().parents[1] / "app.py"
    agac = ast.parse(app_yolu.read_text(encoding="utf-8"))
    hedefler = []
    for dugum in agac.body:
        if isinstance(dugum, ast.Assign) and any(
            isinstance(hedef, ast.Name) and hedef.id == "ARCTIC_HARBOR_COLORS"
            for hedef in dugum.targets
        ):
            hedefler.append(dugum)
        elif isinstance(dugum, ast.FunctionDef) and dugum.name == "arctic_harbor_renk_kartlari_html":
            hedefler.append(dugum)

    modul = ast.fix_missing_locations(ast.Module(body=hedefler, type_ignores=[]))
    ad_alani = {}
    exec(compile(modul, str(app_yolu), "exec"), ad_alani)
    return ad_alani


def test_arctic_harbor_paleti_ve_kartlari():
    renkler = (
        "#08131F",
        "#16314A",
        "#2E4F6B",
        "#5F7F98",
        "#A9BDC9",
        "#E8EFF3",
    )

    app_tema = _app_tema_tanimlarini_yukle()
    assert app_tema["ARCTIC_HARBOR_COLORS"] == renkler

    kartlar = app_tema["arctic_harbor_renk_kartlari_html"]()
    assert kartlar.count("<div") == len(renkler) + 1
    assert all(renk in kartlar for renk in renkler)
