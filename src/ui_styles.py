# src/ui_styles.py
import streamlit as st

def login_sayfasi_stillerini_uygula(accent_color, card_bg, border_color, text_color, subtext_color):
    """Giriş ekranının tüm CSS tasarımını uygular."""
    st.markdown(
        f"""
        <style>
            div[data-testid="stMainBlockContainer"] {{
                padding-top: 32px !important;
                padding-bottom: 24px !important;
            }}
            .st-key-login-layout {{
                width: calc(100% - 32px) !important;
                max-width: 1180px !important;
                margin: 0 auto !important;
                padding-top: 42px !important;
                position: relative;
                left: 10px;
            }}
            .st-key-login-card {{
                min-height: 556px;
                margin-top: 71px;
                padding: 4px 32px 26px;
                box-sizing: border-box;
                gap: 9px !important;
                background: {card_bg} !important;
                border: 1px solid {border_color} !important;
                border-radius: 24px !important;
                box-shadow: 0 18px 55px rgba(0, 0, 0, 0.28) !important;
            }}
            .st-key-login-card h2 {{
                margin: 0;
                padding: 0 !important;
                text-align: center;
                color: {text_color} !important;
                background: none !important;
                background-image: none !important;
                -webkit-background-clip: border-box !important;
                background-clip: border-box !important;
                -webkit-text-fill-color: {text_color} !important;
                font-size: 1.55rem;
                letter-spacing: -0.04em;
            }}
            .st-key-login-card .login-subtitle {{
                margin: 2px 0 8px;
                text-align: center;
                color: {subtext_color};
                font-size: 0.86rem;
            }}
            .st-key-login-card div[data-testid="stForm"] {{
                padding: 0 !important;
                background: transparent !important;
                border: 0 !important;
                box-shadow: none !important;
            }}
            .st-key-login-card [data-testid="stForm"] [data-testid="stMarkdownContainer"] p {{
                margin-bottom: 0 !important;
            }}
            .login-hero {{
                padding: 8px 0 22px;
            }}
            .login-eyebrow {{
                display: inline-block;
                padding: 7px 13px;
                border: 1px solid {border_color};
                border-radius: 999px;
                color: {accent_color};
                background: {card_bg};
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.04em;
            }}
            .login-hero h1 {{
                margin: 22px 0 3px;
                padding: 0 !important;
                color: {text_color} !important;
                font-size: clamp(2.5rem, 3.2vw, 3rem) !important;
                line-height: 1.12;
                letter-spacing: -0.06em;
            }}
            .login-hero h1 .login-brand-accent {{ color: {accent_color} !important; }}
            .login-hero h3 {{
                margin: -3px 0 12px;
                padding: 0 !important;
                color: {subtext_color};
                font-size: 1.05rem;
                font-weight: 600;
            }}
            .login-hero p {{
                max-width: 520px;
                color: {subtext_color};
                font-size: 0.92rem;
                line-height: 1.7;
            }}
            .login-feature-grid {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 14px;
                margin-top: 10px;
            }}
            .login-feature-card {{
                min-height: 132px;
                padding: 15px 16px;
                border: 1px solid {border_color};
                border-radius: 18px;
                background: {card_bg};
                transition: transform 0.18s ease, border-color 0.18s ease,
                            box-shadow 0.18s ease, background 0.18s ease;
            }}
            .login-feature-card:hover {{
                transform: translateY(-4px);
                border-color: {accent_color} !important;
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.16);
            }}
            .login-feature-icon {{
                margin-bottom: 8px;
                font-size: 1.35rem;
            }}
            .login-feature-card h4 {{
                margin: 0 0 4px;
                padding: 0 !important;
                color: {text_color};
                font-size: 0.92rem;
                font-weight: 700;
            }}
            .login-feature-card p {{
                margin: 0;
                color: {subtext_color};
                font-size: 0.76rem;
                line-height: 1.5;
            }}
            .login-version {{
                margin-top: 20px;
                color: {subtext_color};
                font-size: 0.72rem;
                text-align: center;
                opacity: 0.7;
            }}
            @media (max-width: 900px) {{
                div[data-testid="stMainBlockContainer"] {{
                    padding-top: 24px !important;
                }}
                .st-key-login-layout {{
                    width: calc(100% - 32px) !important;
                    max-width: none !important;
                    left: 0;
                    padding-top: 24px !important;
                }}
                .st-key-login-layout [data-testid="stHorizontalBlock"] {{
                    flex-direction: column;
                    gap: 24px;
                }}
                .st-key-login-layout [data-testid="stColumn"] {{
                    width: 100% !important;
                    flex: 1 1 100% !important;
                    min-width: 100% !important;
                }}
                .st-key-login-card {{
                    min-height: 0;
                    margin-top: 0;
                    padding: 22px 18px;
                }}
                .login-feature-grid {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 9px;
                }}
                .login-feature-card {{ padding: 13px; }}
            }}
            @media (max-width: 560px) {{
                .login-feature-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
            /* İkincil butonların (secondary) daha şık görünmesi için */
            div[data-testid="stButton"] > button[kind="secondary"] {
                background-color: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 12px !important;
                transition: all 0.3s ease-in-out !important;
                color: #94A3B8 !important;
                font-weight: 500 !important;
            }
            
            /* Üzerine gelince hafifçe parlasın ve kenarlığı renklensin */
            div[data-testid="stButton"] > button[kind="secondary"]:hover {
                background-color: rgba(16, 185, 129, 0.1) !important;
                border-color: rgba(16, 185, 129, 0.4) !important;
                color: #F4F4F5 !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
            /* İkincil butonların (secondary) daha şık görünmesi için */
            div[data-testid="stButton"] > button[kind="secondary"] {
                background-color: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 12px !important;
                transition: all 0.3s ease-in-out !important;
                color: #94A3B8 !important;
                font-weight: 500 !important;
            }
            
            /* Üzerine gelince hafifçe parlasın ve kenarlığı renklensin */
            div[data-testid="stButton"] > button[kind="secondary"]:hover {
                background-color: rgba(16, 185, 129, 0.1) !important;
                border-color: rgba(16, 185, 129, 0.4) !important;
                color: #F4F4F5 !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )
