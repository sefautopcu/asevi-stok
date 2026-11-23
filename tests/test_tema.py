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


def test_tema_preference_persisted_in_url_survives_reload():
    tema_yukle = _app_tema_tercih_fonksiyonunu_yukle()

    assert tema_yukle("Arctic", "") == "Arctic"
    assert tema_yukle("Dark", "Arctic") == "Dark"
    assert tema_yukle("", "Arctic") == "Arctic"
    assert tema_yukle("", "") == "Dark"
    assert tema_yukle("unknown", "unknown") == "Dark"


def test_login_cards_use_theme_tokens_and_hover_motion():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert ".login-feature-card:hover" in source
    assert "transform: translateY(-4px);" in source
    assert "Veritabanı uyarısı" in source
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in source
    assert ".cost-panel {{ background: {panel_bg};" in source
    assert "background: {panel_bg}; border: 1px solid {panel_border};" in source


def test_dashboard_information_cards_have_theme_hover():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert ".metric-card:hover {{ transform: translateY(-5px);" in source
    assert ".table-panel:hover {{ transform: translateY(-4px);" in source
    assert ".cost-card:hover {{ transform: translateY(-4px);" in source
    assert ".metric-card:hover {{ transform: translateY(-6px);" in source
    assert "border-color: {panel_accent};" in source
    assert "transition: transform 180ms ease" in source


def test_system_feature_cards_fit_two_rows_in_component():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert "min-height: 112px;" in source
    assert "gap: 12px;" in source
    assert "components.html(ozellikler_html, height=255, scrolling=False)" in source


def test_invoice_table_defaults_before_empty_girisler_branch():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    default_pos = source.index("fatura_tablo_verisi = []")
    branch_pos = source.index("if st.session_state.girisler:")
    archive_pos = source.index("if fatura_tablo_verisi:")
    invoice_pos = source.index("# --- FATURA ARŞİVİ TABLOSU ---")

    assert invoice_pos < default_pos < branch_pos < archive_pos


def test_dashboard_table_css_is_escaped_in_f_string():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert """        .table-panel {{
            background: {panel_bg};""" in source
    assert """            height: 100%;
        }}
    </style>""" in source


def test_arctic_and_dark_palette_tokens_are_theme_safe():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert 'border_color = "#C7D3DD"' in source
    assert 'bg_color = "#EDF3F7"' in source
    assert 'card_bg = "#FFFFFF"' in source
    assert 'sidebar_bg = "#E4EDF3"' in source
    assert 'text_color = "#102235"' in source
    assert 'subtext_color = "#52697A"' in source
    assert 'bg_color = "#040711"' in source
    assert 'card_bg = "rgba(10, 15, 29, 0.75)"' in source
    assert 'text_color = "#f4f4f5"' in source
    assert 'subtext_color = "#94a3b8"' in source
    assert "--app-accent-contrast:" in source


def test_theme_css_replaces_fixed_low_contrast_text_tokens():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert "var(--app-text)" in source
    assert "var(--app-muted)" in source
    assert "var(--app-accent)" in source
    assert "var(--app-accent-contrast)" in source


def test_dual_theme_sidebar_config_has_contrast_tokens():
    config_path = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    source = config_path.read_text(encoding="utf-8")

    assert '[theme.light.sidebar]' in source
    assert 'backgroundColor = "#e4edf3"' in source
    assert 'textColor = "#102235"' in source
    assert '[theme.dark.sidebar]' in source
    assert 'backgroundColor = "#060a14"' in source
    assert 'textColor = "#f4f4f5"' in source
