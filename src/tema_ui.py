def _tema_tercihini_yukle(_url_temasi=None, _cerez_temasi=None):
    """Uygulama yalnızca Dark temayı kullanır."""
    return "Dark"


def tema_baglamini_hazirla(st, cerez_oku=None):
    """Dark tema durumunu session_state'e yükler ve renk/CSS değişkenlerini döndürür."""
    st.session_state.tema = "Dark"

    border_color = "rgba(16, 185, 129, 0.35)"
    bg_color = "#040711"
    card_bg = "rgba(10, 15, 29, 0.75)"
    sidebar_bg = "rgba(6, 10, 20, 0.85)"
    text_color = "#F4F4F5"
    subtext_color = "#94A3B8"
    input_bg = "rgba(15, 23, 42, 0.85)"
    popover_bg = "#0b1329"
    accent_color = "#10B981"
    accent_contrast = "#04110C"
    radial_1 = "rgba(16, 185, 129, 0.12)"
    radial_2 = "rgba(56, 189, 248, 0.10)"

    gdg_bg = "#0A0F1D"
    gdg_header = "#060A14"
    gdg_hover = "#111A2E"

    return {
        "border_color": border_color,
        "bg_color": bg_color,
        "card_bg": card_bg,
        "sidebar_bg": sidebar_bg,
        "text_color": text_color,
        "subtext_color": subtext_color,
        "input_bg": input_bg,
        "popover_bg": popover_bg,
        "accent_color": accent_color,
        "accent_contrast": accent_contrast,
        "radial_1": radial_1,
        "radial_2": radial_2,
        "gdg_bg": gdg_bg,
        "gdg_header": gdg_header,
        "gdg_hover": gdg_hover,
    }


def tema_stillerini_uygula(st, palet):
    """Ana Dark tema CSS değişkenlerini ve bileşen stillerini sayfaya enjekte eder."""
    border_color = palet["border_color"]
    bg_color = palet["bg_color"]
    card_bg = palet["card_bg"]
    sidebar_bg = palet["sidebar_bg"]
    text_color = palet["text_color"]
    subtext_color = palet["subtext_color"]
    input_bg = palet["input_bg"]
    popover_bg = palet["popover_bg"]
    accent_color = palet["accent_color"]
    accent_contrast = palet["accent_contrast"]
    radial_1 = palet["radial_1"]
    radial_2 = palet["radial_2"]
    gdg_bg = palet["gdg_bg"]
    gdg_header = palet["gdg_header"]
    gdg_hover = palet["gdg_hover"]

    st.markdown(
        f"""
        <style>
            :root, html, body, .stApp {{
                color-scheme: dark !important;
                --app-bg: {bg_color};
                --app-card: {card_bg};
                --app-sidebar: {sidebar_bg};
                --app-border: {border_color};
                --app-text: {text_color};
                --app-muted: {subtext_color};
                --app-input: {input_bg};
                --app-popover: {popover_bg};
                --app-accent: {accent_color};
                --app-accent-contrast: {accent_contrast};
                --app-radial-1: {radial_1};
                --app-radial-2: {radial_2};
                --primary-color: {accent_color} !important;
                --background-color: {bg_color} !important;
                --secondary-background-color: {gdg_header} !important;
                --text-color: {text_color} !important;
                --gdg-bg-cell: {gdg_bg} !important;
                --gdg-bg-cell-medium: {gdg_header} !important;
                --gdg-bg-header: {gdg_header} !important;
                --gdg-bg-header-has-focus: {gdg_hover} !important;
                --gdg-bg-header-hovered: {gdg_hover} !important;
                --gdg-bg-search-result: {gdg_hover} !important;
                --gdg-text-dark: {text_color} !important;
                --gdg-text-medium: {subtext_color} !important;
                --gdg-text-light: {subtext_color} !important;
                --gdg-text-header: {text_color} !important;
                --gdg-text-group-header: {text_color} !important;
                --gdg-border-color: {border_color} !important;
                --gdg-horizontal-border-color: {border_color} !important;
                --gdg-accent-color: {accent_color} !important;
                --gdg-accent-fg: {accent_contrast} !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

            .stApp {
                background-color: var(--app-bg) !important;
                background-image: radial-gradient(circle at 10% 20%, var(--app-radial-1) 0%, transparent 45%),
                                  radial-gradient(circle at 90% 80%, var(--app-radial-2) 0%, transparent 45%) !important;
                background-attachment: fixed !important;
                color: var(--app-text) !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
            }

            section[data-testid="stSidebar"] {
                background: var(--app-sidebar) !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
                border-right: 1px solid var(--app-border) !important;
            }

            section[data-testid="stSidebar"] div.stButton > button {
                background: transparent !important;
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
                border: 1px solid transparent !important;
                border-radius: 12px !important;
                font-weight: 500 !important;
                padding: 10px 16px !important;
                transition: all 0.25s ease !important;
            }
            section[data-testid="stSidebar"] div.stButton > button p,
            section[data-testid="stSidebar"] div.stButton > button span,
            section[data-testid="stSidebar"] div.stButton > button div,
            section[data-testid="stSidebar"] div.stButton > button strong {
                color: inherit !important;
                -webkit-text-fill-color: inherit !important;
            }
            section[data-testid="stSidebar"] div.stButton > button:hover {
                background: var(--app-accent) !important;
                color: var(--app-accent-contrast) !important;
                border: 1px solid var(--app-border) !important;
                box-shadow: 0 0 25px -3px var(--app-accent) !important;
                transform: translateX(4px) !important;
            }
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"],
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] p,
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] span,
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] div {
                background: var(--app-accent) !important;
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
            }
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
                border: 1px solid var(--app-accent) !important;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.18) !important;
            }
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"],
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"] p,
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"] span,
            section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-secondary"] div {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }
            section[data-testid="stSidebar"] div.stButton > button:hover p,
            section[data-testid="stSidebar"] div.stButton > button:hover span,
            section[data-testid="stSidebar"] div.stButton > button:hover div,
            section[data-testid="stSidebar"] div.stButton > button:hover strong {
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
            }

            div[data-testid="stMetric"],
            div[data-testid="stForm"],
            div[data-testid="stExpander"] {
                background: var(--app-card) !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
                border: 1px solid var(--app-border) !important;
                border-radius: 18px !important;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10) !important;
            }

            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"] {
                background: var(--app-bg) !important;
                background-color: var(--app-bg) !important;
                color: var(--app-text) !important;
            }
            header[data-testid="stHeader"] button,
            header[data-testid="stHeader"] svg {
                color: var(--app-text) !important;
                fill: var(--app-text) !important;
            }

            input,
            textarea,
            div[data-baseweb="base-input"],
            div[data-baseweb="base-input"] > div,
            div[data-baseweb="input"],
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"],
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="select"] > div,
            div[data-baseweb="select"] > div > div {
                background-color: var(--app-input) !important;
                color: var(--app-text) !important;
                border-color: var(--app-border) !important;
            }
            div[data-baseweb="input"],
            div[data-baseweb="textarea"],
            div[data-baseweb="select"] > div {
                border-radius: 12px !important;
                border: 1px solid var(--app-border) !important;
            }
            div[data-baseweb="base-input"] {
                border: none !important;
            }
            div[data-baseweb="input"] button,
            div[data-baseweb="select"] svg {
                background: transparent !important;
                color: var(--app-text) !important;
                fill: var(--app-text) !important;
            }

            [data-testid="stWidgetLabel"] p,
            [data-testid="stWidgetLabel"] label,
            [data-testid="stCaptionContainer"],
            .stMarkdown p,
            .stMarkdown li,
            .stMarkdown td,
            .stMarkdown th,
            div[data-testid="stExpander"] summary,
            div[data-testid="stExpander"] summary p,
            div[data-testid="stExpander"] summary span {
                color: var(--app-text) !important;
            }

            input[type="checkbox"],
            input[type="radio"] {
                accent-color: var(--app-accent) !important;
            }
            [data-testid="stCheckbox"] label,
            [data-testid="stCheckbox"] label p,
            [data-testid="stCheckbox"] label span,
            [data-testid="stRadio"] label,
            [data-testid="stRadio"] label p,
            [data-testid="stRadio"] label span,
            [data-testid="stToggle"] label,
            [data-testid="stToggle"] label p,
            [data-testid="stToggle"] label span {
                color: var(--app-text) !important;
            }
            [data-testid="stCheckbox"] [role="checkbox"],
            [data-testid="stRadio"] [role="radio"],
            [data-testid="stToggle"] [role="switch"] {
                border: 1px solid var(--app-border) !important;
            }

            [data-testid="stTabs"] [role="tab"],
            [data-testid="stTabs"] [role="tab"] p,
            div[data-testid="stDataFrame"],
            div[data-testid="stDataFrame"] *,
            div[data-testid="stTable"],
            div[data-testid="stTable"] * {
                color: var(--app-text) !important;
            }
            [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
                color: var(--app-accent) !important;
                border-bottom-color: var(--app-accent) !important;
            }
            [data-testid="stTabs"] [role="tabpanel"] {
                background: transparent !important;
                color: var(--app-text) !important;
            }

            input,
            textarea,
            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea,
            div[data-baseweb="select"] span,
            div[data-baseweb="select"] div {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }

            input::placeholder,
            textarea::placeholder,
            [data-baseweb="input"] input::placeholder,
            [data-baseweb="textarea"] textarea::placeholder {
                color: var(--app-muted) !important;
                -webkit-text-fill-color: var(--app-muted) !important;
                opacity: 1 !important;
            }

            ul[role="listbox"],
            div[role="listbox"],
            div[data-baseweb="menu"],
            div[data-baseweb="popover"] {
                background: var(--app-popover) !important;
                color: var(--app-text) !important;
                border-color: var(--app-border) !important;
            }
            li[role="option"],
            div[role="option"] {
                color: var(--app-text) !important;
                background: var(--app-popover) !important;
            }
            li[role="option"]:hover,
            div[role="option"]:hover,
            li[aria-selected="true"],
            div[aria-selected="true"] {
                background: var(--app-sidebar) !important;
                color: var(--app-accent) !important;
            }

            [data-baseweb="checkbox"] div,
            [data-baseweb="radio"] div {
                border-color: var(--app-border) !important;
            }

            button[data-testid="baseButton-primary"] {
                background: var(--app-accent) !important;
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
                border: none !important;
                border-radius: 12px !important;
                font-weight: 700 !important;
                box-shadow: 0 4px 20px rgba(15, 23, 42, 0.18) !important;
            }
            button[data-testid="baseButton-primary"] p,
            button[data-testid="baseButton-primary"] span,
            button[data-testid="baseButton-primary"] div,
            button[data-testid="baseButton-primary"] strong {
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
            }
            button[data-testid="baseButton-primary"]:hover,
            button[data-testid="baseButton-primary"]:focus,
            button[data-testid="baseButton-primary"]:active {
                background: var(--app-accent) !important;
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
            }

            button[data-testid="baseButton-secondary"], div.stButton > button {
                background: var(--app-card) !important;
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
                border: 1px solid var(--app-border) !important;
                border-radius: 12px !important;
            }
            button[data-testid="baseButton-secondary"] p,
            button[data-testid="baseButton-secondary"] span,
            button[data-testid="baseButton-secondary"] div,
            button[data-testid="baseButton-secondary"] strong,
            div.stButton > button p,
            div.stButton > button span,
            div.stButton > button div,
            div.stButton > button strong {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }
            button[data-testid="baseButton-secondary"]:hover,
            button[data-testid="baseButton-secondary"]:focus,
            button[data-testid="baseButton-secondary"]:active,
            div.stButton > button:hover,
            div.stButton > button:focus,
            div.stButton > button:active {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }
            button,
            button * {
                background-clip: border-box !important;
                -webkit-background-clip: border-box !important;
            }
            button[data-testid="baseButton-primary"],
            button[data-testid="baseButton-primary"] *,
            .stButton button[data-testid="baseButton-primary"],
            .stButton button[data-testid="baseButton-primary"] * {
                color: var(--app-accent-contrast) !important;
                -webkit-text-fill-color: var(--app-accent-contrast) !important;
            }
            button[data-testid="baseButton-secondary"],
            button[data-testid="baseButton-secondary"] *,
            .stButton button[data-testid="baseButton-secondary"],
            .stButton button[data-testid="baseButton-secondary"] * {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stExpander"],
            section[data-testid="stSidebar"] div[data-testid="stExpander"] details,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] details > summary,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] details[open] > summary,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] details > div {
                background: var(--app-sidebar) !important;
                background-color: var(--app-sidebar) !important;
                color: var(--app-text) !important;
                border-color: var(--app-border) !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stExpander"] summary,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] summary *,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] summary p,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] summary span,
            section[data-testid="stSidebar"] div[data-testid="stExpander"] summary svg {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
                fill: var(--app-text) !important;
                opacity: 1 !important;
            }
            [data-testid="stMain"] div[data-testid="stExpander"] details,
            [data-testid="stMain"] div[data-testid="stExpander"] details > summary,
            [data-testid="stMain"] div[data-testid="stExpander"] details[open] > summary {
                background: transparent !important;
                background-color: transparent !important;
                color: var(--app-text) !important;
            }
            [data-testid="stMain"] div[data-testid="stExpander"] summary,
            [data-testid="stMain"] div[data-testid="stExpander"] summary *,
            [data-testid="stMain"] div[data-testid="stExpander"] summary p,
            [data-testid="stMain"] div[data-testid="stExpander"] summary span,
            [data-testid="stMain"] div[data-testid="stExpander"] summary svg {
                color: var(--app-text) !important;
                -webkit-text-fill-color: var(--app-text) !important;
                fill: var(--app-text) !important;
                opacity: 1 !important;
            }

            .custom-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                margin: 15px 0;
                background: var(--app-card);
                backdrop-filter: blur(16px);
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid var(--app-border);
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10);
            }
            .custom-table th {
                background: var(--app-sidebar);
                color: var(--app-text) !important;
                padding: 14px 18px;
                font-size: 13px !important;
                font-weight: 700;
                border-bottom: 1px solid var(--app-border);
            }
            .custom-table td {
                padding: 14px 18px;
                color: var(--app-text) !important;
                font-size: 13px !important;
                border-bottom: 1px solid var(--app-border);
            }

            .stApp h1:not([data-testid]),
            .stApp h2:not([data-testid]),
            .stApp h3:not([data-testid]) {
                display: inline-block !important;
                max-width: 100% !important;
                background-image: linear-gradient(
                    90deg,
                    #F4F4F5 0%,
                    #10B981 35%,
                    #94A3B8 68%,
                    #38BDF8 100%
                ) !important;
                background-size: 100% 100% !important;
                background-clip: text !important;
                -webkit-background-clip: text !important;
                color: transparent !important;
                -webkit-text-fill-color: transparent !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
