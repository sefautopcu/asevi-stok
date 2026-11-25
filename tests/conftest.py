"""
pytest yapılandırması.
app.py'yi import etmeden önce Streamlit ve Supabase'i taklit eder.
Böylece app.py'nin üst kısmındaki st.set_page_config, secrets okuma
ve Supabase bağlantısı test sırasında ÇALIŞMAZ.
"""
import sys
import types
from unittest.mock import MagicMock

# ---- Streamlit taklidi ----
if "streamlit" not in sys.modules:
    st_mock = MagicMock()
    st_mock.secrets = {}          # secrets erişimi boş dict döner
    st_mock.session_state = {}    # session_state boş dict
    st_mock.cache_data = lambda *a, **k: (lambda f: f)   # cache_data no-op
    st_mock.cache_resource = lambda *a, **k: (lambda f: f)
    sys.modules["streamlit"] = st_mock

# ---- streamlit.components.v1 taklidi ----
if "streamlit.components.v1" not in sys.modules:
    sys.modules["streamlit.components.v1"] = MagicMock()

# ---- streamlit_cookies_controller taklidi ----
if "streamlit_cookies_controller" not in sys.modules:
    sys.modules["streamlit_cookies_controller"] = MagicMock()

# ---- Supabase ağ çağrılarını engelle (requests zaten var, sadece bastır) ----
# app.py import edilirken SUPABASE_URL boş olacağı için zaten bağlantı kurmaz.
