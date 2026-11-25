"""Supabase `yemek_uretim_arsivi` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "uretim_id",
    "yemek_adi",
    "tarih",
    "zaman",
    "kisi_sayisi",
    "islem_yapan",
    "menu_ogeleri",
    "malzemeler",
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


def uretim_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki üretim arşivi sözlüğünü `yemek_uretim_arsivi` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(
        veri.get("id") or veri.get("uretim_id") or f"URETIM-SQL-{sira}"
    ).strip()
    uretim_id_raw = veri.get("uretim_id") or veri.get("id")
    uretim_id = (
        str(uretim_id_raw).strip()
        if uretim_id_raw is not None and str(uretim_id_raw).strip() != ""
        else None
    )

    yemek_adi = str(
        veri.get("yemek_adi")
        or veri.get("menu_adi")
        or veri.get("baslik")
        or ""
    ).strip()
    zaman = str(veri.get("zaman") or veri.get("saat") or "").strip()
    kisi_raw = veri.get("kisi_sayisi")
    if kisi_raw is None or kisi_raw == "":
        kisi_raw = veri.get("porsiyon")

    menu_ogeleri = veri.get("menu_ogeleri")
    if not isinstance(menu_ogeleri, dict):
        menu_ogeleri = {}

    malzemeler = veri.get("malzemeler")
    if not isinstance(malzemeler, list):
        malzemeler = []

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR:
            ekstra_dict[anahtar] = deger

    return {
        "id": kayit_id,
        "uretim_id": uretim_id,
        "yemek_adi": yemek_adi,
        "tarih": str(veri.get("tarih") or "").strip(),
        "zaman": zaman,
        "kisi_sayisi": _sayi_veya_varsayilan(kisi_raw, 0.0),
        "islem_yapan": str(veri.get("islem_yapan") or "").strip(),
        "menu_ogeleri": menu_ogeleri,
        "malzemeler": malzemeler,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_uretim_kaydina_donustur(satir):
    """`yemek_uretim_arsivi` tablo satırını uygulamanın beklediği üretim sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "yemek_adi": str(row.get("yemek_adi") or ""),
        "tarih": str(row.get("tarih") or ""),
        "zaman": str(row.get("zaman") or ""),
        "kisi_sayisi": _sayi_veya_varsayilan(row.get("kisi_sayisi"), 0.0),
        "islem_yapan": str(row.get("islem_yapan") or ""),
        "menu_ogeleri": (
            dict(row["menu_ogeleri"])
            if isinstance(row.get("menu_ogeleri"), dict)
            else {}
        ),
        "malzemeler": (
            list(row["malzemeler"])
            if isinstance(row.get("malzemeler"), list)
            else []
        ),
    })
    if row.get("uretim_id"):
        kayit["uretim_id"] = str(row.get("uretim_id"))
    return kayit


def yemek_uretim_arsivi_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`yemek_uretim_arsivi` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/yemek_uretim_arsivi",
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
    return "ok", [satir_uretim_kaydina_donustur(r) for r in rows]


def yemek_uretim_arsivi_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`yemek_uretim_arsivi` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        uretim_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/yemek_uretim_arsivi",
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
                f"{url}/rest/v1/yemek_uretim_arsivi",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/yemek_uretim_arsivi",
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
                return True, [satir_uretim_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
