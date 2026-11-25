import datetime
import hashlib
import math
from decimal import Decimal, InvalidOperation


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

def qr_kod_degerleri(giris):
    """Stok girişindeki her paket için ayrı QR değeri, dökme stok için tek ID üretir."""
    giris_id = str(giris.get("id", "")).strip()
    if not giris_id:
        raise ValueError("Stok giriş kaydının ID bilgisi bulunamadı.")
    try:
        toplam_miktar = Decimal(str(giris.get("miktar", 0) or 0))
        paket_miktari = Decimal(str(giris.get("paket_miktari", 0) or 0))
    except (InvalidOperation, ValueError) as hata:
        raise ValueError("Stok veya paket miktarı geçersiz.") from hata
    if not toplam_miktar.is_finite() or not paket_miktari.is_finite():
        raise ValueError("Stok veya paket miktarı sonlu bir sayı olmalıdır.")
    if toplam_miktar < 0 or paket_miktari < 0:
        raise ValueError("Stok veya paket miktarı negatif olamaz.")
    if toplam_miktar == 0:
        return []
    if paket_miktari == 0:
        return [giris_id]

    paket_sayisi = int(toplam_miktar // paket_miktari)
    return [f"{giris_id}-P{sira}" for sira in range(1, paket_sayisi + 1)]

def yemek_sepeti_stok_hatalari(girisler, sepet):
    """Üretim sepetindeki tüm miktarların mevcut stoktan karşılanabildiğini doğrular."""
    stoklar = {}
    for giris in girisler:
        urun = str(giris.get("urun", "")).strip().upper()
        if not urun:
            continue
        try:
            kalan = float(giris.get("kalan", 0) or 0)
        except (TypeError, ValueError) as hata:
            raise ValueError(f"{urun} stok miktarı sayısal değil.") from hata
        if not math.isfinite(kalan):
            raise ValueError(f"{urun} stok miktarı geçersiz.")
        if kalan < 0:
            raise ValueError(f"{urun} stok miktarı negatif olamaz.")
        kayit_id = str(giris.get("id", ""))
        stoklar[kayit_id] = kalan

    paket_kalanlari = {}
    hatalar = []
    for sira, item in enumerate(sepet, start=1):
        urun = str(item.get("urun", "")).strip().upper()
        try:
            istenen = float(item.get("miktar", 0) or 0)
        except (TypeError, ValueError) as hata:
            raise ValueError(f"{urun or sira} için sepet miktarı sayısal değil.") from hata
        if not math.isfinite(istenen):
            raise ValueError(f"{urun or sira} için sepet miktarı geçersiz.")
        if not urun or istenen <= 0:
            hatalar.append(f"{urun or 'Malzeme'} için miktar 0'dan büyük olmalıdır.")
            continue

        paket_id = item.get("paket_id")
        fatura_id = str(item.get("fatura_id", "")) if item.get("fatura_id") else None
        uygun_kayitlar = [
            g for g in girisler
            if str(g.get("urun", "")).strip().upper() == urun
            and stoklar.get(str(g.get("id", "")), 0) > 0
            and (not fatura_id or str(g.get("id", "")) == fatura_id)
        ]
        kalan_dusulecek = istenen
        for giris in uygun_kayitlar:
            kayit_id = str(giris.get("id", ""))
            if paket_id:
                try:
                    durumlar = giris.get("paket_durumlari", {})
                    if not isinstance(durumlar, dict):
                        durumlar = {}
                    paket_miktari = float(giris.get("paket_miktari", 0) or 0)
                    paket_kalan = paket_kalanlari.get(
                        (kayit_id, str(paket_id)),
                        float(durumlar.get(
                            paket_id, paket_miktari
                        ) or 0),
                    )
                except (TypeError, ValueError) as hata:
                    raise ValueError(f"{urun} paket stok bilgisi geçersiz.") from hata
                if not math.isfinite(paket_kalan) or not math.isfinite(paket_miktari):
                    raise ValueError(f"{urun} paket stok bilgisi geçersiz.")
                dusulecek = min(kalan_dusulecek, paket_kalan, stoklar[kayit_id])
                paket_kalanlari[(kayit_id, str(paket_id))] = paket_kalan - dusulecek
            else:
                dusulecek = min(kalan_dusulecek, stoklar[kayit_id])

            stoklar[kayit_id] -= dusulecek
            kalan_dusulecek -= dusulecek
            if kalan_dusulecek <= 1e-9:
                break

        if kalan_dusulecek > 1e-9:
            toplam_istenen = 0.0
            for baska in sepet:
                if str(baska.get("urun", "")).strip().upper() != urun:
                    continue
                try:
                    baska_miktar = float(baska.get("miktar", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(baska_miktar):
                    toplam_istenen += baska_miktar
            toplam_kalan = sum(
                float(g.get("kalan", 0) or 0)
                for g in girisler
                if str(g.get("urun", "")).strip().upper() == urun
            )
            mesaj = (
                f"{urun}: sepette toplam istenen miktar ({toplam_istenen:g}), "
                f"mevcut stoktan karşılanamıyor (stok: {toplam_kalan:g})."
            )
            if paket_id:
                mesaj = (
                    f"{urun} ({paket_id}): bu fatura/paket kaydında "
                    f"istenen miktarın tamamı mevcut değil."
                )
            if mesaj not in hatalar:
                hatalar.append(mesaj)

    return hatalar

def _token_hashle(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()
