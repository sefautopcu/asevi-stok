"""Supabase `kritik_seviyeler` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "urun_anahtari",
    "kritik_miktar",
    "birim",
    "ekstra_alanlar",
    "guncellenme_zamani",
}


def _sayi_veya_varsayilan(deger, varsayilan=0.0):
    if deger is None or deger == "":
        return varsayilan
    if isinstance(deger, (int, float)):
        return float(deger)
    metin = str(deger).strip().replace(" ", "")
    if "," in metin and "." not in metin:
        metin = metin.replace(",", ".")
    elif "," in metin and "." in metin:
        metin = metin.replace(".", "").replace(",", ".")
    try:
        return float(metin)
    except (TypeError, ValueError):
        return varsayilan


def kritik_kaydini_satira_donustur(urun_anahtari, deger):
    """Uygulamadaki kritik seviye girdisini `kritik_seviyeler` tablo satırına çevirir."""
    anahtar = str(urun_anahtari or "").strip()
    if isinstance(deger, dict):
        miktar_ham = (
            deger.get("kritik_miktar")
            if deger.get("kritik_miktar") is not None
            else (
                deger.get("miktar")
                if deger.get("miktar") is not None
                else deger.get("seviye")
            )
        )
        birim = str(deger.get("birim") or "").strip()
        ekstra = deger.get("ekstra_alanlar")
        ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
        for k, v in deger.items():
            if k not in _ANA_SUTUNLAR and k not in {"miktar", "seviye"}:
                ekstra_dict[k] = v
    else:
        miktar_ham = deger
        birim = ""
        ekstra_dict = {}

    return {
        "urun_anahtari": anahtar,
        "kritik_miktar": _sayi_veya_varsayilan(miktar_ham, 0.0),
        "birim": birim,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_kritik_kaydina_donustur(satir):
    """`kritik_seviyeler` tablo satırını (anahtar, değer) ikilisine çevirir."""
    row = satir if isinstance(satir, dict) else {}
    anahtar = str(row.get("urun_anahtari") or "").strip()
    miktar = _sayi_veya_varsayilan(row.get("kritik_miktar"), 0.0)
    birim = str(row.get("birim") or "").strip()
    ekstra = row.get("ekstra_alanlar")
    ekstra_temiz = dict(ekstra) if isinstance(ekstra, dict) else {}

    if not birim and not ekstra_temiz:
        return anahtar, miktar

    sozluk = dict(ekstra_temiz)
    sozluk["kritik_miktar"] = miktar
    if birim:
        sozluk["birim"] = birim
    return anahtar, sozluk


def kritik_seviyeler_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`kritik_seviyeler` tablosunu okur; ('ok', sozluk) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/kritik_seviyeler",
            headers=headers_fn(),
            params={"select": "*", "order": "urun_anahtari.asc"},
            timeout=timeout,
        )
    except Exception as exc:
        return "hata", f"Bağlantı hatası: {type(exc).__name__}"
    if response.status_code != 200:
        return "hata", f"HTTP {response.status_code}"
    try:
        rows = response.json()
    except Exception:
        return "hata", "Geçersiz yanıt"
    if not isinstance(rows, list):
        return "hata", "Geçersiz tablo yanıtı"

    sonuc = {}
    for r in rows:
        anahtar, deger = satir_kritik_kaydina_donustur(r)
        if anahtar:
            sonuc[anahtar] = deger
    return "ok", sonuc


def kritik_seviyeler_sql_kaydet(veri_sozlugu, url, headers_fn, session_fn, timeout=10):
    """`kritik_seviyeler` tablosunu güncel sözlükle senkronize eder."""
    sozluk = veri_sozlugu if isinstance(veri_sozlugu, dict) else {}
    satirlar = []
    for k, v in sozluk.items():
        temiz_k = str(k or "").strip()
        if temiz_k:
            satirlar.append(kritik_kaydini_satira_donustur(temiz_k, v))

    aktif_anahtarlar = {s["urun_anahtari"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/kritik_seviyeler",
            headers=headers_fn(),
            params={"select": "urun_anahtari"},
            timeout=timeout,
        )
        if mevcut_resp.status_code != 200:
            return False, f"Mevcut satırlar okunamadı (HTTP {mevcut_resp.status_code})"
        mevcut_anahtarlar = {
            str(r.get("urun_anahtari")).strip()
            for r in (mevcut_resp.json() or [])
            if r.get("urun_anahtari")
        }

        silinecekler = mevcut_anahtarlar - aktif_anahtarlar
        for sil_k in silinecekler:
            del_resp = session_fn().delete(
                f"{url}/rest/v1/kritik_seviyeler",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"urun_anahtari": f"eq.{sil_k}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_k}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/kritik_seviyeler",
                headers=headers_fn({
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=representation",
                }),
                json=satirlar,
                timeout=timeout,
            )
            if up_resp.status_code not in (200, 201):
                return False, f"Yazma hatası (HTTP {up_resp.status_code})"
            donen = up_resp.json()
            if isinstance(donen, list):
                donen_sozluk = {}
                for r in donen:
                    ak, av = satir_kritik_kaydina_donustur(r)
                    if ak:
                        donen_sozluk[ak] = av
                return True, donen_sozluk

        return True, sozluk
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
