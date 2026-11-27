"""Supabase `sabah_brifingi_uyarilari` tablosu için okuma ve yazma yardımcıları."""

import datetime
from urllib.parse import quote


def _bugun_tarih_str():
    try:
        from zoneinfo import ZoneInfo

        return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def _simdi_zaman_str():
    try:
        from zoneinfo import ZoneInfo

        return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sabah_uyarisini_satira_donustur(kayit, sira=1):
    """Uygulamadaki uyarı sözlüğünü `sabah_brifingi_uyarilari` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"BRF-SQL-{sira}").strip() or f"BRF-SQL-{sira}"
    tarih = str(veri.get("tarih") or "").strip()[:10] or _bugun_tarih_str()
    kategori = str(veri.get("kategori") or "Genel").strip() or "Genel"
    onem = str(veri.get("onem_seviyesi") or veri.get("onem") or "Orta").strip() or "Orta"
    baslik = str(veri.get("baslik") or "Sabah Brifingi Uyarısı").strip() or "Sabah Brifingi Uyarısı"
    detay = str(veri.get("detay") or "").strip()
    kaynak_id = str(veri.get("kaynak_id") or "").strip()
    durum = str(veri.get("durum") or "Aktif").strip() or "Aktif"
    guncelleyen = str(veri.get("guncelleyen") or "").strip()
    guncelleme_zamani = str(veri.get("guncelleme_zamani") or "").strip() or _simdi_zaman_str()

    return {
        "id": kayit_id,
        "tarih": tarih,
        "kategori": kategori,
        "onem_seviyesi": onem,
        "baslik": baslik,
        "detay": detay,
        "kaynak_id": kaynak_id,
        "durum": durum,
        "guncelleyen": guncelleyen,
        "guncelleme_zamani": guncelleme_zamani,
    }


def satir_sabah_uyarisina_donustur(satir):
    """`sabah_brifingi_uyarilari` tablo satırını uygulama sözlüğüne çevirir."""
    row = satir if isinstance(satir, dict) else {}
    return {
        "id": str(row.get("id") or "").strip(),
        "tarih": str(row.get("tarih") or "").strip()[:10],
        "kategori": str(row.get("kategori") or "Genel").strip() or "Genel",
        "onem_seviyesi": str(row.get("onem_seviyesi") or "Orta").strip() or "Orta",
        "baslik": str(row.get("baslik") or "Sabah Brifingi Uyarısı").strip() or "Sabah Brifingi Uyarısı",
        "detay": str(row.get("detay") or "").strip(),
        "kaynak_id": str(row.get("kaynak_id") or "").strip(),
        "durum": str(row.get("durum") or "Aktif").strip() or "Aktif",
        "guncelleyen": str(row.get("guncelleyen") or "").strip(),
        "guncelleme_zamani": str(row.get("guncelleme_zamani") or "").strip(),
    }


def sabah_brifingi_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`sabah_brifingi_uyarilari` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/sabah_brifingi_uyarilari",
            headers=headers_fn(),
            params={"select": "*", "order": "tarih.desc,id.desc"},
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
    return "ok", [satir_sabah_uyarisina_donustur(r) for r in rows if isinstance(r, dict)]


def sabah_brifingi_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`sabah_brifingi_uyarilari` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        sabah_uyarisini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/sabah_brifingi_uyarilari",
            headers=headers_fn(),
            params={"select": "id"},
            timeout=timeout,
        )
        if mevcut_resp.status_code != 200:
            return False, f"Mevcut satırlar okunamadı (HTTP {mevcut_resp.status_code})"

        mevcut_veri = mevcut_resp.json() or []
        mevcut_idler = {
            str(r.get("id")).strip()
            for r in mevcut_veri
            if isinstance(r, dict) and str(r.get("id") or "").strip()
        }

        silinecek_idler = mevcut_idler - aktif_idler
        for sil_id in silinecek_idler:
            filtre_degeri = f"eq.{quote(sil_id, safe='')}"
            del_resp = session_fn().delete(
                f"{url}/rest/v1/sabah_brifingi_uyarilari",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": filtre_degeri},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/sabah_brifingi_uyarilari",
                headers=headers_fn({
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=representation",
                }),
                json=satirlar,
                timeout=timeout,
            )
            if up_resp.status_code not in (200, 201):
                return False, f"Yazma hatası (HTTP {up_resp.status_code})"
            try:
                donen = up_resp.json()
            except Exception:
                donen = None
            if isinstance(donen, list) and donen:
                return True, [satir_sabah_uyarisina_donustur(r) for r in donen if isinstance(r, dict)]
            return True, satirlar

        return True, []
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
