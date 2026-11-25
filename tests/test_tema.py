import ast
from pathlib import Path


def _tema_kaynak_dosyasini_bul(root: Path) -> Path:
    adaylar = [
        root / "src" / "tema_ui.py",
        root / "tema_ui.py",
        root / "src" / "app_runtime.py",
    ]
    for yol in adaylar:
        if yol.exists():
            return yol
    return adaylar[0]


def _app_tema_tercih_fonksiyonunu_yukle():
    root = Path(__file__).resolve().parents[1]
    app_yolu = _tema_kaynak_dosyasini_bul(root)
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

    assert tema_yukle("Arctic", "") == "Dark"
    assert tema_yukle("Dark", "Arctic") == "Dark"
    assert tema_yukle("", "Arctic") == "Dark"
    assert tema_yukle("", "") == "Dark"
    assert tema_yukle("unknown", "unknown") == "Dark"


def test_login_cards_use_theme_tokens_and_hover_motion():
    root = Path(__file__).resolve().parents[1]
    
    # CSS kodları ui_styles.py'de, diğer kontroller app_runtime.py'de
    source = (root / "src" / "ui_styles.py").read_text(encoding="utf-8")
    source += (root / "src" / "app_runtime.py").read_text(encoding="utf-8")
    source += (root / "src" / "dashboard_ui.py").read_text(encoding="utf-8")

    assert ".login-feature-card:hover" in source
    assert "transform: translateY(-4px);" in source
    assert "Veritabanı uyarısı" in source
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in source
    assert ".cost-panel {{ background: rgba(10, 15, 29, 0.85);" in source
    assert "border: 1px solid rgba(16, 185, 129, 0.4);" in source


def test_dashboard_information_cards_have_theme_hover():
    app_path = Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.py"
    source = app_path.read_text(encoding="utf-8")

    assert ".metric-card:hover {{ transform: translateY(-5px);" in source
    assert ".table-panel:hover" in source
    assert ".cost-panel" in source
    assert "border-color: rgba(16, 185, 129, 0.8);" in source
    assert "transition: all 0.3s ease" in source


def test_system_feature_cards_fit_two_rows_in_component():
    app_path = Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.py"
    source = app_path.read_text(encoding="utf-8")

    assert "ozellikler_html" in source
    assert "components.html(ozellikler_html, height=190, scrolling=False)" in source
    assert "gap: 15px;" in source


def test_invoice_table_defaults_before_empty_girisler_branch():
    app_path = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    source = app_path.read_text(encoding="utf-8")

    assert "mal_alimi_sayfasi(" in source
    assert "fatura_tablo_verisi = []" not in source


def test_dashboard_table_css_is_escaped_in_f_string():
    app_path = Path(__file__).resolve().parents[1] / "src" / "dashboard_ui.py"
    source = app_path.read_text(encoding="utf-8")

    assert ".table-panel" in source
    assert "background: rgba(10, 15, 29, 0.85);" in source


def test_pure_dark_palette_does_not_keep_light_theme_tokens():
    root = Path(__file__).resolve().parents[1]
    tema_path = _tema_kaynak_dosyasini_bul(root)
    source = tema_path.read_text(encoding="utf-8")

    assert 'bg_color = "#040711"' in source
    assert 'card_bg = "rgba(10, 15, 29, 0.75)"' in source
    assert 'text_color = "#F4F4F5"' in source
    assert 'subtext_color = "#94A3B8"' in source
    assert "--app-accent-contrast:" in source
    assert "Arctic" not in source
    assert "tema_radio_widget" not in source


def test_theme_css_replaces_fixed_low_contrast_text_tokens():
    root = Path(__file__).resolve().parents[1]
    tema_path = _tema_kaynak_dosyasini_bul(root)
    source = tema_path.read_text(encoding="utf-8")

    assert "var(--app-text)" in source
    assert "var(--app-muted)" in source
    assert "var(--app-accent)" in source
    assert "var(--app-accent-contrast)" in source


def test_dark_widgets_popovers_and_sidebar_hover_have_readable_tokens():
    root = Path(__file__).resolve().parents[1]
    tema_path = _tema_kaynak_dosyasini_bul(root)
    source = tema_path.read_text(encoding="utf-8")

    assert 'button[data-testid="baseButton-primary"]' in source
    assert 'button[data-testid="baseButton-secondary"]' in source
    assert 'var(--app-accent-contrast) !important;' in source
    assert 'var(--app-text) !important;' in source
    assert 'button[data-testid="baseButton-primary"]:hover' in source
    assert 'button[data-testid="baseButton-primary"]:focus' in source
    assert 'button[data-testid="baseButton-primary"]:active' in source
    assert 'button[data-testid="baseButton-secondary"]:hover' in source
    assert 'div.stButton > button:focus' in source
    assert 'div.stButton > button:active' in source
    assert '[data-testid="stWidgetLabel"]' in source
    assert 'div[data-testid="stExpander"] summary' in source
    assert 'input[type="checkbox"]' in source
    assert 'input[type="radio"]' in source
    assert '[data-testid="stCheckbox"]' in source
    assert '[data-testid="stRadio"]' in source
    assert '[data-testid="stToggle"]' in source
    assert '[data-testid="stTabs"] [role="tab"]' in source
    assert 'div[data-testid="stDataFrame"]' in source
    assert "input::placeholder" in source
    assert 'ul[role="listbox"]' in source
    assert 'li[role="option"]:hover' in source
    assert 'section[data-testid="stSidebar"] div.stButton > button:hover' in source
    assert "transform: translateX(4px) !important;" in source


def test_user_settings_css_does_not_depend_on_local_f_string_variables():
    app_path = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    source = app_path.read_text(encoding="utf-8")

    assert "manuel_rapor_gonderim_alani(" in source
    assert "guvenlik_durumu_rozetlerini_goster(" in source


def test_user_settings_table_uses_theme_safe_custom_table():
    app_path = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    source = app_path.read_text(encoding="utf-8")

    assert "kullanici_yonetim_sekmesini_goster(" in source
    assert "giris_kayitlari_sekmesini_goster(" in source


def test_dark_sidebar_config_has_contrast_tokens():
    config_path = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    source = config_path.read_text(encoding="utf-8")

    assert '[theme.dark.sidebar]' in source
    assert 'backgroundColor = "#060a14"' in source
    assert 'textColor = "#f4f4f5"' in source
