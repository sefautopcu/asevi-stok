"""
Aziziye Aşevi - Çekirdek Yardımcı Fonksiyonlar
================================================
Bu modül Streamlit'ten BAĞIMSIZDIR. Sadece Python standart kütüphanesi
ve `cryptography` kullanır. Test edilebilir olması için app.py'den ayrıldı.
"""
import hashlib
import hmac
import json
import re
import secrets

from cryptography.fernet import Fernet


# =========================================================================
# FERNET ŞİFRELEME MOTORU
# =========================================================================
class SifrelemeHatasi(RuntimeError):
    """Fernet şifreleme başarısız olduğunda fırlatılır. Düz metin kaydını engeller."""


def _fernet_motoru_kur():
    """
    FERNET_KEY'i ortamdan (test ve CI için) veya Streamlit secrets'tan okur.
    """
    import os
    # 1. Önce ortam değişkenine bak (pytest için)
    anahtar = os.environ.get("FERNET_KEY", "")
    
    # 2. Ortam değişkeninde yoksa Streamlit secrets'a bak
    if not anahtar:
        try:
            import streamlit as st
            # Streamlit secrets'tan okumayı dene
            if "FERNET_KEY" in st.secrets:
                anahtar = str(st.secrets["FERNET_KEY"])
        except Exception:
            pass
            
    if not anahtar:
        return None
    try:
        return Fernet(anahtar.encode("utf-8"))
    except Exception:
        return None


# Modül yüklenirken motoru kurmayı DENER; başarısızsa None kalır.
# app.py'de FERNET_KEY kontrolü zaten yapılıyor; testler ortam değişkeni ile verir.
fernet_motoru = _fernet_motoru_kur()


def metni_sifrele(duz_metin):
    if not duz_metin:
        return ""
    # Zaten şifreli (Fernet) gelen değer tekrar şifrelenmez.
    if str(duz_metin).startswith("gAAAAA"):
        return str(duz_metin)
    if fernet_motoru is None:
        raise SifrelemeHatasi(
            "FERNET_KEY tanımlı değil; şifreleme yapılamadı."
        )
    try:
        return fernet_motoru.encrypt(str(duz_metin).encode("utf-8")).decode("utf-8")
    except Exception as e:
        raise SifrelemeHatasi(
            f"Şifreleme başarısız oldu ({type(e).__name__}); veri kaydedilmedi."
        ) from e


def metni_coz(sifreli_metin):
    if not sifreli_metin:
        return ""
    try:
        if not str(sifreli_metin).startswith("gAAAAA"):
            return str(sifreli_metin)
        if fernet_motoru is None:
            return str(sifreli_metin)
        return fernet_motoru.decrypt(str(sifreli_metin).encode("utf-8")).decode("utf-8")
    except Exception:
        return str(sifreli_metin)


# =========================================================================
# ŞİFRE HASHLEME (scrypt + eski SHA-256 uyumu)
# =========================================================================
def sifre_hashle(sifre):
    """ESKİ yöntem (tuzsuz SHA-256). Yalnızca eski kayıtları doğrulamak için tutulur."""
    if not sifre:
        return ""
    return hashlib.sha256(str(sifre).encode("utf-8")).hexdigest()


# Eski sürümlerde kodda açıkça yazılı olan varsayılan şifrelerin SHA-256 hash'leri.
# Bu hash'lerle kayıtlı hesaplar ilk girişte şifre değiştirmeye zorlanır.
ESKI_VARSAYILAN_HASHLER = {
    "8110e127a1ea6d6e6b10122673400c15d112802259aeb48783b7ae3c795937c4",
    "f6595d11049c9b69670c7ce640632b5131e93032aad76a5796bfc4506c6afd65",
    "eeed6b32b495d07ee61434679ddd7640024cb7b0a7d53561bf847b11b2405a56",
}

_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024


def sifre_hashle_yeni(sifre):
    """Her şifre için rastgele tuzlu, yavaş (scrypt) hash üretir: s1$tuz$hash"""
    tuz = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        str(sifre).encode("utf-8"), salt=tuz, n=_SCRYPT_N, r=_SCRYPT_R,
        p=_SCRYPT_P, dklen=32, maxmem=_SCRYPT_MAXMEM,
    )
    return f"s1${tuz.hex()}${dk.hex()}"


def sifre_dogrula(girilen, kayitli):
    """
    Hem yeni (scrypt) hem eski (SHA-256) kayıtları sabit zamanlı karşılaştırır.

    GÜVENLİK NOTU (Adım 3'te düzeltilecek bug):
    Boş `kayitli` değeri şu an sadece `girilen == ""` ise True döner.
    Bu, boş şifreli bir hesap varsa (misafir hariç) giriş açığı yaratır.
    Adım 3'te bu davranış düzeltilecek; şimdilik mevcut davranış korunuyor
    ki testler mevcut davranışı doğrulasın.
    """
    girilen = str(girilen or "")
    kayitli = str(kayitli or "")
    if kayitli == "":
        return False
    if kayitli.startswith("s1$"):
        try:
            _, tuz_hex, hash_hex = kayitli.split("$")
            dk = hashlib.scrypt(
                girilen.encode("utf-8"), salt=bytes.fromhex(tuz_hex), n=_SCRYPT_N,
                r=_SCRYPT_R, p=_SCRYPT_P, dklen=32, maxmem=_SCRYPT_MAXMEM,
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False
    return hmac.compare_digest(sifre_hashle(girilen), kayitli)


def sifre_yukseltilmeli_mi(kayitli):
    """Kayıtlı hash eski biçimdeyse (SHA-256) True döner."""
    return bool(kayitli) and not str(kayitli).startswith("s1$")


def sifre_politika_hatasi(sifre):
    """Şifre kurallara uymuyorsa hata metni, uyuyorsa None döner."""
    sifre = str(sifre or "")
    if len(sifre) < 10:
        return "Şifre en az 10 karakter olmalıdır."
    if not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", sifre) or not re.search(r"\d", sifre):
        return "Şifre en az bir harf ve en az bir rakam içermelidir."
    return None


# =========================================================================
# VERİ HASH'İ (çakışma denetimi için)
# =========================================================================
def _veri_hash(veri):
    return hashlib.sha256(
        json.dumps(veri, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


# =========================================================================
# ID ÜRETİMİ
# =========================================================================
def yeni_id_uret(onek, liste, genislik=3, anahtar="id"):
    """Mevcut en büyük numaranın bir fazlasını üretir (kayıt silinse bile kimlik tekrarlanmaz)."""
    en_buyuk = 0
    for oge in liste:
        m = re.search(r"(\d+)$", str(oge.get(anahtar, "")))
        if m:
            en_buyuk = max(en_buyuk, int(m.group(1)))
    return f"{onek}{en_buyuk + 1:0{genislik}d}"


def idleri_benzersiz_yap(liste, onek, genislik=3, anahtar="id"):
    """Eski sürümlerde (kayıt sayısına göre üretildiği için) tekrarlanmış kimlikleri düzeltir."""
    sayac = 0
    for oge in liste:
        m = re.search(r"(\d+)$", str(oge.get(anahtar, "")))
        if m:
            sayac = max(sayac, int(m.group(1)))
    gorulen = set()
    for oge in liste:
        kid = oge.get(anahtar)
        if not kid or kid in gorulen:
            sayac += 1
            kid = f"{onek}{sayac:0{genislik}d}"
            oge[anahtar] = kid
        gorulen.add(kid)
    return liste
