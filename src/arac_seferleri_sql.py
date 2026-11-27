"""Supabase `arac_seferleri` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "tarih",
    "arac_plaka",
    "sofor_adi",
    "dagitim_personeli",
    "guzergah_mahalle",
    "cikis_saati",
    "donus_saati",
    "sefertas_porsiyon_sayisi",
    "teslim_edilen_porsiyon",
    "baslangic_km",
    "bitis_km",
    "sigorta_bitis_tarihi",
    "muayene_bitis_tarihi",
    "durum",
    "notlar",
    "olusturma_zamani",
}


def _sayi_veya_varsayilan(deger, varsayilan=0.0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        return varsayilan


def _tam_sayi_veya_varsayilan(deger, varsayilan=0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return int(float(str(deger).replace(",", ".")))
    except (TypeError, ValueError):
        return varsayilan


def sefer_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki sefer sözlüğünü `arac_seferleri` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"SFR-SQL-{sira}").strip()

    baslangic_km = _sayi_veya_varsayilan(veri.get("baslangic_km"), 0.0)
    bitis_km = _sayi_veya_varsayilan(veri.get("bitis_km"), 0.0)
    sefertas_porsiyon = _tam_sayi_veya_varsayilan(
        veri.get("sefertas_porsiyon_sayisi"), 0
    )
    teslim_porsiyon = _tam_sayi_veya_varsayilan(
        veri.get("teslim_edilen_porsiyon"), 0
    )

    durum_varsayilan = (
        "Tamamlandı"
        if (str(veri.get("donus_saati") or "").strip() or bitis_km > 0)
        else "Devam Ediyor"
    )
    durum = str(veri.get("durum") or durum_varsayilan).strip()

    return {
        "id": kayit_id,
        "tarih": str(veri.get("tarih") or "").strip(),
        "arac_plaka": str(veri.get("arac_plaka") or "").strip().upper(),
        "sofor_adi": str(veri.get("sofor_adi") or "").strip(),
        "dagitim_personeli": str(veri.get("dagitim_personeli") or "").strip(),
        "guzergah_mahalle": str(veri.get("guzergah_mahalle") or "").strip(),
        "cikis_saati": str(veri.get("cikis_saati") or "").strip(),
        "donus_saati": str(veri.get("donus_saati") or "").strip(),
        "sefertas_porsiyon_sayisi": sefertas_porsiyon,
        "teslim_edilen_porsiyon": teslim_porsiyon,
        "baslangic_km": baslangic_km,
        "bitis_km": bitis_km,
        "sigorta_bitis_tarihi": str(veri.get("sigorta_bitis_tarihi") or "").strip(),
        "muayene_bitis_tarihi": str(veri.get("muayene_bitis_tarihi") or "").strip(),
        "durum": durum,
        "notlar": str(veri.get("notlar") or "").strip(),
    }


def satir_sefer_kaydina_donustur(satir):
    """`arac_seferleri` tablo satırını uygulamanın beklediği sözlüğe çevirir."""
    row = satir if isinstance(satir, dict) else {}
    baslangic_km = _sayi_veya_varsayilan(row.get("baslangic_km"), 0.0)
    bitis_km = _sayi_veya_varsayilan(row.get("bitis_km"), 0.0)
    yapilan_km = round(max(0.0, bitis_km - baslangic_km), 2) if bitis_km > 0 else 0.0

    return {
        "id": str(row.get("id") or ""),
        "tarih": str(row.get("tarih") or ""),
        "arac_plaka": str(row.get("arac_plaka") or ""),
        "sofor_adi": str(row.get("sofor_adi") or ""),
        "dagitim_personeli": str(row.get("dagitim_personeli") or ""),
        "guzergah_mahalle": str(row.get("guzergah_mahalle") or ""),
        "cikis_saati": str(row.get("cikis_saati") or ""),
        "donus_saati": str(row.get("donus_saati") or ""),
        "sefertas_porsiyon_sayisi": _tam_sayi_veya_varsayilan(
            row.get("sefertas_porsiyon_sayisi"), 0
        ),
        "teslim_edilen_porsiyon": _tam_sayi_veya_varsayilan(
            row.get("teslim_edilen_porsiyon"), 0
        ),
        "baslangic_km": baslangic_km,
        "bitis_km": bitis_km,
        "yapilan_km": yapilan_km,
        "sigorta_bitis_tarihi": str(row.get("sigorta_bitis_tarihi") or ""),
        "muayene_bitis_tarihi": str(row.get("muayene_bitis_tarihi") or ""),
        "durum": str(row.get("durum") or "Devam Ediyor"),
        "notlar": str(row.get("notlar") or ""),
    }


def arac_seferleri_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`arac_seferleri` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/arac_seferleri",
            headers=headers_fn(),
            params={"select": "*", "order": "tarih.desc,cikis_saati.desc,id.desc"},
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
    return "ok", [satir_sefer_kaydina_donustur(r) for r in rows]


def arac_seferleri_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`arac_seferleri` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        sefer_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/arac_seferleri",
            headers=headers_fn(),
            params={"select": "id"},
            timeout=timeout,
        )
        if mevcut_resp.status_code != 200:
            return False, f"Mevcut satırlar okunamadı (HTTP {mevcut_resp.status_code})"
        mevcut_idler = {
            str(r.get("id")) for r in (mevcut_resp.json() or []) if r.get("id")
        }

        silinecek_idler = mevcut_idler - aktif_idler
        for sil_id in silinecek_idler:
            del_resp = session_fn().delete(
                f"{url}/rest/v1/arac_seferleri",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/arac_seferleri",
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
                return True, [satir_sefer_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
