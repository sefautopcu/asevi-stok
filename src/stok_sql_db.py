"""Supabase `stok_girisleri` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "urun",
    "fatura_no",
    "tarih",
    "miktar",
    "kalan",
    "birim",
    "fiyat",
    "birim_fiyat",
    "skt",
    "depo",
    "kategori",
    "paket_miktari",
    "paket_durumlari",
    "ekstra_alanlar",
    "guncellenme_zamani",
}


def _sayi_veya_varsayilan(deger, varsayilan=0.0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return float(deger)
    except (TypeError, ValueError):
        return varsayilan


def stok_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki stok sözlüğünü `stok_girisleri` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"FAT-SQL-{sira}").strip()
    paket_durumlari = veri.get("paket_durumlari")
    if not isinstance(paket_durumlari, dict):
        paket_durumlari = {}

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR:
            ekstra_dict[anahtar] = deger

    birim_fiyat_raw = veri.get("birim_fiyat")
    birim_fiyat = (
        None
        if birim_fiyat_raw is None or str(birim_fiyat_raw).strip() == ""
        else _sayi_veya_varsayilan(birim_fiyat_raw, None)
    )

    return {
        "id": kayit_id,
        "urun": str(veri.get("urun") or "").strip(),
        "fatura_no": str(veri.get("fatura_no") or "").strip(),
        "tarih": str(veri.get("tarih") or "").strip(),
        "miktar": _sayi_veya_varsayilan(veri.get("miktar"), 0.0),
        "kalan": _sayi_veya_varsayilan(veri.get("kalan"), 0.0),
        "birim": str(veri.get("birim") or "").strip(),
        "fiyat": _sayi_veya_varsayilan(veri.get("fiyat"), 0.0),
        "birim_fiyat": birim_fiyat,
        "skt": str(veri.get("skt")).strip() if veri.get("skt") else None,
        "depo": str(veri.get("depo") or "").strip(),
        "kategori": str(veri.get("kategori") or "").strip(),
        "paket_miktari": _sayi_veya_varsayilan(veri.get("paket_miktari"), 0.0),
        "paket_durumlari": paket_durumlari,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_stok_kaydina_donustur(satir):
    """`stok_girisleri` tablo satırını uygulamanın beklediği stok sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "urun": str(row.get("urun") or ""),
        "fatura_no": str(row.get("fatura_no") or ""),
        "tarih": str(row.get("tarih") or ""),
        "miktar": _sayi_veya_varsayilan(row.get("miktar"), 0.0),
        "kalan": _sayi_veya_varsayilan(row.get("kalan"), 0.0),
        "birim": str(row.get("birim") or ""),
        "fiyat": _sayi_veya_varsayilan(row.get("fiyat"), 0.0),
        "birim_fiyat": row.get("birim_fiyat"),
        "skt": row.get("skt") or "",
        "depo": str(row.get("depo") or ""),
        "kategori": str(row.get("kategori") or ""),
        "paket_miktari": _sayi_veya_varsayilan(row.get("paket_miktari"), 0.0),
        "paket_durumlari": (
            dict(row["paket_durumlari"])
            if isinstance(row.get("paket_durumlari"), dict)
            else {}
        ),
    })
    return kayit


def stok_girisleri_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`stok_girisleri` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/stok_girisleri",
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
    return "ok", [satir_stok_kaydina_donustur(r) for r in rows]


def stok_girisleri_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`stok_girisleri` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        stok_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/stok_girisleri",
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
                f"{url}/rest/v1/stok_girisleri",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/stok_girisleri",
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
                return True, [satir_stok_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
