from src.dashboard_utils import dashboard_ozet_hesapla


def test_dashboard_stok_degeri_yeni_eski_kalan_kayitlari_kullanir():
    girisler = [
        {
            "urun": "UN",
            "kategori": "KURU GIDA",
            "depo": "Merkez",
            "kalan": 10,
            "miktar": 20,
            "birim_fiyat": 8,
            "fiyat": 160,
        },
        {
            "urun": "ISPANAK",
            "kategori": "SEBZE",
            "depo": "Merkez",
            "kalan": 4,
            "miktar": 4,
            "fiyat": 25,
        },
        {
            "urun": "BITMIS",
            "kategori": "SEBZE",
            "depo": "Yedek",
            "kalan": 0,
            "birim_fiyat": 999,
            "fiyat": 999,
        },
    ]

    ozet = dashboard_ozet_hesapla(girisler, [], [], ["Merkez", "Yedek"])

    assert ozet["toplam_stok_degeri"] == 180
    assert ozet["gida_toplam"] == 80
    assert ozet["sebze_toplam"] == 100
    assert ozet["depo_doluluk"]["Merkez"] == 100
    assert ozet["depo_doluluk"]["Yedek"] == 0
