import base64
import datetime
import hmac
import json
import os
import re
import secrets
import time
from html import escape as html_escape
from rapor_utils import (
    html_guvenli as _html_guvenli,
    rapor_verilerini_yukle_ve_filtrele,
    rapor_html_olustur,
    manuel_rapor_html_olustur,
    rapor_donemini_hesapla,
    tablo_html_olustur,
    kapsamli_envanter_liste_olustur,
    benzersiz_urun_adlari,
    urun_fiyat_analizi_olustur,
)
import difflib
import zoneinfo
import requests
from cryptography.fernet import Fernet
from rapor_export import excel_raporu_bytes, html_raporu_bytes
from performans_izleyici import bellek_kullanimi_al as _bellek_kullanimi_al_utils
from veri_temizleme import test_kayitlarini_ayikla
from rapor_mail import zamanlanmis_rapor_maili_gonder
from smtp_utils import smtp_gonder as _smtp_gonder_utils
from kalori_ui import kalori_hesaplama_sayfasi
from envanter_rapor_ui import kapsamli_envanter_rapor_sayfasi
from stok_rapor_utils import (
    stok_excel_liste_olustur,
    stok_gorunum_listeleri_olustur,
)
from demirbas_ui import demirbas_yonetim_sayfasi
from qr_sarfiyat_ui import qr_kod_ile_hizli_sarfiyat_sayfasi
from fire_ui import fire_zayiat_sayfasi
from urun_yonetim_ui import urun_sil_duzenle_sayfasi
from toplu_sarfiyat_ui import toplu_stok_dusumu_sayfasi
from guvenlik_durumu_ui import guvenlik_durumu_rozetlerini_goster
from depo_yonetim_ui import depo_yonetim_sayfasi
from guncel_stok_ui import guncel_stok_sayfasi
from mal_alim_ui import mal_alimi_sayfasi
from gunluk_yemek_ui import gunluk_yemek_uretim_sayfasi
from ihtiyac_sahibi_ui import ihtiyac_sahibi_listesi_tabini_goster
from toplu_dagitim_ui import toplu_yemek_dagitimi_tabini_goster
from dagitim_sayac_ui import dagitim_sayac_tabini_goster
from personel_ui import personel_ve_calisma_suresi_sayfasi
from manuel_rapor_ui import manuel_rapor_gonderim_alani
from kullanici_undo_ui import kullanici_islemi_geri_al_alani
from kullanici_sifre_ui import kendi_sifre_sekmesini_goster
from giris_kayit_ui import giris_kayitlari_sekmesini_goster
from yedekleme_ui import yedekleme_sekmesini_goster
from kullanici_yonetim_ui import kullanici_yonetim_sekmesini_goster
from dashboard_ui import dashboard_sayfasi
from stok_islemleri import (
    fifo_sarfiyat_dus,
    fifo_sarfiyat_dus_detayli,
    fifo_miktar_dus_detayli,
)
from supabase_utils import (
    supabase_basliklar as _supabase_basliklar,
    supabase_anahtar_rolu as _supabase_anahtar_rolu,
)
from supabase_store import (
    supabase_atomik_dict_guncelle as _supabase_store_atomik_dict_guncelle,
    supabase_veri_kaydet as _supabase_store_veri_kaydet,
    supabase_veri_oku as _supabase_store_veri_oku,
    supabase_cas_yaz as _supabase_store_cas_yaz,
    supabase_ham_oku as _supabase_store_ham_oku,
    supabase_ham_oku_versiyonlu as _supabase_store_ham_oku_versiyonlu,
)
from besin_hesaplama import urun_kalori_hesapla
from stok_qr_ui import mevcut_urunler_qr_etiket_araci
from qr_utils import qr_png_bytesi_olustur
from personel_tarih_utils import net_calisma_gunu_hesapla, bugunun_turkce_tarihi
from giris_guvenlik import (
    giris_kilit_kalan as _giris_kilit_kalan_utils,
    hatali_giris_kaydet as _hatali_giris_kaydet_utils,
)
from yedek_utils import (
    yedek_paketi_olustur as _yedek_paketi_olustur,
    yedek_geri_yukle as _yedek_geri_yukle,
)
from personel_izin_migrasyonu import eski_izinleri_donustur
from rapor_ui import (
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    kullanim_takibi_sayfasi,
    urun_fiyat_analizi_sayfasi,
)
from kullanicilar_utils import kullanicilari_normallestir
from dashboard_utils import dashboard_ozet_hesapla, dashboard_operasyonel_istatistikleri
from kullanici_kurulumu import varsayilan_kullanicilari_olustur
from istek_guvenlik import istemci_ip_ayikla
from giris_loglari import giris_logu_kaydet as _giris_logu_kaydet
from zaman_utils import simdi_tr_str
from oturum_cerezleri import (
    cerez_oku as _cerez_oku_utils,
    cerez_yaz as _cerez_yaz_utils,
    cerez_sil as _cerez_sil_utils,
)
from oturum_utils import (
    bosta_kalma_suresi_sn as _bosta_kalma_suresi_sn_utils,
    token_hashle as _token_hashle_utils,
    oturum_olustur as _oturum_olustur_utils,
    oturum_dogrula as _oturum_dogrula_utils,
    oturum_sil as _oturum_sil_utils,
    kullanici_oturumlarini_kapat as _kullanici_oturumlarini_kapat_utils,
)
from varsayilanlar import (
    varsayilan_personeller,
    varsayilan_resmi_tatiller,
    varsayilan_depolar,
    varsayilan_demirbaslar,
    misafir_yasaklar_varsayilan,
    misafir_maskeler_varsayilan,
    varsayilan_misafir_kaydi,
    varsayilan_widgets,
)
from veri_donusumleri import (
    ihtiyac_sahiplerini_coz,
    ihtiyac_sahiplerini_sifrele,
    personelleri_coz,
    personelleri_sifrele,
)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import holidays
import smtplib
import logging                                    # YENİ
from concurrent.futures import ThreadPoolExecutor # YENİ

log = logging.getLogger("aziziye")
# Log formatını ayarla (tarih, saat, seviye ve mesaj)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

from cekirdek import (
    SifrelemeHatasi,
    ESKI_VARSAYILAN_HASHLER,
    _veri_hash,
    fernet_motoru,
    giris_sayaclarini_sifirla,
    idleri_benzersiz_yap,
    metni_coz,
    metni_sifrele,
    sifre_dogrula,
    sifre_hashle,
    sifre_hashle_yeni,
    sifre_politika_hatasi,
    sifre_yukseltilmeli_mi,
    yeni_id_uret,
)

# Sayfa Yapılandırması: Streamlit'te İLK komut olmak zorundadır
# (kenar çubuğu, önbellek vb. komutlardan önce çağrılmalıdır).
st.set_page_config(
    page_title="Aziziye - Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide",
)

APP_VERSION = "v2.0.0"
LAST_UPDATE = "Kasım 2026"

def bellek_kullanimi_al():
    """Compatibility wrapper for the process memory metric helper."""
    return _bellek_kullanimi_al_utils()
        
def manuel_rapor_maili_gonder(rapor_tipi="gunluk"):
    """Buton ile tetiklendiğinde çalışır, tarih/saat kontrolünü atlar ve veritabanına kayıt atmaz."""
    simdi = datetime.datetime.now()
    bugun = simdi.date()
    
    baslangic_tarih, bitis_tarih, rapor_baslik, rapor_tarih_str = (
        rapor_donemini_hesapla(bugun, rapor_tipi, manuel=True)
    )

    baslangic_str = baslangic_tarih.strftime("%Y-%m-%d")
    bitis_str = bitis_tarih.strftime("%Y-%m-%d")
    
    secimler = rapor_verilerini_yukle_ve_filtrele(
        _supabase_ham_oku, baslangic_str, bitis_str
    )
    secilen_girisler = secimler["girisler"]
    secilen_fireler = secimler["fireler"]
    secilen_silinenler = secimler["silinenler"]
    secilen_yemekler = secimler["yemekler"]
    secilen_izinler = secimler["izinler"]

    html = manuel_rapor_html_olustur(
        rapor_baslik, rapor_tarih_str, secilen_girisler, secilen_fireler,
        secilen_silinenler, secilen_yemekler, secilen_izinler,
    )

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
    """K4: Aynı dönem için yalnızca BİR tetiklemenin geçmesini atomik olarak garanti eder."""
    sonuc = {"sahiplendi": False}
    def _mutate(mevcut):
        if mevcut.get(rapor_tipi) == deger:
            sonuc["sahiplendi"] = False
            return mevcut
        mevcut[rapor_tipi] = deger
        sonuc["sahiplendi"] = True
        return mevcut
    durum, _ = _atomik_dict_guncelle("mail_loglari", _mutate)
    return durum == "ok" and sonuc["sahiplendi"]

def _rapor_geri_al(rapor_tipi, deger):
    """Gönderim başarısızsa sahiplenmeyi bırak → bir sonraki tetikleme yeniden denesin."""
    def _mutate(mevcut):
        if mevcut.get(rapor_tipi) == deger:
            mevcut.pop(rapor_tipi, None)
        return mevcut
    _atomik_dict_guncelle("mail_loglari", _mutate)

def _rapor_icerigi_olustur(rapor_baslik, rapor_tarih_str, baslangic_str, bitis_str):
    """İki fonksiyondaki neredeyse birebir aynı HTML şablonunu birleştirir."""
    secimler = rapor_verilerini_yukle_ve_filtrele(
        _supabase_ham_oku, baslangic_str, bitis_str
    )
    secilen_girisler = secimler["girisler"]
    secilen_fireler = secimler["fireler"]
    secilen_silinenler = secimler["silinenler"]
    secilen_yemekler = secimler["yemekler"]
    secilen_izinler = secimler["izinler"]

    return rapor_html_olustur(
        rapor_baslik,
        rapor_tarih_str,
        secilen_girisler,
        secilen_fireler,
        secilen_silinenler,
        secilen_yemekler,
        secilen_izinler,
    )

def gunluk_rapor_maili_gonder():
    """Keep app integrations here; delegate scheduled decisions to rapor_mail."""
    simdi = datetime.datetime.now()
    try:
        resmi_tatil = simdi.date() in holidays.Turkey()
    except Exception:
        resmi_tatil = False

    return zamanlanmis_rapor_maili_gonder(
        simdi=simdi,
        resmi_tatil=resmi_tatil,
        rapor_sahiplen=_rapor_sahiplen,
        rapor_geri_al=_rapor_geri_al,
        rapor_icerigi_olustur=_rapor_icerigi_olustur,
        smtp_gonder=_smtp_gonder_senkron,
        log=log,
    )


# Şifreleme Anahtarı Kontrolü
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
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

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
ONBELLEKSIZ_ANAHTARLAR = {"giris_denemeleri", "aktif_oturumlar", "kullanici_yetkileri"}

def _supa_basliklar(ekstra=None):
    return _supabase_basliklar(SUPABASE_KEY, ekstra)


def supabase_anahtar_rolu():
    """Kullanılan Supabase anahtarının rolünü döndürür."""
    return _supabase_anahtar_rolu(SUPABASE_KEY)


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
    return _supabase_store_ham_oku(
        SUPABASE_URL, kayit_id, _supa_basliklar, get_http_session
    )


@st.cache_data(ttl=60, show_spinner=False)
def _supabase_ham_oku_cached(kayit_id):
    """Veritabanı okumalarını 60 saniye boyunca bellek seviyesinde hızlı tutar.
    Güvenlik açısından kritik anahtarlar bu cache'i KULLANMAZ; bkz. ONBELLEKSIZ_ANAHTARLAR."""
    return _supabase_ham_oku(kayit_id)
    
# =========================================================================
# ATOMİK YAZMA + ARKA PLAN MAIL  (K1, K3, K4)
# =========================================================================
_mail_havuzu = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


def _smtp_gonder_senkron(konu, html_icerik):
    """Preserve the app-facing SMTP API while delegating transport details."""
    return _smtp_gonder_utils(konu, html_icerik, st.secrets, smtplib.SMTP)


def _supabase_ham_oku_versiyonlu(kayit_id):
    """('ok', veri, versiyon) | ('yok', None, None) | ('hata', mesaj, None).
    CAS için versiyon ile birlikte okur. CACHE KULLANMAZ."""
    return _supabase_store_ham_oku_versiyonlu(
        SUPABASE_URL, kayit_id, _supa_basliklar, get_http_session
    )


def _supabase_cas_yaz(kayit_id, beklenen_versiyon, yeni_veri):
    """Compare-and-swap. (basarili, guncel_versiyon_veya_hata)."""
    return _supabase_store_cas_yaz(
        SUPABASE_URL,
        kayit_id,
        beklenen_versiyon,
        yeni_veri,
        _supa_basliklar,
        get_http_session,
    )


def _atomik_dict_guncelle(kayit_id, guncelleme_fn, max_retry=8):
    """K3 CAS ile atomik güncelleme; Streamlit bağımlılıkları callback olarak aktarılır."""
    return _supabase_store_atomik_dict_guncelle(
        kayit_id,
        guncelleme_fn,
        _supabase_ham_oku_versiyonlu,
        _supabase_cas_yaz,
        max_retry=max_retry,
        uyku=time.sleep,
    )

def _taban_hashler():
    if "_db_hash" not in st.session_state:
        st.session_state["_db_hash"] = {}
    return st.session_state["_db_hash"]


def _veritabani_hatasi_dur(mesaj):
    st.error(
        f"⚠️ **Veritabanı hatası:** {mesaj}. Verilerinizin bozulmaması için işlem durduruldu. "
        "Bağlantıyı/ayarları kontrol edip sayfayı yenileyin."
    )
    st.stop()


def supabase_veri_oku(kayit_id, varsayilan_deger, kritik=True):
    """Read via cache policy while preserving session baseline and fail-safe behavior."""
    return _supabase_store_veri_oku(
        kayit_id,
        varsayilan_deger,
        kritik,
        SUPABASE_URL,
        SUPABASE_KEY,
        ONBELLEKSIZ_ANAHTARLAR,
        KAYIT_ESLEME,
        _supabase_ham_oku,
        _supabase_ham_oku_cached,
        _taban_hashler,
        _veri_hash,
        _veritabani_hatasi_dur,
    )


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
    """Write data through the store while preserving session conflict checks."""
    return _supabase_store_veri_kaydet(
        kayit_id,
        veri_objesi,
        zorla,
        SUPABASE_URL,
        SUPABASE_KEY,
        KAYIT_ESLEME,
        _supabase_ham_oku,
        _taban_hashler,
        _veri_hash,
        _supa_basliklar,
        requests.post,
        _veritabani_hatasi_dur,
        _cakisma_ve_dur,
    )
    

# =========================================================================
# YEDEKLEME / GERİ YÜKLEME
# =========================================================================
def yedek_paketi_olustur():
    """Veritabanındaki ham veriyi (şifreli alanlar şifreli kalır) paketler. Hata olursa None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return _yedek_paketi_olustur(
        SUPABASE_URL,
        SUPABASE_KEY,
        YEDEK_ANAHTARLARI,
        _supabase_ham_oku,
        simdi_tr_str("%Y-%m-%d %H:%M:%S"),
        st.session_state.get("aktif_kullanici", ""),
    )


def otomatik_yedek_al(neden):
    """Silme gibi geri dönüşsüz işlemlerden önce tek seviyelik otomatik yedek alır."""
    paket = yedek_paketi_olustur()
    if paket is None:
        return False
    paket["_meta"]["neden"] = str(neden)[:200]
    supabase_veri_kaydet("otomatik_yedek", paket)
    return True


def yedek_geri_yukle(paket):
    """Yedek paketini güvenlik yedeği aldıktan sonra geri yükler."""
    def bellekteki_veriyi_temizle():
        for state_key in set(KAYIT_ESLEME.values()):
            st.session_state.pop(state_key, None)
        st.session_state.pop("_db_hash", None)

    return _yedek_geri_yukle(
        paket,
        SUPABASE_URL,
        SUPABASE_KEY,
        YEDEK_ANAHTARLARI,
        otomatik_yedek_al,
        lambda key, value: supabase_veri_kaydet(key, value, zorla=True),
        bellekteki_veriyi_temizle,
    )
    

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
    """Read the configured idle timeout and delegate parsing/clamping."""
    return _bosta_kalma_suresi_sn_utils(
        st.secrets.get("BOSTA_KALMA_DAKIKA", 30)
    )

# Çerez desteği: `extra-streamlit-components` kütüphanesi ile stabil çerez yönetimi.
try:
    import extra_streamlit_components as stx
    # Streamlit widget uyarısını önlemek için doğrudan ana kodda başlatıyoruz.
    cerez_kontrol = stx.CookieManager(key="aziziye_cerez")
except Exception:
    cerez_kontrol = None

def cerez_oku(anahtar=COOKIE_ADI):
    return _cerez_oku_utils(anahtar, st, cerez_kontrol)


def cerez_yaz(deger, anahtar=COOKIE_ADI, max_age=OTURUM_SURESI_SN):
    return _cerez_yaz_utils(deger, anahtar, max_age, cerez_kontrol, log)


def cerez_sil(anahtar=COOKIE_ADI):
    return _cerez_sil_utils(anahtar, cerez_kontrol)

def istemci_ip_bilgisi():
    """(kilit IP, tam X-Forwarded-For); rate-limit için sağdaki proxy adresini kullanır."""
    try:
        return istemci_ip_ayikla(st.context.headers)
    except Exception:
        return "bilinmiyor", ""


def giris_logla(kullanici, durum):
    """Giriş/çıkış/yönetim olaylarını audit tablosuna kaydeder; şifre kaydetmez."""
    return _giris_logu_kaydet(
        SUPABASE_URL,
        SUPABASE_KEY,
        kullanici,
        durum,
        istemci_ip_bilgisi,
        _supa_basliklar,
        requests.post,
        log,
    )


def _token_hashle(token):
    return _token_hashle_utils(token)


def oturum_olustur(kullanici_adi):
    return _oturum_olustur_utils(
        kullanici_adi,
        OTURUM_SURESI_SN,
        _atomik_dict_guncelle,
        _veritabani_hatasi_dur,
        simdi_fn=time.time,
        token_fn=secrets.token_urlsafe,
    )


def oturum_dogrula(token):
    return _oturum_dogrula_utils(token, supabase_veri_oku, time.time)


def oturum_sil(token):
    return _oturum_sil_utils(token, _atomik_dict_guncelle)


def kullanici_oturumlarini_kapat(kullanici, haric_token=None):
    return _kullanici_oturumlarini_kapat_utils(
        kullanici, _atomik_dict_guncelle, haric_token
    )

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
    return _giris_kilit_kalan_utils(kayitlar, anahtar, time.time)


def hatali_giris_kaydet(anahtar, maks=MAKS_HATALI_GIRIS, taban_sn=KILIT_SURESI_SN):
    """(kalan_hak, kilitlendi_mi); kilit süresi her ardışık kilitte ikiye katlanır."""
    return _hatali_giris_kaydet_utils(
        anahtar, _atomik_dict_guncelle, maks, taban_sn, time.time
    )


def giris_denemesini_sifirla(anahtar=None):
    """Bir veya birden fazla anahtarı, ya da anahtar yoksa tümünü temizler."""
    if anahtar is None:
        return giris_sayaclarini_sifirla(None, _atomik_dict_guncelle)
    return giris_sayaclarini_sifirla(anahtar, _atomik_dict_guncelle)


# =========================================================
# SEFA AŞEVİ - PURE DARK LIQUID GLASS TEMA
# =========================================================

# Kodun alt kısımlarındaki KeyError ve NameError hatalarını engelleyen değişkenler:
# Tema state'i: önce çerezden oku, yoksa varsayılan "Dark"
if "tema" not in st.session_state:
    _cerez_tema = ""
    try:
        # cerez_oku fonksiyonu bu noktadan sonra tanımlanıyor, geçici olarak st.context kullan
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            _cerez_tema = st.context.cookies.get("aziziye_tema", "")
    except Exception:
        pass
    if _cerez_tema in ("Dark", "Arctic"):
        st.session_state.tema = _cerez_tema
    else:
        st.session_state.tema = "Dark"

if st.session_state.tema == "Arctic":
    border_color = "#C7D3DD"
    bg_color = "#EDF3F7"
    card_bg = "#FFFFFF"
    sidebar_bg = "#E4EDF3"
    text_color = "#102235"
    subtext_color = "#52697A"
    input_bg = "#FFFFFF"
    popover_bg = "#FFFFFF"
else:
    border_color = "#1A3A32"
    bg_color = "#040711"
    card_bg = "rgba(10, 15, 29, 0.75)"
    sidebar_bg = "#060A14"
    text_color = "#f4f4f5"
    subtext_color = "#94a3b8"
    input_bg = "#0A0F1D"
    popover_bg = "#0b1329"

# STİL ENJEKSİYONU
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Ana Arka Plan ve Tipografi */
    .stApp {
        background-color: {bg_color} !important;
        background-image: {"radial-gradient(circle at 10% 20%, rgba(16,185,129,.12) 0%, transparent 45%), radial-gradient(circle at 90% 80%, rgba(99,102,241,.12) 0%, transparent 45%)" if st.session_state.tema == "Dark" else "linear-gradient(135deg, #f8fafc 0%, #eef4f8 100%)"} !important;
        background-attachment: fixed !important;
        color: {text_color} !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Sol Menü (Sidebar) Cam Görünümü */
    section[data-testid="stSidebar"] {
        background: {sidebar_bg} !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid {border_color} !important;
    }

    /* Sol Menü Butonları */
    section[data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        color: {"#94a3b8" if st.session_state.tema == "Dark" else "#cbd5e1"} !important;
        border: 1px solid transparent !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        padding: 10px 16px !important;
        transition: all 0.25s ease !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(16, 185, 129, 0.12) !important;
        color: {"#f4f4f5" if st.session_state.tema == "Dark" else "#ffffff"} !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35) !important;
        transform: translateX(4px) !important;
    }

    /* Metrik Kartları ve Formlar (Neon Cam Efekti) */
    div[data-testid="stMetric"], 
    div[data-testid="stForm"], 
    div[data-testid="stExpander"] {
        background: {card_bg} !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid {border_color} !important;
        border-radius: 18px !important;
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35) !important;
    }

    /* Girdi Kutuları ve İnputlar (Koyu Mavi Zemin) */
    input, 
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div {
        background-color: {input_bg} !important;
        color: {text_color} !important;
        -webkit-text-fill-color: {text_color} !important;
        border-radius: 12px !important;
        border: 1px solid {border_color} !important;
    }
    input::placeholder,
    textarea::placeholder,
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {{
        color: {subtext_color} !important;
        -webkit-text-fill-color: {subtext_color} !important;
        opacity: 1 !important;
    }}

    /* Native widget metinleri ve açılır menüler */
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stCaptionContainer"],
    .stMarkdown p,
    .stMarkdown li,
    .stMarkdown td,
    .stMarkdown th,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {{
        color: {text_color} !important;
    }}
    ul[role="listbox"],
    div[role="listbox"],
    div[data-baseweb="menu"],
    div[data-baseweb="popover"] {{
        background: {popover_bg} !important;
        color: {text_color} !important;
        border-color: {border_color} !important;
    }}
    li[role="option"],
    div[role="option"] {{
        background: {popover_bg} !important;
        color: {text_color} !important;
    }}
    li[role="option"]:hover,
    div[role="option"]:hover,
    li[aria-selected="true"],
    div[aria-selected="true"] {{
        background: {sidebar_bg} !important;
        color: {"#102235" if st.session_state.tema == "Arctic" else "#10b981"} !important;
    }}

    /* Birincil Yeşil Butonlar */
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4) !important;
    }

    /* İkincil Butonlar */
    button[data-testid="baseButton-secondary"], div.stButton > button {
        background: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
    }

    /* HTML Özel Tablo */
    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 15px 0;
        background: {card_bg};
        backdrop-filter: blur(16px);
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {border_color};
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35);
    }
    .custom-table th {
        background: {"rgba(6, 10, 20, 0.85)" if st.session_state.tema == "Dark" else "#e2e8f0"} !important;
        color: {"#f4f4f5" if st.session_state.tema == "Dark" else "#0f172a"} !important;
        padding: 14px 18px;
        font-size: 13px !important;
        font-weight: 700;
        border-bottom: 1px solid {border_color};
    }
    .custom-table td {
        padding: 14px 18px;
        color: {subtext_color} !important;
        font-size: 13px !important;
        border-bottom: 1px solid {border_color};
    }
</style>
""", unsafe_allow_html=True)

if st.session_state.get("tema") == "Arctic":
    st.markdown("""
    <style>
        .stApp { background: #f8fafc !important; color: #0f172a !important; }
        section[data-testid="stSidebar"] { background: rgba(6, 10, 20, 0.95) !important; border-color: rgba(16, 185, 129, 0.35) !important; }
        .stApp, .stApp p, .stApp label { color: #0f172a !important; }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] { background: #0a0f1d !important; color: #f4f4f5 !important; }
        .stApp h1, .stApp h2, .stApp h3 {
            background-image: none !important;
            -webkit-background-clip: border-box !important;
            -webkit-text-fill-color: #0f172a !important;
            color: #0f172a !important;
        }
        div[data-testid="stMetric"], div[data-testid="stForm"],
        div[data-testid="stExpander"], button[data-testid="baseButton-secondary"],
        div.stButton > button { background: #ffffff !important; color: #0f172a !important; border-color: #cbd5e1 !important; }
        input, div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
            background-color: #ffffff !important; color: #0f172a !important; border-color: #94a3b8 !important;
        }
        .custom-table { background: #ffffff !important; }
        .custom-table th { background: #e2e8f0 !important; color: #0f172a !important; }
        .custom-table td { color: #334155 !important; }
    </style>
    """, unsafe_allow_html=True)

def silme_onay_kutusu(anahtar):
    return st.checkbox(
        "⚠️ Bu işlemin geri alınamayacağını anlıyorum, silmeyi onaylıyorum.", key=anahtar
    )


def varsayilan_kullanicilar_olustur():
    """İlk kurulumda kullanıcıları oluşturur. Kodda sabit şifre YOKTUR."""
    kayit, uretilenler = varsayilan_kullanicilari_olustur(
        lambda key: st.secrets.get(key, ""),
        sifre_hashle_yeni,
        sifre_politika_hatasi,
        varsayilan_misafir_kaydi,
    )
    if uretilenler:
        st.session_state["ilk_kurulum_sifreleri"] = uretilenler
    return kayit

def arayuz_sayfa_ayarlarini_yukle():
    return supabase_veri_oku("arayuz_sayfa_ayarlari", {"sayfalar": {}, "ozel_sayfalar": []})


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
    data = supabase_veri_oku("kullanici_yetkileri", None)
    ilk_kurulum = (not isinstance(data, dict)) or (not data)
    if ilk_kurulum:
        data = varsayilan_kullanicilar_olustur()
    data = kullanicilari_normallestir(
        data,
        misafir_yasaklar_varsayilan,
        misafir_maskeler_varsayilan,
        varsayilan_misafir_kaydi(),
        sifre_hashle_yeni,
    )

    if ilk_kurulum:
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
    return ihtiyac_sahiplerini_coz(ham_veri, metni_coz)


def ihtiyac_sahiplerini_kaydet(veri_listesi):
    try:
        sifrelenmis_liste = ihtiyac_sahiplerini_sifrele(veri_listesi, metni_sifrele)
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
    return personelleri_coz(ham_veri, metni_coz)


def personelleri_kaydet(veri_listesi):
    try:
        sifrelenmis_p = personelleri_sifrele(veri_listesi, metni_sifrele)
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


def eski_izinleri_tasi():
    """Move embedded legacy leaves to the new list, writing destination before source."""
    personeller = st.session_state.personeller
    mevcut = st.session_state.personel_izinleri
    degisti = eski_izinleri_donustur(
        personeller,
        mevcut,
        yeni_id_uret,
        lambda: simdi_tr_str("%Y-%m-%d %H:%M"),
    )
    if degisti:
        # ÖNEMLİ SIRA: önce yeni listeyi yaz, sonra eski kayıtları boşalt.
        # Ters sıra yapılırsa ve arada bir hata olursa veri kaybı yaşanır.
        personel_izinlerini_kaydet(mevcut)
        personelleri_kaydet(personeller)


def resmi_tatilleri_yukle():
    return supabase_veri_oku("resmi_tatiller", varsayilan_resmi_tatiller)


def yemek_uretim_arsivini_yukle():
    return supabase_veri_oku("yemek_uretim_arsivi", [])


def yemek_uretim_arsivini_kaydet(veri):
    supabase_veri_kaydet("yemek_uretim_arsivi", veri)


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
if "kalori_sepeti" not in st.session_state:
    st.session_state.kalori_sepeti = []
if "personel_silme_mesaji" not in st.session_state:
    st.session_state.personel_silme_mesaji = ""
if "dagitim_silme_mesaji" not in st.session_state:
    st.session_state.dagitim_silme_mesaji = ""
if "kullanicilar" not in st.session_state:
    st.session_state.kullanicilar = kullanıcıları_yukle()
if "dashboard_widgets" not in st.session_state:
    st.session_state.dashboard_widgets = widgetlari_yukle()
if "arayuz_sayfa_ayarlari" not in st.session_state:
    st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_yukle()

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

ARAYUZ_SAYFA_AYARLARI_ID = "arayuz_sayfa_ayarlari"
SAYFA_GRUPLARI = (
    "🏠 Genel Bakış", "📦 Depo & Stok Yönetimi", "🍲 Üretim & Mutfak",
    "👥 Sosyal & İnsan Kaynakları", "📈 Raporlar & Arşiv", "⚙️ Sistem Ayarları",
)
VARSAYILAN_BASLIK_RENKLERI = ("#ffffff", "#10b981", "#14b8a6", "#38bdf8")


def _arayuz_renk_kodu_gecerli_mi(deger):
    return isinstance(deger, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", deger) is not None


def _arayuz_sayisini_sinirla(deger, varsayilan, en_az, en_cok):
    try:
        sayi = int(deger)
    except (TypeError, ValueError):
        sayi = varsayilan
    return max(en_az, min(sayi, en_cok))


def arayuz_sayfa_ayarlarini_duzenle(veri):
    """Keep only bounded menu, heading, and plain-text custom-page settings."""
    veri = veri if isinstance(veri, dict) else {}
    sayfalar = {}
    ham_sayfalar = veri.get("sayfalar", {})
    if isinstance(ham_sayfalar, dict):
        for sayfa_id, ayar in ham_sayfalar.items():
            if not isinstance(sayfa_id, str) or not isinstance(ayar, dict):
                continue
            renkler = ayar.get("baslik_renkleri", VARSAYILAN_BASLIK_RENKLERI)
            if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
                renkler = VARSAYILAN_BASLIK_RENKLERI
            sayfalar[sayfa_id] = {
                "etiket": str(ayar.get("etiket", ""))[:100],
                "baslik_metni": str(ayar.get("baslik_metni", ""))[:160],
                "grup": ayar.get("grup") if ayar.get("grup") in SAYFA_GRUPLARI else "",
                "sira": _arayuz_sayisini_sinirla(ayar.get("sira", 0), 0, 0, 999),
                "gorunur": bool(ayar.get("gorunur", True)),
                "baslik_renkleri": [r if _arayuz_renk_kodu_gecerli_mi(r) else d for r, d in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)],
                "baslik_puntosu": _arayuz_sayisini_sinirla(ayar.get("baslik_puntosu", 30), 30, 16, 56),
            }
    ozel_sayfalar, kullanilan = [], set()
    ham_ozeller = veri.get("ozel_sayfalar", [])
    if isinstance(ham_ozeller, list):
        for sayfa in ham_ozeller[:50]:
            if not isinstance(sayfa, dict):
                continue
            sid = sayfa.get("id")
            if not isinstance(sid, str) or not re.fullmatch(r"ozel-[A-Za-z0-9]+", sid) or sid in kullanilan:
                continue
            baslik = str(sayfa.get("baslik", "")).strip()[:100]
            if not baslik:
                continue
            bloklar = []
            if isinstance(sayfa.get("bloklar"), list):
                for blok in sayfa["bloklar"][:100]:
                    if isinstance(blok, dict) and blok.get("tur") in ("baslik", "metin") and isinstance(blok.get("metin"), str):
                        bloklar.append({"tur": blok["tur"], "metin": blok["metin"][:4000]})
            grup = sayfa.get("grup")
            ozel_sayfalar.append({"id": sid, "baslik": baslik, "grup": grup if grup in SAYFA_GRUPLARI[:-1] else SAYFA_GRUPLARI[0], "sira": _arayuz_sayisini_sinirla(sayfa.get("sira", 0), 0, 0, 999), "gorunur": bool(sayfa.get("gorunur", True)), "bloklar": bloklar})
            kullanilan.add(sid)
    return {"sayfalar": sayfalar, "ozel_sayfalar": ozel_sayfalar}


def arayuz_sayfa_ayarlarini_kaydet(veri):
    temiz = arayuz_sayfa_ayarlarini_duzenle(veri)
    supabase_veri_kaydet(ARAYUZ_SAYFA_AYARLARI_ID, temiz)
    return temiz


def arayuz_sayfa_ayari_al(ayarlar, sayfa_id):
    sayfalar = ayarlar.get("sayfalar", {}) if isinstance(ayarlar, dict) else {}
    ayar = sayfalar.get(sayfa_id, {}) if isinstance(sayfalar, dict) else {}
    renkler = ayar.get("baslik_renkleri", VARSAYILAN_BASLIK_RENKLERI)
    if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
        renkler = VARSAYILAN_BASLIK_RENKLERI
    return {"etiket": str(ayar.get("etiket", "")), "baslik_metni": str(ayar.get("baslik_metni", "")), "grup": ayar.get("grup", ""), "sira": _arayuz_sayisini_sinirla(ayar.get("sira", 0), 0, 0, 999), "gorunur": bool(ayar.get("gorunur", True)), "baslik_renkleri": [r if _arayuz_renk_kodu_gecerli_mi(r) else d for r, d in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)], "baslik_puntosu": _arayuz_sayisini_sinirla(ayar.get("baslik_puntosu", 30), 30, 16, 56)}


def sayfa_baslik_metnini_al(ayarlar, sayfa_id):
    ayar = arayuz_sayfa_ayari_al(ayarlar, sayfa_id)
    return ayar["baslik_metni"].strip() or sayfa_id


def admin_sayfa_duzenleyici():
    st.markdown("### 🧩 Kod Yazmadan Sayfa Düzenleyici")
    st.caption("Menü görünürlüğünü, sırasını, grubunu ve başlık görünümünü yönetin. Özel sayfalar yalnızca metin blokları içerir; kod/HTML çalıştırılmaz.")
    arayuz = json.loads(json.dumps(st.session_state.arayuz_sayfa_ayarlari, ensure_ascii=False))
    ozel = arayuz["ozel_sayfalar"]
    ids = [m for m in gecerli_menuler if not m.startswith("ozel-")] + [s["id"] for s in ozel]
    etiketler = {s["id"]: s["baslik"] for s in ozel}
    secim = st.selectbox("Düzenlenecek sayfa", ids, format_func=lambda sid: etiketler.get(sid, sid), key="arayuz_editor_secim")
    ayar = arayuz_sayfa_ayari_al(arayuz, secim)
    ozel_sayfa = next((s for s in ozel if s["id"] == secim), None)
    with st.form("arayuz_sayfa_editor_form"):
        etiket = st.text_input("Menü etiketi", ayar["etiket"] or etiketler.get(secim, secim), max_chars=100)
        baslik = st.text_input("Sayfa başlığı", ozel_sayfa["baslik"] if ozel_sayfa else sayfa_baslik_metnini_al(arayuz, secim), max_chars=160)
        grup_ops = SAYFA_GRUPLARI[:-1] if ozel_sayfa else SAYFA_GRUPLARI
        grup = st.selectbox("Menü grubu", grup_ops, index=grup_ops.index(ayar["grup"]) if ayar["grup"] in grup_ops else 0)
        sira = st.number_input("Menü sırası", min_value=0, max_value=999, value=ayar["sira"])
        gorunur = st.checkbox("Menüde göster", value=ayar["gorunur"], disabled=secim == "Kullanıcı Ayarları")
        punto = st.slider("Başlık punto boyutu", 16, 56, ayar["baslik_puntosu"])
        renkler = [st.color_picker(ad, value=renk, key=f"arayuz_renk_{i}") for i, (ad, renk) in enumerate(zip(("Başlangıç", "Yeşil", "Turkuaz", "Mavi"), ayar["baslik_renkleri"]))]
        bloklar = None
        if ozel_sayfa:
            bloklar = st.data_editor(pd.DataFrame(ozel_sayfa["bloklar"], columns=["tur", "metin"]), num_rows="dynamic", hide_index=True, column_config={"tur": st.column_config.SelectboxColumn(options=["baslik", "metin"], required=True), "metin": st.column_config.TextColumn(max_chars=4000)}, key=f"ozel_bloklar_{secim}")
        kaydet = st.form_submit_button("Sayfa ayarlarını kaydet", type="primary")
    if kaydet:
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("Kalıcı sayfa ayarları için Supabase bağlantısı gerekli.")
        else:
            arayuz["sayfalar"][secim] = {"etiket": etiket.strip(), "baslik_metni": baslik.strip(), "grup": grup, "sira": int(sira), "gorunur": gorunur, "baslik_renkleri": renkler, "baslik_puntosu": punto}
            if ozel_sayfa:
                ozel_sayfa.update({"baslik": baslik.strip(), "grup": grup, "sira": int(sira), "gorunur": gorunur, "bloklar": bloklar.to_dict("records")})
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(arayuz)
            st.rerun()
    with st.form("arayuz_ozel_sayfa_olustur"):
        st.markdown("**Yeni metin sayfası**")
        yeni_ad = st.text_input("Sayfa adı", max_chars=100)
        yeni_grup = st.selectbox("Sayfa grubu", SAYFA_GRUPLARI[:-1])
        olustur = st.form_submit_button("Özel sayfa ekle")
    if olustur:
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("Kalıcı kayıt için Supabase bağlantısı gerekli.")
        elif yeni_ad.strip():
            sid = "ozel-" + secrets.token_hex(8)
            arayuz["ozel_sayfalar"].append({"id": sid, "baslik": yeni_ad.strip(), "grup": yeni_grup, "sira": 999, "gorunur": True, "bloklar": []})
            arayuz["sayfalar"][sid] = {"etiket": yeni_ad.strip(), "grup": yeni_grup, "sira": 999, "gorunur": True}
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(arayuz)
            st.rerun()
    if ozel:
        with st.form("arayuz_ozel_sayfa_sil"):
            sil_id = st.selectbox("Silinecek özel sayfa", [s["id"] for s in ozel], format_func=lambda sid: next(s["baslik"] for s in ozel if s["id"] == sid))
            onay = st.checkbox("Bu özel sayfanın kalıcı olarak silinmesini onaylıyorum.")
            sil = st.form_submit_button("Özel sayfayı sil")
        if sil:
            if not onay:
                st.error("Önce silme işlemini onaylayın.")
            elif SUPABASE_URL and SUPABASE_KEY:
                arayuz["ozel_sayfalar"] = [s for s in ozel if s["id"] != sil_id]
                arayuz["sayfalar"].pop(sil_id, None)
                st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(arayuz)
                st.rerun()


# Remote UI settings are untrusted persisted data; sanitize before menu/render use.
st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_duzenle(
    st.session_state.get("arayuz_sayfa_ayarlari", {})
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
    page["id"] for page in st.session_state.arayuz_sayfa_ayarlari["ozel_sayfalar"]
    if page["id"] not in gecerli_menuler
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




# =========================================================================
# GİRİŞ KONTROLÜ / AÇILIŞ GİRİŞ EKRANI
# =========================================================================
if not st.session_state.oturum_aktif:
    login_accent = "#5F7F98" if st.session_state.tema == "Arctic" else "#10b981"
    st.markdown(
        f"""
        <style>
            .login-feature-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; max-width:620px; margin-top:10px; }}
            .login-feature-card {{ min-height:112px; padding:14px 13px; border:1px solid {border_color}; border-radius:16px; background:{card_bg}; transition:transform .22s ease, border-color .22s ease, box-shadow .22s ease; }}
            .login-feature-card:hover {{ transform:translateY(-4px); border-color:#10b981 !important; box-shadow:0 12px 26px -12px rgba(16,185,129,.55); }}
            .login-feature-icon {{ margin-bottom:8px; font-size:1.35rem; }}
            .login-feature-card h4 {{ margin:0 0 4px; color:{text_color}; font-size:.92rem; }}
            .login-feature-card p {{ margin:0; color:{subtext_color}; font-size:.76rem; line-height:1.5; }}
            .login-hero h1 {{ color:{text_color}; font-size:clamp(2.2rem,4vw,3rem); line-height:1.12; }}
            .login-hero h1 span {{ color:{login_accent}; }}
            .login-hero h3,.login-hero p {{ color:{subtext_color}; }}
            .st-key-login-card {{ padding:28px 30px 24px; background:{card_bg}; border:1px solid {border_color}; border-radius:24px; }}
            .st-key-login-card h2 {{ text-align:center; color:{text_color}; }}
            @media(max-width:760px) {{ .login-feature-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); max-width:none; }} .login-feature-card {{ padding:13px; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    login_left, login_right = st.columns([1.05, 1], gap="large")
    with login_left:
        st.markdown(
            """
            <section class="login-hero">
                <div>🍲 AŞEVİ OTOMASYONU</div>
                <h1>Aziziye <span>Aşevi</span></h1>
                <h3>Yönetim &amp; Takip Sistemi</h3>
                <p>Stok girişinden yemek dağıtımına, fire takibinden personel yönetimine kadar tüm süreçler tek panelde. Sadece giriş yapın, gerisini sistem halletsin.</p>
            </section>
            <section class="login-feature-grid">
                <article class="login-feature-card"><div class="login-feature-icon">📦</div><h4>Stok Yönetimi</h4><p>Fatura bazlı giriş, anlık kalan, kritik seviye uyarıları</p></article>
                <article class="login-feature-card"><div class="login-feature-icon">🍲</div><h4>Yemek Üretimi</h4><p>Kişi başı maliyet, kalori ve porsiyon hesabı</p></article>
                <article class="login-feature-card"><div class="login-feature-icon">🗑️</div><h4>Fire &amp; Zayiat</h4><p>Parti bazlı fire tutarı ve neden analizi</p></article>
                <article class="login-feature-card"><div class="login-feature-icon">📱</div><h4>QR Sarfiyat</h4><p>QR ile hızlı düşüm ve paket takibi</p></article>
                <article class="login-feature-card"><div class="login-feature-icon">👥</div><h4>Personel</h4><p>İzin, çalışma süresi ve demirbaş zimmet takibi</p></article>
                <article class="login-feature-card"><div class="login-feature-icon">📊</div><h4>Raporlama</h4><p>Günlük, haftalık ve aylık otomatik e-posta raporları</p></article>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"{APP_VERSION} · {LAST_UPDATE}")
    with login_right.container(key="login-card"):
        st.markdown(
            f'<div style="text-align:center;font-size:30px">🍲</div><h2>Giriş Yap</h2><p style="text-align:center;color:{subtext_color}">Devam etmek için hesabınızla giriş yapın</p>',
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
                            giris_denemesini_sifirla(
                                [u_anahtar, ip_anahtar]
                                if istemci_ip and istemci_ip != "bilinmiyor"
                                else u_anahtar
                            )
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
            tanimli_master = str(st.secrets.get("MASTER_RECOVERY_KEY", "") or "")
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

# =========================================================================
# TEMA SEÇİCİ (Sidebar)
# =========================================================================
_tema_etiketleri = {"Dark": "🌙 Karanlık", "Arctic": "❄️ Arctic Harbor"}
with st.sidebar.expander(f"🎨 Tema · {_tema_etiketleri[st.session_state.tema]}", expanded=False):
    _secim = st.radio(
        "Tema Seçiniz",
        options=["Dark", "Arctic"],
        format_func=lambda x: _tema_etiketleri[x],
        index=["Dark", "Arctic"].index(st.session_state.tema),
        key="tema_radio_widget",
        label_visibility="collapsed",
    )
    if _secim != st.session_state.tema:
        st.session_state.tema = _secim
        st.query_params["tema"] = _secim
        try:
            if cerez_kontrol is not None:
                cerez_yaz(_secim, "aziziye_tema", max_age=365 * 24 * 3600)
                time.sleep(1.0)  # Çerezin tarayıcıya yazılması için bekle
        except Exception:
            pass
        st.rerun()

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
_orijinal_gruplar = menu_gruplari
menu_gruplari = {g: [] for g in _orijinal_gruplar}
menu_gorunen_etiketler, _varsayilan_gruplar, _varsayilan_siralar = {}, {}, {}
for _grup, _items in _orijinal_gruplar.items():
    for _idx, (_mid, _badge) in enumerate(_items):
        _setting = arayuz_sayfa_ayari_al(_arayuz_ayar, _mid)
        _varsayilan_gruplar[_mid], _varsayilan_siralar[_mid] = _grup, _idx
        if not _setting["gorunur"]:
            continue
        _target_group = _setting["grup"] or _grup
        menu_gruplari.setdefault(_target_group, []).append((_mid, _badge, _setting["sira"] if _mid in _arayuz_ayar["sayfalar"] else _idx))
        menu_gorunen_etiketler[_mid] = _setting["etiket"].strip() or _mid
for _page in _arayuz_ayar["ozel_sayfalar"]:
    if _page["gorunur"]:
        menu_gruplari.setdefault(_page["grup"], []).append((_page["id"], "", _page["sira"]))
        menu_gorunen_etiketler[_page["id"]] = _page["baslik"]
for _group in menu_gruplari:
    menu_gruplari[_group].sort(key=lambda item: item[2])
menu_gruplari = {g: [(m, b) for m, b, _ in items] for g, items in menu_gruplari.items()}
filtrelenmis_gruplar = {}
for grup_adi, alt_menuler in menu_gruplari.items():
    uygun_menuler = []
    for m, badge in alt_menuler:
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
            or sidebar_arama in menu_gorunen_etiketler.get(m, m).lower()
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

            gorunen_ad = menu_gorunen_etiketler.get(m, m)
            btn_label = f"{gorunen_ad}  [{badge}]" if badge and badge != "0" else gorunen_ad
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

def test_verisi_kayit_uygun_mu(kayit, kapsam, girisler):
    if kapsam == "fire":
        return isinstance(kayit, dict) and str(kayit.get("tur", "")).strip().casefold() == "fire/zayiat"
    if kapsam == "yemek_kullanim":
        return isinstance(kayit, dict) and str(kayit.get("tur", "")).strip().casefold().startswith("günlük kullanım")
    if kapsam == "kullanilmayan_depo":
        return not any(isinstance(g, dict) and g.get("depo") == kayit for g in girisler)
    if kapsam == "kullanilmayan_kategori":
        return not any(isinstance(g, dict) and str(g.get("kategori", "")).strip().upper() == str(kayit).strip().upper() for g in girisler)
    return True


def test_verisi_kayit_etiketi_olustur(koleksiyon, kayit, indeks):
    if not isinstance(kayit, dict):
        return f"{indeks + 1}. {kayit}"
    alanlar = {"stok": ("id", "urun", "fatura_no", "tarih", "kalan"), "faturalar": ("id", "urun", "fatura_no", "tarih", "kalan"), "silinen_urunler": ("kayit_id", "urun", "tarih", "neden"), "fire": ("urun", "tarih", "miktar", "aciklama"), "yemek_arsivi": ("yemek_adi", "tarih", "kisi_sayisi", "islem_yapan"), "yemek_kullanim": ("urun", "tur", "tarih", "miktar"), "demirbaslar": ("id", "ad", "kategori", "durum"), "ihtiyac_sahipleri": ("id", "ad_soyad", "hane", "eklenme_tarihi"), "dagitimlar": ("id", "tarih", "kisi", "menu", "porsiyon"), "personeller": ("id", "ad_soyad", "gorev", "baslama_tarihi"), "personel_izinleri": ("id", "personel_ad", "izin_turu", "baslangic", "bitis")}.get(koleksiyon, ())
    return f"{indeks + 1}. " + (" | ".join(f"{a}: {kayit[a]}" for a in alanlar if kayit.get(a) not in (None, "")) or "Detay yok")


def test_verisi_sayfa_koleksiyonlari():
    return {"Güncel Stok Durumu": [("stok", "girisler", "verileri_kaydet", "tum")], "Yeni Mal Alımı / Fatura Ekle": [("faturalar", "girisler", "verileri_kaydet", "tum")], "Ürün Sil / Düzenle": [("stok", "girisler", "verileri_kaydet", "tum"), ("silinen_urunler", "silinen_urun_loglari", "silinen_urun_loglarini_kaydet", "tum")], "Fire / Zayiat Girişi": [("fire", "kullanim_loglari", "loglari_kaydet", "fire")], "Depo Yönetimi": [("depolar", "depolar", "depoları_kaydet", "kullanilmayan_depo"), ("kategoriler", "kategoriler", "supabase_veri_kaydet", "kullanilmayan_kategori")], "Demirbaş Yönetimi": [("demirbaslar", "demirbaslar", "demirbaşları_kaydet", "tum")], "Günlük Yemek Üretimi & Maliyet Raporu": [("yemek_arsivi", "yemek_uretim_arsivi", "yemek_uretim_arsivini_kaydet", "tum"), ("yemek_kullanim", "kullanim_loglari", "loglari_kaydet", "yemek_kullanim")], "İhtiyaç Sahibi & Yemek Dağıtım Takibi": [("ihtiyac_sahipleri", "ihtiyac_sahipleri", "ihtiyac_sahiplerini_kaydet", "tum"), ("dagitimlar", "dagitim_loglari", "dagitim_loglarini_kaydet", "tum")], "Personel & Çalışma Süresi Takibi": [("personeller", "personeller", "personelleri_kaydet", "tum"), ("personel_izinleri", "personel_izinleri", "personel_izinlerini_kaydet", "tum")]}


def test_verilerini_temizle(sayfa=None, secimler=None, sadece=None):
    """Remove selected records from one page, or test-named records globally."""
    if sayfa is not None:
        sayfa_koleksiyonlari = test_verisi_sayfa_koleksiyonlari()
        if sayfa not in sayfa_koleksiyonlari:
            raise ValueError("Test verisi temizliği için geçersiz sayfa seçildi.")
        secimler = secimler if isinstance(secimler, dict) else {}
        toplam_silinen = 0
        girisler = st.session_state.get("girisler", [])
        kaydet_fonksiyonlari = {
            "verileri_kaydet": verileri_kaydet,
            "silinen_urun_loglarini_kaydet": silinen_urun_loglarini_kaydet,
            "loglari_kaydet": loglari_kaydet,
            "depoları_kaydet": depoları_kaydet,
            "demirbaşları_kaydet": demirbasları_kaydet,
            "yemek_uretim_arsivini_kaydet": yemek_uretim_arsivini_kaydet,
            "ihtiyac_sahiplerini_kaydet": ihtiyac_sahiplerini_kaydet,
            "dagitim_loglarini_kaydet": dagitim_loglarini_kaydet,
            "personelleri_kaydet": personelleri_kaydet,
            "personel_izinlerini_kaydet": personel_izinlerini_kaydet,
        }
        for koleksiyon, state_key, callback_adi, kapsam in sayfa_koleksiyonlari[sayfa]:
            secilen_indeksler = {str(i) for i in secimler.get(koleksiyon, [])}
            kayitlar = st.session_state.get(state_key, [])
            if not isinstance(kayitlar, list):
                continue
            kalanlar = []
            degisti = False
            for indeks, kayit in enumerate(kayitlar):
                uygun = test_verisi_kayit_uygun_mu(kayit, kapsam, girisler)
                if str(indeks) in secilen_indeksler and uygun:
                    toplam_silinen += 1
                    degisti = True
                else:
                    kalanlar.append(kayit)
            if degisti:
                st.session_state[state_key] = kalanlar
                if callback_adi == "supabase_veri_kaydet":
                    supabase_veri_kaydet("kategoriler_listesi", kalanlar)
                else:
                    kaydet_fonksiyonlari[callback_adi](kalanlar)
        return toplam_silinen

    temizlik_plani = (
        ("girisler", ("urun", "fatura_no"), verileri_kaydet),
        ("personeller", ("ad_soyad", "tc"), personelleri_kaydet),
        ("ihtiyac_sahipleri", ("ad_soyad", "adres"), ihtiyac_sahiplerini_kaydet),
        ("yemek_uretim_arsivi", ("yemek_adi",), yemek_uretim_arsivini_kaydet),
        ("demirbaslar", ("ad",), demirbasları_kaydet),
        ("kullanim_loglari", ("urun",), loglari_kaydet),
        ("silinen_urun_loglari", ("urun",), silinen_urun_loglarini_kaydet),
    )
    toplam_silinen = 0
    for anahtar, alanlar, kaydet in temizlik_plani:
        if sadece is not None and anahtar != sadece:
            continue
        mevcut = st.session_state.get(anahtar, [])
        kalanlar, silinen = test_kayitlarini_ayikla(mevcut, alanlar)
        toplam_silinen += silinen
        if silinen:
            st.session_state[anahtar] = kalanlar
            kaydet(kalanlar)
    return toplam_silinen


def tablo_to_excel_bytes(veri_listesi, baslik_str):
    return excel_raporu_bytes(
        veri_listesi,
        baslik_str,
        simdi_tr_str("%Y-%m-%d %H:%M:%S"),
    )


def tablo_to_html_pdf_bytes(baslik, veri_listesi):
    return html_raporu_bytes(
        baslik,
        veri_listesi,
        simdi_tr_str("%Y-%m-%d %H:%M:%S"),
        {
            "text_color": text_color,
            "bg_color": bg_color,
            "subtext_color": subtext_color,
            "card_bg": card_bg,
            "border_color": border_color,
            "sidebar_bg": sidebar_bg,
        },
    )


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
    
_sayfa_gorunum_ayari = arayuz_sayfa_ayari_al(
    st.session_state.arayuz_sayfa_ayarlari, menu
)
_sayfa_renkleri = _sayfa_gorunum_ayari["baslik_renkleri"]
_sayfa_puntosu = _sayfa_gorunum_ayari["baslik_puntosu"]
st.markdown(
    f"""
    <style>
      .stApp h1, .stApp h2, .stApp h3 {{
        background-image: linear-gradient(90deg, { _sayfa_renkleri[0] } 0%,
          { _sayfa_renkleri[1] } 35%, { _sayfa_renkleri[2] } 68%,
          { _sayfa_renkleri[3] } 100%);
        -webkit-background-clip: text; background-clip: text;
        color: transparent; font-size: {_sayfa_puntosu}px !important;
      }}
      .stApp h2 {{ font-size: {_sayfa_puntosu * 0.8}px !important; }}
      .stApp h3 {{ font-size: {_sayfa_puntosu * 0.67}px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

_ozel_menu_sayfasi = next((s for s in st.session_state.arayuz_sayfa_ayarlari.get("ozel_sayfalar", []) if s.get("id") == menu), None)
if _ozel_menu_sayfasi and not _ozel_menu_sayfasi["gorunur"]:
    st.warning("Bu özel sayfa şu anda menüde kullanıma kapalı.")
    st.stop()
if _ozel_menu_sayfasi:
    st.header(_ozel_menu_sayfasi["baslik"])
    for _blok in _ozel_menu_sayfasi.get("bloklar", []):
        if _blok.get("tur") == "baslik":
            st.subheader(_blok.get("metin", ""))
        elif _blok.get("tur") == "metin":
            st.markdown(_blok.get("metin", ""), unsafe_allow_html=False)
elif menu == "Kurumsal Dashboard & Özet" or menu == "Genel Bakış":
    dashboard_sayfasi(
        st, aktif_k_maskeleri, yonetici_modu, components, dashboard_ozet_hesapla,
        dashboard_operasyonel_istatistikleri, "", requests, datetime, html_escape,
    )

elif menu == "Güncel Stok Durumu":
    guncel_stok_sayfasi(
        st, misafir_modu, aktif_k_maskeleri, stok_excel_liste_olustur,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        stok_gorunum_listeleri_olustur, ozel_html_tablo_goster, verileri_kaydet,
        kritik_seviyeleri_kaydet, mevcut_urunler_qr_etiket_araci,
    )

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    mal_alimi_sayfasi(
        st, salt_okunur_modu, otomatik_yedek_al, verileri_kaydet, yeni_id_uret,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )

# DEPO YÖNETİMİ
elif menu == "Depo Yönetimi":
    depo_yonetim_sayfasi(
        st, misafir_modu, yonetici_modu, supabase_veri_oku, otomatik_yedek_al,
        depoları_kaydet, verileri_kaydet, supabase_veri_kaydet,
        silme_onay_kutusu, ozel_html_tablo_goster,
    )

# DEMİRBAŞ YÖNETİMİ
elif menu == "Demirbaş Yönetimi":
    demirbas_yonetim_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster, otomatik_yedek_al, demirbasları_kaydet,
        yeni_id_uret, silme_onay_kutusu,
    )

# QR KOD İLE HIZLI SARFİYAT
elif menu == "QR Kod ile Hızlı Sarfiyat":
    qr_kod_ile_hizli_sarfiyat_sayfasi(
        st, salt_okunur_modu, fifo_sarfiyat_dus, simdi_tr_str,
        verileri_kaydet, loglari_kaydet,
    )

# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    urun_sil_duzenle_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu, verileri_kaydet,
        silinen_urun_loglarini_kaydet, otomatik_yedek_al, simdi_tr_str,
        silme_onay_kutusu, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster,
    )

# 4. FİRE / ZAYİAT GİRİŞİ
elif menu == "Fire / Zayiat Girişi":
    fire_zayiat_sayfasi(
        st, menu, misafir_modu, salt_okunur_modu, otomatik_yedek_al,
        verileri_kaydet, loglari_kaydet, fifo_miktar_dus_detayli,
        aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster,
    )

# TOPLU STOK DÜŞÜMÜ & SARFİYAT
elif menu == "Toplu Stok Düşümü & Sarfiyat":
    toplu_stok_dusumu_sayfasi(
        st, misafir_modu, salt_okunur_modu, otomatik_yedek_al,
        fifo_sarfiyat_dus_detayli, verileri_kaydet, loglari_kaydet,
        ozel_html_tablo_goster,
    )

# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    gunluk_yemek_uretim_sayfasi(
        st, misafir_modu, salt_okunur_modu, aktif_k_maskeleri, otomatik_yedek_al,
        verileri_kaydet, loglari_kaydet, yemek_uretim_arsivini_kaydet, simdi_tr_str,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )

elif menu == "Kalori Hesaplama Aracı":
    kalori_hesaplama_sayfasi(
        st, supabase_veri_oku, supabase_veri_kaydet, urun_kalori_hesapla,
        yeni_id_uret, simdi_tr_str, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ozel_html_tablo_goster, ortak_indirme_alani,
    )

# 7. İHTİYAÇ SAHİBİ & YEMEK DAĞITIM TAKİBİ
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi")
        st.markdown(
            "Aşevimizden yemek yardımı alan kişilerin kayıtlarını oluşturun, aktif/pasif durumlarını yönetin ve yemek dağıtımlarını takip edin."
        )

        # 1) Son Silinen İhtiyaç Sahibini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_silinen_ihtiyac_sahibi"):
            son_kisi = st.session_state["son_silinen_ihtiyac_sahibi"]
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                st.info(
                    f"💡 **Son Silinen İhtiyaç Sahibi:** {son_kisi.get('ad_soyad')} (Kayıt No: {son_kisi.get('id')} - T.C./Hane: {son_kisi.get('tc_hane', '-')})"
                )
            with c_undo2:
                if st.button("↩️ Silinen Kişiyi Geri Al", type="secondary", key="btn_undo_kisi_sil_son"):
                    otomatik_yedek_al("Silinen ihtiyaç sahibini geri alma: " + str(son_kisi.get("ad_soyad")))
                    
                    # Kişiyi tekrar listeye iade et
                    if not any(k["id"] == son_kisi["id"] for k in st.session_state.ihtiyac_sahipleri):
                        st.session_state.ihtiyac_sahipleri.append(son_kisi)
                    
                    ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                    st.session_state.pop("son_silinen_ihtiyac_sahibi", None)
                    st.success(f"🎉 '{son_kisi.get('ad_soyad')}' ihtiyaç sahibi listesine başarıyla geri yüklendi!")
                    time.sleep(1)
                    st.rerun()

        # 2) Son Toplu Yemek Dağıtımını Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_toplu_dagitim_kaydi"):
            son_dagitim = st.session_state["son_toplu_dagitim_kaydi"]
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                st.info(
                    f"💡 **Son Toplu Dağıtım:** '{son_dagitim.get('menu')}' ({son_dagitim.get('sayi')} Haneye Dağıtıldı - Tarih: {son_dagitim.get('tarih')})"
                )
            with c_undo2:
                if st.button("↩️ Son Dağıtımı Geri Al", type="secondary", key="btn_undo_dagitim_son"):
                    otomatik_yedek_al("Toplu yemek dağıtımı geri alma: " + str(son_dagitim.get("menu")))
                    
                    silinecek_id_listesi = son_dagitim.get("eklenen_id_listesi", [])
                    st.session_state.dagitim_loglari = [
                        d for d in st.session_state.dagitim_loglari if d.get("id") not in silinecek_id_listesi
                    ]
                    
                    dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                    st.session_state.pop("son_toplu_dagitim_kaydi", None)
                    st.success(f"🎉 '{son_dagitim.get('menu')}' için yapılan toplu dağıtım kaydı geri alındı ve silindi!")
                    time.sleep(1)
                    st.rerun()

        tab1, tab2, tab3 = st.tabs([
            "📋 İhtiyaç Sahibi Listesi, Aktif/Pasif ve Ekle",
            "🍲 Toplu Yemek Dağıtımı",
            "📊 Dağıtım Sayacı & Raporları",
        ])

        ihtiyac_sahibi_listesi_tabini_goster(
            tab1, st, aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
            ortak_indirme_alani, salt_okunur_modu, yonetim_modu, simdi_tr_str, yeni_id_uret,
            ihtiyac_sahiplerini_kaydet, yonetici_modu, silme_onay_kutusu,
            otomatik_yedek_al, ozel_html_tablo_goster,
        )

        toplu_yemek_dagitimi_tabini_goster(
            tab2, st, aktif_k_maskeleri, yonetim_modu, html_escape, simdi_tr_str,
            yeni_id_uret, dagitim_loglarini_kaydet, tablo_to_excel_bytes,
            tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
        )

        dagitim_sayac_tabini_goster(
            tab3, st, aktif_k_maskeleri, tablo_to_excel_bytes,
            tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
        )

# 8. PERSONEL VE ÇALIŞMA SÜRESİ TAKİBİ
elif menu in ["Personel ve Çalışma Süresi Takibi", "Personel & Çalışma Süresi Takibi"]:
    personel_ve_calisma_suresi_sayfasi(
        st, misafir_modu, salt_okunur_modu, yonetici_modu, aktif_k_maskeleri,
        idleri_benzersiz_yap, otomatik_yedek_al, personelleri_kaydet,
        personel_izinlerini_kaydet, yeni_id_uret, simdi_tr_str, silme_onay_kutusu,
        [], tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
        ortak_indirme_alani, ozel_html_tablo_goster, supabase_veri_kaydet,
    )

elif menu == "Kullanım Takibi":
    kullanim_takibi_sayfasi(
        st, misafir_modu, st.session_state.kullanim_loglari,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )

# 10. KAPSAMLI ENVANTER VE HAREKET RAPORU
elif menu == "Kapsamlı Envanter ve Hareket Raporu":
    kapsamli_envanter_rapor_sayfasi(
        st, misafir_modu, st.session_state.girisler, kapsamli_envanter_liste_olustur,
        tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani,
        ozel_html_tablo_goster,
    )

# 11. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    urun_fiyat_analizi_sayfasi(
        st, st.session_state.girisler, aktif_k_maskeleri, benzersiz_urun_adlari,
        urun_fiyat_analizi_olustur, tablo_to_excel_bytes,
        tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster,
    )

# 12. KULLANICI YÖNETİMİ, GÜVENLİK DURUMU, GİRİŞ KAYITLARI VE YEDEKLEME
elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz yalnızca **Admin** kullanıcısına aittir.")
    else:
        st.header("⚙️ Kullanıcı Yönetimi, Güvenlik ve Yedekleme")
        kullanici_db = st.session_state.kullanicilar

        manuel_rapor_gonderim_alani(st, manuel_rapor_maili_gonder)

        st.markdown("---")
        
        # Tip güvenliği: maskeler ve yasaklı menüler düz liste olmalıdır
        for _kk, _kv in kullanici_db.items():
            if not isinstance(_kv.get("maskeli_alanlar"), list):
                _kv["maskeli_alanlar"] = []
            if not isinstance(_kv.get("yasakli_menuler"), list):
                _kv["yasakli_menuler"] = []

        # ------------------------------------------------------------------
        kullanici_islemi_geri_al_alani(
            st, kullanici_db, otomatik_yedek_al, kullanıcıları_kaydet, giris_logla,
        )

        guvenlik_durumu_rozetlerini_goster(
            st, SUPABASE_URL, SUPABASE_KEY, supabase_anahtar_rolu, cerez_kontrol,
            html_escape, bosta_kalma_suresi_sn, kullanici_db, ESKI_VARSAYILAN_HASHLER,
        )

        sekme_k, sekme_s, sekme_l, sekme_y = st.tabs([
            "👤 Kullanıcılar", "🔑 Şifrem", "📜 Giriş Kayıtları", "💾 Yedekleme",
        ])

        # ------------------------------------------------ Kullanıcılar
        kullanici_yonetim_sekmesini_goster(
            sekme_k, st, kullanici_db, ESKI_VARSAYILAN_HASHLER, gecerli_menuler,
            otomatik_yedek_al, kullanici_oturumlarini_kapat, kullanıcıları_kaydet,
            giris_logla, sifre_hashle_yeni, sifre_politika_hatasi,
        )

        kendi_sifre_sekmesini_goster(
            sekme_s, st, kullanici_db, sifre_dogrula, sifre_politika_hatasi, sifre_degistir,
        )

        # ------------------------------------------------ Giriş kayıtları
        giris_kayitlari_sekmesini_goster(
            sekme_l, st, SUPABASE_URL, SUPABASE_KEY, _supa_basliklar,
            _supabase_ham_oku, requests, tablo_to_excel_bytes, tablo_to_html_pdf_bytes,
            ortak_indirme_alani, ozel_html_tablo_goster, giris_denemesini_sifirla, giris_logla,
        )

        yedekleme_sekmesini_goster(
            sekme_y, st, SUPABASE_URL, SUPABASE_KEY, yedek_paketi_olustur,
            simdi_tr_str, giris_logla, yedek_geri_yukle, _supabase_ham_oku,
        )

        # Yönetim araçları User Settings içeriğinin en altındadır.
        st.markdown("---")
        with st.expander("🧩 Kod Yazmadan Sayfa Düzenleyici", expanded=True):
            admin_sayfa_duzenleyici()
        st.markdown("---")
        st.markdown("### 🧹 Test Verisi Temizleme Aracı")
        st.warning(
            "Tüm listelerde adında veya açıklamasında **'test'** geçen kayıtları kalıcı olarak siler."
        )
        onay_test = st.checkbox(
            "Test verilerini silmek istediğimi onaylıyorum.", key="chk_test_temizle"
        )
        if st.button(
            "Test Verilerini Temizle", type="primary", disabled=not onay_test,
            key="btn_test_verilerini_temizle_tumu",
        ):
            silinen = test_verilerini_temizle()
            if silinen > 0:
                st.success(f"Başarılı! {silinen} adet test kaydı sistemden ve loglardan temizlendi.")
                time.sleep(1.5)
                st.rerun()
            else:
                st.info("İçinde 'test' geçen herhangi bir kayıt bulunamadı.")

        with st.expander("🧹 Sayfa Sayfa Test Verisi Temizleme Aracı"):
            st.warning(
                "Önce sayfayı, ardından silinecek kayıtları tek tek seçin. "
                "Bu işlem kayıt adı 'test' içermese bile seçtiğiniz kayıtları kalıcı olarak siler."
            )
            sayfa_koleksiyonlari = test_verisi_sayfa_koleksiyonlari()
            secilen_sayfa = st.selectbox(
                "Temizlenecek Sayfa", list(sayfa_koleksiyonlari),
                key="test_temizleme_sayfasi",
            )
            secimler = {}
            secim_etiketleri = []
            sayfa_aciklamalari = {
                "Güncel Stok Durumu": "Stok partileri aynı fatura/stok verisini kullanan sayfalardan kaldırılır.",
                "Yeni Mal Alımı / Fatura Ekle": "Seçilen stok/fatura partisi stok görünümünden kaldırılır.",
                "Ürün Sil / Düzenle": "Stok partileri ve silinen ürün kayıtları ayrı ayrı seçilir.",
                "Fire / Zayiat Girişi": "Fire kayıtları silinir; düşülmüş stok miktarı otomatik geri eklenmez.",
                "Günlük Yemek Üretimi & Maliyet Raporu": "Arşiv ve kullanım logları silinir; tüketilmiş stok geri yüklenmez.",
                "Depo Yönetimi": "Ürün girişlerinde kullanılan depo/kategoriler seçimden çıkarılır.",
                "İhtiyaç Sahibi & Yemek Dağıtım Takibi": "İhtiyaç sahibi ve dağıtım kayıtları ayrı ayrı seçilir.",
                "Personel & Çalışma Süresi Takibi": "Personel ve izin kayıtları ayrı ayrı seçilir.",
            }
            if secilen_sayfa in sayfa_aciklamalari:
                st.info(sayfa_aciklamalari[secilen_sayfa])
            basliklar = {
                "stok": "Stok partileri", "faturalar": "Fatura / mal alımı kayıtları",
                "silinen_urunler": "Silinen ürün kayıtları", "fire": "Fire / zayiat kayıtları",
                "depolar": "Kullanılmayan depolar", "kategoriler": "Kullanılmayan kategoriler",
                "demirbaslar": "Demirbaş kayıtları", "yemek_arsivi": "Yemek üretim arşivi",
                "yemek_kullanim": "Günlük kullanım logları", "ihtiyac_sahipleri": "İhtiyaç sahibi kayıtları",
                "dagitimlar": "Yemek dağıtım kayıtları", "personeller": "Personel kayıtları",
                "personel_izinleri": "İzin / çalışma süresi kayıtları",
            }
            for koleksiyon, state_key, _callback, kapsam in sayfa_koleksiyonlari[secilen_sayfa]:
                kayitlar = st.session_state.get(state_key, [])
                if not isinstance(kayitlar, list):
                    kayitlar = []
                secilebilir = [
                    (i, kayit) for i, kayit in enumerate(kayitlar)
                    if test_verisi_kayit_uygun_mu(kayit, kapsam, st.session_state.get("girisler", []))
                ]
                st.markdown(f"**{basliklar[koleksiyon]}**")
                if not secilebilir:
                    st.caption("Bu bölümde seçilebilir kayıt bulunmuyor.")
                    continue
                etiketler = {
                    str(i): test_verisi_kayit_etiketi_olustur(koleksiyon, kayit, i)
                    for i, kayit in secilebilir
                }
                liste_imzasi = str(tuple(etiketler.values()))
                secim = st.multiselect(
                    "Silinecek kayıtları seçin", options=list(etiketler),
                    format_func=lambda deger, etiketler=etiketler: etiketler[deger],
                    key=f"test_temizle_{secilen_sayfa}_{koleksiyon}_{abs(hash(liste_imzasi))}",
                    label_visibility="collapsed",
                )
                secimler[koleksiyon] = secim
                secim_etiketleri.extend(etiketler[deger] for deger in secim)
            toplam_secim = sum(len(secim) for secim in secimler.values())
            onay_test_sayfa = st.checkbox(
                f"Bu sayfadaki seçili {toplam_secim} kaydı kalıcı olarak silmek istiyorum.",
                key=f"chk_test_temizle_sayfa_{secilen_sayfa}", disabled=toplam_secim == 0,
            )
            if secim_etiketleri:
                with st.expander("Silinecek kayıtları son kez gözden geçir"):
                    for etiket in secim_etiketleri:
                        st.write(f"- {etiket}")
            if st.button(
                "Seçili Test / Deneme Verilerini Sil", type="secondary",
                disabled=not onay_test_sayfa or toplam_secim == 0,
                key="btn_test_verilerini_temizle_sayfa",
            ):
                silinen = test_verilerini_temizle(secilen_sayfa, secimler)
                if silinen:
                    st.success(f"{silinen} seçili kayıt temizlendi.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.info("Seçilen kayıtlar artık sayfada bulunmuyor veya kullanımda oldukları için silinmedi.")

# Uygulama her açıldığında/yenilendiğinde mail kontrolünü çalıştırır
gunluk_rapor_maili_gonder()
