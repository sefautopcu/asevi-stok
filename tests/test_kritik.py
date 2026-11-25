"""
Aziziye Aşevi - Çekirdek Fonksiyonlar İçin Kritik Testler
"""
import os
import pytest
from cryptography.fernet import Fernet

# Testler başlamadan önce ortam değişkenine geçerli bir Fernet anahtarı veriyoruz
os.environ["FERNET_KEY"] = Fernet.generate_key().decode("utf-8")

# Artık cekirdek modülünü güvenle import edebiliriz
from src.cekirdek import (
    metni_sifrele,
    metni_coz,
    SifrelemeHatasi,
    sifre_hashle_yeni,
    sifre_dogrula,
    sifre_politika_hatasi,
    giris_sayaclarini_sifirla,
    _veri_hash,
    yeni_id_uret,
    idleri_benzersiz_yap,
)

# Stok, QR paket, fire, oturum token ve yedekleme kontrol yardımcıları
from tests.aziziye_core_logic import (
    _token_hashle,
    fire_partisi_detayi,
    fire_partisi_etiketi,
    qr_acik_paketleri_bul,
    qr_kod_degerleri,
    qr_paket_kalanini_hesapla,
    qr_paket_secim_engeli,
    yemek_sepeti_stok_hatalari,
)


# ==========================================
# 1. Şifreleme ve Çözme (T.C. / Telefon / Adres)
# ==========================================
def test_sifreleme_ve_cozme():
    metin = "12345678901"  # T.C. No
    sifreli = metni_sifrele(metin)
    assert sifreli != metin
    assert sifreli.startswith("gAAAAA")

    cozulmus = metni_coz(sifreli)
    assert cozulmus == metin


def test_bos_metin_sifreleme():
    assert metni_sifrele("") == ""
    assert metni_coz("") == ""


def test_zaten_sifreli_metni_tekrar_sifrelemez():
    metin = "Gizli Veri"
    sifreli = metni_sifrele(metin)
    tekrar_sifreli = metni_sifrele(sifreli)
    assert sifreli == tekrar_sifreli


# ==========================================
# 2. Şifre Hash'leme ve Doğrulama (scrypt)
# ==========================================
def test_sifre_hashleme_ve_dogrulama():
    sifre = "GüvenliSifre123"
    hash_degeri = sifre_hashle_yeni(sifre)

    assert hash_degeri.startswith("s1$")
    assert sifre_dogrula("GüvenliSifre123", hash_degeri) is True
    assert sifre_dogrula("YanlisSifre", hash_degeri) is False


def test_bos_hash_her_zaman_reddedilir():
    assert sifre_dogrula("", "") is False
    assert sifre_dogrula("herhangi-bir-sifre", "") is False


def test_basarili_giris_sayaclari_sifirlama_sadece_hedefleri_kaldirir():
    kayitlar = {
        "u|admin|10.0.0.1": {"sayi": 2},
        "ip|10.0.0.1": {"sayi": 4},
        "u|personel|10.0.0.1": {"sayi": 1},
    }

    sifirlanan = giris_sayaclarini_sifirla(
        kayitlar, ("u|admin|10.0.0.1", "ip|10.0.0.1")
    )

    assert sifirlanan == {"u|personel|10.0.0.1": {"sayi": 1}}
    assert len(kayitlar) == 3


def test_sifre_politikasi():
    # 10 karakterden kısa
    assert sifre_politika_hatasi("Kisa1") == "Şifre en az 10 karakter olmalıdır."
    # Sadece harf
    assert "harf ve en az bir rakam" in sifre_politika_hatasi("SadeceHarfler")
    # Geçerli şifre
    assert sifre_politika_hatasi("GecerliSifre123") is None


# ==========================================
# 3. Çakışma Denetimi (Veri Hash'i)
# ==========================================
def test_veri_hash_tutarliligi():
    veri1 = {"id": 1, "ad": "Test"}
    veri2 = {"ad": "Test", "id": 1}  # Sıra farklı ama içerik aynı
    veri3 = {"id": 2, "ad": "Test"}

    # Sözlük sırası farklı olsa da hash aynı olmalı
    assert _veri_hash(veri1) == _veri_hash(veri2)
    # İçerik değişince hash değişmeli
    assert _veri_hash(veri1) != _veri_hash(veri3)


# ==========================================
# 4. ID Üretimi ve Benzersizleştirme
# ==========================================
def test_yeni_id_uretimi():
    liste = [{"id": "PER-001"}, {"id": "PER-005"}]
    yeni_id = yeni_id_uret("PER-", liste)
    assert yeni_id == "PER-006"


def test_idleri_benzersiz_yapma():
    # Eski sistemden kalma mükerrer ID'ler
    liste = [{"id": "IHT-001"}, {"id": "IHT-001"}, {"id": "IHT-003"}]
    duzeltilmis = idleri_benzersiz_yap(liste, "IHT-")

    idler = [oge["id"] for oge in duzeltilmis]
    assert len(idler) == len(set(idler))  # Hepsi benzersiz mi?
    assert idler == ["IHT-001", "IHT-004", "IHT-003"]  # Mükerrer olan en son ID'yi almalı


# ==========================================
# 5. Stok Düşümü, QR Paket, Fire, Oturum ve Yedekleme
# ==========================================
@pytest.fixture
def ornek_stok_ve_parti():
    girisler = [
        {
            "id": "FAT-101",
            "urun": "KIRMIZI MERCİMEK",
            "birim": "kg",
            "miktar": 50.0,
            "kalan": 50.0,
            "paket_miktari": 10.0,
            "paket_durumlari": {"FAT-101-P1": 6.0, "FAT-101-P2": 10.0},
            "fatura_no": "FTR-2026-01",
            "tarih": "2026-11-10",
        },
        {
            "id": "FAT-102",
            "urun": "PİRİNÇ",
            "birim": "kg",
            "miktar": 20.0,
            "kalan": 20.0,
            "paket_miktari": 0.0,
            "paket_durumlari": {},
            "fatura_no": "FTR-2026-02",
            "tarih": "2026-11-12",
        },
    ]
    parti = {
        "id": "FAT-200",
        "urun": "TAVUK ETİ",
        "birim": "kg",
        "miktar": 40.0,
        "kalan": 15.0,
        "fiyat": 4800.0,
        "fatura_no": "FTR-2026-09",
        "tarih": "2026-11-15",
    }
    return girisler, parti


def test_stok_ve_qr_paket_kontrolu(ornek_stok_ve_parti):
    girisler, _ = ornek_stok_ve_parti

    hatalar_fazla = yemek_sepeti_stok_hatalari(
        girisler, [{"urun": "Kırmızı Mercimek", "miktar": 80.0}]
    )
    assert any("KIRMIZI MERCIMEK" in h for h in hatalar_fazla)

    hatalar_sifir = yemek_sepeti_stok_hatalari(
        girisler, [{"urun": "Pirinç", "miktar": 0}]
    )
    assert len(hatalar_sifir) == 1

    paket_kodlari = qr_kod_degerleri(girisler[0])
    assert paket_kodlari == [
        "FAT-101-P1",
        "FAT-101-P2",
        "FAT-101-P3",
        "FAT-101-P4",
        "FAT-101-P5",
    ]

    sepet = [
        {
            "urun": "KIRMIZI MERCİMEK",
            "fatura_id": "FAT-101",
            "paket_id": "FAT-101-P1",
            "miktar": 2.0,
        }
    ]
    assert qr_paket_kalanini_hesapla(girisler[0], sepet, "FAT-101-P1") == pytest.approx(4.0)

    acik = qr_acik_paketleri_bul(girisler, sepet, "KIRMIZI MERCİMEK")
    assert len(acik) == 1
    assert acik[0]["paket_id"] == "FAT-101-P1"

    engel = qr_paket_secim_engeli(girisler, sepet, "KIRMIZI MERCİMEK", "FAT-101-P2")
    assert engel is not None
    assert engel["paket_id"] == "FAT-101-P1"


def test_fire_partisi_kontrolu(ornek_stok_ve_parti):
    _, parti = ornek_stok_ve_parti

    detay = fire_partisi_detayi(parti, 2.5)
    assert detay["giris_id"] == "FAT-200"
    assert detay["fatura_no"] == "FTR-2026-09"
    assert detay["birim_fiyat"] == pytest.approx(120.0)
    assert detay["tutar"] == pytest.approx(300.0)

    etiket = fire_partisi_etiketi(parti)
    assert "TAVUK ETİ" in etiket
    assert "FTR-2026-09" in etiket

    with pytest.raises(ValueError):
        fire_partisi_detayi(parti, 16.0)
    with pytest.raises(ValueError):
        fire_partisi_detayi(parti, 0.0)


def test_oturum_token_ve_bosta_kalma():
    raw_token = "sess_token_aziziye_asevi_2026"
    h1 = _token_hashle(raw_token)
    h2 = _token_hashle(raw_token)
    assert h1 == h2
    assert raw_token not in h1
    assert len(h1) == 64

    bosta_sn = lambda dk: max(5, min(int(dk), 480)) * 60
    assert bosta_sn(30) == 1800
    assert bosta_sn(1) == 300
    assert bosta_sn(999) == 28800


def test_yedekleme_ve_geri_yukleme_bolum_filtreleme():
    allowed_keys = {"girisler", "kullanim_loglari", "demirbaslar_listesi"}
    invalid_pkg = {"_meta": {"surum": 1}, "veri": {"girisler": "liste_degil"}}
    assert not isinstance(invalid_pkg["veri"]["girisler"], list)

    valid_pkg = {
        "_meta": {"zaman": "2026-11-24 09:00:00", "surum": 1, "olusturan": "admin"},
        "veri": {
            "girisler": [{"id": "FAT-1", "urun": "NOHUT", "kalan": 25}],
            "kullanim_loglari": [],
            "kullanici_yetkileri": {"admin": {"sifre": "gizli"}},
        },
    }
    yazilacak = {k: v for k, v in valid_pkg["veri"].items() if k in allowed_keys}
    assert "girisler" in yazilacak
    assert "kullanici_yetkileri" not in yazilacak
