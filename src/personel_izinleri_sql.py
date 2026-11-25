"""Supabase `personel_izinleri` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "personel",
    "baslangic_tarihi",
    "bitis_tarihi",
    "tur",
    "durum",
    "ekstra_alanlar",
    "guncellenme_zamani",
}


def izin_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki izin sözlüğünü `personel_izinleri` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"IZIN-SQL-{sira}").strip()

    personel = str(
        veri.get("personel")
        or veri.get("ad_soyad")
        or veri.get("personel_adi")
        or ""
    ).strip()
    baslangic = str(
        veri.get("baslangic_tarihi") or veri.get("baslangic") or ""
    ).strip()
    bitis = str(
        veri.get("bitis_tarihi") or veri.get("bitis") or ""
    ).strip()
    tur = str(veri.get("tur") or veri.get("izin_turu") or "").strip()

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR:
            ekstra_dict[anahtar] = deger

    return {
        "id": kayit_id,
        "personel": personel,
        "baslangic_tarihi": baslangic,
        "bitis_tarihi": bitis,
        "tur": tur,
        "durum": str(veri.get("durum") or "").strip(),
        "ekstra_alanlar": ekstra_dict,
    }


def satir_izin_kaydina_donustur(satir):
    """`personel_izinleri` tablo satırını uygulamanın beklediği izin sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "personel": str(row.get("personel") or ""),
        "baslangic_tarihi": str(row.get("baslangic_tarihi") or ""),
        "bitis_tarihi": str(row.get("bitis_tarihi") or ""),
        "tur": str(row.get("tur") or ""),
        "durum": str(row.get("durum") or ""),
    })
    return kayit


def personel_izinleri_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`personel_izinleri` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/personel_izinleri",
            headers=headers_fn(),
            params={"select": "*", "order": "baslangic_tarihi.asc,id.asc"},
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
    return "ok", [satir_izin_kaydina_donustur(r) for r in rows]


def personel_izinleri_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`personel_izinleri` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        izin_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/personel_izinleri",
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
                f"{url}/rest/v1/personel_izinleri",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/personel_izinleri",
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
                return True, [satir_izin_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
