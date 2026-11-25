"""Food-energy lookup and calculation helpers for the kitchen workflow."""

import re

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
    # --- EKLENEN MEYVELER (100 Gram Başına Kalori) ---
    "MANDALİNA": 53,
    "MANDALINA": 53,
    "ELMA": 52,
    "MUZ": 89,
    "PORTAKAL": 47,
    "KARPUZ": 30,
    "KAVUN": 34,
    "ÜZÜM": 69,
    "ÇİLEK": 32,
    "KİVİ": 61,
    "AYVA": 57,
    "NAR": 83,
    "İNCİR": 74,
    "KAYISI": 48,
    "ŞEFTALİ": 39,
    "ERİK": 46,
    "VİŞNE": 50,
    "KİRAZ": 63,
    "LİMON": 29,
    "GREYFURT": 42,
}


def urun_kalori_hesapla(urun_adi, miktar, birim):
    """Return the existing approximate calorie calculation for a product amount."""
    urun_upper = urun_adi.upper()
    birim_kalori = 100  # Tabloda olmayan ürünler için varsayılan 100 kcal/100g
    
    for urun, kalori in sorted(
        KALORI_TABLOSU.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if re.search(rf"(?<!\w){re.escape(urun)}(?!\w)", urun_upper):
            birim_kalori = kalori
            break

    birim_str = str(birim).strip().upper()
    
    # Birim bazlı hesaplama (Tablo 100 gram/ml üzerinden hazırlanmıştır)
    if birim_str in ["KG", "LT", "LİTRE", "KİLOGRAM"]:
        # 1 Kg = 10 x 100 gram
        return miktar * 10 * birim_kalori
    elif birim_str in ["GR", "G", "ML", "MİLİLİTRE"]:
        # Gram cinsinden hesaplama (Miktar / 100 * Kalori)
        return (miktar / 100.0) * birim_kalori
    else:
        # Adet, Paket vb. için (Eski sistemdeki gibi 1 adet = 100 gram varsayımı)
        return miktar * birim_kalori
