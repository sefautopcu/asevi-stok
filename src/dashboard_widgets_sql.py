"""Supabase `dashboard_widgets` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "baslik",
    "tur",
    "aktif",
    "sira_no",
    "ekstra_alanlar",
    "guncellenme_zamani",
}


def _bool_veya_varsayilan(deger, varsayilan=True):
    if isinstance(deger, bool):
        return deger
    if isinstance(deger, (int, float)):
        return bool(deger)
    if isinstance(deger, str):
        temiz = deger.strip().lower()
        if temiz in {"true", "1", "evet", "aktif", "yes"}:
            return True
        if temiz in {"false", "0", "hayir", "hayır", "pasif", "no"}:
            return False
    return varsayilan


def widget_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki widget sözlüğünü `dashboard_widgets` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    sira_no = int(sira)
    kayit_id = str(veri.get("id") or f"w{sira_no}").strip()
    baslik = str(veri.get("baslik") or veri.get("ad") or "").strip()

    ekstra = veri.get("ekstra_alanlar")
    ekstra_dict = dict(ekstra) if isinstance(ekstra, dict) else {}
    for anahtar, deger in veri.items():
        if anahtar not in _ANA_SUTUNLAR and anahtar != "ad":
            ekstra_dict[anahtar] = deger

    return {
        "id": kayit_id,
        "baslik": baslik,
        "tur": str(veri.get("tur") or "").strip(),
        "aktif": _bool_veya_varsayilan(veri.get("aktif"), True),
        "sira_no": sira_no,
        "ekstra_alanlar": ekstra_dict,
    }


def satir_widget_kaydina_donustur(satir):
    """`dashboard_widgets` tablo satırını uygulamanın beklediği widget sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    ekstra = row.get("ekstra_alanlar")
    kayit = dict(ekstra) if isinstance(ekstra, dict) else {}

    kayit.update({
        "id": str(row.get("id") or ""),
        "baslik": str(row.get("baslik") or ""),
        "tur": str(row.get("tur") or ""),
        "aktif": _bool_veya_varsayilan(row.get("aktif"), True),
    })
    return kayit


def dashboard_widgets_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`dashboard_widgets` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/dashboard_widgets",
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
    return "ok", [satir_widget_kaydina_donustur(r) for r in rows]


def dashboard_widgets_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`dashboard_widgets` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        widget_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/dashboard_widgets",
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
                f"{url}/rest/v1/dashboard_widgets",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/dashboard_widgets",
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
                return True, [satir_widget_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
