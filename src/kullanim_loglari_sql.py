"""Supabase `kullanim_loglari` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "urun",
    "tur",
    "tarih",
    "miktar",
    "birim",
    "aciklama",
    "islem_yapan",
    "uretim_id",
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
    
def log_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki log sözlüğünü `kullanim_loglari` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"LOG-SQL-{sira}").strip()

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR:
            ekstra_dict[anahtar] = deger

    uretim_id_raw = veri.get("uretim_id")
    uretim_id = (
        str(uretim_id_raw).strip()
        if uretim_id_raw is not None and str(uretim_id_raw).strip() != ""
        else None
    )

    return {
        "id": kayit_id,
        "urun": str(veri.get("urun") or "").strip(),
        "tur": str(veri.get("tur") or "").strip(),
        "tarih": str(veri.get("tarih") or "").strip(),
        "miktar": _sayi_veya_varsayilan(veri.get("miktar"), 0.0),
        "birim": str(veri.get("birim") or "").strip(),
        "aciklama": str(veri.get("aciklama") or "").strip(),
        "islem_yapan": str(veri.get("islem_yapan") or "").strip(),
        "uretim_id": uretim_id,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_log_kaydina_donustur(satir):
    """`kullanim_loglari` tablo satırını uygulamanın beklediği log sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "urun": str(row.get("urun") or ""),
        "tur": str(row.get("tur") or ""),
        "tarih": str(row.get("tarih") or ""),
        "miktar": _sayi_veya_varsayilan(row.get("miktar"), 0.0),
        "birim": str(row.get("birim") or ""),
        "aciklama": str(row.get("aciklama") or ""),
        "islem_yapan": str(row.get("islem_yapan") or ""),
    })
    if row.get("uretim_id"):
        kayit["uretim_id"] = str(row.get("uretim_id"))
    return kayit


def kullanim_loglari_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`kullanim_loglari` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/kullanim_loglari",
            headers=headers_fn(),
            params={"select": "*", "order": "tarih.asc,id.asc"},
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
    return "ok", [satir_log_kaydina_donustur(r) for r in rows]


def kullanim_loglari_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`kullanim_loglari` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        log_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/kullanim_loglari",
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
                f"{url}/rest/v1/kullanim_loglari",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/kullanim_loglari",
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
                return True, [satir_log_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
