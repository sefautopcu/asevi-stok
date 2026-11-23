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


def test_dark_widgets_popovers_and_sidebar_hover_have_readable_tokens():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    assert 'button[data-testid="baseButton-primary"]' in source
    assert 'div.stButton > button[data-testid="baseButton-primary"] p' in source
    assert 'var(--app-accent-contrast) !important;' in source
    assert 'div.stButton > button[data-testid="baseButton-secondary"]' in source
    assert 'var(--app-text) !important;' in source
    assert 'button[data-testid="baseButton-primary"]:hover' in source
    assert 'button[data-testid="baseButton-primary"]:focus' in source
    assert 'button[data-testid="baseButton-primary"]:active' in source
    assert 'button[data-testid="baseButton-secondary"] p' in source
    assert 'button[data-testid="baseButton-secondary"]:hover' in source
    assert 'div.stButton > button:focus' in source
    assert 'div.stButton > button:active' in source
    assert '-webkit-text-fill-color: inherit !important;' in source
    assert 'Düğme metnini görünür renk katmanına son kez sabitle.' in source
    assert 'button[data-testid="baseButton-primary"] *' in source
    assert 'button[data-testid="baseButton-secondary"] *' in source
    assert '[data-testid="stWidgetLabel"]' in source
    assert "div[data-testid=\"stExpander\"] summary" in source
    assert 'input[type="checkbox"]' in source
    assert 'input[type="radio"]' in source
    assert '[data-testid="stCheckbox"]' in source
    assert '[data-testid="stRadio"]' in source
    assert '[data-testid="stToggle"]' in source
    assert '[data-testid="stTabs"] [role="tab"]' in source
    assert 'div[data-testid="stDataFrame"]' in source
    assert "input::placeholder" in source
    assert 'input[type="checkbox"]' in source
    assert '[data-testid="stCheckbox"] label p' in source
    assert '[data-testid="stRadio"] label p' in source
    assert "ul[role=\"listbox\"]" in source
    assert "li[role=\"option\"]:hover" in source
    assert 'section[data-testid="stSidebar"] div.stButton > button:hover' in source
    assert "transform: translateX(4px) !important;" in source


def test_user_settings_css_does_not_depend_on_local_f_string_variables():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    settings_pos = source.index('elif menu == "Kullanıcı Ayarları":')
    settings_source = source[settings_pos:]

    assert 'st.markdown("""' in settings_source
    assert "background-color: var(--app-card) !important;" in settings_source
    assert "border: 1px solid var(--app-border) !important;" in settings_source
    assert "color: var(--app-accent) !important;" in settings_source
    assert "background-color: var(--app-sidebar) !important;" in settings_source


def test_user_settings_table_uses_theme_safe_custom_table():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    source = app_path.read_text(encoding="utf-8")

    settings_pos = source.index('elif menu == "Kullanıcı Ayarları":')
    settings_source = source[settings_pos:]

    assert 'ozel_html_tablo_goster(tablo_satirlari)' in settings_source
    assert 'st.dataframe(pd.DataFrame(tablo_satirlari)' not in settings_source


def test_dual_theme_sidebar_config_has_contrast_tokens():
    config_path = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    source = config_path.read_text(encoding="utf-8")

    assert '[theme.light.sidebar]' in source
    assert 'backgroundColor = "#e4edf3"' in source
    assert 'textColor = "#102235"' in source
    assert '[theme.dark.sidebar]' in source
    assert 'backgroundColor = "#060a14"' in source
    assert 'textColor = "#f4f4f5"' in source
