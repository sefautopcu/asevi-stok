import ast
from pathlib import Path

from src.besin_hesaplama import urun_kalori_hesapla


ROOT = Path(__file__).resolve().parents[1]


def test_short_calorie_tokens_do_not_match_inside_other_words():
    assert urun_kalori_hesapla("PAKET", 1, "Adet") == 100
    assert urun_kalori_hesapla("ET", 1, "Adet") == 250


def test_dashboard_weather_is_cached_and_reports_are_manual():
    runtime = (ROOT / "src" / "app_runtime.py").read_text(encoding="utf-8")
    dashboard = (ROOT / "src" / "dashboard_ui.py").read_text(encoding="utf-8")

    assert "@streamlit_lib.cache_data(ttl=1800, show_spinner=False)" in dashboard
    assert "_hava_durumu_verisini_getir(hava_url)" in dashboard
    assert "gunluk_rapor_maili_gonder(" not in runtime


def test_streamlit_entrypoint_is_small_and_delegates_to_runtime():
    entrypoint = (ROOT / "app.py").read_text(encoding="utf-8")

    assert len(entrypoint.encode("utf-8")) < 40_000
    assert "from src import app_runtime" in entrypoint


def test_nonessential_data_loads_are_deferred_until_login():
    runtime = (ROOT / "src" / "app_runtime.py").read_text(encoding="utf-8")

    auth_loads = 'if st.session_state.oturum_aktif:\n    if "arayuz_sayfa_ayarlari" not in st.session_state:'
    assert auth_loads in runtime
    assert runtime.index(auth_loads) < runtime.index("gecerli_menuler = [")


def test_demirbas_loader_and_saver_names_are_consistent():
    runtime_path = ROOT / "src" / "app_runtime.py"
    runtime = runtime_path.read_text(encoding="utf-8")
    tree = ast.parse(runtime)
    tanimli_fonksiyonlar = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }

    assert "demirbaşları_yukle" not in runtime
    assert "demirbaşları_kaydet" not in runtime
    assert "demirbasları_yukle" in tanimli_fonksiyonlar
    assert "demirbasları_kaydet" in tanimli_fonksiyonlar


def test_user_management_receives_password_change_dependency():
    runtime = (ROOT / "src" / "app_runtime.py").read_text(encoding="utf-8")
    user_ui = (ROOT / "src" / "kullanici_yonetim_ui.py").read_text(encoding="utf-8")

    assert "kullanici_yonetim_sekmesini_goster(" in runtime
    assert "sifre_degistir," in runtime
    assert "def kullanici_yonetim_sekmesini_goster(" in user_ui
    assert "sifre_degistir)" in user_ui
    assert "sifre_degistir(secilen_k_adi" in user_ui
