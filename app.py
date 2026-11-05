import datetime
import io
import json
import os
from cryptography.fernet import Fernet
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Aziziye - Siyah Tema Pro Aşevi Sistemi",
    page_icon="🍲",
    layout="wide",
)

# Şifreleme Anahtarı ve Güvenli Motor Başlatma
@st.cache_resource
def fernet_motorunu_baslat():
    try:
        gizli_anahtar = st.secrets["FERNET_KEY"].encode("utf-8")
        return Fernet(gizli_anahtar)
    except Exception:
        return Fernet(Fernet.generate_key())

fernet_motoru = fernet_motorunu_baslat()

def metni_sifrele(duz_metin):
    if not duz_metin:
        return ""
    try:
        return fernet_motoru.encrypt(str(duz_metin).encode("utf-8")).decode("utf-8")
    except Exception as e:
        return str(duz_metin)

def metni_coz(sifreli_metin):
    if not sifreli_metin:
        return ""
    try:
        return fernet_motoru.decrypt(str(sifreli_metin).encode("utf-8")).decode("utf-8")
    except Exception:
        return str(sifreli_metin)

# TEK VE SAF SİYAH TEMA (Liquid Glass & Beyaz Çizgi İkon/Takvim Stili)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .main, .stApp { 
        background-color: #000000 !important; 
        color: #ffffff !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    .stSidebar { 
        background-color: #000000 !important; 
        padding-top: 10px; 
        border-right: 1px solid #121212 !important;
    }
    .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
        color: #d1d5db !important; 
        font-size: 13.5px; 
    }
    
    section[data-testid="stSidebar"] div[data-testid="stExpander"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        margin-bottom: 4px;
    }
    
    section[data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        color: #9ca3af !important;
        border: none !important;
        border-radius: 10px !important;
        text-align: left !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 8px 12px !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 0 0 1px rgba(255, 255, 255, 0.05) !important;
        transform: translateX(4px);
    }
    
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: rgba(255, 255, 255, 0.09) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    }

    h1, h2, h3, h4, h5, h6 { 
        color: #ffffff !important; 
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
    }
    p, span, label, div, .stMarkdown { 
        color: #e5e7eb !important; 
    }
    button[kind="header"] svg, [data-testid="collapsedControl"] span, [data-testid="collapsedControl"] div { display: none !important; }
    section[data-testid="stSidebar"] [data-testid="baseButton-header"] { color: transparent !important; }

    div.stButton > button, button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"], div.stFormSubmitButton > button {
        background-color: #121212 !important;
        color: #ffffff !important;
        border: 1px solid #2d2d2d !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div.stButton > button:hover, button[data-testid="baseButton-secondary"]:hover, button[data-testid="baseButton-primary"]:hover, div.stFormSubmitButton > button:hover {
        background-color: #1f1f1f !important;
        border-color: #6366f1 !important;
        transform: translateY(-1px);
    }

    div.stMetric, div[data-testid="stExpander"], div.stForm {
        background: #0c0c0c !important;
        border: 1px solid #222222;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.8);
        color: #ffffff !important;
    }
    
    div[data-baseweb="menu"], ul[role="listbox"], div[data-baseweb="popover"], div[data-baseweb="calendar"] {
        background: rgba(12, 12, 12, 0.85) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.6) !important;
        border-radius: 14px !important;
    }
    
    .stDateInput svg, div[data-baseweb="calendar"] svg, button svg {
        filter: brightness(0) invert(1) !important;
        opacity: 0.85;
    }

    li[role="option"], li[role="option"] div, li[role="option"] span {
        background: transparent !important;
        color: #e5e7eb !important;
    }
    li[role="option"]:hover, li[role="option"]:hover div, li[role="option"]:hover span {
        background: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
    }
    li[role="option"][aria-selected="true"] {
        background: rgba(99, 102, 241, 0.2) !important;
        color: #ffffff !important;
        border-left: 3px solid #6366f1 !important;
    }

    div[data-baseweb="calendar"] div, div[data-baseweb="calendar"] span, div[data-baseweb="calendar"] button {
        color: #ffffff !important;
    }
    input, div[data-baseweb="select"] > div {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border-color: #2d2d2d !important;
    }

    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-top: 15px;
        margin-bottom: 15px;
        background-color: #0c0c0c;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #222222;
    }
    .custom-table th {
        background-color: #000000;
        color: #ffffff;
        padding: 14px 18px;
        text-align: left;
        font-size: 13px;
        font-weight: 600;
        border-bottom: 1px solid #222222;
    }
    .custom-table td {
        padding: 14px 18px;
        color: #d1d5db;
        font-size: 13px;
        border-bottom: 1px solid #222222;
    }
    .custom-table tr:hover {
        background-color: rgba(31, 31, 31, 0.6);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

VERI_DOSYASI = "asevi_stok_veritabani.json"
KULLANIM_LOG_DOSYASI = "asevi_kullanim_loglari.json"
IHTIYAC_SAHIPLERI_DOSYASI = "asevi_ihtiyac_sahipleri.json"
DAGITIM_LOG_DOSYASI = "asevi_dagitim_loglari.json"
PERSONEL_DOSYASI = "asevi_personel_veritabani.json"
TATIL_DOSYASI = "asevi_resmi_tatiller.json"
SILINENS_DOSYASI = "asevi_silinen_urunler_loglari.json"
YEMEK_URETIM_ARSIV_DOSYASI = "asevi_yemek_uretim_arsivi.json"
KULLANICI_YETKI_DOSYASI = "asevi_kullanici_yetkileri.json"
DASHBOARD_WIDGET_DOSYASI = "boardui_dashboard_widgets.json"


def ozel_html_tablo_goster(veri_listesi):
    if not veri_listesi:
        st.info("Gösterilecek kayıt bulunmuyor.")
        return
    headers = list(veri_listesi[0].keys())
    html = "<table class='custom-table'><thead><tr>"
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"
    for row in veri_listesi:
        html += "<tr>"
        for h in headers:
            html += f"<td>{row.get(h, '')}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


KALORI_TABLOSU = {
    "PİRİNÇ": 130, "BALDO PİRİNÇ": 130, "KURU FASULYE": 340, "NOHUT": 360,
    "KIRMIZI MERCİMEK": 350, "YEŞİL MERCİMEK": 350, "BULGUR": 340, "PİLAVLIK BULGUR": 340,
    "MAKARNA": 350, "BURGU MAKARNA": 350, "İNCE UZUN MAKARNA": 350, "ERİŞTE MAKARNA": 360,
    "UN": 364, "PATATES": 77, "SOĞAN": 40, "DOMATES": 18, "SALATALIK": 15,
    "BİBER": 40, "ÇARLİ": 40, "KAPYA BİBER": 31, "ISPANAK": 23, "PATLICAN": 25,
    "KABAK": 17, "HAVUÇ": 41, "LAHANA": 25, "KIRMIZI LAHANA": 31, "MAYDANOZ": 36,
    "ET": 250, "KUŞBAŞI ET": 250, "TAVUK": 165, "SIRTSIZ GÖĞÜS": 165, "YUMURTA": 155,
    "YOĞURT": 61, "TAM YAĞLI YOĞURT": 61, "SÜT": 42, "YAĞLI SÜT": 42, "TEREYAĞI": 717,
    "AYÇİÇEK YAĞI": 884, "TENEKE AYÇİÇEK YAĞI": 884, "SALÇA": 82, "DOMATES SALÇASI": 82,
    "ŞEKER": 387, "TOZ ŞEKER": 387, "TUZ": 0, "İRMİK": 360, "BEZELYE": 81, "BEZELYE KONSERVESİ": 81,
}

def urun_kalori_hesapla(urun_adi, miktar, birim):
    urun_upper = urun_adi.upper()
    birim_kalori = 100
    for k, v in KALORI_TABLOSU.items():
        if k in urun_upper:
            birim_kalori = v
            break
    carp = 1000 if birim in ["Kg", "Lt"] else 100
    return (miktar * carp * birim_kalori) / 100.0


varsayilan_girisler = [
    {"id": "STK-001", "tarih": "2026-09-28 08:30", "fatura_no": "FAT-2026-001", "urun": "KIRMIZI LAHANA", "kategori": "SEBZE", "birim": "Kg", "miktar": 42.8, "kalan": max(0.0, 42.8 - 15.0), "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-002", "tarih": "2026-09-28 08:35", "fatura_no": "FAT-2026-002", "urun": "MAYDANOZ", "kategori": "SEBZE", "birim": "Kg", "miktar": 20.0, "kalan": max(0.0, 20.0 - 3.1), "fiyat": 25.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
]

varsayilan_loglar = [
    {"tarih": "2026-10-05 10:00", "urun": "ISPANAK", "tur": "Fire/Zayiat", "miktar": 60.0, "tutar": 4200.00, "islem_yapan": "admin"},
    {"tarih": "2026-10-09 10:00", "urun": "PATLICAN", "tur": "Fire/Zayiat", "miktar": 52.4, "tutar": 2882.00, "islem_yapan": "admin"},
]

varsayilan_personeller = [
    {"tc": "11111111111", "ad_soyad": "MUHAMMED İLKER ÇELİK", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"tc": "22222222222", "ad_soyad": "EMİRHAN DÖNMEZ", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"tc": "33333333333", "ad_soyad": "SEDAT UZUN", "gorev": "Aşçı", "baslama": "2026-09-25", "aktif": True, "izinler": []},
]

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {"tarih": "2026-04-23", "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı"},
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {"tarih": "2026-05-19", "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı"},
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"},
]

varsayilan_kullanicilar = {
    "admin": {"sifre": "Ss123321", "tip": "admin", "yasakli_menuler": []},
    "asci": {"sifre": "sydv25", "tip": "personel", "yasakli_menuler": []},
    "yonetim": {"sifre": "Yonetim25", "tip": "personel", "yasakli_menuler": []},
}

varsayilan_widgets = [
    {"id": "w1", "baslik": "Kategori Bazlı Stok Dağılımı (Sütun Grafik)", "tur": "Sütun Grafik", "aktif": True},
    {"id": "w2", "baslik": "Aylık Fire ve Zayiat Trendi (Çizgi Grafik)", "tur": "Çizgi Grafik", "aktif": True},
]

# --- ÖNBELLEKLENMİŞ YÜKLEME FONKSİYONLARI ---

@st.cache_data
def widgetlari_yukle():
    if os.path.exists(DASHBOARD_WIDGET_DOSYASI):
        try:
            with open(DASHBOARD_WIDGET_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_widgets
    return varsayilan_widgets

def widgetlari_kaydet(veri):
    with open(DASHBOARD_WIDGET_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def kullanıcıları_yukle():
    if os.path.exists(KULLANICI_YETKI_DOSYASI):
        try:
            with open(KULLANICI_YETKI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_kullanicilar
    return varsayilan_kullanicilar

def kullanıcıları_kaydet(veri):
    with open(KULLANICI_YETKI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def verileri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "fatura_no" not in item:
                        item["fatura_no"] = "BELİRTİLMEMİŞ"
                return data
        except Exception:
            return varsayilan_girisler
    return varsayilan_girisler

def verileri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def loglari_yukle():
    if os.path.exists(KULLANIM_LOG_DOSYASI):
        try:
            with open(KULLANIM_LOG_DOSYASI, "r", encoding="utf-8") as f:
                kayitli_loglar = json.load(f)
                if kayitli_loglar:
                    return kayitli_loglar
        except Exception:
            pass
    return varsayilan_loglar

def loglari_kaydet(veri):
    with open(KULLANIM_LOG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def silinen_urun_loglarini_yukle():
    if os.path.exists(SILINENS_DOSYASI):
        try:
            with open(SILINENS_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def silinen_urun_loglarini_kaydet(veri):
    with open(SILINENS_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def ihtiyac_sahiplerini_yukle():
    if os.path.exists(IHTIYAC_SAHIPLERI_DOSYASI):
        try:
            with open(IHTIYAC_SAHIPLERI_DOSYASI, "r", encoding="utf-8") as f:
                ham_veri = json.load(f)
                cozulmus_liste = []
                for k in ham_veri:
                    k_kopya = k.copy()
                    k_kopya["tc_hane"] = metni_coz(k.get("tc_hane", ""))
                    k_kopya["telefon"] = metni_coz(k.get("telefon", ""))
                    k_kopya["adres"] = metni_coz(k.get("adres", ""))
                    cozulmus_liste.append(k_kopya)
                return cozulmus_liste
        except Exception:
            return []
    return []

def ihtiyac_sahiplerini_kaydet(veri_listesi):
    sifrelenmis_liste = []
    for k in veri_listesi:
        k_kopya = k.copy()
        k_kopya["tc_hane"] = metni_sifrele(k.get("tc_hane", ""))
        k_kopya["telefon"] = metni_sifrele(k.get("telefon", ""))
        k_kopya["adres"] = metni_sifrele(k.get("adres", ""))
        sifrelenmis_liste.append(k_kopya)
    with open(IHTIYAC_SAHIPLERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sifrelenmis_liste, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def dagitim_loglarini_yukle():
    if os.path.exists(DAGITIM_LOG_DOSYASI):
        try:
            with open(DAGITIM_LOG_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def dagitim_loglarini_kaydet(veri):
    with open(DAGITIM_LOG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def personelleri_yukle():
    if os.path.exists(PERSONEL_DOSYASI):
        try:
            with open(PERSONEL_DOSYASI, "r", encoding="utf-8") as f:
                ham_veri = json.load(f)
                cozulmus_p = []
                for p in ham_veri:
                    p_kopya = p.copy()
                    p_kopya["tc"] = metni_coz(p.get("tc", ""))
                    cozulmus_p.append(p_kopya)
                return cozulmus_p
        except Exception:
            return varsayilan_personeller
    return varsayilan_personeller

def personelleri_kaydet(veri_listesi):
    sifrelenmis_p = []
    for p in veri_listesi:
        p_kopya = p.copy()
        p_kopya["tc"] = metni_sifrele(p.get("tc", ""))
        sifrelenmis_p.append(p_kopya)
    with open(PERSONEL_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sifrelenmis_p, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

@st.cache_data
def resmi_tatilleri_yukle():
    if os.path.exists(TATIL_DOSYASI):
        try:
            with open(TATIL_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_resmi_tatiller
    return varsayilan_resmi_tatiller

@st.cache_data
def yemek_uretim_arsivini_yukle():
    if os.path.exists(YEMEK_URETIM_ARSIV_DOSYASI):
        try:
            with open(YEMEK_URETIM_ARSIV_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def yemek_uretim_arsivini_kaydet(veri):
    with open(YEMEK_URETIM_ARSIV_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)
    st.cache_data.clear()

# --- SESSION STATE BAŞLATMA ---
if "girisler" not in st.session_state:
    st.session_state.girisler = verileri_yukle()
if "kullanim_loglari" not in st.session_state:
    st.session_state.kullanim_loglari = loglari_yukle()
if "silinen_urun_loglari" not in st.session_state:
    st.session_state.silinen_urun_loglari = silinen_urun_loglarini_yukle()
if "ihtiyac_sahipleri" not in st.session_state:
    st.session_state.ihtiyac_sahipleri = ihtiyac_sahiplerini_yukle()
if "dagitim_loglari" not in st.session_state:
    st.session_state.dagitim_loglari = dagitim_loglarini_yukle()
if "personeller" not in st.session_state:
    st.session_state.personeller = personelleri_yukle()
if "resmi_tatiller" not in st.session_state:
    st.session_state.resmi_tatiller = resmi_tatilleri_yukle()
if "yemek_uretim_arsivi" not in st.session_state:
    st.session_state.yemek_uretim_arsivi = yemek_uretim_arsivini_yukle()
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

query_params = st.query_params

if "oturum_aktif" not in st.session_state:
    if "auth" in query_params and query_params["auth"] == "true" and "user" in query_params:
        st.session_state.oturum_aktif = True
        st.session_state.aktif_kullanici = query_params["user"]
    else:
        st.session_state.oturum_aktif = False
        st.session_state.aktif_kullanici = "misafir"

gecerli_menuler = [
    "Kurumsal Dashboard & Özet", "Güncel Stok Durumu", "Yeni Mal Alımı / Fatura Ekle",
    "Ürün Sil / Düzenle", "Fire / Zayiat Girişi", "Ürün Birim Fiyatları & Ay Analizi",
    "Günlük Yemek Üretimi & Maliyet Raporu", "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi", "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi", "Kullanıcı Ayarları",
]

if "aktif_menu" not in st.session_state:
    if "menu" in query_params and query_params["menu"] in gecerli_menuler:
        st.session_state.aktif_menu = query_params["menu"]
    else:
        st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"

if "silme_mesaji" not in st.session_state:
    st.session_state.silme_mesaji = ""
if "kisi_silme_mesaji" not in st.session_state:
    st.session_state.kisi_silme_mesaji = ""

def net_calisma_gunu_hesapla(baslangic_tarihi, bitis_tarihi, izin_listesi, tatil_listesi):
    if baslangic_tarihi > bitis_tarihi:
        return 0, 0, 0, 0
    tatil_tarihleri = {datetime.datetime.strptime(t["tarih"], "%Y-%m-%d").date() for t in tatil_listesi}
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
    simdi = datetime.date.today()
    aylar = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
    gunler = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
    return f"{simdi.day} {aylar.get(simdi.month, '')} {simdi.year}, {gunler.get(simdi.weekday(), '')}"

# Giriş Ekranı
if not st.session_state.oturum_aktif:
    st.markdown("<div style='text-align: center; margin-top: 50px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="font-weight: 700; letter-spacing: -0.03em;">🍲 AZİZİYE AŞEVİ</h2>
                <p style="opacity: 0.7; font-size: 14px; margin-top: 4px; color: #d1d5db;">Saf Siyah Tasarım Sistemi & Yönetim Paneli</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("merkezi_giris_formu"):
            st.markdown("**Kullanıcı Adı**")
            k_adi_inp = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adı giriniz...", label_visibility="collapsed").strip().lower()
            st.markdown("**Şifre**")
            sifre_inp = st.text_input("Şifre", type="password", placeholder="Şifre giriniz...", label_visibility="collapsed")

            giris_tikla = st.form_submit_button("Giriş Yap", use_container_width=True)

            if giris_tikla:
                kullanici_db = st.session_state.kullanicilar
                if k_adi_inp in kullanici_db and kullanici_db[k_adi_inp]["sifre"] == sifre_inp:
                    st.session_state.oturum_aktif = True
                    st.session_state.aktif_kullanici = k_adi_inp
                    st.query_params["auth"] = "true"
                    st.query_params["user"] = k_adi_inp
                    st.success(f"{k_adi_inp.upper()} olarak giriş yapıldı!")
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")

        st.markdown("<div style='text-align: center; margin: 16px 0; opacity: 0.5; font-size: 13px;'>veya</div>", unsafe_allow_html=True)

        if st.button("👁️ Misafir Girişi İçin Tıklayın (Gözlemci)", use_container_width=True, type="secondary"):
            st.session_state.oturum_aktif = True
            st.session_state.aktif_kullanici = "misafir"
            st.query_params["auth"] = "true"
            st.query_params["user"] = "misafir"
            st.rerun()

    st.stop()

# Menü Yönetimi ve Sidebar
kullanici_adi_goruntule = st.session_state.aktif_kullanici.upper() if st.session_state.oturum_aktif else "MİSAFİR"

st.sidebar.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 12px 8px 18px 8px; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 12px;">
        <div style="background: rgba(255,255,255,0.08); color: #ffffff; width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(12px);">
            🍲
        </div>
        <div>
            <div style="font-weight: 700; font-size: 15px; color: #ffffff; letter-spacing: -0.02em;">AZİZİYE AŞEVİ</div>
            <div style="font-size: 11px; color: #9ca3af; font-weight: 500;">Yönetim & Takip Sistemi</div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div style="background: transparent; padding: 6px 8px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: rgba(255,255,255,0.06); color: white; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border: 1px solid rgba(255,255,255,0.08);">
                {kullanici_adi_goruntule[:1]}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 13.5px; color: #ffffff;">{kullanici_adi_goruntule}</div>
                <div style="font-size: 11px; color: #9ca3af;">Aktif Oturum</div>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

sidebar_arama = st.sidebar.text_input("🔍 Hızlı Arama", placeholder="Öğe veya log ara...", label_visibility="collapsed").strip().lower()

yonetici_modu = st.session_state.oturum_aktif and st.session_state.aktif_kullanici == "admin"
misafir_modu = not st.session_state.oturum_aktif or st.session_state.aktif_kullanici == "misafir"
yonetim_modu = st.session_state.oturum_aktif and st.session_state.aktif_kullanici == "yonetim"
salt_okunur_modu = misafir_modu or yonetim_modu

aktif_k_bilgi = st.session_state.kullanicilar.get(st.session_state.aktif_kullanici, {})
yasakli_menuler_listesi = aktif_k_bilgi.get("yasakli_menuler", [])

toplam_aktif_stok_sayisi = len(set(g["urun"] for g in st.session_state.girisler))
aktif_personel_sayisi = sum(1 for p in st.session_state.personeller if p.get("aktif", True))

menu_gruplari = {
    "🏠 Genel Bakış": [("Kurumsal Dashboard & Özet", "")],
    "📦 Depo & Stok Yönetimi": [
        ("Güncel Stok Durumu", str(toplam_aktif_stok_sayisi)),
        ("Yeni Mal Alımı / Fatura Ekle", ""),
        ("Ürün Sil / Düzenle", ""),
        ("Fire / Zayiat Girişi", ""),
        ("Ürün Birim Fiyatları & Ay Analizi", ""),
    ],
    "🍲 Üretim & Mutfak": [
        ("Günlük Yemek Üretimi & Maliyet Raporu", ""),
        ("Kalori Hesaplama Aracı", ""),
    ],
    "👥 Sosyal & İnsan Kaynakları": [
        ("İhtiyaç Sahibi & Yemek Dağıtım Takibi", str(len(st.session_state.ihtiyac_sahipleri))),
        ("Personel & Çalışma Süresi Takibi", str(aktif_personel_sayisi)),
    ],
    "📈 Raporlar & Arşiv": [("Kullanım Takibi", "")],
}

if yonetici_modu:
    menu_gruplari["⚙️ Sistem Ayarları"] = [("Kullanıcı Ayarları", str(len(st.session_state.kullanicilar)))]

for grup_adi, alt_menuler in menu_gruplari.items():
    grup_aktif_mu = any(st.session_state.aktif_menu == m for m, _ in alt_menuler)
    with st.sidebar.expander(grup_adi, expanded=grup_aktif_mu or bool(sidebar_arama)):
        for m, badge in alt_menuler:
            if m == "Yeni Mal Alımı / Fatura Ekle" and salt_okunur_modu:
                continue
            btn_label = f"{m}  [{badge}]" if badge and badge != "0" else m
            btn_type = "primary" if st.session_state.aktif_menu == m else "secondary"
            if st.button(btn_label, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"):
                st.session_state.aktif_menu = m
                st.query_params["menu"] = m
                st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("Oturumu Kapat", use_container_width=True, type="secondary"):
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.query_params.clear()
    st.rerun()

# Ana Akış Yönlendirmesi
menu = st.session_state.aktif_menu

if not yonetici_modu and menu in yasakli_menuler_listesi:
    st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    st.stop()

st.markdown(f"### 🍲 AZİZİYE - AŞEVİ TAKİP EKRANI (Saf Siyah Pro)")
st.markdown(f"**Hoş geldiniz** &nbsp;|&nbsp; 📅 {bugunun_turkce_tarihi()}")
st.markdown("---")

if menu == "Kurumsal Dashboard & Özet":
    st.success("Sistem güvenli, optimize edilmiş ve performanslı önbellek mimarisiyle çalışmaktadır.")
    st.info("Diğer menülere sol kenar çubuğundan geçiş yapabilirsiniz.")
else:
    st.info(f"Seçilen aktif çalışma alanı: **{menu}**")
