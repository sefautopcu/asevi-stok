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
from src.ui_styles import login_sayfasi_stillerini_uygula
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
import logging
from src.rapor_mail import zamanlanmis_rapor_maili_gonder
from src.tema_ui import _tema_tercihini_yukle, tema_baglamini_hazirla, tema_stillerini_uygula
from src.giris_ekrani_ui import giris_ekrani_goster
from src.ui_kartlar import kurumsal_logo_baslik_goster
from src.ui_kartlar import hosgeldiniz_tarih_bari_goster, kurumsal_logo_baslik_goster
from concurrent.futures import ThreadPoolExecutor
from src.supabase_db import (
    SUPABASE_URL, SUPABASE_KEY, _supa_basliklar, supabase_anahtar_rolu,
    get_http_session, _supabase_ham_oku, _supabase_ham_oku_cached,
    _supabase_ham_oku_versiyonlu, _supabase_cas_yaz, _atomik_dict_guncelle
)
from src.sistem_yardimcilari import (
    secret_deger, simdi_tr_str, bugunun_turkce_tarihi, bellek_kullanimi_al,
    _dashboard_arka_plan_data_uri, _dashboard_arka_plan_yukleme_callback,
    _smtp_gonder_senkron
)
from src.kullanici_yonetimi import (
    varsayilan_personeller,
    ihtiyac_sahiplerini_yukle, ihtiyac_sahiplerini_kaydet,
    personelleri_yukle, personelleri_kaydet,
    eski_izinleri_tasi,
    misafir_yasaklar_varsayilan, misafir_maskeler_varsayilan,
    varsayilan_misafir_kaydi, varsayilan_kullanicilar_olustur,
    kullanıcıları_yukle, kullanıcıları_kaydet
)
from src.veri_yonetimi import (
    varsayilan_resmi_tatiller, varsayilan_depolar, varsayilan_demirbaslar, varsayilan_widgets,
    widgetlari_yukle, widgetlari_kaydet, depoları_yukle, depoları_kaydet,
    demirbasları_yukle, demirbasları_kaydet, kritik_seviyeleri_yukle, kritik_seviyeleri_kaydet,
    verileri_yukle, verileri_kaydet, loglari_yukle, loglari_kaydet,
    silinen_urun_loglarini_yukle, silinen_urun_loglarini_kaydet,
    dagitim_loglarini_yukle, dagitim_loglarini_kaydet,
    personel_izinlerini_yukle, personel_izinlerini_kaydet,
    resmi_tatilleri_yukle, yemek_uretim_arsivini_yukle, yemek_uretim_arsivini_kaydet,
    test_silme_stoku_iade_et,
    tedarikcileri_yukle, tedarikcileri_kaydet,
    arac_seferlerini_yukle, arac_seferlerini_kaydet,
    yemek_receteleri_listesini_yukle, yemek_receteleri_listesini_kaydet,
    haftalik_menu_yukle, haftalik_menu_kaydet,
    rota_teslimat_yukle, rota_teslimat_kaydet,
    denetim_izi_yukle, denetim_izi_kaydet, denetim_kaydi_ekle,
    sabah_brifingi_yukle, sabah_brifingi_kaydet, sabah_brifingi_uyarisi_olustur,
)
from src.tedarikciler_ui import tedarikci_rehberi_sayfasi
from src.arac_sefer_ui import arac_sefer_takip_sayfasi
from src.haftalik_menu_ui import haftalik_menu_planlama_sayfasi
from src.rota_teslimat_ui import rota_teslimat_sayfasi
from src.denetim_izi_ui import denetim_izi_sayfasi
from src.sabah_brifingi_ui import sabah_brifingi_sayfasi
from src.auth_session import (
    OTURUM_SURESI_SN, MAKS_HATALI_GIRIS, KILIT_SURESI_SN, IP_MAKS_HATALI_GIRIS, 
    IP_KILIT_SURESI_SN, COOKIE_ADI, OTURUM_DOGRULAMA_ARALIGI_SN,
    bosta_kalma_suresi_sn, cerez_kontrol, cerez_oku, cerez_yaz, cerez_sil,
    istemci_ip_bilgisi, giris_logla, _token_hashle, oturum_olustur, oturum_dogrula, 
    oturum_sil, kullanici_oturumlarini_kapat,
    giris_kilit_kalan, hatali_giris_kaydet, giris_denemesini_sifirla
)
from src.yemek_receteleri_ui import SAYFA_BASLIGI_YEMEK_RECETELERI, yemek_receteleri_sayfasi
SAYFA_ANAHTARI_YEMEK_RECETELERI = "yemek_receteleri"
from src.yemek_utils import (
    en_son_urun_birim_fiyati,
    fire_partisi_etiketi, fire_partisi_detayi, dashboard_skt_sayilarini_hesapla,
    qr_paket_kalanini_hesapla, qr_acik_paketleri_bul, qr_paket_secim_engeli,
    qr_kod_degerleri, yemek_sepeti_stok_hatalari, yemek_menu_alanlari,
    _malzeme_kullanim_anahtari, _menu_adlari_eslesiyor, yemek_menu_ogelerini_temizle,
    yemek_menu_ogelerini_kayittan_al, yemek_arsiv_menu_kolonlari,
    yemek_kaydi_menu_ogelerini_guncelle, yemek_malzeme_kullanim_istatistikleri,
    yemek_malzeme_kullanim_uyarilari
)

log = logging.getLogger("aziziye")
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


# Sayfa Yapılandırması: Streamlit'te İLK komut olmak zorundadır
st.set_page_config(
    page_title="Aziziye - Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide",
)

APP_VERSION = "v2.0.0"
LAST_UPDATE = "Kasım 2026"


from src.rapor_icerik import (
    _rapor_dagitim_kisi_sayisi,
    _rapor_gonderim_tamamlandi as _rapor_gonderim_tamamlandi_fn,
    _rapor_geri_al as _rapor_geri_al_fn,
    _rapor_html_metni,
    _rapor_icerigi_olustur as _rapor_icerigi_olustur_fn,
    _rapor_menu_detay_metni as _rapor_menu_detay_metni_fn,
    _rapor_sahiplen as _rapor_sahiplen_fn,
    manuel_rapor_maili_gonder as _manuel_rapor_maili_gonder_fn,
)


def _rapor_menu_detay_metni(yemek_kaydi):
    return _rapor_menu_detay_metni_fn(
        yemek_kaydi, yemek_menu_ogelerini_kayittan_al, yemek_menu_alanlari
    )


def _rapor_icerigi_olustur(rapor_baslik, rapor_tarih_str, baslangic_str, bitis_str):
    return _rapor_icerigi_olustur_fn(
        rapor_baslik,
        rapor_tarih_str,
        baslangic_str,
        bitis_str,
        supabase_ham_oku=_supabase_ham_oku,
        yemek_menu_ogelerini_kayittan_al=yemek_menu_ogelerini_kayittan_al,
        yemek_menu_alanlari=yemek_menu_alanlari,
    )


def manuel_rapor_maili_gonder(rapor_tipi="gunluk"):
    return _manuel_rapor_maili_gonder_fn(
        rapor_tipi=rapor_tipi,
        st=st,
        log=log,
        supabase_ham_oku=_supabase_ham_oku,
        smtp_gonder=_smtp_gonder_senkron,
        yemek_menu_ogelerini_kayittan_al=yemek_menu_ogelerini_kayittan_al,
        yemek_menu_alanlari=yemek_menu_alanlari,
    )


def _rapor_sahiplen(rapor_tipi, deger):
    return _rapor_sahiplen_fn(rapor_tipi, deger, _atomik_dict_guncelle)


def _rapor_geri_al(rapor_tipi, deger, claim_id):
    return _rapor_geri_al_fn(rapor_tipi, deger, claim_id, _atomik_dict_guncelle, log=log)


def _rapor_gonderim_tamamlandi(rapor_tipi, deger, claim_id):
    return _rapor_gonderim_tamamlandi_fn(
        rapor_tipi, deger, claim_id, _atomik_dict_guncelle, log=log
    )


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
YEDEK_ANAHTARLARI = [k for k in KAYIT_ESLEME if k != "kullanici_yetkileri"]

ONBELLEKSIZ_ANAHTARLAR = {
    "giris_denemeleri",
    "aktif_oturumlar",
    "kullanici_yetkileri",
    "arayuz_sayfa_ayarlari",
}


def _guvenli_dict_guncelle(kayit_id, guncelleme_fn):
    durum, mevcut = _supabase_ham_oku(kayit_id)
    if durum == "hata":
        return durum, mevcut
    mevcut_dict = mevcut if isinstance(mevcut, dict) else {}
    yeni = guncelleme_fn(dict(mevcut_dict))
    supabase_veri_kaydet(kayit_id, yeni, zorla=True)
    return "ok", yeni


_mail_havuzu = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


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
    if not SUPABASE_URL or not SUPABASE_KEY:
        return varsayilan_deger
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


def yedek_paketi_olustur():
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
    paket = yedek_paketi_olustur()
    if paket is None:
        return False
    paket["_meta"]["neden"] = str(neden)[:200]
    supabase_veri_kaydet("otomatik_yedek", paket)
    return True


def yedek_geri_yukle(paket):
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

    if not otomatik_yedek_al("Geri yükleme öncesi otomatik yedek"):
        return False, "Geri yükleme öncesi otomatik yedek alınamadı; güvenlik için iptal edildi."

    for k, v in yazilacak.items():
        supabase_veri_kaydet(k, v, zorla=True)

    for sk in set(KAYIT_ESLEME.values()):
        st.session_state.pop(sk, None)
    st.session_state.pop("_db_hash", None)

    return True, f"{len(yazilacak)} bölüm geri yüklendi."


def oturumu_baslat(kullanici_adi):
    try:
        token, bitis = oturum_olustur(kullanici_adi)
    except Exception as e:
        _veritabani_hatasi_dur(str(e))
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
    st.rerun()


def sifre_degistir(kullanici, yeni_sifre, haric_token=None, zorunlu=False):
    k = st.session_state.kullanicilar[kullanici]
    k["sifre"] = sifre_hashle_yeni(yeni_sifre)
    if zorunlu:
        k["sifre_degistirilmeli"] = True
    else:
        k.pop("sifre_degistirilmeli", None)
    kullanıcıları_kaydet(st.session_state.kullanicilar)
    kullanici_oturumlarini_kapat(kullanici, haric_token)
    giris_logla(kullanici, "şifre değiştirildi")

def oturumu_kapat():
    kullanici = st.session_state.get("aktif_kullanici", "misafir")
    token = st.session_state.get("oturum_token", "")
    giris_logla(kullanici, "çıkış")
    oturum_sil(token)
    if cerez_kontrol is not None:
        cerez_sil()
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    st.session_state.oturum_bitis = 0
    st.query_params.clear()


def oturumu_zorla_kapat(mesaj, log_durumu):
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
        
def hatali_giris_kaydet(anahtar, maks=MAKS_HATALI_GIRIS, taban_sn=KILIT_SURESI_SN):
    simdi = time.time()
    sonuc = {"kalan": maks, "kilit": False}

    def _guncelle(kayitlar):
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
        return 0, True
    return sonuc["kalan"], sonuc["kilit"]


def giris_denemesini_sifirla(anahtar=None, *ek_anahtarlar):
    if anahtar is None:
        _atomik_dict_guncelle("giris_denemeleri", lambda _: {})
        return

    anahtarlar = (anahtar,) + ek_anahtarlar
    _atomik_dict_guncelle(
        "giris_denemeleri",
        lambda kayitlar: giris_sayaclarini_sifirla(kayitlar, anahtarlar),
    )

_tema_paleti = tema_baglamini_hazirla(st, cerez_oku)
tema_stillerini_uygula(st, _tema_paleti)
border_color = _tema_paleti["border_color"]
bg_color = _tema_paleti["bg_color"]
card_bg = _tema_paleti["card_bg"]
sidebar_bg = _tema_paleti["sidebar_bg"]
text_color = _tema_paleti["text_color"]
subtext_color = _tema_paleti["subtext_color"]
accent_color = _tema_paleti["accent_color"]


def silme_onay_kutusu(anahtar):
    return st.checkbox(
        "⚠️ Bu işlemin geri alınamayacağını anlıyorum, silmeyi onaylıyorum.", key=anahtar
    )

ARAYUZ_SAYFA_AYARLARI_ID = "arayuz_sayfa_ayarlari"
SAYFA_GRUPLARI = (
    "🏠 Genel Bakış",
    "📦 Depo & Stok Yönetimi",
    "🍲 Üretim & Mutfak",
    "👥 Sosyal & İnsan Kaynakları",
    "📈 Raporlar & Arşiv",
    "⚙️ Sistem Ayarları",
)
VARSAYILAN_BASLIK_RENKLERI = ("#F4F4F5", "#10B981", "#94A3B8", "#38BDF8")
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
    "Hazır Yemek Reçeteleri": "🍲 Hazır Yemek Reçeteleri ve Porsiyon Hesabı",
    "Haftalık Menü Planlama": "📅 Haftalık Menü Planlama ve Malzeme İhtiyaç Listesi",
    "Kalori Hesaplama Aracı": "🔥 Reçete ve Kalori Analiz Merkezi",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi": (
        "👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi"
    ),
    "Sıcak Yemek Dağıtım Araç ve Sefer Takibi": (
        "🚐 Sıcak Yemek Dağıtım Araç ve Sefer Takibi"
    ),
    "Rota & Teslimat Takibi": (
        "🗺 İhtiyaç Sahibi Haneleri: Rota, Teslimat Teyidi ve Hanehalkı Güncelleme",
    ),
    "Personel & Çalışma Süresi Takibi": "👥 Personel ve Çalışma Süresi Takibi",
    "Kullanım Takibi": "📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi",
    "Denetim İzi (Audit Log)": "🕵️ Gelişmiş Denetim İzi (Audit Log) ve İşlem Geçmişi",
    "Kritik Uyarı Merkezi & Sabah Brifingi": "🌅 Kritik Uyarı Merkezi ve Günlük Sabah Brifingi",
    "Kapsamlı Envanter ve Hareket Raporu": (
        "📋 Kapsamlı Envanter ve Hareket Raporu"
    ),
    "Ürün Birim Fiyatları & Ay Analizi": (
        "💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi"
    ),
    "Tedarikçi ve Firma Rehberi": "🏢 Tedarikçi ve Firma Rehberi",
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


def arayuz_sayfa_ayarlarini_yukle(okuyucu_fn=None):
    okuyucu = okuyucu_fn or supabase_veri_oku
    ham_veri = okuyucu(ARAYUZ_SAYFA_AYARLARI_ID, {}, kritik=False)
    return arayuz_sayfa_ayarlarini_duzenle(ham_veri)


def arayuz_sayfa_ayarlarini_kaydet(veri, kaydedici_fn=None):
    kaydedici = kaydedici_fn or supabase_veri_kaydet
    temiz_veri = arayuz_sayfa_ayarlarini_duzenle(veri)
    kaydedici(ARAYUZ_SAYFA_AYARLARI_ID, temiz_veri)
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


def admin_sayfa_duzenleyici(
    st,
    gecerli_menuler,
    menu_gorunen_etiketler,
    menu_varsayilan_gruplari,
    menu_varsayilan_siralari,
    supabase_url,
    supabase_key,
    supabase_veri_kaydet,
):
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
        renk_adlari = ("Başlangıç rengi", "Yeşil", "Gri", "Mavi")
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
        if not supabase_url or not supabase_key:
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
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                arayuz, supabase_veri_kaydet
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
        if not supabase_url or not supabase_key:
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
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                arayuz, supabase_veri_kaydet
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
            elif not supabase_url or not supabase_key:
                st.error("Sayfa silmek için kalıcı Supabase bağlantısı gereklidir.")
            else:
                arayuz["ozel_sayfalar"] = [
                    sayfa for sayfa in arayuz["ozel_sayfalar"]
                    if sayfa["id"] != silinecek_id
                ]
                arayuz["sayfalar"].pop(silinecek_id, None)
                st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                    arayuz, supabase_veri_kaydet
                )
                st.success("Özel sayfa silindi.")
                st.rerun()


def test_verisi_kayit_uygun_mu(kayit, kapsam, girisler):
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
        "Tedarikçi ve Firma Rehberi": [
            ("tedarikciler", "tedarikciler", "tedarikcileri_kaydet", "tum"),
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

EK_TEST_VERISI_SAYFA_KOLEKSIYONLARI = {
    "Sıcak Yemek Dağıtım Araç ve Sefer Takibi": [
        (
            "arac_seferleri",
            "arac_seferleri",
            "arac_seferlerini_kaydet",
            "tum",
        ),
    ],
    "Hazır Yemek Reçeteleri": [
        (
            "yemek_receteleri",
            "yemek_receteleri",
            "yemek_receteleri_listesini_kaydet",
            "tum",
        ),
    ],
    "Haftalık Menü Planlama": [
        (
            "haftalik_menu",
            "haftalik_menu",
            "haftalik_menu_kaydet",
            "tum",
        ),
    ],
    "Rota & Teslimat Takibi": [
        (
            "rota_teslimat",
            "rota_teslimat",
            "rota_teslimat_kaydet",
            "tum",
        ),
    ],
    "Denetim İzi (Audit Log)": [
        (
            "denetim_izi",
            "denetim_izi",
            "denetim_izi_kaydet",
            "tum",
        ),
    ],
    "Kritik Uyarı Merkezi & Sabah Brifingi": [
        (
            "sabah_brifingi_uyarilari",
            "sabah_brifingi_uyarilari",
            "sabah_brifingi_kaydet",
            "tum",
        ),
    ],
}

_HARIC_SESSION_LISTELERI = {
    "kalori_sepeti",
    "resmi_tatiller",
    "dashboard_widgets",
}


def dinamik_test_verisi_koleksiyonlarini_al():
    """Sabit 10 sayfayı koruyarak yeni eklenen modülleri ve sayfaları otomatik listeler."""
    birlesik = dict(test_verisi_sayfa_koleksiyonlari())
    birlesik.update(EK_TEST_VERISI_SAYFA_KOLEKSIYONLARI)

    # 1) Kod Yazmadan Sayfa Düzenleyici ile eklenen özel sayfaları otomatik dahil et
    arayuz_ayarlari = st.session_state.get("arayuz_sayfa_ayarlari", {})
    for ozel in arayuz_ayarlari.get("ozel_sayfalar", []):
        baslik = str(ozel.get("baslik") or "").strip()
        sayfa_id = str(ozel.get("id") or "").strip()
        if baslik and sayfa_id and baslik not in birlesik:
            birlesik[baslik] = [
                ("bloklar", f"ozel_bloklar_{sayfa_id}", "supabase_veri_kaydet", "tum")
            ]

    # 2) Gelecekte eklenecek yeni modüllerin session_state listelerini otomatik algıla
    tanimli_state_anahtarlari = {
        state_key
        for koleksiyonlar in birlesik.values()
        for _, state_key, _, _ in koleksiyonlar
    }
    for anahtar, deger in st.session_state.items():
        if (
            anahtar.startswith("_")
            or anahtar in _HARIC_SESSION_LISTELERI
            or anahtar in tanimli_state_anahtarlari
            or not isinstance(deger, list)
        ):
            continue
        kaydet_fn_adi = f"{anahtar}_kaydet"
        if kaydet_fn_adi in globals() and callable(globals()[kaydet_fn_adi]):
            okunabilir_ad = anahtar.replace("_", " ").title()
            birlesik[okunabilir_ad] = [
                (anahtar, anahtar, kaydet_fn_adi, "tum")
            ]

    return birlesik

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

def _uretim_kayitlari_ayni_islem_mi(arsiv_kayit, log_kayit):
    if not isinstance(arsiv_kayit, dict) or not isinstance(log_kayit, dict):
        return False
    a_uid = arsiv_kayit.get("uretim_id")
    l_uid = log_kayit.get("uretim_id")
    if a_uid and l_uid:
        return str(a_uid) == str(l_uid)
    yemek_adi = str(arsiv_kayit.get("yemek_adi", "")).strip()
    tarih = str(arsiv_kayit.get("tarih", "")).strip()
    beklenen_tur = f"Günlük Kullanım ({yemek_adi})"
    return (
        bool(yemek_adi)
        and str(log_kayit.get("tur", "")).strip() == beklenen_tur
        and str(log_kayit.get("tarih", "")).startswith(tarih)
    )


def test_verilerini_temizle(sayfa, secimler):
    _dinamik_fn = globals().get("dinamik_test_verisi_koleksiyonlarini_al")
    sayfa_koleksiyonlari = (
        _dinamik_fn() if callable(_dinamik_fn) else test_verisi_sayfa_koleksiyonlari()
    )    
    if sayfa not in sayfa_koleksiyonlari:
        raise ValueError("Test verisi temizliği için geçersiz sayfa seçildi.")

    silinen_sayisi = 0
    silinen_kayitlar_toplami = []
    silinen_arsiv_kayitlari = []
    girisler = st.session_state.get("girisler", [])

    for koleksiyon, state_key, kaydet_fonksiyonu, kapsam in sayfa_koleksiyonlari[sayfa]:
        secilen_indeksler = {
            str(indeks) for indeks in secimler.get(koleksiyon, [])
        }
        kayitlar = st.session_state.get(state_key, [])
        yeni_kayitlar = []
        degisti = False
        for indeks, kayit in enumerate(kayitlar):
            silinebilir = test_verisi_kayit_uygun_mu(kayit, kapsam, girisler)
            if str(indeks) in secilen_indeksler and silinebilir:
                silinen_sayisi += 1
                degisti = True
                if koleksiyon == "yemek_arsivi":
                    silinen_arsiv_kayitlari.append(kayit)
                    silinen_kayitlar_toplami.append(kayit)
                elif koleksiyon == "yemek_kullanim":
                    if not any(
                        _uretim_kayitlari_ayni_islem_mi(a, kayit)
                        for a in silinen_arsiv_kayitlari
                    ):
                        silinen_kayitlar_toplami.append(kayit)
                elif state_key != "girisler":
                    silinen_kayitlar_toplami.append(kayit)
            else:
                yeni_kayitlar.append(kayit)
        if degisti:
            if state_key == "depolar":
                st.session_state["depolar"] = yeni_kayitlar
                depoları_kaydet(yeni_kayitlar)
            elif state_key == "kategoriler":
                st.session_state["kategoriler"] = yeni_kayitlar
                supabase_veri_kaydet("kategoriler_listesi", yeni_kayitlar)
            else:
                st.session_state[state_key] = yeni_kayitlar
                globals()[kaydet_fonksiyonu](yeni_kayitlar)

    if silinen_kayitlar_toplami and st.session_state.get("girisler"):
        from src.veri_yonetimi import test_silme_stoku_iade_et as _test_silme_stoku_iade_et

        guncel_girisler, _ = _test_silme_stoku_iade_et(
            st.session_state["girisler"], silinen_kayitlar_toplami
        )
        st.session_state["girisler"] = guncel_girisler
        verileri_kaydet(guncel_girisler)

    return silinen_sayisi


if "kalori_sepeti" not in st.session_state:
    st.session_state.kalori_sepeti = []
if "kullanicilar" not in st.session_state:
    st.session_state.kullanicilar = kullanıcıları_yukle()

if "hatali_giris_sayisi" not in st.session_state:
    st.session_state.hatali_giris_sayisi = 0
if "kilitlenme_bitis_zamani" not in st.session_state:
    st.session_state.kilitlenme_bitis_zamani = 0

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

for _eski in ("auth", "user"):
    if _eski in query_params:
        del query_params[_eski]

if "oturum_aktif" not in st.session_state:
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
for _anahtar, _deger in (("oturum_token", ""), ("oturum_bitis", 0)):
    if _anahtar not in st.session_state:
        st.session_state[_anahtar] = _deger

if not st.session_state.oturum_aktif:
    if "token" in st.query_params:
        del st.query_params["token"]

    aday_token = cerez_oku() if cerez_kontrol is not None else ""

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

if st.session_state.oturum_aktif:
    _simdi = time.time()
    if _simdi - st.session_state.get("son_etkinlik", _simdi) > bosta_kalma_suresi_sn():
        oturumu_zorla_kapat(
            "Uzun süre işlem yapılmadığı için oturumunuz güvenlik nedeniyle kapatıldı. Lütfen yeniden giriş yapın.",
            "boşta kalma nedeniyle oturum kapandı",
        )
    else:
        st.session_state["son_etkinlik"] = _simdi

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
    if "tedarikciler" not in st.session_state:
        st.session_state.tedarikciler = tedarikcileri_yukle()
    if "arac_seferleri" not in st.session_state:
        st.session_state.arac_seferleri = idleri_benzersiz_yap(arac_seferlerini_yukle(), "SFR-")
    if "haftalik_menu" not in st.session_state:
        st.session_state.haftalik_menu = idleri_benzersiz_yap(haftalik_menu_yukle(), "HMN-")
    if "rota_teslimat" not in st.session_state:
        st.session_state.rota_teslimat = idleri_benzersiz_yap(rota_teslimat_yukle(), "RTS-")
    if "denetim_izi" not in st.session_state:
        st.session_state.denetim_izi = idleri_benzersiz_yap(denetim_izi_yukle(), "DNT-")
    if "sabah_brifingi_uyarilari" not in st.session_state:
        st.session_state.sabah_brifingi_uyarilari = idleri_benzersiz_yap(sabah_brifingi_yukle(), "BRF-")
    if "kritik_seviyeler" not in st.session_state:
        st.session_state.kritik_seviyeler = kritik_seviyeleri_yukle()
    if "personel_silme_mesaji" not in st.session_state:
        st.session_state.personel_silme_mesaji = ""
    if "dagitim_silme_mesaji" not in st.session_state:
        st.session_state.dagitim_silme_mesaji = ""
    if "dashboard_widgets" not in st.session_state:
        st.session_state.dashboard_widgets = widgetlari_yukle()
    if not st.session_state.get("_otomatik_rapor_kontrol_edildi"):
        st.session_state["_otomatik_rapor_kontrol_edildi"] = True
        try:
            _simdi_tr = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul"))
        except Exception:
            _simdi_tr = datetime.datetime.now()
        _bugun_str = _simdi_tr.strftime("%Y-%m-%d")
        _resmi_tatil_mi = any(
            str(t.get("tarih", ""))[:10] == _bugun_str
            for t in st.session_state.get("resmi_tatiller", [])
        )
        zamanlanmis_rapor_maili_gonder(
            simdi=_simdi_tr,
            resmi_tatil=_resmi_tatil_mi,
            rapor_sahiplen=_rapor_sahiplen,
            rapor_geri_al=_rapor_geri_al,
            rapor_icerigi_olustur=_rapor_icerigi_olustur,
            smtp_gonder=_smtp_gonder_senkron,
            log=log,
            rapor_gonderim_tamamlandi=_rapor_gonderim_tamamlandi,
        )

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
    "Hazır Yemek Reçeteleri",
    "Haftalık Menü Planlama",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Sıcak Yemek Dağıtım Araç ve Sefer Takibi",
    "Rota & Teslimat Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
    "Denetim İzi (Audit Log)",
    "Kritik Uyarı Merkezi & Sabah Brifingi",
    "Kapsamlı Envanter ve Hareket Raporu",
    "Depo Yönetimi",
    "Demirbaş Yönetimi",
    "Tedarikçi ve Firma Rehberi",
    "Kullanıcı Ayarları",
]
_arayuz_sayfa_ayarlari = st.session_state.get(
    "arayuz_sayfa_ayarlari",
    {"sayfalar": {}, "ozel_sayfalar": []},
)
gecerli_menuler.extend(
    sayfa["id"]
    for sayfa in _arayuz_sayfa_ayarlari["ozel_sayfalar"]
    if sayfa["gorunur"]
)

if "aktif_menu" not in st.session_state:
    st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"

_query_menu = query_params.get("menu", "")
if _query_menu in gecerli_menuler:
    st.session_state.aktif_menu = _query_menu
elif st.session_state.aktif_menu not in gecerli_menuler:
    st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"

_aktif_menu_ayari = arayuz_sayfa_ayari_al(
    _arayuz_sayfa_ayarlari,
    st.session_state.aktif_menu,
)
if not _aktif_menu_ayari["gorunur"]:
    st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"
    st.query_params["menu"] = "Kurumsal Dashboard & Özet"

if "silme_mesaji" not in st.session_state:
    st.session_state.silme_mesaji = ""
if "kisi_silme_mesaji" not in st.session_state:
    st.session_state.kisi_silme_mesaji = ""


# =========================================================================
# GİRİŞ KONTROLÜ / AÇILIŞ GİRİŞ EKRANI
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
if not st.session_state.oturum_aktif:
    login_accent = accent_color
    
    # 1. CSS'leri Uygula
    login_sayfasi_stillerini_uygula(
        accent_color=accent_color,
        card_bg=card_bg,
        border_color=border_color,
        text_color=text_color,
        subtext_color=subtext_color
    )

    # 2. Ekranı Sol ve Sağ Olarak İkiye Böl
    login_layout = st.container(key="login-layout")
    login_left, login_right = login_layout.columns([1, 1], gap="large")

    # 3. SOL TARAF (Tanıtım Kartları)
    with login_left:
        st.markdown(
            """
            <section class="login-hero">
                <div class="login-eyebrow" style="display:inline-flex;align-items:center;gap:8px;">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M12 2L4 5.5V11.5C4 16.8 7.4 21.6 12 23C16.6 21.6 20 16.8 20 11.5V5.5L12 2Z" fill="rgba(16,185,129,0.22)" stroke="#10b981" stroke-width="2" stroke-linejoin="round"/><path d="M9 12.2L11 14.2L15.2 10" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    <span>AŞEVİ OTOMASYONU</span>
                </div>
                <div style="display:flex;align-items:center;gap:16px;margin:10px 0 8px 0;">
                    <div style="width:58px;height:58px;min-width:58px;border-radius:16px;background:radial-gradient(circle at 30% 25%,rgba(16,185,129,0.28),rgba(15,23,42,0.96) 75%);border:1px solid rgba(16,185,129,0.48);box-shadow:0 0 26px rgba(16,185,129,0.24),inset 0 1px 0 rgba(251,191,36,0.25);display:flex;align-items:center;justify-content:center;">
                        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                            <defs>
                                <linearGradient id="aziziyeCrestGrad" x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                                    <stop offset="0%" stop-color="#34d399"/>
                                    <stop offset="55%" stop-color="#10b981"/>
                                    <stop offset="100%" stop-color="#fbbf24"/>
                                </linearGradient>
                            </defs>
                            <path d="M16 3L6 7.2V14.8C6 21.4 10.3 27.3 16 29C21.7 27.3 26 21.4 26 14.8V7.2L16 3Z" fill="rgba(16,185,129,0.14)" stroke="url(#aziziyeCrestGrad)" stroke-width="1.8" stroke-linejoin="round"/>
                            <path d="M10.5 16.5H21.5C21.5 19.6 19 22 16 22C13 22 10.5 19.6 10.5 16.5Z" fill="rgba(251,191,36,0.24)" stroke="#fbbf24" stroke-width="1.6" stroke-linejoin="round"/>
                            <path d="M9.5 16.5H22.5" stroke="#34d399" stroke-width="1.8" stroke-linecap="round"/>
                            <path d="M13.2 13.5C13.2 12.2 14.2 11.8 14.2 10.6M16 13.2C16 11.8 17 11.4 17 10M18.8 13.5C18.8 12.2 19.8 11.8 19.8 10.6" stroke="#fde68a" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div>
                        <h1 style="margin:0;line-height:1.12;">Aziziye <span class="login-brand-accent">Aşevi</span></h1>
                        <h3 style="margin:4px 0 0 0;">Yönetim &amp; Takip Sistemi</h3>
                    </div>
                </div>
                <p>Stok girişinden yemek dağıtımına, fire takibinden personel
                yönetimine kadar tüm süreçler tek panelde. Sadece giriş yapın,
                gerisini sistem halletsin.</p>
            </section>
            <section class="login-feature-grid">
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.38);box-shadow:0 0 16px rgba(16,185,129,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                    </div>
                    <h4>Stok Yönetimi</h4>
                    <p>Fatura bazlı giriş, anlık kalan, kritik seviye uyarıları</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(251,191,36,0.14);border:1px solid rgba(251,191,36,0.38);box-shadow:0 0 16px rgba(251,191,36,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16a1 1 0 0 1 1 1v2a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6v-2a1 1 0 0 1 1-1Z"/><path d="M8 7c0-1.5 1-2 1-3.5"/><path d="M12 7c0-1.5 1-2 1-3.5"/><path d="M16 7c0-1.5 1-2 1-3.5"/></svg>
                    </div>
                    <h4>Yemek Üretimi</h4>
                    <p>Kişi başı maliyet, kalori ve porsiyon hesabı</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(244,63,94,0.14);border:1px solid rgba(244,63,94,0.38);box-shadow:0 0 16px rgba(244,63,94,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                    <h4>Fire &amp; Zayiat</h4>
                    <p>Parti bazlı fire tutarı ve neden analizi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.38);box-shadow:0 0 16px rgba(56,189,248,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3z"/><path d="M17 17h4v4h-4z"/><path d="M21 14v.01"/></svg>
                    </div>
                    <h4>QR Sarfiyat</h4>
                    <p>QR ile hızlı düşüm ve paket takibi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(168,85,247,0.14);border:1px solid rgba(168,85,247,0.38);box-shadow:0 0 16px rgba(168,85,247,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    </div>
                    <h4>Personel</h4>
                    <p>İzin, çalışma süresi ve demirbaş zimmet takibi</p>
                </article>
                <article class="login-feature-card">
                    <div class="login-feature-icon" style="width:42px;height:42px;border-radius:12px;background:rgba(52,211,153,0.14);border:1px solid rgba(52,211,153,0.38);box-shadow:0 0 16px rgba(52,211,153,0.16);display:inline-flex;align-items:center;justify-content:center;">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                    </div>
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

    # 4. SAĞ TARAF (Giriş Formu)
    with login_right.container(key="login-card"):
        st.markdown(
            """
            <div style="width:62px;height:62px;margin:0 auto 12px auto;border-radius:18px;background:radial-gradient(circle at 30% 25%,rgba(16,185,129,0.28),rgba(15,23,42,0.96) 75%);border:1px solid rgba(16,185,129,0.48);box-shadow:0 0 28px rgba(16,185,129,0.26),inset 0 1px 0 rgba(251,191,36,0.28);display:flex;align-items:center;justify-content:center;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                    <defs>
                        <linearGradient id="loginLockGrad" x1="3" y1="2" x2="21" y2="22" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stop-color="#34d399"/>
                            <stop offset="60%" stop-color="#10b981"/>
                            <stop offset="100%" stop-color="#fbbf24"/>
                        </linearGradient>
                    </defs>
                    <path d="M12 2L4 5.5V11.5C4 16.8 7.4 21.6 12 23C16.6 21.6 20 16.8 20 11.5V5.5L12 2Z" fill="rgba(16,185,129,0.16)" stroke="url(#loginLockGrad)" stroke-width="1.8" stroke-linejoin="round"/>
                    <rect x="8.8" y="11" width="6.4" height="5.2" rx="1.2" fill="rgba(251,191,36,0.22)" stroke="#fbbf24" stroke-width="1.6"/>
                    <path d="M10.2 11V9.3C10.2 8.3 11 7.5 12 7.5C13 7.5 13.8 8.3 13.8 9.3V11" stroke="#34d399" stroke-width="1.6" stroke-linecap="round"/>
                </svg>
            </div>
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
                "🔑 **İlk kurulum şifreleri** (yalnızca burada, bir kez gösterilir; şimdi not alın):\n\n" + _satirlar +
                "\n\nİlk girişte yeni şifre belirlemeniz istenecek."
            )

        simdikiekran_zaman = time.time()
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
                    placeholder="Şifrenizi giriniz...",
                    label_visibility="collapsed",
                )
                submit_btn = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")

            if submit_btn:
                if not k_adi_inp or not sifre_inp:
                    st.error("Lütfen kullanıcı adı ve şifre giriniz.")
                else:
                    # Boşlukları temizleyerek okuyalım
                    master_key = str(secret_deger("MASTER_KEY", "")).strip()
                    girilen_sifre = sifre_inp.strip()
                    
                    # GEÇİCİ DEBUG: Eğer master key okunamıyorsa bu yazı çıkar. Test bittikten sonra silebilirsin.
                    if not master_key:
                        st.warning("⚠️ Debug: MASTER_KEY secrets dosyasından okunamadı (Boş).")

                    # MASTER KEY KONTROLÜ
                    if master_key and girilen_sifre == master_key:
                        if k_adi_inp not in st.session_state.kullanicilar:
                            st.error("Admin kullanıcısı veritabanında bulunamadı.")
                            hatali_giris_kaydet(master_key, 5, 120)
                            giris_logla("master key", "hatalı kurtarma anahtarı")
                            st.error("Hatalı Kurtarma Anahtarı!")
                        else:
                            gecici_sifre = secrets.token_urlsafe(8)
                            st.session_state.kullanicilar[k_adi_inp]["sifre"] = sifre_hashle_yeni(gecici_sifre)
                            st.session_state.kullanicilar[k_adi_inp]["sifre_degistirilmeli"] = True
                            kullanıcıları_kaydet(st.session_state.kullanicilar)
                            kullanici_oturumlarini_kapat(k_adi_inp)
                            giris_denemesini_sifirla()
                            giris_logla(k_adi_inp, "şifre master key ile sıfırlandı")
                            st.success(f"**{k_adi_inp}** için geçici şifre üretildi. Lütfen bu şifreyle giriş yapın:")
                            st.code(gecici_sifre)
                            st.stop()

                    # NORMAL GİRİŞ KONTROLÜ
                    elif k_adi_inp not in st.session_state.kullanicilar:
                        st.error("Kullanıcı bulunamadı!")
                    else:
                        kullanici_verisi = st.session_state.kullanicilar[k_adi_inp]
                        
                        if sifre_dogrula(girilen_sifre, kullanici_verisi.get("sifre", "")):
                            giris_denemesini_sifirla(k_adi_inp, ip_anahtar)
                            giris_logla(k_adi_inp, "başarılı giriş")
                            oturumu_baslat(k_adi_inp)
                        else:
                            kalan, kilitlendi = hatali_giris_kaydet(k_adi_inp)
                            if ip_anahtar:
                                hatali_giris_kaydet(ip_anahtar)
                            giris_logla(k_adi_inp, "hatalı şifre")
                            
                            if kilitlendi:
                                st.error("Çok fazla hatalı deneme! Hesabınız geçici olarak kilitlendi.")
                            else:
                                st.error(f"Hatalı şifre! Kalan deneme hakkınız: {kalan}")
            # 5. MİSAFİR GİRİŞİ VE DESTEK BUTONLARI
    with login_right.container(key="login-support"):
        # Araya şık bir "veya" ayırıcı çizgisi ekleyelim
        st.markdown(
            """
            <div style='display: flex; align-items: center; margin: 15px 0 25px 0;'>
                <div style='flex: 1; height: 1px; background-color: rgba(255, 255, 255, 0.1);'></div>
                <div style='padding: 0 15px; color: #64748b; font-size: 0.85rem;'>veya</div>
                <div style='flex: 1; height: 1px; background-color: rgba(255, 255, 255, 0.1);'></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Butonları yan yana koymak için 2 sütun oluşturuyoruz
        col_misafir, col_destek = st.columns(2)

        with col_misafir:
            misafir_ayari = st.session_state.kullanicilar.get("misafir", varsayilan_misafir_kaydi())
            if misafir_ayari.get("buton_aktif", True):
                # Buton metnini kısalttık ki yan yana şık dursun
                if st.button("👁️ Misafir Girişi", use_container_width=True, type="secondary"):
                    giris_logla("misafir", "misafir girişi")
                    oturumu_baslat("misafir")

        with col_destek:
            if st.button("✉️ İletişim", use_container_width=True, type="secondary"):
                st.info("✉️ İletişim için **sefaunaltopcu@gmail.com** adresini kullanabilirsiniz.")

    # Giriş yapılmadıysa kodun devamını (ana sayfayı) durdur.
    st.stop()

# =========================================================================
# ZORUNLU ŞİFRE DEĞİŞİMİ
# =========================================================================
kurumsal_logo_baslik_goster(st, "AZİZİYE AŞEVİ", "Stok, Depo & Mutfak Yönetim Sistemi")
hosgeldiniz_tarih_bari_goster(st, bugunun_turkce_tarihi())
st.markdown("---")

kullanici_adi_goruntule = (
    st.session_state.aktif_kullanici.upper()
    if st.session_state.oturum_aktif
    else "MİSAFİR"
)
kullanici_adi_goruntule = html_escape(kullanici_adi_goruntule)

kurumsal_logo_baslik_goster(
    st.sidebar,
    "AZİZİYE AŞEVİ",
    "Stok & Mutfak Yönetim Sistemi",
)

st.sidebar.markdown(
    f"""
    <div style="background: transparent; padding: 6px 8px; display: flex; align-items: center; justify-content: space-between; margin-top: 12px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: rgba(16, 185, 129, 0.14); color: {text_color}; width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border: 1px solid {border_color};">
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
        ("Tedarikçi ve Firma Rehberi", str(len(st.session_state.tedarikciler))),
    ],
    "🍲 Üretim & Mutfak": [
        ("Günlük Yemek Üretimi & Maliyet Raporu", ""),
        ("Hazır Yemek Reçeteleri", ""),
        ("Haftalık Menü Planlama", str(len(st.session_state.haftalik_menu))),
        ("Kalori Hesaplama Aracı", ""),
    ],
    "👥 Sosyal & İnsan Kaynakları": [
        ("İhtiyaç Sahibi & Yemek Dağıtım Takibi", ""),
        ("Sıcak Yemek Dağıtım Araç ve Sefer Takibi", str(len([s for s in st.session_state.arac_seferleri if s.get("durum") == "Devam Ediyor"]))),
        ("Rota & Teslimat Takibi", str(len([k for k in st.session_state.rota_teslimat if k.get("teslim_durumu") == "Bekliyor"]))),
        ("Personel & Çalışma Süresi Takibi", str(len(st.session_state.personeller))),
    ],    
    "📈 Raporlama & Analiz": [
        ("Kullanım Takibi", ""),
        ("Denetim İzi (Audit Log)", str(len(st.session_state.denetim_izi))),
        ("Kritik Uyarı Merkezi & Sabah Brifingi", str(len([u for u in st.session_state.get("sabah_brifingi_uyarilari", []) if isinstance(u, dict) and str(u.get("durum") or "Aktif") != "Okundu"]))),
        ("Kapsamlı Envanter ve Hareket Raporu", ""),
        ("Ürün Birim Fiyatları & Ay Analizi", ""),
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
            "Sıcak Yemek Dağıtım Araç ve Sefer Takibi",
            "Personel & Çalışma Süresi Takibi",
            "Kullanım Takibi",
            "Kapsamlı Envanter ve Hareket Raporu",
            "Depo Yönetimi",
            "Demirbaş Yönetimi",
            "Tedarikçi ve Firma Rehberi",
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
                btn_label, width="stretch", type=btn_type, key=f"menu_btn_{grup_adi}_{abs(hash((grup_adi, btn_label)))}",
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
if yonetici_modu:
    ram_kullanimi = bellek_kullanimi_al()
    if ram_kullanimi > 0:
        st.sidebar.caption(f"💾 **RAM Kullanımı:** {ram_kullanimi} MB")
        if st.sidebar.button("🧹 Önbellek Temizle", key="sb_ram_clean_btn", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


def tablo_to_excel_bytes(veri_listesi, baslik_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapor"
    ws.views.sheetView[0].showGridLines = True
    header_fill = PatternFill(
        start_color="10B981", end_color="10B981", fill_type="solid"
    )
    header_font = Font(name="Calibri", size=11, bold=True, color="04110C")
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
            th {{ background-color: #10B981; color: #04110C; padding: 12px; text-align: left; font-size: 13px; }}
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
    st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"
    st.query_params["menu"] = "Kurumsal Dashboard & Özet"
    st.rerun()

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
                {_sayfa_renkleri[0]} 0%,
                {_sayfa_renkleri[1]} 35%,
                {_sayfa_renkleri[2]} 68%,
                {_sayfa_renkleri[3]} 100%
            ) !important;
            font-size: {_sayfa_puntosu}px !important;
        }}
        .stApp h2 {{ font-size: {_sayfa_puntosu * 0.8}px !important; }}
        .stApp h3 {{ font-size: {_sayfa_puntosu * 0.67}px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

from src.dashboard_utils import dashboard_ozet_hesapla, dashboard_operasyonel_istatistikleri
from src.dashboard_ui import dashboard_sayfasi
from src.demirbas_ui import demirbas_yonetim_sayfasi
from src.veri_yonetimi import tedarikcileri_kaydet, tedarikcileri_yukle
from src.tedarikciler_ui import tedarikci_rehberi_sayfasi
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

_ozel_sayfa = next(
    (s for s in _arayuz_sayfa_ayarlari.get("ozel_sayfalar", []) if s.get("id") == menu),
    None,
)

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
        tedarikcileri_kaydet=tedarikcileri_kaydet,
        simdi_tr_str=simdi_tr_str,
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
        urun_kalori_hesapla, yonetici_modu,
        yemek_malzeme_kullanim_istatistikleri,
        yemek_malzeme_kullanim_uyarilari,
        yemek_sepeti_stok_hatalari,
    )
elif menu == "Hazır Yemek Reçeteleri":
    _recete_maskeli = (
        SAYFA_ANAHTARI_YEMEK_RECETELERI in yasakli_menuler_listesi
        or "Hazır Yemek Reçeteleri" in yasakli_menuler_listesi
    )
    if _recete_maskeli and not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        yemek_receteleri_sayfasi(
            son_fiyat_saglayici=lambda urun_ad: en_son_urun_birim_fiyati(
                st.session_state.get("girisler", []), urun_ad
            ),
            kalori_saglayici=lambda urun_ad, birim_ad: urun_kalori_hesapla(
                urun_ad, 1.0, birim_ad
            ),
            stok_urunleri=[
                g.get("urun", "").strip()
                for g in st.session_state.get("girisler", [])
                if g.get("urun")
            ],
            aktif_k_maskeleri=aktif_k_maskeleri,
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

elif menu == "Tedarikçi ve Firma Rehberi":
    tedarikci_rehberi_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        tedarikcileri_kaydet,
        simdi_tr_str,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
        yonetici_modu,
    )

elif menu == "Sıcak Yemek Dağıtım Araç ve Sefer Takibi":
    arac_sefer_takip_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        yonetici_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        arac_seferlerini_kaydet,
        yeni_id_uret,
        simdi_tr_str,
        silme_onay_kutusu,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
    )

elif menu == "Haftalık Menü Planlama":
    haftalik_menu_planlama_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        yonetici_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        haftalik_menu_kaydet,
        yeni_id_uret,
        silme_onay_kutusu,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
        yemek_receteleri_yukle_fn=yemek_receteleri_listesini_yukle,        
    )

elif menu == "Rota & Teslimat Takibi":
    rota_teslimat_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        yonetici_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        rota_teslimat_kaydet,
        yeni_id_uret,
        silme_onay_kutusu,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
        ihtiyac_sahiplerini_kaydet_fn=globals().get("ihtiyac_sahiplerini_kaydet"),
    )

elif menu == "Denetim İzi (Audit Log)":
    denetim_izi_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        yonetici_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        denetim_izi_kaydet,
        yeni_id_uret,
        silme_onay_kutusu,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
        denetim_kaydi_ekle_fn=denetim_kaydi_ekle,
        aktif_kullanici=st.session_state.get("aktif_kullanici", "sistem"),
        aktif_rol=st.session_state.get("aktif_rol", ""),
    )

elif menu == "Kritik Uyarı Merkezi & Sabah Brifingi":
    sabah_brifingi_sayfasi(
        st,
        misafir_modu,
        salt_okunur_modu,
        yonetici_modu,
        aktif_k_maskeleri,
        otomatik_yedek_al,
        sabah_brifingi_kaydet,
        yeni_id_uret,
        silme_onay_kutusu,
        tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes,
        ortak_indirme_alani,
        ozel_html_tablo_goster,
        uyari_olustur_fn=sabah_brifingi_uyarisi_olustur,
        denetim_kaydi_ekle_fn=denetim_kaydi_ekle,
        denetim_izi_kaydet_fn=denetim_izi_kaydet,
        aktif_kullanici=st.session_state.get("aktif_kullanici", "sistem"),
        aktif_rol=st.session_state.get("aktif_rol", ""),
    )

elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz yalnızca **Admin** kullanıcısına aittir.")
    else:
        st.markdown(
            '<div style="display:inline-flex;align-items:center;gap:10px;background:linear-gradient(90deg,rgba(56,189,248,0.16) 0%,rgba(16,185,129,0.10) 100%);border:1px solid rgba(56,189,248,0.36);border-radius:12px;padding:7px 14px;margin-bottom:4px;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="sysGearGrad" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="#38bdf8"/><stop offset="55%" stop-color="#10b981"/><stop offset="100%" stop-color="#fbbf24"/></linearGradient></defs><circle cx="12" cy="12" r="3.2" stroke="url(#sysGearGrad)" stroke-width="2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="url(#sysGearGrad)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg><span style="font-size:0.74rem;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;color:#38bdf8;">SİSTEM YÖNETİM & GÜVENLİK MERKEZİ</span></div>',
            unsafe_allow_html=True,
        )
        st.header(sayfa_baslik_metnini_al(st.session_state.arayuz_sayfa_ayarlari, "Kullanıcı Ayarları"))
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
            giris_logla, sifre_hashle_yeni, sifre_politika_hatasi, sifre_degistir,
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

def test_temizlik_ui_goster(
    supabase_ham_oku=None,
    atomik_liste_guncelle=None,
    log=None,
    supabase_veri_oku=None,
    test_verilerini_temizle_fn=None,
):
    """Kullanıcı Ayarları altında sayfa bazlı test verisi temizleme arayüzünü gösterir."""
    temizle_fn = test_verilerini_temizle_fn or test_verilerini_temizle
    koleksiyonlar_fn = globals().get("dinamik_test_verisi_koleksiyonlarini_al") or globals().get("test_verisi_sayfa_koleksiyonlari")
    uygun_mu_fn = globals().get("test_verisi_kayit_uygun_mu")
    if not callable(koleksiyonlar_fn) or not callable(uygun_mu_fn):
        return

    sayfa_koleksiyonlari = koleksiyonlar_fn()
    if not isinstance(sayfa_koleksiyonlari, dict) or not sayfa_koleksiyonlari:
        return

    with st.expander("🧹 Test Verilerini Sayfa Sayfa Sil", expanded=False):
        sayfa_listesi = list(sayfa_koleksiyonlari.keys())
        secili_sayfa = st.selectbox(
            "Temizlenecek Sayfa",
            options=sayfa_listesi,
            key="test_temizlik_secili_sayfa",
        )
        girisler = st.session_state.get("girisler", [])
        if secili_sayfa == "Hazır Yemek Reçeteleri" and "yemek_receteleri" not in st.session_state:
            st.session_state["yemek_receteleri"] = yemek_receteleri_listesini_yukle()
        secimler = {}

        for koleksiyon, state_key, _kaydet, kapsam in sayfa_koleksiyonlari.get(            
            secili_sayfa, []
        ):
            kayitlar = st.session_state.get(state_key, [])
            uygun_secenekler = []
            for idx, kayit in enumerate(kayitlar):
                if uygun_mu_fn(kayit, kapsam, girisler):
                    etiket = (
                        kayit.get("ad")
                        or kayit.get("urun")
                        or kayit.get("yemek_adi")
                        or kayit.get("id")
                        or f"Kayıt #{idx + 1}"
                    ) if isinstance(kayit, dict) else f"Kayıt #{idx + 1}"
                    uygun_secenekler.append((str(idx), f"[{idx}] {etiket}"))

            if uygun_secenekler:
                secilen_idler = st.multiselect(
                    f"{koleksiyon} ({state_key})",
                    options=[k for k, _ in uygun_secenekler],
                    format_func=lambda k, opts=dict(uygun_secenekler): opts.get(k, k),
                    key=f"test_temizlik_secim_{secili_sayfa}_{koleksiyon}",
                )
                if secilen_idler:
                    secimler[koleksiyon] = secilen_idler

        if st.button(
            "Seçili Test Verilerini Sil",
            key=f"test_temizlik_sil_btn_{secili_sayfa}",
        ):
            try:
                silinen = temizle_fn(secili_sayfa, secimler)
                st.success(f"{silinen} adet test kaydı temizlendi.")
                st.rerun()
            except Exception as exc:
                st.error(f"Temizlik sırasında hata oluştu: {exc}")


# --- FONKSİYON ÇAĞRILARI (SADECE KULLANICI AYARLARI SAYFASINDA ÇALIŞACAK) ---
if st.session_state.aktif_menu == "Kullanıcı Ayarları":
    
    with st.expander("🧩 Kod Yazmadan Sayfa Düzenleyici", expanded=True):
        admin_sayfa_duzenleyici(
            st,
            gecerli_menuler,
            menu_gorunen_etiketler,
            menu_varsayilan_gruplari,
            menu_varsayilan_siralari,
            SUPABASE_URL,
            SUPABASE_KEY,
            supabase_veri_kaydet,
        )

    test_temizlik_ui_goster(
        supabase_ham_oku=_supabase_ham_oku,
        atomik_liste_guncelle=None,
        log=log,
        supabase_veri_oku=supabase_veri_oku,
        test_verilerini_temizle_fn=test_verilerini_temizle,
    )
# --- Aziziye Aşevi Faz 1: Yan Menü ve Sayfa Maskeleme Entegrasyonu ---
SAYFA_ANAHTARI_YEMEK_RECETELERI = "yemek_receteleri"
MENU_GRUBU_URETIM_MUTFAK = "🍲 Üretim & Mutfak"


def maskeli_sayfalari_recete_icin_hazirla(
    maskeli_sayfalar: list[str] | None = None,
) -> set[str]:
    """Mevcut sayfa maskeleme listesini bozmadan normalize edilmiş maskeli sayfa kümesi döndürür."""
    return {str(s).strip() for s in (maskeli_sayfalar or []) if str(s).strip()}


def uretim_mutfak_menulerini_hazirla(
    mevcut_alt_sayfalar: list[str] | None = None,
    maskeli_sayfalar: list[str] | None = None,
) -> list[str]:
    """'🍲 Üretim & Mutfak' altındaki sayfaları maskeleme listesine göre döndürür."""
    maskeli = maskeli_sayfalari_recete_icin_hazirla(maskeli_sayfalar)
    sayfalar = list(mevcut_alt_sayfalar or [])
    if SAYFA_BASLIGI_YEMEK_RECETELERI not in sayfalar:
        sayfalar.append(SAYFA_BASLIGI_YEMEK_RECETELERI)

    filtreli: list[str] = []
    for sayfa in sayfalar:
        if sayfa == SAYFA_BASLIGI_YEMEK_RECETELERI and (
            SAYFA_ANAHTARI_YEMEK_RECETELERI in maskeli
            or SAYFA_BASLIGI_YEMEK_RECETELERI in maskeli
        ):
            continue
        filtreli.append(sayfa)
    return filtreli


def yemek_receteleri_sayfasini_ac(
    secili_sayfa: str,
    client=None,
    bellek_depo=None,
    son_fiyat_saglayici=None,
    maskeli_sayfalar: list[str] | None = None,
) -> bool:
    """Seçili sayfa Hazır Yemek Reçeteleri ise ve maskelenmemişse render eder."""
    maskeli = maskeli_sayfalari_recete_icin_hazirla(maskeli_sayfalar)
    if secili_sayfa in (
        SAYFA_BASLIGI_YEMEK_RECETELERI,
        SAYFA_ANAHTARI_YEMEK_RECETELERI,
    ):
        if (
            SAYFA_ANAHTARI_YEMEK_RECETELERI in maskeli
            or SAYFA_BASLIGI_YEMEK_RECETELERI in maskeli
        ):
            return False
        yemek_receteleri_sayfasi(
            client=client,
            bellek_depo=bellek_depo,
            son_fiyat_saglayici=son_fiyat_saglayici,
        )
        return True
    return False
