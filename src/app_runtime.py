import base64
import datetime
import hashlib
import hmac
import io
import json
import math
import os
import re
import secrets
import time
from html import escape as html_escape
import difflib
import statistics
import zoneinfo
from decimal import Decimal, InvalidOperation
import requests
from cryptography.fernet import Fernet
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import logging                                    # YENİ
from concurrent.futures import ThreadPoolExecutor # YENİ

log = logging.getLogger("aziziye")
# Log formatını ayarla (tarih, saat, seviye ve mesaj)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

from src.cekirdek import (
    SifrelemeHatasi,
    ESKI_VARSAYILAN_HASHLER,
    _veri_hash,
    fernet_motoru,
    giris_sayaclarini_sifirla,
    idleri_benzersiz_yap,
    metni_coz,
    metni_sifrele,
    rapor_mail_durumunu_guncelle,
    rapor_verilerini_oku,
    sifre_dogrula,
    sifre_hashle,
    sifre_hashle_yeni,
    sifre_politika_hatasi,
    sifre_yukseltilmeli_mi,
    yeni_id_uret,
)
from src.besin_hesaplama import urun_kalori_hesapla


def secret_deger(anahtar, varsayilan=""):
    """Secrets dosyası yokken veya anahtar tanımlı değilken güvenli varsayılan döndürür."""
    try:
        return st.secrets.get(anahtar, varsayilan)
    except Exception:
        return varsayilan


def fire_partisi_etiketi(giris):
    """Fire seçicisinde stok girişini ürün, fatura ve kalan miktarla ayırt eder."""
    return (
        f"{str(giris.get('urun', '')).strip().upper()} | "
        f"Fatura: {giris.get('fatura_no') or 'BELİRTİLMEMİŞ'} | "
        f"Kalan: {giris.get('kalan', 0)} {giris.get('birim', '')} | "
        f"Tarih: {giris.get('tarih', '-')} | Kayıt: {giris.get('id', '-')}"
    )


def fire_partisi_detayi(giris, miktar):
    """Seçilen stok girişinin fatura ve birim fiyat bilgileriyle fire tutarını hesaplar."""
    if not isinstance(giris, dict):
        raise ValueError("Seçilen stok giriş kaydı geçersiz.")
    try:
        miktar = float(miktar)
        kalan = float(giris.get("kalan", 0) or 0)
    except (TypeError, ValueError) as hata:
        raise ValueError("Fire miktarı veya kalan stok sayısal değil.") from hata
    if miktar <= 0:
        raise ValueError("Fire miktarı 0'dan büyük olmalıdır.")
    if miktar > kalan:
        raise ValueError("Fire miktarı seçilen fatura kaydındaki stoktan büyük olamaz.")

    birim_fiyat = giris.get("birim_fiyat")
    try:
        if birim_fiyat in (None, ""):
            giris_miktari = float(giris.get("miktar", 0) or 0)
            toplam_fiyat = float(giris.get("fiyat", 0) or 0)
            birim_fiyat = toplam_fiyat / giris_miktari if giris_miktari > 0 else toplam_fiyat
        else:
            birim_fiyat = float(birim_fiyat)
    except (TypeError, ValueError) as hata:
        raise ValueError("Seçilen fatura kaydının birim fiyatı geçersiz.") from hata

    return {
        "giris_id": str(giris.get("id", "")),
        "fatura_no": str(giris.get("fatura_no") or "BELİRTİLMEMİŞ"),
        "miktar": miktar,
        "birim_fiyat": birim_fiyat,
        "tutar": miktar * birim_fiyat,
    }


def dashboard_skt_sayilarini_hesapla(girisler, bugun=None):
    """Yalnızca kalan stoğu olan ürünlerin SKT durumunu ürün bazında sayar."""
    bugun = bugun or datetime.date.today()
    urun_sktleri = {}

    for giris in girisler:
        urun = str(giris.get("urun", "")).strip().upper()
        if not urun:
            continue
        kalan = float(giris.get("kalan", 0) or 0)
        if not kalan > 0:
            continue

        skt = giris.get("skt")
        if not skt:
            continue
        try:
            skt_tarihi = datetime.datetime.strptime(str(skt), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        urun_sktleri.setdefault(urun, []).append(skt_tarihi)

    skt_kirmizi = 0
    skt_turuncu = 0
    for skt_tarihleri in urun_sktleri.values():
        kalan_gun = (min(skt_tarihleri) - bugun).days
        if kalan_gun < 0:
            skt_kirmizi += 1
        elif kalan_gun <= 7:
            skt_turuncu += 1

    return skt_kirmizi, skt_turuncu


def qr_paket_kalanini_hesapla(giris, sepet, paket_id):
    """QR paketin mevcut kalanından bu üretim sepetinde planlanan miktarı düşer."""
    try:
        paket_miktari = float(giris.get("paket_miktari", 0) or 0)
        durumlar = giris.get("paket_durumlari", {})
        if not isinstance(durumlar, dict):
            durumlar = {}
        kalan = float(durumlar.get(paket_id, paket_miktari) or 0)
        for item in sepet:
            if (
                item.get("paket_id") == paket_id
                and str(item.get("fatura_id")) == str(giris.get("id"))
            ):
                kalan -= float(item.get("miktar", 0) or 0)
    except (AttributeError, TypeError, ValueError) as hata:
        raise ValueError("QR paket miktar bilgisi geçersiz.") from hata
    return max(0.0, kalan)


def qr_acik_paketleri_bul(girisler, sepet, urun):
    """Ürünün kayıtlı veya mevcut üretim sepetinde açılmış paketlerini bulur."""
    aranan_urun = str(urun or "").strip().upper()
    acik_paketler = []
    for giris in girisler:
        if str(giris.get("urun", "")).strip().upper() != aranan_urun:
            continue
        try:
            paket_miktari = float(giris.get("paket_miktari", 0) or 0)
            durumlar = giris.get("paket_durumlari", {})
            if not isinstance(durumlar, dict):
                durumlar = {}
            paket_idleri = set(durumlar)
            paket_idleri.update(
                item.get("paket_id")
                for item in sepet
                if item.get("paket_id")
                and str(item.get("fatura_id")) == str(giris.get("id"))
            )
        except (AttributeError, TypeError, ValueError) as hata:
            raise ValueError("QR paket durum bilgisi geçersiz.") from hata
        if paket_miktari <= 0:
            continue

        for paket_id in sorted(paket_idleri, key=str):
            kalan = qr_paket_kalanini_hesapla(giris, sepet, paket_id)
            if 0 < kalan < paket_miktari:
                acik_paketler.append({
                    "paket_id": paket_id,
                    "fatura_id": giris.get("id"),
                    "kalan": kalan,
                    "birim": giris.get("birim", ""),
                })
    return acik_paketler


def qr_paket_secim_engeli(girisler, sepet, urun, secilen_paket_id):
    """Açık paket varken önce onu bitirmeyi zorunlu kılar."""
    acik_paketler = qr_acik_paketleri_bul(girisler, sepet, urun)
    if acik_paketler and acik_paketler[0]["paket_id"] != secilen_paket_id:
        return acik_paketler[0]
    return None


def qr_kod_degerleri(giris):
    """Stok girişindeki her paket için ayrı QR değeri, dökme stok için tek ID üretir."""
    giris_id = str(giris.get("id", "")).strip()
    if not giris_id:
        raise ValueError("Stok giriş kaydının ID bilgisi bulunamadı.")
    try:
        toplam_miktar = Decimal(str(giris.get("miktar", 0) or 0))
        paket_miktari = Decimal(str(giris.get("paket_miktari", 0) or 0))
    except (InvalidOperation, ValueError) as hata:
        raise ValueError("Stok veya paket miktarı geçersiz.") from hata
    if not toplam_miktar.is_finite() or not paket_miktari.is_finite():
        raise ValueError("Stok veya paket miktarı sonlu bir sayı olmalıdır.")
    if toplam_miktar < 0 or paket_miktari < 0:
        raise ValueError("Stok veya paket miktarı negatif olamaz.")
    if toplam_miktar == 0:
        return []
    if paket_miktari == 0:
        return [giris_id]

    paket_sayisi = int(toplam_miktar // paket_miktari)
    return [f"{giris_id}-P{sira}" for sira in range(1, paket_sayisi + 1)]


def yemek_sepeti_stok_hatalari(girisler, sepet):
    """Üretim sepetindeki tüm miktarların mevcut stoktan karşılanabildiğini doğrular."""
    stoklar = {}
    for giris in girisler:
        urun = str(giris.get("urun", "")).strip().upper()
        if not urun:
            continue
        try:
            kalan = float(giris.get("kalan", 0) or 0)
        except (TypeError, ValueError) as hata:
            raise ValueError(f"{urun} stok miktarı sayısal değil.") from hata
        if not math.isfinite(kalan):
            raise ValueError(f"{urun} stok miktarı geçersiz.")
        if kalan < 0:
            raise ValueError(f"{urun} stok miktarı negatif olamaz.")
        kayit_id = str(giris.get("id", ""))
        stoklar[kayit_id] = kalan

    paket_kalanlari = {}
    hatalar = []
    for sira, item in enumerate(sepet, start=1):
        urun = str(item.get("urun", "")).strip().upper()
        try:
            istenen = float(item.get("miktar", 0) or 0)
        except (TypeError, ValueError) as hata:
            raise ValueError(f"{urun or sira} için sepet miktarı sayısal değil.") from hata
        if not math.isfinite(istenen):
            raise ValueError(f"{urun or sira} için sepet miktarı geçersiz.")
        if not urun or istenen <= 0:
            hatalar.append(f"{urun or 'Malzeme'} için miktar 0'dan büyük olmalıdır.")
            continue

        paket_id = item.get("paket_id")
        fatura_id = str(item.get("fatura_id", "")) if item.get("fatura_id") else None
        uygun_kayitlar = [
            g for g in girisler
            if str(g.get("urun", "")).strip().upper() == urun
            and stoklar.get(str(g.get("id", "")), 0) > 0
            and (not fatura_id or str(g.get("id", "")) == fatura_id)
        ]
        kalan_dusulecek = istenen
        for giris in uygun_kayitlar:
            kayit_id = str(giris.get("id", ""))
            if paket_id:
                try:
                    durumlar = giris.get("paket_durumlari", {})
                    if not isinstance(durumlar, dict):
                        durumlar = {}
                    paket_miktari = float(giris.get("paket_miktari", 0) or 0)
                    paket_kalan = paket_kalanlari.get(
                        (kayit_id, str(paket_id)),
                        float(durumlar.get(
                            paket_id, paket_miktari
                        ) or 0),
                    )
                except (TypeError, ValueError) as hata:
                    raise ValueError(f"{urun} paket stok bilgisi geçersiz.") from hata
                if not math.isfinite(paket_kalan) or not math.isfinite(paket_miktari):
                    raise ValueError(f"{urun} paket stok bilgisi geçersiz.")
                dusulecek = min(kalan_dusulecek, paket_kalan, stoklar[kayit_id])
                paket_kalanlari[(kayit_id, str(paket_id))] = paket_kalan - dusulecek
            else:
                dusulecek = min(kalan_dusulecek, stoklar[kayit_id])

            stoklar[kayit_id] -= dusulecek
            kalan_dusulecek -= dusulecek
            if kalan_dusulecek <= 1e-9:
                break

        if kalan_dusulecek > 1e-9:
            toplam_istenen = 0.0
            for baska in sepet:
                if str(baska.get("urun", "")).strip().upper() != urun:
                    continue
                try:
                    baska_miktar = float(baska.get("miktar", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(baska_miktar):
                    toplam_istenen += baska_miktar
            toplam_kalan = sum(
                float(g.get("kalan", 0) or 0)
                for g in girisler
                if str(g.get("urun", "")).strip().upper() == urun
            )
            mesaj = (
                f"{urun}: sepette toplam istenen miktar ({toplam_istenen:g}), "
                f"mevcut stoktan karşılanamıyor (stok: {toplam_kalan:g})."
            )
            if paket_id:
                mesaj = (
                    f"{urun} ({paket_id}): bu fatura/paket kaydında "
                    f"istenen miktarın tamamı mevcut değil."
                )
            if mesaj not in hatalar:
                hatalar.append(mesaj)

    return hatalar


def yemek_menu_alanlari():
    return (
        ("ana_yemek", "Ana Yemek"),
        ("yardimci_yemek", "Yardımcı Yemek / Ara Yemek"),
        ("corba", "Çorba"),
        ("tatli_meyve_yogurt", "Tatlı / Meyve / Yoğurt"),
    )


def _malzeme_kullanim_anahtari(urun_adi):
    return "".join(str(urun_adi or "").split()).upper()


def yemek_menu_ogelerini_temizle(menu_ogeleri):
    if not isinstance(menu_ogeleri, dict):
        return {alan: "" for alan, _ in yemek_menu_alanlari()}
    return {
        alan: str(menu_ogeleri.get(alan, "") or "").strip()
        for alan, _ in yemek_menu_alanlari()
    }


def yemek_menu_ogelerini_kayittan_al(kayit):
    menu_ogeleri = yemek_menu_ogelerini_temizle(kayit.get("menu_ogeleri"))
    if not any(menu_ogeleri.values()):
        eski_ad = str(kayit.get("yemek_adi", "") or "").strip()
        if eski_ad and "/" not in eski_ad:
            menu_ogeleri["ana_yemek"] = eski_ad
    return menu_ogeleri


def yemek_arsiv_menu_kolonlari(kayit):
    menu_ogeleri = yemek_menu_ogelerini_kayittan_al(kayit)
    return {
        etiket: menu_ogeleri[alan] or "-"
        for alan, etiket in yemek_menu_alanlari()
    }


def yemek_kaydi_menu_ogelerini_guncelle(kayit, menu_ogeleri):
    temiz_menu = yemek_menu_ogelerini_temizle(menu_ogeleri)
    if not any(temiz_menu.values()):
        return False
    kayit["menu_ogeleri"] = temiz_menu
    kayit["yemek_adi"] = " / ".join(
        deger for deger in temiz_menu.values() if deger
    )
    return True


def yemek_malzeme_kullanim_istatistikleri(
    arsiv, menu_ogeleri, kisi_sayisi, referans_tarihi=None, referans_zamani=None
):
    """Aynı menü bölümlerinden geçmiş kişi başı malzeme ortalaması ve sapması."""
    if isinstance(menu_ogeleri, str):
        menu_ogeleri = {"ana_yemek": menu_ogeleri}
    aranan_menu = yemek_menu_ogelerini_temizle(menu_ogeleri)
    aranan_menu = {
        alan: _malzeme_kullanim_anahtari(ad)
        for alan, ad in aranan_menu.items()
        if ad
    }
    if not aranan_menu:
        return {}
    uretimler = []
    malzeme_adlari = set()
    for kayit in arsiv:
        kayit_menu = yemek_menu_ogelerini_kayittan_al(kayit)
        if not any(
            _malzeme_kullanim_anahtari(kayit_menu.get(alan))
            == aranan_ad
            for alan, aranan_ad in aranan_menu.items()
        ):
            continue
        if referans_tarihi:
            kayit_tarihi = str(kayit.get("tarih", ""))[:10]
            hedef_tarih = str(referans_tarihi)[:10]
            if not kayit_tarihi or kayit_tarihi > hedef_tarih:
                continue
            if (
                kayit_tarihi == hedef_tarih
                and referans_zamani
                and kayit.get("zaman")
            ):
                kayit_zamani = str(kayit.get("zaman", ""))
                if kayit_zamani >= str(referans_zamani):
                    continue
        try:
            kisi = float(kayit.get("kisi_sayisi", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(kisi) or kisi <= 0:
            continue
        malzeme_miktarlari = {}
        kayit_malzemeleri = kayit.get("malzemeler", [])
        if not isinstance(kayit_malzemeleri, list):
            continue
        for malzeme in kayit_malzemeleri:
            if not isinstance(malzeme, dict):
                continue
            ad = str(malzeme.get("urun", "")).strip()
            if not ad:
                continue
            try:
                miktar = float(malzeme.get("miktar", 0) or 0)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(miktar) or miktar < 0:
                continue
            anahtar = _malzeme_kullanim_anahtari(ad)
            malzeme_adlari.add(anahtar)
            malzeme_miktarlari[anahtar] = (
                malzeme_miktarlari.get(anahtar, {"ad": ad, "miktar": 0.0})
            )
            malzeme_miktarlari[anahtar]["miktar"] += miktar
        uretimler.append((kisi, malzeme_miktarlari))

    istatistikler = {}
    for anahtar in malzeme_adlari:
        kisi_basi_miktarlar = [
            miktarlar.get(anahtar, {}).get("miktar", 0.0) / kisi
            for kisi, miktarlar in uretimler
        ]
        istatistikler[anahtar] = {
            "ad": next(
                (miktarlar[anahtar]["ad"] for _, miktarlar in uretimler if anahtar in miktarlar),
                anahtar,
            ),
            "uretim_sayisi": len(kisi_basi_miktarlar),
            "ortalama_kisi_basi": statistics.fmean(kisi_basi_miktarlar),
            "sapma_kisi_basi": (
                statistics.pstdev(kisi_basi_miktarlar)
                if len(kisi_basi_miktarlar) > 1 else 0.0
            ),
        }

    try:
        bugunku_kisi = float(kisi_sayisi)
    except (TypeError, ValueError):
        bugunku_kisi = 0.0
    if not math.isfinite(bugunku_kisi):
        bugunku_kisi = 0.0
    for istatistik in istatistikler.values():
        ortalama = istatistik["ortalama_kisi_basi"]
        sapma = istatistik["sapma_kisi_basi"]
        tolerans = max(sapma, abs(ortalama) * 0.1)
        istatistik["beklenen_miktar"] = ortalama * bugunku_kisi
        istatistik["alt_sinir"] = max(0.0, (ortalama - tolerans) * bugunku_kisi)
        istatistik["ust_sinir"] = (ortalama + tolerans) * bugunku_kisi
    return istatistikler


def yemek_malzeme_kullanim_uyarilari(
    istatistikler, sepet, kisi_sayisi, birimler=None
):
    """Geçmişe göre kişi başı kullanımı belirgin farklı malzemeleri listeler."""
    bugunku_miktarlar = {}
    adlar = {}
    for item in sepet:
        ad = str(item.get("urun", "")).strip()
        if not ad:
            continue
        anahtar = _malzeme_kullanim_anahtari(ad)
        try:
            miktar = float(item.get("miktar", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(miktar):
            continue
        bugunku_miktarlar[anahtar] = bugunku_miktarlar.get(anahtar, 0.0) + miktar
        adlar[anahtar] = ad

    uyarilar = []
    for anahtar, miktar in bugunku_miktarlar.items():
        istatistik = istatistikler.get(anahtar)
        if not istatistik:
            continue
        if miktar < istatistik["alt_sinir"] or miktar > istatistik["ust_sinir"]:
            try:
                bugunku_kisi = float(kisi_sayisi)
            except (TypeError, ValueError):
                bugunku_kisi = 0.0
            kisi_basi_miktar = miktar / bugunku_kisi if bugunku_kisi > 0 else 0.0
            birim = (birimler or {}).get(anahtar, "")
            birim_eki = f" {birim}" if birim else ""
            uyarilar.append(
                f"{adlar[anahtar]}: bugün {miktar:g}{birim_eki} "
                f"(kişi başı {kisi_basi_miktar:g} "
                f"{birim_eki.strip()}/kişi) kullanılıyor; "
                f"{istatistik['uretim_sayisi']} geçmiş üretimde kişi başı ortalama "
                f"{istatistik['ortalama_kisi_basi']:g}, bugünkü kişi sayısına göre "
                f"beklenen yaklaşık miktar {istatistik['beklenen_miktar']:g} "
                f"(alışılagelen aralık {istatistik['alt_sinir']:g}–"
                f"{istatistik['ust_sinir']:g})."
            )
    return uyarilar


def _tema_tercihini_yukle(url_temasi, cerez_temasi):
    """Pure Dark arayüzü için geriye dönük tema değerlerini yok sayar."""
    return "Dark"


def _dashboard_arka_plan_data_uri(yuklenen_resim):
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(yuklenen_resim.getvalue())) as acilan_resim:
            resim = ImageOps.exif_transpose(acilan_resim)
            resim.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            if "A" in resim.getbands() or "transparency" in resim.info:
                rgba = resim.convert("RGBA")
                optimize_edilmis = Image.new("RGB", rgba.size, "#08131F")
                optimize_edilmis.paste(rgba, mask=rgba.getchannel("A"))
            else:
                optimize_edilmis = resim.convert("RGB")

            cikti = io.BytesIO()
            optimize_edilmis.save(cikti, format="JPEG", quality=85, optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError("Görsel okunamadı. Lütfen geçerli bir JPG veya PNG seçin.") from exc

    b64 = base64.b64encode(cikti.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _dashboard_arka_plan_yukleme_callback():
    yuklenen_resim = st.session_state.get("dashboard_bg_uploader")
    if yuklenen_resim is None:
        return
    try:
        st.session_state.dashboard_arka_plan = _dashboard_arka_plan_data_uri(
            yuklenen_resim
        )
    except ValueError as exc:
        st.session_state["_dashboard_bg_upload_error"] = str(exc)
        return
    st.session_state["_dashboard_bg_upload_success"] = True


# Sayfa Yapılandırması: Streamlit'te İLK komut olmak zorundadır
# (kenar çubuğu, önbellek vb. komutlardan önce çağrılmalıdır).
st.set_page_config(
    page_title="Aziziye - Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide",
)

APP_VERSION = "v2.0.0"
LAST_UPDATE = "Kasım 2026"


def simdi_tr_str(format_str="%Y-%m-%d %H:%M"):
    """Gerçek Türkiye saatini (Europe/Istanbul) döndürür."""
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).strftime(format_str)
    except Exception:
        return datetime.datetime.now().strftime(format_str)

def bellek_kullanimi_al():
    """Python sürecinin sunucuda kullandığı anlık RAM miktarını (MB) hesaplar."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 1)
    except Exception:
        return 0.0
        

def _rapor_html_metni(deger, varsayilan="-"):
    """Rapor HTML'inde kullanıcı/veritabanı kaynaklı metni güvenli biçimde gösterir."""
    return html_escape(str(varsayilan if deger is None else deger))


def manuel_rapor_maili_gonder(rapor_tipi="gunluk"):
    """Buton ile tetiklendiğinde çalışır, tarih/saat kontrolünü atlar ve veritabanına kayıt atmaz."""
    simdi = datetime.datetime.now()
    bugun = simdi.date()
    
    if rapor_tipi == "gunluk":
        baslangic_tarih = bugun - datetime.timedelta(days=1)
        bitis_tarih = baslangic_tarih
        rapor_baslik = "Günlük Rapor (Manuel)"
        rapor_tarih_str = baslangic_tarih.strftime("%d.%m.%Y")
    elif rapor_tipi == "haftalik":
        baslangic_tarih = bugun - datetime.timedelta(days=7)
        bitis_tarih = bugun - datetime.timedelta(days=1)
        rapor_baslik = "Haftalık Rapor (Manuel)"
        rapor_tarih_str = f"{baslangic_tarih.strftime('%d.%m.%Y')} - {bitis_tarih.strftime('%d.%m.%Y')}"
    else: # aylik
        ilk_gun = bugun.replace(day=1)
        gecen_ay_son_gun = ilk_gun - datetime.timedelta(days=1)
        baslangic_tarih = gecen_ay_son_gun.replace(day=1)
        bitis_tarih = gecen_ay_son_gun
        rapor_baslik = "Aylık Rapor (Manuel)"
        rapor_tarih_str = baslangic_tarih.strftime("%B %Y")

    baslangic_str = baslangic_tarih.strftime("%Y-%m-%d")
    bitis_str = bitis_tarih.strftime("%Y-%m-%d")
    
    try:
        rapor_verileri = rapor_verilerini_oku(_supabase_ham_oku)
    except (RuntimeError, ValueError) as e:
        log.error("Manuel rapor verileri okunamadı: %s", e)
        st.error("Rapor oluşturulamadı; veritabanı verileri alınamadı. Lütfen tekrar deneyin.")
        return False

    tum_girisler = rapor_verileri["girisler"]
    tum_kullanim_loglari = rapor_verileri["kullanim_loglari"]
    tum_silinenler = rapor_verileri["silinen_urun_loglari"]
    tum_yemekler = rapor_verileri["yemek_uretim_arsivi"]
    tum_izinler = rapor_verileri["personel_izinleri"]

    def tarih_filtrele(liste, anahtar="tarih"):
        return [item for item in liste if baslangic_str <= str(item.get(anahtar, ""))[:10] <= bitis_str]

    secilen_girisler = tarih_filtrele(tum_girisler)
    secilen_fireler = [l for l in tarih_filtrele(tum_kullanim_loglari) if l.get("tur") == "Fire/Zayiat"]
    secilen_silinenler = tarih_filtrele(tum_silinenler)
    secilen_yemekler = tarih_filtrele(tum_yemekler)
    
    secilen_izinler = []
    for i in tum_izinler:
        bas = str(i.get("baslangic", ""))
        bit = str(i.get("bitis", ""))
        if bas and bit and (baslangic_str <= bit and bitis_str >= bas):
            secilen_izinler.append(i)

    # HTML İçeriği (Aynı tasarım)
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            h2 {{ color: #10b981; margin-top: 0; }}
            h3 {{ color: #374151; border-bottom: 2px solid #10b981; padding-bottom: 8px; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }}
            th {{ background-color: #f3f4f6; padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; color: #4b5563; font-size: 13px; }}
            td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; color: #1f2937; }}
            .summary-table {{ width: 100%; border-collapse: separate; border-spacing: 10px 0; margin-bottom: 20px; }}
            .summary-card {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; text-align: center; width: 33%; }}
            .summary-title {{ font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold; }}
            .summary-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
            .yemek-box {{ background: #f9fafb; border-left: 4px solid #10b981; padding: 15px; margin-bottom: 15px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🍲 Aziziye Aşevi - {_rapor_html_metni(rapor_baslik)}</h2>
            <p style="color: #6b7280; font-size: 15px;"><b>Tarih:</b> {_rapor_html_metni(rapor_tarih_str)}</p>
            
            <table class="summary-table">
                <tr>
                    <td class="summary-card"><div class="summary-title">Yeni Stok Girişi</div><div class="summary-value" style="color: #10b981;">{len(secilen_girisler)}</div></td>
                    <td class="summary-card"><div class="summary-title">Fire / Zayiat</div><div class="summary-value" style="color: #ef4444;">{len(secilen_fireler)}</div></td>
                    <td class="summary-card"><div class="summary-title">Üretilen Yemek</div><div class="summary-value" style="color: #3b82f6;">{len(secilen_yemekler)}</div></td>
                </tr>
            </table>
    """

    if secilen_girisler:
        html += f"<h3>📦 Gelen Stok Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Fatura No</th></tr>"
        for g in secilen_girisler:
            html += f"<tr><td>{_rapor_html_metni(g.get('urun'))}</td><td>{_rapor_html_metni(g.get('miktar'))} {_rapor_html_metni(g.get('birim', ''), '')}</td><td>{_rapor_html_metni(g.get('fatura_no'))}</td></tr>"
        html += "</table>"

    if secilen_fireler:
        html += f"<h3>🗑️ Fire / Zayiat Girişleri</h3><table><tr><th>Ürün</th><th>Fatura No</th><th>Miktar</th><th>Tutar</th><th>Açıklama</th></tr>"
        for f in secilen_fireler:
            html += f"<tr><td>{_rapor_html_metni(f.get('urun'))}</td><td>{_rapor_html_metni(f.get('fatura_no'))}</td><td>{_rapor_html_metni(f.get('miktar'))}</td><td>{float(f.get('tutar', 0)):,.2f} ₺</td><td>{_rapor_html_metni(f.get('aciklama'))}</td></tr>"
        html += "</table>"

    if secilen_yemekler:
        html += f"<h3>🍲 Üretilen Yemekler</h3>"
        for y in secilen_yemekler:
            toplam_maliyet = float(y.get('toplam_maliyet', 0))
            kisi = int(y.get('kisi_sayisi', 1) or 1)
            kisi_basi = toplam_maliyet / kisi if kisi > 0 else 0
            html += f"<div class='yemek-box'><h4 style='margin: 0 0 10px 0; color: #111827;'>{_rapor_html_metni(y.get('tarih'))} - {_rapor_html_metni(y.get('yemek_adi'))} ({kisi} Kişilik)</h4>"
            html += f"<p style='margin: 0 0 10px 0; font-size: 14px; color: #4b5563;'><b>Toplam Maliyet:</b> {toplam_maliyet:,.2f} ₺ | <b>Kişi Başı:</b> {kisi_basi:,.2f} ₺</p></div>"

    if secilen_izinler:
        html += f"<h3>👥 Personel İzinleri</h3><table><tr><th>Personel</th><th>İzin Türü</th><th>Başlangıç</th><th>Bitiş</th></tr>"
        for i in secilen_izinler:
            html += f"<tr><td>{_rapor_html_metni(i.get('personel_ad'))}</td><td>{_rapor_html_metni(i.get('izin_turu'))}</td><td>{_rapor_html_metni(i.get('baslangic'))}</td><td>{_rapor_html_metni(i.get('bitis'))}</td></tr>"
        html += "</table>"

    if not (secilen_girisler or secilen_fireler or secilen_silinenler or secilen_yemekler or secilen_izinler):
        html += "<div style='text-align: center; padding: 30px; color: #6b7280;'><b>Bu dönemde sisteme girilmiş herhangi bir veri bulunmamaktadır.</b></div>"

    html += "</div></body></html>"

    # K1: Spinner göster ama toplam süre 10 sn ile sınırlı
    with st.spinner("📤 Rapor gönderiliyor..."):
        ok, hata = _smtp_gonder_senkron(
            f"Aziziye Aşevi {rapor_baslik} - {rapor_tarih_str}", html
        )
    if not ok:
        log.error("Manuel rapor hatası: %s", hata)
        return False
    return True

def _rapor_sahiplen(rapor_tipi, deger):
    """Aynı dönemin raporunu tekilleştirir ve gönderim için süreli sahiplenme alır."""
    sonuc = {"sahiplendi": False}
    claim_id = secrets.token_urlsafe(16)
    def _mutate(mevcut):
        yeni, sonuc["sahiplendi"] = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "sahiplen", claim_id
        )
        return yeni
    durum, _ = _atomik_dict_guncelle("mail_loglari", _mutate)
    return claim_id if durum == "ok" and sonuc["sahiplendi"] else None

def _rapor_geri_al(rapor_tipi, deger, claim_id):
    """Gönderim başarısızsa sahiplenmeyi bırak → bir sonraki tetikleme yeniden denesin."""
    def _mutate(mevcut):
        yeni, _ = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "basarisiz", claim_id
        )
        return yeni
    durum, sonuc = _atomik_dict_guncelle("mail_loglari", _mutate)
    if durum != "ok":
        log.error("Rapor gönderim durumu kaydedilemedi (basarisiz): %s", sonuc)

def _rapor_gonderim_tamamlandi(rapor_tipi, deger, claim_id):
    def _mutate(mevcut):
        yeni, _ = rapor_mail_durumunu_guncelle(
            mevcut, rapor_tipi, deger, time.time(), "tamamlandi", claim_id
        )
        return yeni

    durum, sonuc = _atomik_dict_guncelle("mail_loglari", _mutate)
    if durum != "ok":
        log.error("Rapor gönderildi fakat durumu kaydedilemedi: %s", sonuc)
        return False
    return True


def _rapor_icerigi_olustur(rapor_baslik, rapor_tarih_str, baslangic_str, bitis_str):
    """İki fonksiyondaki neredeyse birebir aynı HTML şablonunu birleştirir."""
    rapor_verileri = rapor_verilerini_oku(_supabase_ham_oku)
    tum_girisler = rapor_verileri["girisler"]
    tum_kullanim_loglari = rapor_verileri["kullanim_loglari"]
    tum_silinenler = rapor_verileri["silinen_urun_loglari"]
    tum_yemekler = rapor_verileri["yemek_uretim_arsivi"]
    tum_izinler = rapor_verileri["personel_izinleri"]

    def _filtre(liste, anahtar="tarih"):
        return [i for i in liste if baslangic_str <= str(i.get(anahtar, ""))[:10] <= bitis_str]

    secilen_girisler = _filtre(tum_girisler)
    secilen_fireler  = [l for l in _filtre(tum_kullanim_loglari) if l.get("tur") == "Fire/Zayiat"]
    secilen_silinenler = _filtre(tum_silinenler)
    secilen_yemekler = _filtre(tum_yemekler)
    secilen_izinler = [
        i for i in tum_izinler
        if str(i.get("baslangic", "")) and str(i.get("bitis", ""))
        and baslangic_str <= str(i.get("bitis", "")) and bitis_str >= str(i.get("baslangic", ""))
    ]

    html = f"""<html><head><style>
      body {{ font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
      .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px;
                   border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
      h2 {{ color: #10b981; margin-top: 0; }}
      h3 {{ color: #374151; border-bottom: 2px solid #10b981; padding-bottom: 8px; margin-top: 30px; }}
      table {{ width: 100%; border-collapse: collapse; margin: 10px 0 20px; }}
      th {{ background: #f3f4f6; padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;
            color: #4b5563; font-size: 13px; }}
      td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; color: #1f2937; }}
      .summary-table {{ width: 100%; border-collapse: separate; border-spacing: 10px 0; margin-bottom: 20px; }}
      .summary-card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; text-align: center; }}
      .summary-title {{ font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold; }}
      .summary-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
      .yemek-box {{ background: #f9fafb; border-left: 4px solid #10b981; padding: 15px;
                    margin-bottom: 15px; border-radius: 4px; }}
    </style></head><body><div class="container">
      <h2>🍲 Aziziye Aşevi - {_rapor_html_metni(rapor_baslik)}</h2>
      <p style="color:#6b7280;font-size:15px;"><b>Tarih:</b> {_rapor_html_metni(rapor_tarih_str)}</p>
      <table class="summary-table"><tr>
        <td class="summary-card"><div class="summary-title">Yeni Stok Girişi</div><div class="summary-value" style="color:#10b981;">{len(secilen_girisler)}</div></td>
        <td class="summary-card"><div class="summary-title">Fire / Zayiat</div><div class="summary-value" style="color:#ef4444;">{len(secilen_fireler)}</div></td>
        <td class="summary-card"><div class="summary-title">Üretilen Yemek</div><div class="summary-value" style="color:#3b82f6;">{len(secilen_yemekler)}</div></td>
      </tr></table>"""

    if secilen_girisler:
        html += "<h3>📦 Gelen Stok Girişleri</h3><table><tr><th>Ürün</th><th>Miktar</th><th>Fatura No</th></tr>"
        for g in secilen_girisler:
            html += f"<tr><td>{_rapor_html_metni(g.get('urun'))}</td><td>{_rapor_html_metni(g.get('miktar'))} {_rapor_html_metni(g.get('birim', ''), '')}</td><td>{_rapor_html_metni(g.get('fatura_no'))}</td></tr>"
        html += "</table>"

    if secilen_fireler:
        html += "<h3>🗑️ Fire / Zayiat</h3><table><tr><th>Ürün</th><th>Fatura No</th><th>Miktar</th><th>Tutar</th><th>Açıklama</th></tr>"
        for f in secilen_fireler:
            html += f"<tr><td>{_rapor_html_metni(f.get('urun'))}</td><td>{_rapor_html_metni(f.get('fatura_no'))}</td><td>{_rapor_html_metni(f.get('miktar'))}</td><td>{float(f.get('tutar', 0)):,.2f} ₺</td><td>{_rapor_html_metni(f.get('aciklama'))}</td></tr>"
        html += "</table>"

    if secilen_silinenler:
        html += "<h3>❌ Silinen Ürünler</h3><table><tr><th>Ürün</th><th>Kayıt ID</th><th>Neden</th></tr>"
        for s in secilen_silinenler:
            html += f"<tr><td>{_rapor_html_metni(s.get('urun'))}</td><td>{_rapor_html_metni(s.get('kayit_id'))}</td><td>{_rapor_html_metni(s.get('neden'))}</td></tr>"
        html += "</table>"

    if secilen_yemekler:
        html += "<h3>🍲 Üretilen Yemekler</h3>"
        for y in secilen_yemekler:
            toplam = float(y.get('toplam_maliyet', 0))
            kisi = int(y.get('kisi_sayisi', 1) or 1)
            kisi_basi = toplam / kisi if kisi > 0 else 0
            html += f"<div class='yemek-box'><h4 style='margin:0 0 10px;'>{_rapor_html_metni(y.get('tarih'))} - {_rapor_html_metni(y.get('yemek_adi'))} ({kisi} Kişilik)</h4>"
            html += f"<p style='margin:0 0 10px;font-size:14px;'><b>Toplam:</b> {toplam:,.2f} ₺ | <b>Kişi Başı:</b> {kisi_basi:,.2f} ₺</p>"
            if y.get("malzemeler"):
                html += "<table style='margin:0;'><tr><th>Malzeme</th><th>Miktar</th><th>Maliyet</th></tr>"
                for m in y.get("malzemeler", []):
                    html += f"<tr><td>{_rapor_html_metni(m.get('urun'))}</td><td>{_rapor_html_metni(m.get('miktar'))} {_rapor_html_metni(m.get('birim', ''), '')}</td><td>{float(m.get('tutar', 0)):,.2f} ₺</td></tr>"
                html += "</table>"
            html += "</div>"

    if secilen_izinler:
        html += "<h3>👥 Personel İzinleri</h3><table><tr><th>Personel</th><th>Tür</th><th>Başlangıç</th><th>Bitiş</th></tr>"
        for i in secilen_izinler:
            html += f"<tr><td>{_rapor_html_metni(i.get('personel_ad'))}</td><td>{_rapor_html_metni(i.get('izin_turu'))}</td><td>{_rapor_html_metni(i.get('baslangic'))}</td><td>{_rapor_html_metni(i.get('bitis'))}</td></tr>"
        html += "</table>"

    if not (secilen_girisler or secilen_fireler or secilen_silinenler or secilen_yemekler or secilen_izinler):
        html += "<div style='text-align:center;padding:30px;color:#6b7280;'><b>Bu dönemde veri yok.</b></div>"

    html += "</div></body></html>"
    return html    

# FERNET_KEY tanımlı değilse uygulama BİLEREK durdurulur...
if fernet_motoru is None:
    st.error(
        "🔐 **FERNET_KEY tanımlı değil veya geçersiz.** Güvenlik ve veri kaybını önlemek için "
        "uygulama durduruldu. Aşağıdaki komutla bir anahtar üretip `secrets` ayarlarınıza "
        "`FERNET_KEY = \"...\"` olarak ekleyin ve anahtarı güvenli bir yerde YEDEKLEYİN:"
    )
    st.code(
        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
        language="bash",
    )
    st.stop()


# =========================================================================
# SUPABASE BULUT VERİTABANI BAĞLANTI FONKSİYONLARI
# =========================================================================
SUPABASE_URL = secret_deger("SUPABASE_URL", "")
SUPABASE_KEY = secret_deger("SUPABASE_KEY", "")

# Kayıt kimliği -> session_state anahtarı. Bu veriler için "çakışma denetimi" yapılır:
# başka bir oturum veriyi değiştirdiyse, eski kopyayla üzerine yazmak engellenir.
KAYIT_ESLEME = {
    "girisler": "girisler",
    "kullanim_loglari": "kullanim_loglari",
    "silinen_urun_loglari": "silinen_urun_loglari",
    "ihtiyac_sahipleri": "ihtiyac_sahipleri",
    "dagitim_loglari": "dagitim_loglari",
    "personeller": "personeller",
    "personel_izinleri": "personel_izinleri",
    "resmi_tatiller": "resmi_tatiller",
    "yemek_uretim_arsivi": "yemek_uretim_arsivi",
    "depolar_listesi": "depolar",
    "demirbaslar_listesi": "demirbaslar",
    "kritik_seviyeler": "kritik_seviyeler",
    "kullanici_yetkileri": "kullanicilar",
    "dashboard_widgets": "dashboard_widgets",
    "arayuz_sayfa_ayarlari": "arayuz_sayfa_ayarlari",
}
# Yedeğe giren veriler (kullanıcı/şifre bilgileri, oturum ve deneme kayıtları yedeğe girmez)
YEDEK_ANAHTARLARI = [k for k in KAYIT_ESLEME if k != "kullanici_yetkileri"]

# Güvenlik açısından kritik anahtarlar: bu anahtarların okumaları cache'i
# ATLAMALI. Aksi hâlde 60 sn'lik @st.cache_data penceresinde birbirini izleyen
# "oku → değiştir → yaz" döngüleri eski sayacın üzerine yazar; hem kullanıcı
# bazlı kilit (MAKS_HATALI_GIRIS) hem IP kilidi fiilen devre dışı kalır.
ONBELLEKSIZ_ANAHTARLAR = {
    "giris_denemeleri",
    "aktif_oturumlar",
    "kullanici_yetkileri",
    "arayuz_sayfa_ayarlari",
}


def _supa_basliklar(ekstra=None):
    h = {"apikey": SUPABASE_KEY}
    if not str(SUPABASE_KEY).startswith("sb_"):  # sb_secret_/sb_publishable_ anahtarları JWT değildir
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if ekstra:
        h.update(ekstra)
    return h


def supabase_anahtar_rolu():
    """Kullanılan Supabase anahtarının rolü: 'anon', 'service_role' veya 'bilinmiyor'."""
    anahtar = str(SUPABASE_KEY or "")
    if anahtar.startswith("sb_publishable"):
        return "anon"
    if anahtar.startswith("sb_secret"):
        return "service_role"
    try:
        parca = anahtar.split(".")[1]
        parca += "=" * (-len(parca) % 4)
        return str(json.loads(base64.urlsafe_b64decode(parca)).get("role", "bilinmiyor"))
    except Exception:
        return "bilinmiyor"


# =========================================================================
# HIZLANDIRILMIŞ VERİTABANI BAĞLANTI VE ÖNBELLEKLEME
# =========================================================================
@st.cache_resource
def get_http_session():
    """Tüm Supabase istekleri için ortak ve hızlı HTTP bağlantı havuzu oluşturur."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    return session


def _supabase_ham_oku(kayit_id):
    """('ok', veri) | ('yok', None) | ('hata', mesaj). Oturum durumunu DEĞİŞTİRMEZ."""
    try:
        session = get_http_session()
        r = session.get(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar(),
            params={"id": f"eq.{kayit_id}", "select": "veri"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}"
    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}"
    try:
        data = r.json()
    except Exception:
        return "hata", "Geçersiz yanıt"
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"]
    return "yok", None


@st.cache_data(ttl=60, show_spinner=False)
def _supabase_ham_oku_cached(kayit_id):
    """Veritabanı okumalarını 60 saniye boyunca bellek seviyesinde hızlı tutar.
    Güvenlik açısından kritik anahtarlar bu cache'i KULLANMAZ; bkz. ONBELLEKSIZ_ANAHTARLAR."""
    return _supabase_ham_oku(kayit_id)
    
def _guvenli_dict_guncelle(kayit_id, guncelleme_fn):
    """Oku-değiştir-yaz. İki eşzamanlı yazma aynı dict'i okuyup son yazan kazanır;
    bu pencerede biri kaybedebilir. Kaybedilen güncellemenin etkisi:
      - oturum: kullanıcı bir kez daha giriş yapar.
      - giriş denemesi: bir deneme sayılmaz; IP bazlı limit yine devrededir.
    Kesin atomiklik için Postgres RPC gerekir; bu ölçekte pragmatik ödün."""
    durum, mevcut = _supabase_ham_oku(kayit_id)
    if durum == "hata":
        return durum, mevcut
    mevcut_dict = mevcut if isinstance(mevcut, dict) else {}
    yeni = guncelleme_fn(dict(mevcut_dict))
    supabase_veri_kaydet(kayit_id, yeni, zorla=True)
    return "ok", yeni

# =========================================================================
# ATOMİK YAZMA + ARKA PLAN MAIL  (K1, K3, K4)
# =========================================================================
_mail_havuzu = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


def _smtp_gonder_senkron(konu, html_icerik):
    """Sadece SMTP. Streamlit API'sine DOKUNMAZ. (basarili, hata_mesaji)."""
    try:
        sender = secret_deger("MAIL_SENDER", "")
        password = secret_deger("MAIL_PASSWORD", "")
        recipient = secret_deger("MAIL_RECIPIENT", "")
        server_adresi = secret_deger("MAIL_SERVER", "smtp.gmail.com")
        port = int(secret_deger("MAIL_PORT", 587))

        msg = MIMEMultipart()
        msg["From"] = formataddr(("Aziziye Aşevi Otomasyon", sender))
        msg["To"] = recipient
        msg["Subject"] = konu
        msg.attach(MIMEText(html_icerik, "html", "utf-8"))

        # K1: timeout ZORUNLU (önceki kodda yoktu → thread 30-120sn kilitlenebiliyordu)
        with smtplib.SMTP(server_adresi, port, timeout=10) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _supabase_ham_oku_versiyonlu(kayit_id):
    """('ok', veri, versiyon) | ('yok', None, None) | ('hata', mesaj, None).
    CAS için versiyon ile birlikte okur. CACHE KULLANMAZ."""
    try:
        r = get_http_session().get(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar(),
            params={"id": f"eq.{kayit_id}", "select": "veri,versiyon"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}", None
    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}", None
    try:
        data = r.json()
    except Exception:
        return "hata", "Geçersiz yanıt", None
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"], int(data[0].get("versiyon") or 0)
    return "yok", None, None


def _supabase_cas_yaz(kayit_id, beklenen_versiyon, yeni_veri):
    """Compare-and-swap. (basarili, guncel_versiyon_veya_hata)."""
    try:
        if beklenen_versiyon is None:
            r = get_http_session().post(
                f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
                headers=_supa_basliklar({
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates,return=representation",
                }),
                json={"id": kayit_id, "veri": yeni_veri, "versiyon": 0},
                timeout=10,
            )
            if r.status_code in (200, 201) and r.json():
                return True, 0
            return False, "insert-çakışma"
        yeni_versiyon = beklenen_versiyon + 1
        r = get_http_session().patch(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar({
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }),
            params={"id": f"eq.{kayit_id}", "versiyon": f"eq.{beklenen_versiyon}"},
            json={"veri": yeni_veri, "versiyon": yeni_versiyon},
            timeout=10,
        )
        if r.status_code == 200:
            guncellenen = r.json()
            if guncellenen:
                return True, yeni_versiyon
            return False, "versiyon-çakışma"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"Bağlantı hatası: {type(e).__name__}"


def _atomik_dict_guncelle(kayit_id, guncelleme_fn, max_retry=8):
    """K3: Okuma-değiştirme-yazma yarışını gideren atomik güncelleme.
    Eski `_guvenli_dict_guncelle`'nin yerini alır. Çakışmada üstel geri çekilmeyle tekrar dener."""
    son_hata = ""
    for i in range(max_retry):
        durum, mevcut, versiyon = _supabase_ham_oku_versiyonlu(kayit_id)
        if durum == "hata":
            return "hata", mevcut
        mevcut_dict = dict(mevcut) if isinstance(mevcut, dict) else {}
        yeni = guncelleme_fn(dict(mevcut_dict))
        basarili, sonuc = _supabase_cas_yaz(kayit_id, versiyon, yeni)
        if basarili:
            return "ok", yeni
        son_hata = sonuc
        time.sleep(0.02 * (2 ** min(i, 4)))
    return "hata", f"Çakışma ({max_retry} deneme): {son_hata}"

def _taban_hashler():
    if "_db_hash" not in st.session_state:
        st.session_state["_db_hash"] = {}
    return st.session_state["_db_hash"]


def _veritabani_hatasi_dur(mesaj):
    if not st.session_state.get("oturum_aktif", False):
        st.warning(
            f"⚠️ **Veritabanı uyarısı:** {mesaj}. "
            "Deneme verileriyle giriş ekranı kullanılabilir; yapılandırma düzeltildiğinde sayfayı yenileyin."
        )
        return
    st.error(
        f"⚠️ **Veritabanı hatası:** {mesaj}. Verilerinizin bozulmaması için işlem durduruldu. "
        "Bağlantıyı/ayarları kontrol edip sayfayı yenileyin."
    )
    st.stop()


def supabase_veri_oku(kayit_id, varsayilan_deger, kritik=True):
    """Veriyi okur. Bulunamazsa varsayılanı döndürür. Hata olursa (kritik=True ise)
    boş veri DÖNDÜRMEK yerine işlemi durdurur; aksi hâlde sonraki kayıt veritabanını
    boşla ezebilirdi."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return varsayilan_deger
    # Güvenlik açısından kritik anahtarlar cache'i ATLAR (bkz. ONBELLEKSIZ_ANAHTARLAR).
    if kayit_id in ONBELLEKSIZ_ANAHTARLAR:
        durum, veri = _supabase_ham_oku(kayit_id)
    else:
        durum, veri = _supabase_ham_oku_cached(kayit_id)
    if durum == "hata":
        if kritik:
            _veritabani_hatasi_dur(f"'{kayit_id}' okunamadı ({veri})")
        return varsayilan_deger
    if kayit_id in KAYIT_ESLEME:
        _taban_hashler()[kayit_id] = _veri_hash(veri) if durum == "ok" else "__yok__"
    return veri if durum == "ok" else varsayilan_deger


def _cakisma_ve_dur():
    for sk in set(KAYIT_ESLEME.values()):
        st.session_state.pop(sk, None)
    st.session_state.pop("_db_hash", None)
    st.error(
        "⚠️ **Kayıt YAPILMADI – veri çakışması.** Siz çalışırken başka bir kullanıcı/oturum "
        "bu veriyi değiştirdi. Onun değişikliğinin silinmemesi için işleminiz iptal edildi. "
        "Aşağıdaki düğmeyle güncel verileri yükleyip işlemi tekrar yapın."
    )
    if st.button("🔄 Verileri Yenile", key="cakisma_yenile_btn"):
        st.rerun()
    st.stop()


def supabase_veri_kaydet(kayit_id, veri_objesi, zorla=False):
    """Veriyi kaydeder. Çakışma varsa ve kayıt başarısız olursa işlemi durdurur
    (hata artık sessizce yutulmaz)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    if kayit_id in KAYIT_ESLEME and not zorla:
        durum, mevcut = _supabase_ham_oku(kayit_id)
        if durum == "hata":
            _veritabani_hatasi_dur(f"'{kayit_id}' doğrulanamadı ({mevcut})")
        guncel = _veri_hash(mevcut) if durum == "ok" else "__yok__"
        taban = _taban_hashler().get(kayit_id)
        if taban is not None and taban != guncel:
            _cakisma_ve_dur()
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar({
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }),
            json={"id": kayit_id, "veri": veri_objesi},
            timeout=10,
        )
    except Exception as e:
        _veritabani_hatasi_dur(f"'{kayit_id}' kaydedilemedi (Bağlantı hatası: {type(e).__name__})")
    if r.status_code not in (200, 201):
        _veritabani_hatasi_dur(f"'{kayit_id}' kaydedilemedi (HTTP {r.status_code})")
    if kayit_id in KAYIT_ESLEME:
        try:
            _taban_hashler()[kayit_id] = _veri_hash(r.json()[0]["veri"])
        except Exception:
            _taban_hashler().pop(kayit_id, None)
    

# =========================================================================
# YEDEKLEME / GERİ YÜKLEME
# =========================================================================
def yedek_paketi_olustur():
    """Veritabanındaki ham veriyi (şifreli alanlar şifreli kalır) paketler. Hata olursa None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    veri = {}
    for anahtar in YEDEK_ANAHTARLARI:
        durum, icerik = _supabase_ham_oku(anahtar)
        if durum == "hata":
            return None
        if durum == "ok":
            veri[anahtar] = icerik
    return {
        "_meta": {
            "zaman": simdi_tr_str("%Y-%m-%d %H:%M:%S"),
            "surum": 1,
            "olusturan": st.session_state.get("aktif_kullanici", ""),
        },
        "veri": veri,
    }


def otomatik_yedek_al(neden):
    """Silme gibi geri dönüşsüz işlemlerden önce tek seviyelik otomatik yedek alır."""
    paket = yedek_paketi_olustur()
    if paket is None:
        return False
    paket["_meta"]["neden"] = str(neden)[:200]
    supabase_veri_kaydet("otomatik_yedek", paket)
    return True


def yedek_geri_yukle(paket):
    """Yedek paketini veritabanına yazar. (basarili, mesaj) döndürür."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "Supabase yapılandırılmamış; geri yükleme yapılamadı."
    if not isinstance(paket, dict) or not isinstance(paket.get("veri"), dict):
        return False, "Geçersiz yedek dosyası."
    yazilacak = {k: v for k, v in paket["veri"].items() if k in YEDEK_ANAHTARLARI}
    if not yazilacak:
        return False, "Yedek dosyasında geri yüklenecek bölüm bulunamadı."
    for k, v in yazilacak.items():
        beklenen = dict if k == "kritik_seviyeler" else list
        if not isinstance(v, beklenen):
            return False, f"'{k}' bölümü hatalı biçimde, geri yükleme iptal edildi."
            
    # Önce güvenlik yedeği — başarısızsa iptal
    if not otomatik_yedek_al("Geri yükleme öncesi otomatik yedek"):
        return False, "Geri yükleme öncesi otomatik yedek alınamadı; güvenlik için iptal edildi."
        
    for k, v in yazilacak.items():
        supabase_veri_kaydet(k, v, zorla=True)
        
    # Bellekteki eski verileri temizle ki güncel veriler yüklensin
    for sk in set(KAYIT_ESLEME.values()):
        st.session_state.pop(sk, None)
    st.session_state.pop("_db_hash", None)
    
    return True, f"{len(yazilacak)} bölüm geri yüklendi."
    

# =========================================================================
# OTURUM GÜVENLİĞİ
# =========================================================================
OTURUM_SURESI_SN = 8 * 60 * 60  # 8 saat
MAKS_HATALI_GIRIS = 3           # kullanıcı + IP başına
KILIT_SURESI_SN = 30            # ilk kilit süresi (her kilitte ikiye katlanır, en çok 15 dk)
IP_MAKS_HATALI_GIRIS = 3        # IP başına deneme (kullanıcı adı ile aynı eşik)
IP_KILIT_SURESI_SN = 30         # IP kilit süresi (kullanıcı adı ile aynı)
COOKIE_ADI = "aziziye_oturum"
OTURUM_DOGRULAMA_ARALIGI_SN = 60  # açık oturum bu aralıkla veritabanından yeniden doğrulanır


def bosta_kalma_suresi_sn():
    """Etkinlik olmadığında oturumun kapanacağı süre. Varsayılan 30 dk;
    secrets içinde BOSTA_KALMA_DAKIKA ile 5-480 dk arasında değiştirilebilir."""
    try:
        dk = int(str(secret_deger("BOSTA_KALMA_DAKIKA", 30)))
    except Exception:
        dk = 30
    return max(5, min(dk, 480)) * 60

# Çerez desteği: `extra-streamlit-components` kütüphanesi ile stabil çerez yönetimi.
try:
    import extra_streamlit_components as stx
    # Streamlit widget uyarısını önlemek için doğrudan ana kodda başlatıyoruz.
    cerez_kontrol = stx.CookieManager(key="aziziye_cerez")
except Exception:
    cerez_kontrol = None

def cerez_oku(anahtar=COOKIE_ADI):
    # Öncelik 1: Streamlit'in kendi senkron çerez okuyucusu (1.35+)
    try:
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            deger = st.context.cookies.get(anahtar)
            if deger:
                return str(deger)
    except Exception:
        pass
        
    # Öncelik 2: extra-streamlit-components (Fallback)
    if cerez_kontrol is None:
        return ""
    try:
        return str(cerez_kontrol.get(anahtar) or "")
    except Exception:
        return ""


def cerez_yaz(deger, anahtar=COOKIE_ADI, max_age=OTURUM_SURESI_SN):
    if cerez_kontrol is None:
        return
    try:
        import datetime
        # Zaman dilimi karmaşasını önlemek için yerel saat kullanıyoruz (stx bunu destekler)
        bitis = datetime.datetime.now() + datetime.timedelta(seconds=max_age)
        # path="/" EKLENDİ: Çerezin tüm sayfalarda geçerli olmasını sağlar
        cerez_kontrol.set(anahtar, deger, expires_at=bitis, path="/")
    except Exception as e:
        log.error(f"Çerez yazma hatası: {e}")
        pass


def cerez_sil(anahtar=COOKIE_ADI):
    if cerez_kontrol is None:
        return
    try:
        cerez_kontrol.remove(anahtar)
    except Exception:
        try:
            cerez_kontrol.delete(anahtar)
        except Exception:
            pass

def istemci_ip_bilgisi():
    """(kilit için kullanılan IP, tam X-Forwarded-For). Kilitte EN SAĞDAKİ adres kullanılır:
    istemci tarafından sahte eklenen adresler soldadır, en sağdakini ise sunucuya en yakın
    güvenilir vekil ekler. Böylece sahte başlıkla kilit atlatılamaz."""
    try:
        basliklar = st.context.headers
        xff = str(basliklar.get("X-Forwarded-For", "") or "")
        if xff:
            ip = xff.split(",")[-1].strip()
        else:
            ip = str(basliklar.get("X-Real-Ip", "") or "").strip()
        return (ip or "bilinmiyor"), xff[:200]
    except Exception:
        return "bilinmiyor", ""


def giris_logla(kullanici, durum):
    """Giriş/çıkış/yönetim olaylarını yeni ve güvenli SQL tablosuna kaydeder. Şifre KAYDEDİLMEZ."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    ip, xff = istemci_ip_bilgisi()
    try:
        # Artık JSON listesine değil, doğrudan yeni SQL tablosuna INSERT (ekleme) yapıyoruz
        requests.post(
            f"{SUPABASE_URL}/rest/v1/giris_kayitlari",
            headers=_supa_basliklar({"Content-Type": "application/json", "Prefer": "return=minimal"}),
            json={
                "kullanici": str(kullanici)[:50],
                "durum": str(durum)[:80],
                "ip": ip,
                "xff": xff
            },
            timeout=5
        )
    except Exception as e:
        log.error(f"Log kaydı hatası: {e}")


def _token_hashle(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def oturum_olustur(kullanici_adi):
    token = secrets.token_urlsafe(32)
    simdi = time.time()
    bitis = simdi + OTURUM_SURESI_SN
    
    def _ekle(oturumlar):
        # Süresi geçmiş oturumları temizle
        oturumlar = {h: o for h, o in oturumlar.items() if o.get("bitis", 0) > simdi}
        # Yeni oturumu ekle
        oturumlar[_token_hashle(token)] = {"kullanici": kullanici_adi, "bitis": bitis}
        return oturumlar
        
    durum, sonuc = _atomik_dict_guncelle("aktif_oturumlar", _ekle)
    if durum != "ok":
        _veritabani_hatasi_dur(f"oturum oluşturulamadı ({sonuc})")
    return token, bitis


def oturum_dogrula(token):
    if not token:
        return None
    oturumlar = supabase_veri_oku("aktif_oturumlar", {}, kritik=False)
    if not isinstance(oturumlar, dict):
        return None
    kayit = oturumlar.get(_token_hashle(token))
    if kayit and kayit.get("bitis", 0) > time.time():
        return kayit
    return None


def oturum_sil(token):
    if not token:
        return
    h = _token_hashle(token)
    def _sil(oturumlar):
        oturumlar.pop(h, None)
        return oturumlar
    _atomik_dict_guncelle("aktif_oturumlar", _sil)


def kullanici_oturumlarini_kapat(kullanici, haric_token=None):
    haric = _token_hashle(haric_token) if haric_token else None
    def _filtrele(oturumlar):
        return {h: o for h, o in oturumlar.items()
                if o.get("kullanici") != kullanici or h == haric}
    _atomik_dict_guncelle("aktif_oturumlar", _filtrele)

def oturumu_baslat(kullanici_adi):
    token, bitis = oturum_olustur(kullanici_adi)
    st.session_state.oturum_aktif = True
    st.session_state.aktif_kullanici = kullanici_adi
    st.session_state.oturum_token = token
    st.session_state.oturum_bitis = bitis
    st.session_state["son_etkinlik"] = time.time()
    st.session_state["_oturum_son_dogrulama"] = time.time()
    if kullanici_adi != "misafir":
        st.session_state.pop("ilk_kurulum_sifreleri", None)

    if cerez_kontrol is not None:
        cerez_yaz(token)
        time.sleep(1.5) # Çerezin yazılması için kısa bir bekleme   
    st.rerun()
   
def oturumu_kapat():
    """Oturumu sunucuda iptal eder, çerezi ve oturum durumunu temizler."""
    kullanici = st.session_state.get("aktif_kullanici", "misafir")
    token = st.session_state.get("oturum_token", "")
    giris_logla(kullanici, "çıkış")
    oturum_sil(token)
    if cerez_kontrol is not None:
        cerez_sil()
        time.sleep(0.2)
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    st.session_state.oturum_bitis = 0
    st.query_params.clear()


def oturumu_zorla_kapat(mesaj, log_durumu):
    """Sunucu/süre/boşta kalma nedeniyle oturumu kapatır; giriş ekranında mesaj gösterilir."""
    kullanici = st.session_state.get("aktif_kullanici", "misafir")
    token = st.session_state.get("oturum_token", "")
    giris_logla(kullanici, log_durumu)
    oturum_sil(token)
    if cerez_kontrol is not None:
        cerez_sil()
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    st.session_state.oturum_bitis = 0
    st.session_state["oturum_mesaji"] = mesaj
    if "token" in st.query_params:
        del st.query_params["token"]


def sifre_degistir(kullanici, yeni_sifre, haric_token=None, zorunlu=False):
    """Şifreyi yeni (scrypt) biçimde kaydeder ve kullanıcının diğer oturumlarını kapatır."""
    k = st.session_state.kullanicilar[kullanici]
    k["sifre"] = sifre_hashle_yeni(yeni_sifre)
    if zorunlu:
        k["sifre_degistirilmeli"] = True
    else:
        k.pop("sifre_degistirilmeli", None)
    kullanıcıları_kaydet(st.session_state.kullanicilar)
    kullanici_oturumlarini_kapat(kullanici, haric_token)
    giris_logla(kullanici, "şifre değiştirildi")


def giris_kilit_kalan(anahtar):
    kayitlar = supabase_veri_oku("giris_denemeleri", {}, kritik=False)
    if not isinstance(kayitlar, dict):
        return 0
    return max(0, int(kayitlar.get(anahtar, {}).get("kilit_bitis", 0) - time.time()))


def hatali_giris_kaydet(anahtar, maks=MAKS_HATALI_GIRIS, taban_sn=KILIT_SURESI_SN):
    """(kalan_hak, kilitlendi_mi) döndürür. Her ardışık kilitte süre ikiye katlanır (en çok 15 dk)."""
    simdi = time.time()
    sonuc = {"kalan": maks, "kilit": False}
    
    def _guncelle(kayitlar):
        # Eski ve süresi geçmiş kayıtları temizle
        kayitlar = {k: v for k, v in kayitlar.items()
                    if v.get("kilit_bitis", 0) > simdi or simdi - v.get("son", 0) < 3600}
        kayit = kayitlar.get(anahtar, {"sayi": 0, "kilit_sayisi": 0, "kilit_bitis": 0, "son": 0})
        
        if simdi - kayit.get("son", 0) > 3600:
            kayit["sayi"] = 0
            kayit["kilit_sayisi"] = 0
            
        kayit["sayi"] = kayit.get("sayi", 0) + 1
        kayit["son"] = simdi
        
        if kayit["sayi"] >= maks:
            kayit["kilit_sayisi"] = kayit.get("kilit_sayisi", 0) + 1
            sure = min(taban_sn * (2 ** (kayit["kilit_sayisi"] - 1)), 900)
            kayit["kilit_bitis"] = simdi + sure
            kayit["sayi"] = 0
            sonuc["kilit"] = True
            
        sonuc["kalan"] = max(maks - kayit["sayi"], 0)
        kayitlar[anahtar] = kayit
        return kayitlar
        
    durum, _ = _atomik_dict_guncelle("giris_denemeleri", _guncelle)
    if durum != "ok":
        # Güvenlik gereği yazamıyorsak fail-safe olarak kilitli say
        return 0, True
    return sonuc["kalan"], sonuc["kilit"]


def giris_denemesini_sifirla(anahtar=None, *ek_anahtarlar):
    """Anahtar verilirse belirtilen sayaçları, verilmezse tüm sayaçları temizler."""
    if anahtar is None:
        _atomik_dict_guncelle("giris_denemeleri", lambda _: {})
        return

    anahtarlar = (anahtar,) + ek_anahtarlar
    _atomik_dict_guncelle(
        "giris_denemeleri",
        lambda kayitlar: giris_sayaclarini_sifirla(kayitlar, anahtarlar),
    )


# =========================================================
# SEFA AŞEVİ - PURE DARK LIQUID GLASS TEMA
# =========================================================

# Kodun alt kısımlarındaki KeyError ve NameError hatalarını engelleyen değişkenler:
# Tema state'i: önce çerezden oku, yoksa varsayılan "Dark"
if "tema" not in st.session_state:
    st.session_state.tema = _tema_tercihini_yukle(
        st.query_params.get("tema", ""),
        cerez_oku("aziziye_tema"),
    )

border_color = "rgba(16, 185, 129, 0.35)"
bg_color = "#040711"
card_bg = "rgba(10, 15, 29, 0.75)"
sidebar_bg = "rgba(6, 10, 20, 0.85)"
text_color = "#f4f4f5"
subtext_color = "#94a3b8"
input_bg = "rgba(15, 23, 42, 0.85)"
popover_bg = "#0b1329"

st.markdown(
    f"""
    <style>
        :root {{
            --app-bg: {bg_color};
            --app-card: {card_bg};
            --app-sidebar: {sidebar_bg};
            --app-border: {border_color};
            --app-text: {text_color};
            --app-muted: {subtext_color};
            --app-input: {input_bg};
            --app-popover: {popover_bg};
            --app-accent: #10b981;
            --app-accent-contrast: #04110C;
            --app-radial-1: rgba(16, 185, 129, 0.12);
            --app-radial-2: rgba(99, 102, 241, 0.12);
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# STİL ENJEKSİYONU
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Ana Arka Plan ve Tipografi */
    .stApp {
        background-color: var(--app-bg) !important;
        background-image: radial-gradient(circle at 10% 20%, var(--app-radial-1) 0%, transparent 45%),
                          radial-gradient(circle at 90% 80%, var(--app-radial-2) 0%, transparent 45%) !important;
        background-attachment: fixed !important;
        color: var(--app-text) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Sol Menü (Sidebar) Cam Görünümü */
    section[data-testid="stSidebar"] {
        background: var(--app-sidebar) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--app-border) !important;
    }

    /* Sol Menü Butonları */
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
        box-shadow: 0 0 18px rgba(16, 185, 129, 0.18) !important;
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

    /* Metrik Kartları ve Formlar (Neon Cam Efekti) */
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

    /* Girdi Kutuları ve İnputlar (Koyu Mavi Zemin) */
    input, 
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div {
        background-color: var(--app-input) !important;
        color: var(--app-text) !important;
        border-radius: 12px !important;
        border: 1px solid var(--app-border) !important;
    }

    /* Native widget metinleri: dark/light görünümde tema tokenlarını kullanır. */
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

    /* Checkbox, radio, toggle ve kontroller */
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

    /* Kullanıcı ayarları sekmeleri ve veri panelleri */
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

    /* Açılır menü ve seçenek listeleri */
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

    /* Checkbox, radio ve toggle kontrolleri tema yüzeyine göre okunur kalır. */
    input[type="checkbox"],
    input[type="radio"] {
        accent-color: var(--app-accent) !important;
    }
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label p,
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label p,
    [data-testid="stToggle"] label,
    [data-testid="stToggle"] label p {
        color: var(--app-text) !important;
    }
    [data-baseweb="checkbox"] div,
    [data-baseweb="radio"] div {
        border-color: var(--app-border) !important;
    }

    /* Birincil Yeşil Butonlar */
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

    /* İkincil Butonlar */
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
    /* Streamlit'in button içindeki p/span katmanları bazen transparent kalıyor.
       Düğme metnini görünür renk katmanına son kez sabitle. */
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

    /* HTML Özel Tablo */
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
        color: var(--app-muted) !important;
        font-size: 13px !important;
        border-bottom: 1px solid var(--app-border);
    }
</style>
""", unsafe_allow_html=True)

# Sayfa ve bölüm başlıklarında kurumsal renk geçişi.
st.markdown("""
<style>
    .stApp h1:not([data-testid]),
    .stApp h2:not([data-testid]),
    .stApp h3:not([data-testid]) {
        display: inline-block !important;
        max-width: 100% !important;
        background-image: linear-gradient(
            90deg,
            var(--app-text) 0%,
            var(--app-accent) 45%,
            #14b8a6 72%,
            #38bdf8 100%
        ) !important;
        background-size: 100% 100% !important;
        background-clip: text !important;
        -webkit-background-clip: text !important;
        color: transparent !important;
        -webkit-text-fill-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

def silme_onay_kutusu(anahtar):
    return st.checkbox(
        "⚠️ Bu işlemin geri alınamayacağını anlıyorum, silmeyi onaylıyorum.", key=anahtar
    )


# KVKK ve güvenlik gereği koda gömülü PII (Kişisel Veri) bırakılmamıştır.
varsayilan_personeller = []

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {
        "tarih": "2026-04-23",
        "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı",
    },
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {
        "tarih": "2026-05-19",
        "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
    },
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
            # Secrets'taki şifre politikaya uymuyorsa (zayıfsa) uyarı verilir
            uygun = not sifre_politika_hatasi(sifre)

        kayit[ad] = {
            "sifre": sifre_hashle_yeni(sifre),
            "tip": tip,
            "yasakli_menuler": [],
            "maskeli_alanlar": [],
            "salt_okunur": salt_okunur,
        }
        
        # Şifre rastgele üretildiyse VEYA zayıfsa ilk girişte değiştirilmesi zorunlu tutulur
        if rastgele or not uygun:
            kayit[ad]["sifre_degistirilmeli"] = True
            
    kayit["misafir"] = varsayilan_misafir_kaydi()
    if uretilenler:
        st.session_state["ilk_kurulum_sifreleri"] = uretilenler
    return kayit

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


def widgetlari_yukle():
    return supabase_veri_oku("dashboard_widgets", varsayilan_widgets)


def widgetlari_kaydet(veri):
    supabase_veri_kaydet("dashboard_widgets", veri)


def depoları_yukle():
    return supabase_veri_oku("depolar_listesi", varsayilan_depolar)


def depoları_kaydet(veri):
    supabase_veri_kaydet("depolar_listesi", veri)


def demirbasları_yukle():
    return supabase_veri_oku("demirbaslar_listesi", varsayilan_demirbaslar)


def demirbasları_kaydet(veri):
    supabase_veri_kaydet("demirbaslar_listesi", veri)


def kritik_seviyeleri_yukle():
    return supabase_veri_oku("kritik_seviyeler", {})


def kritik_seviyeleri_kaydet(veri):
    supabase_veri_kaydet("kritik_seviyeler", veri)


def kullanıcıları_yukle():
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

        # Düz metin gelen şifre (eski sürümlerden kalma) yeni biçimde hash'lenir.
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
    supabase_veri_kaydet("kullanici_yetkileri", veri)


def verileri_yukle():
    return supabase_veri_oku("girisler", [])


def verileri_kaydet(veri):
    supabase_veri_kaydet("girisler", veri)


def loglari_yukle():
    return supabase_veri_oku("kullanim_loglari", [])


def loglari_kaydet(veri):
    supabase_veri_kaydet("kullanim_loglari", veri)


def silinen_urun_loglarini_yukle():
    return supabase_veri_oku("silinen_urun_loglari", [])


def silinen_urun_loglarini_kaydet(veri):
    supabase_veri_kaydet("silinen_urun_loglari", veri)


def ihtiyac_sahiplerini_yukle():
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


def dagitim_loglarini_yukle():
    return supabase_veri_oku("dagitim_loglari", [])


def dagitim_loglarini_kaydet(veri):
    supabase_veri_kaydet("dagitim_loglari", veri)


def personelleri_yukle():
    ham_veri = supabase_veri_oku("personeller", varsayilan_personeller)
    cozulmus_p = []
    for p in ham_veri:
        p_kopya = p.copy()
        h_tc = p.get("tc", "")
        p_kopya["tc"] = metni_coz(h_tc) if h_tc else ""
        cozulmus_p.append(p_kopya)
    return cozulmus_p


def personelleri_kaydet(veri_listesi):
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


def personel_izinlerini_yukle():
    veri = supabase_veri_oku("personel_izinleri", [])
    return veri if isinstance(veri, list) else []


def personel_izinlerini_kaydet(veri_listesi):
    supabase_veri_kaydet("personel_izinleri", veri_listesi)


# Eski modelde izinler her personelin içinde (personeller[].izinler) tutuluyordu.
_ESKI_IZIN_TURU_ESLEME = {
    "Yıllık İzin": "Yıllık İzin",
    "Sağlık Raporu": "Hastalık / Rapor",
    "Saatlik İzin": "Mazeret İzni",
}


def eski_izinleri_tasi():
    """Eski biçimdeki (personeller[].izinler) kayıtları yeni listeye (personel_izinleri) aktarır.
    Tekrar çalıştırılırsa aynı kaydı ikinci kez eklemez; aktarılan eski kayıtlar silinmez, boşaltılır."""
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
                # Yeni modelde saatlik izin yok: gün sayısı 0 tutulur, süre açıklamada saklanır.
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
        # ÖNEMLİ SIRA: önce yeni listeyi yaz, sonra eski kayıtları boşalt.
        # Ters sıra yapılırsa ve arada bir hata olursa veri kaybı yaşanır.
        personel_izinlerini_kaydet(mevcut)
        personelleri_kaydet(st.session_state.personeller)


def resmi_tatilleri_yukle():
    return supabase_veri_oku("resmi_tatiller", varsayilan_resmi_tatiller)


def yemek_uretim_arsivini_yukle():
    return supabase_veri_oku("yemek_uretim_arsivi", [])


def yemek_uretim_arsivini_kaydet(veri):
    supabase_veri_kaydet("yemek_uretim_arsivi", veri)


ARAYUZ_SAYFA_AYARLARI_ID = "arayuz_sayfa_ayarlari"
SAYFA_GRUPLARI = (
    "🏠 Genel Bakış",
    "📦 Depo & Stok Yönetimi",
    "🍲 Üretim & Mutfak",
    "👥 Sosyal & İnsan Kaynakları",
    "📈 Raporlar & Arşiv",
    "⚙️ Sistem Ayarları",
)
VARSAYILAN_BASLIK_RENKLERI = ("#ffffff", "#10b981", "#14b8a6", "#38bdf8")
SAYFA_VARSAYILAN_BASLIKLARI = {
    "Kurumsal Dashboard & Özet": "Genel Bakış & Operasyonel Özet",
    "Genel Bakış": "Genel Bakış & Operasyonel Özet",
    "Güncel Stok Durumu": "📦 Güncel Depo Envanteri ve Kritik Stoklar",
    "Yeni Mal Alımı / Fatura Ekle": "📝 Yeni Fatura ve Mal Alımı Girişi",
    "Depo Yönetimi": "🏢 Depo ve Kategori Yönetimi",
    "Demirbaş Yönetimi": "🛠️ Aşevi Demirbaş ve Ekipman Yönetimi",
    "QR Kod ile Hızlı Sarfiyat": "📷 QR Kod ile Hızlı Stok Düşümü",
    "Ürün Sil / Düzenle": "🗑️ Sistemden Ürün veya Kayıt Silme",
    "Fire / Zayiat Girişi": "🗑️ Fire / Zayiat Bildirimi",
    "Toplu Stok Düşümü & Sarfiyat": "🔄 Toplu Stok Düşümü ve Kullanılan Ürünler",
    "Günlük Yemek Üretimi & Maliyet Raporu": (
        "🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi"
    ),
    "Kalori Hesaplama Aracı": "🔥 Reçete ve Kalori Analiz Merkezi",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi": (
        "👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi"
    ),
    "Personel & Çalışma Süresi Takibi": "👥 Personel ve Çalışma Süresi Takibi",
    "Kullanım Takibi": "📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi",
    "Kapsamlı Envanter ve Hareket Raporu": (
        "📋 Kapsamlı Envanter ve Hareket Raporu"
    ),
    "Ürün Birim Fiyatları & Ay Analizi": (
        "💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi"
    ),
    "Kullanıcı Ayarları": "⚙️ Kullanıcı Yönetimi, Güvenlik ve Yedekleme",
}


def _arayuz_renk_kodu_gecerli_mi(deger):
    return (
        isinstance(deger, str)
        and len(deger) == 7
        and deger[0] == "#"
        and all(karakter in "0123456789abcdefABCDEF" for karakter in deger[1:])
    )


def _arayuz_sayisini_sinirla(deger, varsayilan, en_az, en_cok):
    try:
        sayi = int(deger)
    except (TypeError, ValueError):
        sayi = varsayilan
    return max(en_az, min(sayi, en_cok))


def arayuz_sayfa_ayarlarini_duzenle(veri):
    """Yalnızca tanımlı görsel ayarları ve metin bloklarını kabul eder."""
    if not isinstance(veri, dict):
        veri = {}

    sayfalar = {}
    ham_sayfalar = veri.get("sayfalar", {})
    if isinstance(ham_sayfalar, dict):
        for sayfa_id, ham_ayar in ham_sayfalar.items():
            if not isinstance(sayfa_id, str) or not isinstance(ham_ayar, dict):
                continue
            grup = ham_ayar.get("grup")
            renkler = ham_ayar.get("baslik_renkleri")
            if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
                renkler = VARSAYILAN_BASLIK_RENKLERI
            renkler = tuple(
                renk if _arayuz_renk_kodu_gecerli_mi(renk) else varsayilan
                for renk, varsayilan in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)
            )
            sayfalar[sayfa_id] = {
                "etiket": str(ham_ayar.get("etiket", ""))[:100],
                "baslik_metni": str(ham_ayar.get("baslik_metni", ""))[:160],
                "grup": grup if grup in SAYFA_GRUPLARI else "",
                "sira": _arayuz_sayisini_sinirla(
                    ham_ayar.get("sira", 0), 0, 0, 999
                ),
                "gorunur": bool(ham_ayar.get("gorunur", True)),
                "baslik_renkleri": list(renkler),
                "baslik_puntosu": _arayuz_sayisini_sinirla(
                    ham_ayar.get("baslik_puntosu", 30), 30, 16, 56
                ),
            }

    ozel_sayfalar = []
    ham_ozel_sayfalar = veri.get("ozel_sayfalar", [])
    if isinstance(ham_ozel_sayfalar, list):
        kullanilan_idler = set()
        for ham_sayfa in ham_ozel_sayfalar[:50]:
            if not isinstance(ham_sayfa, dict):
                continue
            sayfa_id = ham_sayfa.get("id")
            if (
                not isinstance(sayfa_id, str)
                or not sayfa_id.startswith("ozel-")
                or not sayfa_id[5:].isalnum()
                or sayfa_id in kullanilan_idler
            ):
                continue
            baslik = str(ham_sayfa.get("baslik", "")).strip()[:100]
            if not baslik:
                continue
            bloklar = []
            ham_bloklar = ham_sayfa.get("bloklar", [])
            if isinstance(ham_bloklar, list):
                for blok in ham_bloklar[:100]:
                    if not isinstance(blok, dict):
                        continue
                    tur = blok.get("tur")
                    metin = blok.get("metin")
                    if tur not in ("baslik", "metin") or not isinstance(metin, str):
                        continue
                    bloklar.append({"tur": tur, "metin": metin[:4000]})
            grup = ham_sayfa.get("grup")
            ozel_sayfalar.append(
                {
                    "id": sayfa_id,
                    "baslik": baslik,
                    "grup": grup if grup in SAYFA_GRUPLARI[:-1] else SAYFA_GRUPLARI[0],
                    "sira": _arayuz_sayisini_sinirla(
                        ham_sayfa.get("sira", 0), 0, 0, 999
                    ),
                    "gorunur": bool(ham_sayfa.get("gorunur", True)),
                    "bloklar": bloklar,
                }
            )
            kullanilan_idler.add(sayfa_id)

    return {"sayfalar": sayfalar, "ozel_sayfalar": ozel_sayfalar}


def arayuz_sayfa_ayarlarini_yukle():
    ham_veri = supabase_veri_oku(ARAYUZ_SAYFA_AYARLARI_ID, {}, kritik=False)
    return arayuz_sayfa_ayarlarini_duzenle(ham_veri)


def arayuz_sayfa_ayarlarini_kaydet(veri):
    temiz_veri = arayuz_sayfa_ayarlarini_duzenle(veri)
    supabase_veri_kaydet(ARAYUZ_SAYFA_AYARLARI_ID, temiz_veri)
    return temiz_veri


def arayuz_sayfa_ayari_al(ayarlar, sayfa_id):
    sayfalar = ayarlar.get("sayfalar", {}) if isinstance(ayarlar, dict) else {}
    ayar = sayfalar.get(sayfa_id, {}) if isinstance(sayfalar, dict) else {}
    renkler = ayar.get("baslik_renkleri", VARSAYILAN_BASLIK_RENKLERI)
    if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
        renkler = VARSAYILAN_BASLIK_RENKLERI
    temiz_renkler = [
        renk if _arayuz_renk_kodu_gecerli_mi(renk) else varsayilan
        for renk, varsayilan in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)
    ]
    return {
        "etiket": str(ayar.get("etiket", "")),
        "baslik_metni": str(ayar.get("baslik_metni", "")),
        "grup": ayar.get("grup", ""),
        "sira": _arayuz_sayisini_sinirla(ayar.get("sira", 0), 0, 0, 999),
        "gorunur": bool(ayar.get("gorunur", True)),
        "baslik_renkleri": temiz_renkler,
        "baslik_puntosu": _arayuz_sayisini_sinirla(
            ayar.get("baslik_puntosu", 30), 30, 16, 56
        ),
    }


def sayfa_baslik_metnini_al(ayarlar, sayfa_id):
    sayfalar = ayarlar.get("sayfalar", {}) if isinstance(ayarlar, dict) else {}
    sayfa = sayfalar.get(sayfa_id, {}) if isinstance(sayfalar, dict) else {}
    duzenlenmis = str(sayfa.get("baslik_metni", "")).strip()
    return duzenlenmis or SAYFA_VARSAYILAN_BASLIKLARI.get(sayfa_id, sayfa_id)


if "kalori_sepeti" not in st.session_state:
    st.session_state.kalori_sepeti = []
if "kullanicilar" not in st.session_state:
    st.session_state.kullanicilar = kullanıcıları_yukle()

if "hatali_giris_sayisi" not in st.session_state:
    st.session_state.hatali_giris_sayisi = 0
if "kilitlenme_bitis_zamani" not in st.session_state:
    st.session_state.kilitlenme_bitis_zamani = 0

# F5 sonrası kilit bilgisini çerezden geri yükle
kilit_cerez = cerez_oku("kilit_zamani")
if kilit_cerez:
    try:
        kilit_zamani = float(kilit_cerez)
        if kilit_zamani > time.time():
            st.session_state.kilitlenme_bitis_zamani = kilit_zamani
        else:
            cerez_sil("kilit_zamani")
    except Exception:
        cerez_sil("kilit_zamani")

query_params = st.query_params

# Eski, güvensiz parametreleri URL'den temizle
for _eski in ("auth", "user"):
    if _eski in query_params:
        del query_params[_eski]

if "oturum_aktif" not in st.session_state:
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
# Eski sürümden kalan oturumlarda eksik anahtarları tamamla
for _anahtar, _deger in (("oturum_token", ""), ("oturum_bitis", 0)):
    if _anahtar not in st.session_state:
        st.session_state[_anahtar] = _deger

# Giriş yapılmamışsa: Sadece çerezdeki token ile oturumu geri yüklemeyi dene
if not st.session_state.oturum_aktif:
    # K2: Yalnızca çerez. URL'deki eski token varsa hemen temizle.
    if "token" in st.query_params:
        del st.query_params["token"]

    aday_token = cerez_oku() if cerez_kontrol is not None else ""
    
    # F5 sonrası stx kütüphanesinin çerezi okuyabilmesi için 1 kerelik bekleme (BURAYI EKLE)
    
    if not aday_token and cerez_kontrol is not None:
        if not st.session_state.get("_cerez_beklemesi_yapildi"):
            st.session_state["_cerez_beklemesi_yapildi"] = True
            time.sleep(0.5)
            st.rerun()
    if aday_token:
        kayit = oturum_dogrula(aday_token)
        if kayit and kayit.get("kullanici") in st.session_state.kullanicilar:
            st.session_state.oturum_aktif = True
            st.session_state.aktif_kullanici = kayit["kullanici"]
            st.session_state.oturum_token = aday_token
            st.session_state.oturum_bitis = kayit["bitis"]
            st.session_state["son_etkinlik"] = time.time()
            st.session_state["_oturum_son_dogrulama"] = time.time()
        else:
            if cerez_kontrol is not None and not st.session_state.get("_cerez_temizlendi"):
                cerez_sil()
                st.session_state["_cerez_temizlendi"] = True

# Her çalışmada: token'sız (eski), süresi dolmuş veya kullanıcısı silinmiş oturumu kapat
if st.session_state.oturum_aktif and (
    not st.session_state.oturum_token
    or st.session_state.aktif_kullanici not in st.session_state.kullanicilar
    or time.time() > st.session_state.oturum_bitis
):
    oturum_sil(st.session_state.oturum_token)
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    if "token" in st.query_params:
        del st.query_params["token"]

# Boşta kalma: Streamlit yalnızca kullanıcı işlem yapınca çalıştığı için, her çalışma bir etkinliktir.
if st.session_state.oturum_aktif:
    _simdi = time.time()
    if _simdi - st.session_state.get("son_etkinlik", _simdi) > bosta_kalma_suresi_sn():
        oturumu_zorla_kapat(
            "Uzun süre işlem yapılmadığı için oturumunuz güvenlik nedeniyle kapatıldı. Lütfen yeniden giriş yapın.",
            "boşta kalma nedeniyle oturum kapandı",
        )
    else:
        st.session_state["son_etkinlik"] = _simdi

# Açık oturumu belirli aralıkla veritabanından yeniden doğrula ve kullanıcı yetkilerini tazele:
# silinen/şifresi değişen/yetkisi kısıtlanan kullanıcı 8 saat beklemeden en geç 1 dk içinde etkilenir.
# Geçici veritabanı hatasında oturum AÇIK bırakılır (ağ kesintisi herkesi dışarı atmasın).
if st.session_state.oturum_aktif and SUPABASE_URL and SUPABASE_KEY:
    _simdi = time.time()
    if _simdi - st.session_state.get("_oturum_son_dogrulama", 0) > OTURUM_DOGRULAMA_ARALIGI_SN:
        st.session_state["_oturum_son_dogrulama"] = _simdi
        _d, _oturumlar = _supabase_ham_oku("aktif_oturumlar")
        if _d in ("ok", "yok"):
            _kayit = (_oturumlar or {}).get(_token_hashle(st.session_state.oturum_token)) if isinstance(_oturumlar, dict) else None
            if not _kayit or _kayit.get("bitis", 0) <= _simdi:
                oturumu_zorla_kapat(
                    "Oturumunuz sonlandırıldı (başka bir yerden kapatıldı, şifreniz değişti veya süre doldu). Lütfen yeniden giriş yapın.",
                    "oturum sunucuda geçersiz, kapatıldı",
                )
        if st.session_state.oturum_aktif:
            _kd, _ = _supabase_ham_oku("kullanici_yetkileri")
            if _kd == "ok":
                st.session_state.kullanicilar = kullanıcıları_yukle()
                if st.session_state.aktif_kullanici not in st.session_state.kullanicilar:
                    oturumu_zorla_kapat("Hesabınız bulunamadı. Lütfen yöneticiyle iletişime geçin.", "hesap silinmiş, oturum kapandı")

if st.session_state.oturum_aktif:
    if "arayuz_sayfa_ayarlari" not in st.session_state:
        st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_yukle()
    if "girisler" not in st.session_state:
        st.session_state.girisler = idleri_benzersiz_yap(verileri_yukle(), "FAT-")
    if "kullanim_loglari" not in st.session_state:
        st.session_state.kullanim_loglari = loglari_yukle()
    if "silinen_urun_loglari" not in st.session_state:
        st.session_state.silinen_urun_loglari = silinen_urun_loglarini_yukle()
    if "ihtiyac_sahipleri" not in st.session_state:
        st.session_state.ihtiyac_sahipleri = idleri_benzersiz_yap(ihtiyac_sahiplerini_yukle(), "IHT-")
    if "dagitim_loglari" not in st.session_state:
        st.session_state.dagitim_loglari = idleri_benzersiz_yap(dagitim_loglarini_yukle(), "DAG-")
    if "personeller" not in st.session_state:
        st.session_state.personeller = idleri_benzersiz_yap(personelleri_yukle(), "PER-")
    if "personel_izinleri" not in st.session_state:
        st.session_state.personel_izinleri = idleri_benzersiz_yap(personel_izinlerini_yukle(), "IZN-")
        eski_izinleri_tasi()
    if "resmi_tatiller" not in st.session_state:
        st.session_state.resmi_tatiller = resmi_tatilleri_yukle()
    if "yemek_uretim_arsivi" not in st.session_state:
        st.session_state.yemek_uretim_arsivi = yemek_uretim_arsivini_yukle()
    if "depolar" not in st.session_state:
        st.session_state.depolar = depoları_yukle()
    if "demirbaslar" not in st.session_state:
        st.session_state.demirbaslar = idleri_benzersiz_yap(demirbasları_yukle(), "DEM-")
    if "kritik_seviyeler" not in st.session_state:
        st.session_state.kritik_seviyeler = kritik_seviyeleri_yukle()
    if "personel_silme_mesaji" not in st.session_state:
        st.session_state.personel_silme_mesaji = ""
    if "dagitim_silme_mesaji" not in st.session_state:
        st.session_state.dagitim_silme_mesaji = ""
    if "dashboard_widgets" not in st.session_state:
        st.session_state.dashboard_widgets = widgetlari_yukle()

gecerli_menuler = [
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
    "Kullanıcı Ayarları",
]
gecerli_menuler.extend(
    sayfa["id"]
    for sayfa in st.session_state.arayuz_sayfa_ayarlari["ozel_sayfalar"]
    if sayfa["gorunur"]
)

if "aktif_menu" not in st.session_state:
    if "menu" in query_params and query_params["menu"] in gecerli_menuler:
        st.session_state.aktif_menu = query_params["menu"]
    else:
        st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"

if "silme_mesaji" not in st.session_state:
    st.session_state.silme_mesaji = ""
if "kisi_silme_mesaji" not in st.session_state:
    st.session_state.kisi_silme_mesaji = ""


def net_calisma_gunu_hesapla(
    baslangic_tarihi, bitis_tarihi, izin_listesi, tatil_listesi
):
    if baslangic_tarihi > bitis_tarihi:
        return 0, 0, 0, 0
    tatil_tarihleri = {
        datetime.datetime.strptime(t["tarih"], "%Y-%m-%d").date()
        for t in tatil_listesi
    }
    tam_gun_izin_tarihleri = set()
    saglik_raporu_gun_sayisi = 0
    saatlik_izin_toplam_saat = 0.0

    for izin in izin_listesi:
        tur = izin.get("tur", "Yıllık İzin")
        i_bas = datetime.datetime.strptime(izin["baslangic"], "%Y-%m-%d").date()
        i_bit = datetime.datetime.strptime(izin["bitis"], "%Y-%m-%d").date()
        if tur == "Saatlik İzin":
            saatlik_izin_toplam_saat += float(izin.get("saat", 2.0))
        elif tur == "Sağlık Raporu":
            curr = i_bas
            while curr <= i_bit:
                if curr.weekday() < 5 and curr not in tatil_tarihleri:
                    saglik_raporu_gun_sayisi += 1
                curr += datetime.timedelta(days=1)
        else:
            curr = i_bas
            while curr <= i_bit:
                tam_gun_izin_tarihleri.add(curr)
                curr += datetime.timedelta(days=1)

    net_gun = 0
    toplam_izin_gunu = len(tam_gun_izin_tarihleri)
    curr = baslangic_tarihi
    while curr <= bitis_tarihi:
        hafta_sonu = curr.weekday() >= 5
        resmi_tatil = curr in tatil_tarihleri
        izinli = curr in tam_gun_izin_tarihleri
        if not hafta_sonu and not resmi_tatil and not izinli:
            net_gun += 1
        curr += datetime.timedelta(days=1)
    return net_gun, toplam_izin_gunu, saglik_raporu_gun_sayisi, saatlik_izin_toplam_saat


def bugunun_turkce_tarihi():
    simdi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).date() if hasattr(datetime, "datetime") else datetime.date.today()
    aylar = {
        1: "Ocak",
        2: "Şubat",
        3: "Mart",
        4: "Nisan",
        5: "Mayıs",
        6: "Haziran",
        7: "Temmuz",
        8: "Ağustos",
        9: "Eylül",
        10: "Ekim",
        11: "Kasım",
        12: "Aralık",
    }
    gunler = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }
    return f"{simdi.day} {aylar.get(simdi.month, '')} {simdi.year}, {gunler.get(simdi.weekday(), '')}"


# =========================================================================
# GİRİŞ KONTROLÜ / AÇILIŞ GİRİŞ EKRANI
# =========================================================================
if not st.session_state.oturum_aktif:
    login_accent = "#10b981"
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
                color: {login_accent};
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
            .login-hero h1 .login-brand-accent {{ color: {login_accent} !important; }}
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
                border-color: {login_accent} !important;
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
    login_layout = st.container(key="login-layout")
    login_left, login_right = login_layout.columns([1, 1], gap="large")
    with login_left:
        st.markdown(
            """
            <section class="login-hero">
                <div class="login-eyebrow">🍲 AŞEVİ OTOMASYONU</div>
                <h1>Aziziye <span class="login-brand-accent">Aşevi</span></h1>
                <h3>Yönetim &amp; Takip Sistemi</h3>
                <p>Stok girişinden yemek dağıtımına, fire takibinden personel
                yönetimine kadar tüm süreçler tek panelde. Sadece giriş yapın,
                gerisini sistem halletsin.</p>
            </section>
            <section class="login-feature-grid">
                <article class="login-feature-card">
                    <div class="login-feature-icon">📦</div>
                    <h4>Stok Yönetimi</h4>
                    <p>Fatura bazlı giriş, anlık kalan, kritik seviye uyarıları</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon">🍲</div>
                    <h4>Yemek Üretimi</h4>
                    <p>Kişi başı maliyet, kalori ve porsiyon hesabı</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon">🗑️</div>
                    <h4>Fire &amp; Zayiat</h4>
                    <p>Parti bazlı fire tutarı ve neden analizi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon">📱</div>
                    <h4>QR Sarfiyat</h4>
                    <p>QR ile hızlı düşüm ve paket takibi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon">👥</div>
                    <h4>Personel</h4>
                    <p>İzin, çalışma süresi ve demirbaş zimmet takibi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon">📊</div>
                    <h4>Raporlama</h4>
                    <p>Günlük, haftalık ve aylık otomatik e-posta raporları</p>
                </article>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='login-version'>{APP_VERSION} · {LAST_UPDATE}</div>",
            unsafe_allow_html=True,
        )

    with login_right.container(key="login-card"):
        st.markdown(
            f"""
                <div style="text-align:center; font-size:30px; margin:0;">🍲</div>
                <h2>Giriş Yap</h2>
                <p class="login-subtitle">Devam etmek için hesabınızla giriş yapın</p>
            """,
            unsafe_allow_html=True,
        )

            
        if st.session_state.get("oturum_mesaji"):
            st.warning(st.session_state.pop("oturum_mesaji"))

        if st.session_state.get("ilk_kurulum_sifreleri"):
            _satirlar = "\n".join(
                f"- **{ad}** → `{sf}`" for ad, sf in st.session_state["ilk_kurulum_sifreleri"].items()
            )
            st.warning(
                "🔑 **İlk kurulum şifreleri** (yalnızca burada, bir kez gösterilir; şimdi not edin). "
                "İlk girişte yeni şifre belirlemeniz istenecek:\n\n" + _satirlar
            )

        simdikiekran_zaman = time.time() 
        
        # F5 (sayfa yenileme) atlatmasını önlemek için sunucudan (IP bazlı) kilidi kontrol et
        istemci_ip, _xff = istemci_ip_bilgisi()
        ip_anahtar = f"ip|{istemci_ip}"
        kalan_kilit_db = giris_kilit_kalan(ip_anahtar) if istemci_ip and istemci_ip != "bilinmiyor" else 0

        kilitli_mi = st.session_state.kilitlenme_bitis_zamani > simdikiekran_zaman or kalan_kilit_db > 0

        if kilitli_mi:
            kalan_sure = max(int(st.session_state.kilitlenme_bitis_zamani - simdikiekran_zaman), kalan_kilit_db)
            st.error(f"⚠️ Çok fazla hatalı giriş yaptınız! Güvenlik nedeniyle girişler {kalan_sure} saniye süreyle kilitlendi.")
        else:
            with st.form("merkezi_giris_formu"):
                st.markdown("**Kullanıcı Adı**")
                k_adi_inp = st.text_input(
                    "Kullanıcı Adı",
                    placeholder="Kullanıcı adı giriniz...",
                    label_visibility="collapsed",
                ).strip().lower()
                st.markdown("**Şifre**")
                sifre_inp = st.text_input(
                    "Şifre",
                    type="password",
                    placeholder="Şifre giriniz...",
                    label_visibility="collapsed",
                )

                giris_tikla = st.form_submit_button(
                    "Giriş Yap", use_container_width=True
                )

                if giris_tikla:
                    kullanici_db = st.session_state.kullanicilar
                    istemci_ip, _xff = istemci_ip_bilgisi()
                    kullanici_var = k_adi_inp in kullanici_db
                    log_adi = k_adi_inp if kullanici_var else "(bilinmeyen kullanıcı)"
                    u_anahtar = f"u|{k_adi_inp if kullanici_var else '_bilinmeyen'}|{istemci_ip}"
                    ip_anahtar = f"ip|{istemci_ip}"
                    kalan_kilit = max(giris_kilit_kalan(u_anahtar), giris_kilit_kalan(ip_anahtar))

                    if kalan_kilit > 0:
                        giris_logla(log_adi, "kilitliyken deneme")
                        st.error(f"⚠️ Çok fazla hatalı deneme. Lütfen {kalan_kilit} saniye sonra tekrar deneyin.")
                    else:
                        kayitli_hash = str(kullanici_db.get(k_adi_inp, {}).get("sifre", ""))
                        if kullanici_var:
                            gecerli = (kayitli_hash != "" or k_adi_inp == "misafir") and sifre_dogrula(sifre_inp, kayitli_hash)
                        else:
                            sifre_dogrula(sifre_inp, sifre_hashle_yeni("sahte"))
                            gecerli = False

                        if gecerli:
                            if sifre_yukseltilmeli_mi(kayitli_hash):
                                if kayitli_hash in ESKI_VARSAYILAN_HASHLER:
                                    kullanici_db[k_adi_inp]["sifre_degistirilmeli"] = True
                                kullanici_db[k_adi_inp]["sifre"] = sifre_hashle_yeni(sifre_inp)
                                kullanıcıları_kaydet(kullanici_db)
                            st.session_state.hatali_giris_sayisi = 0
                            if istemci_ip and istemci_ip != "bilinmiyor":
                                giris_denemesini_sifirla(u_anahtar, ip_anahtar)
                            else:
                                giris_denemesini_sifirla(u_anahtar)
                            cerez_sil("kilit_zamani")
                            giris_logla(k_adi_inp, "başarılı giriş")
                            oturumu_baslat(k_adi_inp)
                            st.rerun()
                        else:
                            kalan_hak, kilit_u = hatali_giris_kaydet(u_anahtar, MAKS_HATALI_GIRIS, KILIT_SURESI_SN)
                            if istemci_ip and istemci_ip != "bilinmiyor":
                                _, kilit_ip = hatali_giris_kaydet(ip_anahtar, IP_MAKS_HATALI_GIRIS, IP_KILIT_SURESI_SN)
                            else:
                                kilit_ip = False
                            giris_logla(log_adi, "hatalı giriş")
                            st.session_state.hatali_giris_sayisi += 1
                            if kilit_u or kilit_ip:
                                st.session_state.kilitlenme_bitis_zamani = time.time() + KILIT_SURESI_SN
                                st.session_state.hatali_giris_sayisi = 0
                                cerez_yaz(str(int(st.session_state.kilitlenme_bitis_zamani)), "kilit_zamani", max_age=3600)
                                time.sleep(0.8)  # Çerezin tarayıcıya yazılması için bekle
                                st.rerun()
                            else:
                                st.error(f"Hatalı kullanıcı adı veya şifre! Kalan deneme hakkı: {max(kalan_hak, 0)}")
            
        st.markdown(
            f"<div style='text-align: center; margin: 16px 0; opacity: 0.4; font-size: 13px; color: {subtext_color};'>veya</div>",
            unsafe_allow_html=True,
        )

        misafir_ayar = st.session_state.kullanicilar.get("misafir", {})
        misafir_buton_metni = misafir_ayar.get("buton_metni", "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)")
        misafir_buton_aktif = misafir_ayar.get("buton_aktif", True)

        if misafir_buton_aktif:
            if st.button(
                misafir_buton_metni,
                use_container_width=True,
                type="secondary",
            ):
                giris_logla("misafir", "misafir girişi")
                oturumu_baslat("misafir")
                st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        with st.expander("🔑 Admin Şifre Kurtarma (Master Key)"):
            tanimli_master = str(secret_deger("MASTER_RECOVERY_KEY", "") or "")
            if not tanimli_master:
                st.info(
                    "Şifre kurtarma devre dışı. Etkinleştirmek için `secrets` ayarlarına "
                    "güçlü bir `MASTER_RECOVERY_KEY` ekleyin. Eklediğiniz hâlde bu mesajı görüyorsanız "
                    "secrets'a `TANI_MODU = \"1\"` ekleyip adres sonuna `?tani=1` yazarak Bağlantı Tanılama sayfasına bakın."
                )
            else:
                with st.form("master_key_sifre_sifirla"):
                    st.markdown("Şifrenizi unuttuysanız kurtarma anahtarı ile admin için geçici bir şifre üretebilirsiniz.")
                    master_key_inp = st.text_input("Kurtarma Anahtarı (Master Recovery Key)", type="password")
                    sifirla_btn = st.form_submit_button("Admin Şifresini Sıfırla")

                    if sifirla_btn:
                        m_ip, _ = istemci_ip_bilgisi()
                        m_anahtar = f"master|{m_ip}"
                        m_kalan = giris_kilit_kalan(m_anahtar)
                        if m_kalan > 0:
                            st.error(f"⚠️ Çok fazla hatalı deneme. {m_kalan} saniye sonra tekrar deneyin.")
                        elif hmac.compare_digest(master_key_inp.encode("utf-8"), tanimli_master.encode("utf-8")):
                            if "admin" in st.session_state.kullanicilar:
                                gecici_sifre = secrets.token_urlsafe(10)
                                st.session_state.kullanicilar["admin"]["sifre"] = sifre_hashle_yeni(gecici_sifre)
                                st.session_state.kullanicilar["admin"]["sifre_degistirilmeli"] = True
                                kullanıcıları_kaydet(st.session_state.kullanicilar)
                                kullanici_oturumlarini_kapat("admin")
                                giris_denemesini_sifirla()
                                giris_logla("admin", "şifre master key ile sıfırlandı")
                                st.success("Admin için geçici şifre üretildi. Şimdi not edin; girişte değiştirmeniz istenecek:")
                                st.code(gecici_sifre)
                            else:
                                st.error("Admin kullanıcısı veritabanında bulunamadı.")
                        else:
                            hatali_giris_kaydet(m_anahtar, 5, 120)
                            giris_logla("(master key)", "hatalı kurtarma anahtarı")
                            st.error("Hatalı Kurtarma Anahtarı!")

    with login_right.container(key="login-support"):
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button(
            "✉️ İletişim / Destek", use_container_width=True, type="secondary"
        ):
            st.info("📩 İletişim için **sefaunaltopcu@gmail.com** mail adresi ile iletişime geçebilirsiniz.")

    st.stop()

# =========================================================================
# ZORUNLU ŞİFRE DEĞİŞİMİ (ilk kurulum / eski varsayılan şifre / sıfırlanmış şifre)
# =========================================================================
_aktif_kb = st.session_state.kullanicilar.get(st.session_state.aktif_kullanici, {})
if st.session_state.aktif_kullanici != "misafir" and (
    _aktif_kb.get("sifre_degistirilmeli") or _aktif_kb.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
):
    _z1, _z2, _z3 = st.columns([1, 1.6, 1])
    with _z2:
        st.markdown("### 🔐 Şifrenizi değiştirmeniz gerekiyor")
        st.info(
            "Güvenlik nedeniyle devam etmeden önce yeni bir şifre belirlemelisiniz "
            "(en az 10 karakter, en az bir harf ve bir rakam)."
        )
        with st.form("zorunlu_sifre_formu"):
            z_yeni1 = st.text_input("Yeni Şifre", type="password")
            z_yeni2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
            z_kaydet = st.form_submit_button("Şifreyi Kaydet", use_container_width=True)
            if z_kaydet:
                z_hata = sifre_politika_hatasi(z_yeni1)
                if z_hata:
                    st.error(z_hata)
                elif z_yeni1 != z_yeni2:
                    st.error("Şifreler aynı değil.")
                elif sifre_dogrula(z_yeni1, _aktif_kb.get("sifre", "")):
                    st.error("Yeni şifre eskisiyle aynı olamaz.")
                else:
                    sifre_degistir(
                        st.session_state.aktif_kullanici, z_yeni1,
                        haric_token=st.session_state.oturum_token,
                    )
                    st.success("Şifreniz güncellendi.")
                    st.rerun()
        if st.button("Oturumu Kapat", key="zorunlu_cikis_btn"):
            oturumu_kapat()
            st.rerun()
    st.stop()

# =========================================================================
# ANA UYGULAMA İÇERİĞİ
# =========================================================================
st.markdown("### 🍲 AZİZİYE - AŞEVİ TAKİP EKRANI ")
st.markdown(f"**Hoş geldiniz** &nbsp;|&nbsp; 📅 {bugunun_turkce_tarihi()}")
st.markdown("---")

kullanici_adi_goruntule = (
    st.session_state.aktif_kullanici.upper()
    if st.session_state.oturum_aktif
    else "MİSAFİR"
)
kullanici_adi_goruntule = html_escape(kullanici_adi_goruntule)

st.sidebar.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 12px 8px 18px 8px; border-bottom: 1px solid {border_color}; margin-bottom: 12px;">
        <div style="background: rgba(99, 102, 241, 0.1); color: {text_color}; width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; border: 1px solid {border_color}; backdrop-filter: blur(12px);">
            🍲
        </div>
        <div>
            <div style="font-weight: 700; font-size: 15px; color: {text_color}; letter-spacing: -0.02em;">AZİZİYE AŞEVİ</div>
            <div style="font-size: 11px; color: {subtext_color}; font-weight: 500;">Yönetim & Takip Sistemi</div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div style="background: transparent; padding: 6px 8px; display: flex; align-items: center; justify-content: space-between; margin-top: 12px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: rgba(99, 102, 241, 0.12); color: {text_color}; width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border: 1px solid {border_color};">
                {kullanici_adi_goruntule[:1]}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 13.5px; color: {text_color};">{kullanici_adi_goruntule}</div>
                <div style="font-size: 11px; color: {subtext_color};">Aktif Oturum</div>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

sidebar_arama = st.sidebar.text_input(
    "🔍 Hızlı Arama",
    placeholder="Öğe veya log ara...",
    label_visibility="collapsed",
).strip().lower()

otomatik_yonlendirilen_menu = None
if sidebar_arama:
    urun_veya_fatura_bulundu = any(
        sidebar_arama in g.get("urun", "").lower()
        or sidebar_arama in g.get("fatura_no", "").lower()
        for g in st.session_state.girisler
    )
    if urun_veya_fatura_bulundu:
        otomatik_yonlendirilen_menu = "Güncel Stok Durumu"

    personel_bulundu = any(
        sidebar_arama in p.get("ad_soyad", "").lower()
        or sidebar_arama in p.get("tc", "")
        for p in st.session_state.personeller
    )
    if personel_bulundu:
        otomatik_yonlendirilen_menu = "Personel & Çalışma Süresi Takibi"

    ihtiyac_sahibi_bulundu = any(
        sidebar_arama in i.get("ad_soyad", "").lower()
        or sidebar_arama in i.get("tc_hane", "")
        for i in st.session_state.ihtiyac_sahipleri
    )
    if ihtiyac_sahibi_bulundu:
        otomatik_yonlendirilen_menu = "İhtiyaç Sahibi & Yemek Dağıtım Takibi"

    if otomatik_yonlendirilen_menu:
        st.session_state.aktif_menu = otomatik_yonlendirilen_menu
        st.query_params["menu"] = otomatik_yonlendirilen_menu

st.sidebar.markdown(
    f'<p style="font-size: 11px; font-weight: 700; margin-top: 12px; margin-bottom: 8px; padding-left: 4px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; color: {subtext_color};">ÇALIŞMA ALANI NAVİGASYONU</p>',
    unsafe_allow_html=True,
)

yonetici_modu = (
    st.session_state.oturum_aktif
    and st.session_state.aktif_kullanici == "admin"
)
misafir_modu = (
    not st.session_state.oturum_aktif
    or st.session_state.aktif_kullanici == "misafir"
)

aktif_k_bilgi = st.session_state.kullanicilar.get(
    st.session_state.aktif_kullanici, {}
)
kullanici_salt_okunur_mu = aktif_k_bilgi.get("salt_okunur", False) or st.session_state.aktif_kullanici in ["yonetim", "misafir"]

yonetim_modu = (
    st.session_state.oturum_aktif
    and kullanici_salt_okunur_mu
)
salt_okunur_modu = misafir_modu or yonetim_modu

yasakli_menuler_listesi = aktif_k_bilgi.get("yasakli_menuler", [])
aktif_k_maskeleri = aktif_k_bilgi.get("maskeli_alanlar", [])

toplam_aktif_stok_sayisi = len(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
aktif_personel_sayisi = sum(
    1 for p in st.session_state.personeller if p.get("aktif", True)
)

menu_gruplari = {
    "🏠 Genel Bakış": [("Kurumsal Dashboard & Özet", "")],
    "📦 Depo & Stok Yönetimi": [
        ("Güncel Stok Durumu", str(toplam_aktif_stok_sayisi)),
        ("Yeni Mal Alımı / Fatura Ekle", ""),
        ("QR Kod ile Hızlı Sarfiyat", ""),
        ("Ürün Sil / Düzenle", ""),
        ("Fire / Zayiat Girişi", ""),
        ("Toplu Stok Düşümü & Sarfiyat", ""),
        ("Ürün Birim Fiyatları & Ay Analizi", ""),
        ("Depo Yönetimi", str(len(st.session_state.depolar))),
        ("Demirbaş Yönetimi", str(len(st.session_state.demirbaslar))),
    ],
    "🍲 Üretim & Mutfak": [
        ("Günlük Yemek Üretimi & Maliyet Raporu", ""),
        ("Kalori Hesaplama Aracı", ""),
    ],
    "👥 Sosyal & İnsan Kaynakları": [
        (
            "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
            str(len(st.session_state.ihtiyac_sahipleri)),
        ),
        ("Personel & Çalışma Süresi Takibi", str(aktif_personel_sayisi)),
    ],
    "📈 Raporlar & Arşiv": [
        ("Kullanım Takibi", ""),
        ("Kapsamlı Envanter ve Hareket Raporu", ""),
    ],
}

if yonetici_modu:
    menu_gruplari["⚙️ Sistem Ayarları"] = [(
        "Kullanıcı Ayarları",
        str(len(st.session_state.kullanicilar)),
    )]

_arayuz_ayar = st.session_state.arayuz_sayfa_ayarlari
_orijinal_menu_gruplari = menu_gruplari
menu_gruplari = {grup: [] for grup in menu_gruplari}
menu_gorunen_etiketler = {}
menu_varsayilan_gruplari = {}
menu_varsayilan_siralari = {}
for _grup, _alt_menuler in _orijinal_menu_gruplari.items():
    for _indeks, (_menu_anahtari, _badge) in enumerate(_alt_menuler):
        _ayar = arayuz_sayfa_ayari_al(_arayuz_ayar, _menu_anahtari)
        menu_varsayilan_gruplari[_menu_anahtari] = _grup
        menu_varsayilan_siralari[_menu_anahtari] = _indeks
        if not _ayar["gorunur"]:
            continue
        _hedef_grup = _ayar["grup"] or _grup
        if _hedef_grup not in menu_gruplari:
            menu_gruplari[_hedef_grup] = []
        menu_gruplari[_hedef_grup].append(
            (
                _menu_anahtari,
                _badge,
                _ayar["sira"]
                if _menu_anahtari in _arayuz_ayar["sayfalar"]
                else _indeks,
            )
        )
        menu_gorunen_etiketler[_menu_anahtari] = (
            _ayar["etiket"].strip() or _menu_anahtari
        )

for _sayfa in _arayuz_ayar["ozel_sayfalar"]:
    if not _sayfa["gorunur"]:
        continue
    menu_gruplari.setdefault(_sayfa["grup"], []).append(
        (_sayfa["id"], "", _sayfa["sira"])
    )
    menu_gorunen_etiketler[_sayfa["id"]] = _sayfa["baslik"]

for _grup in menu_gruplari:
    menu_gruplari[_grup].sort(key=lambda _oge: _oge[2])

filtrelenmis_gruplar = {}
for grup_adi, alt_menuler in menu_gruplari.items():
    uygun_menuler = []
    for m, badge, _sira in alt_menuler:
        gorunen_adi = menu_gorunen_etiketler.get(m, m)
        if misafir_modu and m in [
            "Güncel Stok Durumu",
            "Ürün Sil / Düzenle",
            "Fire / Zayiat Girişi",
            "Toplu Stok Düşümü & Sarfiyat",
            "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
            "Personel & Çalışma Süresi Takibi",
            "Kullanım Takibi",
            "Kapsamlı Envanter ve Hareket Raporu",
            "Depo Yönetimi",
            "Demirbaş Yönetimi",
        ]:
            continue
        if not yonetici_modu and m in yasakli_menuler_listesi:
            continue
        if (
            not sidebar_arama
            or sidebar_arama in gorunen_adi.lower()
            or sidebar_arama in grup_adi.lower()
            or otomatik_yonlendirilen_menu == m
        ):
            uygun_menuler.append((m, badge))
    if uygun_menuler:
        filtrelenmis_gruplar[grup_adi] = uygun_menuler

for grup_adi, alt_menuler in filtrelenmis_gruplar.items():
    grup_aktif_mu = any(st.session_state.aktif_menu == m for m, _ in alt_menuler)
    with st.sidebar.expander(
        grup_adi, expanded=grup_aktif_mu or bool(sidebar_arama)
    ):
        for m, badge in alt_menuler:
            if m == "Yeni Mal Alımı / Fatura Ekle" and salt_okunur_modu:
                continue

            gorunen_adi = menu_gorunen_etiketler.get(m, m)
            btn_label = f"{gorunen_adi}  [{badge}]" if badge and badge != "0" else gorunen_adi
            btn_type = (
                "primary" if st.session_state.aktif_menu == m else "secondary"
            )
            if st.button(
                btn_label, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"
            ):
                st.session_state.aktif_menu = m
                st.query_params["menu"] = m
                st.rerun()

st.sidebar.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button(
    "Oturumu Kapat", use_container_width=True, type="secondary"
):
    oturumu_kapat()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<p style="font-size: 11px; text-align: center; opacity: 0.5; color: {subtext_color};">sefautopcu</p>',
    unsafe_allow_html=True,
)
st.sidebar.caption(f"🚀 {APP_VERSION} · Son güncelleme: {LAST_UPDATE}")
if yonetici_modu:  # sunucu bellek bilgisi yalnızca admin'e gösterilir
    ram_kullanimi = bellek_kullanimi_al()
    if ram_kullanimi > 0:
        st.sidebar.caption(f"💾 **RAM Kullanımı:** {ram_kullanimi} MB")
        if st.sidebar.button("🧹 Önbellek Temizle", key="sb_ram_clean_btn", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


def admin_sayfa_duzenleyici():
    st.markdown("### 🧩 Kod Yazmadan Sayfa Düzenleyici")
    st.caption(
        "Mevcut iş akışlarının kodunu değiştirmeden sayfa menülerini ve başlık görünümünü "
        "yönetin; özel metin sayfaları oluşturun. Yerleşik sayfalar silinmez, menüden gizlenir. "
        "Python kodu veya HTML çalıştırılamaz."
    )
    arayuz = json.loads(
        json.dumps(st.session_state.arayuz_sayfa_ayarlari, ensure_ascii=False)
    )
    ozel_sayfalar = arayuz["ozel_sayfalar"]
    yerlesik_sayfalar = [
        sayfa_id for sayfa_id in gecerli_menuler
        if not sayfa_id.startswith("ozel-")
    ]
    sayfa_secenekleri = yerlesik_sayfalar + [
        sayfa["id"] for sayfa in ozel_sayfalar
    ]
    gorunen_etiketler = dict(menu_gorunen_etiketler)
    gorunen_etiketler.update(
        {sayfa["id"]: sayfa["baslik"] for sayfa in ozel_sayfalar}
    )
    secici_surumu = hashlib.sha256(
        "|".join(sayfa_secenekleri).encode("utf-8")
    ).hexdigest()[:10]
    secilen_sayfa_id = st.selectbox(
        "Düzenlenecek sayfa",
        sayfa_secenekleri,
        format_func=lambda sayfa_id: gorunen_etiketler.get(sayfa_id, sayfa_id),
        key=f"arayuz_sayfa_sec_{secici_surumu}",
    )
    sayfa_ayari = arayuz_sayfa_ayari_al(arayuz, secilen_sayfa_id)
    ozel_sayfa = next(
        (sayfa for sayfa in ozel_sayfalar if sayfa["id"] == secilen_sayfa_id),
        None,
    )
    varsayilan_grup = (
        sayfa_ayari["grup"]
        or (
            ozel_sayfa["grup"]
            if ozel_sayfa
            else menu_varsayilan_gruplari.get(secilen_sayfa_id, SAYFA_GRUPLARI[0])
        )
    )
    if varsayilan_grup not in SAYFA_GRUPLARI:
        varsayilan_grup = SAYFA_GRUPLARI[0]
    grup_secenekleri = SAYFA_GRUPLARI[:-1] if ozel_sayfa else SAYFA_GRUPLARI
    sayfa_basligi = (
        ozel_sayfa["baslik"] if ozel_sayfa
        else sayfa_baslik_metnini_al(arayuz, secilen_sayfa_id)
    )
    varsayilan_sira = sayfa_ayari["sira"]
    if secilen_sayfa_id not in arayuz["sayfalar"]:
        varsayilan_sira = menu_varsayilan_siralari.get(secilen_sayfa_id, 0)

    with st.form(f"arayuz_sayfa_duzenle_{secilen_sayfa_id}"):
        yeni_menu_etiketi = st.text_input(
            "Menüde görünen sayfa adı",
            value=sayfa_ayari["etiket"] or gorunen_etiketler.get(
                secilen_sayfa_id, secilen_sayfa_id
            ),
            max_chars=100,
        )
        yeni_baslik = sayfa_basligi
        if ozel_sayfa:
            yeni_baslik = st.text_input(
                "Özel sayfanın ana başlığı",
                value=ozel_sayfa["baslik"],
                max_chars=100,
            )
        else:
            yeni_baslik = st.text_input(
                "Sayfa içerik başlığı",
                value=sayfa_basligi,
                max_chars=160,
            )
        grup_secimi = st.selectbox(
            "Menü grubu",
            grup_secenekleri,
            index=(
                grup_secenekleri.index(varsayilan_grup)
                if varsayilan_grup in grup_secenekleri else 0
            ),
        )
        yeni_sira = st.number_input(
            "Menü sırası (küçük sayı üstte)",
            min_value=0,
            max_value=999,
            value=varsayilan_sira,
            step=1,
        )
        gorunur = st.checkbox(
            "Menüde göster",
            value=sayfa_ayari["gorunur"],
            disabled=secilen_sayfa_id == "Kullanıcı Ayarları",
        )
        yeni_punto = st.slider(
            "Başlık punto boyutu",
            min_value=16,
            max_value=56,
            value=sayfa_ayari["baslik_puntosu"],
            step=1,
        )
        renk_sutunlari = st.columns(4)
        yeni_renkler = []
        renk_adlari = ("Başlangıç rengi", "Yeşil", "Turkuaz", "Mavi")
        for indeks, sutun in enumerate(renk_sutunlari):
            with sutun:
                yeni_renkler.append(
                    st.color_picker(
                        renk_adlari[indeks],
                        value=sayfa_ayari["baslik_renkleri"][indeks],
                    )
                )

        duzenlenmis_bloklar = None
        if ozel_sayfa:
            st.markdown("**Sayfa satırları**")
            st.caption("Satır eklemek için tablo altındaki + düğmesini, silmek için satır seçimini kullanın.")
            blok_tablosu = pd.DataFrame(
                ozel_sayfa["bloklar"], columns=["tur", "metin"]
            )
            duzenlenmis_bloklar = st.data_editor(
                blok_tablosu,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "tur": st.column_config.SelectboxColumn(
                        "Satır türü", options=["baslik", "metin"], required=True
                    ),
                    "metin": st.column_config.TextColumn(
                        "İçerik", width="large", max_chars=4000
                    ),
                },
                key=f"ozel_sayfa_satirlari_{secilen_sayfa_id}",
            )
        kaydet = st.form_submit_button("Sayfa ayarlarını kaydet", type="primary")

    if kaydet:
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("Sayfa ayarlarını kalıcı kaydetmek için Supabase bağlantısı gereklidir.")
        else:
            arayuz["sayfalar"][secilen_sayfa_id] = {
                "etiket": yeni_menu_etiketi.strip(),
                "baslik_metni": yeni_baslik.strip(),
                "grup": grup_secimi,
                "sira": int(yeni_sira),
                "gorunur": gorunur,
                "baslik_renkleri": yeni_renkler,
                "baslik_puntosu": yeni_punto,
            }
            if ozel_sayfa:
                ozel_sayfa["baslik"] = yeni_baslik.strip() or "Yeni Sayfa"
                ozel_sayfa["grup"] = grup_secimi
                ozel_sayfa["sira"] = int(yeni_sira)
                ozel_sayfa["gorunur"] = gorunur
                ozel_sayfa["bloklar"] = duzenlenmis_bloklar.to_dict("records")
            st.session_state.arayuz_sayfa_ayarlari = (
                arayuz_sayfa_ayarlarini_kaydet(arayuz)
            )
            st.success("Sayfa ayarları kaydedildi.")
            st.rerun()

    st.markdown("---")
    with st.form("ozel_sayfa_olustur"):
        st.markdown("**Yeni metin sayfası oluştur**")
        yeni_sayfa_adi = st.text_input(
            "Sayfa adı", max_chars=100, key="yeni_ozel_sayfa_adi"
        )
        yeni_sayfa_grubu = st.selectbox(
            "Sayfa grubu",
            SAYFA_GRUPLARI[:-1],
            key="yeni_ozel_sayfa_grubu",
        )
        olustur = st.form_submit_button("Özel sayfa ekle")
    if olustur:
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("Özel sayfa oluşturmak için kalıcı Supabase bağlantısı gereklidir.")
        elif not yeni_sayfa_adi.strip():
            st.error("Özel sayfa için bir ad girin.")
        else:
            yeni_id = f"ozel-{secrets.token_hex(8)}"
            arayuz["ozel_sayfalar"].append(
                {
                    "id": yeni_id,
                    "baslik": yeni_sayfa_adi.strip(),
                    "grup": yeni_sayfa_grubu,
                    "sira": 999,
                    "gorunur": True,
                    "bloklar": [],
                }
            )
            arayuz["sayfalar"][yeni_id] = {
                "etiket": yeni_sayfa_adi.strip(),
                "grup": yeni_sayfa_grubu,
                "sira": 999,
                "gorunur": True,
                "baslik_renkleri": list(VARSAYILAN_BASLIK_RENKLERI),
                "baslik_puntosu": 30,
            }
            st.session_state.arayuz_sayfa_ayarlari = (
                arayuz_sayfa_ayarlarini_kaydet(arayuz)
            )
            st.success("Özel sayfa oluşturuldu.")
            st.rerun()

    if arayuz["ozel_sayfalar"]:
        with st.form("ozel_sayfa_sil"):
            st.markdown("**Özel sayfa sil**")
            silinecek_id = st.selectbox(
                "Silinecek özel sayfa",
                [sayfa["id"] for sayfa in arayuz["ozel_sayfalar"]],
                format_func=lambda sayfa_id: next(
                    sayfa["baslik"]
                    for sayfa in arayuz["ozel_sayfalar"]
                    if sayfa["id"] == sayfa_id
                ),
            )
            silme_onayi = st.checkbox(
                "Bu özel sayfanın kalıcı olarak silinmesini onaylıyorum."
            )
            sil = st.form_submit_button("Özel sayfayı sil")
        if sil:
            if not silme_onayi:
                st.error("Silmek için önce onay kutusunu işaretleyin.")
            elif not SUPABASE_URL or not SUPABASE_KEY:
                st.error("Sayfa silmek için kalıcı Supabase bağlantısı gereklidir.")
            else:
                arayuz["ozel_sayfalar"] = [
                    sayfa for sayfa in arayuz["ozel_sayfalar"]
                    if sayfa["id"] != silinecek_id
                ]
                arayuz["sayfalar"].pop(silinecek_id, None)
                st.session_state.arayuz_sayfa_ayarlari = (
                    arayuz_sayfa_ayarlarini_kaydet(arayuz)
                )
                st.success("Özel sayfa silindi.")
                st.rerun()


def test_verisi_kayit_uygun_mu(kayit, kapsam, girisler):
    """Seçilen sayfanın temizliğinde korunması gereken bağlı verileri ayıklar."""
    if kapsam == "fire":
        return str(kayit.get("tur", "")).strip().casefold() == "fire/zayiat"
    if kapsam == "yemek_kullanim":
        return str(kayit.get("tur", "")).strip().casefold().startswith(
            "günlük kullanım"
        )
    if kapsam == "kullanilmayan_depo":
        return not any(g.get("depo") == kayit for g in girisler)
    if kapsam == "kullanilmayan_kategori":
        return not any(
            str(g.get("kategori", "")).strip().upper()
            == str(kayit).strip().upper()
            for g in girisler
        )
    return True


def test_verisi_kayit_etiketi_olustur(koleksiyon, kayit, indeks):
    """Kayıtları silme listesindeki kişisel hassas alanları göstermeden tanıtır."""
    if not isinstance(kayit, dict):
        return f"{indeks + 1}. {kayit}"

    alanlar = {
        "stok": ("id", "urun", "fatura_no", "tarih", "kalan"),
        "faturalar": ("id", "urun", "fatura_no", "tarih", "kalan"),
        "silinen_urunler": ("kayit_id", "urun", "tarih", "neden"),
        "fire": ("urun", "tarih", "miktar", "aciklama"),
        "yemek_arsivi": ("yemek_adi", "tarih", "kisi_sayisi", "islem_yapan"),
        "yemek_kullanim": ("urun", "tur", "tarih", "miktar"),
        "demirbaslar": ("id", "ad", "kategori", "durum"),
        "ihtiyac_sahipleri": ("id", "ad_soyad", "hane", "eklenme_tarihi"),
        "dagitimlar": ("id", "tarih", "kisi", "menu", "porsiyon"),
        "personeller": ("id", "ad_soyad", "gorev", "baslama_tarihi"),
        "personel_izinleri": (
            "id", "personel_ad", "izin_turu", "baslangic", "bitis"
        ),
    }.get(koleksiyon, ())
    detay = " | ".join(
        f"{alan}: {kayit[alan]}"
        for alan in alanlar
        if kayit.get(alan) not in (None, "")
    )
    return f"{indeks + 1}. {detay or 'Detay yok'}"


def test_verisi_sayfa_koleksiyonlari():
    return {
        "Güncel Stok Durumu": [
            ("stok", "girisler", "verileri_kaydet", "tum"),
        ],
        "Yeni Mal Alımı / Fatura Ekle": [
            ("faturalar", "girisler", "verileri_kaydet", "tum"),
        ],
        "Ürün Sil / Düzenle": [
            ("stok", "girisler", "verileri_kaydet", "tum"),
            (
                "silinen_urunler",
                "silinen_urun_loglari",
                "silinen_urun_loglarini_kaydet",
                "tum",
            ),
        ],
        "Fire / Zayiat Girişi": [
            ("fire", "kullanim_loglari", "loglari_kaydet", "fire"),
        ],
        "Depo Yönetimi": [
            ("depolar", "depolar", "depoları_kaydet", "kullanilmayan_depo"),
            (
                "kategoriler",
                "kategoriler",
                "supabase_veri_kaydet",
                "kullanilmayan_kategori",
            ),
        ],
        "Demirbaş Yönetimi": [
            ("demirbaslar", "demirbaslar", "demirbasları_kaydet", "tum"),
        ],
        "Günlük Yemek Üretimi & Maliyet Raporu": [
            (
                "yemek_arsivi",
                "yemek_uretim_arsivi",
                "yemek_uretim_arsivini_kaydet",
                "tum",
            ),
            (
                "yemek_kullanim",
                "kullanim_loglari",
                "loglari_kaydet",
                "yemek_kullanim",
            ),
        ],
        "İhtiyaç Sahibi & Yemek Dağıtım Takibi": [
            (
                "ihtiyac_sahipleri",
                "ihtiyac_sahipleri",
                "ihtiyac_sahiplerini_kaydet",
                "tum",
            ),
            ("dagitimlar", "dagitim_loglari", "dagitim_loglarini_kaydet", "tum"),
        ],
        "Personel & Çalışma Süresi Takibi": [
            ("personeller", "personeller", "personelleri_kaydet", "tum"),
            (
                "personel_izinleri",
                "personel_izinleri",
                "personel_izinlerini_kaydet",
                "tum",
            ),
        ],
    }


def test_verilerini_temizle(sayfa, secimler):
    """Yalnızca seçilen sayfa ve kayıt kimlikleri için temizliği kaydeder."""
    sayfa_koleksiyonlari = test_verisi_sayfa_koleksiyonlari()
    if sayfa not in sayfa_koleksiyonlari:
        raise ValueError("Test verisi temizliği için geçersiz sayfa seçildi.")

    silinen_sayisi = 0
    state = st.session_state
    girisler = state.get("girisler", [])
    for koleksiyon, state_key, kaydet_fonksiyonu, kapsam in sayfa_koleksiyonlari[sayfa]:
        secilen_indeksler = {
            str(indeks) for indeks in secimler.get(koleksiyon, [])
        }
        kayitlar = state.get(state_key, [])
        yeni_kayitlar = []
        degisti = False
        for indeks, kayit in enumerate(kayitlar):
            silinebilir = test_verisi_kayit_uygun_mu(kayit, kapsam, girisler)
            if str(indeks) in secilen_indeksler and silinebilir:
                silinen_sayisi += 1
                degisti = True
            else:
                yeni_kayitlar.append(kayit)
        if degisti:
            if state_key == "depolar":
                state.depolar = yeni_kayitlar
                globals()[kaydet_fonksiyonu](yeni_kayitlar)
            elif state_key == "kategoriler":
                state.kategoriler = yeni_kayitlar
                globals()[kaydet_fonksiyonu]("kategoriler_listesi", yeni_kayitlar)
            else:
                state[state_key] = yeni_kayitlar
                globals()[kaydet_fonksiyonu](yeni_kayitlar)

    return silinen_sayisi
    
def tablo_to_excel_bytes(veri_listesi, baslik_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapor"
    ws.views.sheetView[0].showGridLines = True
    header_fill = PatternFill(
        start_color="6366f1", end_color="6366f1", fill_type="solid"
    )
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="000000")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(
        left=Side(style="thin", color="e2e8f0"),
        right=Side(style="thin", color="e2e8f0"),
        top=Side(style="thin", color="e2e8f0"),
        bottom=Side(style="thin", color="e2e8f0"),
    )

    ws.cell(row=1, column=1, value=baslik_str).font = title_font
    ws.cell(
        row=2,
        column=1,
        value=f"Rapor Tarihi ve Saati: {simdi_tr_str('%Y-%m-%d %H:%M:%S')}",
    ).font = Font(name="Calibri", size=11, italic=True, color="6b7280")

    if not veri_listesi:
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        return excel_buffer.getvalue()

    headers = list(veri_listesi[0].keys())
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 5
    for item in veri_listesi:
        for col_idx, h in enumerate(headers, 1):
            val = item.get(h, "")
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            if c.data_type == "f":
                c.data_type = "s"
            c.font = regular_font
            c.border = thin_border
        row_idx += 1

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    return excel_buffer.getvalue()


def tablo_to_html_pdf_bytes(baslik, veri_listesi):
    tr_zaman = simdi_tr_str("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{html_escape(str(baslik))}</title>
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; margin: 30px; color: {text_color}; background: {bg_color}; }}
            h2 {{ color: {text_color}; margin-bottom: 5px; }}
            p {{ color: {subtext_color}; font-size: 14px; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: {card_bg}; }}
            th {{ background-color: #6366f1; color: white; padding: 12px; text-align: left; font-size: 13px; }}
            td {{ border: 1px solid {border_color}; padding: 10px 12px; font-size: 13px; color: {subtext_color}; }}
            tr:nth-child(even) {{ background-color: {sidebar_bg}; }}
        </style>
    </head>
    <body>
        <h2>{html_escape(str(baslik))}</h2>
        <p>Rapor Tarihi ve Saati: {tr_zaman}</p>
        <hr style="border: 0; border-top: 1px solid {border_color};"/>
    """
    if veri_listesi:
        headers = list(veri_listesi[0].keys())
        html += "<table><tr>"
        for h in headers:
            html += f"<th>{html_escape(str(h))}</th>"
        html += "</tr>"
        for item in veri_listesi:
            html += "<tr>"
            for h in headers:
                html += f"<td>{html_escape(str(item.get(h, '')))}</td>"
            html += "</tr>"
        html += "</table>"
    else:
        html += "<p>Kayıt bulunamadı.</p>"
    html += "</body></html>"
    return html.encode("utf-8")


def ortak_indirme_alani(excel_veri, pdf_veri, dosya_adi_koku, unique_key):
    col_sec, col_btn = st.columns([2, 1])
    with col_sec:
        format_secimi = st.selectbox(
            "İndirilecek Formatı Seçin",
            ["Excel (.xlsx)", "PDF / HTML (.html)"],
            key=f"sel_{unique_key}",
        )
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if "Excel" in format_secimi:
            st.download_button(
                label="📥 Raporu İndir",
                data=excel_veri,
                file_name=f"{dosya_adi_koku}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                key=f"btn_{unique_key}",
            )
        else:
            st.download_button(
                label="📥 Raporu İndir",
                data=pdf_veri,
                file_name=f"{dosya_adi_koku}.html",
                mime="text/html",
                key=f"btn_{unique_key}",
            )


def ozel_html_tablo_goster(veri_listesi):
    if not veri_listesi:
        st.info("Gösterilecek veri bulunmuyor.")
        return
    
    headers = list(veri_listesi[0].keys())
    html = "<table class='custom-table'><thead><tr>"
    for h in headers:
        html += f"<th>{html_escape(str(h))}</th>"
    html += "</tr></thead><tbody>"
    
    for row in veri_listesi:
        html += "<tr>"
        for h in headers:
            html += f"<td>{html_escape(str(row.get(h, '')))}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


if yonetici_modu and SUPABASE_URL and supabase_anahtar_rolu() == "anon":
    st.warning(
        "🛡️ **Güvenlik uyarısı:** Supabase için herkese açık (anon) anahtar kullanıyorsunuz. "
        "Veritabanını RLS ile kilitleyip `secrets` içinde `service_role` anahtarını kullanın "
        "(adımlar için `supabase_guvenlik.sql` dosyasına bakın)."
    )

menu = st.session_state.aktif_menu

if not yonetici_modu and menu in yasakli_menuler_listesi:
    st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    st.stop()

_sayfa_baslik_stili = arayuz_sayfa_ayari_al(
    st.session_state.arayuz_sayfa_ayarlari, menu
)
_sayfa_renkleri = _sayfa_baslik_stili["baslik_renkleri"]
_sayfa_puntosu = _sayfa_baslik_stili["baslik_puntosu"]
_sayfa_baslik_metni = sayfa_baslik_metnini_al(
    st.session_state.arayuz_sayfa_ayarlari, menu
)
st.markdown(
    f"""
    <style>
        .stApp h1, .stApp h2, .stApp h3 {{
            background-image: linear-gradient(
                90deg,
                #F4F4F5 0%,
                #10B981 35%,
                #94A3B8 68%,
                #38BDF8 100%
            ) !important;
            font-size: {_sayfa_puntosu}px !important;
        }}
        .stApp h2 {{ font-size: {_sayfa_puntosu * 0.8}px !important; }}
        .stApp h3 {{ font-size: {_sayfa_puntosu * 0.67}px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

_ozel_sayfa = next(
    (
        sayfa
        for sayfa in st.session_state.arayuz_sayfa_ayarlari["ozel_sayfalar"]
        if sayfa["id"] == menu
    ),
    None,
)
if _ozel_sayfa and not _ozel_sayfa["gorunur"]:
    st.warning("Bu özel sayfa şu anda menüde kullanıma kapalı.")
    st.stop()
    
from src.dashboard_utils import dashboard_ozet_hesapla, dashboard_operasyonel_istatistikleri
from src.dashboard_ui import dashboard_sayfasi
from src.demirbas_ui import demirbas_yonetim_sayfasi
from src.depo_yonetim_ui import depo_yonetim_sayfasi
from src.envanter_rapor_ui import kapsamli_envanter_rapor_sayfasi
from src.fire_ui import fire_zayiat_sayfasi
from src.guncel_stok_ui import guncel_stok_sayfasi
from src.gunluk_yemek_ui import gunluk_yemek_uretim_sayfasi
from src.ihtiyac_sahibi_ui import ihtiyac_sahibi_listesi_tabini_goster
from src.kalori_ui import kalori_hesaplama_sayfasi
from src.kullanici_sifre_ui import kendi_sifre_sekmesini_goster
from src.kullanici_undo_ui import kullanici_islemi_geri_al_alani
from src.kullanici_yonetim_ui import kullanici_yonetim_sekmesini_goster
from src.mal_alim_ui import mal_alimi_sayfasi
from src.manuel_rapor_ui import manuel_rapor_gonderim_alani
from src.personel_ui import personel_ve_calisma_suresi_sayfasi
from src.qr_sarfiyat_ui import qr_kod_ile_hizli_sarfiyat_sayfasi
from src.rapor_ui import kullanim_takibi_sayfasi, urun_fiyat_analizi_sayfasi
from src.stok_islemleri import fifo_miktar_dus_detayli, fifo_sarfiyat_dus, fifo_sarfiyat_dus_detayli
from src.stok_qr_ui import mevcut_urunler_qr_etiket_araci
from src.stok_rapor_utils import stok_excel_liste_olustur, stok_gorunum_listeleri_olustur
from src.toplu_dagitim_ui import toplu_yemek_dagitimi_tabini_goster
from src.toplu_sarfiyat_ui import toplu_stok_dusumu_sayfasi
from src.urun_yonetim_ui import urun_sil_duzenle_sayfasi
from src.guvenlik_durumu_ui import guvenlik_durumu_rozetlerini_goster
from src.giris_kayit_ui import giris_kayitlari_sekmesini_goster
from src.yedekleme_ui import yedekleme_sekmesini_goster
from src.rapor_utils import kapsamli_envanter_liste_olustur, urun_fiyat_analizi_olustur, benzersiz_urun_adlari
from src.personel_tarih_utils import net_calisma_gunu_hesapla


if _ozel_sayfa and not _ozel_sayfa["gorunur"]:
    st.warning("Bu özel sayfa şu anda menüde kullanıma kapalı.")
    st.stop()

if _ozel_sayfa:
    st.title(_ozel_sayfa["baslik"])
    for _blok in _ozel_sayfa["bloklar"]:
        if _blok["tur"] == "baslik":
            st.markdown(f"### {_blok['metin']}")
        elif _blok["tur"] == "metin":
            st.markdown(_blok["metin"])

elif menu in {"Kurumsal Dashboard & Özet", "Genel Bakış"}:
    dashboard_sayfasi(
        st, aktif_k_maskeleri, yonetici_modu, components,
        dashboard_ozet_hesapla, dashboard_operasyonel_istatistikleri,
        "", requests, datetime, html_escape,
    )
elif menu == "Güncel Stok Durumu":
    guncel_stok_sayfasi(
        st, misafir_modu, aktif_k_maskeleri, stok_excel_liste_olustur,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        stok_gorunum_listeleri_olustur, ozel_html_tablo_goster,
        verileri_kaydet, kritik_seviyeleri_kaydet, mevcut_urunler_qr_etiket_araci,
    )
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    mal_alimi_sayfasi(
        st, salt_okunur_modu, otomatik_yedek_al, verileri_kaydet, yeni_id_uret,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )
elif menu == "Depo Yönetimi":
    depo_yonetim_sayfasi(
        st, misafir_modu, yonetici_modu, supabase_veri_oku, otomatik_yedek_al,
        depoları_kaydet, verileri_kaydet, supabase_veri_kaydet,
        silme_onay_kutusu, ozel_html_tablo_goster,
    )
elif menu == "Demirbaş Yönetimi":
    demirbas_yonetim_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster, otomatik_yedek_al, demirbasları_kaydet,
        yeni_id_uret, silme_onay_kutusu,
    )
elif menu == "QR Kod ile Hızlı Sarfiyat":
    qr_kod_ile_hizli_sarfiyat_sayfasi(
        st, salt_okunur_modu, fifo_sarfiyat_dus, simdi_tr_str,
        verileri_kaydet, loglari_kaydet,
    )
elif menu == "Ürün Sil / Düzenle":
    urun_sil_duzenle_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu, verileri_kaydet,
        silinen_urun_loglarini_kaydet, otomatik_yedek_al, simdi_tr_str,
        silme_onay_kutusu, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster,
    )
elif menu == "Fire / Zayiat Girişi":
    fire_zayiat_sayfasi(
        st, menu, misafir_modu, salt_okunur_modu, otomatik_yedek_al,
        verileri_kaydet, loglari_kaydet, fifo_miktar_dus_detayli,
        aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster,
    )
elif menu == "Toplu Stok Düşümü & Sarfiyat":
    toplu_stok_dusumu_sayfasi(
        st, misafir_modu, salt_okunur_modu, otomatik_yedek_al,
        fifo_sarfiyat_dus_detayli, verileri_kaydet, loglari_kaydet,
        ozel_html_tablo_goster,
    )
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    gunluk_yemek_uretim_sayfasi(
        st, misafir_modu, salt_okunur_modu, aktif_k_maskeleri,
        otomatik_yedek_al, verileri_kaydet, loglari_kaydet,
        yemek_uretim_arsivini_kaydet, simdi_tr_str, tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
        urun_kalori_hesapla,
    )
elif menu == "Kalori Hesaplama Aracı":
    kalori_hesaplama_sayfasi(
        st, supabase_veri_oku, supabase_veri_kaydet, urun_kalori_hesapla,
        yeni_id_uret, simdi_tr_str, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ozel_html_tablo_goster, ortak_indirme_alani,
    )
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    tab1, tab2, tab3 = st.tabs(["👥 İhtiyaç Sahipleri", "🍲 Toplu Dağıtım", "📊 Dağıtım Sayaçları"])
    ihtiyac_sahibi_listesi_tabini_goster(
        tab1, st, aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, salt_okunur_modu, yonetim_modu, simdi_tr_str,
        yeni_id_uret, ihtiyac_sahiplerini_kaydet, yonetici_modu, silme_onay_kutusu,
        otomatik_yedek_al, ozel_html_tablo_goster,
    )
    toplu_yemek_dagitimi_tabini_goster(
        tab2, st, aktif_k_maskeleri, yonetim_modu, html_escape, simdi_tr_str,
        yeni_id_uret, dagitim_loglarini_kaydet, tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
    )
    from src.dagitim_sayac_ui import dagitim_sayac_tabini_goster
    dagitim_sayac_tabini_goster(
        tab3, st, aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster,
    )
elif menu == "Personel & Çalışma Süresi Takibi":
    personel_ve_calisma_suresi_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu, aktif_k_maskeleri,
        idleri_benzersiz_yap, otomatik_yedek_al, personelleri_kaydet,
        personel_izinlerini_kaydet, yeni_id_uret, simdi_tr_str, silme_onay_kutusu,
        net_calisma_gunu_hesapla, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster, supabase_veri_kaydet,
    )
elif menu == "Kullanım Takibi":
    kullanim_takibi_sayfasi(
        st, misafir_modu, st.session_state.get("kullanim_loglari", []),
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )
elif menu == "Kapsamlı Envanter ve Hareket Raporu":
    kapsamli_envanter_rapor_sayfasi(
        st, misafir_modu, st.session_state.get("girisler", []),
        kapsamli_envanter_liste_olustur, tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
    )
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    urun_fiyat_analizi_sayfasi(
        st, st.session_state.get("girisler", []), aktif_k_maskeleri,
        benzersiz_urun_adlari, urun_fiyat_analizi_olustur, tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
    )
elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz yalnızca **Admin** kullanıcısına aittir.")
    else:
        st.header(sayfa_baslik_metnini_al(st.session_state.arayuz_sayfa_ayarlari, menu))
        kullanici_db = st.session_state.kullanicilar
        manuel_rapor_gonderim_alani(st, manuel_rapor_maili_gonder)
        guvenlik_durumu_rozetlerini_goster(
            st, SUPABASE_URL, SUPABASE_KEY, supabase_anahtar_rolu,
            cerez_kontrol, html_escape, bosta_kalma_suresi_sn,
            kullanici_db, ESKI_VARSAYILAN_HASHLER,
        )
        sekme_k, sekme_s, sekme_l, sekme_y = st.tabs([
            "👤 Kullanıcılar", "🔑 Şifrem", "📜 Giriş Kayıtları", "💾 Yedekleme",
        ])
        kullanici_yonetim_sekmesini_goster(
            sekme_k, st, kullanici_db, ESKI_VARSAYILAN_HASHLER, gecerli_menuler,
            otomatik_yedek_al, kullanici_oturumlarini_kapat, kullanıcıları_kaydet,
            giris_logla, sifre_hashle_yeni, sifre_politika_hatasi,
        )
        kendi_sifre_sekmesini_goster(
            sekme_s, st, kullanici_db, sifre_dogrula, sifre_politika_hatasi,
            sifre_degistir,
        )
        giris_kayitlari_sekmesini_goster(
            sekme_l, st, SUPABASE_URL, SUPABASE_KEY, _supa_basliklar,
            _supabase_ham_oku, requests, tablo_to_excel_bytes,
            tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
            giris_denemesini_sifirla, giris_logla,
        )
        yedekleme_sekmesini_goster(
            sekme_y, st, SUPABASE_URL, SUPABASE_KEY, yedek_paketi_olustur,
            simdi_tr_str, giris_logla, yedek_geri_yukle, _supabase_ham_oku,
        )
        kullanici_islemi_geri_al_alani(
            st, kullanici_db, otomatik_yedek_al, kullanıcıları_kaydet, giris_logla,
        )
