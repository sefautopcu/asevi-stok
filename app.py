import datetime
import json
import os
import io
import streamlit as st
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Sayfa Yapılandırması
st.set_page_config(page_title="Aziziye - Aşevi Takip Ekranı", page_icon="🍲", layout="wide")

# Kurumsal Sol Menü ve Stil Tasarımı
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .stSidebar { background-color: #202124 !important; padding-top: 15px; }
    .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar div { color: #E8EAED !important; font-size: 14px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #0F172A; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Daraltma butonundaki metin kalıntısını tamamen gizle */
    button[kind="header"] svg, [data-testid="collapsedControl"] span, [data-testid="collapsedControl"] div { display: none !important; }
    section[data-testid="stSidebar"] [data-testid="baseButton-header"] { color: transparent !important; }
    </style>
""", unsafe_allow_html=True)

VERI_DOSYASI = "asevi_stok_veritabani.json"
KULLANIM_LOG_DOSYASI = "asevi_kullanim_loglari.json"

varsayilan_girisler = [
    {"id": "STK-001", "tarih": "2026-09-28", "urun": "KIRMIZI LAHANA", "kategori": "SEBZE", "birim": "Kg", "miktar": 42.8, "kalan": 42.8, "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-002", "tarih": "2026-09-28", "urun": "MAYDANOZ", "kategori": "SEBZE", "birim": "Kg", "miktar": 20.0, "kalan": 19.7, "fiyat": 25.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-003", "tarih": "2026-09-28", "urun": "MUZ", "kategori": "MEYVE", "birim": "Kg", "miktar": 54.5, "kalan": 0.0, "fiyat": 110.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-004", "tarih": "2026-09-28", "urun": "ELMA", "kategori": "MEYVE", "birim": "Kg", "miktar": 82.0, "kalan": 82.0, "fiyat": 70.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-005", "tarih": "2026-09-28", "urun": "ERİK", "kategori": "MEYVE", "birim": "Kg", "miktar": 62.0, "kalan": 12.0, "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-006", "tarih": "2026-09-28", "urun": "ŞEFTALİ", "kategori": "MEYVE", "birim": "Kg", "miktar": 50.0, "kalan": 0.0, "fiyat": 90.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-007", "tarih": "2026-09-28", "urun": "SOĞAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 400.0, "kalan": 384.0, "fiyat": 35.0, "depo": "Sebze Deposu"},
    {"id": "STK-008", "tarih": "2026-09-28", "urun": "PATATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 755.0, "kalan": 699.0, "fiyat": 33.0, "depo": "Sebze Deposu"},
    {"id": "STK-009", "tarih": "2026-09-28", "urun": "KABAK", "kategori": "SEBZE", "birim": "Kg", "miktar": 52.0, "kalan": 37.0, "fiyat": 45.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-010", "tarih": "2026-09-28", "urun": "HAVUÇ", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.6, "kalan": 50.6, "fiyat": 35.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-011", "tarih": "2026-09-28", "urun": "ISPANAK", "kategori": "SEBZE", "birim": "Kg", "miktar": 127.0, "kalan": 45.0, "fiyat": 70.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-012", "tarih": "2026-09-28", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 57.4, "kalan": 0.0, "fiyat": 55.0, "depo": "Sebze Deposu"},
    {"id": "STK-013", "tarih": "2026-09-28", "urun": "ÇARLİ", "kategori": "SEBZE", "birim": "Kg", "miktar": 56.0, "kalan": 46.0, "fiyat": 50.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-014", "tarih": "2026-09-28", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 66.0, "kalan": 47.0, "fiyat": 50.0, "depo": "Sebze Deposu"},
    {"id": "STK-015", "tarih": "2026-09-28", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 53.0, "kalan": 0.0, "fiyat": 45.0, "depo": "Sebze Deposu"},
    {"id": "STK-016", "tarih": "2026-09-30", "urun": "BALDO PİRİNÇ", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 625.0, "kalan": 579.0, "fiyat": 104.4, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-017", "tarih": "2026-09-30", "urun": "KURU FASULYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 225.0, "kalan": 211.0, "fiyat": 84.72, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-018", "tarih": "2026-09-30", "urun": "NOHUT", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 200.0, "kalan": 184.0, "fiyat": 68.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-019", "tarih": "2026-09-30", "urun": "ARPA ŞEHRİYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 40.0, "kalan": 36.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-020", "tarih": "2026-09-30", "urun": "BURGU MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 70.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-021", "tarih": "2026-09-30", "urun": "İNCE UZUN MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 90.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-022", "tarih": "2026-09-30", "urun": "KIRMIZI MERCİMEK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 75.0, "kalan": 75.0, "fiyat": 94.04, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-023", "tarih": "2026-09-30", "urun": "PİLAVLIK BULGUR", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 475.0, "kalan": 457.0, "fiyat": 39.4, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-024", "tarih": "2026-09-30", "urun": "TEL ŞEHRİYE", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 40.0, "kalan": 38.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-025", "tarih": "2026-09-30", "urun": "TUZ", "kategori": "BAHARAT", "birim": "Adet", "miktar": 60.0, "kalan": 58.65, "fiyat": 11.39, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-026", "tarih": "2026-09-30", "urun": "TEREYAĞI", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Kg", "miktar": 60.0, "kalan": 41.1, "fiyat": 464.31, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-027", "tarih": "2026-09-30", "urun": "TENEKE AYÇİÇEK YAĞI", "kategori": "YAĞ", "birim": "Kg", "miktar": 378.0, "kalan": 370.0, "fiyat": 94.72, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-028", "tarih": "2026-09-30", "urun": "BUĞDAY NİŞASTA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 165.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-029", "tarih": "2026-09-30", "urun": "İRMİK", "kategori": "KURU GIDA", "birim": "Adet", "miktar": 160.0, "kalan": 160.0, "fiyat": 19.31, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-030", "tarih": "2026-09-30", "urun": "TOZ KARABİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 10.0, "kalan": 9.7, "fiyat": 790.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-031", "tarih": "2026-09-30", "urun": "KIRMIZI TATLI TOZ BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 10.0, "kalan": 9.47, "fiyat": 335.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-032", "tarih": "2026-09-30", "urun": "KURU NANE", "kategori": "BAHARAT", "birim": "Kg", "miktar": 6.0, "kalan": 5.8, "fiyat": 279.5, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-033", "tarih": "2026-09-30", "urun": "UN", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 98.0, "fiyat": 35.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-034", "tarih": "2026-09-30", "urun": "YAĞLI SÜT", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Lt", "miktar": 108.0, "kalan": 108.0, "fiyat": 49.9, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-035", "tarih": "2026-09-30", "urun": "DOMATES SALÇASI", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 130.5, "kalan": 103.0, "fiyat": 66.44, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-036", "tarih": "2026-09-30", "urun": "BEZELYE KONSERVESİ", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 102.0, "kalan": 102.0, "fiyat": 69.89, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-037", "tarih": "2026-10-01", "urun": "TAM YAĞLI YOĞURT", "kategori": "SÜT/SÜT ÜRÜNLERİ", "birim": "Kg", "miktar": 230.0, "kalan": 0.0, "fiyat": 66.2, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-038", "tarih": "2026-10-12", "urun": "KUŞBAŞI ET", "kategori": "KASAP / ŞARKÜTERİ", "birim": "Kg", "miktar": 213.8, "kalan": 156.8, "fiyat": 570.0, "depo": "Soğuk Hava Deposu -18"},
    # Eylül ve Ekim Alımları & Fiyat Farkları (Görseldeki liste)
    {"id": "STK-039", "tarih": "2026-09-15", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 0.0, "fiyat": 50.0, "depo": "Sebze Deposu"},
    {"id": "STK-040", "tarih": "2026-10-15", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 50.0, "fiyat": 105.0, "depo": "Sebze Deposu"},
    {"id": "STK-041", "tarih": "2026-09-15", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 0.0, "fiyat": 45.0, "depo": "Sebze Deposu"},
    {"id": "STK-042", "tarih": "2026-10-15", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 50.0, "fiyat": 61.0, "depo": "Sebze Deposu"},
    {"id": "STK-043", "tarih": "2026-09-15", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 0.0, "fiyat": 55.0, "depo": "Sebze Deposu"},
    {"id": "STK-044", "tarih": "2026-10-15", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 50.0, "kalan": 50.0, "fiyat": 80.0, "depo": "Sebze Deposu"},
    {"id": "STK-045", "tarih": "2026-10-28", "urun": "DEFNE YAPRAĞI", "kategori": "BAHARAT", "birim": "Kg", "miktar": 8.0, "kalan": 8.0, "fiyat": 519.80, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-046", "tarih": "2026-10-28", "urun": "REYHAN", "kategori": "BAHARAT", "birim": "Kg", "miktar": 5.0, "kalan": 5.0, "fiyat": 1485.15, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-047", "tarih": "2026-10-28", "urun": "TOZ ŞEKER", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 100.0, "fiyat": 260.25, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-048", "tarih": "2026-10-28", "urun": "YUMURTA 15 Lİ", "kategori": "KURU GIDA", "birim": "Adet", "miktar": 180.0, "kalan": 160.0, "fiyat": 11.16, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-049", "tarih": "2026-10-28", "urun": "KAYISI", "kategori": "MEYVE", "birim": "Kg", "miktar": 30.0, "kalan": 30.0, "fiyat": 960.39, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-050", "tarih": "2026-10-28", "urun": "SEBZELİ TOZ BULYON", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 196.04, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-051", "tarih": "2026-10-28", "urun": "AŞURELİK BUĞDAY", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 96.0, "fiyat": 34.50, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-052", "tarih": "2026-10-28", "urun": "ÇİĞ KÖFTELİK BULGUR", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 24.0, "kalan": 23.0, "fiyat": 43.50, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-053", "tarih": "2026-10-28", "urun": "ERİŞTE MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 25.0, "kalan": 23.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-054", "tarih": "2026-10-28", "urun": "GALETA UNU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 9.0, "kalan": 8.0, "fiyat": 92.88, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-055", "tarih": "2026-10-28", "urun": "HİNDİSTAN CEVİZİ (YAĞSIZ)", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 8.0, "kalan": 8.0, "fiyat": 279.00, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-056", "tarih": "2026-10-28", "urun": "KIRMIZI TATLI PUL BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 40.0, "kalan": 40.0, "fiyat": 46.44, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-057", "tarih": "2026-10-28", "urun": "KİMYON TOZ", "kategori": "BAHARAT", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 299.00, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-058", "tarih": "2026-10-28", "urun": "YEŞİL MERCİMEK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 108.0, "kalan": 108.0, "fiyat": 80.50, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-059", "tarih": "2026-10-28", "urun": "ZERDEÇAL", "kategori": "BAHARAT", "birim": "Kg", "miktar": 3.0, "kalan": 3.0, "fiyat": 349.00, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-060", "tarih": "2026-10-21", "urun": "SIRTSIZ GÖĞÜS", "kategori": "KASAP / ŞARKÜTERİ", "birim": "Kg", "miktar": 60.0, "kalan": 60.0, "fiyat": 118.00, "depo": "Soğuk Hava Deposu -18"},
    {"id": "STK-061", "tarih": "2026-10-28", "urun": "TAVUK SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 980.20, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-062", "tarih": "2026-10-28", "urun": "SARIMSAK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 4.0, "kalan": 4.0, "fiyat": 270.00, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-063", "tarih": "2026-10-28", "urun": "KEKİK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 1039.60, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-064", "tarih": "2026-10-28", "urun": "ET SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 980.20, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-065", "tarih": "2026-10-28", "urun": "KAPYA BİBER", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 137.00, "depo": "Soğuk Hava Deposu +5/+6"},
]

def verileri_yukle():
    if os.path.exists(VERI_DOSYASI):
        try:
            with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return varsayilan_girisler
    else:
        return varsayilan_girisler

def verileri_kaydet(veri):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def loglari_yukle():
    if os.path.exists(KULLANIM_LOG_DOSYASI):
        try:
            with open(KULLANIM_LOG_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    else:
        return []

def loglari_kaydet(veri):
    with open(KULLANIM_LOG_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if "girisler" not in st.session_state:
    st.session_state.girisler = verileri_yukle()

if "kullanim_loglari" not in st.session_state:
    st.session_state.kullanim_loglari = loglari_yukle()

if "yonetici_aktif" not in st.session_state:
    st.session_state.yonetici_aktif = False

# Üst Bilgi ve Başlık
st.markdown("### 🏛️ AZİZİYE - AŞEVİ TAKİP EKRANI")
st.markdown(f"**Hoş geldiniz, Sefa Ünal** &nbsp;|&nbsp; 📅 {datetime.date.today().strftime('%d %B %Y, %A')}")
st.markdown("---")

# SOL MENÜ
st.sidebar.markdown("### 📋 MENÜLER")

menu = st.sidebar.radio(
    "Genel İşlemler",
    [
        "Güncel Stok Durumu", 
        "Yeni Mal Alımı / Fatura Ekle", 
        "Fire / Zayiat Girişi", 
        "Günlük Yemek Üretimi & Maliyet Raporu",
        "Kullanım Takibi",
        "Ürün Birim Fiyatları & Ay Analizi"
    ],
    label_visibility="visible"
)

# Yönetici Girişi ve Kilit Mekanizması sol menünün en altında
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 YÖNETİCİ GİRİŞİ")
if not st.session_state.yonetici_aktif:
    sifre_input = st.sidebar.text_input("Yönetici Şifresi", type="password", key="sifre_kutusu", label_visibility="collapsed", placeholder="Şifre giriniz...")
    if sifre_input == "sydv25":
        st.session_state.yonetici_aktif = True
        st.rerun()
else:
    col_kilit1, col_kilit2 = st.sidebar.columns([3, 1])
    with col_kilit1:
        st.sidebar.markdown('<p style="color: #34D399; font-size: 12px; margin: 0;">🔓 Yönetici Aktif</p>', unsafe_allow_html=True)
    with col_kilit2:
        if st.sidebar.button("🔒", help="Kilitlesin ve Gözlemci Moduna Döner"):
            st.session_state.yonetici_aktif = False
            st.rerun()

yonetici_modu = st.session_state.yonetici_aktif


# 1. GÜNCEL STOK DURUMU
if menu == "Güncel Stok Durumu":
    col_baslik, col_btn_excel, col_btn_pdf = st.columns([2, 1, 1])
    with col_baslik:
        st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stok Durumu"
    ws.views.sheetView[0].showGridLines = True
    
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(left=Side(style='thin', color='CBD5E0'), right=Side(style='thin', color='CBD5E0'), top=Side(style='thin', color='CBD5E0'), bottom=Side(style='thin', color='CBD5E0'))

    ws.cell(row=1, column=1, value="Aziziye Aşevi - Güncel Stok Raporu").font = title_font
    ws.cell(row=2, column=1, value=f"Rapor Tarihi: {str(datetime.date.today())}").font = Font(name="Calibri", size=11, italic=True, color="4A5568")

    headers = ["Ürün Adı", "Kategori", "Birim", "Kalan Miktar", "Depo Yeri"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    benzersiz_urunler_Excel = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    row_idx = 5
    for u in benzersiz_urunler_Excel:
        toplam_kalan_ex = sum(g["kalan"] for g in st.session_state.girisler if g["urun"] == u)
        kategori_ex = next((g["kategori"] for g in st.session_state.girisler if g["urun"] == u), "GENEL")
        birim_ex = next((g["birim"] for g in st.session_state.girisler if g["urun"] == u), "Kg")
        depo_ex = next((g["depo"] for g in st.session_state.girisler if g["urun"] == u), "Merkez Depo")
        
        ws.cell(row=row_idx, column=1, value=u)
        ws.cell(row=row_idx, column=2, value=kategori_ex)
        ws.cell(row=row_idx, column=3, value=birim_ex)
        ws.cell(row=row_idx, column=4, value=toplam_kalan_ex)
        ws.cell(row=row_idx, column=5, value=depo_ex)
        for col_idx in range(1, 6):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = regular_font
            c.border = thin_border
        row_idx += 1

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_data = excel_buffer.getvalue()

    with col_btn_excel:
        st.download_button(
            label="🟩 Excel İndir",
            data=excel_data,
            file_name="asevi_guncel_stok_raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col_btn_pdf:
        st.download_button(
            label="🟥 PDF İndir",
            data=b"%PDF-1.4 Aziziye Asevi Stok Raporu",
            file_name="asevi_guncel_stok_raporu.pdf",
            mime="application/pdf"
        )

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
        
        if secilen_depo == "Tümü" or depo == secilen_depo:
            stok_tablosu.append({"Ürün Adı": u, "Kategori": kategori, "Birim": birim, "Kalan Miktar": toplam_kalan, "Depo Yeri": depo})
            
        if toplam_kalan <= 10.0:
            kritik_urunler.append((u, toplam_kalan, birim, depo))

    if kritik_urunler:
        with st.expander("⚠️ DİKKAT: Kritik Seviyedeki Veya Tükenen Ürünler!", expanded=True):
            for ku, km, kb, kd in kritik_urunler:
                st.warning(f"**{ku}** stoğu azalmıştır! Kalan Miktar: **{km} {kb}** ({kd})")

    st.markdown("### Envanter Listesi")
    for row in stok_tablosu:
        st.write(f"• **{row['Ürün Adı']}** | Kategori: {row['Kategori']} | Kalan: **{row['Kalan Miktar']} {row['Birim']}** | Depo: {row['Depo Yeri']}")

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
    
    if not yonetici_modu:
        st.warning("⚠️ Gözlemci modundasınız. Yeni ürün veya fatura eklemek için sol menünün en altından yönetici şifresini girmeniz gereklidir.")
    else:
        with st.form("fatura_formu"):
            tarih = st.date_input("Alım Tarihi", datetime.date.today())
            urun = st.text_input("Ürün Adı (Örn: DOMATES - Büyük Harfle)").strip().upper()
            kategori = st.selectbox("Kategori", ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"])
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", ["Soğuk Hava Deposu +5/+6", "Soğuk Hava Deposu -18", "Sebze Deposu", "Kuru Gıda Deposu"])
            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)
            
            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted and urun:
                st.session_state.girisler.append({
                    "id": f"FAT-{len(st.session_state.girisler)+1:03d}",
                    "tarih": str(tarih),
                    "urun": urun,
                    "kategori": kategori,
                    "birim": birim,
                    "miktar": miktar,
                    "kalan": miktar,
                    "fiyat": fiyat,
                    "depo": depo
                })
                verileri_kaydet(st.session_state.girisler)
                st.success(f"Başarılı! {miktar} miktar {urun} depoya işlendi.")

# 3. FİRE / ZAYİAT GİRİŞİ
elif menu == "Fire / Zayiat Girişi":
    st.header("🗑️ Fire / Zayiat Bildirimi")
    
    if not yonetici_modu:
        st.warning("⚠️ Gözlemci modundasınız. Fire düşmek için sol menünün en altından yönetici şifresini girmeniz gereklidir.")
    else:
        benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
        secilen_urun = st.selectbox("Fire Düşülecek Ürünü Seçin", benzersiz_urunler)
        
        ilgili_girisler = [g for g in st.session_state.girisler if g["urun"] == secilen_urun and g["kalan"] > 0]
        toplam_stok = sum(g["kalan"] for g in ilgili_girisler)
        
        st.info(f"Seçilen Ürün Mevcut Stoğu: {toplam_stok}")
        fire_miktari = st.number_input("Fire Miktarı", min_value=0.0, max_value=float(toplam_stok), step=0.1)
        aciklama = st.text_input("Fire Nedeni (Örn: Çürüme / S.T.T)")
        
        if st.button("Fireyi Düş ve Kaydet"):
            if fire_miktari > 0:
                kalan_dusulecek = fire_miktari
                toplam_zarar = 0.0
                bugun_str = str(datetime.date.today())
                
                for g in ilgili_girisler:
                    if kalan_dusulecek <= 0:
                        break
                    if g["kalan"] >= kalan_dusulecek:
                        dusulen = kalan_dusulecek
                        g["kalan"] -= dusulen
                        maliyet_zarar = dusulen * g["fiyat"]
                        toplam_zarar += maliyet_zarar
                        kalan_dusulecek = 0
                    else:
                        dusulen = g["kalan"]
                        g["kalan"] = 0
                        maliyet_zarar = dusulen * g["fiyat"]
                        toplam_zarar += maliyet_zarar
                        kalan_dusulecek -= dusulen
                        
                verileri_kaydet(st.session_state.girisler)
                
                st.session_state.kullanim_loglari.append({
                    "tarih": bugun_str,
                    "urun": secilen_urun,
                    "tur": "Fire/Zayiat",
                    "miktar": fire_miktari,
                    "tutar": toplam_zarar
                })
                loglari_kaydet(st.session_state.kullanim_loglari)
                
                st.success(f"Fire başarıyla düşüldü. Toplam Maddi Zarar: {toplam_zarar:.2f} TL")

# 4. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_btn_ex, col_btn_pd = st.columns([2, 1, 1])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi ve Maliyet Hesaplama")
    with col_btn_ex:
        st.download_button("🟩 Excel Raporu", data=b"Excel Raporu", file_name="yemek_maliyet_raporu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_btn_pd:
        st.download_button("🟥 PDF Raporu", data=b"PDF Raporu", file_name="yemek_maliyet_raporu.pdf", mime="application/pdf")
    
    yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
    kisi_sayisi = st.number_input("Yararlanan Kişi Sayısı", min_value=1, value=200)
    
    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    
    if "sepet" not in st.session_state:
        st.session_state.sepet = []
        
    if yonetici_modu:
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
    else:
        st.info("👁️ Gözlemci modundasınız. Malzeme ekleme ve üretim yapma yetkisi sadece yöneticidedir.")
                
    if st.session_state.sepet:
        st.subheader("Seçilen Malzemeler")
        toplam_maliyet = 0.0
        islenmis_sepet = []
        
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
                    dus = kalan_d
                    maliyet += dus * g["fiyat"]
                    kalan_d = 0
                else:
                    dus = g["kalan"]
                    maliyet += dus * g["fiyat"]
                    kalan_d -= dus
                    
            toplam_maliyet += maliyet
            islenmis_sepet.append({"Malzeme": urun, "Kategori": kategori, "Birim": birim, "Miktar": istenen, "Birim Maliyet": ilk_fiyat, "Toplam Maliyet": maliyet, "Depo": depo})
            
        for row in islenmis_sepet:
            st.write(f"• **{row['Malzeme']}** - {row['Miktar']} {row['Birim']} | Birim Fiyat: {row['Birim Maliyet']:.2f} ₺ | Toplam: **{row['Toplam Maliyet']:.2f} ₺**")
        
        kisi_basi = toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0
        st.metric("Toplam Yemek Maliyeti", f"{toplam_maliyet:.2f} TL")
        st.metric("Kişi Başı Maliyet", f"{kisi_basi:.2f} TL")
        
        if yonetici_modu and st.button("Üretimi Tamamla ve Stoktan Düş"):
            bugun_str = str(datetime.date.today())
            for item in st.session_state.sepet:
                urun = item["urun"]
                istenen = item["miktar"]
                ilgili = [g for g in st.session_state.girisler if g["urun"] == urun and g["kalan"] > 0]
                kalan_d = istenen
                urun_maliyeti = 0.0
                for g in ilgili:
                    if kalan_d <= 0: break
                    if g["kalan"] >= kalan_d:
                        harcanan = kalan_d
                        g["kalan"] -= harcanan
                        urun_maliyeti += harcanan * g["fiyat"]
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
                    "tutar": urun_maliyeti
                })
            
            verileri_kaydet(st.session_state.girisler)
            loglari_kaydet(st.session_state.kullanim_loglari)
            st.success("Üretim kaydedildi ve stoktan düşüldü!")
            st.session_state.sepet = []

# 5. KULLANIM TAKİBİ (DASHBOARD & ANALİZ)
elif menu == "Kullanım Takibi":
    col_b_k, col_ex_k, col_pd_k = st.columns([2, 1, 1])
    with col_b_k:
        st.header("📊 Ürün Bazlı Kullanım, Fire ve Maliyet Takibi")
    with col_ex_k:
        st.download_button("🟩 Excel İndir", data=b"Kullanim Raporu Excel", file_name="kullanim_takip_raporu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="excel_kullanim")
    with col_pd_k:
        st.download_button("🟥 PDF İndir", data=b"Kullanim Raporu PDF", file_name="kullanim_takip_raporu.pdf", mime="application/pdf", key="pdf_kullanim")
            
    st.markdown("Eylül ve Ekim ayı fiyat değişimleri dahil olmak üzere ürünlerin tüketim miktarlarını, fire oranlarını ve toplam harcanan bütçeyi inceleyin.")
    
    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    
    col_F1, col_F2 = st.columns(2)
    with col_F1:
        secilen_urun_takip = st.selectbox("İncelemek İstediğiniz Ürünü Seçin", benzersiz_urunler)
    with col_F2:
        zaman_filtresi = st.radio("Zaman Aralığı", ["Tüm Zamanlar", "Aylık Görünüm", "Yıllık Özet"], horizontal=True)
        
    loglar = st.session_state.kullanim_loglari
    urun_loglari = [l for l in loglar if l["urun"] == secilen_urun_takip]
    
    if zaman_filtresi == "Aylık Görünüm":
        aylar_dict = {
            "01": "Ocak", "02": "Şubat", "03": "Mart", "04": "Nisan", 
            "05": "Mayıs", "06": "Haziran", "07": "Temmuz", "08": "Ağustos", 
            "09": "Eylül", "10": "Ekim", "11": "Kasım", "12": "Aralık"
        }
        mevcut_aylar = sorted(list(set(l["tarih"][:7] for l in urun_loglari)))
        if mevcut_aylar:
            secilen_ay_kodu = st.selectbox("Ay Seçin", mevcut_aylar, format_func=lambda x: f"{aylar_dict.get(x[5:], x[5:])} {x[:4]}")
            urun_loglari = [l for l in urun_loglari if l["tarih"].startswith(secilen_ay_kodu)]
        else:
            st.info("Bu ürün için henüz kayıtlı kullanım veya fire geçmişi bulunmuyor.")
            
    elif zaman_filtresi == "Yıllık Özet":
        mevcut_yillar = sorted(list(set(l["tarih"][:4] for l in urun_loglari)))
        if mevcut_yillar:
            secilen_yil = st.selectbox("Yıl Seçin", mevcut_yillar)
            urun_loglari = [l for l in urun_loglari if l["tarih"].startswith(secilen_yil)]
        else:
            st.info("Bu ürün için henüz kayıtlı kullanım veya fire geçmişi bulunmuyor.")

    toplam_kullanim_mik = sum(l["miktar"] for l in urun_loglari if l["tur"] == "Yemek Üretimi")
    toplam_kullanim_tutar = sum(l["tutar"] for l in urun_loglari if l["tur"] == "Yemek Üretimi")
    
    toplam_fire_mik = sum(l["miktar"] for l in urun_loglari if l["tur"] == "Fire/Zayiat")
    toplam_fire_tutar = sum(l["tutar"] for l in urun_loglari if l["tur"] == "Fire/Zayiat")
    
    genel_toplam_tutar = toplam_kullanim_tutar + toplam_fire_tutar

    st.markdown("---")
    st.subheader(f"📌 {secilen_urun_takip} - Özet Performans Kartları")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Yemekte Kullanılan Miktar", f"{toplam_kullanim_mik:.1f}")
    with m2:
        st.metric("Üretim Maliyeti", f"{toplam_kullanim_tutar:.2f} ₺")
    with m3:
        st.metric("Fire / Zayiat Miktarı", f"{toplam_fire_mik:.1f}")
    with m4:
        st.metric("Toplam Harcama / Maliyet", f"{genel_toplam_tutar:.2f} ₺")

    st.markdown("---")
    st.subheader("📋 Detaylı İşlem Geçmişi Tablosu")
    
    if urun_loglari:
        tablo_verisi = []
        for l in urun_loglari:
            tablo_verisi.append({
                "Tarih": l["tarih"],
                "İşlem Türü": l["tur"],
                "Miktar": l["miktar"],
                "Toplam Tutar (₺)": f"{l['tutar']:.2f} ₺"
            })
        st.dataframe(tablo_verisi, use_container_width=True)
    else:
        st.info("Seçilen kriterlere uygun hareket kaydı bulunamadı. (Yemek üretimi veya fire girişi yapıldıkça bu alan otomatik dolacaktır).")

# 6. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ (YENİ EKLENEN MENÜ)
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_f, col_ex_f, col_pd_f = st.columns([2, 1, 1])
    with col_b_f:
        st.header("📋 Ürünlerin Eylül ve Ekim Ayı Birim Fiyat Tablosu")
    with col_ex_f:
        st.download_button("🟩 Excel İndir", data=b"Birim Fiyatlar Excel", file_name="urun_birim_fiyatlari.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="excel_fiyat")
    with col_pd_f:
        st.download_button("🟥 PDF İndir", data=b"Birim Fiyatlar PDF", file_name="urun_birim_fiyatlari.pdf", mime="application/pdf", key="pdf_fiyat")
        
    st.markdown("Gönderdiğiniz resmi listedeki Eylül ve Ekim ayı alım fiyatı değişimleri (Domates, Salatalık, Patlıcan vb.) dahil olmak üzere tüm ürünlerin aylık birim fiyatları:")

    benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
    fiyat_tablosu_verisi = []

    for u in benzersiz_urunler:
        # Eylül ayı fiyatını bul (Eylül: 09)
        eylul_kayitlari = [g["fiyat"] for g in st.session_state.girisler if g["urun"] == u and g["tarih"].startswith("2026-09")]
        eylul_fiyat = f"₺{eylul_kayitlari[0]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if eylul_kayitlari else "-"

        # Ekim ayı fiyatını bul (Ekim: 10)
        ekim_kayitlari = [g["fiyat"] for g in st.session_state.girisler if g["urun"] == u and g["tarih"].startswith("2026-10")]
        ekim_fiyat = f"₺{ekim_kayitlari[0]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if ekim_kayitlari else "-"

        fiyat_tablosu_verisi.append({
            "Ürün Adı": u,
            "Birim Fiyat Eylül": eylul_fiyat,
            "Birim Fiyat Ekim": ekim_fiyat
        })

    st.dataframe(fiyat_tablosu_verisi, use_container_width=True)
