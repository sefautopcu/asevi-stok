import ast
import datetime
from pathlib import Path


def _dashboard_skt_helper():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "dashboard_skt_sayilarini_hesapla"
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[function], type_ignores=[])
    )
    namespace = {"datetime": datetime}
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace["dashboard_skt_sayilarini_hesapla"]


def test_dashboard_skt_sadece_kalan_stogu_olan_urunleri_sayar():
    bugun = datetime.date(2026, 11, 19)
    girisler = [
        {"urun": "Yoğurt", "kalan": 0, "skt": "2026-11-18"},
        {"urun": "Arpa", "kalan": 2, "skt": "2026-11-18"},
        {"urun": "ARPA", "kalan": 1, "skt": "2026-11-17"},
        {"urun": "Peynir", "kalan": 0, "skt": "2026-11-18"},
        {"urun": "Peynir", "kalan": 3, "skt": "2026-11-23"},
        {"urun": "Süt", "kalan": 2, "skt": "2026-11-21"},
        {"urun": "SÜT", "kalan": 1, "skt": "2026-11-25"},
    ]

    assert _dashboard_skt_helper()(girisler, bugun) == (1, 2)
