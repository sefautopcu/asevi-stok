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
            background-color: #1E293B !important; 
            padding-top: 10px; 
            border-right: 1px solid #334155;
        }
        .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
            color: #94A3B8 !important; 
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
            color: #CBD5E1 !important;
            border: none !important;
            border-radius: 8px !important;
            text-align: left !important;
            font-weight: 400 !important;
            padding: 6px 10px !important;
            transition: all 0.2s ease;
        }
        section[data-testid="stSidebar"] button[kind="secondary"]:hover {
            background-color: #334155 !important;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #334155 !important;
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
            background-color: #F4F5F7 !important; 
            padding-top: 10px; 
            border-right: 1px solid #E5E7EB;
        }
        .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { 
            color: #374151 !important; 
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
            background-color: #EFEFF1 !important;
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

# Kalori Sözlüğü
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

# Stok Başlangıç Listesi
varsayilan_girisler = [
    {"id": "STK-001", "tarih": "2026-09-28 08:30", "fatura_no": "FAT-2026-001", "urun": "KIRMIZI LAHANA", "kategori": "SEBZE", "birim": "Kg", "miktar": 42.8, "kalan": max(0.0, 42.8 - 15.0), "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-002", "tarih": "2026-09-28 08:35", "fatura_no": "FAT-2026-002", "urun": "MAYDANOZ", "kategori": "SEBZE", "birim": "Kg", "miktar": 20.0, "kalan": max(0.0, 20.0 - 3.1), "fiyat": 25.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-003", "tarih": "2026-09-28 09:00", "fatura_no": "FAT-2026-003", "urun": "MUZ", "kategori": "MEYVE", "birim": "Kg", "miktar": 54.5, "kalan": 0.0, "fiyat": 110.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-004", "tarih": "2026-09-28 09:10", "fatura_no": "FAT-2026-004", "urun": "ELMA", "kategori": "MEYVE", "birim": "Kg", "miktar": 82.0, "kalan": max(0.0, 82.0 - 41.0), "fiyat": 70.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-005", "tarih": "2026-09-28 09:15", "fatura_no": "FAT-2026-005", "urun": "ERİK", "kategori": "MEYVE", "birim": "Kg", "miktar": 62.0, "kalan": max(0.0, 62.0 - 50.0), "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-006", "tarih": "2026-09-28 09:20", "fatura_no": "FAT-2026-006", "urun": "ŞEFTALİ", "kategori": "MEYVE", "birim": "Kg", "miktar": 50.0, "kalan": 0.0, "fiyat": 90.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-007", "tarih": "2026-09-28 09:30", "fatura_no": "FAT-2026-007", "urun": "SOĞAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 400.0, "kalan": max(0.0, 400.0 - 29.0), "fiyat": 35.0, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-008", "tarih": "2026-09-28 09:40", "fatura_no": "FAT-2026-008", "urun": "PATATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 755.0, "kalan": max(0.0, 755.0 - 72.0), "fiyat": 33.0, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-009", "tarih": "2026-09-28 10:00", "fatura_no": "FAT-2026-009", "urun": "KABAK", "kategori": "SEBZE", "birim": "Kg", "miktar": 52.0, "kalan": max(0.0, 52.0 - 35.0), "fiyat": 45.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-010", "tarih": "2026-09-28 10:10", "fatura_no": "FAT-2026-010", "urun": "HAVUÇ", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.6, "kalan": max(0.0, 50.6 - 15.0), "fiyat": 35.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-011", "tarih": "2026-09-28 10:20", "fatura_no": "FAT-2026-011", "urun": "ISPANAK", "kategori": "SEBZE", "birim": "Kg", "miktar": 127.0, "kalan": max(0.0, 127.0 - 22.0 - 60.0), "fiyat": 70.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-012", "tarih": "2026-09-28 10:30", "fatura_no": "FAT-2026-012", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 57.4, "kalan": max(0.0, 57.4 - 5.0 - 52.4), "fiyat": 55.0, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-013", "tarih": "2026-09-28 10:40", "fatura_no": "FAT-2026-013", "urun": "ÇARLİ", "kategori": "SEBZE", "birim": "Kg", "miktar": 56.0, "kalan": max(0.0, 56.0 - 19.0), "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-014", "tarih": "2026-09-28 10:50", "fatura_no": "FAT-2026-014", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 66.0, "kalan": max(0.0, 66.0 - 52.0), "fiyat": 50.0, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-015", "tarih": "2026-09-28 11:00", "fatura_no": "FAT-2026-015", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 53.0, "kalan": max(0.0, 53.0 - 13.0 - 43.0), "fiyat": 45.0, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-016", "tarih": "2026-09-30 08:30", "fatura_no": "FAT-2026-016", "urun": "BALDO PİRİNÇ", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 625.0, "kalan": max(0.0, 625.0 - 62.0), "fiyat": 104.40, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-017", "tarih": "2026-09-30 08:40", "fatura_no": "FAT-2026-017", "urun": "KURU FASULYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 225.0, "kalan": max(0.0, 225.0 - 30.0), "fiyat": 84.72, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-018", "tarih": "2026-09-30 08:50", "fatura_no": "FAT-2026-018", "urun": "NOHUT", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 200.0, "kalan": max(0.0, 200.0 - 16.0), "fiyat": 68.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-019", "tarih": "2026-09-30 09:00", "fatura_no": "FAT-2026-019", "urun": "ARPA ŞEHRİYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 40.0, "kalan": max(0.0, 40.0 - 6.0), "fiyat": 43.98, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-020", "tarih": "2026-09-30 09:10", "fatura_no": "FAT-2026-020", "urun": "BURGU MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": max(0.0, 100.0 - 30.0), "fiyat": 43.98, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-021", "tarih": "2026-09-30 09:20", "fatura_no": "FAT-2026-021", "urun": "İNCE UZUN MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": max(0.0, 100.0 - 27.0), "fiyat": 43.98, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-022", "tarih": "2026-09-30 09:30", "fatura_no": "FAT-2026-022", "urun": "KIRMIZI MERCİMEK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 75.0, "kalan": max(0.0, 75.0 - 11.0), "fiyat": 94.04, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-023", "tarih": "2026-09-30 09:40", "fatura_no": "FAT-2026-023", "urun": "PİLAVLIK BULGUR", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 475.0, "kalan": max(0.0, 475.0 - 65.0), "fiyat": 39.40, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-024", "tarih": "2026-09-30 09:50", "fatura_no": "FAT-2026-024", "urun": "TEL ŞEHRİYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 40.0, "kalan": max(0.0, 40.0 - 4.0), "fiyat": 43.98, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-025", "tarih": "2026-09-30 10:00", "fatura_no": "FAT-2026-025", "urun": "TUZ", "kategori": "BAHARAT", "birim": "Adet", "miktar": 60.0, "kalan": max(0.0, 60.0 - 2.65), "fiyat": 11.39, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-026", "tarih": "2026-09-30 10:10", "fatura_no": "FAT-2026-026", "urun": "TEREYAĞI", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Kg", "miktar": 60.0, "kalan": max(0.0, 60.0 - 29.4), "fiyat": 464.31, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-027", "tarih": "2026-09-30 10:20", "fatura_no": "FAT-2026-027", "urun": "TENEKE AYÇİÇEK YAĞI", "kategori": "YAĞ", "birim": "Kg", "miktar": 378.0, "kalan": max(0.0, 378.0 - 15.0), "fiyat": 94.72, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-028", "tarih": "2026-09-30 10:30", "fatura_no": "FAT-2026-028", "urun": "BUĞDAY NİŞASTA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 165.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-029", "tarih": "2026-09-30 10:40", "fatura_no": "FAT-2026-029", "urun": "İRMİK", "kategori": "KURU GIDA", "birim": "Adet", "miktar": 160.0, "kalan": max(0.0, 160.0 - 10.0), "fiyat": 19.31, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-030", "tarih": "2026-09-30 10:50", "fatura_no": "FAT-2026-030", "urun": "TOZ KARABİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 10.0, "kalan": max(0.0, 10.0 - 0.32), "fiyat": 790.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-031", "tarih": "2026-09-30 11:00", "fatura_no": "FAT-2026-031", "urun": "KIRMIZI TATLI TOZ BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 10.0, "kalan": max(0.0, 10.0 - 0.54), "fiyat": 335.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-032", "tarih": "2026-09-30 11:10", "fatura_no": "FAT-2026-032", "urun": "KURU NANE", "kategori": "BAHARAT", "birim": "Kg", "miktar": 6.0, "kalan": max(0.0, 6.0 - 0.25), "fiyat": 279.50, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-033", "tarih": "2026-09-30 11:20", "fatura_no": "FAT-2026-033", "urun": "UN", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": max(0.0, 100.0 - 6.0), "fiyat": 35.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-034", "tarih": "2026-09-30 11:30", "fatura_no": "FAT-2026-034", "urun": "YAĞLI SÜT", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Lt", "miktar": 108.0, "kalan": 108.0, "fiyat": 49.90, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-035", "tarih": "2026-09-30 11:40", "fatura_no": "FAT-2026-035", "urun": "DOMATES SALÇASI", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 130.5, "kalan": max(0.0, 130.5 - 42.5), "fiyat": 66.44, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-036", "tarih": "2026-09-30 11:50", "fatura_no": "FAT-2026-036", "urun": "BEZELYE KONSERVESİ", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 102.0, "kalan": max(0.0, 102.0 - 42.5), "fiyat": 69.89, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-037", "tarih": "2026-10-01 08:30", "fatura_no": "FAT-2026-037", "urun": "TAM YAĞLI YOĞURT", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Kg", "miktar": 230.0, "kalan": max(0.0, 230.0 - 215.0 - 15.0), "fiyat": 66.20, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-038", "tarih": "2026-10-12 09:00", "fatura_no": "FAT-2026-038", "urun": "KUŞBAŞI ET", "kategori": "KASAP / ŞARKÜTERİ", "birim": "Kg", "miktar": 213.8, "kalan": max(0.0, 213.8 - 85.0), "fiyat": 570.00, "depo": "Soğuk Hava Deposu -18", "islem_yapan": "admin"},
    {"id": "STK-039", "tarih": "2026-10-21 10:00", "fatura_no": "FAT-2026-039", "urun": "SIRTSIZ GÖĞÜS", "kategori": "KASAP / ŞARKÜTERİ", "birim": "Kg", "miktar": 60.0, "kalan": max(0.0, 60.0 - 35.0), "fiyat": 118.00, "depo": "Soğuk Hava Deposu -18", "islem_yapan": "admin"},
    {"id": "STK-040", "tarih": "2026-10-28 08:30", "fatura_no": "FAT-2026-040", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 80.00, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-041", "tarih": "2026-10-28 08:35", "fatura_no": "FAT-2026-041", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 20.0, "kalan": 20.0, "fiyat": 105.00, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-042", "tarih": "2026-10-28 08:40", "fatura_no": "FAT-2026-042", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 61.00, "depo": "Sebze Deposu", "islem_yapan": "admin"},
    {"id": "STK-043", "tarih": "2026-10-28 08:45", "fatura_no": "FAT-2026-043", "urun": "KIRMIZI TATLI TOZ BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 40.0, "kalan": 40.0, "fiyat": 335.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-044", "tarih": "2026-10-28 08:50", "fatura_no": "FAT-2026-044", "urun": "TAM YAĞLI YOĞURT", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Kg", "miktar": 100.0, "kalan": 100.0, "fiyat": 66.20, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"},
    {"id": "STK-045", "tarih": "2026-10-28 09:00", "fatura_no": "FAT-2026-045", "urun": "DEFNE YAPRAĞI", "kategori": "BAHARAT", "birim": "Kg", "miktar": 8.0, "kalan": max(0.0, 8.0 - 0.01), "fiyat": 519.80, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-046", "tarih": "2026-10-28 09:10", "fatura_no": "FAT-2026-046", "urun": "REYHAN", "kategori": "BAHARAT", "birim": "Kg", "miktar": 5.0, "kalan": 5.0, "fiyat": 1485.15, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-047", "tarih": "2026-10-28 09:20", "fatura_no": "FAT-2026-047", "urun": "TOZ ŞEKER", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": max(0.0, 100.0 - 10.0), "fiyat": 260.25, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-048", "tarih": "2026-10-28 09:30", "fatura_no": "FAT-2026-048", "urun": "YUMURTA 15 Lİ", "kategori": "KURU GIDA", "birim": "Adet", "miktar": 180.0, "kalan": max(0.0, 180.0 - 20.0), "fiyat": 11.16, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-049", "tarih": "2026-10-28 09:40", "fatura_no": "FAT-2026-049", "urun": "KAYISI", "kategori": "MEYVE", "birim": "Kg", "miktar": 30.0, "kalan": 30.0, "fiyat": 960.39, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-050", "tarih": "2026-10-28 09:50", "fatura_no": "FAT-2026-050", "urun": "SEBZELİ TOZ BULYON", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 196.04, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-051", "tarih": "2026-10-28 10:00", "fatura_no": "FAT-2026-051", "urun": "AŞURELİK BUĞDAY", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": max(0.0, 100.0 - 4.0), "fiyat": 34.50, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-052", "tarih": "2026-10-28 10:10", "fatura_no": "FAT-2026-052", "urun": "ÇİĞ KÖFTELİK BULGUR", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 24.0, "kalan": max(0.0, 24.0 - 1.0), "fiyat": 43.50, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-053", "tarih": "2026-10-28 10:20", "fatura_no": "FAT-2026-053", "urun": "ERİŞTE MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 25.0, "kalan": max(0.0, 25.0 - 2.0), "fiyat": 43.98, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-054", "tarih": "2026-10-28 10:30", "fatura_no": "FAT-2026-054", "urun": "GALETA UNU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 9.0, "kalan": max(0.0, 9.0 - 1.0), "fiyat": 92.88, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-055", "tarih": "2026-10-28 10:40", "fatura_no": "FAT-2026-055", "urun": "HİNDİSTAN CEVİZİ (YAĞSIZ)", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 8.0, "kalan": 8.0, "fiyat": 279.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-056", "tarih": "2026-10-28 10:50", "fatura_no": "FAT-2026-056", "urun": "KIRMIZI TATLI PUL BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 40.0, "kalan": max(0.0, 40.0 - 0.01), "fiyat": 46.44, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-057", "tarih": "2026-10-28 11:00", "fatura_no": "FAT-2026-057", "urun": "KİMYON TOZ", "kategori": "BAHARAT", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 299.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-058", "tarih": "2026-10-28 11:10", "fatura_no": "FAT-2026-058", "urun": "YEŞİL MERCİMEK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 108.0, "kalan": max(0.0, 108.0 - 2.0), "fiyat": 80.50, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-059", "tarih": "2026-10-28 11:20", "fatura_no": "FAT-2026-059", "urun": "ZERDEÇAL", "kategori": "BAHARAT", "birim": "Kg", "miktar": 3.0, "kalan": 3.0, "fiyat": 349.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-060", "tarih": "2026-10-28 11:30", "fatura_no": "FAT-2026-060", "urun": "TAVUK SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 980.20, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-061", "tarih": "2026-10-28 11:40", "fatura_no": "FAT-2026-061", "urun": "SARIMSAK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 4.0, "kalan": 4.0, "fiyat": 270.00, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-062", "tarih": "2026-10-28 11:50", "fatura_no": "FAT-2026-062", "urun": "KEKİK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 1039.60, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-063", "tarih": "2026-10-28 12:00", "fatura_no": "FAT-2026-063", "urun": "ET SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 980.20, "depo": "Kuru Gıda Deposu", "islem_yapan": "admin"},
    {"id": "STK-064", "tarih": "2026-10-28 12:10", "fatura_no": "FAT-2026-064", "urun": "KAPYA BİBER", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 137.00, "depo": "Soğuk Hava Deposu +5/+6", "islem_yapan": "admin"}
]

# Varsayılan Personel Listesi (İstediğin Tarihlerle Güncellendi)
varsayilan_personeller = [
    {"id": "PER-001", "ad_soyad": "MUHAMMED İLKER ÇELİK", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"id": "PER-002", "ad_soyad": "EMİRHAN DÖNMEZ", "gorev": "Şoför", "baslama": "2026-10-12", "aktif": True, "izinler": []},
    {"id": "PER-003", "ad_soyad": "SEDAT UZUN", "gorev": "Aşçı", "baslama": "2026-09-25", "aktif": True, "izinler": []},
    {"id": "PER-004", "ad_soyad": "BURAK AYAŞTI", "gorev": "Temizlik Personeli", "baslama": "2026-09-25", "aktif": True, "izinler": []},
    {"id": "PER-005", "ad_soyad": "HÜSEYİN KAYMAK", "gorev": "Aşçı Yardımcısı", "baslama": "2026-10-26", "aktif": True, "izinler": []}
]

# Varsayılan 2026 Resmi Tatiller
varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {"tarih": "2026-03-20", "aciklama": "Ramazan Bayramı Arifesi"},
    {"tarih": "2026-03-21", "aciklama": "Ramazan Bayramı 1. Gün"},
    {"tarih": "2026-03-22", "aciklama": "Ramazan Bayramı 2. Gün"},
    {"tarih": "2026-03-23", "aciklama": "Ramazan Bayramı 3. Gün"},
    {"tarih": "2026-04-23", "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı"},
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {"tarih": "2026-05-19", "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı"},
    {"tarih": "2026-05-27", "aciklama": "Kurban Bayramı Arifesi"},
    {"tarih": "2026-05-28", "aciklama": "Kurban Bayramı 1. Gün"},
    {"tarih": "2026-05-29", "aciklama": "Kurban Bayramı 2. Gün"},
    {"tarih": "2026-05-30", "aciklama": "Kurban Bayramı 3. Gün"},
    {"tarih": "2026-05-31", "aciklama": "Kurban Bayramı 4. Gün"},
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"}
]

ekim_tuketimleri_verileri = [
    ("KIRMIZI LAHANA", 15.0), ("MAYDANOZ", 3.1), ("ELMA", 41.0), ("ERİK", 50.0), 
    ("ŞEFTALİ", 50.0), ("SOĞAN", 29.0), ("PATATES", 72.0), ("KABAK", 35.0), 
    ("HAVUÇ", 15.0), ("ISPANAK", 22.0), ("PATLICAN", 5.0), ("ÇARLİ", 19.0), 
    ("DOMATES", 52.0), ("SALATALIK", 13.0), ("BALDO PİRİNÇ", 62.0), ("KURU FASULYE", 30.0), 
    ("NOHUT", 16.0), ("ARPA ŞEHRİYE", 6.0), ("BURGU MAKARNA", 30.0), ("İNCE UZUN MAKARNA", 27.0), 
    ("KIRMIZI MERCİMEK", 11.0), ("PİLAVLIK BULGUR", 65.0), ("TEL ŞEHRİYE", 4.0), ("TUZ", 2.65), 
    ("TEREYAĞI", 29.4), ("TENEKE AYÇİÇEK YAĞI", 15.0), ("İRMİK", 10.0), ("TOZ KARABİBER", 0.32), 
    ("KIRMIZI TATLI TOZ BİBER", 0.54), ("KURU NANE", 0.25), ("UN", 6.0), ("DOMATES SALÇASI", 42.5), 
    ("BEZELYE KONSERVESİ", 42.5), ("TAM YAĞLI YOĞURT", 215.0), ("KUŞBAŞI ET", 85.0), 
    ("SIRTSIZ GÖĞÜS", 35.0), ("DEFNE YAPRAĞI", 0.01), ("TOZ ŞEKER", 10.0), ("YUMURTA 15 Lİ", 20.0), 
    ("AŞURELİK BUĞDAY", 4.0), ("ÇİĞ KÖFTELİK BULGUR", 1.0), ("ERİŞTE MAKARNA", 2.0), 
    ("GALETA UNU", 1.0), ("KIRMIZI TATLI PUL BİBER", 0.01), ("YEŞİL MERCİMEK", 2.0)
]

ekim_fire_verileri = [
    ("MUZ", 54.50), ("ISPANAK", 60.00), ("PATLICAN", 52.40), ("SALATALIK", 43.00), ("TAM YAĞLI YOĞURT", 15.00)
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
    tum_loglar = []
    for urun_adi, miktar in ekim_tuketimleri_verileri:
        bulunan_fiyat = 50.0
        for g in varsayilan_girisler:
            if g["urun"] == urun_adi:
                bulunan_fiyat = g["fiyat"]
                break
        tum_loglar.append({"tarih": "2026-10-31 12:00", "urun": urun_adi, "tur": "Yemek Üretimi", "miktar": miktar, "tutar": miktar * bulunan_fiyat, "islem_yapan": "admin"})

    for urun_adi, miktar in ekim_fire_verileri:
        bulunan_fiyat = 50.0
        for g in varsayilan_girisler:
            if g["urun"] == urun_adi:
                bulunan_fiyat = g["fiyat"]
                break
        tum_loglar.append({"tarih": "2026-10-31 12:30", "urun": urun_adi, "tur": "Fire/Zayiat", "miktar": miktar, "tutar": miktar * bulunan_fiyat, "islem_yapan": "admin"})
    
    if os.path.exists(KULLANIM_LOG_DOSYASI):
        try:
            with open(KULLANIM_LOG_DOSYASI, "r", encoding="utf-8") as f:
                kayitli_loglar = json.load(f)
                if kayitli_loglar:
                    return kayitli_loglar
        except Exception:
            pass
    return tum_loglar

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
                data = json.load(f)
                for p in data:
                    ad = p.get("ad_soyad", "")
                    if "baslama" not in p or not p["baslama"] or p["baslama"] == "-":
                        if "MUHAMMED İLKER ÇELİK" in ad or "EMİRHAN DÖNMEZ" in ad:
                            p["baslama"] = "2026-10-12"
                        elif "SEDAT UZUN" in ad or "BURAK AYAŞTI" in ad:
                            p["baslama"] = "2026-09-25"
                        elif "HÜSEYİN KAYMAK" in ad:
                            p["baslama"] = "2026-10-26"
                        else:
                            p["baslama"] = str(datetime.date.today())
                return data
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

def resmi_tatilleri_kaydet(veri):
    with open(TATIL_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

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

# --- OTURUM KALICILIĞI ---
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
        return 0, 0, 0, 0, 0
    
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
        else: # Yıllık İzin
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

# --- SOL MENÜ & TEMA SEÇİCİ ---
st.sidebar.markdown('<p style="font-size: 14px; font-weight: 600; margin-bottom: 8px; padding-left: 5px;">Arayüz Teması</p>', unsafe_allow_html=True)
yeni_tema = st.sidebar.selectbox("Tema Seçin", ["Koyu Tema (Dark)", "Açık Tema (Light)"], index=0 if st.session_state.tema_secimi=="Koyu Tema (Dark)" else 1, label_visibility="collapsed")
if yeni_tema != st.session_state.tema_secimi:
    st.session_state.tema_secimi = yeni_tema
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown('<p style="font-size: 14px; font-weight: 600; margin-bottom: 8px; padding-left: 5px;">Ana Menü</p>', unsafe_allow_html=True)

yonetici_modu = (st.session_state.oturum_aktif and st.session_state.aktif_kullanici == "admin")
asci_modu = (st.session_state.oturum_aktif and st.session_state.aktif_kullanici == "asci")
misafir_modu = (not st.session_state.oturum_aktif or st.session_state.aktif_kullanici == "misafir")

menuler_listesi = [
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu", 
]

if not misafir_modu:
    menuler_listesi.append("Yeni Mal Alımı / Fatura Ekle")

menuler_listesi.extend([
    "Ürün Sil / Düzenle", 
    "Fire / Zayiat Girişi", 
    "Günlük Yemek Üretimi & Maliyet Raporu",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
    "Ürün Birim Fiyatları & Ay Analizi"
])

for m in menuler_listesi:
    btn_type = "primary" if st.session_state.aktif_menu == m else "secondary"
    if st.sidebar.button(m, use_container_width=True, type=btn_type):
        st.session_state.aktif_menu = m
        st.rerun()

menu = st.session_state.aktif_menu

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 KULLANICI & YÖNETİCİ GİRİŞİ")
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
    col_kilit1, col_kilit2 = st.sidebar.columns([2, 2])
    with col_kilit1:
        if st.session_state.aktif_kullanici == "admin":
            rol_adi = "👑 Admin"
        elif st.session_state.aktif_kullanici == "asci":
            rol_adi = "👨‍🍳 Aşçı"
        else:
            rol_adi = "👀 Misafir"
        st.sidebar.markdown(f'<p style="color: #059669; font-size: 13px; margin: 0; padding-top: 5px; font-weight: 600;">🔓 {rol_adi}</p>', unsafe_allow_html=True)
    with col_kilit2:
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
st.sidebar.markdown('<p style="font-size: 11px; text-align: center; margin-top: 10px;">sefautopcu</p>', unsafe_allow_html=True)


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


# 0. KURUMSAL DASHBOARD & ÖZET (Kare Kart Tasarımı)
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
                    <div style="background: rgba(56, 189, 248, 0.15); padding: 12px; border-radius: 12px; color: #38BDF8; font-size: 20px;">
                        📦
                    </div>
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
                    <div style="background: rgba(239, 68, 68, 0.15); padding: 12px; border-radius: 12px; color: #EF4444; font-size: 20px;">
                        📉
                    </div>
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
                    <div style="background: rgba(52, 211, 153, 0.15); padding: 12px; border-radius: 12px; color: #34D399; font-size: 20px;">
                        💰
                    </div>
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
                    <div style="background: rgba(167, 139, 250, 0.15); padding: 12px; border-radius: 12px; color: #A78BFA; font-size: 20px;">
                        👥
                    </div>
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
        
        excel_liste.append({"Ürün Adı": u, "Kategori": kategori_ex, "Birim": birim_ex, "Kalan Miktar": toplam_kalan_ex, "Depo Yeri": depo_ex, "Son İşlemi Yapan": islem_yapan_ex})

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
        
        if secilen_depo == "Tümü" or depo == secilen_depo:
            stok_tablosu.append({"Ürün Adı": u, "Kategori": kategori, "Birim": birim, "Kalan Miktar": toplam_kalan, "Depo Yeri": depo, "İşlemi Yapan": islem_yapan})
            
        if toplam_kalan <= 10.0:
            kritik_urunler.append((u, toplam_kalan, birim, depo))

    if kritik_urunler:
        with st.expander("⚠️ DİKKAT: Kritik Seviyedeki Veya Tükenen Ürünler!", expanded=False):
            for ku, km, kb, kd in kritik_urunler:
                st.warning(f"**{ku}** stoğu azalmıştır! Kalan Miktar: **{km} {kb}** ({kd})")

    st.markdown("### Envanter Listesi")
    for row in stok_tablosu:
        st.write(f"• **{row['Ürün Adı']}** | Kategori: {row['Kategori']} | Kalan: **{row['Kalan Miktar']} {row['Birim']}** | Depo: {row['Depo Yeri']} | *(Ekleyen: {row['İşlemi Yapan']})*")


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
                st.success(f"Başarılı! {miktar} miktar {urun} depoya işlendi. (Fatura No: {fatura_no_degeri} - İşlemi Yapan: {islem_yapan_kisi})")
                st.rerun()

        st.markdown("---")
        st.subheader("📋 Mal Alımı / Fatura Log Kayıtları Arşivi")
        if st.session_state.girisler:
            fatura_log_tablosu = []
            for g in reversed(st.session_state.girisler):
                fatura_log_tablosu.append({
                    "Kayıt ID": g.get("id", "-"),
                    "Tarih / Saat": g.get("tarih", "-"),
                    "Fatura No": g.get("fatura_no", "BELİRTİLMEMİŞ"),
                    "Ürün Adı": g.get("urun", "-"),
                    "Kategori": g.get("kategori", "-"),
                    "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                    "Birim Fiyat": f"{g.get('fiyat', 0):,.2f} ₺",
                    "Toplam Tutar": f"{(g.get('miktar', 0) * g.get('fiyat', 0)):,.2f} ₺",
                    "Depo Yeri": g.get("depo", "-"),
                    "İşlemi Yapan": g.get("islem_yapan", "admin")
                })
            st.dataframe(fatura_log_tablosu, use_container_width=True)
        else:
            st.info("Kayıtlı mal alımı faturası bulunmuyor.")


# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
    
    if misafir_modu:
        st.warning("👀 Misafir modundasınız. Bu ekranda yalnızca gözlem yapabilirsiniz, silme işlemi gerçekleştiremezsiniz.")
    elif not yonetici_modu:
        st.warning("⚠️ Bu ekrana erişmek ve ürün silmek için **Admin (Sefa Bey)** hesabıyla giriş yapmanız gereklidir.")
    else:
        if st.session_state.silme_mesaji:
            st.success(st.session_state.silme_mesaji)
            st.session_state.silme_mesaji = ""

        st.markdown("Depoda kayıtlı olan tüm ürünleri ve fatura girişlerini aşağıda görebilir, silmek istediğiniz kaydı seçerek sistemden kalıcı olarak kaldırabilirsiniz.")
        
        if not st.session_state.girisler:
            st.info("Sistemde silinecek kayıt bulunmuyor.")
        else:
            with st.form("urun_silme_formu"):
                secenekler = [f"{g['id']} - {g['urun']} (Fatura: {g.get('fatura_no', '-')}, Kalan: {g['kalan']} {g['birim']}, Ekleyen: {g.get('islem_yapan', 'admin')})" for g in st.session_state.girisler]
                secilen_kayit_str = st.selectbox("Silmek İstediğiniz Kaydı / Faturayı Seçin", secenekler)
                silme_nedeni_input = st.text_input("Silme Nedeni / Gerekçesi", "Örn: Yanlış giriş / Mükerrer kayıt")
                sil_onay_btn = st.form_submit_button("Seçilen Ürünü / Kaydı Kalıcı Olarak Sil", type="primary")

                if sil_onay_btn:
                    secilen_id = secilen_kayit_str.split(" - ")[0]
                    ilgili_oge = next((g for g in st.session_state.girisler if g["id"] == secilen_id), None)
                    if ilgili_oge:
                        silinen_urun_adi = ilgili_oge['urun']
                        islem_tarihi_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        islem_yapan_kisi = st.session_state.aktif_kullanici

                        st.session_state.silinen_urun_loglari.append({
                            "tarih": islem_tarihi_str,
                            "urun": silinen_urun_adi,
                            "kayit_id": ilgili_oge['id'],
                            "fatura_no": ilgili_oge.get('fatura_no', '-'),
                            "detay": f"Miktar: {ilgili_oge['miktar']} {ilgili_oge['birim']}, Fiyat: {ilgili_oge['fiyat']} ₺",
                            "neden": silme_nedeni_input if silme_nedeni_input else "Belirtilmedi",
                            "islem_yapan": islem_yapan_kisi
                        })
                        silinen_urun_loglarini_kaydet(st.session_state.silinen_urun_loglari)

                        st.session_state.girisler = [g for g in st.session_state.girisler if g["id"] != secilen_id]
                        verileri_kaydet(st.session_state.girisler)
                        
                        st.session_state.silme_mesaji = f"Başarılı! {silinen_urun_adi} sistemden silindi ve arşive kaydedildi."
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Silinen Ürünler ve İşlem Geçmişi Arşivi")
    silinen_loglar = st.session_state.silinen_urun_loglari
    if silinen_loglar:
        silinen_tablo_verisi = [{
            "Silinme Tarihi": sl["tarih"],
            "Kayıt ID": sl.get("kayit_id", "-"),
            "Fatura No": sl.get("fatura_no", "-"),
            "Ürün Adı": sl["urun"],
            "Detaylar": sl.get("detay", "-"),
            "Silme Nedeni": sl["neden"],
            "İşlemi Yapan": sl.get("islem_yapan", "admin")
        } for sl in silinen_loglar]
        st.dataframe(silinen_tablo_verisi, use_container_width=True)
    else:
        st.info("Sistemden henüz silinmiş bir ürün kaydı bulunmuyor.")


# 4. FİRE / ZAYİAT GİRİŞİ VE İZLEME EKRANI
elif menu == "Fire / Zayiat Girişi":
    st.header("🗑️ Fire / Zayiat Bildirimi ve Durum İzleme")
    
    if misafir_modu:
        st.warning("👀 Misafir modundasınız. Bu ekranda yalnızca kayıtlı fireleri gözlemleyebilirsiniz, yeni fire düşemezsiniz.")
    else:
        with st.form("fire_formu"):
            st.subheader("Yeni Fire Girişi Yap")
            benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
            secenek_listesi_fire = ["Tüm Ürünler"] + benzersiz_urunler
            secilen_urun = st.selectbox("Fire Düşülecek Ürünü Seçin", secenek_listesi_fire)
            
            if secilen_urun == "Tüm Ürünler":
                secilen_gercek_urun = st.selectbox("İşlem Yapılacak Spesifik Ürünü Seçin", benzersiz_urunler)
            else:
                secilen_gercek_urun = secilen_urun
                
            ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == secilen_gercek_urun and g["kalan"] > 0]
            toplam_stok = sum(g["kalan"] for g in ilgili_girisler)
            
            st.info(f"Seçilen Ürün ({secilen_gercek_urun}) Mevcut Stoğu: {toplam_stok}")
            fire_miktari = st.number_input("Fire Miktarı", min_value=0.0, max_value=float(toplam_stok) if toplam_stok>0 else 1.0, step=0.1)
            aciklama = st.text_input("Fire Nedeni (Örn: Çürüme / S.T.T)")
            
            submitted_fire = st.form_submit_button("Fireyi Düş ve Kaydet")
            if submitted_fire:
                if fire_miktari > 0:
                    kalan_dusulecek = fire_miktari
                    toplam_zarar = 0.0
                    bugun_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    islem_yapan_kisi = st.session_state.aktif_kullanici
                    
                    for g in ilgili_girisler:
                        if kalan_dusulecek <= 0:
                            break
                        if g["kalan"] >= kalan_dusulecek:
                            dusulen = kalan_dusulecek
                            g["kalan"] -= dusulen
                            toplam_zarar += dusulen * g["fiyat"]
                            kalan_dusulecek = 0
                        else:
                            dusulen = g["kalan"]
                            g["kalan"] = 0
                            toplam_zarar += dusulen * g["fiyat"]
                            kalan_dusulecek -= dusulen
                            
                    verileri_kaydet(st.session_state.girisler)
                    st.session_state.kullanim_loglari.append({
                        "tarih": bugun_str, 
                        "urun": secilen_gercek_urun, 
                        "tur": "Fire/Zayiat", 
                        "miktar": fire_miktari, 
                        "tutar": toplam_zarar, 
                        "islem_yapan": islem_yapan_kisi
                    })
                    loglari_kaydet(st.session_state.kullanim_loglari)
                    st.success(f"Fire başarıyla düşüldü. Toplam Maddi Zarar: {toplam_zarar:.2f} TL (İşlemi Yapan: {islem_yapan_kisi} - {bugun_str})")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Sistemde Kayıtlı Olan Tüm Fire ve Zayiat Durumları")
    fire_loglari = [l for l in st.session_state.kullanim_loglari if l["tur"] == "Fire/Zayiat"]
    if fire_loglari:
        fire_tablo_verisi = [{
            "Tarih / Saat": fl["tarih"], 
            "Ürün Adı": fl["urun"], 
            "Fire Miktarı (Kg)": f"{fl['miktar']:.2f} Kg", 
            "Maddi Zarar (₺)": f"{fl['tutar']:.2f} ₺",
            "İşlemi Yapan": fl.get("islem_yapan", "admin")
        } for fl in fire_loglari]
        st.dataframe(fire_tablo_verisi, use_container_width=True)
    else:
        st.info("Sistemde kayıtlı henüz bir fire veya zayiat bulunmuyor.")


# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi ve Maliyet Hesaplama")
    
    yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
    kisi_sayisi = st.number_input("Yararlanan Kişi Sayısı", min_value=1, value=200)
    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    
    if "sepet" not in st.session_state:
        st.session_state.sepet = []
        
    if misafir_modu:
        st.info("👀 Misafir modundasınız. Bu ekranda yalnızca maliyet hesaplamalarını ve sepeti gözlemleyebilirsiniz, üretim yapamazsınız.")
    else:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            secilen_urun = st.selectbox("Malzeme Seç", benzersiz_urunler, key="yemek_urun")
        with col2:
            ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == secilen_urun and g["kalan"] > 0]
            stok_max = sum(g["kalan"] for g in ilgili_girisler)
            kullanilacak_miktar = st.number_input(f"Miktar (Stok: {stok_max})", min_value=0.0, max_value=float(stok_max) if stok_max>0 else 0.1, step=0.1, key="yemek_miktar")
        with col3:
            if st.button("Sepete Ekle"):
                if kullanilacak_miktar > 0 and kullanilacak_miktar <= stok_max:
                    st.session_state.sepet.append({"urun": secilen_urun, "miktar": kullanilacak_miktar, "girisler": ilgili_girisler})
                    st.success("Eklendi!")
                
    if st.session_state.sepet:
        st.subheader("Seçilen Malzemeler")
        toplam_maliyet = 0.0
        islenmis_sepet = []
        excel_sepet_liste = []

        for item in st.session_state.sepet:
            urun = item["urun"]
            istenen = item["miktar"]
            ilgili = [g for g in st.session_state.girisler if g["urun"] == urun and g["kalan"] > 0]
            kalan_d = istenen
            maliyet = 0.0
            ilk_fiyat = ilgili[0]["fiyat"] if ilgili else 0.0
            depo = ilgili[0]["depo"] if ilgili else ""
            kategori = ilgili[0]["kategori"] if ilgili else ""
            birim = ilgili[0]["birim"] if ilgili else "Kg"
            
            for g in ilgili:
                if kalan_d <= 0: break
                if g["kalan"] >= kalan_d:
                    maliyet += kalan_d * g["fiyat"]
                    kalan_d = 0
                else:
                    maliyet += g["kalan"] * g["fiyat"]
                    kalan_d -= g["kalan"]
                    
            toplam_maliyet += maliyet
            islenmis_sepet.append({"Malzeme": urun, "Kategori": kategori, "Birim": birim, "Miktar": istenen, "Birim Maliyet": ilk_fiyat, "Toplam Maliyet": maliyet, "Depo": depo})
            excel_sepet_liste.append({"Malzeme": urun, "Kategori": kategori, "Birim": birim, "Miktar": istenen, "Birim Maliyet (TL)": round(ilk_fiyat, 2), "Toplam Maliyet (TL)": round(maliyet, 2)})

        pdf_data = tablo_to_html_pdf_bytes(f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste)
        excel_sepet_data = tablo_to_excel_bytes(excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}")

        with col_indir_alan:
            ortak_indirme_alani(excel_sepet_data, pdf_data, "yemek_maliyet_raporu", "yemek_sayfasi")
            
        for row in islenmis_sepet:
            st.write(f"• **{row['Malzeme']}** - {row['Miktar']} {row['Birim']} | Birim Fiyat: {row['Birim Maliyet']:.2f} ₺ | Toplam: **{row['Toplam Maliyet']:.2f} ₺**")
        
        kisi_basi = toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0
        st.metric("Toplam Yemek Maliyeti", f"{toplam_maliyet:.2f} TL")
        st.metric("Kişi Başı Maliyet", f"{kisi_basi:.2f} TL")
        
        if not misafir_modu and st.button("Üretimi Tamamla ve Stoktan Düş"):
            bugun_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            islem_yapan_kisi = st.session_state.aktif_kullanici
            for item in st.session_state.sepet:
                urun = item["urun"]
                istenen = item["miktar"]
                ilgili = [g for g in st.session_state.girisler if g["urun"] == urun and g["kalan"] > 0]
                kalan_d = istenen
                urun_maliyeti = 0.0
                for g in ilgili:
                    if kalan_d <= 0: break
                    if g["kalan"] >= kalan_d:
                        g["kalan"] -= kalan_d
                        urun_maliyeti += kalan_d * g["fiyat"]
                        kalan_d = 0
                    else:
                        harcanan = g["kalan"]
                        g["kalan"] = 0
                        urun_maliyeti += harcanan * g["fiyat"]
                        kalan_d -= harcanan
                
                st.session_state.kullanim_loglari.append({
                    "tarih": bugun_str, 
                    "urun": urun, 
                    "tur": "Yemek Üretimi", 
                    "miktar": istenen, 
                    "tutar": urun_maliyeti, 
                    "islem_yapan": islem_yapan_kisi
                })
            
            verileri_kaydet(st.session_state.girisler)
            loglari_kaydet(st.session_state.kullanim_loglari)
            st.success(f"Üretim kaydedildi ve stoktan düşüldü! (İşlemi Yapan: {islem_yapan_kisi})")
            st.session_state.sepet = []
    else:
        empty_excel = tablo_to_excel_bytes([], "Boş Rapor")
        empty_pdf = tablo_to_html_pdf_bytes("Boş Rapor", [])
        with col_indir_alan:
            ortak_indirme_alani(empty_excel, empty_pdf, "bos_yemek_raporu", "yemek_bos_sayfasi")


# 6. MÜSTAKİL KALORİ HESAPLAMA ARACI
elif menu == "Kalori Hesaplama Aracı":
    col_b_kal, col_indir_kal = st.columns([2, 2])
    with col_b_kal:
        st.header("🔥 Bağımsız Kalori ve Besin Değeri Hesaplama Aracı")
    
    st.markdown("Bu ekranda herhangi bir yemek tarifi için **birden fazla malzeme seçebilir**, gramajlarını girerek toplam kaloriyi ve **1 porsiyon ortalama kaloriyi** hesaplayabilirsiniz.")

    col_tarif_adi, col_kisi_giris = st.columns(2)
    with col_tarif_adi:
        kalori_tarif_adi = st.text_input("Tarif / Yemek Adı", "Örn: Etli Kuru Fasulye ve Pilav Menüsü")
    with col_kisi_giris:
        kalori_kisi_sayisi = st.number_input("Planlanan Kişi / Porsiyon Sayısı", min_value=1, value=100)

    benzersiz_urunler_kalori = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    
    col_k_sec1, col_k_sec2, col_k_sec3 = st.columns([2, 1, 1])
    with col_k_sec1:
        secilen_kalori_urun = st.selectbox("Malzeme Seçin", benzersiz_urunler_kalori, key="kalori_urun_sec")
    with col_k_sec2:
        kalori_miktar_input = st.number_input("Miktar", min_value=0.1, value=1.0, step=0.5, key="kalori_miktar_input")
    with col_k_sec3:
        kalori_birim_input = st.selectbox("Birim", ["Kg", "Adet", "Lt"], key="kalori_birim_input")

    col_btn_ekle, col_btn_sifirla = st.columns([1, 1])
    with col_btn_ekle:
        if st.button("➕ Listeye Malzeme Ekle", use_container_width=True):
            st.session_state.kalori_sepeti.append({
                "urun": secilen_kalori_urun,
                "miktar": kalori_miktar_input,
                "birim": kalori_birim_input
            })
            st.success(f"{secilen_kalori_urun} listeye eklendi!")

    with col_btn_sifirla:
        if st.button("🔄 Hesaplamayı Sıfırla", use_container_width=True, type="secondary"):
            st.session_state.kalori_sepeti = []
            st.success("Liste başarıyla sıfırlandı!")
            st.rerun()

    st.markdown("---")
    if st.session_state.kalori_sepeti:
        st.subheader(f"📋 '{kalori_tarif_adi}' İçin Seçilen Malzemeler")
        
        toplam_tarif_kalorisi = 0.0
        kalori_tablo_verisi = []
        excel_kalori_liste = []

        for item in st.session_state.kalori_sepeti:
            u_adi = item["urun"]
            u_mik = item["miktar"]
            u_birim = item["birim"]
            
            malzeme_kalori = urun_kalori_hesapla(u_adi, u_mik, u_birim)
            toplam_tarif_kalorisi += malzeme_kalori

            kalori_tablo_verisi.append({
                "Malzeme": u_adi,
                "Miktar": f"{u_mik} {u_birim}",
                "Tahmini Kalori": f"{malzeme_kalori:,.0f} kcal"
            })
            excel_kalori_liste.append({
                "Malzeme": u_adi,
                "Miktar": f"{u_mik} {u_birim}",
                "Tahmini Kalori (kcal)": round(malzeme_kalori, 1)
            })

        pdf_kalori_data = tablo_to_html_pdf_bytes(f"Kalori Hesaplama Raporu - {kalori_tarif_adi}", excel_kalori_liste)
        excel_kalori_data = tablo_to_excel_bytes(excel_kalori_liste, f"Kalori Hesaplama Raporu - {kalori_tarif_adi}")

        with col_indir_kal:
            ortak_indirme_alani(excel_kalori_data, pdf_kalori_data, "kalori_hesaplama_raporu", "kalori_sayfasi")

        st.dataframe(kalori_tablo_verisi, use_container_width=True)

        kisi_basi_kalori_sonuc = toplam_tarif_kalorisi / kalori_kisi_sayisi if kalori_kisi_sayisi > 0 else 0

        km1, km2 = st.columns(2)
        with km1:
            st.metric("Toplam Tarif Kalorisi", f"{toplam_tarif_kalorisi:,.0f} kcal")
        with km2:
            st.metric("1 Porsiyon Kalori (Ortalama)", f"{kisi_basi_kalori_sonuc:,.0f} kcal")
    else:
        empty_excel_k = tablo_to_excel_bytes([], "Boş Rapor")
        empty_pdf_k = tablo_to_html_pdf_bytes("Boş Rapor", [])
        with col_indir_kal:
            ortak_indirme_alani(empty_excel_k, empty_pdf_k, "bos_kalori_raporu", "kalori_bos_sayfasi")
        st.info("Henüz hesaplama için malzeme eklenmedi. Yukarıdan malzeme seçip ekleyebilirsiniz.")


# 7. İHTİYAÇ SAHİBİ & YEMEK DAĞITIM TAKİBİ
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    st.header("👥 İhtiyaç Sahibi ve Günlük / Aylık / Yıllık Yemek Dağıtım Takibi")
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
                        st.success(f"Başarılı! {yeni_ad} sisteme kaydedildi. (İşlemi Yapan: {islem_yapan_kisi})")
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
            st.dataframe(kisi_liste_gosterim, use_container_width=True)
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
                    islem_yapan_kisi = st.session_state.aktif_kullanici
                    st.session_state.dagitim_loglari.append({
                        "tarih": d_tarih_saat,
                        "kisi": secilen_kisi,
                        "menu": menu_adi,
                        "porsiyon": porsiyon_mik,
                        "islem_yapan": islem_yapan_kisi
                    })
                    dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                    st.success(f"Başarılı! {secilen_kisi} adlı kişiye yapılan yemek dağıtımı kaydedildi. (İşlemi Yapan: {islem_yapan_kisi} - {d_tarih_saat})")
                    st.rerun()

    with tab3:
        col_b_d, col_indir_alan = st.columns([2, 2])
        with col_b_d:
            st.subheader("📊 Kim Ne Kadar Süredir Yemek Almış?")

        kisi_secenekleri_rapor = ["Tüm İhtiyaç Sahipleri (Genel Rapor)"] + [k["ad_soyad"] for k in st.session_state.ihtiyac_sahipleri]
        secilen_rapor_kisi = st.selectbox("Raporlanacak Kişiyi Seçin", kisi_secenekleri_rapor, key="rapor_kisi_sec")
        
        dagitimlar = st.session_state.dagitim_loglari
        if secilen_rapor_kisi != "Tüm İhtiyaç Sahipleri (Genel Rapor)":
            dagitimlar = [d for d in dagitimlar if d["kisi"] == secilen_rapor_kisi]

        zaman_kriteri = st.radio("Zaman Periyodu Seçin", ["Tüm Zamanlar", "Günlük", "Aylık", "Yıllık"], horizontal=True, key="rapor_zaman_kriteri")

        simdi_gun_str = str(datetime.date.today())
        if zaman_kriteri == "Günlük":
            dagitimlar = [d for d in dagitimlar if d["tarih"].startswith(simdi_gun_str)]
        elif zaman_kriteri == "Aylık":
            ay_kodu = simdi_gun_str[:7]
            dagitimlar = [d for d in dagitimlar if d["tarih"].startswith(ay_kodu)]
        elif zaman_kriteri == "Yıllık":
            yil_kodu = simdi_gun_str[:4]
            dagitimlar = [d for d in dagitimlar if d["tarih"].startswith(yil_kodu)]

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
        if misafir_modu:
            st.info("👀 Misafir modundasınız. Bu ekranda yalnızca personel listesini görüntüleyebilirsiniz.")
        else:
            col_p_ekle, col_p_durum = st.columns(2)
            with col_p_ekle:
                with st.form("personel_ekle_form"):
                    st.markdown("**➕ Yeni Personel Ekle**")
                    p_ad = st.text_input("Personel Adı Soyadı").strip().upper()
                    p_gorev = st.text_input("Görevi (Örn: Aşçı / Depo Sorumlusu)")
                    p_bas = st.date_input("İşe Başlama Tarihi", value=datetime.date.today())
                    p_submit = st.form_submit_button("Personeli Kaydet")
                    
                    if p_submit and p_ad:
                        st.session_state.personeller.append({
                            "id": f"PRS-{len(st.session_state.personeller)+1:03d}",
                            "ad_soyad": p_ad,
                            "gorev": p_gorev if p_gorev else "Personel",
                            "baslama": str(p_bas),
                            "aktif": True,
                            "izinler": []
                        })
                        personelleri_kaydet(st.session_state.personeller)
                        st.success(f"Başarılı! {p_ad} kadroya eklendi.")
                        st.rerun()

            with col_p_durum:
                with st.form("personel_durum_form"):
                    st.markdown("**🔄 Personel Durum Güncelle (Aktif/Pasif)**")
                    if st.session_state.personeller:
                        p_secenekler = [f"{p['id']} - {p['ad_soyad']} ({'Aktif' if p.get('aktif', True) else 'Ayrıldı'})" for p in st.session_state.personeller]
                        secilen_p_str = st.selectbox("Personel Seç", p_secenekler)
                        yeni_durum = st.radio("Durum Seç", ["Aktif Çalışıyor", "İşten Ayrıldı / Pasif"], horizontal=True)
                        p_durum_btn = st.form_submit_button("Durumu Güncelle")
                        
                        if p_durum_btn:
                            p_id = secilen_p_str.split(" - ")[0]
                            for p in st.session_state.personeller:
                                if p["id"] == p_id:
                                    p["aktif"] = (yeni_durum == "Aktif Çalışıyor")
                            personelleri_kaydet(st.session_state.personeller)
                            st.success("Personel durumu güncellendi!")
                            st.rerun()
                    else:
                        st.info("Kayıtlı personel bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Personel Kadrosu ve Çalışma Süresi Sayacı")
        if st.session_state.personeller:
            bugun_tarihi = datetime.date.today()
            p_gosterim = []
            for p in st.session_state.personeller:
                bas_tarih_str = p.get("baslama", "2026-01-01")
                try:
                    bas_dt = datetime.datetime.strptime(bas_tarih_str, "%Y-%m-%d").date()
                except:
                    bas_dt = datetime.date(2026, 1, 1)
                
                # İşe giriş tarihinden bugüne kadar net çalışma günü hesabı (Hafta sonları hariç)
                net_calisilan, _, _, _ = net_calisma_gunu_hesapla(bas_dt, bugun_tarihi, p.get("izinler", []), st.session_state.resmi_tatiller)
                
                p_gosterim.append({
                    "ID": p["id"],
                    "Adı Soyadı": p["ad_soyad"],
                    "Görevi": p["gorev"],
                    "İşe Başlama": bas_tarih_str,
                    "Çalışma Günü Sayacı": f"{net_calisilan} Gün",
                    "Durum": "Aktif Çalışıyor" if p.get("aktif", True) else "Pasif / Ayrıldı",
                    "Kayıtlı İzin/Rapor": len(p.get("izinler", []))
                })
            st.dataframe(p_gosterim, use_container_width=True)
        else:
            st.info("Henüz kayıtlı personel bulunmuyor.")

    with p_tab2:
        st.subheader("🏖️ Yıllık İzin Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Yıllık izin ekleme ve silme işlemleri yalnızca **Admin (Sefa Bey)** tarafından yapılabilir.")
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
                                        p["izinler"].append({
                                            "tur": "Yıllık İzin",
                                            "baslangic": str(i_bas),
                                            "bitis": str(i_bit)
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
                                    "ozet": f"{p['ad_soyad']} | Başlangıç: {iz['baslangic']} - Bitiş: {iz['bitis']}"
                                })
                    
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
        st.subheader("📋 Kayıtlı Tüm Yıllık İzinler Tablosu")
        yillik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Yıllık İzin":
                    yillik_tablo_listesi.append({
                        "Personel": p["ad_soyad"],
                        "İzin Türü": "Yıllık İzin",
                        "Başlangıç Tarihi": iz.get("baslangic", "-"),
                        "Bitiş Tarihi": iz.get("bitis", "-"),
                        "Açıklama": "Standart Yıllık İzin"
                    })
        
        if yillik_tablo_listesi:
            st.dataframe(yillik_tablo_listesi, use_container_width=True)
            exc_y = tablo_to_excel_bytes(yillik_tablo_listesi, "Yıllık İzinler Raporu")
            pdf_y = tablo_to_html_pdf_bytes("Yıllık İzinler Raporu", yillik_tablo_listesi)
            ortak_indirme_alani(exc_y, pdf_y, "yillik_izinler_raporu", "yillik_izin_indzir")
        else:
            st.info("Kayıtlı yıllık izin bulunmuyor.")

    with p_tab3:
        st.subheader("⏰ Saatlik İzin Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Saatlik izin ekleme ve silme işlemleri yalnızca **Admin (Sefa Bey)** tarafından yapılabilir.")
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
                        with col_saat1:
                            s_bas_saat = st.time_input("Başlangıç Saati", value=datetime.time(9, 0))
                        with col_saat2:
                            s_bit_saat = st.time_input("Bitiş Saati", value=datetime.time(11, 0))
                        
                        s_aciklama = st.text_input("Gerekçe / Açıklama", "Örn: Özel iş / Mazeret")
                        saat_submit = st.form_submit_button("Saatlik İzni Kaydet")
                        
                        if saat_submit:
                            t1 = datetime.datetime.combine(s_tarih, s_bas_saat)
                            t2 = datetime.datetime.combine(s_tarih, s_bit_saat)
                            fark_saat = (t2 - t1).total_seconds() / 3600.0
                            
                            if fark_saat <= 0:
                                st.error("Bitiş saati başlangıç saatinizden sonra olmalıdır!")
                            else:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_p_saat:
                                        if "izinler" not in p: p["izinler"] = []
                                        p["izinler"].append({
                                            "tur": "Saatlik İzin",
                                            "baslangic": str(s_tarih),
                                            "bitis": str(s_tarih),
                                            "saat": round(fark_saat, 2),
                                            "detay": f"{s_bas_saat.strftime('%H:%M')} - {s_bit_saat.strftime('%H:%M')} ({s_aciklama})"
                                        })
                                personelleri_kaydet(st.session_state.personeller)
                                st.success(f"{round(fark_saat, 2)} saatlik izin başarıyla kaydedildi!")
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
                                    "ozet": f"{p['ad_soyad']} | Tarih: {iz['baslangic']} | {iz.get('saat')} Saat ({iz.get('detay')})"
                                })
                    
                    if tum_saatlik_izinler:
                        secenek_sil_s = [item["ozet"] for item in tum_saatlik_izinler]
                        secilen_sil_s_str = st.selectbox("Silinecek Saatlik İzni Seçin", secenek_sil_s)
                        s_sil_btn = st.form_submit_button("Seçilen Saatlik İzni Sil", type="primary")
                        
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
                                st.success("Seçilen saatlik izin silindi!")
                                st.rerun()
                    else:
                        st.info("Silinebilecek saatlik izin kaydı bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Tüm Saatlik İzinler Tablosu")
        saatlik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Saatlik İzin":
                    saatlik_tablo_listesi.append({
                        "Personel": p["ad_soyad"],
                        "İzin Türü": "Saatlik İzin",
                        "Tarih": iz.get("baslangic", "-"),
                        "Süre (Saat)": iz.get("saat", 0),
                        "Detay / Gerekçe": iz.get("detay", "-")
                    })
        
        if saatlik_tablo_listesi:
            st.dataframe(saatlik_tablo_listesi, use_container_width=True)
            exc_s = tablo_to_excel_bytes(saatlik_tablo_listesi, "Saatlik İzinler Raporu")
            pdf_s = tablo_to_html_pdf_bytes("Saatlik İzinler Raporu", saatlik_tablo_listesi)
            ortak_indirme_alani(exc_s, pdf_s, "saatlik_izinler_raporu", "saatlik_izin_indzir")
        else:
            st.info("Kayıtlı saatlik izin bulunmuyor.")

    with p_tab4:
        st.subheader("🏥 Sağlık Raporu Yönetimi (Ekle & Sil)")
        if not yonetici_modu:
            st.warning("⚠️ Sağlık raporu ekleme ve silme işlemleri yalnızca **Admin (Sefa Bey)** tarafından yapılabilir.")
        else:
            col_r_ekle, col_r_sil = st.columns(2)
            with col_r_ekle:
                with st.form("saglik_raporu_form"):
                    st.markdown("**➕ Sağlık Raporu Ekle**")
                    p_rap_secenekleri = [p["ad_soyad"] for p in st.session_state.personeller if p.get("aktif", True)]
                    if p_rap_secenekleri:
                        secilen_p_rap = st.selectbox("Personel Seçin", p_rap_secenekleri, key="rap_p")
                        
                        r_nereden = st.text_input("Raporun Alındığı Yer (Hastane / Kurum / Aile Hekimi)", "Örn: Erzurum Şehir Hastanesi")
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            r_bas = st.date_input("Rapor Başlangıç Tarihi", key="rap_bas")
                        with col_r2:
                            r_bit = st.date_input("Rapor Bitiş Tarihi", key="rap_bit")
                        
                        r_teshis = st.text_input("Teşhis / Hastalık Açıklaması", "Örn: Üst Solunum Yolu Enfeksiyonu")
                        rap_submit = st.form_submit_button("Sağlık Raporunu Kaydet")
                        
                        if rap_submit:
                            if r_bas > r_bit:
                                st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz!")
                            else:
                                for p in st.session_state.personeller:
                                    if p["ad_soyad"] == secilen_p_rap:
                                        if "izinler" not in p: p["izinler"] = []
                                        p["izinler"].append({
                                            "tur": "Sağlık Raporu",
                                            "baslangic": str(r_bas),
                                            "bitis": str(r_bit),
                                            "kurum": r_nereden,
                                            "teshis": r_teshis
                                        })
                                personelleri_kaydet(st.session_state.personeller)
                                st.success("Sağlık raporu başarıyla kaydedildi!")
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
                                    "ozet": f"{p['ad_soyad']} | Kurum: {iz.get('kurum')} | Başlangıç: {iz['baslangic']} ({iz.get('teshis')})"
                                })
                    
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
                                st.success("Seçilen sağlık raporu silindi!")
                                st.rerun()
                    else:
                        st.info("Silinebilecek sağlık raporu kaydı bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Tüm Sağlık Raporları Tablosu")
        saglik_tablo_listesi = []
        for p in st.session_state.personeller:
            for iz in p.get("izinler", []):
                if iz.get("tur") == "Sağlık Raporu":
                    saglik_tablo_listesi.append({
                        "Personel": p["ad_soyad"],
                        "İzin Türü": "Sağlık Raporu",
                        "Alındığı Kurum": iz.get("kurum", "-"),
                        "Başlangıç Tarihi": iz.get("baslangic", "-"),
                        "Bitiş Tarihi": iz.get("bitis", "-"),
                        "Teşhis / Açıklama": iz.get("teshis", "-")
                    })
        
        if saglik_tablo_listesi:
            st.dataframe(saglik_tablo_listesi, use_container_width=True)
            exc_r = tablo_to_excel_bytes(saglik_tablo_listesi, "Sağlık Raporları Raporu")
            pdf_r = tablo_to_html_pdf_bytes("Sağlık Raporları Raporu", saglik_tablo_listesi)
            ortak_indirme_alani(exc_r, pdf_r, "saglik_raporlari_raporu", "saglik_rapor_indzir")
        else:
            st.info("Kayıtlı sağlık raporu bulunmuyor.")

    with p_tab5:
        col_b_prs, col_indir_prs = st.columns([2, 2])
        with col_b_prs:
            st.subheader("📊 Personel Net Çalışma Süresi Raporu")

        if not st.session_state.personeller:
            st.info("Hesaplama yapabilmek için kayıtlı personel bulunmuyor.")
        else:
            p_isimleri = [p["ad_soyad"] for p in st.session_state.personeller]
            secilen_rapor_p = st.selectbox("Personel Seçin", p_isimleri, key="prs_rapor_sec")
            
            c_kol1, c_kol2 = st.columns(2)
            with c_kol1:
                donem_bas = st.date_input("Dönem Başlangıç Tarihi", value=datetime.date(2026, 10, 1), key="d_bas")
            with c_kol2:
                donem_bit = st.date_input("Dönem Bitiş Tarihi", value=datetime.date(2026, 10, 31), key="d_bit")

            ilgili_personel_obj = next((p for p in st.session_state.personeller if p["ad_soyad"] == secilen_rapor_p), None)
            if ilgili_personel_obj:
                net_gun, toplam_izin, saglik_raporu_gun, saatlik_izin_saat = net_calisma_gunu_hesapla(donem_bas, donem_bit, ilgili_personel_obj.get("izinler", []), st.session_state.resmi_tatiller)
                
                st.markdown("---")
                m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                with m_p1:
                    st.metric("Net Çalışılan Gün", f"{net_gun} Gün")
                with m_p2:
                    st.metric("Yıllık İzin Günü", f"{toplam_izin} Gün")
                with m_p3:
                    st.metric("Sağlık Raporu", f"{saglik_raporu_gun} Gün")
                with m_p4:
                    st.metric("Saatlik İzin", f"{saatlik_izin_saat} Saat")

                # Personele ait izin ve rapor geçmişi dökümü
                st.markdown("### 📋 Personele Ait İzin ve Rapor Geçmişi Detayı")
                personel_izinleri = ilgili_personel_obj.get("izinler", [])
                if personel_izinleri:
                    detay_tablo = []
                    for iz in personel_izinleri:
                        detay_tablo.append({
                            "Tür": iz.get("tur", "-"),
                            "Başlangıç": iz.get("baslangic", "-"),
                            "Bitiş": iz.get("bitis", "-"),
                            "Süre (Saat/Detay)": iz.get("saat", iz.get("kurum", "-")),
                            "Açıklama / Teşhis": iz.get("teshis", iz.get("detay", "-"))
                        })
                    st.dataframe(detay_tablo, use_container_width=True)
                else:
                    st.info("Bu personel için kayıtlı izin veya rapor bulunmuyor.")

                rapor_veri = [{
                    "Personel": secilen_rapor_p,
                    "Başlangıç": str(donem_bas),
                    "Bitiş": str(donem_bit),
                    "Net Çalışma Günü": net_gun,
                    "Yıllık İzin Günü": toplam_izin,
                    "Sağlık Raporu (Gün)": saglik_raporu_gun,
                    "Saatlik İzin (Saat)": saatlik_izin_saat
                }]
                prs_excel_data = tablo_to_excel_bytes(rapor_veri, f"Personel Raporu - {secilen_rapor_p}")
                prs_pdf_data = tablo_to_html_pdf_bytes(f"Personel Çalışma Raporu - {secilen_rapor_p}", rapor_veri)

                with col_indir_prs:
                    ortak_indirme_alani(prs_excel_data, prs_pdf_data, "personel_calisma_raporu", "prs_sayfasi")


# 9. KULLANIM TAKİBİ
elif menu == "Kullanım Takibi":
    col_b_kul, col_indir_kul = st.columns([2, 2])
    with col_b_kul:
        st.header("📈 Depo Ürün Kullanım ve Tüketim Takibi")

    st.markdown("Bu ekranda aşevinde gerçekleştirilen yemek üretimi ve fire/zayiat amaçlı tüm malzeme çıkışlarını ve tüketim geçmişini inceleyebilirsiniz.")

    loglar = st.session_state.kullanim_loglari
    if loglar:
        k_tablo_verisi = []
        excel_kullanim_liste = []

        for l in reversed(loglar):
            k_tablo_verisi.append({
                "Tarih / Saat": l.get("tarih", "-"),
                "Ürün Adı": l.get("urun", "-"),
                "İşlem Türü": l.get("tur", "-"),
                "Miktar": f"{l.get('miktar', 0):,.2f}",
                "Toplam Tutar": f"{l.get('tutar', 0):,.2f} ₺",
                "İşlemi Yapan": l.get("islem_yapan", "admin")
            })
            excel_kullanim_liste.append({
                "Tarih / Saat": l.get("tarih", "-"),
                "Ürün Adı": l.get("urun", "-"),
                "İşlem Türü": l.get("tur", "-"),
                "Miktar": round(l.get("miktar", 0), 2),
                "Tutar (TL)": round(l.get("tutar", 0), 2),
                "İşlemi Yapan": l.get("islem_yapan", "admin")
            })

        kul_excel_data = tablo_to_excel_bytes(excel_kullanim_liste, "Aziziye Aşevi - Kullanım ve Tüketim Raporu")
        kul_pdf_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Kullanım ve Tüketim Raporu", excel_kullanim_liste)

        with col_indir_kul:
            ortak_indirme_alani(kul_excel_data, kul_pdf_data, "kullanim_takip_raporu", "kullanim_sayfasi")

        st.dataframe(k_tablo_verisi, use_container_width=True)
    else:
        empty_excel_kul = tablo_to_excel_bytes([], "Boş Rapor")
        empty_pdf_kul = tablo_to_html_pdf_bytes("Boş Rapor", [])
        with col_indir_kul:
            ortak_indirme_alani(empty_excel_kul, empty_pdf_kul, "bos_kullanim_raporu", "kullanim_bos_sayfasi")
        st.info("Sistemde henüz kayıtlı bir kullanım veya tüketim hareketi bulunmuyor.")


# 10. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_fiy, col_indir_fiy = st.columns([2, 2])
    with col_b_fiy:
        st.header("💰 Ürün Birim Fiyatları ve Aylık Maliyet Analizi")

    st.markdown("Depodaki ürünlerin güncel birim fiyatlarını inceleyebilir ve ürün bazlı maliyet analizlerini görselleştirebilirsiniz.")

    if st.session_state.girisler:
        fiyat_tablo = []
        excel_fiyat_liste = []

        urun_fiyat_sozlugu = {}
        for g in st.session_state.girisler:
            urun_fiyat_sozlugu[g["urun"]] = {"fiyat": g["fiyat"], "kategori": g.get("kategori", "-"), "birim": g.get("birim", "Kg"), "depo": g.get("depo", "-")}

        for u_adi, u_bilgi in sorted(urun_fiyat_sozlugu.items()):
            fiyat_tablo.append({
                "Ürün Adı": u_adi,
                "Kategori": u_bilgi["kategori"],
                "Birim": u_bilgi["birim"],
                "Birim Fiyat": f"{u_bilgi['fiyat']:,.2f} ₺",
                "Depo": u_bilgi["depo"]
            })
            excel_fiyat_liste.append({
                "Ürün Adı": u_adi,
                "Kategori": u_bilgi["kategori"],
                "Birim": u_bilgi["birim"],
                "Birim Fiyat (TL)": round(u_bilgi["fiyat"], 2),
                "Depo": u_bilgi["depo"]
            })

        fiyat_excel_data = tablo_to_excel_bytes(excel_fiyat_liste, "Aziziye Aşevi - Ürün Birim Fiyatları Listesi")
        fiyat_pdf_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Ürün Birim Fiyatları Listesi", excel_fiyat_liste)

        with col_indir_fiy:
            ortak_indirme_alani(fiyat_excel_data, fiyat_pdf_data, "urun_birim_fiyatlari_raporu", "fiyat_sayfasi")

        st.subheader("📋 Envanter Birim Fiyat Tablosu")
        st.dataframe(fiyat_tablo, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 En Yüksek Birim Fiyata Sahip İlk 10 Ürün")
        
        sirali_fiyatlar = sorted(excel_fiyat_liste, key=lambda x: x["Birim Fiyat (TL)"], reverse=True)[:10]
        df_fiyat = pd.DataFrame(sirali_fiyatlar)
        
        if not df_fiyat.empty:
            fig = px.bar(df_fiyat, x="Ürün Adı", y="Birim Fiyat (TL)", color="Birim Fiyat (TL)", text="Birim Fiyat (TL)", title="Birim Fiyata Göre Ürün Sıralaması")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    else:
        empty_excel_f = tablo_to_excel_bytes([], "Boş Rapor")
        empty_pdf_f = tablo_to_html_pdf_bytes("Boş Rapor", [])
        with col_indir_fiy:
            ortak_indirme_alani(empty_excel_f, empty_pdf_f, "bos_fiyat_raporu", "fiyat_bos_sayfasi")
        st.info("Görüntülenecek ürün birim fiyatı bulunmuyor.")
