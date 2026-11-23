import ast
from pathlib import Path


def _page_editor_helpers():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    names = {
        "ARAYUZ_SAYFA_AYARLARI_ID",
        "SAYFA_GRUPLARI",
        "VARSAYILAN_BASLIK_RENKLERI",
        "SAYFA_VARSAYILAN_BASLIKLARI",
    }
    functions = {
        "_arayuz_renk_kodu_gecerli_mi",
        "_arayuz_sayisini_sinirla",
        "arayuz_sayfa_ayarlarini_duzenle",
        "arayuz_sayfa_ayari_al",
        "sayfa_baslik_metnini_al",
    }
    body = [
        node for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id in names
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.FunctionDef) and node.name in functions
        )
    ]
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    namespace = {}
    exec(compile(module, str(app_path), "exec"), namespace)
    return (
        namespace["arayuz_sayfa_ayarlarini_duzenle"],
        namespace["arayuz_sayfa_ayari_al"],
    )


def test_page_editor_preserves_layout_and_heading_preferences():
    normalize, get_page = _page_editor_helpers()
    settings = normalize(
        {
            "sayfalar": {
                "Güncel Stok Durumu": {
                    "etiket": "Stoklarım",
                    "baslik_metni": "",
                    "grup": "📦 Depo & Stok Yönetimi",
                    "sira": "3",
                    "gorunur": False,
                    "baslik_renkleri": ["#112233", "#223344", "#334455", "#445566"],
                    "baslik_puntosu": 42,
                }
            }
        }
    )

    assert get_page(settings, "Güncel Stok Durumu") == {
        "etiket": "Stoklarım",
        "baslik_metni": "",
        "grup": "📦 Depo & Stok Yönetimi",
        "sira": 3,
        "gorunur": False,
        "baslik_renkleri": ["#112233", "#223344", "#334455", "#445566"],
        "baslik_puntosu": 42,
    }


def test_page_editor_sanitizes_invalid_style_and_custom_page_blocks():
    normalize, get_page = _page_editor_helpers()
    settings = normalize(
        {
            "sayfalar": {
                "Güncel Stok Durumu": {
                    "sira": "not-a-number",
                    "baslik_puntosu": 500,
                    "baslik_renkleri": ["red", "#123456", "#abcdef", "#000000"],
                }
            },
            "ozel_sayfalar": [
                {
                    "id": "ozel-0123456789abcdef",
                    "baslik": "  Bilgilendirme  ",
                    "grup": "⚙️ Sistem Ayarları",
                    "bloklar": [
                        {"tur": "baslik", "metin": "Günlük duyuru"},
                        {"tur": "script", "metin": "yürütülmemeli"},
                        {"tur": "metin", "metin": "Açıklama"},
                    ],
                },
                {
                    "id": "ozel-gecersiz!",
                    "baslik": "Geçersiz",
                    "bloklar": [],
                },
            ],
        }
    )

    assert get_page(settings, "Güncel Stok Durumu") == {
        "etiket": "",
        "baslik_metni": "",
        "grup": "",
        "sira": 0,
        "gorunur": True,
        "baslik_renkleri": ["#ffffff", "#123456", "#abcdef", "#000000"],
        "baslik_puntosu": 56,
    }
    assert settings["ozel_sayfalar"] == [
        {
            "id": "ozel-0123456789abcdef",
            "baslik": "Bilgilendirme",
            "grup": "🏠 Genel Bakış",
            "sira": 0,
            "gorunur": True,
            "bloklar": [
                {"tur": "baslik", "metin": "Günlük duyuru"},
                {"tur": "metin", "metin": "Açıklama"},
            ],
        }
    ]


def test_builtin_page_title_can_be_changed_without_changing_its_route():
    normalize, _ = _page_editor_helpers()
    from_app = normalize(
        {
            "sayfalar": {
                "Güncel Stok Durumu": {"baslik_metni": "Depo Özeti"}
            }
        }
    )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "sayfa_baslik_metnini_al"
    )
    constant = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "SAYFA_VARSAYILAN_BASLIKLARI"
            for target in node.targets
        )
    )
    namespace = {}
    module = ast.fix_missing_locations(
        ast.Module(body=[constant, helper], type_ignores=[])
    )
    exec(compile(module, str(app_path), "exec"), namespace)

    assert namespace["sayfa_baslik_metnini_al"](
        from_app, "Güncel Stok Durumu"
    ) == "Depo Özeti"
    assert namespace["sayfa_baslik_metnini_al"](
        {}, "Güncel Stok Durumu"
    ) == "📦 Güncel Depo Envanteri ve Kritik Stoklar"


def test_builtin_page_headers_read_the_admin_configured_title():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    header_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "st"
        and node.func.attr == "header"
    ]

    assert header_calls
    assert all(
        isinstance(call.args[0], ast.Call)
        and isinstance(call.args[0].func, ast.Name)
        and call.args[0].func.id == "sayfa_baslik_metnini_al"
        for call in header_calls
    )


def test_admin_tools_render_after_the_settings_tabs():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    lines = app_path.read_text(encoding="utf-8").splitlines()
    editor_line = next(
        index for index, line in enumerate(lines)
        if 'with st.expander("🧩 Kod Yazmadan Sayfa Düzenleyici"' in line
    )
    cleanup_line = next(
        index for index, line in enumerate(lines)
        if "# Sayfa ve kayıt bazlı test verisi temizleme aracı" in line
    )
    tab_lines = [
        index for index, line in enumerate(lines)
        if line.strip().startswith("with sekme_")
    ]

    assert tab_lines
    assert editor_line > max(tab_lines)
    assert cleanup_line > editor_line
    assert lines[editor_line - 1].strip() == "if yonetici_modu:"


def test_custom_page_delete_confirmation_is_checked_after_form_submit():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    editor = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "admin_sayfa_duzenleyici"
    )
    delete_button = next(
        node for node in ast.walk(editor)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "form_submit_button"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "Özel sayfayı sil"
    )
    confirms_after_submit = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.UnaryOp)
        and isinstance(node.test.op, ast.Not)
        and isinstance(node.test.operand, ast.Name)
        and node.test.operand.id == "silme_onayi"
        for node in ast.walk(editor)
    )

    assert all(keyword.arg != "disabled" for keyword in delete_button.keywords)
    assert confirms_after_submit
