import datetime
import json
import os
import io
import streamlit as st
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Sayfa Yapılandırması
st.set_page_config(page_title="Aziziye - Aşevi Takip Ekranı", page_icon="🍲", layout="wide")

# Oturumda Tema Durumu Kontrolü
if "tema_secimi" not in st.session_state:
    st.session_state.tema_secimi = "Koyu Tema (Dark)"

# Dinamik Tema CSS Entegrasyonu
if st.session_state.tema_secimi == "Koyu Tema (Dark)":
    st.markdown("""
        <style>
        .main, .stApp { 
            background-color: #0F172A !important; 
            color: #F8FAFC !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .stSidebar { 
            background-color: #111827 !important; 
            padding-top: 10px; 
            border-right: 1px solid #1F2937;
        }
        .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
            color: #9CA3AF !important; 
            font-size: 13.5px; 
        }
        h1, h2, h3, h4, h5, h6 { 
            color: #F8FAFC !important; 
            font-size: 22px !important;
            font-weight: 600 !important;
            letter-spacing: 2px !important;
        }
        p, span, label, div, .stMarkdown { 
            color: #F8FAFC !important; 
        }
        button[kind="header"] svg, [data-testid="collapsedControl"] span, [data-testid="collapsedControl"] div { display: none !important; }
        section[data-testid="stSidebar"] [data-testid="baseButton-header"] { color: transparent !important; }

        section[data-testid="stSidebar"] button[kind="secondary"] {
            background-color: transparent !important;
            color: #9CA3AF !important;
            border: none !important;
            border-radius: 8px !important;
            text-align: left !important;
            font-weight: 400 !important;
            padding: 6px 10px !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] button[kind="secondary"]:hover {
            background-color: #1F2937 !important;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #1F2937 !important;
            color: #38BDF8 !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        div.stMetric, div[data-testid="stExpander"], div.stForm {
            background: #1E293B !important;
            border: 1px solid #334155;
            padding: 16px 20px;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            color: #F8FAFC !important;
        }
        .custom-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            margin-bottom: 15px;
            background-color: #1E293B;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #334155;
        }
        .custom-table th {
            background-color: #0F172A;
            color: #38BDF8;
            padding: 12px 16px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            border-bottom: 1px solid #334155;
        }
        .custom-table td {
            padding: 12px 16px;
            color: #F8FAFC;
            font-size: 13px;
            border-bottom: 1px solid #334155;
        }
        .custom-table tr:hover {
            background-color: #273548;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .main, .stApp { 
            background-color: #FAFAFB !important; 
            color: #111827 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .stSidebar { 
            background-color: #F9FAFB !important; 
            padding-top: 10px; 
            border-right: 1px solid #E5E7EB;
        }
        .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
            color: #4B5563 !important; 
            font-size: 13.5px; 
        }
        h1, h2, h3, h4, h5, h6 { 
            color: #111827 !important; 
            font-size: 22px !important;
            font-weight: 600 !important;
            letter-spacing: 2px !important;
        }
        p, span, label, div, .stMarkdown { 
            color: #111827 !important; 
        }
        button[kind="header"] svg, [data-testid="collapsedControl"] span, [data-testid="collapsedControl"] div { display: none !important; }
        section[data-testid="stSidebar"] [data-testid="baseButton-header"] { color: transparent !important; }

        section[data-testid="stSidebar"] button[kind="secondary"] {
            background-color: transparent !important;
            color: #4B5563 !important;
            border: none !important;
            border-radius: 8px !important;
            text-align: left !important;
            font-weight: 400 !important;
            padding: 6px 10px !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] button[kind="secondary"]:hover {
            background-color: #F3F4F6 !important;
            color: #111827 !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #E5E7EB !important;
            color: #111827 !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        div.stMetric, div[data-testid="stExpander"], div.stForm {
            background: #FFFFFF !important;
            border: 1px solid #E5E7EB;
            padding: 16px 20px;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
            color: #111827 !important;
        }
        .custom-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            margin-bottom: 15px;
            background-color: #FFFFFF;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #E5E7EB;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .custom-table th {
            background-color: #F3F4F6;
            color: #111827;
            padding: 12px 16px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
            border-bottom: 1px solid #E5E7EB;
        }
        .custom-table td {
            padding: 12px 16px;
            color: #374151;
            font-size: 13px;
            border-bottom: 1px solid #E5E7EB;
        }
        .custom-table tr:hover {
            background-color: #F9FAFB;
        }
        </style>
    """, unsafe_allow_html=True)

VERI_DOSYASI = "asevi_stok_veritabani.json"
KULLANIM_LOG_DOSYASI = "asevi_kullanim_loglari.json"
IHTIYAC_SAHIPLERI_DOSYASI = "asevi_ihtiyac_sahipleri.json"
DAGITIM_LOG_DOSYASI = "asevi_dagitim_loglari.json"
PERSONEL_DOSYASI = "asevi_personel_veritabani.json"
SIFRE_DOSYASI = "asevi_yonetici_sifre.json"
TATIL_DOSYASI = "asevi_resmi_tatiller.json"
SILINENS_DOSYASI = "asevi_silinen_urunler_loglari.json"

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
    "ŞEKER": 387, "TOZ ŞEKER": 387, "TUZ": 0, "İRMİK": 360, "BEZELYE": 81, "BEZELYE KONSERVESİ": 81
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

# Doğru tutar ve tarihlerle güncellenmiş fire log kayıtları
varsayilan_loglar = [
    {"tarih": "2026-10-05 10:00", "urun": "ISPANAK", "tur": "Fire/Zayiat", "miktar": 60.0, "tutar": 4200.00, "islem_yapan": "admin"},
    {"tarih": "2026-10-09 10:00", "urun": "PATLICAN", "tur": "Fire/Zayiat", "miktar": 52.4, "tutar": 2882.00, "islem_yapan": "admin"},
    {"tarih": "2026-10-14 10:00", "urun": "MUZ", "tur": "Fire/Zayiat", "miktar": 54.5, "tutar": 5995.00, "islem_yapan": "admin"},
    {"tarih": "2026-10-20 10:00", "urun": "SALATALIK", "tur": "Fire/Zayiat", "miktar": 43.0, "tutar": 1935.00, "islem_yapan": "admin"},
    {"tarih": "2026-10-21 10:00", "urun": "TAM YAĞLI YOĞURT", "tur": "Fire/Zayiat", "miktar": 15.0, "tutar": 993.00, "islem_yapan": "admin"}
]

varsayilan_personeller = [
    {"tc": "11111111111", "ad_soyad": "MUHAMMED İLKER ÇELİK", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"tc": "22222222222", "ad_soyad": "EMİRHAN DÖNMEZ", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"tc": "33333333333", "ad_soyad": "SEDAT UZUN", "gorev": "Aşçı", "baslama": "2026-09-25", "aktif": True, "izinler": []},
    {"tc": "44444444444", "ad_soyad": "BURAK AYAŞTI", "gorev": "Temizlik Personeli", "baslama": "2026-09-25", "aktif": True, "izinler": []},
    {"tc": "55555555555", "ad_soyad": "HÜSEYİN KAYMAK", "gorev": "Aşçı Yardımcısı", "baslama": "2026-10-26", "aktif": True, "izinler": []}
]

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {"tarih": "2026-04-23", "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı"},
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {"tarih": "2026-05-19", "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı"},
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"}
]

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
                return json.load(f)
        except Exception:
            return []
    return []

def ihtiyac_sahiplerini_kaydet(veri):
    with open(IHTIYAC_SAHIPLERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

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
                return json.load(f)
        except Exception:
            return varsayilan_personeller
    return varsayilan_personeller

def personelleri_kaydet(veri):
    with open(PERSONEL_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def resmi_tatilleri_yukle():
    if os.path.exists(TATIL_DOSYASI):
        try:
            with open(TATIL_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_resmi_tatiller
    return varsayilan_resmi_tatiller

def yonetici_sifresi_yukle():
    if os.path.exists(SIFRE_DOSYASI):
        try:
            with open(SIFRE_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f).get("sifre", "Ss123321")
        except Exception:
            return "Ss123321"
    return "Ss123321"

def yonetici_sifresi_kaydet(yeni_sifre):
    with open(SIFRE_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"sifre": yeni_sifre}, f, ensure_ascii=False, indent=4)

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
if "kalori_sepeti" not in st.session_state:
    st.session_state.kalori_sepeti = []
if "personel_silme_mesaji" not in st.session_state:
    st.session_state.personel_silme_mesaji = ""

query_params = st.query_params
if "oturum_aktif" not in st.session_state:
    if "auth" in query_params and query_params["auth"] == "true" and "user" in query_params:
        st.session_state.oturum_aktif = True
        st.session_state.aktif_kullanici = query_params["user"]
    else:
        st.session_state.oturum_aktif = False
        st.session_state.aktif_kullanici = "misafir"

if "aktif_menu" not in st.session_state:
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

st.markdown("### 🍲 AZİZİYE - AŞEVİ TAKİP EKRANI")
st.markdown(f"**Hoş geldiniz** &nbsp;|&nbsp; 📅 {bugunun_turkce_tarihi()}")
st.markdown("---")

# ----------------- MODERN AĞAÇ (TREE) MENÜ YAPISI -----------------
st.sidebar.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding-left: 4px;">
        <div style="background: #3B82F6; color: white; padding: 6px 10px; border-radius: 8px; font-weight: bold; font-size: 14px;">AZ</div>
        <div>
            <div style="font-weight: 600; font-size: 14px; line-height: 1.2;">Aziziye Aşevi</div>
            <div style="font-size: 11px; opacity: 0.7;">Yönetim Paneli</div>
        </div>
    </div>
""", unsafe_allow_html=True)

sidebar_arama = st.sidebar.text_input("🔍 Menüde Ara...", placeholder="Örn: Stok, Fatura...", label_visibility="collapsed")
st.sidebar.markdown('<p style="font-size: 12px; font-weight: 600; margin-top: 10px; margin-bottom: 4px; padding-left: 4px; opacity: 0.6;">AĞAÇ MENÜ & SİSTEM</p>', unsafe_allow_html=True)

yonetici_modu = (st.session_state.oturum_aktif and st.session_state.aktif_kullanici == "admin")
misafir_modu = (not st.session_state.oturum_aktif or st.session_state.aktif_kullanici == "misafir")

menu_gruplari = {
    "🏠 Genel Bakış": [
        "Kurumsal Dashboard & Özet"
    ],
    "📦 Depo & Stok Yönetimi": [
        "Güncel Stok Durumu", 
        "Yeni Mal Alımı / Fatura Ekle", 
        "Ürün Sil / Düzenle", 
        "Fire / Zayiat Girişi",
        "Ürün Birim Fiyatları & Ay Analizi"
    ],
    "🍲 Üretim & Mutfak": [
        "Günlük Yemek Üretimi & Maliyet Raporu",
        "Kalori Hesaplama Aracı"
    ],
    "👥 Sosyal & İnsan Kaynakları": [
        "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
        "Personel & Çalışma Süresi Takibi"
    ],
    "📈 Raporlar & Arşiv": [
        "Kullanım Takibi"
    ]
}

filtrelenmis_gruplar = {}
for grup_adi, alt_menuler in menu_gruplari.items():
    uygun_menuler = [m for m in alt_menuler if not sidebar_arama or sidebar_arama.lower() in m.lower() or sidebar_arama.lower() in grup_adi.lower()]
    if uygun_menuler:
        filtrelenmis_gruplar[grup_adi] = uygun_menuler

for grup_adi, alt_menuler in filtrelenmis_gruplar.items():
    grup_aktif_mu = st.session_state.aktif_menu in alt_menuler
    with st.sidebar.expander(grup_adi, expanded=grup_aktif_mu):
        for m in alt_menuler:
            if m == "Yeni Mal Alımı / Fatura Ekle" and misafir_modu:
                continue
            btn_type = "primary" if st.session_state.aktif_menu == m else "secondary"
            if st.button(m, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"):
                st.session_state.aktif_menu = m
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown('<p style="font-size: 13px; font-weight: 600; margin-bottom: 6px; padding-left: 2px;">🎨 Arayüz Teması</p>', unsafe_allow_html=True)
yeni_tema = st.sidebar.selectbox("Tema Seçin", ["Koyu Tema (Dark)", "Açık Tema (Light)"], index=0 if st.session_state.tema_secimi=="Koyu Tema (Dark)" else 1, label_visibility="collapsed")
if yeni_tema != st.session_state.tema_secimi:
    st.session_state.tema_secimi = yeni_tema
    st.rerun()

st.sidebar.markdown("---")
kullanici_adi_goruntule = st.session_state.aktif_kullanici.upper() if st.session_state.oturum_aktif else "MİSAFİR"
st.sidebar.markdown(f"""
    <div style="background: rgba(125, 125, 125, 0.08); padding: 10px 12px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: #3B82F6; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px;">
                {kullanici_adi_goruntule[:1]}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 13px;">{kullanici_adi_goruntule}</div>
                <div style="font-size: 11px; opacity: 0.6;">Aktif Oturum</div>
            </div>
        </div>
        <div style="font-size: 16px; opacity: 0.6; cursor: pointer;">⋮</div>
    </div>
""", unsafe_allow_html=True)

aktif_yonetici_sifresi = yonetici_sifresi_yukle()

if not st.session_state.oturum_aktif:
    with st.sidebar.form("giris_formu"):
        kullanici_adi_input = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adı giriniz...").strip().lower()
        sifre_input = st.text_input("Şifre", type="password", placeholder="Şifre giriniz...")
        giris_butonu = st.form_submit_button("Giriş Yap", use_container_width=True)
        if giris_butonu:
            if kullanici_adi_input == "admin" and sifre_input == aktif_yonetici_sifresi:
                st.session_state.oturum_aktif = True
                st.session_state.aktif_kullanici = "admin"
                st.query_params["auth"] = "true"
                st.query_params["user"] = "admin"
                st.success("Admin olarak giriş yapıldı!")
                st.rerun()
            elif kullanici_adi_input == "asci" and sifre_input == "sydv25":
                st.session_state.oturum_aktif = True
                st.session_state.aktif_kullanici = "asci"
                st.query_params["auth"] = "true"
                st.query_params["user"] = "asci"
                st.success("Aşçı olarak giriş yapıldı!")
                st.rerun()
            elif kullanici_adi_input == "misafir" and sifre_input == "Erzurum25":
                st.session_state.oturum_aktif = True
                st.session_state.aktif_kullanici = "misafir"
                st.query_params["auth"] = "true"
                st.query_params["user"] = "misafir"
                st.success("Misafir olarak giriş yapıldı!")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
else:
    if st.sidebar.button("Oturumu Kapat", use_container_width=True, type="secondary"):
        st.session_state.oturum_aktif = False
        st.session_state.aktif_kullanici = "misafir"
        st.query_params.clear()
        st.rerun()

    if st.session_state.aktif_kullanici == "admin":
        with st.sidebar.expander("➡️ Admin Şifresini Değiştir"):
            with st.form("sifre_degistir_form"):
                eski_sifre = st.text_input("Mevcut Şifre", type="password")
                yeni_sifre_1 = st.text_input("Yeni Şifre", type="password")
                yeni_sifre_2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
                sifre_guncelle_btn = st.form_submit_button("Şifreyi Güncelle")
                if sifre_guncelle_btn:
                    if eski_sifre != aktif_yonetici_sifresi:
                        st.error("Mevcut şifre hatalı!")
                    elif not yeni_sifre_1 or yeni_sifre_1 != yeni_sifre_2:
                        st.error("Yeni şifreler uyuşmuyor!")
                    else:
                        yonetici_sifresi_kaydet(yeni_sifre_1)
                        st.success("Admin şifresi başarıyla değiştirildi!")

st.sidebar.markdown("---")
st.sidebar.markdown('<p style="font-size: 11px; text-align: center; opacity: 0.5;">sefautopcu</p>', unsafe_allow_html=True)


def tablo_to_excel_bytes(veri_listesi, baslik_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapor"
    ws.views.sheetView[0].showGridLines = True
    header_fill = PatternFill(start_color="111827", end_color="111827", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="111827")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(left=Side(style='thin', color='E5E7EB'), right=Side(style='thin', color='E5E7EB'), top=Side(style='thin', color='E5E7EB'), bottom=Side(style='thin', color='E5E7EB'))

    ws.cell(row=1, column=1, value=baslik_str).font = title_font
    ws.cell(row=2, column=1, value=f"Rapor Tarihi: {str(datetime.datetime.now())}").font = Font(name="Calibri", size=11, italic=True, color="4B5563")

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
            body {{ font-family: 'Inter', sans-serif; margin: 30px; color: #111827; }}
            h2 {{ color: #111827; margin-bottom: 5px; }}
            p {{ color: #4B5563; font-size: 14px; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #111827; color: white; padding: 10px; text-align: left; font-size: 13px; }}
            td {{ border: 1px solid #E5E7EB; padding: 8px 10px; font-size: 13px; }}
            tr:nth-child(even) {{ background-color: #F9FAFB; }}
        </style>
    </head>
    <body>
        <h2>{baslik}</h2>
        <p>Rapor Tarihi: {datetime.datetime.now()}</p>
        <hr style="border: 0; border-top: 1px solid #E5E7EB;"/>
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
        format_secimi = st.selectbox("İndirilecek Formatı Seçin", ["Excel (.xlsx)", "PDF / HTML (.html)"], key=f"sel_{unique_key}")
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if "Excel" in format_secimi:
            st.download_button(
                label="📥 Raporu İndir",
                data=excel_veri,
                file_name=f"{dosya_adi_koku}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"btn_{unique_key}"
            )
        else:
            st.download_button(
                label="📥 Raporu İndir",
                data=pdf_veri,
                file_name=f"{dosya_adi_koku}.html",
                mime="text/html",
                key=f"btn_{unique_key}"
            )


menu = st.session_state.aktif_menu

# 0. KURUMSAL DASHBOARD & ÖZET
if menu == "Kurumsal Dashboard & Özet":
    toplam_stok_kalemi = len(set(g["urun"] for g in st.session_state.girisler))
    toplam_envanter_maliyeti = sum(g["kalan"] * g["fiyat"] for g in st.session_state.girisler)

    loglar = st.session_state.kullanim_loglari
    toplam_fire_mik = sum(l["miktar"] for l in loglar if l["tur"] == "Fire/Zayiat")
    toplam_fire_tutar = sum(l["tutar"] for l in loglar if l["tur"] == "Fire/Zayiat")
    aktif_calisan_personel_sayisi = sum(1 for p in st.session_state.personeller if p.get("aktif", True))

    is_dark = (st.session_state.tema_secimi == "Koyu Tema (Dark)")
    card_bg = "#1E293B" if is_dark else "#FFFFFF"
    card_border = "#334155" if is_dark else "#E5E7EB"
    text_color = "#F8FAFC" if is_dark else "#111827"
    subtext_color = "#94A3B8" if is_dark else "#4B5563"

    kare_kart_style = f"""
        background: {card_bg}; 
        border: 1px solid {card_border}; 
        padding: 24px; 
        border-radius: 16px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
        margin-bottom: 20px; 
        height: 180px; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
    """

    row1_c1, row1_c2 = st.columns(2)
    with row1_c1:
        st.markdown(f"""
            <div style="{kare_kart_style}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="color: {subtext_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Toplam Ürün Çeşidi</div>
                        <div style="color: {text_color}; font-size: 32px; font-weight: 700; margin-top: 10px;">{toplam_stok_kalemi} Çeşit</div>
                    </div>
                    <div style="background: rgba(56, 189, 248, 0.15); padding: 12px; border-radius: 12px; color: #38BDF8; font-size: 20px;">📦</div>
                </div>
                <div style="color: {subtext_color}; font-size: 12px;">Aktif Depo Çeşitliliği</div>
            </div>
        """, unsafe_allow_html=True)

    with row1_c2:
        st.markdown(f"""
            <div style="{kare_kart_style}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="color: {subtext_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Toplam Fire / Zayiat</div>
                        <div style="color: {text_color}; font-size: 32px; font-weight: 700; margin-top: 10px;">{toplam_fire_mik:,.1f} Kg</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.15); padding: 12px; border-radius: 12px; color: #EF4444; font-size: 20px;">📉</div>
                </div>
                <div style="color: #EF4444; font-size: 12px; font-weight: 600;">Maddi Zarar: {toplam_fire_tutar:,.2f} ₺</div>
            </div>
        """, unsafe_allow_html=True)

    row2_c1, row2_c2 = st.columns(2)
    with row2_c1:
        st.markdown(f"""
            <div style="{kare_kart_style}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="color: {subtext_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Toplam Stok Değeri</div>
                        <div style="color: {text_color}; font-size: 28px; font-weight: 700; margin-top: 10px;">{toplam_envanter_maliyeti:,.2f} ₺</div>
                    </div>
                    <div style="background: rgba(52, 211, 153, 0.15); padding: 12px; border-radius: 12px; color: #34D399; font-size: 20px;">💰</div>
                </div>
                <div style="color: {subtext_color}; font-size: 12px;">Güncel Envanter Maliyeti</div>
            </div>
        """, unsafe_allow_html=True)

    with row2_c2:
        st.markdown(f"""
            <div style="{kare_kart_style}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <div style="color: {subtext_color}; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Aktif Çalışan Personel</div>
                        <div style="color: {text_color}; font-size: 32px; font-weight: 700; margin-top: 10px;">{aktif_calisan_personel_sayisi} Kişi</div>
                    </div>
                    <div style="background: rgba(167, 139, 250, 0.15); padding: 12px; border-radius: 12px; color: #A78BFA; font-size: 20px;">👥</div>
                </div>
                <div style="color: {subtext_color}; font-size: 12px;">Aktif Kadro Durumu</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🚀 Hızlı İşlem Kısayolları")
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("📦 Stok Durumuna Git", use_container_width=True):
            st.session_state.aktif_menu = "Güncel Stok Durumu"
            st.rerun()
    with q2:
        if st.button("🍲 Yemek Üretimi Yap", use_container_width=True):
            st.session_state.aktif_menu = "Günlük Yemek Üretimi & Maliyet Raporu"
            st.rerun()
    with q3:
        if st.button("🔥 Kalori Hesaplama Aracı", use_container_width=True):
            st.session_state.aktif_menu = "Kalori Hesaplama Aracı"
            st.rerun()

# 1. GÜNCEL STOK DURUMU
elif menu == "Güncel Stok Durumu":
    col_baslik, col_indir_alan = st.columns([2, 2])
    with col_baslik:
        st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")

    benzersiz_urunler_Excel = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    excel_liste = []
    for u in benzersiz_urunler_Excel:
        toplam_kalan_ex = sum(g["kalan"] for g in st.session_state.girisler if g["urun"] == u)
        kategori_ex = next((g["kategori"] for g in st.session_state.girisler if g["urun"] == u), "GENEL")
        birim_ex = next((g["birim"] for g in st.session_state.girisler if g["urun"] == u), "Kg")
        depo_ex = next((g["depo"] for g in st.session_state.girisler if g["urun"] == u), "Merkez Depo")
        islem_yapan_ex = next((g.get("islem_yapan", "admin") for g in st.session_state.girisler if g["urun"] == u), "admin")
        en_son_tarih_ex = max((g.get("tarih", "-") for g in st.session_state.girisler if g["urun"] == u), default="-")
        excel_liste.append({"Ürün Adı": u, "Kategori": kategori_ex, "Birim": birim_ex, "Kalan Miktar": toplam_kalan_ex, "Depo Yeri": depo_ex, "Eklenme/Güncelleme Tarihi": en_son_tarih_ex, "Son İşlemi Yapan": islem_yapan_ex})

    excel_data = tablo_to_excel_bytes(excel_liste, "Aziziye Aşevi - Güncel Stok Raporu")
    pdf_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Güncel Stok Raporu", excel_liste)

    with col_indir_alan:
        ortak_indirme_alani(excel_data, pdf_data, "asevi_guncel_stok_raporu", "stok_sayfasi")

    depolar = ["Tümü", "Soğuk Hava Deposu +5/+6", "Soğuk Hava Deposu -18", "Sebze Deposu", "Kuru Gıda Deposu"]
    secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)
    
    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    stok_tablosu = []
    kritik_urunler = []
    for u in benzersiz_urunler:
        toplam_kalan = sum(g["kalan"] for g in st.session_state.girisler if g["urun"] == u)
        kategori = next((g["kategori"] for g in st.session_state.girisler if g["urun"] == u), "GENEL")
        birim = next((g["birim"] for g in st.session_state.girisler if g["urun"] == u), "Kg")
        depo = next((g["depo"] for g in st.session_state.girisler if g["urun"] == u), "Merkez Depo")
        islem_yapan = next((g.get("islem_yapan", "admin") for g in st.session_state.girisler if g["urun"] == u), "admin")
        en_son_tarih = max((g.get("tarih", "-") for g in st.session_state.girisler if g["urun"] == u), default="-")
        
        if secilen_depo == "Tümü" or depo == secilen_depo:
            stok_tablosu.append({"Ürün Adı": u, "Kategori": kategori, "Birim": birim, "Kalan Miktar": toplam_kalan, "Depo Yeri": depo, "Eklenme Tarihi": en_son_tarih, "İşlemi Yapan": islem_yapan})
        if toplam_kalan <= 10.0:
            kritik_urunler.append((u, toplam_kalan, birim, depo))

    if kritik_urunler:
        with st.expander("⚠️ DİKKAT: Kritik Seviyedeki Veya Tükenen Ürünler!", expanded=False):
            for ku, km, kb, kd in kritik_urunler:
                st.warning(f"**{ku}** stoğu azalmıştır! Kalan Miktar: **{km} {kb}** ({kd})")

    st.markdown("### Envanter Listesi")
    for row in stok_tablosu:
        st.write(f"• **{row['Ürün Adı']}** | Kategori: {row['Kategori']} | Kalan: **{row['Kalan Miktar']} {row['Birim']}** | Depo: {row['Depo Yeri']} | Eklenme Tarihi: **{row['Eklenme Tarihi']}** | *(Ekleyen: {row['İşlemi Yapan']})*")

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
        with st.form("fatura_formu"):
            tarih_giris = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            fatura_no_input = st.text_input("Fatura No / Belge No (Örn: FAT-2026-105)").strip().upper()
            urun = st.text_input("Ürün Adı (Örn: DOMATES - Büyük Harfle)").strip().upper()
            kategori = st.selectbox("Kategori", ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"])
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", ["Soğuk Hava Deposu +5/+6", "Soğuk Hava Deposu -18", "Sebze Deposu", "Kuru Gıda Deposu"])
            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)
            
            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted and urun:
                islem_yapan_kisi = st.session_state.aktif_kullanici
                fatura_no_degeri = fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
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
                    "islem_yapan": islem_yapan_kisi
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
                    "Toplam Tutar": f"{(g.get('miktar', 0) * g.get('fiyat', 0)):,.2f} ₺",
                    "Depo Yeri": g.get("depo", "-"),
                    "İşlemi Yapan": g.get("islem_yapan", "admin")
                })
            ozel_html_tablo_goster(fatura_log_tablosu)
        else:
            st.info("Kayıtlı mal alımı faturası bulunmuyor.")

# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
    if misafir_modu:
        st.warning("👀 Misafir modundasınız. Bu ekranda silme işlemi gerçekleştiremezsiniz.")
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
                secenekler = [f"{g['id']} - {g['urun']} (Eklenme: {g.get('tarih', '-')}, Kalan: {g['kalan']} {g['birim']})" for g in st.session_state.girisler]
                secilen_kayit_str = st.selectbox("Silmek İstediğiniz Kaydı / Faturayı Seçin", secenekler)
                silme_nedeni_input = st.text_input("Silme Nedeni / Gerekçesi", "Örn: Yanlış giriş")
                sil_onay_btn = st.form_submit_button("Seçilen Kaydı Kalıcı Olarak Sil", type="primary")

                if sil_onay_btn:
                    secilen_id = secilen_kayit_str.split(" - ")[0]
                    ilgili_oge = next((g for g in st.session_state.girisler if g["id"] == secilen_id), None)
                    if ilgili_oge:
                        silinen_urun_adi = ilgili_oge['urun']
                        st.session_state.silinen_urun_loglari.append({
                            "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "urun": silinen_urun_adi,
                            "kayit_id": ilgili_oge['id'],
                            "fatura_no": ilgili_oge.get('fatura_no', '-'),
                            "neden": silme_nedeni_input if silme_nedeni_input else "Belirtilmedi",
                            "islem_yapan": st.session_state.aktif_kullanici
                        })
                        silinen_urun_loglarini_kaydet(st.session_state.silinen_urun_loglari)
                        st.session_state.girisler = [g for g in st.session_state.girisler if g["id"] != secilen_id]
                        verileri_kaydet(st.session_state.girisler)
                        st.session_state.silme_mesaji = f"Başarılı! {silinen_urun_adi} sistemden silindi."
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Silinen Ürünler Arşivi")
    if st.session_state.silinen_urun_loglari:
        silinen_tablo_verisi = [{
            "Silinme Tarihi": sl["tarih"],
            "Kayıt ID": sl.get("kayit_id", "-"),
            "Ürün Adı": sl["urun"],
            "Silme Nedeni": sl["neden"],
            "İşlemi Yapan": sl.get("islem_yapan", "admin")
        } for sl in st.session_state.silinen_urun_loglari]
        ozel_html_tablo_goster(silinen_tablo_verisi)
    else:
        st.info("Silinmiş ürün kaydı bulunmuyor.")

# 4. FİRE / ZAYİAT GİRİŞİ
elif menu == "Fire / Zayiat Girişi":
    st.header("🗑️ Fire / Zayiat Bildirimi")
    if misafir_modu:
        st.warning("👀 Misafir modundasınız.")
    else:
        with st.form("fire_formu"):
            benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
            secilen_gercek_urun = st.selectbox("Fire Düşülecek Ürünü Seçin", benzersiz_urunler)
            ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == secilen_gercek_urun and g["kalan"] > 0]
            toplam_stok = sum(g["kalan"] for g in ilgili_girisler)
            st.info(f"Mevcut Stok: {toplam_stok}")
            fire_miktari = st.number_input("Fire Miktarı", min_value=0.0, max_value=float(toplam_stok) if toplam_stok>0 else 1.0, step=0.1)
            
            submitted_fire = st.form_submit_button("Fireyi Düş ve Kaydet")
            if submitted_fire and fire_miktari > 0:
                kalan_dusulecek = fire_miktari
                toplam_zarar = 0.0
                for g in ilgili_girisler:
                    if kalan_dusulecek <= 0: break
                    if g["kalan"] >= kalan_dusulecek:
                        g["kalan"] -= kalan_dusulecek
                        toplam_zarar += kalan_dusulecek * g["fiyat"]
                        kalan_dusulecek = 0
                    else:
                        dusulen = g["kalan"]
                        g["kalan"] = 0
                        toplam_zarar += dusulen * g["fiyat"]
                        kalan_dusulecek -= dusulen
                verileri_kaydet(st.session_state.girisler)
                st.session_state.kullanim_loglari.append({
                    "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "urun": secilen_gercek_urun,
                    "tur": "Fire/Zayiat",
                    "miktar": fire_miktari,
                    "tutar": toplam_zarar,
                    "islem_yapan": st.session_state.aktif_kullanici
                })
                loglari_kaydet(st.session_state.kullanim_loglari)
                st.success("Fire başarıyla düşüldü.")
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Kayıtlı Fire ve Zayiatlar Listesi")
    fire_loglari = [l for l in st.session_state.kullanim_loglari if l.get("tur") == "Fire/Zayiat"]
    if fire_loglari:
        fire_tablo_verisi = []
        for f_log in reversed(fire_loglari):
            fire_tablo_verisi.append({
                "Tarih / Saat": f_log.get("tarih", "-"),
                "Ürün Adı": f_log.get("urun", "-"),
                "Fire Miktarı": f"{f_log.get('miktar', 0)} Kg",
                "Toplam Tutar": f"{f_log.get('tutar', 0):,.2f} ₺",
                "İşlemi Yapan": f_log.get("islem_yapan", "admin")
            })
        ozel_html_tablo_goster(fire_tablo_verisi)
    else:
        st.info("Sistemde kayıtlı fire / zayiat bulunmuyor.")

# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi ve Maliyet")
    yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
    kisi_sayisi = st.number_input("Yararlanan Kişi Sayısı", min_value=1, value=200)
    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    
    if "sepet" not in st.session_state:
        st.session_state.sepet = []
        
    if not misafir_modu:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            secilen_urun = st.selectbox("Malzeme Seç", benzersiz_urunler, key="yemek_urun")
        with col2:
            ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == secilen_urun and g["kalan"] > 0]
            stok_max = sum(g["kalan"] for g in ilgili_girisler)
            kullanilacak_miktar = st.number_input(f"Miktar (Stok: {stok_max})", min_value=0.0, max_value=float(stok_max) if stok_max>0 else 0.1, step=0.1, key="yemek_miktar")
        with col3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Sepete Ekle", use_container_width=True):
                if kullanilacak_miktar > 0 and kullanilacak_miktar <= stok_max:
                    st.session_state.sepet.append({"urun": secilen_urun, "miktar": kullanilacak_miktar})
                    st.success("Eklendi!")
                    st.rerun()

    st.markdown("---")
    st.subheader("Seçilen Malzemeler")
    
    if st.session_state.sepet:
        if st.button("🔄 Tümünü Sıfırla"):
            st.session_state.sepet = []
            st.rerun()
        
        toplam_maliyet = 0.0
        excel_sepet_liste = []
        
        silinecek_index = None
        for idx, item in enumerate(st.session_state.sepet):
            urun = item["urun"]
            istenen = item["miktar"]
            
            ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == urun]
            ortalama_fiyat = 0.0
            if ilgili_girisler:
                toplam_fiyat_degeri = sum(g["fiyat"] * g["miktar"] for g in ilgili_girisler)
                toplam_miktar_degeri = sum(g["miktar"] for g in ilgili_girisler)
                ortalama_fiyat = toplam_fiyat_degeri / toplam_miktar_degeri if toplam_miktar_degeri > 0 else 0.0
            
            item_maliyeti = istenen * ortalama_fiyat
            toplam_maliyet += item_maliyeti
            
            c_item_ad, c_item_mik, c_item_mal, c_item_sil = st.columns([3, 2, 2, 1])
            with c_item_ad:
                st.markdown(f"• **{urun}**")
            with c_item_mik:
                st.markdown(f"Miktar: {istenen}")
            with c_item_mal:
                st.markdown(f"Maliyet: **{item_maliyeti:,.2f} ₺**")
            with c_item_sil:
                if st.button("❌", key=f"sil_item_{idx}"):
                    silinecek_index = idx
            
            excel_sepet_liste.append({"Malzeme": urun, "Miktar": istenen, "Maliyet (TL)": round(item_maliyeti, 2)})

        if silinecek_index is not None:
            st.session_state.sepet.pop(silinecek_index)
            st.rerun()

        st.markdown("---")
        kisi_basi_maliyet = toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0.0

        m1, m2 = st.columns(2)
        with m1:
            st.metric("Toplam Maliyet", f"{toplam_maliyet:,.2f} ₺")
        with m2:
            st.metric("Kişi Başı Maliyet", f"{kisi_basi_maliyet:,.2f} ₺")

        pdf_data = tablo_to_html_pdf_bytes(f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste)
        excel_sepet_data = tablo_to_excel_bytes(excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}")
        with col_indir_alan:
            ortak_indirme_alani(excel_sepet_data, pdf_data, "yemek_maliyet_raporu", "yemek_sayfasi")
    else:
        st.info("Henüz sepete malzeme eklenmedi.")

# 6. KALORİ HESAPLAMA ARACI
elif menu == "Kalori Hesaplama Aracı":
    col_b_kal, col_indir_kal = st.columns([2, 2])
    with col_b_kal:
        st.header("🔥 Kalori Hesaplama Aracı")
    
    benzersiz_urunler_kalori = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    col_k_sec1, col_k_sec2, col_k_sec3 = st.columns([2, 1, 1])
    with col_k_sec1:
        secilen_kalori_urun = st.selectbox("Malzeme Seçin", benzersiz_urunler_kalori, key="kalori_urun_sec")
    with col_k_sec2:
        kalori_miktar_input = st.number_input("Miktar", min_value=0.1, value=1.0, step=0.5, key="kalori_mik")
    with col_k_sec3:
        kalori_birim_input = st.selectbox("Birim", ["Kg", "Adet", "Lt"], key="kalori_brm")

    if st.button("➕ Listeye Ekle"):
        st.session_state.kalori_sepeti.append({"urun": secilen_kalori_urun, "miktar": kalori_miktar_input, "birim": kalori_birim_input})
        st.success("Eklendi!")

    if st.session_state.kalori_sepeti:
        toplam_kalori = sum(urun_kalori_hesapla(i["urun"], i["miktar"], i["birim"]) for i in st.session_state.kalori_sepeti)
        st.metric("Toplam Tarif Kalorisi", f"{toplam_kalori:,.0f} kcal")

# 7. İHTİYAÇ SAHİBİ & YEMEK DAĞITIM TAKİBİ
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    st.header("👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi")
    st.markdown("Aşevimizden yemek yardımı alan kişilerin kayıtlarını oluşturun, yönetin ve yemek dağıtımlarını takip edin.")

    tab1, tab2, tab3 = st.tabs(["📋 İhtiyaç Sahibi Listesi, Ekle ve Sil", "🍲 Yemek Dağıtım Girişi", "📊 Dağıtım Raporları (Günlük/Aylık/Yıllık)"])

    with tab1:
        if st.session_state.kisi_silme_mesaji:
            st.success(st.session_state.kisi_silme_mesaji)
            st.session_state.kisi_silme_mesaji = ""

        if misafir_modu:
            st.info("👀 Misafir modundasınız. Bu ekranda yalnızca kayıtlı ihtiyaç sahiplerini gözlemleyebilirsiniz.")
        else:
            col_form_ekle, col_form_sil = st.columns(2)
            with col_form_ekle:
                with st.form("ihtiyac_sahibi_formu"):
                    st.markdown("**➕ Yeni İhtiyaç Sahibi / Hane Ekle**")
                    yeni_tc_hane = st.text_input("T.C. Kimlik No / Hane No").strip()
                    yeni_ad = st.text_input("Adı Soyadı / Hane Unvanı").strip().upper()
                    yeni_tel = st.text_input("Telefon Numarası")
                    yeni_adres = st.text_input("Açık Adres")
                    yeni_birey = st.number_input("Aile / Hane Birey Sayısı", min_value=1, value=1)
                    
                    kaydet_btn = st.form_submit_button("İhtiyaç Sahibini Kaydet")
                    if kaydet_btn and yeni_ad:
                        islem_tarihi_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        islem_yapan_kisi = st.session_state.aktif_kullanici
                        st.session_state.ihtiyac_sahipleri.append({
                            "id": f"IHT-{len(st.session_state.ihtiyac_sahipleri)+1:03d}",
                            "tc_hane": yeni_tc_hane,
                            "ad_soyad": yeni_ad,
                            "telefon": yeni_tel,
                            "adres": yeni_adres,
                            "birey_sayisi": yeni_birey,
                            "eklenme_tarihi": islem_tarihi_str,
                            "islem_yapan": islem_yapan_kisi
                        })
                        ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                        st.success(f"Başarılı! {yeni_ad} sisteme kaydedildi.")
                        st.rerun()

            with col_form_sil:
                with st.form("ihtiyac_sahibi_sil_formu"):
                    st.markdown("**🗑️ Kayıtlı İhtiyaç Sahibini Sil**")
                    if st.session_state.ihtiyac_sahipleri:
                        kisi_secenekleri_sil = [f"{k['id']} - {k['ad_soyad']} (T.C./Hane: {k.get('tc_hane', '-')})" for k in st.session_state.ihtiyac_sahipleri]
                        secilen_silinecek = st.selectbox("Silinecek Kişiyi / Haneyi Seçin", kisi_secenekleri_sil)
                        sil_btn = st.form_submit_button("Seçilen Kişiyi Sistemden Sil", type="primary")
                        
                        if sil_btn:
                            silinecek_id = secilen_silinecek.split(" - ")[0]
                            silinen_kisi_obj = next((k for k in st.session_state.ihtiyac_sahipleri if k["id"] == silinecek_id), None)
                            silinen_isim = silinen_kisi_obj["ad_soyad"] if silinen_kisi_obj else ""
                            st.session_state.ihtiyac_sahipleri = [k for k in st.session_state.ihtiyac_sahipleri if k["id"] != silinecek_id]
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.session_state.kisi_silme_mesaji = f"Başarılı! {silinen_isim} sistemden silindi."
                            st.rerun()
                    else:
                        st.info("Silinecek kayıt bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı İhtiyaç Sahipleri Listesi")
        if st.session_state.ihtiyac_sahipleri:
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
                    "İşlemi Yapan": k.get("islem_yapan", "admin")
                })
            ozel_html_tablo_goster(kisi_liste_gosterim)
        else:
            st.info("Sistemde kayıtlı ihtiyaç sahibi bulunmuyor.")

    with tab2:
        st.subheader("🍲 Günlük Yemek Dağıtım Kaydı")
        if misafir_modu:
            st.info("👀 Misafir modundasınız. Bu ekranda yeni dağıtım kaydı oluşturamazsınız.")
        elif not st.session_state.ihtiyac_sahipleri:
            st.warning("Önce 'İhtiyaç Sahibi Listesi, Ekle ve Sil' sekmesinden kişi kaydı yapmalısınız.")
        else:
            with st.form("dagitim_formu"):
                d_tarih_saat = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                kisi_secenekleri = [k["ad_soyad"] for k in st.session_state.ihtiyac_sahipleri]
                secilen_kisi = st.selectbox("Yemek Alan Kişi / Hane", kisi_secenekleri)
                menu_adi = st.text_input("Verilen Menü / Yemek Adı", "Ispanak Yemeği ve Pilav")
                porsiyon_mik = st.number_input("Verilen Porsiyon / Sefer Tası Miktarı", min_value=1, value=1)
                
                dagitim_ekle_btn = st.form_submit_button("Dağıtımı Kaydet")
                if dagitim_ekle_btn:
                    st.session_state.dagitim_loglari.append({
                        "tarih": d_tarih_saat,
                        "kisi": secilen_kisi,
                        "menu": menu_adi,
                        "porsiyon": porsiyon_mik,
                        "islem_yapan": st.session_state.aktif_kullanici
                    })
                    dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                    st.success("Başarılı! Yemek dağıtımı kaydedildi.")
                    st.rerun()

    with tab3:
        st.subheader("📊 Kim Ne Kadar Süredir Yemek Almış?")
        kisi_secenekleri_rapor = ["Tüm İhtiyaç Sahipleri (Genel Rapor)"] + [k["ad_soyad"] for k in st.session_state.ihtiyac_sahipleri]
        secilen_rapor_kisi = st.selectbox("Raporlanacak Kişiyi Seçin", kisi_secenekleri_rapor, key="rapor_kisi_sec")
        dagitimlar = st.session_state.dagitim_loglari
        if secilen_rapor_kisi != "Tüm İhtiyaç Sahipleri (Genel Rapor)":
            dagitimlar = [d for d in dagitimlar if d["kisi"] == secilen_rapor_kisi]
        
        toplam_porsiyon_alınan = sum(d["porsiyon"] for d in dagitimlar)
        toplam_alis_sefer_sayisi = len(dagitimlar)
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Toplam Alınan Öğün / Sefer Sayısı", f"{toplam_alis_sefer_sayisi} Kez")
        with m2:
            st.metric("Toplam Dağıtılan Porsiyon", f"{toplam_porsiyon_alınan} Porsiyon")

# 8. PERSONEL & ÇALIŞMA SÜRESİ TAKİBİ
elif menu == "Personel & Çalışma Süresi Takibi":
    st.header("👥 Personel ve Çalışma Süresi Takibi")
    st.markdown("Personel yönetimi, yıllık izinler, saatlik izinler, sağlık raporları ve resmi tatilleri bu ekrandan yönetebilirsiniz.")

    p_tab1, p_tab2, p_tab3, p_tab4, p_tab5 = st.tabs([
        "👨‍💼 Personel Listesi", 
        "🏖️ Yıllık İzinler", 
        "⏰ Saatlik İzinler", 
        "🏥 Sağlık Raporları", 
        "📊 Net Çalışma Raporu"
    ])

    with p_tab1:
        if st.session_state.personel_silme_mesaji:
            st.success(st.session_state.personel_silme_mesaji)
            st.session_state.personel_silme_mesaji = ""

        if misafir_modu:
            st.info("👀 Misafir modundasınız. Bu ekranda yalnızca personel listesini görüntüleyebilirsiniz.")
        else:
            col_p_ekle, col_p_sil, col_p_durum = st.columns(3)
            with col_p_ekle:
                with st.form("personel_ekle_form"):
                    st.markdown("**➕ Yeni Personel Ekle**")
                    p_tc = st.text_input("T.C. No").strip()
                    p_ad = st.text_input("Personel Adı Soyadı").strip().upper()
                    p_gorev = st.text_input("Görevi (Örn: Aşçı)")
                    p_bas = st.date_input("İşe Başlama Tarihi", value=datetime.date.today())
                    p_submit = st.form_submit_button("Personeli Kaydet")
                    
                    if p_submit and p_ad:
                        st.session_state.personeller.append({
                            "tc": p_tc if p_tc else "00000000000",
                            "ad_soyad": p_ad,
                            "gorev": p_gorev if p_gorev else "Personel",
                            "baslama": str(p_bas),
                            "aktif": True,
                            "izinler": []
                        })
                        personelleri_kaydet(st.session_state.personeller)
                        st.success(f"Başarılı! {p_ad} kadroya eklendi.")
                        st.rerun()

            with col_p_sil:
                with st.form("personel_sil_form"):
                    st.markdown("**🗑️ Personeli Sil**")
                    if st.session_state.personeller:
                        p_sil_secenekleri = [f"{p.get('tc', '---')} - {p['ad_soyad']}" for p in st.session_state.personeller]
                        secilen_sil_p = st.selectbox("Silinecek Personel", p_sil_secenekleri)
                        p_sil_btn = st.form_submit_button("Personeli Kadrodan Sil", type="primary")
                        
                        if p_sil_btn:
                            sil_tc = secilen_sil_p.split(" - ")[0]
                            silinen_obj = next((p for p in st.session_state.personeller if p.get('tc') == sil_tc), None)
                            silinen_ad = silinen_obj["ad_soyad"] if silinen_obj else ""
                            st.session_state.personeller = [p for p in st.session_state.personeller if p.get('tc') != sil_tc]
                            personelleri_kaydet(st.session_state.personeller)
                            st.session_state.personel_silme_mesaji = f"Başarılı! {silinen_ad} kadrodan silindi."
                            st.rerun()
                    else:
                        st.info("Silinecek personel bulunmuyor.")

            with col_p_durum:
                with st.form("personel_durum_form"):
                    st.markdown("**🔄 Durum Güncelle**")
                    if st.session_state.personeller:
                        p_secenekler = [f"{p.get('tc', '---')} - {p['ad_soyad']} ({'Aktif' if p.get('aktif', True) else 'Pasif'})" for p in st.session_state.personeller]
                        secilen_p_str = st.selectbox("Personel Seç", p_secenekler)
                        yeni_durum = st.radio("Durum", ["Aktif Çalışıyor", "Pasif / Ayrıldı"], horizontal=True)
                        p_durum_btn = st.form_submit_button("Durumu Güncelle")
                        
                        if p_durum_btn:
                            p_tc_secilen = secilen_p_str.split(" - ")[0]
                            for p in st.session_state.personeller:
                                if p.get('tc') == p_tc_secilen:
                                    p["aktif"] = (yeni_durum == "Aktif Çalışıyor")
                            personelleri_kaydet(st.session_state.personeller)
                            st.success("Durum güncellendi!")
                            st.rerun()
                    else:
                        st.info("Kayıt yok.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Personel Kadrosu")
        if st.session_state.personeller:
            bugun_tarihi = datetime.date.today()
            p_gosterim = []
            for p in st.session_state.personeller:
                bas_tarih_str = p.get("baslama", "2026-01-01")
                try:
                    bas_dt = datetime.datetime.strptime(bas_tarih_str, "%Y-%m-%d").date()
                except:
                    bas_dt = datetime.date(2026, 1, 1)
                net_calisilan, _, _, _ = net_calisma_gunu_hesapla(bas_dt, bugun_tarihi, p.get("izinler", []), st.session_state.resmi_tatiller)
                p_gosterim.append({
                    "T.C. No": p.get("tc", "-"),
                    "Adı Soyadı": p["ad_soyad"],
                    "Görevi": p["gorev"],
                    "İşe Başlama": bas_tarih_str,
                    "Çalışma Günü Sayacı": f"{net_calisilan} Gün",
                    "Durum": "Aktif Çalışıyor" if p.get("aktif", True) else "Pasif / Ayrıldı"
                })
            ozel_html_tablo_goster(p_gosterim)
        else:
            st.info("Kayıtlı personel bulunmuyor.")

    with p_tab2:
        st.subheader("🏖️ Yıllık İzin Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Yıllık izin işlemleri yalnızca **Admin** tarafından yapılabilir.")
        else:
            col_y_ekle, col_y_sil = st.columns(2)
            with col_y_ekle:
                with st.form("yillik_izin_form"):
                    st.markdown("**➕ Yıllık İzin Ekle**")
                    p_izin_secenekleri = [p["ad_soyad"] for p in st.session_state.personeller if p.get("aktif", True)]
                    if p_izin_secenekleri:
                        secilen_p = st.selectbox("Personel Seçin", p_izin_secenekleri, key="yil_p")
                        i_bas = st.date_input("İzin Başlangıç Tarihi", key="yil_bas")
                        i_bit = st.date_input("İzin Bitiş Tarihi", key="yil_bit")
                        yil_submit = st.form_submit_button("Yıllık İzni Kaydet")
                        
                        if yil_submit:
                            if i_bas > i_bit:
                                st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                            else:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_p:
                                        if "izinler" not in p: p["izinler"] = []
                                        p["izinler"].append({"tur": "Yıllık İzin", "baslangic": str(i_bas), "bitis": str(i_bit)})
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
                                tum_yillik_izinler.append({"personel": p["ad_soyad"], "idx": idx, "ozet": f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} - Bitiş: {iz['bitis']}"})
                    
                    if tum_yillik_izinler:
                        secenek_sil_y = [item["ozet"] for item in tum_yillik_izinler]
                        secilen_sil_y_str = st.selectbox("Silinecek İzni Seçin", secenek_sil_y)
                        y_sil_btn = st.form_submit_button("Seçilen İzni Sil", type="primary")
                        
                        if y_sil_btn:
                            secilen_item = next((item for item in tum_yillik_izinler if item["ozet"] == secilen_sil_y_str), None)
                            if secilen_item:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_item["personel"]:
                                        yilliklar = [i for i in p["izinler"] if i.get("tur") == "Yıllık İzin"]
                                        digerleri = [i for i in p["izinler"] if i.get("tur") != "Yıllık İzin"]
                                        silinecek_hedef = yilliklar[secilen_item["idx"]]
                                        p["izinler"] = digerleri + [i for i in yilliklar if i != silinecek_hedef]
                                personelleri_kaydet(st.session_state.personeller)
                                st.success("Seçilen yıllık izin silindi!")
                                st.rerun()
                    else:
                        st.info("Silinebilecek yıllık izin kaydı bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Tüm Yıllık İzinler")
        yillik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Yıllık İzin":
                    yillik_tablo_listesi.append({"Personel": p["ad_soyad"], "İzin Türü": "Yıllık İzin", "Başlangıç": iz.get("baslangic", "-"), "Bitiş": iz.get("bitis", "-")})
        if yillik_tablo_listesi:
            ozel_html_tablo_goster(yillik_tablo_listesi)
        else:
            st.info("Kayıtlı yıllık izin bulunmuyor.")

    with p_tab3:
        st.subheader("⏰ Saatlik İzin Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Saatlik izin işlemleri yalnızca **Admin** tarafından yapılabilir.")
        else:
            col_s_ekle, col_s_sil = st.columns(2)
            with col_s_ekle:
                with st.form("saatlik_izin_form"):
                    st.markdown("**➕ Saatlik İzin Ekle**")
                    p_saat_secenekleri = [p["ad_soyad"] for p in st.session_state.personeller if p.get("aktif", True)]
                    if p_saat_secenekleri:
                        secilen_p_saat = st.selectbox("Personel Seçin", p_saat_secenekleri, key="saat_p")
                        s_tarih = st.date_input("İzin Tarihi", key="saat_tarih")
                        col_saat1, col_saat2 = st.columns(2)
                        with col_saat1: s_bas_saat = st.time_input("Başlangıç Saati", value=datetime.time(9, 0))
                        with col_saat2: s_bit_saat = st.time_input("Bitiş Saati", value=datetime.time(11, 0))
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
                                        if "izinler" not in p: p["izinler"] = []
                                        p["izinler"].append({"tur": "Saatlik İzin", "baslangic": str(s_tarih), "bitis": str(s_tarih), "saat": round(fark_saat, 2), "detay": f"{s_bas_saat.strftime('%H:%M')} - {s_bit_saat.strftime('%H:%M')} ({s_aciklama})"})
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
                                tum_saatlik_izinler.append({"personel": p["ad_soyad"], "idx": idx, "ozet": f"{p['ad_soyad']} | Tarih: {iz['baslangic']} | {iz.get('saat')} Saat"})
                    
                    if tum_saatlik_izinler:
                        secenek_sil_s = [item["ozet"] for item in tum_saatlik_izinler]
                        secilen_sil_s_str = st.selectbox("Silinecek Saatlik İzni Seçin", secenek_sil_s)
                        s_sil_btn = st.form_submit_button("Seçilen İzni Sil", type="primary")
                        
                        if s_sil_btn:
                            secilen_item_s = next((item for item in tum_saatlik_izinler if item["ozet"] == secilen_sil_s_str), None)
                            if secilen_item_s:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_item_s["personel"]:
                                        saatlikler = [i for i in p["izinler"] if i.get("tur") == "Saatlik İzin"]
                                        digerleri = [i for i in p["izinler"] if i.get("tur") != "Saatlik İzin"]
                                        silinecek_hedef_s = saatlikler[secilen_item_s["idx"]]
                                        p["izinler"] = digerleri + [i for i in saatlikler if i != silinecek_hedef_s]
                                personelleri_kaydet(st.session_state.personeller)
                                st.success("Saatlik izin silindi!")
                                st.rerun()
                    else:
                        st.info("Silinebilecek saatlik izin yok.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Tüm Saatlik İzinler")
        saatlik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Saatlik İzin":
                    saatlik_tablo_listesi.append({"Personel": p["ad_soyad"], "İzin Türü": "Saatlik İzin", "Tarih": iz.get("baslangic", "-"), "Süre (Saat)": iz.get("saat", 0), "Detay": iz.get("detay", "-")})
        if saatlik_tablo_listesi:
            ozel_html_tablo_goster(saatlik_tablo_listesi)
        else:
            st.info("Kayıtlı saatlik izin bulunmuyor.")

    with p_tab4:
        st.subheader("🏥 Sağlık Raporu Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Sağlık raporu işlemleri yalnızca **Admin** tarafından yapılabilir.")
        else:
            col_r_ekle, col_r_sil = st.columns(2)
            with col_r_ekle:
                with st.form("saglik_raporu_form"):
                    st.markdown("**➕ Sağlık Raporu Ekle**")
                    p_rap_secenekleri = [p["ad_soyad"] for p in st.session_state.personeller if p.get("aktif", True)]
                    if p_rap_secenekleri:
                        secilen_p_rap = st.selectbox("Personel Seçin", p_rap_secenekleri, key="rap_p")
                        r_nereden = st.text_input("Kurum / Hastane", "Örn: Erzurum Şehir Hastanesi")
                        col_r1, col_r2 = st.columns(2)
                        with col_r1: r_bas = st.date_input("Başlangıç Tarihi", key="rap_bas")
                        with col_r2: r_bit = st.date_input("Bitiş Tarihi", key="rap_bit")
                        r_teshis = st.text_input("Teşhis / Açıklama", "Örn: Üst Solunum Yolu")
                        rap_submit = st.form_submit_button("Sağlık Raporunu Kaydet")
                        
                        if rap_submit:
                            if r_bas > r_bit:
                                st.error("Başlangıç bitişten sonra olamaz!")
                            else:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_p_rap:
                                        if "izinler" not in p: p["izinler"] = []
                                        p["izinler"].append({"tur": "Sağlık Raporu", "baslangic": str(r_bas), "bitis": str(r_bit), "kurum": r_nereden, "teshis": r_teshis})
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
                                tum_saglik_raporlari.append({"personel": p["ad_soyad"], "idx": idx, "ozet": f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} ({iz.get('teshis')})"})
                    
                    if tum_saglik_raporlari:
                        secenek_sil_r = [item["ozet"] for item in tum_saglik_raporlari]
                        secilen_sil_r_str = st.selectbox("Silinecek Raporu Seçin", secenek_sil_r)
                        r_sil_btn = st.form_submit_button("Seçilen Raporu Sil", type="primary")
                        
                        if r_sil_btn:
                            secilen_item_r = next((item for item in tum_saglik_raporlari if item["ozet"] == secilen_sil_r_str), None)
                            if secilen_item_r:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_item_r["personel"]:
                                        raporlar = [i for i in p["izinler"] if i.get("tur") == "Sağlık Raporu"]
                                        digerleri = [i for i in p["izinler"] if i.get("tur") != "Sağlık Raporu"]
                                        silinecek_hedef_r = raporlar[secilen_item_r["idx"]]
                                        p["izinler"] = digerleri + [i for i in raporlar if i != silinecek_hedef_r]
                                personelleri_kaydet(st.session_state.personeller)
                                st.success("Sağlık raporu silindi!")
                                st.rerun()
                    else:
                        st.info("Silinebilecek sağlık raporu yok.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Tüm Sağlık Raporları")
        saglik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Sağlık Raporu":
                    saglik_tablo_listesi.append({"Personel": p["ad_soyad"], "İzin Türü": "Sağlık Raporu", "Kurum": iz.get("kurum", "-"), "Başlangıç": iz.get("baslangic", "-"), "Bitiş": iz.get("bitis", "-"), "Teşhis": iz.get("teshis", "-")})
        if saglik_tablo_listesi:
            ozel_html_tablo_goster(saglik_tablo_listesi)
        else:
            st.info("Kayıtlı sağlık raporu bulunmuyor.")

    with p_tab5:
        st.subheader("📊 Personel Net Çalışma Süresi Raporu")
        if not st.session_state.personeller:
            st.info("Kayıtlı personel bulunmuyor.")
        else:
            p_isimleri = [p["ad_soyad"] for p in st.session_state.personeller]
            secilen_rapor_p = st.selectbox("Personel Seçin", p_isimleri, key="prs_rapor_sec")
            c_kol1, c_kol2 = st.columns(2)
            with c_kol1: donem_bas = st.date_input("Dönem Başlangıç", value=datetime.date(2026, 10, 1), key="d_bas")
            with c_kol2: donem_bit = st.date_input("Dönem Bitiş", value=datetime.date(2026, 10, 31), key="d_bit")

            if donem_bas > donem_bit:
                st.error("⚠️ Başlangıç tarihi bitişten büyük olamaz!")
            else:
                ilgili_personel_obj = next((p for p in st.session_state.personeller if p["ad_soyad"] == secilen_rapor_p), None)
                if ilgili_personel_obj:
                    net_gun, toplam_izin, saglik_raporu_gun, saatlik_izin_saat = net_calisma_gunu_hesapla(donem_bas, donem_bit, ilgili_personel_obj.get("izinler", []), st.session_state.resmi_tatiller)
                    m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                    with m_p1: st.metric("Net Çalışılan Gün", f"{net_gun} Gün")
                    with m_p2: st.metric("Yıllık İzin", f"{toplam_izin} Gün")
                    with m_p3: st.metric("Sağlık Raporu", f"{saglik_raporu_gun} Gün")
                    with m_p4: st.metric("Saatlik İzin", f"{saatlik_izin_saat} Saat")

# 9. KULLANIM TAKİBİ
elif menu == "Kullanım Takibi":
    col_b_kul, col_indir_kul = st.columns([2, 2])
    with col_b_kul:
        st.header("📈 Depo Ürün Kullanım Takibi")
    loglar = st.session_state.kullanim_loglari
    if loglar:
        ozel_html_tablo_goster(loglar)
    else:
        st.info("Kullanım hareketi bulunmuyor.")

# 10. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_fiy, col_indir_fiy = st.columns([2, 2])
    with col_b_fiy:
        st.header("💰 Ürün Birim Fiyatları")
    if st.session_state.girisler:
        fiyat_tablo = [{"Ürün": g["urun"], "Fiyat": g["fiyat"], "Birim": g["birim"]} for g in st.session_state.girisler]
        ozel_html_tablo_goster(fiyat_tablo)
