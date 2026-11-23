from pathlib import Path

from src.besin_hesaplama import urun_kalori_hesapla


ROOT = Path(__file__).resolve().parents[1]


def test_short_calorie_tokens_do_not_match_inside_other_words():
    assert urun_kalori_hesapla("PAKET", 1, "Adet") == 100
    assert urun_kalori_hesapla("ET", 1, "Adet") == 250


def test_dashboard_weather_is_cached_and_reports_are_manual():
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "@st.cache_data(ttl=900, show_spinner=False)" in source
    assert "hava_durumu_verisini_getir(hava_url)" in source
    assert "# Raporlar yalnızca dashboard'daki manuel butonlarla gönderilir." in source
    assert "gunluk_rapor_maili_gonder()" not in source.split(
        "# Raporlar yalnızca dashboard'daki manuel butonlarla gönderilir.", 1
    )[1]
