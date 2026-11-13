"""
Aziziye Aşevi - Çekirdek Fonksiyonlar İçin Kritik Testler
"""
import os
import pytest

# Testler başlamadan önce ortam değişkenine geçerli bir Fernet anahtarı veriyoruz
from cryptography.fernet import Fernet
os.environ["FERNET_KEY"] = Fernet.generate_key().decode("utf-8")

# Artık cekirdek modülünü güvenle import edebiliriz
from cekirdek import (
    metni_sifrele, metni_coz, SifrelemeHatasi,
    sifre_hashle_yeni, sifre_dogrula, sifre_politika_hatasi,
    _veri_hash, yeni_id_uret, idleri_benzersiz_yap
)

# ==========================================
# 1. Şifreleme ve Çözme (T.C. / Telefon / Adres)
# ==========================================
def test_sifreleme_ve_cozme():
    metin = "12345678901" # T.C. No
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
    veri2 = {"ad": "Test", "id": 1} # Sıra farklı ama içerik aynı
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
    assert len(idler) == len(set(idler)) # Hepsi benzersiz mi?
    assert idler == ["IHT-001", "IHT-004", "IHT-003"] # Mükerrer olan en son ID'yi almalı
