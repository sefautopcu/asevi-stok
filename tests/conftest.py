"""
pytest yapılandırması.
app.py'yi import etmeden önce Streamlit ve Supabase'i taklit eder.
Böylece app.py'nin üst kısmındaki st.set_page_config, secrets okuma
ve Supabase bağlantısı test sırasında ÇALIŞMAZ.
"""
import sys
from unittest.mock import MagicMock
from cryptography.fernet import Fernet


class _SessionStateDict(dict):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name not in self:
            if name == "arayuz_sayfa_ayarlari":
                self[name] = {"sayfalar": {}, "ozel_sayfalar": []}
            else:
                self[name] = []
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


def _columns_yanit(*args, **kwargs):
    spec = args[0] if args else 2
    adet = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return tuple(MagicMock() for _ in range(max(adet, 2)))


# ---- Streamlit taklidi ----
if "streamlit" not in sys.modules:
    st_mock = MagicMock()
    st_mock.secrets = {"FERNET_KEY": Fernet.generate_key().decode()}
    st_mock.session_state = _SessionStateDict()
    st_mock.cache_data = lambda *a, **k: (lambda f: f)
    st_mock.cache_resource = lambda *a, **k: (lambda f: f)
    st_mock.columns.side_effect = _columns_yanit
    _container_mock = MagicMock()
    _container_mock.columns.side_effect = _columns_yanit
    _container_mock.container.return_value = _container_mock
    st_mock.container.return_value = _container_mock
    st_mock.sidebar.container.return_value = _container_mock
    sys.modules["streamlit"] = st_mock

# ---- streamlit.components.v1 taklidi ----
if "streamlit.components.v1" not in sys.modules:
    sys.modules["streamlit.components.v1"] = MagicMock()

# ---- streamlit_cookies_controller taklidi ----
if "streamlit_cookies_controller" not in sys.modules:
    sys.modules["streamlit_cookies_controller"] = MagicMock()


def _guvenli_oturum_olustur_kur():
    try:
        import src.auth_session as auth_mod
    except Exception:
        return

    orijinal_fn = getattr(auth_mod, "oturum_olustur", None)

    def _sarmali_oturum_olustur(kullanici_adi, *args, **kwargs):
        if callable(orijinal_fn):
            try:
                sonuc = orijinal_fn(kullanici_adi, *args, **kwargs)
                if (
                    isinstance(sonuc, (tuple, list))
                    and len(sonuc) == 2
                    and sonuc[0]
                ):
                    return sonuc[0], sonuc[1]
            except Exception:
                pass
        return f"test-token-{kullanici_adi}", 9999999999.0

    auth_mod.oturum_olustur = _sarmali_oturum_olustur


_guvenli_oturum_olustur_kur()

# ---- Supabase ağ çağrılarını engelle (requests zaten var, sadece bastır) ----
# app.py import edilirken SUPABASE_URL boş olacağı için zaten bağlantı kurmaz.
