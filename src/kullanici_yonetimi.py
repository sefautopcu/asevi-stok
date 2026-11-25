# src/kullanici_yonetimi.py
import datetime
import secrets
import streamlit as st

from src.cekirdek import (
    metni_coz, metni_sifrele, SifrelemeHatasi, 
    sifre_hashle_yeni, sifre_politika_hatasi, yeni_id_uret
)

varsayilan_personeller = []

_ESKI_IZIN_TURU_ESLEME = {
    "Yıllık İzin": "Yıllık İzin",
    "Sağlık Raporu": "Hastalık / Rapor",
    "Saatlik İzin": "Mazeret İzni",
}

def ihtiyac_sahiplerini_yukle():
    from src.app_runtime import supabase_veri_oku
    ham_veri = supabase_veri_oku("ihtiyac_sahipleri", [])
    cozulmus_liste = []
    for k in ham_veri:
        k_kopya = k.copy()
        h_tc = k.get("tc_hane", "")
        h_tel = k.get("telefon", "")
        h_adr = k.get("adres", "")

        k_kopya["tc_hane"] = metni_coz(h_tc) if h_tc else ""
        k_kopya["telefon"] = metni_coz(h_tel) if h_tel else ""
        k_kopya["adres"] = metni_coz(h_adr) if h_adr else ""
        if "aktif" not in k_kopya:
            k_kopya["aktif"] = True
        cozulmus_liste.append(k_kopya)
    return cozulmus_liste

def ihtiyac_sahiplerini_kaydet(veri_listesi):
    from src.app_runtime import supabase_veri_kaydet
    try:
        sifrelenmis_liste = []
        for k in veri_listesi:
            k_kopya = k.copy()
            k_kopya["tc_hane"] = metni_sifrele(k.get("tc_hane", ""))
            k_kopya["telefon"] = metni_sifrele(k.get("telefon", ""))
            k_kopya["adres"] = metni_sifrele(k.get("adres", ""))
            sifrelenmis_liste.append(k_kopya)
    except SifrelemeHatasi as e:
        st.error(
            f"⚠️ **Kayıt YAPILMADI — hassas veri korunamadı.** {e} "
            "Fernet anahtarını ve sunucu durumunu kontrol edip tekrar deneyin. "
            "Hassas alanlar şifrelenmeden veritabanına yazılmaz."
        )
        st.stop()
    supabase_veri_kaydet("ihtiyac_sahipleri", sifrelenmis_liste)

def personelleri_yukle():
    from src.app_runtime import supabase_veri_oku
    ham_veri = supabase_veri_oku("personeller", varsayilan_personeller)
    cozulmus_p = []
    for p in ham_veri:
        p_kopya = p.copy()
        h_tc = p.get("tc", "")
        p_kopya["tc"] = metni_coz(h_tc) if h_tc else ""
        cozulmus_p.append(p_kopya)
    return cozulmus_p

def personelleri_kaydet(veri_listesi):
    from src.app_runtime import supabase_veri_kaydet
    try:
        sifrelenmis_p = []
        for p in veri_listesi:
            p_kopya = p.copy()
            p_kopya["tc"] = metni_sifrele(p.get("tc", ""))
            sifrelenmis_p.append(p_kopya)
    except SifrelemeHatasi as e:
        st.error(
            f"⚠️ **Kayıt YAPILMADI — hassas veri korunamadı.** {e} "
            "Fernet anahtarını kontrol edip tekrar deneyin."
        )
        st.stop()
    supabase_veri_kaydet("personeller", sifrelenmis_p)

def eski_izinleri_tasi():
    from src.app_runtime import personel_izinlerini_kaydet, simdi_tr_str
    mevcut = st.session_state.personel_izinleri
    anahtarlar = {
        (i.get("personel_ad"), i.get("izin_turu"), i.get("baslangic"), i.get("bitis"), i.get("aciklama"))
        for i in mevcut if i.get("kaynak") == "eski_kayit"
    }
    degisti = False
    for p in st.session_state.personeller:
        eskiler = p.get("izinler") or []
        if not eskiler:
            continue
        ad = p.get("ad_soyad", p.get("ad", p.get("isim", "-")))
        for iz in eskiler:
            eski_tur = iz.get("tur", "Yıllık İzin")
            tur = _ESKI_IZIN_TURU_ESLEME.get(eski_tur, "Resmi Görev / Diğer")
            bas = str(iz.get("baslangic", ""))
            bit = str(iz.get("bitis", bas))
            try:
                gun = (datetime.date.fromisoformat(bit) - datetime.date.fromisoformat(bas)).days + 1
            except Exception:
                gun = 0
            kayit_saat = None
            if eski_tur == "Saatlik İzin":
                kayit_saat = iz.get("saat", 0)
                gun = 0
                aciklama = f"Saatlik izin: {kayit_saat} saat ({iz.get('detay', '-')})"
            else:
                aciklama = str(iz.get("detay") or "Eski sistemden aktarıldı")
            anahtar = (ad, tur, bas, bit, aciklama)
            if anahtar in anahtarlar:
                continue
            yeni = {
                "id": yeni_id_uret("IZN-", mevcut),
                "personel_ad": ad,
                "izin_turu": tur,
                "baslangic": bas,
                "bitis": bit,
                "gun_sayisi": max(gun, 0),
                "aciklama": aciklama,
                "ekleme_tarihi": simdi_tr_str("%Y-%m-%d %H:%M"),
                "kaynak": "eski_kayit",
            }
            if kayit_saat is not None:
                yeni["saat"] = kayit_saat
            mevcut.append(yeni)
            anahtarlar.add(anahtar)
        p["izinler"] = []
        degisti = True
    if degisti:
        personel_izinlerini_kaydet(mevcut)
        personelleri_kaydet(st.session_state.personeller)

misafir_yasaklar_varsayilan = [
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu",
    "Yeni Mal Alımı / Fatura Ekle",
    "QR Kod ile Hızlı Sarfiyat",
    "Ürün Sil / Düzenle",
    "Fire / Zayiat Girişi",
    "Toplu Stok Düşümü & Sarfiyat",
    "Ürün Birim Fiyatları & Ay Analizi",
    "Günlük Yemek Üretimi & Maliyet Raporu",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
    "Kapsamlı Envanter ve Hareket Raporu",
    "Depo Yönetimi",
    "Demirbaş Yönetimi",
]

misafir_maskeler_varsayilan = [
    "1. Sayfa: Toplam Fire",
    "1. Sayfa: Stok Değeri",
    "2. Sayfa: Güncel Stok Durumu - Kalan Miktar",
    "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi",
    "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu",
]

def varsayilan_misafir_kaydi():
    return {
        "sifre": "",
        "tip": "misafir",
        "yasakli_menuler": list(misafir_yasaklar_varsayilan),
        "maskeli_alanlar": list(misafir_maskeler_varsayilan),
        "salt_okunur": True,
        "buton_metni": "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)",
        "buton_aktif": True,
    }

def varsayilan_kullanicilar_olustur():
    """İlk kurulumda kullanıcıları oluşturur. Kodda sabit şifre YOKTUR."""
    from src.app_runtime import secret_deger
    kayit = {}
    uretilenler = {}
    for ad, tip, salt_okunur, secret_adi in (
        ("admin", "admin", False, "ADMIN_INITIAL_PASSWORD"),
        ("asci", "personel", False, "ASCI_INITIAL_PASSWORD"),
        ("yonetim", "personel", True, "YONETIM_INITIAL_PASSWORD"),
    ):
        try:
            sifre = str(secret_deger(secret_adi, "") or "")
        except Exception:
            sifre = ""

        rastgele = False
        if not sifre:
            sifre = secrets.token_urlsafe(9)
            uretilenler[ad] = sifre
            rastgele = True
            uygun = True
        else:
            uygun = not sifre_politika_hatasi(sifre)

        kayit[ad] = {
            "sifre": sifre_hashle_yeni(sifre),
            "tip": tip,
            "yasakli_menuler": [],
            "maskeli_alanlar": [],
            "salt_okunur": salt_okunur,
        }

        if rastgele or not uygun:
            kayit[ad]["sifre_degistirilmeli"] = True

    kayit["misafir"] = varsayilan_misafir_kaydi()
    if uretilenler:
        st.session_state["ilk_kurulum_sifreleri"] = uretilenler
    return kayit

def kullanıcıları_yukle():
    from src.app_runtime import _supabase_ham_oku, supabase_veri_kaydet
    from src.supabase_db import SUPABASE_URL, SUPABASE_KEY
    
    db_durumu = "yok"
    if SUPABASE_URL and SUPABASE_KEY:
        db_durumu, ham_data = _supabase_ham_oku("kullanici_yetkileri")
        data = ham_data if db_durumu == "ok" else None
    else:
        data = None
    ilk_kurulum = (not isinstance(data, dict)) or (not data)
    if ilk_kurulum:
        data = varsayilan_kullanicilar_olustur()
    for k, v in data.items():
        if "yasakli_menuler" not in v:
            v["yasakli_menuler"] = []
        if "maskeli_alanlar" not in v:
            v["maskeli_alanlar"] = []
        if "salt_okunur" not in v:
            v["salt_okunur"] = (k in ["yonetim", "misafir"])
        elif k in ["yonetim", "misafir"]:
            v["salt_okunur"] = True

        if k == "misafir":
            if not v["yasakli_menuler"]:
                v["yasakli_menuler"] = misafir_yasaklar_varsayilan
            if not v["maskeli_alanlar"]:
                v["maskeli_alanlar"] = misafir_maskeler_varsayilan

        sifre_deger = v.get("sifre", "")
        if (
            sifre_deger
            and k != "misafir"
            and not str(sifre_deger).startswith("s1$")
            and len(str(sifre_deger)) != 64
        ):
            v["sifre"] = sifre_hashle_yeni(sifre_deger)

    if "misafir" not in data:
        data["misafir"] = varsayilan_misafir_kaydi()
    else:
        if "buton_metni" not in data["misafir"]:
            data["misafir"]["buton_metni"] = "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)"
        if "buton_aktif" not in data["misafir"]:
            data["misafir"]["buton_aktif"] = True
        if not data["misafir"]["yasakli_menuler"]:
            data["misafir"]["yasakli_menuler"] = misafir_yasaklar_varsayilan
        if not data["misafir"]["maskeli_alanlar"]:
            data["misafir"]["maskeli_alanlar"] = misafir_maskeler_varsayilan

    if ilk_kurulum and db_durumu == "yok":
        kullanıcıları_kaydet(data)
    return data

def kullanıcıları_kaydet(veri):
    from src.app_runtime import supabase_veri_kaydet
    supabase_veri_kaydet("kullanici_yetkileri", veri)
