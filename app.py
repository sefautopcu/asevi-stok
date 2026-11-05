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
        return fernet_motoru.decrypt(str(sifreli_metin).encode("utf-8")).decode(
            "utf-8"
        )
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
    
    /* Yan Menü Arka Planı ve Çerçevesiz Tasarım */
    .stSidebar { 
        background-color: #000000 !important; 
        padding-top: 10px; 
        border-right: 1px solid #121212 !important;
    }
    .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
        color: #d1d5db !important; 
        font-size: 13.5px; 
    }
    
    /* Yan Menü Expander ve Buton Çerçevelerinin Kaldırılması & Liquid Glass Efekti */
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
    
    /* Liquid Glass Hover Efekti */
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 0 0 1px rgba(255, 255, 255, 0.05) !important;
        transform: translateX(4px);
    }
    
    /* Aktif Menü Butonu Stili */
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

    /* Ana Sayfa Butonları */
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
    
    /* AÇILIR SEÇİM MENÜLERİ VE TAKVİM İKONLARI (BEYAZ ÇİZGİ / OUTLINE DÖNÜŞÜMÜ) */
    div[data-baseweb="menu"], ul[role="listbox"], div[data-baseweb="popover"], div[data-baseweb="calendar"] {
        background: rgba(12, 12, 12, 0.85) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 16px 40px 0 rgba(0, 0, 0, 0.6) !important;
        border-radius: 14px !important;
    }
    
    /* Takvim ve Sistem İkonlarının Beyaz Çizgi (Outline) Görünümü */
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


varsayilan_girisler = [
    {
        "id": "STK-001",
        "tarih": "2026-09-28 08:30",
        "fatura_no": "FAT-2026-001",
        "urun": "KIRMIZI LAHANA",
        "kategori": "SEBZE",
        "birim": "Kg",
        "miktar": 42.8,
        "kalan": max(0.0, 42.8 - 15.0),
        "fiyat": 50.0,
        "depo": "Soğuk Hava Deposu +5/+6",
        "islem_yapan": "admin",
    },
    {
        "id": "STK-002",
        "tarih": "2026-09-28 08:35",
        "fatura_no": "FAT-2026-002",
        "urun": "MAYDANOZ",
        "kategori": "SEBZE",
        "birim": "Kg",
        "miktar": 20.0,
        "kalan": max(0.0, 20.0 - 3.1),
        "fiyat": 25.0,
        "depo": "Soğuk Hava Deposu +5/+6",
        "islem_yapan": "admin",
    },
]

varsayilan_loglar = [
    {
        "tarih": "2026-10-05 10:00",
        "urun": "ISPANAK",
        "tur": "Fire/Zayiat",
        "miktar": 60.0,
        "tutar": 4200.00,
        "islem_yapan": "admin",
    },
    {
        "tarih": "2026-10-09 10:00",
        "urun": "PATLICAN",
        "tur": "Fire/Zayiat",
        "miktar": 52.4,
        "tutar": 2882.00,
        "islem_yapan": "admin",
    },
    {
        "tarih": "2026-10-14 10:00",
        "urun": "MUZ",
        "tur": "Fire/Zayiat",
        "miktar": 54.5,
        "tutar": 5995.00,
        "islem_yapan": "admin",
    },
    {
        "tarih": "2026-10-20 10:00",
        "urun": "SALATALIK",
        "tur": "Fire/Zayiat",
        "miktar": 43.0,
        "tutar": 1935.00,
        "islem_yapan": "admin",
    },
    {
        "tarih": "2026-10-21 10:00",
        "urun": "TAM YAĞLI YOĞURT",
        "tur": "Fire/Zayiat",
        "miktar": 15.0,
        "tutar": 993.00,
        "islem_yapan": "admin",
    },
]

varsayilan_personeller = [
    {
        "tc": "11111111111",
        "ad_soyad": "MUHAMMED İLKER ÇELİK",
        "gorev": "Şoför",
        "baslama": "2026-10-12",
        "aktif": True,
        "izinler": [],
    },
    {
        "tc": "22222222222",
        "ad_soyad": "EMİRHAN DÖNMEZ",
        "gorev": "Şoför",
        "baslama": "2026-10-12",
        "aktif": True,
        "izinler": [],
    },
    {
        "tc": "33333333333",
        "ad_soyad": "SEDAT UZUN",
        "gorev": "Aşçı",
        "baslama": "2026-09-25",
        "aktif": True,
        "izinler": [],
    },
    {
        "tc": "44444444444",
        "ad_soyad": "BURAK AYAŞTI",
        "gorev": "Temizlik Personeli",
        "baslama": "2026-09-25",
        "aktif": True,
        "izinler": [],
    },
    {
        "tc": "55555555555",
        "ad_soyad": "HÜSEYİN KAYMAK",
        "gorev": "Aşçı Yardımcısı",
        "baslama": "2026-10-26",
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

varsayilan_kullanicilar = {
    "admin": {"sifre": "Ss123321", "tip": "admin", "yasakli_menuler": []},
    "asci": {"sifre": "sydv25", "tip": "personel", "yasakli_menuler": []},
    "yonetim": {"sifre": "Yonetim25", "tip": "personel", "yasakli_menuler": []},
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


def resmi_tatilleri_yukle():
    if os.path.exists(TATIL_DOSYASI):
        try:
            with open(TATIL_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_resmi_tatiller
    return varsayilan_resmi_tatiller


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
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu",
    "Yeni Mal Alımı / Fatura Ekle",
    "Ürün Sil / Düzenle",
    "Fire / Zayiat Girişi",
    "Ürün Birim Fiyatları & Ay Analizi",
    "Günlük Yemek Üretimi & Maliyet Raporu",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
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
    simdi = datetime.date.today()
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
# GİRİŞ KONTROLÜ / AÇILIŞ GİRİŞ EKRANI (Saf Siyah Tema)
# =========================================================================
if not st.session_state.oturum_aktif:
    st.markdown(
        "<div style='text-align: center; margin-top: 50px;'></div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown(
            """
                <div style="text-align: center; margin-bottom: 24px;">
                    <h2 style="font-weight: 700; letter-spacing: -0.03em;">🍲 AZİZİYE AŞEVİ</h2>
                    <p style="opacity: 0.7; font-size: 14px; margin-top: 4px; color: #d1d5db;">Yönetim Paneli</p>
                </div>
            """,
            unsafe_allow_html=True,
        )

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
                if (
                    k_adi_inp in kullanici_db
                    and kullanici_db[k_adi_inp]["sifre"] == sifre_inp
                ):
                    st.session_state.oturum_aktif = True
                    st.session_state.aktif_kullanici = k_adi_inp
                    st.query_params["auth"] = "true"
                    st.query_params["user"] = k_adi_inp
                    st.success(f"{k_adi_inp.upper()} olarak giriş yapıldı!")
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")

        st.markdown(
            "<div style='text-align: center; margin: 16px 0; opacity: 0.5; font-size:"
            " 13px;'>veya</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.oturum_aktif = True
            st.session_state.aktif_kullanici = "misafir"
            st.query_params["auth"] = "true"
            st.query_params["user"] = "misafir"
            st.rerun()

        st.markdown(
            "<div style='margin-top: 20px;'></div>", unsafe_allow_html=True
        )
        if st.button(
            "✉️ İletişim / Destek", use_container_width=True, type="secondary"
        ):
            st.info(
                "📩 İletişim için **sefaunaltopcu@gmail.com** mail adresi ile"
                " iletişime geçebilirsiniz."
            )

    st.stop()

# =========================================================================
# ANA UYGULAMA İÇERİĞİ
# =========================================================================
st.markdown("### 🍲 AZİZİYE - AŞEVİ TAKİP EKRANI ")
st.markdown(f"**Hoş geldiniz** &nbsp;|&nbsp; 📅 {bugunun_turkce_tarihi()}")
st.markdown("---")

# ----------------- SIDEBAR & AĞAÇ MENÜ BİLEŞENLERİ (Logo + Liquid Glass) -----------------
kullanici_adi_goruntule = (
    st.session_state.aktif_kullanici.upper()
    if st.session_state.oturum_aktif
    else "MİSAFİR"
)

# Yan Menünün En Üstüne Kurumsal Logo / Simgesi Eklendi
st.sidebar.markdown(
    """
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
    '<p style="font-size: 11px; font-weight: 700; margin-top: 12px;'
    ' margin-bottom: 8px; padding-left: 4px; opacity: 0.6; text-transform:'
    ' uppercase; letter-spacing: 0.05em; color: #9ca3af;">ÇALIŞMA ALANI'
    ' NAVİGASYONU</p>',
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
yonetim_modu = (
    st.session_state.oturum_aktif
    and st.session_state.aktif_kullanici == "yonetim"
)
salt_okunur_modu = misafir_modu or yonetim_modu

aktif_k_bilgi = st.session_state.kullanicilar.get(
    st.session_state.aktif_kullanici, {}
)
yasakli_menuler_listesi = aktif_k_bilgi.get("yasakli_menuler", [])

toplam_aktif_stok_sayisi = len(set(g["urun"] for g in st.session_state.girisler))
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
        ("Ürün Birim Fiyatları & Ay Analizi", ""),
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
    "📈 Raporlar & Arşiv": [("Kullanım Takibi", "")],
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
            "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
            "Personel & Çalışma Süresi Takibi",
            "Kullanım Takibi",
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

            btn_label = f"{m}  [{badge}]" if badge and badge != "0" else m
            btn_type = (
                "primary" if st.session_state.aktif_menu == m else "secondary"
            )
            if st.button(
                btn_label, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"
            ):
                st.session_state.aktif_menu = m
                st.query_params["menu"] = m
                st.rerun()

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
    '<p style="font-size: 11px; text-align: center; opacity: 0.5; color:'
    ' #9ca3af;">sefautopcu</p>',
    unsafe_allow_html=True,
)


def tablo_to_excel_bytes(veri_listesi, baslik_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapor"
    ws.views.sheetView[0].showGridLines = True
    header_fill = PatternFill(
        start_color="121212", end_color="121212", fill_type="solid"
    )
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="000000")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(
        left=Side(style="thin", color="2d2d2d"),
        right=Side(style="thin", color="2d2d2d"),
        top=Side(style="thin", color="2d2d2d"),
        bottom=Side(style="thin", color="2d2d2d"),
    )

    ws.cell(row=1, column=1, value=baslik_str).font = title_font
    ws.cell(
        row=2,
        column=1,
        value=f"Rapor Tarihi: {str(datetime.datetime.now())}",
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
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{baslik}</title>
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; margin: 30px; color: #ffffff; background: #000000; }}
            h2 {{ color: #ffffff; margin-bottom: 5px; }}
            p {{ color: #9ca3af; font-size: 14px; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #0c0c0c; }}
            th {{ background-color: #121212; color: white; padding: 12px; text-align: left; font-size: 13px; }}
            td {{ border: 1px solid #2d2d2d; padding: 10px 12px; font-size: 13px; color: #d1d5db; }}
            tr:nth-child(even) {{ background-color: #050505; }}
        </style>
    </head>
    <body>
        <h2>{baslik}</h2>
        <p>Rapor Tarihi: {datetime.datetime.now()}</p>
        <hr style="border: 0; border-top: 1px solid #2d2d2d;"/>
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


menu = st.session_state.aktif_menu

if not yonetici_modu and menu in yasakli_menuler_listesi:
    st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    st.stop()

# 0. KURUMSAL DASHBOARD & ÖZET
if menu == "Kurumsal Dashboard & Özet":
    toplam_stok_kalemi = len(set(g["urun"] for g in st.session_state.girisler))
    toplam_envanter_maliyeti = sum(
        g["kalan"] * g["fiyat"] for g in st.session_state.girisler
    )

    loglar = st.session_state.kullanim_loglari
    toplam_fire_mik = sum(
        l["miktar"] for l in loglar if l["tur"] == "Fire/Zayiat"
    )
    toplam_fire_tutar = sum(l["tutar"] for l in loglar if l["tur"] == "Fire/Zayiat")
    aktif_calisan_personel_sayisi = sum(
        1 for p in st.session_state.personeller if p.get("aktif", True)
    )

    card_bg = "#0c0c0c"
    card_border = "#222222"
    text_color = "#ffffff"
    subtext_color = "#9ca3af"

    st.markdown(
        f"""
        <style>
        .dashboard-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: {card_bg};
            border: 1px solid {card_border};
            padding: 28px 36px;
            border-radius: 20px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.9);
        }}
        .metric-card {{
            background: {card_bg};
            border: 1px solid {card_border};
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
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
                <p style="margin: 6px 0 0 0; color: {subtext_color}; font-size: 14px;">Aziziye Aşevi Saf Siyah Tasarım & Yönetim Paneli</p>
            </div>
            <div style="background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); padding: 8px 16px; border-radius: 10px; font-weight: 600; font-size: 12px;">
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
                    <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{toplam_stok_kalemi} <span style="font-size: 13px; font-weight: normal; color: {subtext_color};">Çeşit</span></div>
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
            st.markdown(
                f"""
                <div class="metric-card">
                    <div>
                        <div style="color: {subtext_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Toplam Fire</div>
                        <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{toplam_fire_mik:,.1f} <span style="font-size: 13px; font-weight: normal; color: {subtext_color};">Kg</span></div>
                    </div>
                    <div style="color: #f87171; font-size: 12px; font-weight: 600;">Zarar: {toplam_fire_tutar:,.0f} ₺</div>
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
                        <div style="color: {text_color}; font-size: 24px; font-weight: 700; margin-top: 8px;">{toplam_envanter_maliyeti:,.0f} <span style="font-size: 13px; font-weight: normal; color: {subtext_color};">₺</span></div>
                    </div>
                    <div style="color: #34d399; font-size: 12px; font-weight: 600;">💰 Güncel Maliyet</div>
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
                    <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 8px;">{aktif_calisan_personel_sayisi} <span style="font-size: 13px; font-weight: normal; color: {subtext_color};">Kişi</span></div>
                </div>
                <div style="color: #c084fc; font-size: 12px; font-weight: 600;">👥 Kadro Durumu</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='margin-top: 30px;'></div>", unsafe_allow_html=True
    )
    st.markdown(
        f"<h3 style='font-size: 16px; font-weight: 700; color:"
        f" {text_color}; margin-bottom: 16px;'>⚡ Hızlı İşlem Kısayolları</h3>",
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

    # DASHBOARD GRAFİK WIDGET ALANI
    st.markdown("---")
    st.markdown(
        f"<h3 style='font-size: 18px; font-weight: 700; color:"
        f" {text_color}; margin-top: 20px;'>📊 İnteraktif Dashboard Grafikleri"
        " ve Widget Alanı</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color: {subtext_color}; font-size: 13.5px;'>Aşağıda"
        " etkinleştirilmiş olan Saf Siyah kart tasarımlı grafikler"
        " görüntülenmektedir. Admin kullanıcıları yeni grafik widget'ı"
        " ekleyebilir veya mevcutları silebilir.</p>",
        unsafe_allow_html=True,
    )

    aktif_w_list = [
        w for w in st.session_state.dashboard_widgets if w.get("aktif", True)
    ]
    if aktif_w_list:
        for w in aktif_w_list:
            st.markdown(
                f"<div style='border: 1px solid {card_border}; background:"
                f" {card_bg}; padding: 24px; border-radius: 16px; margin-bottom:"
                " 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.8);'>",
                unsafe_allow_html=True,
            )
            st.markdown(f"#### {w['baslik']}")

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
                            title="Kategori Bazlı Kalan Stok Miktarları",
                            template="plotly_dark",
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
                            title="Zaman İçerisinde Fire ve Kullanım Maliyeti Trendi",
                            template="plotly_dark",
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
                        title="Ürün Bazlı Envanter Dağılımı",
                        template="plotly_dark",
                    )
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
                        st.rerun()
                else:
                    st.info("Kaldırılacak grafik bulunmuyor.")
    else:
        st.markdown(
            f"<p style='font-size: 12px; color: {subtext_color}; font-style:"
            " italic;'>🔒 Dashboard sayfasına yeni grafik ekleme / kaldırma yetkisi"
            " yalnızca <b>Admin</b> kullanıcısına özeldir.</p>",
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
            list(set(g["urun"] for g in st.session_state.girisler))
        )
        excel_liste = []
        for u in benzersiz_urunler_Excel:
            toplam_kalan_ex = sum(
                g["kalan"] for g in st.session_state.girisler if g["urun"] == u
            )
            kategori_ex = next(
                (g["kategori"] for g in st.session_state.girisler if g["urun"] == u),
                "GENEL",
            )
            birim_ex = next(
                (g["birim"] for g in st.session_state.girisler if g["urun"] == u),
                "Kg",
            )
            depo_ex = next(
                (g["depo"] for g in st.session_state.girisler if g["urun"] == u),
                "Merkez Depo",
            )
            islem_yapan_ex = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g["urun"] == u
                ),
                "admin",
            )
            en_son_tarih_ex = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g["urun"] == u
                ),
                default="-",
            )
            excel_liste.append({
                "Ürün Adı": u,
                "Kategori": kategori_ex,
                "Birim": birim_ex,
                "Kalan Miktar": toplam_kalan_ex,
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

        depolar = [
            "Tümü",
            "Soğuk Hava Deposu +5/+6",
            "Soğuk Hava Deposu -18",
            "Sebze Deposu",
            "Kuru Gıda Deposu",
        ]
        secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)

        benzersiz_urunler = sorted(
            list(set(g["urun"] for g in st.session_state.girisler))
        )
        stok_tablosu = []
        kritik_urunler = []
        for u in benzersiz_urunler:
            toplam_kalan = sum(
                g["kalan"] for g in st.session_state.girisler if g["urun"] == u
            )
            kategori = next(
                (g["kategori"] for g in st.session_state.girisler if g["urun"] == u),
                "GENEL",
            )
            birim = next(
                (g["birim"] for g in st.session_state.girisler if g["urun"] == u),
                "Kg",
            )
            depo = next(
                (g["depo"] for g in st.session_state.girisler if g["urun"] == u),
                "Merkez Depo",
            )
            islem_yapan = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g["urun"] == u
                ),
                "admin",
            )
            en_son_tarih = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g["urun"] == u
                ),
                default="-",
            )

            if secilen_depo == "Tümü" or depo == secilen_depo:
                stok_tablosu.append({
                    "Ürün Adı": u,
                    "Kategori": kategori,
                    "Birim": birim,
                    "Kalan Miktar": toplam_kalan,
                    "Depo Yeri": depo,
                    "Eklenme Tarihi": en_son_tarih,
                    "İşlemi Yapan": islem_yapan,
                })
            if toplam_kalan <= 10.0:
                kritik_urunler.append((u, toplam_kalan, birim, depo))

        if kritik_urunler:
            with st.expander(
                "⚠️ DİKKAT: Kritik Seviyedeki Veya Tükenen Ürünler!", expanded=False
            ):
                for ku, km, kb, kd in kritik_urunler:
                    st.warning(
                        f"**{ku}** stoğu azalmıştır! Kalan Miktar: **{km} {kb}** ({kd})"
                    )

        st.markdown("### Envanter Listesi")
        ozel_html_tablo_goster(stok_tablosu)

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    if salt_okunur_modu:
        st.warning(
            "⚠️ Bu sayfaya yalnızca gözlem amaçlı erişebilirsiniz. Salt okunur"
            " (Yönetim/Misafir) modda işlem yapamazsınız."
        )
    else:
        st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
        with st.form("fatura_formu"):
            tarih_giris = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            fatura_no_input = st.text_input(
                "Fatura No / Belge No (Örn: FAT-2026-105)"
            ).strip().upper()
            urun = st.text_input(
                "Ürün Adı (Örn: DOMATES - Büyük Harfle)"
            ).strip().upper()
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
            depo = st.selectbox(
                "Depo Yeri",
                [
                    "Soğuk Hava Deposu +5/+6",
                    "Soğuk Hava Deposu -18",
                    "Sebze Deposu",
                    "Kuru Gıda Deposu",
                ],
            )
            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)

            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted and urun:
                islem_yapan_kisi = st.session_state.aktif_kullanici
                fatura_no_degeri = (
                    fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
                )
                st.session_state.girisler.append({
                    "id": f"FAT-{len(st.session_state.girisler)+1:03d}",
                    "tarih": tarih_giris,
                    "fatura_no": fatura_no_degeri,
                    "urun": urun,
                    "kategori": kategori,
                    "birim": birim,
                    "miktar": miktar,
                    "kalan": miktar,
                    "fiyat": fiyat,
                    "depo": depo,
                    "islem_yapan": islem_yapan_kisi,
                })
                verileri_kaydet(st.session_state.girisler)
                st.success(f"Başarılı! {miktar} miktar {urun} depoya işlendi.")
                st.rerun()

        st.markdown("---")
        st.subheader("📋 Mal Alımı / Fatura Log Kayıtları Arşivi")
        if st.session_state.girisler:
            fatura_log_tablosu = []
            for g in reversed(st.session_state.girisler):
                fatura_log_tablosu.append({
                    "Kayıt ID": g.get("id", "-"),
                    "Eklenme Tarihi / Saati": g.get("tarih", "-"),
                    "Fatura No": g.get("fatura_no", "BELİRTİLMEMİŞ"),
                    "Ürün Adı": g.get("urun", "-"),
                    "Kategori": g.get("kategori", "-"),
                    "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                    "Birim Fiyat": f"{g.get('fiyat', 0):,.2f} ₺",
                    "Toplam Tutar": (
                        f"{(g.get('miktar', 0) * g.get('fiyat', 0)):,.2f} ₺"
                    ),
                    "Depo Yeri": g.get("depo", "-"),
                    "İşlemi Yapan": g.get("islem_yapan", "admin"),
                })
            ozel_html_tablo_goster(fatura_log_tablosu)
        else:
            st.info("Kayıtlı mal alımı faturası bulunmuyor.")

# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
        if salt_okunur_modu:
            st.warning(
                "👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda silme"
                " işlemi gerçekleştiremezsiniz."
            )
        elif not yonetici_modu:
            st.warning(
                "⚠️ Bu ekrana erişmek için **Admin** hesabıyla giriş yapmalısınız."
            )
        else:
            if st.session_state.silme_mesaji:
                st.success(st.session_state.silme_mesaji)
                st.session_state.silme_mesaji = ""
            if not st.session_state.girisler:
                st.info("Sistemde silinecek kayıt bulunmuyor.")
            else:
                with st.form("urun_silme_formu"):
                    secenekler = [
                        f"{g['id']} - {g['urun']} (Eklenme: {g.get('tarih', '-')},"
                        f" Kalan: {g['kalan']} {g['birim']})"
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
                                "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
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
                                f"Başarılı! {silinen_urun_adi} sistemden silindi."
                            )
                            st.rerun()

        st.markdown("---")
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
            st.warning(
                "👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda fire"
                " düşemezsiniz."
            )
        else:
            with st.form("fire_formu"):
                benzersiz_urunler = sorted(
                    list(set(g["urun"] for g in st.session_state.girisler))
                )
                secilen_gercek_urun = st.selectbox(
                    "Fire Düşülecek Ürünü Seçin", benzersiz_urunler
                )
                ilgili_girisler = [
                    g
                    for g in st.session_state.girisler
                    if g["urun"] == secilen_gercek_urun and g["kalan"] > 0
                ]
                toplam_stok = sum(g["kalan"] for g in ilgili_girisler)

                en_son_fiyat = 0.0
                if ilgili_girisler:
                    en_son_kayit = max(
                        ilgili_girisler, key=lambda x: x.get("tarih", "")
                    )
                    en_son_fiyat = en_son_kayit.get("fiyat", 0.0)

                st.info(
                    f"Mevcut Stok: {toplam_stok} | Güncel (En Son Fatura) Birim Fiyat:"
                    f" {en_son_fiyat:,.2f} ₺"
                )
                fire_miktari = st.number_input(
                    "Fire Miktarı",
                    min_value=0.0,
                    max_value=float(toplam_stok) if toplam_stok > 0 else 1.0,
                    step=0.1,
                )

                submitted_fire = st.form_submit_button("Fireyi Düş ve Kaydet")
                if submitted_fire and fire_miktari > 0:
                    kalan_dusulecek = fire_miktari

                    for g in ilgili_girisler:
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
                        "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "urun": secilen_gercek_urun,
                        "tur": "Fire/Zayiat",
                        "miktar": fire_miktari,
                        "tutar": toplam_zarar,
                        "islem_yapan": st.session_state.aktif_kullanici,
                    })
                    loglari_kaydet(st.session_state.kullanim_loglari)
                    st.success(
                        f"Fire başarıyla düşüldü. En son fatura fiyatı ({en_son_fiyat:,.2f}"
                        f" ₺) üzerinden toplam zarar: {toplam_zarar:,.2f} ₺"
                    )
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Kayıtlı Fire ve Zayiatlar Listesi")
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
                    "Fire Miktarı": f"{f_log.get('miktar', 0)} Kg",
                    "Toplam Tutar": f"{f_log.get('tutar', 0):,.2f} ₺",
                    "İşlemi Yapan": f_log.get("islem_yapan", "admin"),
                })
            ozel_html_tablo_goster(fire_tablo_verisi)
        else:
            st.info("Sistemde kayıtlı fire / zayiat bulunmuyor.")

# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Takibi")

    col_tarih_mod, col_tarih_sec = st.columns([1, 2])
    with col_tarih_mod:
        zaman_modu = st.radio(
            "Görünüm Modu", ["Tarihe Göre Seç", "Tüm Zamanlar"], horizontal=True
        )
    with col_tarih_sec:
        if zaman_modu == "Tarihe Göre Seç":
            secilen_tarih_filtresi = st.date_input(
                "📅 Sorgulanacak Tarihi Seçin", value=datetime.date.today()
            )
            secilen_tarih_str = secilen_tarih_filtresi.strftime("%Y-%m-%d")
        else:
            secilen_tarih_str = "TÜMÜ"

    if not misafir_modu:
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
            list(set(g["urun"] for g in st.session_state.girisler))
        )

        if "sepet" not in st.session_state:
            st.session_state.sepet = []

        if not salt_okunur_modu:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                secilen_urun = st.selectbox(
                    "Malzeme Seç", benzersiz_urunler, key="yemek_urun"
                )
            with col2:
                ilgili_girisler = [
                    g
                    for g in st.session_state.girisler
                    if g["urun"] == secilen_urun and g["kalan"] > 0
                ]
                stok_max = sum(g["kalan"] for g in ilgili_girisler)
                kullanilacak_miktar = st.number_input(
                    f"Miktar (Stok: {stok_max})",
                    min_value=0.0,
                    max_value=float(stok_max) if stok_max > 0 else 0.1,
                    step=0.1,
                    key="yemek_miktar",
                )
            with col3:
                st.markdown(
                    "<div style='margin-top: 28px;'></div>", unsafe_allow_html=True
                )
                if st.button("Sepete Ekle", use_container_width=True):
                    if kullanilacak_miktar > 0 and kullanilacak_miktar <= stok_max:
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
                    g for g in st.session_state.girisler if g["urun"] == urun
                ]
                ortalama_fiyat = 0.0
                if ilgili_girisler:
                    toplam_fiyat_degeri = sum(
                        g["fiyat"] * g["miktar"] for g in ilgili_girisler
                    )
                    toplam_miktar_degeri = sum(g["miktar"] for g in ilgili_girisler)
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
                    tarih_simdi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                    arsiv_malzemeler = []
                    for item in st.session_state.sepet:
                        urun = item["urun"]
                        istenen = item["miktar"]
                        kalan_dusulecek = istenen
                        item_tutar = 0.0
                        ilgili_g = [
                            g
                            for g in st.session_state.girisler
                            if g["urun"] == urun and g["kalan"] > 0
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
                        f"{uretim_tarih_str} tarihli üretim başarıyla tamamlandı ve"
                        " arşive kaydedildi!"
                    )
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
    if secilen_tarih_str == "TÜMÜ":
        st.subheader("📚 Tüm Zamanların Yemek Üretim ve Maliyet Arşivi")
        secilen_gun_uretimleri = st.session_state.yemek_uretim_arsivi
    else:
        st.subheader(
            f"📅 Seçilen Tarihteki ({secilen_tarih_str}) Yemek Üretim ve Maliyet"
            " Arşivi"
        )
        secilen_gun_uretimleri = [
            u
            for u in st.session_state.yemek_uretim_arsivi
            if u.get("tarih") == secilen_tarih_str
        ]

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

        ozel_html_tablo_goster(arsiv_tablo_verisi)

        rapor_adi_etiketi = (
            "tum_zamanlar_yemek_uretim_raporu"
            if secilen_tarih_str == "TÜMÜ"
            else f"yemek_uretim_raporu_{secilen_tarih_str}"
        )
        baslik_etiketi = (
            "Aziziye Aşevi - Tüm Zamanlar Yemek Üretim Raporu"
            if secilen_tarih_str == "TÜMÜ"
            else f"Aziziye Aşevi - {secilen_tarih_str} Yemek Üretim Raporu"
        )

        excel_arsiv_data = tablo_to_excel_bytes(
            excel_arsiv_listesi, baslik_etiketi
        )
        pdf_arsiv_data = tablo_to_html_pdf_bytes(baslik_etiketi, excel_arsiv_listesi)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_sec_arsiv, col_btn_arsiv = st.columns([2, 2])
        with col_sec_arsiv:
            st.markdown(f"**Arşiv Raporunu İndir ({secilen_tarih_str})**")
        with col_btn_arsiv:
            ortak_indirme_alani(
                excel_arsiv_data,
                pdf_arsiv_data,
                rapor_adi_etiketi,
                f"arsiv_{secilen_tarih_str}",
            )
    else:
        st.info(
            f"Seçilen kriterde kayıtlı yemek üretim ve maliyet arşivi bulunmuyor."
        )

# 6. KALORİ HESAPLAMA ARACI
elif menu == "Kalori Hesaplama Aracı":
    col_b_kal, col_indir_kal = st.columns([2, 2])
    with col_b_kal:
        st.header("🔥 Kalori Hesaplama Aracı")

    benzersiz_urunler_kalori = sorted(
        list(set(g["urun"] for g in st.session_state.girisler))
    )
    col_k_sec1, col_k_sec2, col_k_sec3 = st.columns([2, 1, 1])
    with col_k_sec1:
        secilen_kalori_urun = st.selectbox(
            "Malzeme Seçin", benzersiz_urunler_kalori, key="kalori_urun_sec"
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
        st.success("Eklendi!")

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
            "Aşevimizden yemek yardımı alan kişilerin kayıtlarını oluşturun,"
            " yönetin ve yemek dağıtımlarını takip edin."
        )

        tab1, tab2, tab3 = st.tabs([
            "📋 İhtiyaç Sahibi Listesi, Ekle ve Sil",
            "🍲 Yemek Dağıtım Girişi",
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
                kisi_liste_gosterim.append({
                    "Kayıt No": k["id"],
                    "T.C. Kimlik No / Hane No": k.get("tc_hane", ""),
                    "Adı Soyadı": k["ad_soyad"],
                    "Telefon": k["telefon"],
                    "Adres": k["adres"],
                    "Birey Sayısı": k["birey_sayisi"],
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

            if yonetim_modu:
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda yalnızca kayıtlı ihtiyaç"
                    " sahiplerini gözlemleyebilirsiniz."
                )
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
                            islem_tarihi_str = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            )
                            islem_yapan_kisi = st.session_state.aktif_kullanici
                            st.session_state.ihtiyac_sahipleri.append({
                                "id": f"IHT-{len(st.session_state.ihtiyac_sahipleri)+1:03d}",
                                "tc_hane": yeni_tc_hane,
                                "ad_soyad": yeni_ad,
                                "telefon": yeni_tel,
                                "adres": yeni_adres,
                                "birey_sayisi": yeni_birey,
                                "eklenme_tarihi": islem_tarihi_str,
                                "islem_yapan": islem_yapan_kisi,
                            })
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.success(f"Başarılı! {yeni_ad} sisteme kaydedildi.")
                            st.rerun()

                with col_form_sil:
                    with st.form("ihtiyac_sahibi_sil_formu"):
                        st.markdown("**🗑️ Kayıtlı İhtiyaç Sahibini Sil**")
                        if st.session_state.ihtiyac_sahipleri:
                            kisi_secenekleri_sil = [
                                f"{k['id']} - {k['ad_soyad']} (T.C./Hane:"
                                f" {k.get('tc_hane', '-')})"
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
                                    f"Başarılı! {silinen_isim} sistemden silindi."
                                )
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
                st.subheader("🍲 Günlük Yemek Dağıtım Girişi ve Yönetimi")

            if st.session_state.dagitim_silme_mesaji:
                st.success(st.session_state.dagitim_silme_mesaji)
                st.session_state.dagitim_silme_mesaji = ""

            dagitim_gosterim_listesi = []
            for idx, d in enumerate(st.session_state.dagitim_loglari):
                dagitim_gosterim_listesi.append({
                    "Kayıt No": f"DAG-{idx:03d}",
                    "Tarih / Saat": d.get("tarih", "-"),
                    "Kişi / Hane": d.get("kisi", "-"),
                    "Menü": d.get("menu", "-"),
                    "Porsiyon": d.get("porsiyon", 1),
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

            if yonetim_modu:
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda yeni dağıtım kaydı"
                    " oluşturamazsınız."
                )
            elif not st.session_state.ihtiyac_sahipleri:
                st.warning(
                    "Önce 'İhtiyaç Sahibi Listesi, Ekle ve Sil' sekmesinden kişi kaydı"
                    " yapmalısınız."
                )
            else:
                col_d_ekle, col_d_sil = st.columns(2)
                with col_d_ekle:
                    with st.form("dagitim_formu"):
                        st.markdown("**➕ Yeni Yemek Dağıtımı Ekle**")
                        d_tarih_saat = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        kisi_secenekleri = [
                            k["ad_soyad"] for k in st.session_state.ihtiyac_sahipleri
                        ]
                        secilen_kisi = st.selectbox(
                            "Yemek Alan Kişi / Hane", kisi_secenekleri
                        )
                        menu_adi = st.text_input(
                            "Verilen Menü / Yemek Adı", "Ispanak Yemeği ve Pilav"
                        )
                        porsiyon_mik = st.number_input(
                            "Verilen Porsiyon / Sefer Tası Miktarı", min_value=1, value=1
                        )

                        dagitim_ekle_btn = st.form_submit_button("Dağıtımı Kaydet")
                        if dagitim_ekle_btn:
                            st.session_state.dagitim_loglari.append({
                                "id": f"DAG-{len(st.session_state.dagitim_loglari)+1:03d}",
                                "tarih": d_tarih_saat,
                                "kisi": secilen_kisi,
                                "menu": menu_adi,
                                "porsiyon": porsiyon_mik,
                                "islem_yapan": st.session_state.aktif_kullanici,
                            })
                            dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                            st.success("Eklendi")
                            st.rerun()

                with col_d_sil:
                    with st.form("dagitim_sil_form"):
                        st.markdown("**🗑️ Yemek Dağıtım Kaydını Sil**")
                        if st.session_state.dagitim_loglari:
                            dagitim_secenekleri = [
                                f"DAG-{idx:03d} - {d['kisi']} | Menü: {d['menu']}"
                                f" ({d['tarih']})"
                                for idx, d in enumerate(st.session_state.dagitim_loglari)
                            ]
                            secilen_sil_dag = st.selectbox(
                                "Silinecek Dağıtım Kaydını Seçin", dagitim_secenekleri
                            )
                            dag_sil_btn = st.form_submit_button(
                                "Seçilen Dağıtımı Sil", type="primary"
                            )

                            if dag_sil_btn:
                                secilen_idx = int(
                                    secilen_sil_dag.split(" - ")[0].replace("DAG-", "")
                                )
                                silinen_dagitim = st.session_state.dagitim_loglari.pop(
                                    secilen_idx
                                )
                                dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                                st.session_state.dagitim_silme_mesaji = (
                                    f"Başarılı! {silinen_dagitim['kisi']} için yapılan"
                                    " dağıtım kaydı silindi."
                                )
                                st.rerun()
                        else:
                            st.info("Silinebilecek yemek dağıtım kaydı bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Yemek Dağıtımları Tablosu")
            if dagitim_gosterim_listesi:
                ozel_html_tablo_goster(dagitim_gosterim_listesi)
            else:
                st.info("Kayıtlı yemek dağıtımı bulunmuyor.")

        with tab3:
            col_b_sayac, col_indir_sayac = st.columns([2, 2])
            with col_b_sayac:
                st.subheader(
                    "📊 Kişi Bazlı Günlük, Haftalık ve Aylık Sayaç Raporu"
                )

            simdi_dt = datetime.datetime.now()
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

                sayac_tablosu.append({
                    "T.C. / Hane No": k.get("tc_hane", "-"),
                    "İhtiyaç Sahibi": kisi_adi,
                    "Günlük Alım (Kez / Porsiyon)": (
                        f"{gunluk_sefer} Kez / {gunluk_porsiyon} Pors."
                    ),
                    "Haftalık Alım (Kez / Porsiyon)": (
                        f"{haftalik_sefer} Kez / {haftalik_porsiyon} Pors."
                    ),
                    "Aylık Alım (Kez / Porsiyon)": (
                        f"{aylik_sefer} Kez / {aylik_porsiyon} Pors."
                    ),
                })

                excel_sayac_liste.append({
                    "T.C. / Hane No": k.get("tc_hane", "-"),
                    "İhtiyaç Sahibi": kisi_adi,
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
            "Personel yönetimi, yıllık izinler, saatlik izinler, sağlık"
            " raporları ve resmi tatilleri bu ekrandan yönetebilirsiniz."
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

            bugun_tarihi = datetime.date.today()
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
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda yalnızca personel listesini"
                    " görüntüleyebilirsiniz."
                )
            else:
                col_p_ekle, col_p_sil, col_p_durum = st.columns(3)
                with col_p_ekle:
                    with st.form("personel_ekle_form"):
                        st.markdown("**➕ Yeni Personel Ekle**")
                        p_tc = st.text_input("T.C. No").strip()
                        p_ad = st.text_input("Personel Adı Soyadı").strip().upper()
                        p_gorev = st.text_input("Görevi (Örn: Aşçı)")
                        p_bas = st.date_input(
                            "İşe Başlama Tarihi", value=datetime.date.today()
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
                            st.success(f"Başarılı! {p_ad} kadroya eklendi.")
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
                                    f"Başarılı! {silinen_ad} kadrodan silindi."
                                )
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
                                st.success("Durum başarıyla güncellendi!")
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
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda izin ekleyemez veya"
                    " silemezsiniz."
                )
            elif not yonetici_modu:
                st.warning(
                    "⚠️ Yıllık izin işlemleri yalnızca **Admin** tarafından"
                    " yapılabilir."
                )
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
                                    st.success("Yıllık izin başarıyla kaydedildi!")
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
                                            f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} -"
                                            f" Bitiş: {iz['bitis']}"
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
                                    st.success("Seçilen yıllık izin silindi!")
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
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda saatlik izin ekleyemez veya"
                    " silemezsiniz."
                )
            elif not yonetici_modu:
                st.warning(
                    "⚠️ Saatlik izin işlemleri yalnızca **Admin** tarafından"
                    " yapılabilir."
                )
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
                                                    f"{s_bas_saat.strftime('%H:%M')} -"
                                                    f" {s_bit_saat.strftime('%H:%M')} ({s_aciklama})"
                                                ),
                                            })
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("Saatlik izin kaydedildi!")
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
                                            f"{p['ad_soyad']} | Tarih: {iz['baslangic']} |"
                                            f" {iz.get('saat')} Saat"
                                        ),
                                    })

                        if tum_saatlik_izinler:
                            secenek_sil_s = [item["ozet"] for item in tum_saatlik_izinler]
                            secilen_sil_s_str = st.selectbox(
                                "Silinecek Saatlik İzni Seçin", secenek_sil_s
                            )
                            s_sil_btn = st.form_submit_button(
                                "Seçilen İzni Sil", type="primary"
                            )

                            if s_sil_btn:
                                secilen_item_s = next(
                                    (
                                        item
                                        for item in tum_saatlik_izinler
                                        if item["ozet"] == secilen_sil_s_str
                                    ),
                                    None,
                                )
                                if secilen_item_s:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_item_s["personel"]:
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
                                            silinecek_hedef_s = saatlikler[secilen_item_s["idx"]]
                                            p["izinler"] = digerleri + [
                                                i for i in saatlikler if i != silinecek_hedef_s
                                            ]
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("Saatlik izin silindi!")
                                    st.rerun()
                        else:
                            st.info("Silinebilecek saatlik izin yok.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Tüm Saatlik İzinler Tablosu")
            if saatlik_tablo_listesi:
                ozel_html_tablo_goster(saatlik_tablo_listesi)
            else:
                st.info("Kayıtlı saatlik izin bulunmuyor.")

        with p_tab4:
            col_b_sag, col_indir_sag = st.columns([2, 2])
            with col_b_sag:
                st.subheader("🏥 Sağlık Raporu Yönetimi (Ekle & Sil)")

            saglik_tablo_listesi = []
            for p in st.session_state.personeller:
                for iz in p.get("izinler", []):
                    if iz.get("tur") == "Sağlık Raporu":
                        saglik_tablo_listesi.append({
                            "Personel": p["ad_soyad"],
                            "İzin Türü": "Sağlık Raporu",
                            "Kurum": iz.get("kurum", "-"),
                            "Başlangıç": iz.get("baslangic", "-"),
                            "Bitiş": iz.get("bitis", "-"),
                            "Teşhis": iz.get("teshis", "-"),
                        })

            excel_sag_data = tablo_to_excel_bytes(
                saglik_tablo_listesi, "Aziziye Aşevi - Sağlık Raporları"
            )
            pdf_sag_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Sağlık Raporları", saglik_tablo_listesi
            )

            with col_indir_sag:
                ortak_indirme_alani(
                    excel_sag_data,
                    pdf_sag_data,
                    "saglik_raporlari_raporu",
                    "saglik_raporu_sayfasi",
                )

            if yonetim_modu:
                st.info(
                    "👀 Yönetim modundasınız. Bu ekranda sağlık raporu ekleyemez veya"
                    " silemezsiniz."
                )
            elif not yonetici_modu:
                st.warning(
                    "⚠️ Sağlık raporu işlemleri yalnızca **Admin** tarafından"
                    " yapılabilir."
                )
            else:
                col_r_ekle, col_r_sil = st.columns(2)
                with col_r_ekle:
                    with st.form("saglik_raporu_form"):
                        st.markdown("**➕ Sağlık Raporu Ekle**")
                        p_rap_secenekleri = [
                            p["ad_soyad"]
                            for p in st.session_state.personeller
                            if p.get("aktif", True)
                        ]
                        if p_rap_secenekleri:
                            secilen_p_rap = st.selectbox(
                                "Personel Seçin", p_rap_secenekleri, key="rap_p"
                            )
                            r_nereden = st.text_input(
                                "Kurum / Hastane", "Örn: Erzurum Şehir Hastanesi"
                            )
                            col_r1, col_r2 = st.columns(2)
                            with col_r1:
                                r_bas = st.date_input("Başlangıç Tarihi", key="rap_bas")
                            with col_r2:
                                r_bit = st.date_input("Bitiş Tarihi", key="rap_bit")
                            r_teshis = st.text_input(
                                "Teşhis / Açıklama", "Örn: Üst Solunum Yolu"
                            )
                            rap_submit = st.form_submit_button("Sağlık Raporunu Kaydet")

                            if rap_submit:
                                if r_bas > r_bit:
                                    st.error("Başlangıç bitişten sonra olamaz!")
                                else:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_p_rap:
                                            if "izinler" not in p:
                                                p["izinler"] = []
                                            p["izinler"].append({
                                                "tur": "Sağlık Raporu",
                                                "baslangic": str(r_bas),
                                                "bitis": str(r_bit),
                                                "kurum": r_nereden,
                                                "teshis": r_teshis,
                                            })
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("Sağlık raporu kaydedildi!")
                                    st.rerun()
                        else:
                            st.info("Aktif personel bulunmuyor.")

                with col_r_sil:
                    with st.form("saglik_raporu_sil_form"):
                        st.markdown("**🗑️ Sağlık Raporu Sil**")
                        tum_saglik_raporlari = []
                        for p in st.session_state.personeller:
                            for idx, iz in enumerate(p.get("izinler", [])):
                                if iz.get("tur") == "Sağlık Raporu":
                                    tum_saglik_raporlari.append({
                                        "personel": p["ad_soyad"],
                                        "idx": idx,
                                        "ozet": (
                                            f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']}"
                                            f" ({iz.get('teshis')})"
                                        ),
                                    })

                        if tum_saglik_raporlari:
                            secenek_sil_r = [item["ozet"] for item in tum_saglik_raporlari]
                            secilen_sil_r_str = st.selectbox(
                                "Silinecek Raporu Seçin", secenek_sil_r
                            )
                            r_sil_btn = st.form_submit_button(
                                "Seçilen Raporu Sil", type="primary"
                            )

                            if r_sil_btn:
                                secilen_item_r = next(
                                    (
                                        item
                                        for item in tum_saglik_raporlari
                                        if item["ozet"] == secilen_sil_r_str
                                    ),
                                    None,
                                )
                                if secilen_item_r:
                                    for p in st.session_state.personeller:
                                        if p["ad_soyad"] == secilen_item_r["personel"]:
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
                                            silinecek_hedef_r = raporlar[secilen_item_r["idx"]]
                                            p["izinler"] = digerleri + [
                                                i for i in raporlar if i != silinecek_hedef_r
                                            ]
                                    personelleri_kaydet(st.session_state.personeller)
                                    st.success("Sağlık raporu silindi!")
                                    st.rerun()
                        else:
                            st.info("Silinebilecek sağlık raporu yok.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Tüm Sağlık Raporları Tablosu")
            if saglik_tablo_listesi:
                ozel_html_tablo_goster(saglik_tablo_listesi)
            else:
                st.info("Kayıtlı sağlık raporu bulunmuyor.")

        with p_tab5:
            col_b_net, col_indir_net = st.columns([2, 2])
            with col_b_net:
                st.subheader("📊 Personel Net Çalışma Süresi Raporu")

            if not st.session_state.personeller:
                st.info("Kayıtlı personel bulunmuyor.")
            else:
                p_isimleri = [p["ad_soyad"] for p in st.session_state.personeller]
                secilen_rapor_p = st.selectbox(
                    "Personel Seçin", p_isimleri, key="prs_rapor_sec"
                )
                c_kol1, c_kol2 = st.columns(2)
                with c_kol1:
                    donem_bas = st.date_input(
                        "Dönem Başlangıç", value=datetime.date(2026, 10, 1), key="d_bas"
                    )
                with c_kol2:
                    donem_bit = st.date_input(
                        "Dönem Bitiş", value=datetime.date(2026, 10, 31), key="d_bit"
                    )

                if donem_bas > donem_bit:
                    st.error("⚠️ Başlangıç tarihi bitişten büyük olamaz!")
                else:
                    ilgili_personel_obj = next(
                        (
                            p
                            for p in st.session_state.personeller
                            if p["ad_soyad"] == secilen_rapor_p
                        ),
                        None,
                    )
                    if ilgili_personel_obj:
                        net_gun, toplam_izin, saglik_raporu_gun, saatlik_izin_saat = (
                            net_calisma_gunu_hesapla(
                                donem_bas,
                                donem_bit,
                                ilgili_personel_obj.get("izinler", []),
                                st.session_state.resmi_tatiller,
                            )
                        )
                        m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                        with m_p1:
                            st.metric("Net Çalışılan Gün", f"{net_gun} Gün")
                        with m_p2:
                            st.metric("Yıllık İzin", f"{toplam_izin} Gün")
                        with m_p3:
                            st.metric("Sağlık Raporu", f"{saglik_raporu_gun} Gün")
                        with m_p4:
                            st.metric("Saatlik İzin", f"{saatlik_izin_saat} Saat")

                        net_rapor_liste = [{
                            "Personel": secilen_rapor_p,
                            "Dönem": f"{donem_bas} / {donem_bit}",
                            "Net Çalışılan Gün": f"{net_gun} Gün",
                            "Yıllık İzin": f"{toplam_izin} Gün",
                            "Sağlık Raporu": f"{saglik_raporu_gun} Gün",
                            "Saatlik İzin": f"{saatlik_izin_saat} Saat",
                        }]

                        excel_net_data = tablo_to_excel_bytes(
                            net_rapor_liste, f"Net Çalışma Raporu - {secilen_rapor_p}"
                        )
                        pdf_net_data = tablo_to_html_pdf_bytes(
                            f"Net Çalışma Raporu - {secilen_rapor_p}", net_rapor_liste
                        )

                        with col_indir_net:
                            ortak_indirme_alani(
                                excel_net_data,
                                pdf_net_data,
                                f"net_calisma_raporu_{secilen_rapor_p}",
                                "net_calisma_sayfasi",
                            )

                        st.markdown("---")
                        ozel_html_tablo_goster(net_rapor_liste)

# 9. KULLANIM TAKİBİ
elif menu == "Kullanım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_kul, col_indir_kul = st.columns([2, 2])
        with col_b_kul:
            st.header("📈 Depo Ürün Kullanım ve Fire Takibi")

        loglar = st.session_state.kullanim_loglari
        kullanim_tablo_verisi = []
        if loglar:
            for l in reversed(loglar):
                kullanim_tablo_verisi.append({
                    "Tarih / Saat": l.get("tarih", "-"),
                    "Ürün Adı": l.get("urun", "-"),
                    "İşlem Türü": l.get("tur", "Günlük Kullanım"),
                    "Miktar": f"{l.get('miktar', 0)}",
                    "Tutar": f"{l.get('tutar', 0):,.2f} ₺",
                    "İşlemi Yapan": l.get("islem_yapan", "admin"),
                })

        excel_kul_data = tablo_to_excel_bytes(
            kullanim_tablo_verisi, "Aziziye Aşevi - Kullanım ve Fire Takibi Raporu"
        )
        pdf_kul_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kullanım ve Fire Takibi Raporu", kullanim_tablo_verisi
        )

        with col_indir_kul:
            ortak_indirme_alani(
                excel_kul_data,
                pdf_kul_data,
                "kullanim_ve_fire_takibi",
                "kullanim_sayfasi",
            )

        if kullanim_tablo_verisi:
            ozel_html_tablo_goster(kullanim_tablo_verisi)
        else:
            st.info("Kullanım veya fire hareketi bulunmuyor.")

# 10. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_fiy, col_indir_fiy = st.columns([2, 2])
    with col_b_fiy:
        st.header("💰 Ürün Birim Fiyatları")
    if st.session_state.girisler:
        if misafir_modu:
            fiyat_tablo = [
                {"Ürün Adı": g["urun"], "Birim": g["birim"]}
                for g in st.session_state.girisler
            ]
        else:
            fiyat_tablo = [
                {"Ürün": g["urun"], "Fiyat": g["fiyat"], "Birim": g["birim"]}
                for g in st.session_state.girisler
            ]
        ozel_html_tablo_goster(fiyat_tablo)

# 11. KULLANICI AYARLARI (SADECE ADMİN)
elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya yalnızca **Admin** erişebilir.")
    else:
        st.header("⚙️ Kullanıcı Ayarları ve Sayfa Yetki Yönetimi")
        st.markdown(
            "Sistemdeki kullanıcıları yönetebilir, yeni kullanıcı ekleyebilir,"
            " şifrelerini değiştirebilir ve istiyorsanız belirli sayfalara erişim"
            " kısıtlamaları (yetki) verebilirsiniz."
        )

        k_tab1, k_tab2, k_tab3 = st.tabs([
            "👤 Kullanıcı Ekle / Sil",
            "🔑 Şifre Değiştir",
            "🛡️ Sayfa Yetki Yönetimi (Aç/Kapat)",
        ])

        with k_tab1:
            col_k_ekle, col_k_sil = st.columns(2)
            with col_k_ekle:
                with st.form("yeni_kullanici_ekle_form"):
                    st.markdown("**➕ Yeni Kullanıcı Ekle**")
                    y_k_adi = (
                        st.text_input("Kullanıcı Adı (Örn: depo_sorumlusu)")
                        .strip()
                        .lower()
                    )
                    y_sifre = st.text_input("Şifre", type="password")
                    y_tip = st.selectbox("Kullanıcı Tipi", ["personel", "admin"])
                    y_kaydet_btn = st.form_submit_button("Kullanıcıyı Kaydet")

                    if y_kaydet_btn and y_k_adi and y_sifre:
                        if y_k_adi in st.session_state.kullanicilar:
                            st.error("Bu kullanıcı adı zaten sistemde mevcut!")
                        else:
                            st.session_state.kullanicilar[y_k_adi] = {
                                "sifre": y_sifre,
                                "tip": y_tip,
                                "yasakli_menuler": [],
                            }
                            kullanıcıları_kaydet(st.session_state.kullanicilar)
                            st.success(f"Başarılı! '{y_k_adi}' kullanıcısı oluşturuldu.")
                            st.rerun()

            with col_k_sil:
                with st.form("kullanici_sil_form"):
                    st.markdown("**🗑️ Kullanıcı Sil**")
                    silinebilir_kullanicilar = [
                        k for k in st.session_state.kullanicilar.keys() if k != "admin"
                    ]
                    if silinebilir_kullanicilar:
                        secilen_sil_k = st.selectbox(
                            "Silinecek Kullanıcıyı Seçin", silinebilir_kullanicilar
                        )
                        k_sil_btn = st.form_submit_button(
                            "Kullanıcıyı Sil", type="primary"
                        )

                        if k_sil_btn:
                            del st.session_state.kullanicilar[secilen_sil_k]
                            kullanıcıları_kaydet(st.session_state.kullanicilar)
                            st.success(f"Başarılı! '{secilen_sil_k}' silindi.")
                            st.rerun()
                    else:
                        st.info(
                            "Silinebilecek başka kullanıcı bulunmuyor (Admin silinemez)."
                        )

            st.markdown("---")
            st.subheader("📋 Mevcut Kullanıcılar Listesi")
            kullanici_tablo_listesi = []
            for k_ad, k_vals in st.session_state.kullanicilar.items():
                kullanici_tablo_listesi.append({
                    "Kullanıcı Adı": k_ad,
                    "Kullanıcı Tipi": k_vals.get("tip", "personel"),
                    "Yasaklı Menü Sayısı": len(k_vals.get("yasakli_menuler", [])),
                })
            ozel_html_tablo_goster(kullanici_tablo_listesi)

        with k_tab2:
            with st.form("admin_sifre_guncelle_form"):
                st.markdown("**🔑 Kullanıcı Şifresi Değiştir / Güncelle**")
                tum_k_isimleri = list(st.session_state.kullanicilar.keys())
                secilen_k_duzenle = st.selectbox(
                    "Şifresi Değiştirilecek Kullanıcı", tum_k_isimleri
                )
                yeni_sifre_1 = st.text_input("Yeni Şifre", type="password")
                yeni_sifre_2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
                sifre_guncelle_btn = st.form_submit_button("Şifreyi Güncelle")

                if sifre_guncelle_btn:
                    if not yeni_sifre_1 or yeni_sifre_1 != yeni_sifre_2:
                        st.error("Yeni şifreler uyuşmuyor!")
                    else:
                        st.session_state.kullanicilar[secilen_k_duzenle]["sifre"] = (
                            yeni_sifre_1
                        )
                        kullanıcıları_kaydet(st.session_state.kullanicilar)
                        st.success(
                            f"'{secilen_k_duzenle}' kullanıcısının şifresi başarıyla"
                            " güncellendi!"
                        )

        with k_tab3:
            st.markdown(
                "**🛡️ Sayfa Yetki Yönetimi (İstediğiniz sayfayı kullanıcıya kapatın"
                " veya açın)**"
            )
            yetki_verilecek_k = st.selectbox(
                "Yetkileri Düzenlenecek Kullanıcı",
                [k for k in st.session_state.kullanicilar.keys() if k != "admin"],
            )

            if yetki_verilecek_k:
                mevcur_yasaklar = st.session_state.kullanicilar[yetki_verilecek_k].get(
                    "yasakli_menuler", []
                )

                st.markdown(
                    f"**'{yetki_verilecek_k}'** kullanıcısının erişmesini"
                    " **istemediğiniz** (kapalı olmasını istediğiniz) sayfaları"
                    " seçin:"
                )

                tum_yonetilebilir_menuler = [
                    "Kurumsal Dashboard & Özet",
                    "Güncel Stok Durumu",
                    "Yeni Mal Alımı / Fatura Ekle",
                    "Ürün Sil / Düzenle",
                    "Fire / Zayiat Girişi",
                    "Ürün Birim Fiyatları & Ay Analizi",
                    "Günlük Yemek Üretimi & Maliyet Raporu",
                    "Kalori Hesaplama Aracı",
                    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
                    "Personel & Çalışma Süresi Takibi",
                    "Kullanım Takibi",
                ]

                secilen_yasaklar = []
                for m_item in tum_yonetilebilir_menuler:
                    varsayilan_durum = m_item in mevcur_yasaklar
                    if st.checkbox(
                        f"Kapat / Gizle: {m_item}",
                        value=varsayilan_durum,
                        key=f"yasak_{yetki_verilecek_k}_{m_item}",
                    ):
                        secilen_yasaklar.append(m_item)

                if st.button("Yetki Ayarlarını Kaydet", type="primary"):
                    st.session_state.kullanicilar[yetki_verilecek_k]["yasakli_menuler"] = (
                        secilen_yasaklar
                    )
                    kullanıcıları_kaydet(st.session_state.kullanicilar)
                    st.success(
                        f"'{yetki_verilecek_k}' kullanıcısının sayfa yetkileri başarıyla"
                        " güncellendi!"
                    )
                    st.rerun()
