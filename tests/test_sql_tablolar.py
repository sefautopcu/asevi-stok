"""İlişkisel SQL tablo modülleri ve veri_yonetimi entegrasyon testleri."""

from src.dagitim_loglari_sql import (
    dagitim_kaydini_satira_donustur,
    dagitim_loglari_sql_kaydet,
    dagitim_loglari_sql_oku,
    satir_dagitim_kaydina_donustur,
)
from src.dashboard_widgets_sql import (
    dashboard_widgets_sql_kaydet,
    dashboard_widgets_sql_oku,
    satir_widget_kaydina_donustur,
    widget_kaydini_satira_donustur,
)
from src.depolar_listesi_sql import (
    depo_kaydini_satira_donustur,
    depolar_listesi_sql_kaydet,
    depolar_listesi_sql_oku,
    satir_depo_kaydina_donustur,
)
from src.kritik_seviyeler_sql import (
    kritik_kaydini_satira_donustur,
    kritik_seviyeler_sql_kaydet,
    kritik_seviyeler_sql_oku,
    satir_kritik_kaydina_donustur,
)
from src.kullanim_loglari_sql import (
    kullanim_loglari_sql_kaydet,
    kullanim_loglari_sql_oku,
    log_kaydini_satira_donustur,
    satir_log_kaydina_donustur,
)
from src.silinen_urun_loglari_sql import (
    satir_silinen_kaydina_donustur,
    silinen_kaydini_satira_donustur,
    silinen_urun_loglari_sql_kaydet,
    silinen_urun_loglari_sql_oku,
)
from src.yemek_uretim_arsivi_sql import (
    satir_uretim_kaydina_donustur,
    uretim_kaydini_satira_donustur,
    yemek_uretim_arsivi_sql_kaydet,
    yemek_uretim_arsivi_sql_oku,
)


class _SahteYanit:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _SahteSession:
    def __init__(self, get_payload=None, post_payload=None, get_responses=None):
        self.get_payload = get_payload if get_payload is not None else []
        self.post_payload = post_payload
        self._get_responses = list(get_responses) if get_responses is not None else []
        self.deletes = []
        self.posts = []

    def get(self, url, headers=None, params=None, timeout=10):
        if self._get_responses:
            return self._get_responses.pop(0)
        return _SahteYanit(200, self.get_payload)

    def delete(self, url, headers=None, params=None, timeout=10):
        self.deletes.append((url, params))
        return _SahteYanit(204, None)

    def post(self, url, headers=None, json=None, timeout=10):
        self.posts.append((url, json))
        donen = self.post_payload if self.post_payload is not None else (json or [])
        return _SahteYanit(201, donen)


def _baslik_fn(ekstra=None):
    base = {"apikey": "test-key", "Authorization": "Bearer test-key"}
    if ekstra:
        base.update(ekstra)
    return base


def test_kullanim_loglari_donusum_ve_senkronizasyon():
    kayit = {
        "id": "LOG-1",
        "urun": "Mercimek",
        "tur": "İade",
        "tarih": "2026-11-20",
        "miktar": "12,5",
        "birim": "kg",
        "aciklama": "SKT iade",
        "islem_yapan": "Depocu",
        "iade_nedeni": "Son kullanma",
    }
    satir = log_kaydini_satira_donustur(kayit)
    assert satir["miktar"] == 12.5
    assert satir["ekstra_alanlar"]["iade_nedeni"] == "Son kullanma"

    geri = satir_log_kaydina_donustur(satir)
    assert geri["miktar"] == 12.5
    assert geri["iade_nedeni"] == "Son kullanma"

    session = _SahteSession(get_payload=[{"id": "LOG-1"}, {"id": "ESKI-LOG"}])
    ok, sonuc = kullanim_loglari_sql_kaydet(
        [kayit], "https://ornek.supabase.co", _baslik_fn, lambda: session
    )
    assert ok is True
    assert session.deletes == [
        ("https://ornek.supabase.co/rest/v1/kullanim_loglari", {"id": "eq.ESKI-LOG"})
    ]
    assert len(sonuc) == 1

    durum, okunan = kullanim_loglari_sql_oku(
        "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession(get_payload=[satir])
    )
    assert durum == "ok"
    assert okunan[0]["urun"] == "Mercimek"


def test_yemek_uretim_arsivi_donusum_ve_senkronizasyon():
    kayit = {
        "id": "UR-1",
        "yemek_adi": "Yayla Çorbası",
        "tarih": "2026-11-21",
        "zaman": "11:30",
        "kisi_sayisi": "450",
        "islem_yapan": "Aşçıbaşı",
        "menu_ogeleri": {"ana_yemek": "Yayla Çorbası"},
        "malzemeler": [{"urun": "Pirinç", "miktar": 15}],
        "toplam_kalori": 620,
    }
    satir = uretim_kaydini_satira_donustur(kayit)
    assert satir["kisi_sayisi"] == 450.0
    assert satir["ekstra_alanlar"]["toplam_kalori"] == 620

    geri = satir_uretim_kaydina_donustur(satir)
    assert geri["menu_ogeleri"]["ana_yemek"] == "Yayla Çorbası"
    assert geri["toplam_kalori"] == 620

    session = _SahteSession(get_payload=[])
    ok, _ = yemek_uretim_arsivi_sql_kaydet(
        [kayit], "https://ornek.supabase.co", _baslik_fn, lambda: session
    )
    assert ok is True
    assert len(session.posts) == 1

    durum, okunan = yemek_uretim_arsivi_sql_oku(
        "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession(get_payload=[satir])
    )
    assert durum == "ok"
    assert okunan[0]["yemek_adi"] == "Yayla Çorbası"


def test_dagitim_ve_silinen_urun_loglari_donusum_ve_senkronizasyon():
    dag_kayit = {
        "id": "DAG-1",
        "tarih": "2026-11-22",
        "zaman": "12:15",
        "islem_yapan": "Dağıtım Sorumlusu",
        "bolge": "Merkez",
    }
    dag_satir = dagitim_kaydini_satira_donustur(dag_kayit)
    assert dag_satir["ekstra_alanlar"]["bolge"] == "Merkez"
    assert satir_dagitim_kaydina_donustur(dag_satir)["bolge"] == "Merkez"

    d_ok, _ = dagitim_loglari_sql_kaydet(
        [dag_kayit], "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession()
    )
    d_durum, d_okunan = dagitim_loglari_sql_oku(
        "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession(get_payload=[dag_satir])
    )
    assert d_ok is True
    assert d_durum == "ok"
    assert d_okunan[0]["id"] == "DAG-1"

    sil_kayit = {
        "id": "SIL-1",
        "urun": "Kuru Fasulye",
        "tarih": "2026-11-22",
        "miktar": "8",
        "birim": "kg",
        "islem_yapan": "Depocu",
        "silme_nedeni": "Hatalı giriş",
    }
    sil_satir = silinen_kaydini_satira_donustur(sil_kayit)
    assert sil_satir["miktar"] == 8.0
    assert satir_silinen_kaydina_donustur(sil_satir)["silme_nedeni"] == "Hatalı giriş"

    s_ok, _ = silinen_urun_loglari_sql_kaydet(
        [sil_kayit], "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession()
    )
    s_durum, s_okunan = silinen_urun_loglari_sql_oku(
        "https://ornek.supabase.co", _baslik_fn, lambda: _SahteSession(get_payload=[sil_satir])
    )
    assert s_ok is True
    assert s_durum == "ok"
    assert s_okunan[0]["urun"] == "Kuru Fasulye"


def test_depolar_listesi_donusum_ve_senkronizasyon():
    satir = depo_kaydini_satira_donustur("Soğuk Hava Deposu +5/+6", sira=1)
    assert satir["id"] == "DEPO-001"
    assert satir["depo_adi"] == "Soğuk Hava Deposu +5/+6"
    assert satir["sira_no"] == 1
    assert satir_depo_kaydina_donustur(satir) == "Soğuk Hava Deposu +5/+6"

    session = _SahteSession(get_payload=[{"id": "DEPO-001"}, {"id": "DEPO-003"}])
    ok, _ = depolar_listesi_sql_kaydet(
        ["Soğuk Hava Deposu +5/+6"], "https://ornek.supabase.co", _baslik_fn, lambda: session
    )
    assert ok is True
    assert session.deletes == [
        ("https://ornek.supabase.co/rest/v1/depolar_listesi", {"id": "eq.DEPO-003"})
    ]
    assert len(session.posts) == 1

    durum, okunan = depolar_listesi_sql_oku(
        "https://ornek.supabase.co",
        _baslik_fn,
        lambda: _SahteSession(
            get_payload=[
                {"id": "DEPO-001", "depo_adi": "Soğuk Hava Deposu +5/+6", "sira_no": 1},
                {"id": "DEPO-002", "depo_adi": "Kuru Gıda Deposu", "sira_no": 2},
            ]
        ),
    )
    assert durum == "ok"
    assert okunan == ["Soğuk Hava Deposu +5/+6", "Kuru Gıda Deposu"]


def test_kritik_seviyeler_donusum_ve_senkronizasyon():
    satir = kritik_kaydini_satira_donustur("ARPA ŞEHRİYE", "5,5")
    assert satir["urun_anahtari"] == "ARPA ŞEHRİYE"
    assert satir["kritik_miktar"] == 5.5
    assert satir_kritik_kaydina_donustur(satir) == ("ARPA ŞEHRİYE", 5.5)

    session = _SahteSession(
        get_payload=[{"urun_anahtari": "ARPA ŞEHRİYE"}, {"urun_anahtari": "ESKİ ÜRÜN"}]
    )
    ok, _ = kritik_seviyeler_sql_kaydet(
        {"ARPA ŞEHRİYE": 5.5}, "https://ornek.supabase.co", _baslik_fn, lambda: session
    )
    assert ok is True
    assert session.deletes == [
        (
            "https://ornek.supabase.co/rest/v1/kritik_seviyeler",
            {"urun_anahtari": "eq.ESKİ ÜRÜN"},
        )
    ]
    assert len(session.posts) == 1

    durum, sozluk = kritik_seviyeler_sql_oku(
        "https://ornek.supabase.co",
        _baslik_fn,
        lambda: _SahteSession(
            get_payload=[
                {
                    "urun_anahtari": "ARPA ŞEHRİYE",
                    "kritik_miktar": 5.5,
                    "birim": "",
                    "ekstra_alanlar": {},
                }
            ]
        ),
    )
    assert durum == "ok"
    assert sozluk == {"ARPA ŞEHRİYE": 5.5}


def test_dashboard_widgets_donusum_ve_senkronizasyon():
    satir = widget_kaydini_satira_donustur(
        {"id": "w1", "baslik": "Stok Grafiği", "tur": "Sütun Grafik", "aktif": "false"},
        sira=1,
    )
    assert satir["id"] == "w1"
    assert satir["aktif"] is False
    assert satir["sira_no"] == 1
    assert satir_widget_kaydina_donustur(satir) == {
        "id": "w1",
        "baslik": "Stok Grafiği",
        "tur": "Sütun Grafik",
        "aktif": False,
    }

    session = _SahteSession(get_payload=[{"id": "w1"}, {"id": "w9"}])
    ok, _ = dashboard_widgets_sql_kaydet(
        [{"id": "w1", "baslik": "Stok Grafiği", "tur": "Sütun Grafik", "aktif": False}],
        "https://ornek.supabase.co",
        _baslik_fn,
        lambda: session,
    )
    assert ok is True
    assert session.deletes == [
        ("https://ornek.supabase.co/rest/v1/dashboard_widgets", {"id": "eq.w9"})
    ]
    assert len(session.posts) == 1

    durum, widgetler = dashboard_widgets_sql_oku(
        "https://ornek.supabase.co",
        _baslik_fn,
        lambda: _SahteSession(
            get_payload=[
                {
                    "id": "w1",
                    "baslik": "Stok Grafiği",
                    "tur": "Sütun Grafik",
                    "aktif": False,
                    "sira_no": 1,
                }
            ]
        ),
    )
    assert durum == "ok"
    assert widgetler[0]["id"] == "w1"
    assert widgetler[0]["aktif"] is False
