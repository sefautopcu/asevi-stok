import datetime
import json
import os
import streamlit as st
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Sayfa Yapılandırması
st.set_page_config(page_title="Aziziye - Aşevi Takip Ekranı", page_icon="🍲", layout="wide")

# Sol menü arka planı #182828 ve yazılar beyaz olacak şekilde özel tasarım
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .stSidebar { background-color: #182828 !important; padding-top: 10px; }
    .stSidebar * { color: #FFFFFF !important; }
    h1, h2, h3 { color: #0F172A; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    </style>
""", unsafe_allow_html=True)

VERI_DOSYASI = "asevi_stok_veritabani.json"

# Varsayılan 62 Kalem Ürün ve Başlangıç Verileri
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
    {"id": "STK-039", "tarih": "2026-10-28", "urun": "DEFNE YAPRAĞI", "kategori": "BAHARAT", "birim": "Kg", "miktar": 8.0, "kalan": 8.0, "fiyat": 519.8, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-040", "tarih": "2026-10-28", "urun": "REYHAN", "kategori": "BAHARAT", "birim": "Kg", "miktar": 5.0, "kalan": 5.0, "fiyat": 1485.15, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-041", "tarih": "2026-10-28", "urun": "TOZ ŞEKER", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 100.0, "fiyat": 260.25, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-042", "tarih": "2026-10-28", "urun": "YUMURTA 15 Lİ", "kategori": "KURU GIDA", "birim": "Adet", "miktar": 180.0, "kalan": 160.0, "fiyat": 11.155, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-043", "tarih": "2026-10-28", "urun": "KAYISI", "kategori": "MEYVE", "birim": "Kg", "miktar": 30.0, "kalan": 30.0, "fiyat": 960.39, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-044", "tarih": "2026-10-28", "urun": "SEBZELİ TOZ BULYON", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 196.04, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-045", "tarih": "2026-10-28", "urun": "AŞURELİK BUĞDAY", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 100.0, "kalan": 96.0, "fiyat": 34.5, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-046", "tarih": "2026-10-28", "urun": "ÇİĞ KÖFTELİK BULGUR", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 24.0, "kalan": 23.0, "fiyat": 43.5, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-047", "tarih": "2026-10-28", "urun": "ERİŞTE MAKARNA", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 25.0, "kalan": 23.0, "fiyat": 43.98, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-048", "tarih": "2026-10-28", "urun": "GALETA UNU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 9.0, "kalan": 8.0, "fiyat": 92.88, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-049", "tarih": "2026-10-28", "urun": "HİNDİSTAN CEVİZİ (YAĞSIZ)", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 8.0, "kalan": 8.0, "fiyat": 279.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-050", "tarih": "2026-10-28", "urun": "KIRMIZI TATLI PUL BİBER", "kategori": "BAHARAT", "birim": "Kg", "miktar": 40.0, "kalan": 40.0, "fiyat": 46.44, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-051", "tarih": "2026-10-28", "urun": "KİMYON TOZ", "kategori": "BAHARAT", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 299.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-052", "tarih": "2026-10-28", "urun": "YEŞİL MERCİMEK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 108.0, "kalan": 108.0, "fiyat": 80.5, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-053", "tarih": "2026-10-28", "urun": "ZERDEÇAL", "kategori": "BAHARAT", "birim": "Kg", "miktar": 3.0, "kalan": 3.0, "fiyat": 349.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-054", "tarih": "2026-10-21", "urun": "SIRTSIZ GÖĞÜS", "kategori": "KASAP / ŞARKÜTERİ", "birim": "Kg", "miktar": 60.0, "kalan": 60.0, "fiyat": 118.0, "depo": "Soğuk Hava Deposu -18"},
    {"id": "STK-055", "tarih": "2026-10-28", "urun": "TAVUK SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 980.2, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-056", "tarih": "2026-10-28", "urun": "SARIMSAK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 4.0, "kalan": 4.0, "fiyat": 270.0, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-057", "tarih": "2026-10-28", "urun": "KEKİK", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 1039.6, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-058", "tarih": "2026-10-28", "urun": "ET SUYU", "kategori": "KURU GIDA", "birim": "Kg", "miktar": 2.0, "kalan": 2.0, "fiyat": 980.2, "depo": "Kuru Gıda Deposu"},
    {"id": "STK-059", "tarih": "2026-10-28", "urun": "KAPYA BİBER", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 137.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-060", "tarih": "2026-10-28", "urun": "SALATALIK", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 61.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-061", "tarih": "2026-10-28", "urun": "DOMATES", "kategori": "SEBZE", "birim": "Kg", "miktar": 20.0, "kalan": 20.0, "fiyat": 105.0, "depo": "Soğuk Hava Deposu +5/+6"},
    {"id": "STK-062", "tarih": "2026-10-28", "urun": "PATLICAN", "kategori": "SEBZE", "birim": "Kg", "miktar": 10.0, "kalan": 10.0, "fiyat": 80.0, "depo": "Soğuk Hava Deposu +5/+6"},
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

if "girisler" not in st.session_state:
    st.session_state.girisler = verileri_yukle()

if "yonetici_aktif" not in st.session_state:
    st.session_state.yonetici_aktif = False

# Üst Bilgi ve Başlık
st.markdown("### 🏛️ AZİZİYE SYDV - KONTROL PANELİ")
st.markdown(f"**Hoş geldiniz, Sefa Ünal** &nbsp;|&nbsp; 📅 {datetime.date.today().strftime('%d %B %Y, %A')}")
st.markdown("---")

# SOL MENÜ: Açılır kapanır Genel İşlemler
st.sidebar.markdown("### 📋 MENÜLER")

with st.sidebar.expander("📂 GENEL İŞLEMLER", expanded=True):
    menu = st.radio(
        "Genel İşlemler",
        ["Güncel Stok Durumu", "Yeni Mal Alımı / Fatura Ekle", "Fire / Zayiat Girişi", "Günlük Yemek Üretimi & Maliyet Raporu"],
        label_visibility="collapsed"
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
    col_baslik, col_buton = st.columns([4, 1])
    with col_baslik:
        st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")
    with col_buton:
        if st.button("📥 Excel İndir"):
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

            benzersiz_urunler = sorted(list(set(g["urun"] for g in st.session_state.girisler)))
            row_idx = 5
            for u in benzersiz_urunler:
                toplam_kalan = sum(g["kalan"] for g in st.session_state.girisler if g["urun"] == u)
                kategori = next((g["kategori"] for g in st.session_state.girisler if g["urun"] == u), "GENEL")
                birim = next((g["birim"] for g in st.session_state.girisler if g["urun"] == u), "Kg")
                depo = next((g["depo"] for g in st.session_state.girisler if g["urun"] == u), "Merkez Depo")
                
                ws.cell(row=row_idx, column=1, value=u)
                ws.cell(row=row_idx, column=2, value=kategori)
                ws.cell(row=row_idx, column=3, value=birim)
                ws.cell(row=row_idx, column=4, value=toplam_kalan)
                ws.cell(row=row_idx, column=5, value=depo)
                for col_idx in range(1, 6):
                    c = ws.cell(row=row_idx, column=col_idx)
                    c.font = regular_font
                    c.border = thin_border
                row_idx += 1

            excel_adi = "asevi_guncel_stok_raporu.xlsx"
            wb.save(excel_adi)
            st.success("Stok raporu başarıyla indirildi!")

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
    st.header("📝 Yeni Fatura ve Mal Alımı Girişi (Örn. Greyfurt vb.)")
    
    if not yonetici_modu:
        st.warning("⚠️ Gözlemci modundasınız. Yeni ürün veya fatura eklemek için sol menünün en altından yönetici şifresini girmeniz gereklidir.")
    else:
        with st.form("fatura_formu"):
            tarih = st.date_input("Alım Tarihi", datetime.date.today())
            urun = st.text_input("Ürün Adı (Örn: GREYFURT - Büyük Harfle)").strip().upper()
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
                st.success(f"Başarılı! {miktar} miktar {urun} depoya işlendi ve kalıcı olarak kaydedildi.")

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
                for g in ilgili_girisler:
                    if kalan_dusulecek <= 0:
                        break
                    if g["kalan"] >= kalan_dusulecek:
                        dusulen = kalan_dusulecek
                        g["kalan"] -= dusulen
                        toplam_zarar += (dusulen * g["fiyat"])
                        kalan_dusulecek = 0
                    else:
                        dusulen = g["kalan"]
                        g["kalan"] = 0
                        toplam_zarar += (dusulen * g["fiyat"])
                        kalan_dusulecek -= dusulen
                verileri_kaydet(st.session_state.girisler)
                st.success(f"Fire başarıyla düşüldü. Toplam Maddi Zarar: {toplam_zarar:.2f} TL")

# 4. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    st.header("🍲 Günlük Yemek Üretimi ve Maliyet Hesaplama")
    
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
        
        if yonetici_modu and st.button("Üretimi Tamamla, Stoktan Düş ve Excel Raporu Al"):
            for item in st.session_state.sepet:
                urun = item["urun"]
                istenen = item["miktar"]
                ilgili = [g for g in st.session_state.girisler if g["urun"] == urun and g["kalan"] > 0]
                kalan_d = istenen
                for g in ilgili:
                    if kalan_d <= 0: break
                    if g["kalan"] >= kalan_d:
                        g["kalan"] -= kalan_d
                        kalan_d = 0
                    else:
                        kalan_d -= g["kalan"]
                        g["kalan"] = 0
            verileri_kaydet(st.session_state.girisler)
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Günlük Maliyet Raporu"
            ws.views.sheetView[0].showGridLines = True
            
            header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
            bold_font = Font(name="Calibri", size=11, bold=True)
            regular_font = Font(name="Calibri", size=11)
            summary_fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
            thin_border = Border(left=Side(style='thin', color='CBD5E0'), right=Side(style='thin', color='CBD5E0'), top=Side(style='thin', color='CBD5E0'), bottom=Side(style='thin', color='CBD5E0'))
            total_border = Border(top=Side(style='thin', color='1E3A8A'), bottom=Side(style='double', color='1E3A8A'))

            ws.cell(row=1, column=1, value="Aşevi Günlük Üretim ve Maliyet Raporu").font = title_font
            ws.cell(row=2, column=1, value=f"Tarih: {str(datetime.date.today())} | Menü: {yemek_adi} | Kişi Sayısı: {kisi_sayisi}").font = Font(name="Calibri", size=11, italic=True, color="4A5568")

            headers = ["Malzeme Adı", "Kategori", "Birim", "Kullanılan Miktar", "Birim Maliyet (TL)", "Toplam Maliyet (TL)", "Depo Yeri", "Yemek", "Tarih"]
            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col_idx, value=h)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            start_row = 5
            for idx, k in enumerate(islenmis_sepet):
                r = start_row + idx
                ws.cell(row=r, column=1, value=k["Malzeme"])
                ws.cell(row=r, column=2, value=k["Kategori"])
                ws.cell(row=r, column=3, value=k["Birim"])
                ws.cell(row=r, column=4, value=k["Miktar"])
                ws.cell(row=r, column=5, value=k["Birim Maliyet"])
                ws.cell(row=r, column=6, value=f"=D{r}*E{r}")
                ws.cell(row=r, column=7, value=k["Depo"])
                ws.cell(row=r, column=8, value=yemek_adi)
                ws.cell(row=r, column=9, value=str(datetime.date.today()))

                for col_idx in range(1, 10):
                    c = ws.cell(row=r, column=col_idx)
                    c.font = regular_font
                    c.border = thin_border
                    if col_idx in [3, 9]: c.alignment = Alignment(horizontal="center")
                    elif col_idx in [4, 5, 6]:
                        c.alignment = Alignment(horizontal="right")
                        if col_idx in [5, 6]: c.number_format = '#,##0.00 "₺"'

            last_data_row = start_row + len(islenmis_sepet) - 1
            tot_row = last_data_row + 1

            ws.cell(row=tot_row, column=1, value="TOPLAM MALİYET").font = bold_font
            for col_idx in range(1, 10):
                c = ws.cell(row=tot_row, column=col_idx)
                c.border = total_border
                c.fill = summary_fill
                if col_idx == 6:
                    c.value = f"=SUM(F{start_row}:F{last_data_row})"
                    c.font = bold_font
                    c.number_format = '#,##0.00 "₺"'
                    c.alignment = Alignment(horizontal="right")

            kisi_sayisi_row = tot_row + 2
            kisi_basi_row = tot_row + 3

            ws.cell(row=kisi_sayisi_row, column=1, value="Toplam Yararlanan Kişi Sayısı").font = bold_font
            ws.cell(row=kisi_sayisi_row, column=2, value=kisi_sayisi).font = bold_font
            ws.cell(row=kisi_sayisi_row, column=2).number_format = '#,##0'
            ws.cell(row=kisi_sayisi_row, column=2).alignment = Alignment(horizontal="right")

            ws.cell(row=kisi_basi_row, column=1, value="Kişi Başı Maliyet").font = bold_font
            ws.cell(row=kisi_basi_row, column=2, value=f"=F{tot_row}/B{kisi_sayisi_row}").font = bold_font
            ws.cell(row=kisi_basi_row, column=2).number_format = '#,##0.00 "₺"'
            ws.cell(row=kisi_basi_row, column=2).alignment = Alignment(horizontal="right")

            for r_idx in [kisi_sayisi_row, kisi_basi_row]:
                for c_idx in range(1, 3):
                    ws.cell(row=r_idx, column=c_idx).border = thin_border
                    ws.cell(row=r_idx, column=c_idx).fill = summary_fill

            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row > 2 and cell.value:
                        val_str = str(cell.value)
                        if len(val_str) > max_len: max_len = len(val_str)
                    ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            rapor_adi = "asevi_gunluk_maliyet_raporu.xlsx"
            wb.save(rapor_adi)
            st.success("Üretim kaydedildi, stoktan düşüldü ve rapor hazırlandı!")
            st.session_state.sepet = []
