"""Default records and UI configuration used during first-run initialization."""

# KVKK ve güvenlik gereği koda gömülü PII (Kişisel Veri) bırakılmamıştır.
varsayilan_personeller = []

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {"tarih": "2026-04-23", "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı"},
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {"tarih": "2026-05-19", "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı"},
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"},
]

varsayilan_depolar = [
    "Soğuk Hava Deposu +5/+6",
    "Soğuk Hava Deposu -18",
    "Sebze Deposu",
    "Kuru Gıda Deposu",
]

varsayilan_demirbaslar = [
    {
        "id": "DEM-001",
        "ad": "Endüstriyel Çorba Kazanı",
        "kategori": "Mutfak Ekipmanı",
        "adet": 2,
        "durum": "Sağlam",
        "zimmet": "Aşçıbaşı",
        "tarih": "2026-01-15",
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
