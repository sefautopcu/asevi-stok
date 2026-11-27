"""Supabase `denetim_izi` ilişkisel tablosu için okuma ve yazma yardımcıları."""

import datetime
import json
from urllib.parse import quote


def _json_veya_metin(deger):
    """Sözlük/liste veya metin verisini JSON/string biçiminde güvenli şekilde döndürür."""
    if deger is None:
        return ""
    if isinstance(deger, str):
        return deger
    if isinstance(deger, (dict, list)):
        try:
            return json.dumps(deger, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(deger)
    return str(deger)


def _simdi_zaman_damgasi():
    try:
        from zoneinfo import ZoneInfo

        return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def denetim_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki denetim izi sözlüğünü `denetim_izi` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"DNT-SQL-{sira}").strip() or f"DNT-SQL-{sira}"
    zaman = str(veri.get("zaman") or veri.get("tarih") or "").strip() or _simdi_zaman_damgasi()
    kullanici = str(veri.get("kullanici") or veri.get("kullanici_adi") or "sistem").strip() or "sistem"
    rol = str(veri.get("rol") or "").strip()
    modul = str(veri.get("modul") or "Genel").strip() or "Genel"
    islem = str(veri.get("islem") or veri.get("aksiyon") or "Güncelleme").strip() or "Güncelleme"
    hedef_id = str(veri.get("kayit_id") or veri.get("hedef_id") or "").strip()

    return {
        "id": kayit_id,
        "zaman": zaman,
        "kullanici": kullanici,
        "rol": rol,
        "modul": modul,
        "islem": islem,
        "kayit_id": hedef_id,
        "onceki_veri": _json_veya_metin(veri.get("onceki_veri")),
        "sonraki_veri": _json_veya_metin(veri.get("sonraki_veri")),
    }


def satir_denetim_kaydina_donustur(satir):
    """`denetim_izi` tablo satırını uygulamanın beklediği sözlüğe çevirir."""
    row = satir if isinstance(satir, dict) else {}
    return {
        "id": str(row.get("id") or "").strip(),
        "zaman": str(row.get("zaman") or "").strip(),
        "kullanici": str(row.get("kullanici") or "sistem").strip() or "sistem",
        "rol": str(row.get("rol") or "").strip(),
        "modul": str(row.get("modul") or "Genel").strip() or "Genel",
        "islem": str(row.get("islem") or "Güncelleme").strip() or "Güncelleme",
        "kayit_id": str(row.get("kayit_id") or "").strip(),
        "onceki_veri": _json_veya_metin(row.get("onceki_veri")),
        "sonraki_veri": _json_veya_metin(row.get("sonraki_veri")),
    }


def denetim_izi_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`denetim_izi` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/denetim_izi",
            headers=headers_fn(),
            params={"select": "*", "order": "zaman.desc,id.desc"},
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
    return "ok", [satir_denetim_kaydina_donustur(r) for r in rows if isinstance(r, dict)]


def denetim_izi_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`denetim_izi` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        denetim_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/denetim_izi",
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
                f"{url}/rest/v1/denetim_izi",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": filtre_degeri},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/denetim_izi",
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
                return True, [satir_denetim_kaydina_donustur(r) for r in donen if isinstance(r, dict)]
            return True, satirlar

        return True, []
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
