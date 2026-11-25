"""Supabase `depolar_listesi` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "depo_adi",
    "sira_no",
    "ekstra_alanlar",
    "guncellenme_zamani",
}


def depo_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki depo öğesini (metin veya sözlük) `depolar_listesi` satırına çevirir."""
    sira_no = int(sira)
    if isinstance(kayit, dict):
        kayit_id = str(kayit.get("id") or f"DEPO-{sira_no:03d}").strip()
        depo_adi = str(
            kayit.get("depo_adi")
            or kayit.get("ad")
            or kayit.get("depo")
            or ""
        ).strip()
        ekstra = kayit.get("ekstra_alanlar")
        ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
        for anahtar, deger in kayit.items():
            if anahtar not in _ANA_SUTUNLAR and anahtar not in {"ad", "depo"}:
                ekstra_dict[anahtar] = deger
    else:
        kayit_id = f"DEPO-{sira_no:03d}"
        depo_adi = str(kayit or "").strip()
        ekstra_dict = {}

    return {
        "id": kayit_id,
        "depo_adi": depo_adi,
        "sira_no": sira_no,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_depo_kaydina_donustur(satir):
    """`depolar_listesi` tablo satırını uygulamanın beklediği depo değerine çevirir."""
    row = satir if isinstance(satir, dict) else {}
    depo_adi = str(row.get("depo_adi") or "").strip()
    ekstra = row.get("ekstra_alanlar")
    if isinstance(ekstra, dict) and len(ekstra) > 0:
        kayit = dict(ekstra)
        kayit["id"] = str(row.get("id") or "")
        kayit["depo_adi"] = depo_adi
        return kayit
    return depo_adi


def depolar_listesi_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`depolar_listesi` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/depolar_listesi",
            headers=headers_fn(),
            params={"select": "*", "order": "sira_no.asc,id.asc"},
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
    return "ok", [satir_depo_kaydina_donustur(r) for r in rows]


def depolar_listesi_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`depolar_listesi` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        depo_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/depolar_listesi",
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
                f"{url}/rest/v1/depolar_listesi",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/depolar_listesi",
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
                return True, [satir_depo_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
