import datetime
import hashlib
import io
import json
import os
import time
import difflib
import zoneinfo
import requests
from cryptography.fernet import Fernet
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Aziziye - Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide",
)

# Şifreleme Anahtarı ve Motoru
try:
    gizli_anahtar = st.secrets["FERNET_KEY"].encode("utf-8")
    fernet_motoru = Fernet(gizli_anahtar)
except Exception:
    fernet_motoru = Fernet(Fernet.generate_key())


def metni_sifrele(duz_metin):
    if not duz_metin:
        return ""
    try:
        return fernet_motoru.encrypt(str(duz_metin).encode("utf-8")).decode("utf-8")
    except Exception:
        return str(duz_metin)


def metni_coz(sifreli_metin):
    if not sifreli_metin:
        return ""
    try:
        if not str(sifreli_metin).startswith("gAAAAA"):
            return str(sifreli_metin)
        return fernet_motoru.decrypt(str(sifreli_metin).encode("utf-8")).decode(
            "utf-8"
        )
    except Exception:
        return str(sifreli_metin)


def sifre_hashle(sifre):
    """Şifreleri SHA-256 ile güvenli bir şekilde hashler."""
    if not sifre:
        return ""
    return hashlib.sha256(str(sifre).encode("utf-8")).hexdigest()


def simdi_tr_str(format_str="%Y-%m-%d %H:%M"):
    """Gerçek Türkiye saatini (Europe/Istanbul) döndürür."""
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).strftime(format_str)
    except Exception:
        return datetime.datetime.now().strftime(format_str)


# =========================================================================
# SUPABASE BULUT VERİTABANI BAĞLANTI FONKSİYONLARI
# =========================================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

def supabase_veri_oku(kayit_id, varsayilan_deger):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return varsayilan_deger
    url = f"{SUPABASE_URL}/rest/v1/asevi_veritabani?id=eq.{kayit_id}&select=veri"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get("veri", varsayilan_deger)
    except Exception:
        pass
    return varsayilan_deger

def supabase_veri_kaydet(kayit_id, veri_objesi):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/asevi_veritabani"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    payload = {
        "id": kayit_id,
        "veri": veri_objesi
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=5)
    except Exception:
        pass


# Tema Durumu Yönetimi
query_params = st.query_params

if "tema" not in st.session_state:
    if "theme" in query_params and query_params["theme"] in ["Dark", "Light"]:
        st.session_state.tema = query_params["theme"]
    else:
        st.session_state.tema = "Dark"

# Tema Renk Paletleri
if st.session_state.tema == "Dark":
    bg_color = "#000000"
    card_bg = "#090909"
    sidebar_bg = "#000000"
    text_color = "#ffffff"
    subtext_color = "#9ca3af"
    border_color = "#1f1f1f"
    input_bg = "#0b0b0b"
    table_hover = "rgba(255, 255, 255, 0.03)"
    popover_bg = "#121212"
    plotly_template = "plotly_dark"
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    sidebar_bg = "#f1f5f9"
    text_color = "#0f172a"
    subtext_color = "#64748b"
    border_color = "#cbd5e1"
    input_bg = "#ffffff"
    table_hover = "rgba(0, 0, 0, 0.02)"
    popover_bg = "#ffffff"
    plotly_template = "plotly_white"

# DİNAMİK TEMA STİLLERİ
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    .main, .stApp {{ 
        background-color: {bg_color} !important; 
        color: {text_color} !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }}
    
    .stSidebar {{ 
        background-color: {sidebar_bg} !important; 
        padding-top: 10px; 
        border-right: 1px solid {border_color} !important;
    }}
    .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div {{ 
        color: {subtext_color} !important; 
        font-size: 13.5px; 
    }}
    
    section[data-testid="stSidebar"] div[data-testid="stExpander"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        margin-bottom: -50px;
    }}
    
    section[data-testid="stSidebar"] div.stButton > button {{
        background: transparent !important;
        color: {subtext_color} !important;
        border: none !important;
        border-radius: 12px !important;
        text-align: left !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 9px 14px !important;
    }}
    
    section[data-testid="stSidebar"] div.stButton > button:hover {{
        background: rgba(99, 102, 241, 0.08) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        color: {text_color} !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.15) !important;
        transform: translateX(5px);
    }}
    
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
        background: rgba(99, 102, 241, 0.15) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        color: {text_color} !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        font-weight: 600 !important;
    }}

    h1, h2, h3, h4, h5, h6 {{ 
        color: {text_color} !important; 
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
    }}
    p, span, label, div, .stMarkdown {{ 
        color: {text_color} !important; 
    }}
    button[kind="header"] svg, [data-testid="collapsedControl"] span, [data-testid="collapsedControl"] div {{ display: none !important; }}
    section[data-testid="stSidebar"] [data-testid="baseButton-header"] {{ color: transparent !important; }}

    div.stButton > button, button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"], div.stFormSubmitButton > button {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 13.5px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    div.stButton > button:hover, button[data-testid="baseButton-secondary"]:hover, button[data-testid="baseButton-primary"]:hover, div.stFormSubmitButton > button:hover {{
        border-color: #6366f1 !important;
        transform: translateY(-1px);
    }}

    div.stMetric, div[data-testid="stExpander"], div.stForm {{
        background: {card_bg} !important;
        border: 1px solid {border_color};
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 12px 30px -8px rgba(0, 0, 0, 0.12);
        color: {text_color} !important;
    }}
    
    div[data-baseweb="menu"], 
    ul[role="listbox"], 
    div[data-baseweb="popover"], 
    div[data-baseweb="calendar"],
    div[data-baseweb="select"] ul,
    div[id*="popover"],
    div[class*="popover"] {{
        background-color: {popover_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2) !important;
        border-radius: 12px !important;
    }}

    li[role="option"], 
    li[role="option"] div, 
    li[role="option"] span,
    div[data-baseweb="menu"] div {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    li[role="option"]:hover, 
    li[role="option"]:hover div, 
    li[role="option"]:hover span {{
        background-color: rgba(99, 102, 241, 0.15) !important;
        color: {text_color} !important;
    }}
    li[role="option"][aria-selected="true"] {{
        background-color: rgba(99, 102, 241, 0.3) !important;
        color: {text_color} !important;
    }}

    div[data-baseweb="calendar"] *, 
    div[data-baseweb="calendar"] div, 
    div[data-baseweb="calendar"] span, 
    div[data-baseweb="calendar"] button {{
        color: {text_color} !important;
        background-color: transparent !important;
    }}
    div[data-baseweb="calendar"] button:hover {{
        background-color: rgba(99, 102, 241, 0.2) !important;
        border-radius: 50% !important;
    }}

    input, 
    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"] {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border-radius: 12px !important;
        border-color: {border_color} !important;
    }}
    
    input::placeholder {{
        color: {subtext_color} !important;
        opacity: 0.7;
    }}

    .custom-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin-top: 15px;
        margin-bottom: 15px;
        background-color: {card_bg};
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {border_color};
    }}
    .custom-table th {{
        background-color: {sidebar_bg};
        color: {text_color};
        padding: 14px 18px;
        text-align: left;
        font-size: 13px;
        font-weight: 600;
        border-bottom: 1px solid {border_color};
    }}
    .custom-table td {{
        padding: 14px 18px;
        color: {subtext_color};
        font-size: 13px;
        border-bottom: 1px solid {border_color};
    }}
    .custom-table tr:hover {{
        background-color: {table_hover};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


KALORI_TABLOSU = {
    "PİRİNÇ": 130,
    "BALDO PİRİNÇ": 130,
    "KURU FASULYE": 340,
    "NOHUT": 360,
    "KIRMIZI MERCİMEK": 350,
    "YEŞİL MERCİMEK": 350,
    "BULGUR": 340,
    "PİLAVLIK BULGUR": 340,
    "MAKARNA": 350,
    "BURGU MAKARNA": 350,
    "İNCE UZUN MAKARNA": 350,
    "ERİŞTE MAKARNA": 360,
    "ARPA ŞEHRİYE": 350,
    "UN": 364,
    "PATATES": 77,
    "SOĞAN": 40,
    "DOMATES": 18,
    "SALATALIK": 15,
    "BİBER": 40,
    "ÇARLİ": 40,
    "KAPYA BİBER": 31,
    "ISPANAK": 23,
    "PATLICAN": 25,
    "KABAK": 17,
    "HAVUÇ": 41,
    "LAHANA": 25,
    "KIRMIZI LAHANA": 31,
    "MAYDANOZ": 36,
    "ET": 250,
    "KUŞBAŞI ET": 250,
    "TAVUK": 165,
    "SIRTSIZ GÖĞÜS": 165,
    "YUMURTA": 155,
    "YOĞURT": 61,
    "TAM YAĞLI YOĞURT": 61,
    "SÜT": 42,
    "YAĞLI SÜT": 42,
    "TEREYAĞI": 717,
    "AYÇİÇEK YAĞI": 884,
    "TENEKE AYÇİÇEK YAĞI": 884,
    "SALÇA": 82,
    "DOMATES SALÇASI": 82,
    "ŞEKER": 387,
    "TOZ ŞEKER": 387,
    "TUZ": 0,
    "İRMİK": 360,
    "BEZELYE": 81,
    "BEZELYE KONSERVESİ": 81,
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


varsayilan_personeller = [
    {
        "tc": "11111111111",
        "ad_soyad": "MUHAMMED İLKER ÇELİK",
        "gorev": "Şoför",
        "baslama": "2026-10-12",
        "aktif": True,
        "izinler": [],
    },
]

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

varsayilan_kullanicilar = {
    "admin": {"sifre": sifre_hashle("Ss123321"), "tip": "admin", "yasakli_menuler": [], "maskeli_alanlar": [], "salt_okunur": False},
    "asci": {"sifre": sifre_hashle("sydv25"), "tip": "personel", "yasakli_menuler": [], "maskeli_alanlar": [], "salt_okunur": False},
    "yonetim": {"sifre": sifre_hashle("Yonetim25"), "tip": "personel", "yasakli_menuler": [], "maskeli_alanlar": [], "salt_okunur": True},
    "misafir": {
        "sifre": "", 
        "tip": "misafir", 
        "yasakli_menuler": misafir_yasaklar_varsayilan, 
        "maskeli_alanlar": misafir_maskeler_varsayilan, 
        "salt_okunur": True,
        "buton_metni": "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)",
        "buton_aktif": True
    },
}

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
    data = supabase_veri_oku("kullanici_yetkileri", varsayilan_kullanicilar)
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

        if v.get("sifre") and len(v["sifre"]) != 64 and k != "misafir":
            v["sifre"] = sifre_hashle(v["sifre"])
    
    if "misafir" not in data:
        data["misafir"] = varsayilan_kullanicilar["misafir"]
    else:
        if "buton_metni" not in data["misafir"]:
            data["misafir"]["buton_metni"] = "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)"
        if "buton_aktif" not in data["misafir"]:
            data["misafir"]["buton_aktif"] = True
        if not data["misafir"]["yasakli_menuler"]:
            data["misafir"]["yasakli_menuler"] = misafir_yasaklar_varsayilan
        if not data["misafir"]["maskeli_alanlar"]:
            data["misafir"]["maskeli_alanlar"] = misafir_maskeler_varsayilan

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
    sifrelenmis_liste = []
    for k in veri_listesi:
        k_kopya = k.copy()
        k_kopya["tc_hane"] = metni_sifrele(k.get("tc_hane", ""))
        k_kopya["telefon"] = metni_sifrele(k.get("telefon", ""))
        k_kopya["adres"] = metni_sifrele(k.get("adres", ""))
        sifrelenmis_liste.append(k_kopya)
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
    sifrelenmis_p = []
    for p in veri_listesi:
        p_kopya = p.copy()
        p_kopya["tc"] = metni_sifrele(p.get("tc", ""))
        sifrelenmis_p.append(p_kopya)
    supabase_veri_kaydet("personeller", sifrelenmis_p)


def resmi_tatilleri_yukle():
    return supabase_veri_oku("resmi_tatiller", varsayilan_resmi_tatiller)


def yemek_uretim_arsivini_yukle():
    return supabase_veri_oku("yemek_uretim_arsivi", [])


def yemek_uretim_arsivini_kaydet(veri):
    supabase_veri_kaydet("yemek_uretim_arsivi", veri)


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
if "depolar" not in st.session_state:
    st.session_state.depolar = depoları_yukle()
if "demirbaslar" not in st.session_state:
    st.session_state.demirbaslar = demirbasları_yukle()
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

if "hatali_giris_sayisi" not in st.session_state:
    st.session_state.hatali_giris_sayisi = 0
if "kilitlenme_bitis_zamani" not in st.session_state:
    st.session_state.kilitlenme_bitis_zamani = 0

query_params = st.query_params

if "oturum_aktif" not in st.session_state:
    if "auth" in query_params and query_params["auth"] == "true" and "user" in query_params:
        st.session_state.oturum_aktif = True
        st.session_state.aktif_kullanici = query_params["user"]
    else:
        st.session_state.oturum_aktif = False
        st.session_state.aktif_kullanici = "misafir"

gecerli_menuler = [
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu",
    "Yeni Mal Alımı / Fatura Ekle",
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
    st.markdown(
        "<div style='text-align: center; margin-top: 40px;'></div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown(
            f"""
                <div style="text-align: center; margin-bottom: 28px; background: {card_bg}; border: 1px solid {border_color}; padding: 32px; border-radius: 20px; box-shadow: 0 16px 40px rgba(0,0,0,0.08);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🍲</div>
                    <h2 style="font-weight: 700; letter-spacing: -0.03em; margin: 0; color: {text_color};">AZİZİYE AŞEVİ</h2>
                    <p style="opacity: 0.6; font-size: 13.5px; margin-top: 6px; color: {subtext_color};">Yönetim & Takip Sistemi</p>
                </div>
            """,
            unsafe_allow_html=True,
        )

        simdikiekran_zaman = time.time()
        kilitli_mi = st.session_state.kilitlenme_bitis_zamani > simdikiekran_zaman

        if kilitli_mi:
            kalan_sure = int(st.session_state.kilitlenme_bitis_zamani - simdikiekran_zaman)
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
                    girilen_sifre_hash = sifre_hashle(sifre_inp)

                    if (
                        k_adi_inp in kullanici_db
                        and kullanici_db[k_adi_inp]["sifre"] == girilen_sifre_hash
                    ):
                        st.session_state.hatali_giris_sayisi = 0
                        st.session_state.oturum_aktif = True
                        st.session_state.aktif_kullanici = k_adi_inp
                        st.query_params["auth"] = "true"
                        st.query_params["user"] = k_adi_inp
                        st.success(f"{k_adi_inp.upper()} olarak giriş yapıldı!")
                        st.rerun()
                    else:
                        st.session_state.hatali_giris_sayisi += 1
                        kalan_hak = 3 - st.session_state.hatali_giris_sayisi
                        if st.session_state.hatali_giris_sayisi >= 3:
                            st.session_state.kilitlenme_bitis_zamani = time.time() + 30
                            st.session_state.hatali_giris_sayisi = 0
                            st.error("⚠️ 3 kez hatalı şifre girdiniz. Sistem 30 saniye kilitlendi!")
                            st.rerun()
                        else:
                            st.error(f"Hatalı kullanıcı adı veya şifre! Kalan deneme hakkı: {kalan_hak}")

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
                st.session_state.oturum_aktif = True
                st.session_state.aktif_kullanici = "misafir"
                st.query_params["auth"] = "true"
                st.query_params["user"] = "misafir"
                st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        with st.expander("🔑 Admin Şifre Kurtarma (Master Key)"):
            with st.form("master_key_sifre_sifirla"):
                st.markdown("Şifrenizi unuttuysanız sistem kurtarma anahtarı ile admin şifresini sıfırlayabilirsiniz.")
                master_key_inp = st.text_input("Kurtarma Anahtarı (Master Recovery Key)", type="password")
                sifirla_btn = st.form_submit_button("Admin Şifresini Fabrika Ayarına Döndür")

                if sifirla_btn:
                    tanimli_master = st.secrets.get("MASTER_RECOVERY_KEY", "aziziye_master_2026")
                    if master_key_inp == tanimli_master:
                        if "admin" in st.session_state.kullanicilar:
                            st.session_state.kullanicilar["admin"]["sifre"] = sifre_hashle("Ss123321")
                            kullanıcıları_kaydet(st.session_state.kullanicilar)
                            st.success("Başarılı! Admin şifresi 'Ss123321' olarak sıfırlandı. Şimdi giriş yapabilirsiniz.")
                        else:
                            st.error("Admin kullanıcısı veritabanında bulunamadı.")
                    else:
                        st.error("Hatalı Kurtarma Anahtarı!")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button(
            "✉️ İletişim / Destek", use_container_width=True, type="secondary"
        ):
            st.info("📩 İletişim için **sefaunaltopcu@gmail.com** mail adresi ile iletişime geçebilirsiniz.")

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

st.sidebar.markdown(f'<p style="font-size: 11px; font-weight: 700; margin-bottom: 6px; padding-left: 4px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; color: {subtext_color};">GÖRÜNÜM MODU</p>', unsafe_allow_html=True)
yeni_tema = st.sidebar.radio(
    "Tema Seçimi", 
    ["Dark (Koyu)", "Light (Açık)"], 
    index=0 if st.session_state.tema == "Dark" else 1,
    label_visibility="collapsed",
    horizontal=True
)
secilen_tema_val = "Dark" if "Dark" in yeni_tema else "Light"
if secilen_tema_val != st.session_state.tema:
    st.session_state.tema = secilen_tema_val
    st.query_params["theme"] = secilen_tema_val
    st.rerun()

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
            or sidebar_arama in m.lower()
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

            btn_label = f"{m}  [{badge}]" if badge and badge != "0" else m
            btn_type = (
                "primary" if st.session_state.aktif_menu == m else "secondary"
            )
            if st.button(
                btn_label, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"
            ):
                st.session_state.aktif_menu = m
                st.query_params["menu"] = m
                st.rerun()

st.sidebar.markdown("<div style='margin-top: 150px;'></div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button(
    "Oturumu Kapat", use_container_width=True, type="secondary"
):
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<p style="font-size: 11px; text-align: center; opacity: 0.5; color: {subtext_color};">sefautopcu</p>',
    unsafe_allow_html=True,
)


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
        <title>{baslik}</title>
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
        <h2>{baslik}</h2>
        <p>Rapor Tarihi ve Saati: {tr_zaman}</p>
        <hr style="border: 0; border-top: 1px solid {border_color};"/>
    """
    if veri_listesi:
        headers = list(veri_listesi[0].keys())
        html += "<table><tr>"
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr>"
        for item in veri_listesi:
            html += "<tr>"
            for h in headers:
                html += f"<td>{item.get(h, '')}</td>"
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
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"
    
    for row in veri_listesi:
        html += "<tr>"
        for h in headers:
            html += f"<td>{row.get(h, '')}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


menu = st.session_state.aktif_menu

if not yonetici_modu and menu in yasakli_menuler_listesi:
    st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    st.stop()

# 0. KURUMSAL DASHBOARD & ÖZET
if menu == "Kurumsal Dashboard & Özet":
    toplam_stok_kalemi = len(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
    toplam_envanter_maliyeti = sum(
        g.get("kalan", 0) * g.get("fiyat", 0) for g in st.session_state.girisler
    )

    loglar = st.session_state.kullanim_loglari
    toplam_fire_mik = sum(
        l.get("miktar", 0) for l in loglar if l.get("tur") == "Fire/Zayiat"
    )
    toplam_fire_tutar = sum(l.get("tutar", 0) for l in loglar if l.get("tur") == "Fire/Zayiat")
    aktif_calisan_personel_sayisi = sum(
        1 for p in st.session_state.personeller if p.get("aktif", True)
    )

    m_urun_cesidi = "🔒 Gizli" if "1. Sayfa: Ürün Çeşidi" in aktif_k_maskeleri else f"{toplam_stok_kalemi} <span style='font-size: 13px; font-weight: normal; color: {subtext_color};'>Çeşit</span>"
    m_toplam_fire = "🔒 Gizli" if "1. Sayfa: Toplam Fire" in aktif_k_maskeleri else f"{toplam_fire_mik:,.1f} <span style='font-size: 13px; font-weight: normal; color: {subtext_color};'>Kg</span>"
    stok_formatli = f"{toplam_envanter_maliyeti:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    m_stok_degeri = "🔒 Gizli" if "1. Sayfa: Stok Değeri" in aktif_k_maskeleri else f"{stok_formatli} <span style='font-size: 13px; font-weight: normal; color: {subtext_color};'>₺</span>"
    m_aktif_personel = "🔒 Gizli" if "1. Sayfa: Aktif Personel" in aktif_k_maskeleri else f"{aktif_calisan_personel_sayisi} <span style='font-size: 13px; font-weight: normal; color: {subtext_color};'>Kişi</span>"

    st.markdown(
        f"""
        <style>
        .dashboard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: {card_bg};
            border: 1px solid {border_color};
            padding: 28px 36px;
            border-radius: 20px;
            margin-bottom: 24px;
            box-shadow: 0 12px 30px -8px rgba(0, 0, 0, 0.08);
        }}
        .metric-card {{
            background: {card_bg};
            border: 1px solid {border_color};
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .metric-card:hover {{
            border-color: #6366f1;
            transform: translateY(-2px);
        }}
        </style>

        <div class="dashboard-header">
            <div>
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: {text_color};">Genel Bakış & Operasyonel Özet</h1>
                <p style="margin: 6px 0 0 0; color: {subtext_color}; font-size: 14px;">Aziziye Aşevi Yönetim Paneli</p>
            </div>
            <div style="background: rgba(99, 102, 241, 0.12); color: #6366f1; border: 1px solid rgba(99, 102, 241, 0.3); padding: 8px 16px; border-radius: 12px; font-weight: 600; font-size: 12px; backdrop-filter: blur(12px);">
                ● sefautopcu
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div>
                    <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Ürün Çeşidi</div>
                    <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{m_urun_cesidi}</div>
                </div>
                <div style="color: {subtext_color}; font-size: 12px;">📦 Aktif Envanter</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    with c2:
        if misafir_modu:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div>
                        <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Toplam Fire / Zayiat</div>
                        <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">Gizli</div>
                    </div>
                    <div style="color: {subtext_color}; font-size: 12px;">Yetkisiz Görünüm</div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            zarar_gosterim_metin = "🔒 Gizli" if "1. Sayfa: Toplam Fire" in aktif_k_maskeleri else f"{toplam_fire_tutar:,.0f} ₺"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div>
                        <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Toplam Fire</div>
                        <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{m_toplam_fire}</div>
                    </div>
                    <div style="color: #ef4444; font-size: 12px; font-weight: 600;">Zarar: {zarar_gosterim_metin}</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

    with c3:
        if misafir_modu:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div>
                        <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Toplam Stok Değeri</div>
                        <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">Gizli</div>
                    </div>
                    <div style="color: {subtext_color}; font-size: 12px;">Yetkisiz Görünüm</div>
                </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div>
                        <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Stok Değeri</div>
                        <div style="color: {text_color}; font-size: 24px; font-weight: 700; margin-top: 8px;">{m_stok_degeri}</div>
                    </div>
                    <div style="color: #10b981; font-size: 12px; font-weight: 600;">💰 Güncel Maliyet</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div>
                    <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Aktif Personel</div>
                    <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{m_aktif_personel}</div>
                </div>
                <div style="color: #a855f7; font-size: 12px; font-weight: 600;">👥 Kadro Durumu</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<h3 style='font-size: 16px; font-weight: 700; color: {text_color}; margin-bottom: 16px;'>⚡ Hızlı İşlem Kısayolları</h3>",
        unsafe_allow_html=True,
    )

    q1, q2, q3 = st.columns(3)
    with q1:
        if not misafir_modu:
            if st.button("📦 Güncel Stok Durumuna Git", use_container_width=True):
                st.session_state.aktif_menu = "Güncel Stok Durumu"
                st.query_params["menu"] = "Güncel Stok Durumu"
                st.rerun()
        else:
            st.button("📦 Stok Durumu (Kısıtlı)", use_container_width=True, disabled=True)
    with q2:
        if st.button("🍲 Günlük Yemek Üretimi Yap", use_container_width=True):
            st.session_state.aktif_menu = "Günlük Yemek Üretimi & Maliyet Raporu"
            st.query_params["menu"] = "Günlük Yemek Üretimi & Maliyet Raporu"
            st.rerun()
    with q3:
        if st.button("🔥 Kalori Hesaplama Aracı", use_container_width=True):
            st.session_state.aktif_menu = "Kalori Hesaplama Aracı"
            st.query_params["menu"] = "Kalori Hesaplama Aracı"
            st.rerun()

    st.markdown("---")
    st.markdown(
        f"<h3 style='font-size: 18px; font-weight: 700; color: {text_color}; margin-top: 20px;'>📊 İnteraktif Dashboard Grafikleri ve Widget Alanı</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color: {subtext_color}; font-size: 13.5px;'>Aşağıda etkinleştirilmiş olan EasyUI tarzı modern, cam efektli ve akışkan grafikler görüntülenmektedir.</p>",
        unsafe_allow_html=True,
    )

    if "1. Sayfa: Grafik Alanı" in aktif_k_maskeleri:
        st.info("🔒 Dashboard grafik alanı bu kullanıcı için maskelenmiştir (gizlenmiştir).")
    else:
        aktif_w_list = [
            w for w in st.session_state.dashboard_widgets if w.get("aktif", True)
        ]
        if aktif_w_list:
            for w in aktif_w_list:
                st.markdown(
                    f"<div style='border: 1px solid {border_color}; background: {card_bg}; padding: 24px; border-radius: 18px; margin-bottom: 24px; box-shadow: 0 12px 30px -8px rgba(0,0,0,0.08);'>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"#### {w['baslik']}")

                easyui_colors = ["#6366f1", "#10b981", "#a855f7", "#ef4444", "#3b82f6", "#f59e0b"]

                if w["tur"] == "Sütun Grafik":
                    if st.session_state.girisler:
                        df_stok = pd.DataFrame(st.session_state.girisler)
                        if (
                            not df_stok.empty
                            and "kategori" in df_stok.columns
                            and "kalan" in df_stok.columns
                        ):
                            fig = px.bar(
                                df_stok,
                                x="kategori",
                                y="kalan",
                                color="kategori",
                                template=plotly_template,
                                color_discrete_sequence=easyui_colors,
                            )
                            fig.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="Plus Jakarta Sans", color=subtext_color, size=12),
                                margin=dict(l=20, r=20, t=30, b=20),
                                xaxis=dict(showgrid=False, linecolor=border_color),
                                yaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", linecolor=border_color),
                                legend=dict(bgcolor=card_bg, bordercolor=border_color, borderwidth=1)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Grafik için yeterli veri bulunmuyor.")
                elif w["tur"] == "Çizgi Grafik":
                    if st.session_state.kullanim_loglari:
                        df_log = pd.DataFrame(st.session_state.kullanim_loglari)
                        if (
                            not df_log.empty
                            and "tarih" in df_log.columns
                            and "tutar" in df_log.columns
                        ):
                            fig2 = px.line(
                                df_log,
                                x="tarih",
                                y="tutar",
                                template=plotly_template,
                                color_discrete_sequence=["#6366f1"],
                            )
                            fig2.update_traces(line=dict(width=3, shape="spline"))
                            fig2.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="Plus Jakarta Sans", color=subtext_color, size=12),
                                margin=dict(l=20, r=20, t=30, b=20),
                                xaxis=dict(showgrid=False, linecolor=border_color),
                                yaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.1)", linecolor=border_color),
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("Trend grafiği için yeterli log kaydı bulunmuyor.")
                elif w["tur"] == "Pasta Grafik (Dağılım)":
                    if st.session_state.girisler:
                        df_giris = pd.DataFrame(st.session_state.girisler)
                        fig3 = px.pie(
                            df_giris,
                            names="urun",
                            values="kalan",
                            template=plotly_template,
                            color_discrete_sequence=easyui_colors,
                        )
                        fig3.update_layout(
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="Plus Jakarta Sans", color=subtext_color, size=12),
                            margin=dict(l=20, r=20, t=30, b=20),
                            legend=dict(bgcolor=card_bg, bordercolor=border_color, borderwidth=1)
                        )
                        fig3.update_traces(textinfo="percent+label", marker=dict(line=dict(color=card_bg, width=2)))
                        st.plotly_chart(fig3, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Görüntülenecek aktif grafik widget'ı bulunmuyor.")

    if yonetici_modu:
        with st.expander(
            "➕ Admin Özel: Dashboard'a Yeni Grafik / Widget Ekle veya Kaldır",
            expanded=False,
        ):
            with st.form("yeni_widget_ekle_form"):
                st.markdown("**Dashboard'a Yeni Grafik Ekle**")
                w_baslik = st.text_input("Grafik Başlığı", "Örn: Depo Doluluk Oranı")
                w_tur = st.selectbox(
                    "Grafik Türü",
                    ["Sütun Grafik", "Çizgi Grafik", "Pasta Grafik (Dağılım)"],
                )
                w_ekle_btn = st.form_submit_button("Grafik Widget'ını Ekle")

                if w_ekle_btn and w_baslik:
                    st.session_state.dashboard_widgets.append({
                        "id": f"w-{len(st.session_state.dashboard_widgets)+1}",
                        "baslik": w_baslik,
                        "tur": w_tur,
                        "aktif": True,
                    })
                    widgetlari_kaydet(st.session_state.dashboard_widgets)
                    st.success("Yeni grafik başarıyla eklendi!")
                    st.balloons()
                    st.rerun()

            st.markdown("---")
            with st.form("widget_sil_form"):
                st.markdown("**🗑️ Mevcut Grafik Widget'ını Kaldır**")
                if st.session_state.dashboard_widgets:
                    w_secenekleri = [
                        f"{w['id']} - {w['baslik']} ({w['tur']})"
                        for w in st.session_state.dashboard_widgets
                    ]
                    secilen_w_sil = st.selectbox(
                        "Kaldırılacak Grafiği Seçin", w_secenekleri
                    )
                    w_sil_btn = st.form_submit_button(
                        "Seçilen Grafiği Kaldır", type="primary"
                    )

                    if w_sil_btn:
                        wid = secilen_w_sil.split(" - ")[0]
                        st.session_state.dashboard_widgets = [
                            w
                            for w in st.session_state.dashboard_widgets
                            if w["id"] != wid
                        ]
                        widgetlari_kaydet(st.session_state.dashboard_widgets)
                        st.success("Grafik widget'ı kaldırıldı!")
                        st.balloons()
                        st.rerun()
                else:
                    st.info("Kaldırılacak grafik bulunmuyor.")
    else:
        st.markdown(
            f"<p style='font-size: 12px; color: {subtext_color}; font-style: italic;'>🔒 Dashboard sayfasına yeni grafik ekleme / kaldırma yetkisi yalnızca <b>Admin</b> kullanıcısına özeldir.</p>",
            unsafe_allow_html=True,
        )

# 1. GÜNCEL STOK DURUMU
elif menu == "Güncel Stok Durumu":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_baslik, col_indir_alan = st.columns([2, 2])
        with col_baslik:
            st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")

        benzersiz_urunler_Excel = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )
        excel_liste = []
        for u in benzersiz_urunler_Excel:
            toplam_kalan_ex = sum(
                g.get("kalan", 0) for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u
            )
            kategori_ex = next(
                (g.get("kategori", "GENEL") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "GENEL",
            )
            birim_ex = next(
                (g.get("birim", "Kg") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Kg",
            )
            depo_ex = next(
                (g.get("depo", "Merkez Depo") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Merkez Depo",
            )
            islem_yapan_ex = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                "admin",
            )
            en_son_tarih_ex = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                default="-",
            )
            
            gosterilen_kalan_excel = "🔒 Gizli" if "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri else toplam_kalan_ex
            
            excel_liste.append({
                "Ürün Adı": u,
                "Kategori": kategori_ex,
                "Birim": birim_ex,
                "Kalan Miktar": gosterilen_kalan_excel,
                "Depo Yeri": depo_ex,
                "Eklenme/Güncelleme Tarihi": en_son_tarih_ex,
                "Son İşlemi Yapan": islem_yapan_ex,
            })

        excel_data = tablo_to_excel_bytes(
            excel_liste, "Aziziye Aşevi - Güncel Stok Raporu"
        )
        pdf_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Güncel Stok Raporu", excel_liste
        )

        with col_indir_alan:
            ortak_indirme_alani(
                excel_data, pdf_data, "asevi_guncel_stok_raporu", "stok_sayfasi"
            )

        depolar = ["Tümü"] + st.session_state.depolar
        secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)

        benzersiz_urunler = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )
        stok_tablosu = []
        kritik_urunler_tablosu = []
        
        for u in benzersiz_urunler:
            toplam_kalan = sum(
                g.get("kalan", 0) for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u
            )
            kategori = next(
                (g.get("kategori", "GENEL") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "GENEL",
            )
            birim = next(
                (g.get("birim", "Kg") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Kg",
            )
            depo = next(
                (g.get("depo", "Merkez Depo") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Merkez Depo",
            )
            islem_yapan = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                "admin",
            )
            en_son_tarih = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                default="-",
            )

            final_kalan_gosterim = "🔒 Gizli" if "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri else toplam_kalan

            if secilen_depo == "Tümü" or depo == secilen_depo:
                stok_tablosu.append({
                    "Ürün Adı": u,
                    "Kategori": kategori,
                    "Birim": birim,
                    "Kalan Miktar": final_kalan_gosterim,
                    "Depo Yeri": depo,
                    "Eklenme Tarihi": en_son_tarih,
                    "İşlemi Yapan": islem_yapan,
                })

            ozel_kritik_sinir = st.session_state.kritik_seviyeler.get(u, 10.0)
            if toplam_kalan <= float(ozel_kritik_sinir) and "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" not in aktif_k_maskeleri:
                kritik_urunler_tablosu.append({
                    "Ürün Adı": u,
                    "Kalan Miktar": f"{toplam_kalan} {birim}",
                    "Kritik Eşik Sınırı": f"{ozel_kritik_sinir} {birim}",
                    "Depo Yeri": depo
                })

        st.markdown("### Envanter Listesi")
        ozel_html_tablo_goster(stok_tablosu)

        st.markdown("---")
        st.markdown("### ⚠️ Kritik Seviyenin Altındaki veya Tükenen Ürünler Tablosu")
        if kritik_urunler_tablosu:
            ozel_html_tablo_goster(kritik_urunler_tablosu)
        else:
            st.success("Tebrikler! Kritik seviyenin altında ürün bulunmuyor.")

        with st.expander("⚙️ Ürün Bazlı Kritik Eşik Sınırı Belirle"):
            with st.form("kritik_ayar_form"):
                secilen_k_urun = st.selectbox("Kritik Eşiği Değiştirilecek Ürün", benzersiz_urunler if benzersiz_urunler else ["Yok"])
                mevcut_esin = st.session_state.kritik_seviyeler.get(secilen_k_urun, 10.0)
                yeni_esin_deger = st.number_input("Kritik Miktar Sınırı", min_value=0.0, value=float(mevcut_esin), step=1.0)
                kritik_kaydet_btn = st.form_submit_button("Kritik Eşiği Güncelle", type="primary")

                if kritik_kaydet_btn and secilen_k_urun != "Yok":
                    st.session_state.kritik_seviyeler[secilen_k_urun] = yeni_esin_deger
                    kritik_seviyeleri_kaydet(st.session_state.kritik_seviyeler)
                    st.success("🎉 Başarılı! Kritik sınır güncellendi.")
                    st.balloons()
                    st.rerun()

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    if salt_okunur_modu:
        st.warning(
            "⚠️ Bu sayfaya yalnızca gözlem amaçlı erişebilirsiniz. Salt okunur (Yönetim/Misafir) modda işlem yapamazsınız."
        )
    else:
        st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
        st.markdown("Her yeni mal alımı ayrı bir kayıt olarak depoya eklenir; böylece aynı ürün eklendiğinde stoğunuz artar ve geçmiş alım fiyatlarınız/tarihçeniz korunur.")
        with st.form("fatura_formu"):
            fatura_tarihi_secim = st.date_input("📅 Fatura / Alım Tarihi", value=datetime.date.today())
            fatura_saati_secim = st.time_input("⏰ Alım Saati", value=datetime.datetime.now().time())
            tarih_giris = f"{fatura_tarihi_secim.strftime('%Y-%m-%d')} {fatura_saati_secim.strftime('%H:%M')}"

            fatura_no_input = st.text_input(
                "Fatura No / Belge No (Örn: FAT-2026-105)"
            ).strip().upper()
            
            mevcut_urun_listesi = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
            
            yeni_urun_secimi = st.checkbox("➕ Listede Olmayan Yepyeni Bir Ürün Ekle")
            
            if yeni_urun_secimi or not mevcut_urun_listesi:
                urun = st.text_input(
                    "Yeni Ürün Adı (Örn: KIRMIZI MERCİMEK - Büyük Harfle)"
                ).strip().upper()
            else:
                urun = st.selectbox("Mevcut Ürünlerden Seçin", mevcut_urun_listesi)

            kategori = st.selectbox(
                "Kategori",
                [
                    "SEBZE",
                    "MEYVE",
                    "KURU GIDA",
                    "BAHARAT",
                    "SÜT/SÜT ÜRÜNLERİ",
                    "KASAP / ŞARKÜTERİ",
                    "YAĞ",
                ],
            )
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"])
            
            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)

            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted and urun:
                urun_temiz = urun.strip().upper()
                
                if yeni_urun_secimi and mevcut_urun_listesi:
                    benzerler = difflib.get_close_matches(urun_temiz, mevcut_urun_listesi, n=1, cutoff=0.7)
                    if benzerler:
                        st.warning(f"⚠️ Dikkat! Yazdığınız ürün mevcut '{benzerler[0]}' adına çok benziyor.")

                islem_yapan_kisi = st.session_state.aktif_kullanici
                fatura_no_degeri = (
                    fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
                )
                yeni_kayit_id = f"FAT-{len(st.session_state.girisler)+1:03d}"
                st.session_state.girisler.append({
                    "id": yeni_kayit_id,
                    "tarih": tarih_giris,
                    "fatura_no": fatura_no_degeri,
                    "urun": urun_temiz,
                    "kategori": kategori,
                    "birim": birim,
                    "miktar": miktar,
                    "kalan": miktar,
                    "fiyat": fiyat,
                    "depo": depo,
                    "islem_yapan": islem_yapan_kisi,
                })
                verileri_kaydet(st.session_state.girisler)
                st.markdown(
                """
                <div style="background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; padding: 14px 18px; border-radius: 14px; margin: 16px 0; font-weight: 600; font-size: 15px;">
                🎉 Başarılı! Yeni mal alımı faturası ve ürün depoya eklendi (Güncel stok artırıldı, fiyat geçmişi korundu).
                </div>
                """,
                unsafe_allow_html=True
                )
                st.balloons()
                time.sleep(2)
                st.rerun()

        st.markdown("---")
        col_b_fatura, col_indir_fatura = st.columns([2, 2])
        with col_b_fatura:
            st.subheader("📋 Mal Alımı / Fatura Log Kayıtları Arşivi (Tüm Geçmiş Fiyatlar)")

        if st.session_state.girisler:
            fatura_log_tablosu = []
            for g in reversed(st.session_state.girisler):
                fatura_log_tablosu.append({
                    "Kayıt ID": g.get("id", "-"),
                    "Fatura / Alım Tarihi": g.get("tarih", "-"),
                    "Fatura No": g.get("fatura_no", "BELİRTİLMEMİŞ"),
                    "Ürün Adı": g.get("urun", "-"),
                    "Kategori": g.get("kategori", "-"),
                    "Alınan Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                    "Kalan Miktar": f"{g.get('kalan', 0)} {g.get('birim', 'Kg')}",
                    "Birim Fiyat": f"{g.get('fiyat', 0):,.2f} ₺",
                    "Toplam Tutar": f"{(g.get('miktar', 0) * g.get('fiyat', 0)):,.2f} ₺",
                    "Depo Yeri": g.get("depo", "-"),
                    "İşlemi Yapan": g.get("islem_yapan", "admin"),
                })

            excel_fatura_data = tablo_to_excel_bytes(fatura_log_tablosu, "Aziziye Aşevi - Mal Alımı Fatura Arşivi")
            pdf_fatura_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Mal Alımı Fatura Arşivi", fatura_log_tablosu)
            with col_indir_fatura:
                ortak_indirme_alani(excel_fatura_data, pdf_fatura_data, "fatura_mal_alimi_arsivi", "fatura_arsiv_sayfasi")

            with st.expander("✏️ Seçili Fatura / Mal Alım Kaydını Düzenle (Depo veya Kategori Değiştir)"):
                with st.form("fatura_duzenle_form"):
                    secenekler_fatura_edit = [f"{g.get('id')} - {g.get('urun')} (Tarih: {g.get('tarih')}, Fatura: {g.get('fatura_no', '-')}, Fiyat: {g.get('fiyat')} TL)" for g in st.session_state.girisler]
                    secilen_edit_fatura_str = st.selectbox("Düzenlenecek Kaydı Seçin", secenekler_fatura_edit)
                    
                    hedef_id = secilen_edit_fatura_str.split(" - ")[0]
                    mevcut_kayit_obj = next((g for g in st.session_state.girisler if g.get("id") == hedef_id), None)
                    
                    yeni_kat_sec = st.selectbox("Yeni Kategori", ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"], index=0 if not mevcut_kayit_obj else max(0, ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"].index(mevcut_kayit_obj.get("kategori", "SEBZE")) if mevcut_kayit_obj.get("kategori") in ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"] else 0))
                    yeni_depo_sec = st.selectbox("Yeni Depo Yeri", st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"])
                    yeni_fiyat_sec = st.number_input("Güncel Birim Fiyat (TL)", min_value=0.01, value=float(mevcut_kayit_obj.get("fiyat", 1.0)) if mevcut_kayit_obj else 1.0, step=0.1)
                    
                    duzenle_submit_btn = st.form_submit_button("Değişiklikleri Kaydet ve Güncelle", type="primary")
                    if duzenle_submit_btn and mevcut_kayit_obj:
                        mevcut_kayit_obj["kategori"] = yeni_kat_sec
                        mevcut_kayit_obj["depo"] = yeni_depo_sec
                        mevcut_kayit_obj["fiyat"] = yeni_fiyat_sec
                        verileri_kaydet(st.session_state.girisler)
                        st.success("🎉 Başarılı! Kayıt güncellendi.")
                        st.balloons()
                        st.rerun()

            ozel_html_tablo_goster(fatura_log_tablosu)
        else:
            st.info("Kayıtlı mal alımı faturası bulunmuyor.")

# DEPO YÖNETİMİ
elif menu == "Depo Yönetimi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🏢 Dinamik Depo Yönetimi")
        st.markdown("Sisteme yeni depo ekleyebilir veya mevcut bir depoyu silebilirsiniz. Depo silindiğinde o depoda kayıtlı olan tüm ürünler ve loglar sistemden otomatik olarak temizlenir.")

        col_depo_ekle, col_depo_sil = st.columns(2)
        with col_depo_ekle:
            with st.form("yeni_depo_ekle_form"):
                st.markdown("**➕ Yeni Depo Ekle**")
                yeni_depo_adi = st.text_input("Depo Adı (Örn: Soğuk Hava Deposu -20)").strip()
                depo_ekle_btn = st.form_submit_button("Depoyu Kaydet", type="primary")

                if depo_ekle_btn and yeni_depo_adi:
                    if yeni_depo_adi in st.session_state.depolar:
                        st.error("⚠️ Bu depo zaten mevcut!")
                    else:
                        st.session_state.depolar.append(yeni_depo_adi)
                        depoları_kaydet(st.session_state.depolar)
                        st.success(f"🎉 Başarılı! '{yeni_depo_adi}' deposu eklendi.")
                        st.balloons()
                        st.rerun()

        with col_depo_sil:
            with st.form("depo_sil_form"):
                st.markdown("**🗑️ Depo Sil**")
                if st.session_state.depolar:
                    secilen_sil_depo = st.selectbox("Silinecek Depoyu Seçin", st.session_state.depolar)
                    depo_sil_btn = st.form_submit_button("Seçilen Depoyu ve Bağlı Ürünleri Sil", type="primary")

                    if depo_sil_btn:
                        if len(st.session_state.depolar) <= 1:
                            st.error("⚠️ Sistemde en az 1 depo kalmalıdır, tamamen silemezsiniz!")
                        else:
                            st.session_state.depolar.remove(secilen_sil_depo)
                            depoları_kaydet(st.session_state.depolar)
                            
                            st.session_state.girisler = [g for g in st.session_state.girisler if g.get("depo") != secilen_sil_depo]
                            verileri_kaydet(st.session_state.girisler)

                            st.success(f"🎉 Başarılı! Depo ve bağlı ürünler silindi.")
                            st.balloons()
                            st.rerun()
                else:
                    st.info("Silinecek depo bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Aktif Depolar Listesi")
        depo_tablosu = [{"Depo Adı": d} for d in st.session_state.depolar]
        ozel_html_tablo_goster(depo_tablosu)

# DEMİRBAŞ YÖNETİMİ
elif menu == "Demirbaş Yönetimi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🛠️ Aşevi Demirbaş ve Ekipman Yönetimi")
        st.markdown("Aşevinde bulunan demirbaşları, mutfak ekipmanlarını ve malzemeleri buradan ekleyebilir, durumlarını (Sağlam, Bakımda vb.) takip edebilirsiniz.")

        col_b_dem, col_indir_dem = st.columns([2, 2])
        with col_b_dem:
            st.subheader("📋 Kayıtlı Demirbaş Listesi")

        demirbas_tablo = []
        excel_demirbas_listesi = []
        for d in st.session_state.demirbaslar:
            demirbas_tablo.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })
            excel_demirbas_listesi.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })

        excel_dem_data = tablo_to_excel_bytes(excel_demirbas_listesi, "Aziziye Aşevi - Demirbaş Listesi")
        pdf_dem_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Demirbaş Listesi", excel_demirbas_listesi)

        with col_indir_dem:
            ortak_indirme_alani(excel_dem_data, pdf_dem_data, "demirbas_listesi_raporu", "demirbas_sayfasi")

        if salt_okunur_modu:
            st.warning("👀 Salt okunur modundasınız. Yeni demirbaş ekleyemez veya düzenleyemezsiniz.")
        else:
            col_dem_ekle, col_dem_sil = st.columns(2)
            with col_dem_ekle:
                with st.form("demirbas_ekle_form"):
                    st.markdown("**➕ Yeni Demirbaş Ekle**")
                    d_ad = st.text_input("Demirbaş Adı (Örn: Sanayi Tipi Fırın)").strip()
                    d_kat = st.selectbox("Kategori", ["Mutfak Ekipmanı", "Elektronik", "Mobilya", "Taşıt / Lojistik", "Diğer"])
                    d_adet = st.number_input("Adet", min_value=1, value=1, step=1)
                    d_durum = st.selectbox("Durumu", ["Sağlam", "Bakımda", "Hurda / Kullanılamaz"])
                    d_zimmet = st.text_input("Zimmetli Sorumlu / Yer (Örn: Aşçıbaşı)").strip()
                    d_tarih = st.date_input("Kayıt Tarihi", value=datetime.date.today())

                    dem_ekle_btn = st.form_submit_button("Demirbaş Kaydet", type="primary")
                    if dem_ekle_btn and d_ad:
                        yeni_d_id = f"DEM-{len(st.session_state.demirbaslar)+1:03d}"
                        st.session_state.demirbaslar.append({
                            "id": yeni_d_id,
                            "ad": d_ad,
                            "kategori": d_kat,
                            "adet": int(d_adet),
                            "durum": d_durum,
                            "zimmet": d_zimmet if d_zimmet else "Belirtilmemiş",
                            "tarih": str(d_tarih)
                        })
                        demirbasları_kaydet(st.session_state.demirbaslar)
                        st.success(f"🎉 Başarılı! '{d_ad}' demirbaş listesine eklendi.")
                        st.balloons()
                        st.rerun()

            with col_dem_sil:
                with st.form("demirbas_sil_form"):
                    st.markdown("**🗑️ Demirbaş Sil**")
                    if st.session_state.demirbaslar:
                        dem_secenekleri = [f"{d['id']} - {d['ad']} ({d['kategori']})" for d in st.session_state.demirbaslar]
                        secilen_sil_dem = st.selectbox("Silinecek Demirbaşı Seçin", dem_secenekleri)
                        dem_sil_btn = st.form_submit_button("Seçilen Demirbaş Kaydını Sil", type="primary")

                        if dem_sil_btn:
                            sil_id = secilen_sil_dem.split(" - ")[0]
                            st.session_state.demirbaslar = [d for d in st.session_state.demirbaslar if d["id"] != sil_id]
                            demirbasları_kaydet(st.session_state.demirbaslar)
                            st.success("🎉 Başarılı! Demirbaş kaydı silindi.")
                            st.balloons()
                            st.rerun()
                    else:
                        st.info("Silinecek demirbaş bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Demirbaş Tablosu")
        if demirbas_tablo:
            ozel_html_tablo_goster(demirbas_tablo)
        else:
            st.info("Kayıtlı demirbaş bulunmuyor.")

# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda silme işlemi gerçekleştiremezsiniz.")
        elif not yonetici_modu:
            st.warning("⚠️ Bu ekrana erişmek için **Admin** hesabıyla giriş yapmalısınız.")
        else:
            if st.session_state.silme_mesaji:
                st.success(st.session_state.silme_mesaji)
                st.session_state.silme_mesaji = ""
            if not st.session_state.girisler:
                st.info("Sistemde silinecek kayıt bulunmuyor.")
            else:
                with st.form("urun_silme_formu"):
                    secenekler = [
                        f"{g['id']} - {g['urun']} (Eklenme: {g.get('tarih', '-')}, Kalan: {g['kalan']} {g['birim']}, Fiyat: {g.get('fiyat', 0)} TL)"
                        for g in st.session_state.girisler
                    ]
                    secilen_kayit_str = st.selectbox(
                        "Silmek İstediğiniz Kaydı / Faturayı Seçin", secenekler
                    )
                    silme_nedeni_input = st.text_input(
                        "Silme Nedeni / Gerekçesi", "Örn: Yanlış giriş"
                    )
                    sil_onay_btn = st.form_submit_button(
                        "Seçilen Kaydı Kalıcı Olarak Sil", type="primary"
                    )

                    if sil_onay_btn:
                        secilen_id = secilen_kayit_str.split(" - ")[0]
                        ilgili_oge = next(
                            (g for g in st.session_state.girisler if g["id"] == secilen_id),
                            None,
                        )
                        if ilgili_oge:
                            silinen_urun_adi = ilgili_oge["urun"]
                            st.session_state.silinen_urun_loglari.append({
                                "tarih": simdi_tr_str("%Y-%m-%d %H:%M"),
                                "urun": silinen_urun_adi,
                                "kayit_id": ilgili_oge["id"],
                                "fatura_no": ilgili_oge.get("fatura_no", "-"),
                                "neden": (
                                    silme_nedeni_input
                                    if silme_nedeni_input
                                    else "Belirtilmedi"
                                ),
                                "islem_yapan": st.session_state.aktif_kullanici,
                            })
                            silinen_urun_loglarini_kaydet(
                                st.session_state.silinen_urun_loglari
                            )
                            st.session_state.girisler = [
                                g
                                for g in st.session_state.girisler
                                if g["id"] != secilen_id
                            ]
                            verileri_kaydet(st.session_state.girisler)
                            st.session_state.silme_mesaji = (
                                f"🎉 Başarılı! {silinen_urun_adi} kayıt ID {secilen_id} sistemden silindi."
                            )
                            st.balloons()
                            st.rerun()

        st.markdown("---")
        
        col_b_silinen, col_indir_silinen = st.columns([2, 2])
        with col_b_silinen:
            st.subheader("📋 Silinen Ürünler Arşivi")

        if st.session_state.silinen_urun_loglari:
            silinen_tablo_verisi = [
                {
                    "Silinme Tarihi": sl["tarih"],
                    "Kayıt ID": sl.get("kayit_id", "-"),
                    "Ürün Adı": sl["urun"],
                    "Silme Nedeni": sl["neden"],
                    "İşlemi Yapan": sl.get("islem_yapan", "admin"),
                }
                for sl in st.session_state.silinen_urun_loglari
            ]
            
            excel_silinen_data = tablo_to_excel_bytes(silinen_tablo_verisi, "Aziziye Aşevi - Silinen Ürünler Arşivi")
            pdf_silinen_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Silinen Ürünler Arşivi", silinen_tablo_verisi)
            with col_indir_silinen:
                ortak_indirme_alani(excel_silinen_data, pdf_silinen_data, "silinen_urunler_arsivi", "silinen_arsiv_sayfasi")

            ozel_html_tablo_goster(silinen_tablo_verisi)
        else:
            st.info("Silinmiş ürün kaydı bulunmuyor.")

# 4. FİRE / ZAYİAT GİRİŞİ
elif menu == "Fire / Zayiat Girişi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Fire / Zayiat Bildirimi")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda fire düşemezsiniz.")
        else:
            benzersiz_urunler = sorted(
                list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
            )
            
            with st.form("fire_formu"):
                col_f_t1, col_f_t2 = st.columns(2)
                with col_f_t1:
                    fire_tarihi_secim = st.date_input("📅 Fire / Zayiat Tarihi", value=datetime.date.today())
                with col_f_t2:
                    fire_saati_secim = st.time_input("⏰ Fire Saati", value=datetime.datetime.now().time())
                fire_tarih_str = f"{fire_tarihi_secim.strftime('%Y-%m-%d')} {fire_saati_secim.strftime('%H:%M')}"

                secilen_gercek_urun = st.selectbox(
                    "Fire Düşülecek Ürünü Seçin", benzersiz_urunler if benzersiz_urunler else ["Yok"]
                )
                
                ilgili_girisler = [
                    g
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == secilen_gercek_urun.strip().upper()
                ]
                toplam_stok = sum(g.get("kalan", 0) for g in ilgili_girisler)
                aktif_ilgili_girisler = [g for g in ilgili_girisler if g.get("kalan", 0) > 0]

                en_son_fiyat = 0.0
                if ilgili_girisler:
                    en_son_kayit = max(
                        ilgili_girisler, key=lambda x: x.get("tarih", "")
                    )
                    en_son_fiyat = en_son_kayit.get("fiyat", 0.0)

                st.info(
                    f"Güncel Toplam Stok ({secilen_gercek_urun}): {toplam_stok} | Baz Alınan Birim Fiyat: {en_son_fiyat:,.2f} ₺"
                )
                fire_miktari = st.number_input(
                    "Fire Miktarı",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                )

                submitted_fire = st.form_submit_button("Fireyi Düş ve Kaydet")
                if submitted_fire and fire_miktari > 0:
                    if fire_miktari > toplam_stok:
                        st.error(f"⚠️ Hata: Girilen fire miktarı ({fire_miktari}), güncel toplam stoktan ({toplam_stok}) büyük olamaz!")
                    else:
                        kalan_dusulecek = fire_miktari

                        for g in aktif_ilgili_girisler:
                            if kalan_dusulecek <= 0:
                                break
                            if g["kalan"] >= kalan_dusulecek:
                                g["kalan"] -= kalan_dusulecek
                                kalan_dusulecek = 0
                            else:
                                dusulen = g["kalan"]
                                g["kalan"] = 0
                                kalan_dusulecek -= dusulen

                        toplam_zarar = fire_miktari * en_son_fiyat

                        verileri_kaydet(st.session_state.girisler)
                        st.session_state.kullanim_loglari.append({
                            "tarih": fire_tarih_str,
                            "urun": secilen_gercek_urun,
                            "tur": "Fire/Zayiat",
                            "miktar": fire_miktari,
                            "tutar": toplam_zarar,
                            "islem_yapan": st.session_state.aktif_kullanici,
                        })
                        loglari_kaydet(st.session_state.kullanim_loglari)
                        st.success(
                            f"🎉 Başarılı! {secilen_gercek_urun} için fire düşüldü ({fire_tarih_str}). Toplam zarar: {toplam_zarar:,.2f} ₺"
                        )
                        st.balloons()
                        st.rerun()

        st.markdown("---")
        
        col_b_fire, col_indir_fire = st.columns([2, 2])
        with col_b_fire:
            st.subheader("📋 Kayıtlı Fire ve Zayiatlar Listesi")
        
        if "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi" in aktif_k_maskeleri:
            st.info("🔒 Kayıtlı Fire ve Zayiatlar Listesi tablosu bu kullanıcı için tamamen maskelenmiştir (gizlenmiştir).")
        else:
            fire_loglari = [
                l
                for l in st.session_state.kullanim_loglari
                if l.get("tur") == "Fire/Zayiat"
            ]
            if fire_loglari:
                fire_tablo_verisi = []
                for f_log in reversed(fire_loglari):
                    fire_tablo_verisi.append({
                        "Tarih / Saat": f_log.get("tarih", "-"),
                        "Ürün Adı": f_log.get("urun", "-"),
                        "Fire Miktarı": f"{f_log.get('miktar', 0)}",
                        "Toplam Tutar": f"{f_log.get('tutar', 0):,.2f} ₺",
                        "İşlemi Yapan": f_log.get("islem_yapan", "admin"),
                    })
                
                excel_fire_data = tablo_to_excel_bytes(fire_tablo_verisi, "Aziziye Aşevi - Fire ve Zayiat Raporu")
                pdf_fire_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Fire ve Zayiat Raporu", fire_tablo_verisi)
                with col_indir_fire:
                    ortak_indirme_alani(excel_fire_data, pdf_fire_data, "fire_ve_zayiat_listesi", "fire_arsiv_sayfasi")

                ozel_html_tablo_goster(fire_tablo_verisi)
            else:
                st.info("Sistemde kayıtlı fire / zayiat bulunmuyor.")

# TOPLU STOK DÜŞÜMÜ & SARFİYAT
elif menu == "Toplu Stok Düşümü & Sarfiyat":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🔄 Toplu Stok Düşümü ve Kullanılan Ürünler")
        st.markdown("Geçmiş yemek tarifleri seçmek zorunda kalmadan, kullanılan malzemeleri ve miktarlarını seçerek doğrudan stoktan düşürebilir ve kullanılan ürünler listesine ekleyebilirsiniz.")
        
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda toplu stok düşümü yapamazsınız.")
        else:
            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                st.subheader("Malzeme Çıkış Formu")
                benzersiz_urunler_toplu = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
                
                if benzersiz_urunler_toplu:
                    selected_item = st.selectbox("Malzeme Seçin", benzersiz_urunler_toplu, key="toplu_malzeme_selectbox")
                    
                    ilgili_girisler_toplu = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == selected_item.strip().upper()]
                    current_stock = sum(g.get("kalan", 0) for g in ilgili_girisler_toplu)
                    aktif_ilgili_toplu = [g for g in ilgili_girisler_toplu if g.get("kalan", 0) > 0]
                    
                    unit = ilgili_girisler_toplu[0].get("birim", "Kg") if ilgili_girisler_toplu else "Kg"
                    
                    st.info(f"Mevcut Toplam Stok ({selected_item}): {current_stock} {unit}")
                    
                    used_amount = st.number_input(f"Kullanılan Miktar ({unit})", min_value=0.1, value=1.0, step=0.5)
                    description = st.text_input("Açıklama / Not (Örn: Kazan yemeği, günlük dağıtım vb.)", "Günlük Aşevi Üretimi")
                    
                    if st.button("Stoktan Düş ve Kullanılanlara Ekle", type="primary"):
                        if used_amount > current_stock:
                            st.error(f"⚠️ Hata: Kullanılan miktar ({used_amount}), mevcut toplam stoktan ({current_stock}) büyük olamaz!")
                        else:
                            kalan_dusulecek = used_amount
                            harcanan_tutar = 0.0
                            
                            for g in aktif_ilgili_toplu:
                                if kalan_dusulecek <= 0:
                                    break
                                if g["kalan"] >= kalan_dusulecek:
                                    g["kalan"] -= kalan_dusulecek
                                    harcanan_tutar += kalan_dusulecek * g["fiyat"]
                                    kalan_dusulecek = 0
                                else:
                                    dusulen = g["kalan"]
                                    g["kalan"] = 0
                                    harcanan_tutar += dusulen * g["fiyat"]
                                    kalan_dusulecek -= dusulen
                            
                            verileri_kaydet(st.session_state.girisler)
                            
                            islem_tarihi_str = simdi_tr_str("%Y-%m-%d %H:%M")
                            st.session_state.kullanim_loglari.append({
                                "tarih": islem_tarihi_str,
                                "urun": selected_item,
                                "tur": f"Toplu Sarfiyat ({description})",
                                "miktar": used_amount,
                                "tutar": harcanan_tutar,
                                "islem_yapan": st.session_state.aktif_kullanici,
                            })
                            loglari_kaydet(st.session_state.kullanim_loglari)
                            
                            st.success(f"🎉 Başarılı! {used_amount} {unit} {selected_item} stoktan düşüldü ve loglara eklendi!")
                            st.balloons()
                            st.rerun()
                else:
                    st.info("Depoda kayıtlı ürün bulunmuyor.")

            with col_form2:
                st.subheader("Geçmişte Kullanılan Ürünler (Sarfiyat Logu)")
                toplu_sarfiyat_loglari = [l for l in st.session_state.kullanim_loglari if "Toplu Sarfiyat" in l.get("tur", "")]
                if toplu_sarfiyat_loglari:
                    tablo_sarf = []
                    for s_log in reversed(toplu_sarfiyat_loglari):
                        tablo_sarf.append({
                            "Tarih / Saat": s_log.get("tarih", "-"),
                            "Malzeme": s_log.get("urun", "-"),
                            "Miktar": f"{s_log.get('miktar', 0)}",
                            "Tutar": f"{s_log.get('tutar', 0):,.2f} ₺",
                            "Açıklama": s_log.get("tur", "-"),
                            "İşlemi Yapan": s_log.get("islem_yapan", "-"),
                        })
                    ozel_html_tablo_goster(tablo_sarf)
                else:
                    st.info("Henüz toplu stok düşümü yapılmadı.")

# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi")

    col_tarih_mod, col_tarih_sec = st.columns([1.2, 1.8])
    with col_tarih_mod:
        zaman_modu = st.radio(
            "Arşiv Görünüm Modu", ["Tek Tarih", "Tarih Aralığı", "Tüm Zamanlar"], horizontal=True
        )
    with col_tarih_sec:
        if zaman_modu == "Tek Tarih":
            secilen_tarih_filtresi = st.date_input(
                "📅 Sorgulanacak Tarihi Seçin", value=datetime.date.today()
            )
            secilen_tarih_str = secilen_tarih_filtresi.strftime("%Y-%m-%d")
        elif zaman_modu == "Tarih Aralığı":
            c_bas, c_bit = st.columns(2)
            with c_bas:
                bas_tarih_filt = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7))
            with c_bit:
                bit_tarih_filt = st.date_input("Bitiş Tarihi", value=datetime.date.today())
        else:
            secilen_tarih_str = "TÜMÜ"

    if not misafir_modu:
        st.markdown("---")
        st.subheader("🍲 Yeni Yemek Üretim Planı ve Malzeme Düşümü")
        yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
        kisi_sayisi = st.number_input(
            "Yararlanan Kişi Sayısı", min_value=1, value=200
        )
        uretim_tarihi_input = st.date_input(
            "📅 Yemeğin Yapıldığı Tarih (Geçmiş / Bugün)",
            value=datetime.date.today(),
        )
        uretim_tarih_str = uretim_tarihi_input.strftime("%Y-%m-%d")

        benzersiz_urunler = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )

        if "sepet" not in st.session_state:
            st.session_state.sepet = []

        if not salt_okunur_modu:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                secilen_urun = st.selectbox(
                    "Malzeme Seç", benzersiz_urunler if benzersiz_urunler else ["Yok"], key="yemek_urun"
                )
            with col2:
                ilgili_girisler = [
                    g
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == secilen_urun.strip().upper()
                ]
                stok_max = sum(g.get("kalan", 0) for g in ilgili_girisler)
                kullanilacak_miktar = st.number_input(
                    f"Miktar (Toplam Stok: {stok_max})",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                    key="yemek_miktar",
                )
            with col3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Sepete Ekle", use_container_width=True):
                    if kullanilacak_miktar > 0:
                        st.session_state.sepet.append(
                            {"urun": secilen_urun, "miktar": kullanilacak_miktar}
                        )
                        st.success("Eklendi!")
                        st.rerun()

        st.markdown("---")
        st.subheader("Seçilen Malzemeler")

        if st.session_state.sepet:
            if not salt_okunur_modu:
                if st.button("🔄 Tümünü Sıfırla"):
                    st.session_state.sepet = []
                    st.rerun()

            toplam_maliyet = 0.0
            excel_sepet_liste = []

            silinecek_index = None
            for idx, item in enumerate(st.session_state.sepet):
                urun = item["urun"]
                istenen = item["miktar"]

                ilgili_girisler = [
                    g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper()
                ]
                ortalama_fiyat = 0.0
                if ilgili_girisler:
                    toplam_fiyat_degeri = sum(
                        g.get("fiyat", 0) * g.get("miktar", 0) for g in ilgili_girisler
                    )
                    toplam_miktar_degeri = sum(g.get("miktar", 0) for g in ilgili_girisler)
                    ortalama_fiyat = (
                        toplam_fiyat_degeri / toplam_miktar_degeri
                        if toplam_miktar_degeri > 0
                        else 0.0
                    )

                item_maliyeti = istenen * ortalama_fiyat
                toplam_maliyet += item_maliyeti

                c_item_ad, c_item_mik, c_item_mal, c_item_sil = st.columns(
                    [3, 2, 2, 1]
                )
                with c_item_ad:
                    st.markdown(f"• **{urun}**")
                with c_item_mik:
                    st.markdown(f"Miktar: {istenen}")
                with c_item_mal:
                    st.markdown(f"Maliyet: **{item_maliyeti:,.2f} ₺**")
                with c_item_sil:
                    if not salt_okunur_modu:
                        if st.button("❌", key=f"sil_item_{idx}"):
                            silinecek_index = idx

                excel_sepet_liste.append({
                    "Malzeme": urun,
                    "Miktar": istenen,
                    "Maliyet (TL)": round(item_maliyeti, 2),
                })

            if silinecek_index is not None:
                st.session_state.sepet.pop(silinecek_index)
                st.rerun()

            if not salt_okunur_modu:
                if st.button(
                    "🍲 Üretimi Tamamla ve Stoktan / Kullanıma Düş", type="primary"
                ):
                    tarih_simdi = simdi_tr_str("%Y-%m-%d %H:%M")

                    arsiv_malzemeler = []
                    for item in st.session_state.sepet:
                        urun = item["urun"]
                        istenen = item["miktar"]
                        kalan_dusulecek = istenen
                        item_tutar = 0.0
                        ilgili_g = [
                            g
                            for g in st.session_state.girisler
                            if g.get("urun", "").strip().upper() == urun.strip().upper() and g.get("kalan", 0) > 0
                        ]
                        for g in ilgili_g:
                            if kalan_dusulecek <= 0:
                                break
                            if g["kalan"] >= kalan_dusulecek:
                                g["kalan"] -= kalan_dusulecek
                                item_tutar += kalan_dusulecek * g["fiyat"]
                                kalan_dusulecek = 0
                            else:
                                dusulen = g["kalan"]
                                g["kalan"] = 0
                                item_tutar += dusulen * g["fiyat"]
                                kalan_dusulecek -= dusulen

                        arsiv_malzemeler.append(
                            {"urun": urun, "miktar": istenen, "tutar": item_tutar}
                        )

                        st.session_state.kullanim_loglari.append({
                            "tarih": f"{uretim_tarih_str} 12:00",
                            "urun": urun,
                            "tur": f"Günlük Kullanım ({yemek_adi})",
                            "miktar": istenen,
                            "tutar": item_tutar,
                            "islem_yapan": st.session_state.aktif_kullanici,
                        })

                    st.session_state.yemek_uretim_arsivi.append({
                        "tarih": uretim_tarih_str,
                        "zaman": tarih_simdi,
                        "yemek_adi": yemek_adi,
                        "kisi_sayisi": kisi_sayisi,
                        "malzemeler": arsiv_malzemeler,
                        "toplam_maliyet": toplam_maliyet,
                        "islem_yapan": st.session_state.aktif_kullanici,
                    })
                    yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)

                    verileri_kaydet(st.session_state.girisler)
                    loglari_kaydet(st.session_state.kullanim_loglari)
                    st.session_state.sepet = []
                    st.success(
                        f"🎉 Başarılı! {uretim_tarih_str} tarihli üretim arşive kaydedildi."
                    )
                    st.balloons()
                    st.rerun()

            st.markdown("---")
            kisi_basi_maliyet = (
                toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0.0
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Toplam Maliyet", f"{toplam_maliyet:,.2f} ₺")
            with m2:
                st.metric("Kişi Başı Maliyet", f"{kisi_basi_maliyet:,.2f} ₺")

            pdf_data = tablo_to_html_pdf_bytes(
                f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste
            )
            excel_sepet_data = tablo_to_excel_bytes(
                excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}"
            )
            with col_indir_alan:
                ortak_indirme_alani(
                    excel_sepet_data,
                    pdf_data,
                    "yemek_maliyet_raporu",
                    "yemek_sayfasi",
                )
        else:
            st.info("Henüz sepete malzeme eklenmedi.")

    st.markdown("---")
    
    col_b_arsiv, col_indir_arsiv = st.columns([2, 2])
    with col_b_arsiv:
        if zaman_modu == "Tüm Zamanlar":
            st.subheader("📚 Tüm Zamanların Yemek Üretim ve Maliyet Arşivi")
            secilen_gun_uretimleri = st.session_state.yemek_uretim_arsivi
        elif zaman_modu == "Tek Tarih":
            st.subheader(
                f"📅 Seçilen Tarihteki ({secilen_tarih_str}) Yemek Üretim ve Maliyet Arşivi"
            )
            secilen_gun_uretimleri = [
                u
                for u in st.session_state.yemek_uretim_arsivi
                if u.get("tarih") == secilen_tarih_str
            ]
        else:
            st.subheader(f"📅 Tarih Aralığı Arşivi ({bas_tarih_filt} ile {bit_tarih_filt} arası)")
            secilen_gun_uretimleri = []
            for u in st.session_state.yemek_uretim_arsivi:
                t_str = u.get("tarih", "")
                try:
                    t_dt = datetime.datetime.strptime(t_str, "%Y-%m-%d").date()
                    if bas_tarih_filt <= t_dt <= bit_tarih_filt:
                        secilen_gun_uretimleri.append(u)
                except:
                    pass

    if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" in aktif_k_maskeleri:
        st.info("🔒 Yemek Üretim ve Maliyet Arşivi bu kullanıcı için maskelenmiştir (gizlenmiştir).")
    else:
        if secilen_gun_uretimleri:
            arsiv_tablo_verisi = []
            excel_arsiv_listesi = []
            for u_kayit in secilen_gun_uretimleri:
                if misafir_modu:
                    arsiv_tablo_verisi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                    })
                    excel_arsiv_listesi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                    })
                else:
                    for m in u_kayit.get("malzemeler", []):
                        arsiv_tablo_verisi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Kullanılan Malzeme": m.get("urun", "-"),
                            "Miktar": m.get("miktar", 0),
                            "Maliyet": f"{m.get('tutar', 0):,.2f} ₺",
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })
                        excel_arsiv_listesi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Kullanılan Malzeme": m.get("urun", "-"),
                            "Miktar": m.get("miktar", 0),
                            "Maliyet (TL)": round(m.get("tutar", 0), 2),
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })

            rapor_adi_etiketi = "yemek_uretim_raporu_arsiv"
            baslik_etiketi = "Aziziye Aşevi - Yemek Üretim Raporu Arşivi"

            excel_arsiv_data = tablo_to_excel_bytes(
                excel_arsiv_listesi, baslik_etiketi
            )
            pdf_arsiv_data = tablo_to_html_pdf_bytes(baslik_etiketi, excel_arsiv_listesi)

            with col_indir_arsiv:
                ortak_indirme_alani(
                    excel_arsiv_data,
                    pdf_arsiv_data,
                    rapor_adi_etiketi,
                    "arsiv_tarih_araligi",
                )

            ozel_html_tablo_goster(arsiv_tablo_verisi)
        else:
            st.info("Seçilen tarih aralığında kayıtlı yemek üretim ve maliyet arşivi bulunmuyor.")

# 6. KALORİ HESAPLAMA ARACI
elif menu == "Kalori Hesaplama Aracı":
    col_b_kal, col_indir_kal = st.columns([2, 2])
    with col_b_kal:
        st.header("🔥 Kalori Hesaplama Aracı")

    benzersiz_urunler_kalori = sorted(
        list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
    )
    col_k_sec1, col_k_sec2, col_k_sec3 = st.columns([2, 1, 1])
    with col_k_sec1:
        secilen_kalori_urun = st.selectbox(
            "Malzeme Seçin", benzersiz_urunler_kalori if benzersiz_urunler_kalori else ["Yok"], key="kalori_urun_sec"
        )
    with col_k_sec2:
        kalori_miktar_input = st.number_input(
            "Miktar", min_value=0.1, value=1.0, step=0.5, key="kalori_mik"
        )
    with col_k_sec3:
        kalori_birim_input = st.selectbox(
            "Birim", ["Kg", "Adet", "Lt"], key="kalori_brm"
        )

    if st.button("➕ Listeye Ekle"):
        st.session_state.kalori_sepeti.append({
            "urun": secilen_kalori_urun,
            "miktar": kalori_miktar_input,
            "birim": kalori_birim_input,
        })
        st.success("🎉 Başarılı! Eklendi.")
        st.balloons()

    if st.session_state.kalori_sepeti:
        toplam_kalori = sum(
            urun_kalori_hesapla(i["urun"], i["miktar"], i["birim"])
            for i in st.session_state.kalori_sepeti
        )
        st.metric("Toplam Tarif Kalorisi", f"{toplam_kalori:,.0f} kcal")

# 7. İHTİYAÇ SAHİBİ & YEMEK DAĞITIM TAKİBİ
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi")
        st.markdown(
            "Aşevimizden yemek yardımı alan kişilerin kayıtlarını oluşturun, aktif/pasif durumlarını yönetin ve yemek dağıtımlarını takip edin."
        )

        tab1, tab2, tab3 = st.tabs([
            "📋 İhtiyaç Sahibi Listesi, Aktif/Pasif ve Ekle",
            "🍲 Toplu Yemek Dağıtımı",
            "📊 Dağıtım Sayacı & Raporları",
        ])

        with tab1:
            col_b_kisi, col_indir_kisi = st.columns([2, 2])
            with col_b_kisi:
                st.subheader("📋 İhtiyaç Sahibi Listesi ve Yönetimi")

            if st.session_state.kisi_silme_mesaji:
                st.success(st.session_state.kisi_silme_mesaji)
                st.session_state.kisi_silme_mesaji = ""

            kisi_liste_gosterim = []
            for k in st.session_state.ihtiyac_sahipleri:
                tc_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "")
                ad_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adı Soyadı" in aktif_k_maskeleri else k.get("ad_soyad", "")
                tel_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Telefon" in aktif_k_maskeleri else k.get("telefon", "")
                adres_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adres" in aktif_k_maskeleri else k.get("adres", "")
                birey_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı" in aktif_k_maskeleri else k.get("birey_sayisi", "")
                durum_str = "🟢 Aktif" if k.get("aktif", True) else "🔴 Pasif"

                kisi_liste_gosterim.append({
                    "Kayıt No": k["id"],
                    "Durumu": durum_str,
                    "T.C. Kimlik No / Hane No": tc_maskele,
                    "Adı Soyadı": ad_maskele,
                    "Telefon": tel_maskele,
                    "Adres": adres_maskele,
                    "Birey Sayısı": birey_maskele,
                    "Eklenme Zamanı": k.get("eklenme_tarihi", "-"),
                    "İşlemi Yapan": k.get("islem_yapan", "admin"),
                })

            excel_kisi_data = tablo_to_excel_bytes(
                kisi_liste_gosterim, "Aziziye Aşevi - İhtiyaç Sahipleri Listesi"
            )
            pdf_kisi_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - İhtiyaç Sahipleri Listesi", kisi_liste_gosterim
            )

            with col_indir_kisi:
                ortak_indirme_alani(
                    excel_kisi_data,
                    pdf_kisi_data,
                    "ihtiyac_sahipleri_listesi",
                    "ihtiyac_kisi_sayfasi",
                )

            if not salt_okunur_modu:
                with st.expander("🔄 Vatandaşın Aktif / Pasif Durumunu Değiştir"):
                    with st.form("aktif_pasif_form"):
                        kisi_sec_list = [f"{k['id']} - {k['ad_soyad']} (Mevcut: {'Aktif' if k.get('aktif', True) else 'Pasif'})" for k in st.session_state.ihtiyac_sahipleri]
                        secilen_kisi_durum_str = st.selectbox("Vatandaş Seçin", kisi_sec_list if kisi_sec_list else ["Yok"])
                        yeni_durum_secim = st.radio("Yeni Durum", ["Aktif Yap", "Pasif Yap"], horizontal=True)
                        durum_degis_btn = st.form_submit_button("Durumu Güncelle", type="primary")

                        if durum_degis_btn and secilen_kisi_durum_str != "Yok":
                            h_id = secilen_kisi_durum_str.split(" - ")[0]
                            for k in st.session_state.ihtiyac_sahipleri:
                                if k["id"] == h_id:
                                    k["aktif"] = (yeni_durum_secim == "Aktif Yap")
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.success("🎉 Başarılı! Vatandaşın aktif/pasif durumu güncellendi (Geçmiş dağıtım kayıtları korundu).")
                            st.rerun()

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda yalnızca kayıtlı ihtiyaç sahiplerini gözlemleyebilirsiniz.")
            else:
                col_form_ekle, col_form_sil = st.columns(2)
                with col_form_ekle:
                    with st.form("ihtiyac_sahibi_formu"):
                        st.markdown("**➕ Yeni İhtiyaç Sahibi / Hane Ekle**")
                        yeni_tc_hane = st.text_input("T.C. Kimlik No / Hane No").strip()
                        yeni_ad = (
                            st.text_input("Adı Soyadı / Hane Unvanı").strip().upper()
                        )
                        yeni_tel = st.text_input("Telefon Numarası")
                        yeni_adres = st.text_input("Açık Adres")
                        yeni_birey = st.number_input(
                            "Aile / Hane Birey Sayısı", min_value=1, value=1
                        )

                        kaydet_btn = st.form_submit_button("İhtiyaç Sahibini Kaydet")
                        if kaydet_btn and yeni_ad:
                            islem_tarihi_str = simdi_tr_str("%Y-%m-%d %H:%M")
                            islem_yapan_kisi = st.session_state.aktif_kullanici
                            st.session_state.ihtiyac_sahipleri.append({
                                "id": f"IHT-{len(st.session_state.ihtiyac_sahipleri)+1:03d}",
                                "tc_hane": yeni_tc_hane,
                                "ad_soyad": yeni_ad,
                                "telefon": yeni_tel,
                                "adres": yeni_adres,
                                "birey_sayisi": yeni_birey,
                                "aktif": True,
                                "eklenme_tarihi": islem_tarihi_str,
                                "islem_yapan": islem_yapan_kisi,
                            })
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.success(f"🎉 Başarılı! {yeni_ad} kaydedildi.")
                            st.balloons()
                            st.rerun()

                with col_form_sil:
                    with st.form("ihtiyac_sahibi_sil_formu"):
                        st.markdown("**🗑️ Kayıtlı İhtiyaç Sahibini Sil**")
                        if st.session_state.ihtiyac_sahipleri:
                            kisi_secenekleri_sil = [
                                f"{k['id']} - {k['ad_soyad']} (T.C./Hane: {k.get('tc_hane', '-')})"
                                for k in st.session_state.ihtiyac_sahipleri
                            ]
                            secilen_silinecek = st.selectbox(
                                "Silinecek Kişiyi / Haneyi Seçin", kisi_secenekleri_sil
                            )
                            sil_btn = st.form_submit_button(
                                "Seçilen Kişiyi Sistemden Sil", type="primary"
                            )

                            if sil_btn:
                                silinecek_id = secilen_silinecek.split(" - ")[0]
                                silinen_kisi_obj = next(
                                    (
                                        k
                                        for k in st.session_state.ihtiyac_sahipleri
                                        if k["id"] == silinecek_id
                                    ),
                                    None,
                                )
                                silinen_isim = (
                                    silinen_kisi_obj["ad_soyad"] if silinen_kisi_obj else ""
                                )
                                st.session_state.ihtiyac_sahipleri = [
                                    k
                                    for k in st.session_state.ihtiyac_sahipleri
                                    if k["id"] != silinecek_id
                                ]
                                ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                                st.session_state.kisi_silme_mesaji = (
                                    f"🎉 Başarılı! {silinen_isim} silindi."
                                )
                                st.balloons()
                                st.rerun()
                        else:
                            st.info("Silinecek kayıt bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı İhtiyaç Sahipleri Tablosu")
            if kisi_liste_gosterim:
                ozel_html_tablo_goster(kisi_liste_gosterim)
            else:
                st.info("Sistemde kayıtlı ihtiyaç sahibi bulunmuyor.")

        with tab2:
            col_b_dag, col_indir_dag = st.columns([2, 2])
            with col_b_dag:
                st.subheader("🍲 Toplu Yemek Dağıtımı Girişi ve Yönetimi")

            if st.session_state.dagitim_silme_mesaji:
                st.success(st.session_state.dagitim_silme_mesaji)
                st.session_state.dagitim_silme_mesaji = ""

            aktif_ihtiyac_sahipleri = [k for k in st.session_state.ihtiyac_sahipleri if k.get("aktif", True)]

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda yeni dağıtım kaydı oluşturamazsınız.")
            elif not aktif_ihtiyac_sahipleri:
                st.warning("Aktif durumda kayıtlı ihtiyaç sahibi bulunmuyor.")
            else:
                st.markdown("##### ⚡ Toplu Dağıtım Paneli (Aktif Vatandaşlar)")
                with st.form("toplu_dagitim_formu"):
                    menu_adi_toplu = st.text_input(
                        "Dağıtılacak Ortak Menü / Yemek Adı", "Ispanak Yemeği ve Pilav"
                    )
                    st.markdown("---")
                    st.markdown("**Aktif İhtiyaç Sahibi Listesi ve Porsiyon Belirleme**")
                    
                    secim_verileri = []
                    for idx, k in enumerate(aktif_ihtiyac_sahipleri):
                        c1, c2, c3 = st.columns([0.5, 2.5, 1])
                        with c1:
                            secili_mi = st.checkbox("Seç", value=True, key=f"toplu_sec_{idx}", label_visibility="collapsed")
                        with c2:
                            st.markdown(f"**{k['ad_soyad']}** <span style='font-size:12px; opacity:0.6;'>(Hane/T.C: {k.get('tc_hane', '-')})</span>", unsafe_allow_html=True)
                        with c3:
                            varsayilan_porsiyon = int(k.get("birey_sayisi", 1))
                            pors_val = st.number_input("Porsiyon", min_value=1, value=varsayilan_porsiyon, key=f"toplu_pors_{idx}", label_visibility="collapsed")
                        
                        secim_verileri.append({
                            "kisi": k["ad_soyad"],
                            "secili": secili_mi,
                            "porsiyon": pors_val
                        })

                    st.markdown("---")
                    toplu_kaydet_btn = st.form_submit_button("🚀 Seçilen Tüm Hanelere Toplu Dağıtımı Onayla ve Kaydet", type="primary")

                    if toplu_kaydet_btn:
                        d_tarih_saat = simdi_tr_str("%Y-%m-%d %H:%M")
                        eklenen_sayisi = 0
                        for sv in secim_verileri:
                            if sv["secili"]:
                                st.session_state.dagitim_loglari.append({
                                    "id": f"DAG-{len(st.session_state.dagitim_loglari)+1:03d}",
                                    "tarih": d_tarih_saat,
                                    "kisi": sv["kisi"],
                                    "menu": menu_adi_toplu,
                                    "porsiyon": sv["porsiyon"],
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                })
                                eklenen_sayisi += 1
                        
                        dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                        st.success(f"🎉 Başarılı! Seçilen {eklenen_sayisi} haneye yemek dağıtımı işlendi.")
                        st.balloons()
                        st.rerun()

            st.markdown("---")
            st.subheader("📋 Kayıtlı Yemek Dağıtımları Tablosu")
            
            dagitim_gosterim_listesi = []
            for idx, d in enumerate(st.session_state.dagitim_loglari):
                tarih_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Tarih/Saat" in aktif_k_maskeleri else d.get("tarih", "-")
                kisi_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Kişi/Hane" in aktif_k_maskeleri else d.get("kisi", "-")
                menu_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Menü" in aktif_k_maskeleri else d.get("menu", "-")
                porsiyon_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Porsiyon" in aktif_k_maskeleri else d.get("porsiyon", 1)

                dagitim_gosterim_listesi.append({
                    "Kayıt No": f"DAG-{idx:03d}",
                    "Tarih / Saat": tarih_maskele_d,
                    "Kişi / Hane": kisi_maskele_d,
                    "Menü": menu_maskele_d,
                    "Porsiyon": porsiyon_maskele_d,
                    "İşlemi Yapan": d.get("islem_yapan", "admin"),
                })

            excel_dag_data = tablo_to_excel_bytes(
                dagitim_gosterim_listesi, "Aziziye Aşevi - Yemek Dağıtım Listesi"
            )
            pdf_dag_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Yemek Dağıtım Listesi", dagitim_gosterim_listesi
            )

            with col_indir_dag:
                ortak_indirme_alani(
                    excel_dag_data,
                    pdf_dag_data,
                    "yemek_dagitim_listesi",
                    "dagitim_sayfasi",
                )

            if dagitim_gosterim_listesi:
                ozel_html_tablo_goster(dagitim_gosterim_listesi)
            else:
                st.info("Kayıtlı yemek dağıtımı bulunmuyor.")

        with tab3:
            col_b_sayac, col_indir_sayac = st.columns([2, 2])
            with col_b_sayac:
                st.subheader("📊 Kişi Bazlı Günlük, Haftalık ve Aylık Sayaç Raporu")

            simdi_dt = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")) if hasattr(datetime, "datetime") else datetime.datetime.now()
            bugun_str = simdi_dt.strftime("%Y-%m-%d")
            yedi_gun_once = (simdi_dt - datetime.timedelta(days=7)).date()
            bu_yil_ay = simdi_dt.strftime("%Y-%m")

            sayac_tablosu = []
            excel_sayac_liste = []

            for k in st.session_state.ihtiyac_sahipleri:
                kisi_adi = k["ad_soyad"]
                k_loglari = [
                    d
                    for d in st.session_state.dagitim_loglari
                    if d.get("kisi") == kisi_adi
                ]

                gunluk_sefer = 0
                gunluk_porsiyon = 0
                haftalik_sefer = 0
                haftalik_porsiyon = 0
                aylik_sefer = 0
                aylik_porsiyon = 0

                for d in k_loglari:
                    tarih_saat_str = d.get("tarih", "")
                    pors = int(d.get("porsiyon", 1))
                    if not tarih_saat_str:
                        continue
                    try:
                        d_tarih = datetime.datetime.strptime(
                            tarih_saat_str.split()[0], "%Y-%m-%d"
                        ).date()
                    except:
                        continue

                    if tarih_saat_str.startswith(bugun_str):
                        gunluk_sefer += 1
                        gunluk_porsiyon += pors

                    if yedi_gun_once <= d_tarih <= simdi_dt.date():
                        haftalik_sefer += 1
                        haftalik_porsiyon += pors

                    if tarih_saat_str.startswith(bu_yil_ay):
                        aylik_sefer += 1
                        aylik_porsiyon += pors

                tc_hane_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "-")
                kisi_ad_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - İhtiyaç Sahibi" in aktif_k_maskeleri else kisi_adi
                gunluk_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Günlük Alım" in aktif_k_maskeleri else f"{gunluk_sefer} Kez / {gunluk_porsiyon} Pors."
                haftalik_maskele = "🔒 Gizli" if "4. Sayfa: Haftalık Alım" in aktif_k_maskeleri else f"{haftalik_sefer} Kez / {haftalik_porsiyon} Pors."
                aylik_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Aylık Alım" in aktif_k_maskeleri else f"{aylik_sefer} Kez / {aylik_porsiyon} Pors."

                sayac_tablosu.append({
                    "T.C. / Hane No": tc_hane_maskele,
                    "İhtiyaç Sahibi": kisi_ad_maskele,
                    "Günlük Alım (Kez / Porsiyon)": gunluk_maskele,
                    "Haftalık Alım (Kez / Porsiyon)": haftalik_maskele,
                    "Aylık Alım (Kez / Porsiyon)": aylik_maskele,
                })

                excel_sayac_liste.append({
                    "T.C. / Hane No": tc_hane_maskele,
                    "İhtiyaç Sahibi": kisi_ad_maskele,
                    "Günlük Kez": gunluk_sefer,
                    "Günlük Porsiyon": gunluk_porsiyon,
                    "Haftalık Kez": haftalik_sefer,
                    "Haftalık Porsiyon": haftalik_porsiyon,
                    "Aylık Kez": aylik_sefer,
                    "Aylık Porsiyon": aylik_porsiyon,
                })

            excel_sayac_data = tablo_to_excel_bytes(
                excel_sayac_liste,
                "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
            )
            pdf_sayac_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
                excel_sayac_liste,
            )

            with col_indir_sayac:
                ortak_indirme_alani(
                    excel_sayac_data,
                    pdf_sayac_data,
                    "kisi_bazli_yemek_sayac_raporu",
                    "sayac_sayfasi",
                )

            if sayac_tablosu:
                ozel_html_tablo_goster(sayac_tablosu)
            else:
                st.info("Listelenecek ihtiyaç sahibi veya dağıtım verisi bulunmuyor.")

# 8. PERSONEL & ÇALIŞMA SÜRESİ TAKİBİ
elif menu == "Personel & Çalışma Süresi Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 Personel ve Çalışma Süresi Takibi")
        st.markdown(
            "Personel yönetimi, yıllık izinler, saatlik izinler, sağlık raporları ve resmi tatilleri bu ekrandan yönetebilirsiniz."
        )

        p_tab1, p_tab2, p_tab3, p_tab4, p_tab5 = st.tabs([
            "👨‍💼 Personel Listesi",
            "🏖️ Yıllık İzinler",
            "⏰ Saatlik İzinler",
            "🏥 Sağlık Raporları",
            "📊 Net Çalışma Raporu",
        ])

        with p_tab1:
            col_b_p_list, col_indir_p_list = st.columns([2, 2])
            with col_b_p_list:
                st.subheader("👨‍💼 Personel Kadrosu Listesi")

            if st.session_state.personel_silme_mesaji:
                st.success(st.session_state.personel_silme_mesaji)
                st.session_state.personel_silme_mesaji = ""

            bugun_tarihi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).date() if hasattr(datetime, "datetime") else datetime.date.today()
            p_gosterim = []
            for p in st.session_state.personeller:
                bas_tarih_str = p.get("baslama", "2026-01-01")
                try:
                    bas_dt = datetime.datetime.strptime(
                        bas_tarih_str, "%Y-%m-%d"
                    ).date()
                except:
                    bas_dt = datetime.date(2026, 1, 1)
                net_calisilan, _, _, _ = net_calisma_gunu_hesapla(
                    bas_dt,
                    bugun_tarihi,
                    p.get("izinler", []),
                    st.session_state.resmi_tatiller,
                )

                p_gosterim.append({
                    "T.C. No": p.get("tc", "-"),
                    "Adı Soyadı": p["ad_soyad"],
                    "Görevi": p["gorev"],
                    "İşe Başlama": bas_tarih_str,
                    "Çalışma Günü Sayacı": f"{net_calisilan} Gün",
                    "Durum": (
                        "Aktif Çalışıyor" if p.get("aktif", True) else "Pasif / Ayrıldı"
                    ),
                })

            excel_p_list_data = tablo_to_excel_bytes(
                p_gosterim, "Aziziye Aşevi - Personel Listesi"
            )
            pdf_p_list_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Personel Listesi", p_gosterim
            )

            with col_indir_p_list:
                ortak_indirme_alani(
                    excel_p_list_data,
                    pdf_p_list_data,
                    "personel_listesi_raporu",
                    "personel_list_sayfasi",
                )

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda yalnızca personel listesini görüntüleyebilirsiniz.")
            else:
                col_p_ekle, col_p_sil, col_p_durum = st.columns(3)
                with col_p_ekle:
                    with st.form("personel_ekle_form"):
                        st.markdown("**➕ Yeni Personel Ekle**")
                        p_tc = st.text_input("T.C. No").strip()
                        p_ad = st.text_input("Personel Adı Soyadı").strip().upper()
                        p_gorev = st.text_input("Görevi (Örn: Aşçı)")
                        p_bas = st.date_input(
                            "İşe Başlama Tarihi", value=datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).date() if hasattr(datetime, "datetime") else datetime.date.today()
                        )
                        p_submit = st.form_submit_button("Personeli Kaydet")

                        if p_submit and p_ad:
                            st.session_state.personeller.append({
                                "tc": p_tc if p_tc else "00000000000",
                                "ad_soyad": p_ad,
                                "gorev": p_gorev if p_gorev else "Personel",
                                "baslama": str(p_bas),
                                "aktif": True,
                                "izinler": [],
                            })
                            personelleri_kaydet(st.session_state.personeller)
                            st.success(f"🎉 Başarılı! {p_ad} eklendi.")
                            st.balloons()
                            st.rerun()

                with col_p_sil:
                    with st.form("personel_sil_form"):
                        st.markdown("**🗑️ Personeli Sil**")
                        if st.session_state.personeller:
                            p_sil_secenekleri = [
                                f"{p.get('tc', '---')} - {p['ad_soyad']}"
                                for p in st.session_state.personeller
                            ]
                            secilen_sil_p = st.selectbox("Silinecek Personel", p_sil_secenekleri)
                            p_sil_btn = st.form_submit_button(
                                "Personeli Kadrodan Sil", type="primary"
                            )

                            if p_sil_btn:
                                sil_tc = secilen_sil_p.split(" - ")[0]
                                silinen_obj = next(
                                    (
                                        p
                                        for p in st.session_state.personeller
                                        if p.get("tc") == sil_tc
                                    ),
                                    None,
                                )
                                silinen_ad = silinen_obj["ad_soyad"] if silinen_obj else ""
                                st.session_state.personeller = [
                                    p
                                    for p in st.session_state.personeller
                                    if p.get("tc") != sil_tc
                                ]
                                personelleri_kaydet(st.session_state.personeller)
                                st.session_state.personel_silme_mesaji = (
                                    f"🎉 Başarılı! {silinen_ad} silindi."
                                )
                                st.balloons()
                                st.rerun()
                        else:
                            st.info("Silinecek personel bulunmuyor.")

                with col_p_durum:
                    with st.form("durum_guncelle_form"):
                        st.markdown("**🔄 Durum Güncelle**")
                        if st.session_state.personeller:
                            p_secenekler = [
                                f"{p['ad_soyad']} ({'Aktif' if p.get('aktif', True) else 'Pasif'})"
                                for p in st.session_state.personeller
                            ]
                            secilen_p_str = st.selectbox(
                                "Personel Seç", p_secenekler, key="secilen_p_durum_box"
                            )
                            yeni_durum = st.radio(
                                "Durum",
                                ["Aktif Çalışıyor", "Pasif / Ayrıldı"],
                                horizontal=True,
                                key="yeni_durum_radio",
                            )
                            durum_guncelle_btn = st.form_submit_button(
                                "Durumu Güncelle", use_container_width=True
                            )

                            if durum_guncelle_btn:
                                secilen_isim = secilen_p_str.split(" (")[0]
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_isim:
                                        p["aktif"] = yeni_durum == "Aktif Çalışıyor"
                                personelleri_kaydet(st.session_state.personeller)
                                st.success("🎉 Başarılı! Durum güncellendi.")
                                st.balloons()
                                st.rerun()
                        else:
                            st.info("Kayıt yok.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Personel Kadrosu Tablosu")
            if p_gosterim:
                ozel_html_tablo_goster(p_gosterim)
            else:
                st.info("Kayıtlı personel bulunmuyor.")

        with p_tab2:
            col_b_yil, col_indir_yil = st.columns([2, 2])
            with col_b_yil:
                st.subheader("🏖️ Yıllık İzin Yönetimi (Ekle & Sil)")

            yillik_tablo_listesi = []
            for p in st.session_state.personeller:
                for iz in p.get("izinler", []):
                    if iz.get("tur") == "Yıllık İzin":
                        yillik_tablo_listesi.append({
                            "Personel": p["ad_soyad"],
                            "İzin Türü": "Yıllık İzin",
                            "Başlangıç": iz.get("baslangic", "-"),
                            "Bitiş": iz.get("bitis", "-"),
                        })

            excel_yil_data = tablo_to_excel_bytes(
                yillik_tablo_listesi, "Aziziye Aşevi - Yıllık İzinler"
            )
            pdf_yil_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Yıllık İzinler", yillik_tablo_listesi
            )

            with col_indir_yil:
                ortak_indirme_alani(
                    excel_yil_data,
                    pdf_yil_data,
                    "yillik_izinler_raporu",
                    "yillik_izin_sayfasi",
                )

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda izin ekleyemez veya silemezsiniz.")
            elif not yonetici_modu:
                st.warning("⚠️ Yıllık izin işlemleri yalnızca **Admin** tarafından yapılabilir.")
            else:
                col_y_ekle, col_y_sil = st.columns(2)
                with col_y_ekle:
                    with st.form("yillik_izin_form"):
                        st.markdown("**➕ Yıllık İzin Ekle**")
                        p_izin_secenekleri = [
                            p["ad_soyad"]
                            for p in st.session_state.personeller
                            if p.get("aktif", True)
                        ]
                        if p_izin_secenekleri:
                            secilen_p = st.selectbox(
                                "Personel Seçin", p_izin_secenekleri, key="yil_p"
                            )
                            i_bas = st.date_input("İzin Başlangıç Tarihi", key="yil_bas")
                            i_bit = st.date_input("İzin Bitiş Tarihi", key="yil_bit")
                            yil_submit = st.form_submit_button("Yıllık İzni Kaydet")

                            if yil_submit:
                                if i_bas > i_bit:
                                    st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                                else:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_p:
                                            if "izinler" not in p:
                                                p["izinler"] = []
                                            p["izinler"].append({
                                                "tur": "Yıllık İzin",
                                                "baslangic": str(i_bas),
                                                "bitis": str(i_bit),
                                            })
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! İzin kaydedildi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Aktif personel bulunmuyor.")

                with col_y_sil:
                    with st.form("yillik_izin_sil_form"):
                        st.markdown("**🗑️ Yıllık İzin Sil**")
                        tum_yillik_izinler = []
                        for p in st.session_state.personeller:
                            for idx, iz in enumerate(p.get("izinler", [])):
                                if iz.get("tur") == "Yıllık İzin":
                                    tum_yillik_izinler.append({
                                        "personel": p["ad_soyad"],
                                        "idx": idx,
                                        "ozet": (
                                            f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} - Bitiş: {iz['bitis']}"
                                        ),
                                    })

                        if tum_yillik_izinler:
                            secenek_sil_y = [item["ozet"] for item in tum_yillik_izinler]
                            secilen_sil_y_str = st.selectbox(
                                "Silinecek İzni Seçin", secenek_sil_y
                            )
                            y_sil_btn = st.form_submit_button(
                                "Seçilen İzni Sil", type="primary"
                            )

                            if y_sil_btn:
                                secilen_item = next(
                                    (
                                        item
                                        for item in tum_yillik_izinler
                                        if item["ozet"] == secilen_sil_y_str
                                    ),
                                    None,
                                )
                                if secilen_item:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_item["personel"]:
                                            yilliklar = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") == "Yıllık İzin"
                                            ]
                                            digerleri = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") != "Yıllık İzin"
                                            ]
                                            silinecek_hedef = yilliklar[secilen_item["idx"]]
                                            p["izinler"] = digerleri + [
                                                i for i in yilliklar if i != silinecek_hedef
                                            ]
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! İzin silindi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Silinebilecek yıllık izin kaydı bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Tüm Yıllık İzinler Tablosu")
            if yillik_tablo_listesi:
                ozel_html_tablo_goster(yillik_tablo_listesi)
            else:
                st.info("Kayıtlı yıllık izin bulunmuyor.")

        with p_tab3:
            col_b_saat, col_indir_saat = st.columns([2, 2])
            with col_b_saat:
                st.subheader("⏰ Saatlik İzin Yönetimi (Ekle & Sil)")

            saatlik_tablo_listesi = []
            for p in st.session_state.personeller:
                for iz in p.get("izinler", []):
                    if iz.get("tur") == "Saatlik İzin":
                        saatlik_tablo_listesi.append({
                            "Personel": p["ad_soyad"],
                            "İzin Türü": "Saatlik İzin",
                            "Tarih": iz.get("baslangic", "-"),
                            "Süre (Saat)": iz.get("saat", 0),
                            "Detay": iz.get("detay", "-"),
                        })

            excel_saat_data = tablo_to_excel_bytes(
                saatlik_tablo_listesi, "Aziziye Aşevi - Saatlik İzinler"
            )
            pdf_saat_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Saatlik İzinler", saatlik_tablo_listesi
            )

            with col_indir_saat:
                ortak_indirme_alani(
                    excel_saat_data,
                    pdf_saat_data,
                    "saatlik_izinler_raporu",
                    "saatlik_izin_sayfasi",
                )

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda saatlik izin ekleyemez veya silemezsiniz.")
            elif not yonetici_modu:
                st.warning("⚠️ Saatlik izin işlemleri yalnızca **Admin** tarafından yapılabilir.")
            else:
                col_s_ekle, col_s_sil = st.columns(2)
                with col_s_ekle:
                    with st.form("saatlik_izin_form"):
                        st.markdown("**➕ Saatlik İzin Ekle**")
                        p_saat_secenekleri = [
                            p["ad_soyad"]
                            for p in st.session_state.personeller
                            if p.get("aktif", True)
                        ]
                        if p_saat_secenekleri:
                            secilen_p_saat = st.selectbox(
                                "Personel Seçin", p_saat_secenekleri, key="saat_p"
                            )
                            s_tarih = st.date_input("İzin Tarihi", key="saat_tarih")
                            col_saat1, col_saat2 = st.columns(2)
                            with col_saat1:
                                s_bas_saat = st.time_input(
                                    "Başlangıç Saati", value=datetime.time(9, 0)
                                )
                            with col_saat2:
                                s_bit_saat = st.time_input(
                                    "Bitiş Saati", value=datetime.time(11, 0)
                                )
                            s_aciklama = st.text_input("Gerekçe / Açıklama", "Örn: Özel iş")
                            saat_submit = st.form_submit_button("Saatlik İzni Kaydet")

                            if saat_submit:
                                t1 = datetime.datetime.combine(s_tarih, s_bas_saat)
                                t2 = datetime.datetime.combine(s_tarih, s_bit_saat)
                                fark_saat = (t2 - t1).total_seconds() / 3600.0
                                if fark_saat <= 0:
                                    st.error("Bitiş saati başlangıçtan sonra olmalıdır!")
                                else:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_p_saat:
                                            if "izinler" not in p:
                                                p["izinler"] = []
                                            p["izinler"].append({
                                                "tur": "Saatlik İzin",
                                                "baslangic": str(s_tarih),
                                                "bitis": str(s_tarih),
                                                "saat": round(fark_saat, 2),
                                                "detay": (
                                                    f"{s_bas_saat.strftime('%H:%M')} - {s_bit_saat.strftime('%H:%M')} ({s_aciklama})"
                                                ),
                                            })
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! Saatlik izin kaydedildi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Aktif personel bulunmuyor.")

                with col_s_sil:
                    with st.form("saatlik_izin_sil_form"):
                        st.markdown("**🗑️ Saatlik İzin Sil**")
                        tum_saatlik_izinler = []
                        for p in st.session_state.personeller:
                            for idx, iz in enumerate(p.get("izinler", [])):
                                if iz.get("tur") == "Saatlik İzin":
                                    tum_saatlik_izinler.append({
                                        "personel": p["ad_soyad"],
                                        "idx": idx,
                                        "ozet": (
                                            f"{p['ad_soyad']} | Tarih: {iz['baslangic']} - Süre: {iz['saat']} Saat ({iz.get('detay', '-')})"
                                        ),
                                    })

                        if tum_saatlik_izinler:
                            secenek_sil_s = [item["ozet"] for item in tum_saatlik_izinler]
                            secilen_sil_s_str = st.selectbox(
                                "Silinecek Saatlik İzni Seçin", secenek_sil_s
                            )
                            s_sil_btn = st.form_submit_button(
                                "Seçilen Saatlik İzni Sil", type="primary"
                            )

                            if s_sil_btn:
                                secilen_item = next(
                                    (
                                        item
                                        for item in tum_saatlik_izinler
                                        if item["ozet"] == secilen_sil_s_str
                                    ),
                                    None,
                                )
                                if secilen_item:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_item["personel"]:
                                            saatlikler = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") == "Saatlik İzin"
                                            ]
                                            digerleri = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") != "Saatlik İzin"
                                            ]
                                            silinecek_hedef_s = saatlikler[secilen_item["idx"]]
                                            p["izinler"] = digerleri + [
                                                i for i in saatlikler if i != silinecek_hedef_s
                                            ]
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! Saatlik izin silindi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Silinebilecek saatlik izin kaydı bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Tüm Saatlik İzinler Tablosu")
            if saatlik_tablo_listesi:
                ozel_html_tablo_goster(saatlik_tablo_listesi)
            else:
                st.info("Kayıtlı saatlik izin bulunmuyor.")

        with p_tab4:
            col_b_rap, col_indir_rap = st.columns([2, 2])
            with col_b_rap:
                st.subheader("🏥 Sağlık Raporları Yönetimi (Ekle & Sil)")

            rapor_tablo_listesi = []
            for p in st.session_state.personeller:
                for iz in p.get("izinler", []):
                    if iz.get("tur") == "Sağlık Raporu":
                        rapor_tablo_listesi.append({
                            "Personel": p["ad_soyad"],
                            "İzin Türü": "Sağlık Raporu",
                            "Başlangıç": iz.get("baslangic", "-"),
                            "Bitiş": iz.get("bitis", "-"),
                        })

            excel_rap_data = tablo_to_excel_bytes(
                rapor_tablo_listesi, "Aziziye Aşevi - Sağlık Raporları"
            )
            pdf_rap_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Sağlık Raporları", rapor_tablo_listesi
            )

            with col_indir_rap:
                ortak_indirme_alani(
                    excel_rap_data,
                    pdf_rap_data,
                    "saglik_raporlari_raporu",
                    "saglik_rapor_sayfasi",
                )

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda sağlık raporu ekleyemez veya silemezsiniz.")
            elif not yonetici_modu:
                st.warning("⚠️ Sağlık raporu işlemleri yalnızca **Admin** tarafından yapılabilir.")
            else:
                col_r_ekle, col_r_sil = st.columns(2)
                with col_r_ekle:
                    with st.form("saglik_rapor_form"):
                        st.markdown("**➕ Sağlık Raporu Ekle**")
                        p_rapor_secenekleri = [
                            p["ad_soyad"]
                            for p in st.session_state.personeller
                            if p.get("aktif", True)
                        ]
                        if p_rapor_secenekleri:
                            secilen_p_rapor = st.selectbox(
                                "Personel Seçin", p_rapor_secenekleri, key="rap_p"
                            )
                            r_bas = st.date_input("Rapor Başlangıç Tarihi", key="rap_bas")
                            r_bit = st.date_input("Rapor Bitiş Tarihi", key="rap_bit")
                            rapor_submit = st.form_submit_button("Sağlık Raporunu Kaydet")

                            if rapor_submit:
                                if r_bas > r_bit:
                                    st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                                else:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_p_rapor:
                                            if "izinler" not in p:
                                                p["izinler"] = []
                                            p["izinler"].append({
                                                "tur": "Sağlık Raporu",
                                                "baslangic": str(r_bas),
                                                "bitis": str(r_bit),
                                            })
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! Sağlık raporu kaydedildi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Aktif personel bulunmuyor.")

                with col_r_sil:
                    with st.form("saglik_rapor_sil_form"):
                        st.markdown("**🗑️ Sağlık Raporu Sil**")
                        tum_saglik_raporlari = []
                        for p in st.session_state.personeller:
                            for idx, iz in enumerate(p.get("izinler", [])):
                                if iz.get("tur") == "Sağlık Raporu":
                                    tum_saglik_raporlari.append({
                                        "personel": p["ad_soyad"],
                                        "idx": idx,
                                        "ozet": (
                                            f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} - Bitiş: {iz['bitis']}"
                                        ),
                                    })

                        if tum_saglik_raporlari:
                            secenek_sil_r = [item["ozet"] for item in tum_saglik_raporlari]
                            secilen_sil_r_str = st.selectbox(
                                "Silinecek Raporu Seçin", secenek_sil_r
                            )
                            r_sil_btn = st.form_submit_button(
                                "Seçilen Sağlık Raporunu Sil", type="primary"
                            )

                            if r_sil_btn:
                                secilen_item = next(
                                    (
                                        item
                                        for item in tum_saglik_raporlari
                                        if item["ozet"] == secilen_sil_r_str
                                    ),
                                    None,
                                )
                                if secilen_item:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_item["personel"]:
                                            raporlar = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") == "Sağlık Raporu"
                                            ]
                                            digerleri = [
                                                i
                                                for i in p["izinler"]
                                                if i.get("tur") != "Sağlık Raporu"
                                            ]
                                            silinecek_hedef_r = raporlar[secilen_item["idx"]]
                                            p["izinler"] = digerleri + [
                                                i for i in raporlar if i != silinecek_hedef_r
                                            ]
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("🎉 Başarılı! Sağlık raporu silindi.")
                                    st.balloons()
                                    st.rerun()
                        else:
                            st.info("Silinebilecek sağlık raporu kaydı bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Tüm Sağlık Raporları Tablosu")
            if rapor_tablo_listesi:
                ozel_html_tablo_goster(rapor_tablo_listesi)
            else:
                st.info("Kayıtlı sağlık raporu bulunmuyor.")

        with p_tab5:
            col_b_net, col_indir_net = st.columns([2, 2])
            with col_b_net:
                st.subheader("📊 Net Çalışma Süresi ve İzin / Rapor Özeti Raporu")

            col_ay1, col_ay2 = st.columns(2)
            with col_ay1:
                baslangic_filtresi = st.date_input(
                    "Rapor Başlangıç Tarihi",
                    value=datetime.date(datetime.date.today().year, 1, 1),
                )
            with col_ay2:
                bitis_filtresi = st.date_input(
                    "Rapor Bitiş Tarihi", value=datetime.date.today()
                )

            net_rapor_listesi = []
            excel_net_listesi = []
            for p in st.session_state.personeller:
                bas_str = p.get("baslama", "2026-01-01")
                try:
                    p_bas_dt = datetime.datetime.strptime(bas_str, "%Y-%m-%d").date()
                except:
                    p_bas_dt = datetime.date(2026, 1, 1)

                efektif_bas = max(baslangic_filtresi, p_bas_dt)
                efektif_bit = bitis_filtresi

                net_gun, izin_gunu, rapor_gunu, saatlik_izin_saat = (
                    net_calisma_gunu_hesapla(
                        efektif_bas,
                        efektif_bit,
                        p.get("izinler", []),
                        st.session_state.resmi_tatiller,
                    )
                )

                net_rapor_listesi.append({
                    "T.C. No": p.get("tc", "-"),
                    "Personel": p["ad_soyad"],
                    "Görevi": p["gorev"],
                    "Net Çalışılan Gün": f"{net_gun} Gün",
                    "Yıllık / Tam Gün İzin": f"{izin_gunu} Gün",
                    "Sağlık Raporu": f"{rapor_gunu} Gün",
                    "Saatlik İzin": f"{saatlik_izin_saat} Saat",
                })

                excel_net_listesi.append({
                    "T.C. No": p.get("tc", "-"),
                    "Personel": p["ad_soyad"],
                    "Görevi": p["gorev"],
                    "Net Çalışılan Gün": net_gun,
                    "Yıllık / Tam Gün İzin Gün": izin_gunu,
                    "Sağlık Raporu Gün": rapor_gunu,
                    "Saatlik İzin Saat": saatlik_izin_saat,
                })

            excel_net_data = tablo_to_excel_bytes(
                excel_net_listesi, "Aziziye Aşevi - Net Çalışma Raporu"
            )
            pdf_net_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Net Çalışma Raporu", excel_net_listesi
            )

            with col_indir_net:
                ortak_indirme_alani(
                    excel_net_data,
                    pdf_net_data,
                    "net_calisma_suresi_raporu",
                    "net_calisma_sayfasi",
                )

            if net_rapor_listesi:
                ozel_html_tablo_goster(net_rapor_listesi)
            else:
                st.info("Raporlanacak personel verisi bulunmuyor.")

# 9. KULLANIM TAKİBİ
elif menu == "Kullanım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_kullanim, col_indir_kullanim = st.columns([2, 2])
        with col_b_kullanim:
            st.header("📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi")

        if st.session_state.kullanim_loglari:
            log_tablosu = []
            for log in reversed(st.session_state.kullanim_loglari):
                log_tablosu.append({
                    "Tarih / Saat": log.get("tarih", "-"),
                    "İşlem Türü / Açıklama": log.get("tur", "-"),
                    "Ürün / Malzeme": log.get("urun", "-"),
                    "Miktar": f"{log.get('miktar', 0)}",
                    "Tutar": f"{log.get('tutar', 0):,.2f} ₺",
                    "İşlemi Yapan": log.get("islem_yapan", "admin"),
                })

            excel_log_data = tablo_to_excel_bytes(
                log_tablosu, "Aziziye Aşevi - Sistem Kullanım Logları"
            )
            pdf_log_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Sistem Kullanım Logları", log_tablosu
            )

            with col_indir_kullanim:
                ortak_indirme_alani(
                    excel_log_data,
                    pdf_log_data,
                    "sistem_kullanim_loglari_arsivi",
                    "kullanim_sayfasi",
                )

            ozel_html_tablo_goster(log_tablosu)
        else:
            st.info("Henüz sistemde kayıtlı kullanım logu bulunmuyor.")

# 10. KAPSAMLI ENVANTER VE HAREKET RAPORU
elif menu == "Kapsamlı Envanter ve Hareket Raporu":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_env, col_indir_env = st.columns([2, 2])
        with col_b_env:
            st.header("📋 Kapsamlı Envanter ve Hareket Raporu")

        kapsamli_liste = []
        for g in st.session_state.girisler:
            kapsamli_liste.append({
                "Kayıt ID": g.get("id", "-"),
                "Tarih": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Ürün Adı": g.get("urun", "-"),
                "Kategori": g.get("kategori", "-"),
                "Depo": g.get("depo", "-"),
                "Alınan Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                "Kalan Miktar": f"{g.get('kalan', 0)} {g.get('birim', 'Kg')}",
                "Birim Fiyat": f"{g.get('fiyat', 0):,.2f} ₺",
                "Toplam Değer": f"{(g.get('kalan', 0) * g.get('fiyat', 0)):,.2f} ₺",
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })

        excel_kapsamli_data = tablo_to_excel_bytes(
            kapsamli_liste, "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu"
        )
        pdf_kapsamli_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu", kapsamli_liste
        )

        with col_indir_env:
            ortak_indirme_alani(
                excel_kapsamli_data,
                pdf_kapsamli_data,
                "kapsamli_envanter_ve_hareket_raporu",
                "kapsamli_envanter_sayfasi",
            )

        if kapsamli_liste:
            ozel_html_tablo_goster(kapsamli_liste)
        else:
            st.info("Kapsamlı rapor için kayıt bulunmuyor.")

# 11. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_fiy, col_indir_fiy = st.columns([2, 2])
    with col_b_fiy:
        st.header("💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi")

    benzersiz_urunler_fiyat = sorted(
        list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
    )

    if benzersiz_urunler_fiyat:
        secilen_fiyat_urun = st.selectbox(
            "Analiz Edilecek Ürünü Seçin", benzersiz_urunler_fiyat
        )
        urun_kayitlari = [
            g
            for g in st.session_state.girisler
            if g.get("urun", "").strip().upper() == secilen_fiyat_urun.strip().upper()
        ]

        fiyat_analiz_tablosu = []
        excel_fiyat_analiz = []
        for g in urun_kayitlari:
            fiyat_degeri = g.get("fiyat", 0)
            gosterilen_fiyat = "🔒 Gizli" if "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu" in aktif_k_maskeleri else f"{fiyat_degeri:,.2f} ₺"
            fiyat_analiz_tablosu.append({
                "Alım Tarihi": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Depo": g.get("depo", "-"),
                "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                "Birim Fiyat": gosterilen_fiyat,
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })
            excel_fiyat_analiz.append({
                "Alım Tarihi": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Depo": g.get("depo", "-"),
                "Miktar": g.get("miktar", 0),
                "Birim Fiyat (TL)": fiyat_degeri,
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })

        excel_fiy_data = tablo_to_excel_bytes(
            excel_fiyat_analiz, f"Aziziye Aşevi - {secilen_fiyat_urun} Fiyat Analizi"
        )
        pdf_fiy_data = tablo_to_html_pdf_bytes(
            f"Aziziye Aşevi - {secilen_fiyat_urun} Fiyat Analizi", excel_fiyat_analiz
        )

        with col_indir_fiy:
            ortak_indirme_alani(
                excel_fiy_data,
                pdf_fiy_data,
                f"urun_fiyat_analizi_{secilen_fiyat_urun.lower()}",
                "fiyat_analiz_sayfasi",
            )

        ozel_html_tablo_goster(fiyat_analiz_tablosu)
    else:
        st.info("Analiz edilecek ürün kaydı bulunmuyor.")

# 11. KULLANICI AYARLARI VE DETAYLI HASSAS ALAN MASKELEME YÖNETİMİ
elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz yalnızca **Admin** kullanıcısına aittir.")
    else:
        st.header("⚙️ Kullanıcı Yetkileri, Menü Kısıtlamaları ve Hassas Alan Maskeleme")
        st.markdown(
            "Sistem kullanıcılarını yönetebilir, yeni kullanıcı ekleyebilir, mevcut kullanıcıları silebilir; belirttiğiniz kritik sayfalar ve metrikler üzerinde hassas alan maskeleme kurallarını yönetebilirsiniz."
        )

        # Veritabanı ve tip güvenliği kontrolü
        if "kullanicilar" not in st.session_state:
            st.session_state.kullanicilar = {}

        for k_key, k_val in st.session_state.kullanicilar.items():
            if not isinstance(k_val.get("maskeli_alanlar"), dict):
                k_val["maskeli_alanlar"] = {}
            if not isinstance(k_val.get("yasakli_menuler"), list):
                k_val["yasakli_menuler"] = []

        st.markdown("---")
        st.subheader("📋 1. Aktif Kullanıcılar ve Yetki Matrisi")
        
        kullanici_db = st.session_state.kullanicilar
        
        if len(kullanici_db) > 0:
            table_rows = []
            for k_adi, k_obj in kullanici_db.items():
                gizli_alanlar = k_obj.get("maskeli_alanlar", {})
                gizlenen_ozet = []
                if isinstance(gizli_alanlar, dict):
                    for sayfa, sutunlar in gizli_alanlar.items():
                        if sutunlar:
                            gizlenen_ozet.append(f"{sayfa}: {', '.join(sutunlar)}")
                        
                table_rows.append({
                    "Kullanıcı Adı": k_adi,
                    "Rol": "Admin" if k_adi == "admin" else k_obj.get("rol", "Personel"),
                    "Salt Okunur": "Evet" if k_obj.get("salt_okunur", False) else "Hayır",
                    "Maskelenen Hassas Alanlar": " | ".join(gizlenen_ozet) if gizlenen_ozet else "Yok",
                    "Yasaklı Menüler": ", ".join(k_obj.get("yasakli_menuler", [])) if k_obj.get("yasakli_menuler") else "Yok"
                })
            
            df_kullanicilar = pd.DataFrame(table_rows)
            st.dataframe(df_kullanicilar, use_container_width=True, hide_index=True)
        else:
            st.info("Sistemde kayıtlı kullanıcı bulunmuyor.")

        st.markdown("---")
        st.subheader("🛠️ 2. Kullanıcı Düzenle, Yetki Ver ve Hassas Alan Maskele")

        yonetilebilir_kullanicilar = [k for k in kullanici_db.keys() if k != "admin"]

        if yonetilebilir_kullanicilar:
            secilen_k_adi = st.selectbox("İşlem Yapılacak Kullanıcıyı Seçin", yonetilebilir_kullanicilar, key="secilen_k_ozel_mask")
            
            if secilen_k_adi and secilen_k_adi in kullanici_db:
                k_obj = kullanici_db[secilen_k_adi]

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    mevcut_rol = k_obj.get("rol", "Personel")
                    rol_secenekleri = ["Personel", "Yönetim", "Misafir"]
                    rol_index = rol_secenekleri.index(mevcut_rol) if mevcut_rol in rol_secenekleri else 0
                    yeni_rol = st.selectbox("Kullanıcı Rolü", rol_secenekleri, index=rol_index, key=f"rol_ozel_{secilen_k_adi}")
                    yeni_salt_okunur = st.checkbox("Salt Okunur Özelliği (Veri Değiştiremez)", value=k_obj.get("salt_okunur", False), key=f"ro_ozel_{secilen_k_adi}")
                with col_d2:
                    kullaniciyi_sil = st.checkbox("⚠️ Bu kullanıcıyı sistemden kalıcı olarak çıkar / sil", value=False, key=f"sil_ozel_{secilen_k_adi}")

                st.markdown("---")
                st.markdown("### 🔒 Sizin Belirttiğiniz Kritik Sayfa ve Alanlar (Maskelenecekleri İşaretleyin)")
                st.markdown("Aşağıdaki alanların bu kullanıcı tarafından **gizlenmesini / yıldızlanmasını** istiyorsanız seçin:")

                # Sizin belirttiğiniz 6 özel alan listesi
                hassas_alanlar_yapisi = {
                    "Kurumsal Dashboard": ["Ürün Çeşidi", "Toplam Fire", "Stok Değeri", "Aktif Personel"],
                    "Güncel Stok": ["Kalan Miktar Sütunu"],
                    "Ürün Sil": ["Silinen Ürünler Arşivi"],
                    "Fire / Zayiat": ["Kayıtlı Fire ve Zayiatları Listesi"],
                    "Ürün Birim Fiyatları": ["Birim Fiyat Sütunu"],
                    "Günlük Yemek Üretimi": ["Maliyet Sütunu"]
                }

                mevcut_maskeler = k_obj.get("maskeli_alanlar", {})
                if not isinstance(mevcut_maskeler, dict):
                    mevcut_maskeler = {}

                yeni_maskeli_alanlar = {}

                for sayfa_adi, sutunlar in hassas_alanlar_yapisi.items():
                    st.markdown(f"**📂 Sayfa: {sayfa_adi}**")
                    secilen_sutunlar = []
                    s_cols = st.columns(len(sutunlar))
                    
                    mevcut_sayfa_yasaklari = mevcut_maskeler.get(sayfa_adi, [])
                    if not isinstance(mevcut_sayfa_yasaklari, list):
                        mevcut_sayfa_yasaklari = []
                    
                    for idx, sutun in enumerate(sutunlar):
                        with s_cols[idx]:
                            is_masked = st.checkbox(sutun, value=(sutun in mevcut_sayfa_yasaklari), key=f"ozel_mask_{secilen_k_adi}_{sayfa_adi}_{idx}")
                            if is_masked:
                                secilen_sutunlar.append(sutun)
                    
                    if secilen_sutunlar:
                        yeni_maskeli_alanlar[sayfa_adi] = secilen_sutunlar

                st.markdown("---")
                st.markdown("### 🚫 Sayfa / Menü Erişim Kısıtlamaları")
                tum_menu_ogeleri = [
                    "Güncel Stok Durumu", "Ürün Sil / Düzenle", "Fire / Zayiat Girişi", 
                    "Toplu Stok Düşümü & Sarfiyat", "İhtiyaç Sahibi & Yemek Dağıtım Takibi", 
                    "Personel & Çalışma Süresi Takibi", "Kullanım Takibi", 
                    "Kapsamlı Envanter ve Hareket Raporu", "Depo Yönetimi", "Demirbaş Yönetimi"
                ]
                
                mevcut_yasaklar = k_obj.get("yasakli_menuler", [])
                if not isinstance(mevcut_yasaklar, list):
                    mevcut_yasaklar = []

                yeni_yasaklar = []
                
                m_cols = st.columns(2)
                for idx, m_item in enumerate(tum_menu_ogeleri):
                    with m_cols[idx % 2]:
                        yasakli_mi = st.checkbox(m_item, value=(m_item in mevcut_yasaklar), key=f"ozel_yasak_{secilen_k_adi}_{idx}")
                        if yasakli_mi:
                            yeni_yasaklar.append(m_item)

                st.markdown("")
                if st.button("Değişiklikleri Kaydet / Uygula", type="primary", key=f"btn_ozel_kaydet_{secilen_k_adi}"):
                    if kullaniciyi_sil:
                        del st.session_state.kullanicilar[secilen_k_adi]
                        st.toast(f"🗑️ '{secilen_k_adi}' kullanıcısı sistemden silindi!", icon="✅")
                        st.rerun()
                    else:
                        st.session_state.kullanicilar[secilen_k_adi]["rol"] = yeni_rol
                        st.session_state.kullanicilar[secilen_k_adi]["salt_okunur"] = yeni_salt_okunur
                        st.session_state.kullanicilar[secilen_k_adi]["maskeli_alanlar"] = yeni_maskeli_alanlar
                        st.session_state.kullanicilar[secilen_k_adi]["yasakli_menuler"] = yeni_yasaklar
                        
                        st.toast(f"✅ '{secilen_k_adi}' kullanıcısının hassas alan ayarları kaydedildi!", icon="🎉")
                        st.rerun()
        else:
            st.info("Düzenlenebilecek ek kullanıcı bulunmuyor.")

        st.markdown("---")
        st.subheader("➕ 3. Yeni Sistem Kullanıcısı Ekle")
        
        yeni_k_adi = st.text_input("Kullanıcı Adı (Benzersiz)", key="yeni_k_adi_input_ozel")
        yeni_sifre = st.text_input("Şifre", type="password", key="yeni_sifre_input_ozel")
        
        y_col1, y_col2 = st.columns(2)
        with y_col1:
            yeni_k_rol = st.selectbox("Kullanıcı Rolü", ["Personel", "Yönetim", "Misafir"], key="yeni_rol_select_ozel")
        with y_col2:
            yeni_k_salt = st.checkbox("Salt Okunur Kullanıcı Yap", value=False, key="yeni_salt_chk_ozel")

        st.markdown("")
        if st.button("Yeni Kullanıcıyı Sisteme Ekle", type="secondary", key="btn_ozel_yeni_ekle"):
            if yeni_k_adi and yeni_sifre:
                if yeni_k_adi in st.session_state.kullanicilar:
                    st.error("Bu kullanıcı adı zaten sistemde mevcut!")
                else:
                    st.session_state.kullanicilar[yeni_k_adi] = {
                        "sifre": yeni_sifre,
                        "rol": yeni_k_rol,
                        "salt_okunur": yeni_k_salt,
                        "maskeli_alanlar": {},
                        "yasakli_menuler": []
                    }
                    st.toast(f"🎉 Yeni kullanıcı '{yeni_k_adi}' eklendi!", icon="✨")
                    st.rerun()
            else:
                st.error("Lütfen kullanıcı adı ve şifre alanlarını doldurun.")
