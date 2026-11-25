# src/veri_yonetimi.py
from src.dagitim_loglari_sql import (
    dagitim_loglari_sql_kaydet,
    dagitim_loglari_sql_oku,
)
from src.dashboard_widgets_sql import (
    dashboard_widgets_sql_kaydet,
    dashboard_widgets_sql_oku,
)
from src.demirbaslar_listesi_sql import (
    demirbaslar_listesi_sql_kaydet,
    demirbaslar_listesi_sql_oku,
)
from src.depolar_listesi_sql import (
    depolar_listesi_sql_kaydet,
    depolar_listesi_sql_oku,
)
from src.kritik_seviyeler_sql import (
    kritik_seviyeler_sql_kaydet,
    kritik_seviyeler_sql_oku,
)
from src.kullanim_loglari_sql import (
    kullanim_loglari_sql_kaydet,
    kullanim_loglari_sql_oku,
)
from src.personel_izinleri_sql import (
    personel_izinleri_sql_kaydet,
    personel_izinleri_sql_oku,
)
from src.silinen_urun_loglari_sql import (
    silinen_urun_loglari_sql_kaydet,
    silinen_urun_loglari_sql_oku,
)
from src.stok_sql_db import stok_girisleri_sql_kaydet, stok_girisleri_sql_oku
from src.yemek_uretim_arsivi_sql import (
    yemek_uretim_arsivi_sql_kaydet,
    yemek_uretim_arsivi_sql_oku,
)

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {"tarih": "2026-04-23", "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı"},
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {"tarih": "2026-05-19", "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı"},
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"},
]

varsayilan_depolar = [
    "Soğuk Hava Deposu +5/+6",
    "Soğuk Hava Deposu -18",
    "Sebze Deposu",
    "Kuru Gıda Deposu"
]

varsayilan_demirbaslar = [
    {
        "id": "DEM-001",
        "ad": "Endüstriyel Çorba Kazanı",
        "kategori": "Mutfak Ekipmanı",
        "adet": 2,
        "durum": "Sağlam",
        "zimmet": "Aşçıbaşı",
        "tarih": "2026-01-15"
    }
]

varsayilan_widgets = [
    {
        "id": "w1",
        "baslik": "Kategori Bazlı Stok Dağılımı (Sütun Grafik)",
        "tur": "Sütun Grafik",
        "aktif": True,
    },
    {
        "id": "w2",
        "baslik": "Aylık Fire ve Zayiat Trendi (Çizgi Grafik)",
        "tur": "Çizgi Grafik",
        "aktif": True,
    },
]


def _supabase_baglamini_al():
    from src.app_runtime import (
        SUPABASE_KEY,
        SUPABASE_URL,
        _supa_basliklar,
        get_http_session,
        supabase_veri_kaydet,
        supabase_veri_oku,
    )
    return (
        SUPABASE_URL,
        SUPABASE_KEY,
        _supa_basliklar,
        get_http_session,
        supabase_veri_oku,
        supabase_veri_kaydet,
    )


def widgetlari_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = dashboard_widgets_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("dashboard_widgets", varsayilan_widgets)


def widgetlari_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = dashboard_widgets_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("dashboard_widgets", veri, zorla=True)
    else:
        supabase_veri_kaydet("dashboard_widgets", veri)


def depoları_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = depolar_listesi_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("depolar_listesi", varsayilan_depolar)


def depoları_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = depolar_listesi_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("depolar_listesi", veri, zorla=True)
    else:
        supabase_veri_kaydet("depolar_listesi", veri)


def demirbasları_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = demirbaslar_listesi_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("demirbaslar_listesi", varsayilan_demirbaslar)


def demirbasları_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = demirbaslar_listesi_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("demirbaslar_listesi", veri, zorla=True)
    else:
        supabase_veri_kaydet("demirbaslar_listesi", veri)


def kritik_seviyeleri_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = kritik_seviyeler_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, dict) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("kritik_seviyeler", {})


def kritik_seviyeleri_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = kritik_seviyeler_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("kritik_seviyeler", veri, zorla=True)
    else:
        supabase_veri_kaydet("kritik_seviyeler", veri)


def verileri_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = stok_girisleri_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("girisler", [])


def verileri_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = stok_girisleri_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("girisler", veri, zorla=True)
    else:
        supabase_veri_kaydet("girisler", veri)


def loglari_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = kullanim_loglari_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("kullanim_loglari", [])


def loglari_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = kullanim_loglari_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("kullanim_loglari", veri, zorla=True)
    else:
        supabase_veri_kaydet("kullanim_loglari", veri)


def silinen_urun_loglarini_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = silinen_urun_loglari_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("silinen_urun_loglari", [])


def silinen_urun_loglarini_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = silinen_urun_loglari_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("silinen_urun_loglari", veri, zorla=True)
    else:
        supabase_veri_kaydet("silinen_urun_loglari", veri)


def dagitim_loglarini_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = dagitim_loglari_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("dagitim_loglari", [])


def dagitim_loglarini_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = dagitim_loglari_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("dagitim_loglari", veri, zorla=True)
    else:
        supabase_veri_kaydet("dagitim_loglari", veri)


def personel_izinlerini_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = personel_izinleri_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("personel_izinleri", [])
    return veri if isinstance(veri, list) else []


def personel_izinlerini_kaydet(veri_listesi):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = personel_izinleri_sql_kaydet(veri_listesi, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("personel_izinleri", veri_listesi, zorla=True)
    else:
        supabase_veri_kaydet("personel_izinleri", veri_listesi)


def resmi_tatilleri_yukle():
    from src.app_runtime import supabase_veri_oku
    return supabase_veri_oku("resmi_tatiller", varsayilan_resmi_tatiller)


def yemek_uretim_arsivini_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = yemek_uretim_arsivi_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    return supabase_veri_oku("yemek_uretim_arsivi", [])


def yemek_uretim_arsivini_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = yemek_uretim_arsivi_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("yemek_uretim_arsivi", veri, zorla=True)
    else:
        supabase_veri_kaydet("yemek_uretim_arsivi", veri)

def test_silme_stoku_iade_et(girisler, silinen_kayitlar):
    """Silinen test kayıtlarına bağlı stok miktarlarını `girisler` listesine iade eder."""
    guncel_girisler = [dict(g) if isinstance(g, dict) else g for g in (girisler or [])]
    iade_edilen_adet = 0

    for kayit in silinen_kayitlar or []:
        if not isinstance(kayit, dict):
            continue
        urun_adi = str(
            kayit.get("urun")
            or kayit.get("urun_adi")
            or kayit.get("ad")
            or ""
        ).strip()
        if not urun_adi:
            continue

        miktar_ham = kayit.get("miktar")
        if miktar_ham is None:
            continue
        try:
            miktar = float(str(miktar_ham).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if miktar <= 0:
            continue

        for giris in guncel_girisler:
            if not isinstance(giris, dict):
                continue
            g_urun = str(
                giris.get("urun")
                or giris.get("urun_adi")
                or giris.get("ad")
                or ""
            ).strip()
            if g_urun.lower() == urun_adi.lower():
                mevcut = giris.get("miktar", giris.get("kalan_miktar", 0))
                try:
                    mevcut_sayi = float(str(mevcut).replace(",", "."))
                except (TypeError, ValueError):
                    mevcut_sayi = 0.0
                yeni_deger = mevcut_sayi + miktar
                if "miktar" in giris:
                    giris["miktar"] = yeni_deger
                elif "kalan_miktar" in giris:
                    giris["kalan_miktar"] = yeni_deger
                else:
                    giris["miktar"] = yeni_deger
                iade_edilen_adet += 1
                break

    return guncel_girisler, iade_edilen_adet
