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

    Boş kayıtlı hash hiçbir zaman geçerli sayılmaz; misafir hesabı da uygulama
    tarafından özel olarak ele alınmalı, boş hash ile doğrulanmamalıdır.
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


def giris_sayaclarini_sifirla(kayitlar, anahtarlar):
    """Belirtilen giriş denemesi sayaçlarını korunan diğer kayıtları değiştirmeden siler."""
    sifirlanan = dict(kayitlar)
    for anahtar in anahtarlar:
        sifirlanan.pop(anahtar, None)
    return sifirlanan


def fire_partisi_etiketi(giris):
    """Fire seçicisinde stok girişini ürün, fatura ve kalan miktarla ayırt eder."""
    return (
        f"{str(giris.get('urun', '')).strip().upper()} | "
        f"Fatura: {giris.get('fatura_no') or 'BELİRTİLMEMİŞ'} | "
        f"Kalan: {giris.get('kalan', 0)} {giris.get('birim', '')} | "
        f"Tarih: {giris.get('tarih', '-')} | Kayıt: {giris.get('id', '-')}"
    )


def fire_partisi_detayi(giris, miktar):
    """Seçilen stok girişinin fatura ve birim fiyat bilgileriyle fire tutarını hesaplar."""
    if not isinstance(giris, dict):
        raise ValueError("Seçilen stok giriş kaydı geçersiz.")
    try:
        miktar = float(miktar)
        kalan = float(giris.get("kalan", 0) or 0)
    except (TypeError, ValueError) as hata:
        raise ValueError("Fire miktarı veya kalan stok sayısal değil.") from hata
    if miktar <= 0:
        raise ValueError("Fire miktarı 0'dan büyük olmalıdır.")
    if miktar > kalan:
        raise ValueError("Fire miktarı seçilen fatura kaydındaki stoktan büyük olamaz.")

    birim_fiyat = giris.get("birim_fiyat")
    try:
        if birim_fiyat in (None, ""):
            giris_miktari = float(giris.get("miktar", 0) or 0)
            toplam_fiyat = float(giris.get("fiyat", 0) or 0)
            birim_fiyat = toplam_fiyat / giris_miktari if giris_miktari > 0 else toplam_fiyat
        else:
            birim_fiyat = float(birim_fiyat)
    except (TypeError, ValueError) as hata:
        raise ValueError("Seçilen fatura kaydının birim fiyatı geçersiz.") from hata

    return {
        "giris_id": str(giris.get("id", "")),
        "fatura_no": str(giris.get("fatura_no") or "BELİRTİLMEMİŞ"),
        "miktar": miktar,
        "birim_fiyat": birim_fiyat,
        "tutar": miktar * birim_fiyat,
    }


def qr_paket_kalanini_hesapla(giris, sepet, paket_id):
    """QR paketin mevcut kalanından bu üretim sepetinde planlanan miktarı düşer."""
    try:
        paket_miktari = float(giris.get("paket_miktari", 0) or 0)
        durumlar = giris.get("paket_durumlari", {})
        if not isinstance(durumlar, dict):
            durumlar = {}
        kalan = float(durumlar.get(paket_id, paket_miktari) or 0)
        for item in sepet:
            if (
                item.get("paket_id") == paket_id
                and str(item.get("fatura_id")) == str(giris.get("id"))
            ):
                kalan -= float(item.get("miktar", 0) or 0)
    except (AttributeError, TypeError, ValueError) as hata:
        raise ValueError("QR paket miktar bilgisi geçersiz.") from hata
    return max(0.0, kalan)


def qr_acik_paketleri_bul(girisler, sepet, urun):
    """Ürünün kayıtlı veya mevcut üretim sepetinde açılmış paketlerini bulur."""
    aranan_urun = str(urun or "").strip().upper()
    acik_paketler = []
    for giris in girisler:
        if str(giris.get("urun", "")).strip().upper() != aranan_urun:
            continue
        try:
            paket_miktari = float(giris.get("paket_miktari", 0) or 0)
            durumlar = giris.get("paket_durumlari", {})
            if not isinstance(durumlar, dict):
                durumlar = {}
            paket_idleri = set(durumlar)
            paket_idleri.update(
                item.get("paket_id")
                for item in sepet
                if item.get("paket_id")
                and str(item.get("fatura_id")) == str(giris.get("id"))
            )
        except (AttributeError, TypeError, ValueError) as hata:
            raise ValueError("QR paket durum bilgisi geçersiz.") from hata
        if paket_miktari <= 0:
            continue

        for paket_id in sorted(paket_idleri, key=str):
            kalan = qr_paket_kalanini_hesapla(giris, sepet, paket_id)
            if 0 < kalan < paket_miktari:
                acik_paketler.append({
                    "paket_id": paket_id,
                    "fatura_id": giris.get("id"),
                    "kalan": kalan,
                    "birim": giris.get("birim", ""),
                })
    return acik_paketler


def qr_paket_secim_engeli(girisler, sepet, urun, secilen_paket_id):
    """Açık paket varken önce onu bitirmeyi zorunlu kılar."""
    acik_paketler = qr_acik_paketleri_bul(girisler, sepet, urun)
    if acik_paketler and acik_paketler[0]["paket_id"] != secilen_paket_id:
        return acik_paketler[0]
    return None


RAPOR_VERI_ANAHTARLARI = (
    "girisler",
    "kullanim_loglari",
    "silinen_urun_loglari",
    "yemek_uretim_arsivi",
    "personel_izinleri",
)
RAPOR_YENIDEN_DENEME_SANIYE = 15 * 60
RAPOR_GONDERIM_KILIT_SANIYE = 10 * 60


def rapor_verilerini_oku(oku_fn):
    """Rapor için gerekli listeleri okur; eksik veya hatalı okumada raporu durdurur."""
    veriler = {}
    for anahtar in RAPOR_VERI_ANAHTARLARI:
        durum, veri = oku_fn(anahtar)
        if durum == "hata":
            raise RuntimeError(f"'{anahtar}' okunamadı: {veri}")
        if durum == "yok":
            veriler[anahtar] = []
        elif durum == "ok" and isinstance(veri, list):
            if not all(isinstance(kayit, dict) for kayit in veri):
                raise ValueError(f"'{anahtar}' kayıtları nesne biçiminde değil.")
            veriler[anahtar] = veri
        elif durum == "ok":
            raise ValueError(f"'{anahtar}' verisi liste biçiminde değil.")
        else:
            raise ValueError(f"'{anahtar}' için geçersiz okuma durumu: {durum}")
    return veriler


def rapor_mail_durumunu_guncelle(
    kayitlar,
    rapor_tipi,
    donem,
    simdi,
    islem,
    claim_id=None,
    kilit_saniye=RAPOR_GONDERIM_KILIT_SANIYE,
    yeniden_deneme_saniye=RAPOR_YENIDEN_DENEME_SANIYE,
):
    """Otomatik rapor e-postası için atomik güncelleme fonksiyonunun saf durum geçişi."""
    yeni = dict(kayitlar) if isinstance(kayitlar, dict) else {}
    durumlar = yeni.get("_rapor_durum")
    durumlar = dict(durumlar) if isinstance(durumlar, dict) else {}
    mevcut_durum = durumlar.get(rapor_tipi)
    ayni_donem = yeni.get(rapor_tipi) == donem

    if islem == "sahiplen":
        if not claim_id:
            raise ValueError("Rapor sahiplenme anahtarı gereklidir.")
        if ayni_donem:
            if not isinstance(mevcut_durum, dict) or mevcut_durum.get("donem") != donem:
                return yeni, False
            durum = mevcut_durum.get("durum")
            if durum == "gonderildi":
                return yeni, False
            if durum == "gonderiliyor":
                kilit_sonu = mevcut_durum.get("kilit_sonu")
                if not isinstance(kilit_sonu, (int, float)) or simdi < kilit_sonu:
                    return yeni, False
            if durum == "basarisiz":
                yeniden_deneme = mevcut_durum.get("yeniden_deneme")
                if (
                    not isinstance(yeniden_deneme, (int, float))
                    or simdi < yeniden_deneme
                ):
                    return yeni, False
            if durum not in ("gonderiliyor", "basarisiz"):
                return yeni, False

        yeni[rapor_tipi] = donem
        durumlar[rapor_tipi] = {
            "donem": donem,
            "durum": "gonderiliyor",
            "claim_id": claim_id,
            "kilit_sonu": simdi + kilit_saniye,
        }
    elif islem in ("tamamlandi", "basarisiz"):
        if (
            not isinstance(mevcut_durum, dict)
            or mevcut_durum.get("donem") != donem
            or mevcut_durum.get("durum") != "gonderiliyor"
            or mevcut_durum.get("claim_id") != claim_id
        ):
            return yeni, False
        if islem == "tamamlandi":
            durumlar[rapor_tipi] = {"donem": donem, "durum": "gonderildi"}
        else:
            durumlar[rapor_tipi] = {
                "donem": donem,
                "durum": "basarisiz",
                "yeniden_deneme": simdi + yeniden_deneme_saniye,
            }
    else:
        raise ValueError(f"Geçersiz rapor işlemi: {islem}")

    yeni["_rapor_durum"] = durumlar
    return yeni, True


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
