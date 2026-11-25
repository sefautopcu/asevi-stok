"""Supabase `demirbaslar_listesi` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "ad",
    "kategori",
    "adet",
    "durum",
    "zimmet",
    "tarih",
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


def demirbas_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki demirbaş sözlüğünü `demirbaslar_listesi` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"DEM-SQL-{sira}").strip()
    ad = str(veri.get("ad") or veri.get("demirbas_adi") or "").strip()

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR:
            ekstra_dict[anahtar] = deger

    return {
        "id": kayit_id,
        "ad": ad,
        "kategori": str(veri.get("kategori") or "").strip(),
        "adet": _sayi_veya_varsayilan(veri.get("adet"), 0.0),
        "durum": str(veri.get("durum") or "").strip(),
        "zimmet": str(veri.get("zimmet") or "").strip(),
        "tarih": str(veri.get("tarih") or "").strip(),
        "ekstra_alanlar": ekstra_dict,
    }


def satir_demirbas_kaydina_donustur(satir):
    """`demirbaslar_listesi` tablo satırını uygulamanın beklediği demirbaş sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "ad": str(row.get("ad") or ""),
        "kategori": str(row.get("kategori") or ""),
        "adet": _sayi_veya_varsayilan(row.get("adet"), 0.0),
        "durum": str(row.get("durum") or ""),
        "zimmet": str(row.get("zimmet") or ""),
        "tarih": str(row.get("tarih") or ""),
    })
    return kayit


def demirbaslar_listesi_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`demirbaslar_listesi` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/demirbaslar_listesi",
            headers=headers_fn(),
            params={"select": "*", "order": "id.asc"},
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
    return "ok", [satir_demirbas_kaydina_donustur(r) for r in rows]


def demirbaslar_listesi_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`demirbaslar_listesi` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        demirbas_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/demirbaslar_listesi",
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
                f"{url}/rest/v1/demirbaslar_listesi",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/demirbaslar_listesi",
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
                return True, [satir_demirbas_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
