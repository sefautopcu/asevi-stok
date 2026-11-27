"""Supabase `rota_teslimat` ilişkisel tablosu için okuma ve yazma yardımcıları."""


def _tam_sayi_veya_varsayilan(deger, varsayilan=0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return int(float(str(deger).replace(",", ".")))
    except (TypeError, ValueError):
        return varsayilan


def _plaka_temizle(plaka):
    return " ".join(str(plaka or "").strip().upper().split())


def rota_teslimat_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki rota/teslimat sözlüğünü `rota_teslimat` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"RTS-SQL-{sira}").strip()
    nufus = max(1, _tam_sayi_veya_varsayilan(veri.get("hane_nufusu"), 1))
    planlanan = max(0, _tam_sayi_veya_varsayilan(veri.get("planlanan_porsiyon"), nufus))
    teslim_edilen = max(0, _tam_sayi_veya_varsayilan(veri.get("teslim_edilen_porsiyon"), 0))
    durum = str(veri.get("teslim_durumu") or "Bekliyor").strip() or "Bekliyor"

    return {
        "id": kayit_id,
        "tarih": str(veri.get("tarih") or "").strip(),
        "mahalle": str(veri.get("mahalle") or "").strip(),
        "sefer_id": str(veri.get("sefer_id") or "").strip(),
        "arac_plaka": _plaka_temizle(veri.get("arac_plaka")),
        "hane_id": str(veri.get("hane_id") or "").strip(),
        "hane_adi": str(veri.get("hane_adi") or "").strip(),
        "adres": str(veri.get("adres") or "").strip(),
        "hane_nufusu": nufus,
        "planlanan_porsiyon": planlanan,
        "teslim_edilen_porsiyon": teslim_edilen,
        "teslim_durumu": durum,
        "notlar": str(veri.get("notlar") or "").strip(),
    }


def satir_rota_teslimat_kaydina_donustur(satir):
    """`rota_teslimat` tablo satırını uygulamanın beklediği sözlüğe çevirir."""
    row = satir if isinstance(satir, dict) else {}
    nufus = max(1, _tam_sayi_veya_varsayilan(row.get("hane_nufusu"), 1))
    planlanan = max(0, _tam_sayi_veya_varsayilan(row.get("planlanan_porsiyon"), nufus))
    teslim_edilen = max(0, _tam_sayi_veya_varsayilan(row.get("teslim_edilen_porsiyon"), 0))

    return {
        "id": str(row.get("id") or ""),
        "tarih": str(row.get("tarih") or ""),
        "mahalle": str(row.get("mahalle") or ""),
        "sefer_id": str(row.get("sefer_id") or ""),
        "arac_plaka": _plaka_temizle(row.get("arac_plaka")),
        "hane_id": str(row.get("hane_id") or ""),
        "hane_adi": str(row.get("hane_adi") or ""),
        "adres": str(row.get("adres") or ""),
        "hane_nufusu": nufus,
        "planlanan_porsiyon": planlanan,
        "teslim_edilen_porsiyon": teslim_edilen,
        "teslim_durumu": str(row.get("teslim_durumu") or "Bekliyor"),
        "notlar": str(row.get("notlar") or ""),
    }


def rota_teslimat_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`rota_teslimat` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/rota_teslimat",
            headers=headers_fn(),
            params={"select": "*", "order": "tarih.desc,mahalle.asc,id.asc"},
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
    return "ok", [satir_rota_teslimat_kaydina_donustur(r) for r in rows]


def rota_teslimat_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`rota_teslimat` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        rota_teslimat_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/rota_teslimat",
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
                f"{url}/rest/v1/rota_teslimat",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/rota_teslimat",
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
                return True, [satir_rota_teslimat_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
