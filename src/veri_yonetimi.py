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
from src.tedarikciler_sql import (
    tedarikciler_sql_kaydet,
    tedarikciler_sql_oku,
)
from src.tedarikciler_sql import (
    tedarikciler_sql_kaydet,
    tedarikciler_sql_oku,
)
from src.arac_seferleri_sql import (
    arac_seferleri_sql_kaydet,
    arac_seferleri_sql_oku,
)
from src.haftalik_menu_sql import (
    haftalik_menu_sql_kaydet,
    haftalik_menu_sql_oku,
)
from src.rota_teslimat_sql import (
    rota_teslimat_sql_kaydet,
    rota_teslimat_sql_oku,
)
from src.denetim_izi_sql import (
    denetim_izi_sql_kaydet,
    denetim_izi_sql_oku,
    denetim_kaydini_satira_donustur,
)
from src.sabah_brifingi_sql import (
    sabah_brifingi_sql_kaydet,
    sabah_brifingi_sql_oku,
    sabah_uyarisini_satira_donustur,
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

# --- Aziziye Aşevi Faz 1: Hazir Yemek Receteleri Entegrasyonu ---
from src.yemek_receteleri_sql import (
    hesapla_kalori_ve_maliyet as recete_hesapla_kalori_ve_maliyet,
    yemek_receteleri_sql_kaydet,
    yemek_receteleri_sql_oku,
)


def veri_yemek_receteleri_getir(
    client=None, bellek_depo=None, filtre_aktif=None
):
    return yemek_receteleri_sql_oku(
        client=client, bellek_depo=bellek_depo, filtre_aktif=filtre_aktif
    )


def veri_yemek_recetesi_kaydet(
    recete, client=None, bellek_depo=None, son_fiyat_saglayici=None
):
    saglayici = son_fiyat_saglayici
    if saglayici is None and "en_son_urun_birim_fiyati" in globals():
        saglayici = globals()["en_son_urun_birim_fiyati"]
    return yemek_receteleri_sql_kaydet(
        recete=recete,
        client=client,
        bellek_depo=bellek_depo,
        son_fiyat_saglayici=saglayici,
    )


def veri_recete_kalori_maliyet_hesapla(
    kalemler, porsiyon_sayisi=1.0, son_fiyat_saglayici=None
):
    saglayici = son_fiyat_saglayici
    if saglayici is None and "en_son_urun_birim_fiyati" in globals():
        saglayici = globals()["en_son_urun_birim_fiyati"]
    return recete_hesapla_kalori_ve_maliyet(
        kalemler=kalemler,
        porsiyon_sayisi=porsiyon_sayisi,
        son_fiyat_saglayici=saglayici,
    )


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

def tedarikcileri_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = tedarikciler_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("tedarikciler", [])
    return veri if isinstance(veri, list) else []


def tedarikcileri_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = tedarikciler_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("tedarikciler", veri, zorla=True)
    else:
        supabase_veri_kaydet("tedarikciler", veri)

def tedarikcileri_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = tedarikciler_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("tedarikciler", veri, zorla=True)
    else:
        supabase_veri_kaydet("tedarikciler", veri)

def arac_seferlerini_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = arac_seferleri_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("arac_seferleri", [])
    return veri if isinstance(veri, list) else []


def arac_seferlerini_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = arac_seferleri_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("arac_seferleri", veri, zorla=True)
    else:
        supabase_veri_kaydet("arac_seferleri", veri)


def yemek_receteleri_listesini_yukle():
    sonuc = yemek_receteleri_sql_oku()
    if isinstance(sonuc, list):
        return sonuc
    if isinstance(sonuc, tuple) and len(sonuc) >= 2 and sonuc[0] == "ok" and isinstance(sonuc[1], list):
        return sonuc[1]
    _, _, _, _, supabase_veri_oku, _ = _supabase_baglamini_al()
    veri = supabase_veri_oku("yemek_receteleri", [])
    return veri if isinstance(veri, list) else []


def yemek_receteleri_listesini_kaydet(veri):
    liste = veri if isinstance(veri, list) else []
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()

    if url and anahtar:
        aktif_idler = {
            str(k.get("id")).strip()
            for k in liste
            if isinstance(k, dict) and k.get("id")
        }
        try:
            mevcut_resp = session_fn().get(
                f"{url}/rest/v1/yemek_receteleri",
                headers=basliklar_fn(),
                params={"select": "id"},
                timeout=10,
            )
            if mevcut_resp.status_code == 200:
                mevcut_idler = {
                    str(r.get("id")).strip()
                    for r in (mevcut_resp.json() or [])
                    if r.get("id")
                }
                for sil_id in mevcut_idler - aktif_idler:
                    session_fn().delete(
                        f"{url}/rest/v1/yemek_receteleri",
                        headers=basliklar_fn({"Prefer": "return=minimal"}),
                        params={"id": f"eq.{sil_id}"},
                        timeout=10,
                    )
        except Exception:
            pass

    for kayit in liste:
        if isinstance(kayit, dict):
            yemek_receteleri_sql_kaydet(recete=kayit)

    if url and anahtar:
        supabase_veri_kaydet("yemek_receteleri", liste, zorla=True)

def haftalik_menu_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = haftalik_menu_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("haftalik_menu", [])
    return veri if isinstance(veri, list) else []


def haftalik_menu_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = haftalik_menu_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("haftalik_menu", veri, zorla=True)
    else:
        supabase_veri_kaydet("haftalik_menu", veri)

def rota_teslimat_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = rota_teslimat_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("rota_teslimat", [])
    return veri if isinstance(veri, list) else []


def rota_teslimat_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = rota_teslimat_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("rota_teslimat", veri, zorla=True)
    else:
        supabase_veri_kaydet("rota_teslimat", veri)

def denetim_izi_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = denetim_izi_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("denetim_izi", [])
    return veri if isinstance(veri, list) else []


def denetim_izi_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = denetim_izi_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("denetim_izi", veri, zorla=True)
    else:
        supabase_veri_kaydet("denetim_izi", veri)


def denetim_kaydi_ekle(
    mevcut_kayitlar,
    modul,
    islem,
    kullanici="sistem",
    rol="",
    kayit_id="",
    onceki_veri=None,
    sonraki_veri=None,
    maks_kayit=500,
):
    """Yeni bir denetim izi kaydı oluşturup listenin başına ekler."""
    liste = list(mevcut_kayitlar) if isinstance(mevcut_kayitlar, list) else []
    mevcut_id_sayisi = len(liste) + 1
    yeni_satir = denetim_kaydini_satira_donustur(
        {
            "id": f"DNT-{mevcut_id_sayisi:05d}",
            "kullanici": kullanici,
            "rol": rol,
            "modul": modul,
            "islem": islem,
            "kayit_id": kayit_id,
            "onceki_veri": onceki_veri,
            "sonraki_veri": sonraki_veri,
        },
        sira=mevcut_id_sayisi,
    )
    # Benzersiz ID garantisi
    mevcut_idler = {str(k.get("id") or "") for k in liste if isinstance(k, dict)}
    sayac = mevcut_id_sayisi
    while yeni_satir["id"] in mevcut_idler:
        sayac += 1
        yeni_satir["id"] = f"DNT-{sayac:05d}"

    guncel = [yeni_satir] + liste
    if maks_kayit and len(guncel) > maks_kayit:
        guncel = guncel[:maks_kayit]
    return guncel

def sabah_brifingi_yukle():
    url, anahtar, basliklar_fn, session_fn, supabase_veri_oku, _ = _supabase_baglamini_al()
    if url and anahtar:
        durum, sql_kayitlar = sabah_brifingi_sql_oku(url, basliklar_fn, session_fn)
        if durum == "ok" and isinstance(sql_kayitlar, list) and len(sql_kayitlar) > 0:
            return sql_kayitlar
    veri = supabase_veri_oku("sabah_brifingi_uyarilari", [])
    return veri if isinstance(veri, list) else []


def sabah_brifingi_kaydet(veri):
    url, anahtar, basliklar_fn, session_fn, _, supabase_veri_kaydet = _supabase_baglamini_al()
    if not url or not anahtar:
        return
    sql_ok, _ = sabah_brifingi_sql_kaydet(veri, url, basliklar_fn, session_fn)
    if sql_ok:
        supabase_veri_kaydet("sabah_brifingi_uyarilari", veri, zorla=True)
    else:
        supabase_veri_kaydet("sabah_brifingi_uyarilari", veri)


def sabah_brifingi_uyarisi_olustur(
    mevcut_uyarilar,
    baslik,
    kategori="Genel",
    onem_seviyesi="Orta",
    detay="",
    kaynak_id="",
    tarih="",
    guncelleyen="",
):
    """Yeni veya güncellenmiş sabah brifingi uyarısı üretir; aynı kaynak_id için tekrar üretmez."""
    liste = list(mevcut_uyarilar) if isinstance(mevcut_uyarilar, list) else []
    hedef_kaynak = str(kaynak_id or "").strip()
    if hedef_kaynak:
        for kayit in liste:
            if isinstance(kayit, dict) and str(kayit.get("kaynak_id") or "").strip() == hedef_kaynak:
                return liste

    mevcut_idler = {str(k.get("id") or "").strip() for k in liste if isinstance(k, dict)}
    sira = len(liste) + 1
    yeni_id = f"BRF-{sira:04d}"
    while yeni_id in mevcut_idler:
        sira += 1
        yeni_id = f"BRF-{sira:04d}"

    yeni_satir = sabah_uyarisini_satira_donustur(
        {
            "id": yeni_id,
            "tarih": tarih,
            "kategori": kategori,
            "onem_seviyesi": onem_seviyesi,
            "baslik": baslik,
            "detay": detay,
            "kaynak_id": hedef_kaynak,
            "durum": "Aktif",
            "guncelleyen": guncelleyen,
        },
        sira=sira,
    )
    return [yeni_satir] + liste
