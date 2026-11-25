# src/yemek_utils.py
import datetime
import math
import statistics
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

def dashboard_skt_sayilarini_hesapla(girisler, bugun=None):
    """Yalnızca kalan stoğu olan ürünlerin SKT durumunu ürün bazında sayar."""
    bugun = bugun or datetime.date.today()
    urun_sktleri = {}

    for giris in girisler:
        urun = str(giris.get("urun", "")).strip().upper()
        if not urun:
            continue
            
        # DÜZELTME 1: Sadece kalan stoğu 0'dan büyük olanları hesaba kat
        try:
            kalan = float(giris.get("kalan", 0) or 0)
        except (TypeError, ValueError):
            continue
        if kalan <= 0:
            continue

        skt = giris.get("skt")
        if not skt:
            continue
        try:
            skt_tarihi = datetime.datetime.strptime(str(skt), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
            
        urun_sktleri.setdefault(urun, []).append(skt_tarihi)

    skt_kirmizi = 0
    skt_turuncu = 0
    
    for urun, skt_tarihleri in urun_sktleri.items():
        # Ürünün birden fazla partisi varsa, en yakın (en erken) SKT tarihini baz al
        en_yakin_skt = min(skt_tarihleri)
        kalan_gun = (en_yakin_skt - bugun).days
        
        # DÜZELTME 2: 0 gün kaldığında (yani süresi bugün bittiğinde) kırmızıya geçer
        if kalan_gun < 0:
            skt_kirmizi += 1
        # DÜZELTME 3: 0 ile 7 gün arası (7 dahil) turuncu sayar
        elif 0 <= kalan_gun <= 7:
            skt_turuncu += 1

    return skt_kirmizi, skt_turuncu

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

def yemek_menu_alanlari():
    return (
        ("ana_yemek", "Ana Yemek"),
        ("yardimci_yemek", "Yardımcı Yemek / Ara Yemek"),
        ("corba", "Çorba"),
        ("tatli_meyve_yogurt", "Tatlı / Meyve / Yoğurt"),
    )

def _malzeme_kullanim_anahtari(urun_adi):
    return "".join(str(urun_adi or "").split()).upper()

def _menu_adlari_eslesiyor(solan_ad, sag_ad):
    sol = _malzeme_kullanim_anahtari(solan_ad)
    sag = _malzeme_kullanim_anahtari(sag_ad)
    if not sol or not sag:
        return False
    if sol == sag:
        return True
    for ek in ("YEMEĞI", "YEMEĞİ", "YEMEGI", "YEMEK"):
        if sol.endswith(ek):
            sol = sol[: -len(ek)]
        if sag.endswith(ek):
            sag = sag[: -len(ek)]
    return bool(sol) and sol == sag

def yemek_menu_ogelerini_temizle(menu_ogeleri):
    if not isinstance(menu_ogeleri, dict):
        return {alan: "" for alan, _ in yemek_menu_alanlari()}
    return {
        alan: str(menu_ogeleri.get(alan, "") or "").strip()
        for alan, _ in yemek_menu_alanlari()
    }

def yemek_menu_ogelerini_kayittan_al(kayit):
    menu_ogeleri = yemek_menu_ogelerini_temizle(kayit.get("menu_ogeleri"))
    if not any(menu_ogeleri.values()):
        menu_ogeleri = yemek_menu_ogelerini_temizle(
            {
                alan: kayit.get(f"menu_{alan}", "")
                for alan, _ in yemek_menu_alanlari()
            }
        )
    if not any(menu_ogeleri.values()):
        eski_ad = str(kayit.get("yemek_adi", "") or "").strip()
        eski_parcalar = [
            parca.strip()
            for parca in eski_ad.replace(";", "/").split("/")
            if parca.strip()
        ]
        if len(eski_parcalar) == 1 and ":" in eski_parcalar[0]:
            etiket, deger = (
                parca.strip() for parca in eski_parcalar[0].split(":", 1)
            )
            etiket_anahtari = _malzeme_kullanim_anahtari(etiket)
            etiket_eslesmeleri = {
                "ANAYEMEK": "ana_yemek",
                "YARDIMCIYEMEK": "yardimci_yemek",
                "ARAYEMEK": "yardimci_yemek",
                "CORBA": "corba",
                "TATLIMEYVEYOĞURT": "tatli_meyve_yogurt",
                "TATLIMEYVEYOGURT": "tatli_meyve_yogurt",
            }
            alan = etiket_eslesmeleri.get(etiket_anahtari)
            if alan and deger:
                menu_ogeleri[alan] = deger
        elif eski_ad and "/" not in eski_ad and ";" not in eski_ad:
            menu_ogeleri["ana_yemek"] = eski_ad
    return menu_ogeleri

def yemek_arsiv_menu_kolonlari(kayit):
    menu_ogeleri = yemek_menu_ogelerini_kayittan_al(kayit)
    return {
        etiket: menu_ogeleri[alan] or "-"
        for alan, etiket in yemek_menu_alanlari()
    }

def yemek_kaydi_menu_ogelerini_guncelle(kayit, menu_ogeleri):
    temiz_menu = yemek_menu_ogelerini_temizle(menu_ogeleri)
    if not any(temiz_menu.values()):
        return False
    kayit["menu_ogeleri"] = temiz_menu
    kayit["yemek_adi"] = " / ".join(
        deger for deger in temiz_menu.values() if deger
    )
    return True

def yemek_malzeme_kullanim_istatistikleri(
    arsiv, menu_ogeleri, kisi_sayisi, referans_tarihi=None, referans_zamani=None
):
    """Aynı menü bölümlerinden geçmiş kişi başı malzeme ortalaması ve sapması."""
    if isinstance(menu_ogeleri, str):
        menu_ogeleri = {"ana_yemek": menu_ogeleri}
    aranan_menu = yemek_menu_ogelerini_temizle(menu_ogeleri)
    aranan_menu = {
        alan: _malzeme_kullanim_anahtari(ad)
        for alan, ad in aranan_menu.items()
        if ad
    }
    if not aranan_menu:
        return {}
    uretimler = []
    malzeme_adlari = set()
    for kayit in arsiv:
        kayit_menu = yemek_menu_ogelerini_kayittan_al(kayit)
        if not any(
            _menu_adlari_eslesiyor(kayit_menu.get(alan), aranan_ad)
            for alan, aranan_ad in aranan_menu.items()
        ):
            continue
        if referans_tarihi:
            kayit_tarihi = str(kayit.get("tarih", ""))[:10]
            hedef_tarih = str(referans_tarihi)[:10]
            if not kayit_tarihi or kayit_tarihi > hedef_tarih:
                continue
            if (
                kayit_tarihi == hedef_tarih
                and referans_zamani
                and kayit.get("zaman")
            ):
                kayit_zamani = str(kayit.get("zaman", ""))
                if kayit_zamani >= str(referans_zamani):
                    continue
        try:
            kisi = float(kayit.get("kisi_sayisi", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(kisi) or kisi <= 0:
            continue
        malzeme_miktarlari = {}
        kayit_malzemeleri = kayit.get("malzemeler", [])
        if not isinstance(kayit_malzemeleri, list):
            continue
        for malzeme in kayit_malzemeleri:
            if not isinstance(malzeme, dict):
                continue
            ad = str(malzeme.get("urun", "")).strip()
            if not ad:
                continue
            try:
                miktar = float(malzeme.get("miktar", 0) or 0)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(miktar) or miktar < 0:
                continue
            anahtar = _malzeme_kullanim_anahtari(ad)
            malzeme_adlari.add(anahtar)
            malzeme_miktarlari[anahtar] = (
                malzeme_miktarlari.get(anahtar, {"ad": ad, "miktar": 0.0})
            )
            malzeme_miktarlari[anahtar]["miktar"] += miktar
        uretimler.append((kisi, malzeme_miktarlari))

    istatistikler = {}
    for anahtar in malzeme_adlari:
        kisi_basi_miktarlar = [
            miktarlar.get(anahtar, {}).get("miktar", 0.0) / kisi
            for kisi, miktarlar in uretimler
        ]
        istatistikler[anahtar] = {
            "ad": next(
                (miktarlar[anahtar]["ad"] for _, miktarlar in uretimler if anahtar in miktarlar),
                anahtar,
            ),
            "uretim_sayisi": len(kisi_basi_miktarlar),
            "ortalama_kisi_basi": statistics.fmean(kisi_basi_miktarlar),
            "sapma_kisi_basi": (
                statistics.pstdev(kisi_basi_miktarlar)
                if len(kisi_basi_miktarlar) > 1 else 0.0
            ),
        }

    try:
        bugunku_kisi = float(kisi_sayisi)
    except (TypeError, ValueError):
        bugunku_kisi = 0.0
    if not math.isfinite(bugunku_kisi):
        bugunku_kisi = 0.0
    for istatistik in istatistikler.values():
        ortalama = istatistik["ortalama_kisi_basi"]
        sapma = istatistik["sapma_kisi_basi"]
        tolerans = max(sapma, abs(ortalama) * 0.1)
        istatistik["beklenen_miktar"] = ortalama * bugunku_kisi
        istatistik["alt_sinir"] = max(0.0, (ortalama - tolerans) * bugunku_kisi)
        istatistik["ust_sinir"] = (ortalama + tolerans) * bugunku_kisi
    return istatistikler

def yemek_malzeme_kullanim_uyarilari(
    istatistikler, sepet, kisi_sayisi, birimler=None
):
    """Geçmişe göre kişi başı kullanımı belirgin farklı malzemeleri listeler."""
    bugunku_miktarlar = {}
    adlar = {}
    for item in sepet:
        ad = str(item.get("urun", "")).strip()
        if not ad:
            continue
        anahtar = _malzeme_kullanim_anahtari(ad)
        try:
            miktar = float(item.get("miktar", 0) or 0)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(miktar):
            continue
        bugunku_miktarlar[anahtar] = bugunku_miktarlar.get(anahtar, 0.0) + miktar
        adlar[anahtar] = ad

    uyarilar = []
    for anahtar, miktar in bugunku_miktarlar.items():
        istatistik = istatistikler.get(anahtar)
        if not istatistik:
            continue
        if miktar < istatistik["alt_sinir"] or miktar > istatistik["ust_sinir"]:
            try:
                bugunku_kisi = float(kisi_sayisi)
            except (TypeError, ValueError):
                bugunku_kisi = 0.0
            kisi_basi_miktar = miktar / bugunku_kisi if bugunku_kisi > 0 else 0.0
            birim = (birimler or {}).get(anahtar, "")
            birim_eki = f" {birim}" if birim else ""
            uyarilar.append(
                f"{adlar[anahtar]}: bugün {miktar:g}{birim_eki} "
                f"(kişi başı {kisi_basi_miktar:g} "
                f"{birim_eki.strip()}/kişi) kullanılıyor; "
                f"{istatistik['uretim_sayisi']} geçmiş üretimde kişi başı ortalama "
                f"{istatistik['ortalama_kisi_basi']:g}, bugünkü kişi sayısına göre "
                f"beklenen yaklaşık miktar {istatistik['beklenen_miktar']:g} "
                f"(alışılagelen aralık {istatistik['alt_sinir']:g}–"
                f"{istatistik['ust_sinir']:g})."
            )
    return uyarilar

def giris_birim_fiyati_al(giris):
    """Stok giriş kaydının birim fiyatını güvenli şekilde döndürür."""
    if not isinstance(giris, dict):
        return 0.0
    for alan in ("birim_fiyat", "fiyat"):
        deger = giris.get(alan)
        try:
            if deger not in (None, "") and float(deger) > 0:
                return float(deger)
        except (TypeError, ValueError):
            continue
    return 0.0


def en_son_urun_birim_fiyati(girisler, urun):
    """Yeni Mal Alımı kayıtlarında ilgili ürün için en son girilen kaydın birim fiyatını döndürür."""
    aranan = str(urun or "").strip().upper()
    if not aranan or not girisler:
        return 0.0

    adaylar = []
    for idx, g in enumerate(girisler):
        if not isinstance(g, dict):
            continue
        if str(g.get("urun", "")).strip().upper() != aranan:
            continue
        birim_f = giris_birim_fiyati_al(g)
        if birim_f > 0:
            tarih_str = str(g.get("tarih", "") or "")
            adaylar.append((tarih_str, idx, birim_f))

    if not adaylar:
        return 0.0

    adaylar.sort(key=lambda x: (x[0], x[1]))
    return adaylar[-1][2]


def yemek_sepeti_maliyet_hesapla(girisler, sepet):
    """Sepetteki her kalemin ve toplam sepetin maliyetini ürünün en son mal alımı birim fiyatıyla hesaplar."""
    kalem_maliyetleri = []
    toplam_maliyet = 0.0

    for item in sepet:
        urun = str(item.get("urun", "")).strip().upper()
        try:
            istenen = float(item.get("miktar", 0) or 0)
        except (TypeError, ValueError):
            istenen = 0.0

        if not urun or istenen <= 0:
            kalem_maliyetleri.append(0.0)
            continue

        son_birim_fiyat = en_son_urun_birim_fiyati(girisler, urun)
        item_tutar = istenen * son_birim_fiyat
        kalem_maliyetleri.append(item_tutar)
        toplam_maliyet += item_tutar

    return kalem_maliyetleri, toplam_maliyet
