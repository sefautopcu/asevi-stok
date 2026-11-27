# src/tedarikciler_sql.py
import re

TEDARIKCI_KATEGORILERI = [
    "🥩 Et ve Tavuk Ürünleri",
    "🌾 Bakliyat ve Kuru Gıda",
    "🥬 Sebze ve Meyve",
    "🥛 Süt ve Kahvaltılık",
    "🫒 Yağ, Salça ve Baharat",
    "🍞 Unlu Mamuller ve Ekmek",
    "📦 Ambalaj ve Temizlik",
    "🏪 Genel Gıda",
]


def _metin_norm(deger):
    """Türkçe karakter uyumlu küçük harf ve boşluk normalizasyonu yapar."""
    if deger is None:
        return ""
    metin = str(deger).strip()
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", metin)


def yeni_tedarikci_id_uret(mevcut_listesi):
    """Mevcut listedeki en büyük TED-XXX numarasının bir fazlasını üretir."""
    en_buyuk = 0
    for kayit in mevcut_listesi or []:
        if not isinstance(kayit, dict):
            continue
        kid = str(kayit.get("id", "")).strip().upper()
        eslesme = re.match(r"^TED-(\d+)$", kid)
        if eslesme:
            en_buyuk = max(en_buyuk, int(eslesme.group(1)))
    return f"TED-{en_buyuk + 1:03d}"


def tedarikci_dogrula(firma_adi, telefon="", vergi_no="", mevcut_listesi=None, haric_id=None):
    """Tedarikçi kaydını doğrular; (gecerli_mi, hata_mesaji) döndürür."""
    temiz_ad = str(firma_adi or "").strip()
    if len(temiz_ad) < 2:
        return False, "Firma adı en az 2 karakter olmalıdır."

    aranan_norm = _metin_norm(temiz_ad)
    for kayit in mevcut_listesi or []:
        if not isinstance(kayit, dict):
            continue
        if haric_id and str(kayit.get("id", "")) == str(haric_id):
            continue
        if _metin_norm(kayit.get("firma_adi", "")) == aranan_norm:
            return False, f"'{temiz_ad}' adında bir tedarikçi zaten kayıtlı."

    temiz_vno = re.sub(r"\D", "", str(vergi_no or ""))
    if temiz_vno and len(temiz_vno) not in (10, 11):
        return False, "Vergi No 10 haneli (veya T.C. Kimlik No 11 haneli) olmalıdır."

    temiz_tel = re.sub(r"\D", "", str(telefon or ""))
    if temiz_tel and len(temiz_tel) < 10:
        return False, "Telefon numarası en az 10 haneli olmalıdır."

    return True, ""


def tedarikci_alim_istatistikleri(firma_adi, girisler):
    """Belirli bir tedarikçiye ait stok giriş kayıtlarından özet istatistik çıkarır."""
    aranan = _metin_norm(firma_adi)
    if not aranan or not girisler:
        return {
            "fatura_sayisi": 0,
            "toplam_tutar": 0.0,
            "urun_ozeti": [],
        }

    faturalar = set()
    toplam_tutar = 0.0
    urun_map = {}

    for g in girisler:
        if not isinstance(g, dict):
            continue
        g_firma = (
            g.get("tedarikci")
            or g.get("firma")
            or g.get("firma_adi")
            or g.get("satici")
            or ""
        )
        if _metin_norm(g_firma) != aranan:
            continue

        fatura_no = str(g.get("fatura_no") or g.get("id") or "").strip()
        if fatura_no:
            faturalar.add(fatura_no)

        try:
            miktar = float(g.get("miktar", 0) or 0)
        except (TypeError, ValueError):
            miktar = 0.0

        try:
            birim_fiyat = float(g.get("birim_fiyat") or g.get("fiyat") or 0)
        except (TypeError, ValueError):
            birim_fiyat = 0.0

        satir_tutar = miktar * birim_fiyat
        toplam_tutar += satir_tutar

        urun = str(g.get("urun", "-")).strip().upper()
        birim = str(g.get("birim", "Kg")).strip()
        tarih = str(g.get("tarih", "")).strip()

        if urun not in urun_map:
            urun_map[urun] = {
                "urun": urun,
                "birim": birim,
                "toplam_miktar": 0.0,
                "toplam_tutar": 0.0,
                "son_birim_fiyat": birim_fiyat,
                "son_tarih": tarih,
                "alim_sayisi": 0,
            }

        kayit = urun_map[urun]
        kayit["toplam_miktar"] += miktar
        kayit["toplam_tutar"] += satir_tutar
        kayit["alim_sayisi"] += 1
        if tarih >= kayit["son_tarih"]:
            kayit["son_tarih"] = tarih
            kayit["son_birim_fiyat"] = birim_fiyat

    urun_ozeti = sorted(
        urun_map.values(),
        key=lambda x: x["toplam_tutar"],
        reverse=True,
    )
    return {
        "fatura_sayisi": len(faturalar),
        "toplam_tutar": toplam_tutar,
        "urun_ozeti": urun_ozeti,
    }


def tedarikciler_sql_oku(supabase_url, basliklar_fn, session_fn):
    """Supabase `tedarikciler` tablosundan kayıtları okur."""
    try:
        r = session_fn().get(
            f"{supabase_url}/rest/v1/tedarikciler",
            headers=basliklar_fn(),
            params={"select": "*", "order": "id.asc"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}"

    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}"

    try:
        veriler = r.json()
    except Exception:
        return "hata", "Geçersiz JSON yanıtı"

    if not isinstance(veriler, list):
        return "hata", "Beklenmeyen veri formatı"

    return "ok", veriler


def tedarikciler_sql_kaydet(veri_listesi, supabase_url, basliklar_fn, session_fn):
    """Tedarikçi listesini Supabase `tedarikciler` tablosuna senkronize eder."""
    kayitlar = [dict(x) for x in (veri_listesi or []) if isinstance(x, dict) and x.get("id")]
    session = session_fn()
    endpoint = f"{supabase_url}/rest/v1/tedarikciler"

    try:
        mevcut_r = session.get(
            endpoint,
            headers=basliklar_fn(),
            params={"select": "id"},
            timeout=10,
        )
        if mevcut_r.status_code == 200:
            mevcut_idler = {
                str(row.get("id"))
                for row in (mevcut_r.json() or [])
                if isinstance(row, dict) and row.get("id")
            }
            yeni_idler = {str(row.get("id")) for row in kayitlar}
            silinecek_idler = mevcut_idler - yeni_idler
            for sil_id in silinecek_idler:
                session.delete(
                    endpoint,
                    headers=basliklar_fn(),
                    params={"id": f"eq.{sil_id}"},
                    timeout=10,
                )

        if not kayitlar:
            return True, "ok"

        temiz_payload = []
        for k in kayitlar:
            temiz_payload.append({
                "id": str(k.get("id", "")).strip(),
                "firma_adi": str(k.get("firma_adi", "")).strip(),
                "yetkili_kisi": str(k.get("yetkili_kisi", "") or "").strip(),
                "telefon": str(k.get("telefon", "") or "").strip(),
                "vergi_no": str(k.get("vergi_no", "") or "").strip(),
                "kategori": str(k.get("kategori", "🏪 Genel Gıda") or "🏪 Genel Gıda").strip(),
                "adres": str(k.get("adres", "") or "").strip(),
                "aktif": bool(k.get("aktif", True)),
                "notlar": str(k.get("notlar", "") or "").strip(),
                "olusturma_tarihi": str(k.get("olusturma_tarihi", "") or "").strip(),
                "guncelleme_tarihi": str(k.get("guncelleme_tarihi", "") or "").strip(),
            })

        r = session.post(
            endpoint,
            headers=basliklar_fn({
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }),
            json=temiz_payload,
            timeout=10,
        )
        if r.status_code in (200, 201):
            return True, "ok"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"Bağlantı hatası: {type(e).__name__}"
