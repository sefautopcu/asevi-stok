"""Supabase `haftalik_menu` ilişkisel tablosu için okuma ve yazma yardımcıları."""

_ANA_SUTUNLAR = {
    "id",
    "hafta_baslangic",
    "gun_adi",
    "tarih",
    "ogun_turu",
    "recete_id",
    "yemek_adi",
    "tahmini_porsiyon",
    "durum",
    "notlar",
    "olusturma_zamani",
}


def _tam_sayi_veya_varsayilan(deger, varsayilan=0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return int(float(str(deger).replace(",", ".")))
    except (TypeError, ValueError):
        return varsayilan


def _hafta_baslangici_hesapla(tarih_str):
    """YYYY-MM-DD tarihinden ilgili haftanın Pazartesi tarihini döndürür."""
    metin = str(tarih_str or "").strip()[:10]
    try:
        import datetime

        d = datetime.date.fromisoformat(metin)
        pazartesi = d - datetime.timedelta(days=d.weekday())
        return pazartesi.isoformat()
    except ValueError:
        return ""


def menu_kaydini_satira_donustur(kayit, sira=1):
    """Uygulamadaki haftalık menü sözlüğünü `haftalik_menu` tablo satırına çevirir."""
    veri = kayit if isinstance(kayit, dict) else {}
    kayit_id = str(veri.get("id") or f"HMN-SQL-{sira}").strip()
    tarih = str(veri.get("tarih") or "").strip()
    hafta_baslangic = str(veri.get("hafta_baslangic") or "").strip() or _hafta_baslangici_hesapla(tarih)

    return {
        "id": kayit_id,
        "hafta_baslangic": hafta_baslangic,
        "gun_adi": str(veri.get("gun_adi") or "").strip(),
        "tarih": tarih,
        "ogun_turu": str(veri.get("ogun_turu") or "Ana Öğün").strip(),
        "recete_id": str(veri.get("recete_id") or "").strip(),
        "yemek_adi": str(veri.get("yemek_adi") or "").strip(),
        "tahmini_porsiyon": _tam_sayi_veya_varsayilan(veri.get("tahmini_porsiyon"), 0),
        "durum": str(veri.get("durum") or "Planlandı").strip(),
        "notlar": str(veri.get("notlar") or "").strip(),
    }


def satir_menu_kaydina_donustur(satir):
    """`haftalik_menu` tablo satırını uygulamanın beklediği sözlüğe çevirir."""
    row = satir if isinstance(satir, dict) else {}
    tarih = str(row.get("tarih") or "")
    return {
        "id": str(row.get("id") or ""),
        "hafta_baslangic": str(row.get("hafta_baslangic") or "") or _hafta_baslangici_hesapla(tarih),
        "gun_adi": str(row.get("gun_adi") or ""),
        "tarih": tarih,
        "ogun_turu": str(row.get("ogun_turu") or "Ana Öğün"),
        "recete_id": str(row.get("recete_id") or ""),
        "yemek_adi": str(row.get("yemek_adi") or ""),
        "tahmini_porsiyon": _tam_sayi_veya_varsayilan(row.get("tahmini_porsiyon"), 0),
        "durum": str(row.get("durum") or "Planlandı"),
        "notlar": str(row.get("notlar") or ""),
    }


def haftalik_menu_sql_oku(url, headers_fn, session_fn, timeout=10):
    """`haftalik_menu` tablosundan kayıtları okur; ('ok', liste) veya ('hata', mesaj) döner."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/haftalik_menu",
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
    return "ok", [satir_menu_kaydina_donustur(r) for r in rows]


def haftalik_menu_sql_kaydet(veri_listesi, url, headers_fn, session_fn, timeout=10):
    """`haftalik_menu` tablosunu güncel listeyle senkronize eder."""
    liste = veri_listesi if isinstance(veri_listesi, list) else []
    satirlar = [
        menu_kaydini_satira_donustur(kayit, sira=idx)
        for idx, kayit in enumerate(liste, start=1)
    ]
    aktif_idler = {s["id"] for s in satirlar}

    try:
        mevcut_resp = session_fn().get(
            f"{url}/rest/v1/haftalik_menu",
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
                f"{url}/rest/v1/haftalik_menu",
                headers=headers_fn({"Prefer": "return=minimal"}),
                params={"id": f"eq.{sil_id}"},
                timeout=timeout,
            )
            if del_resp.status_code not in (200, 204):
                return False, f"Silme hatası ({sil_id}: HTTP {del_resp.status_code})"

        if satirlar:
            up_resp = session_fn().post(
                f"{url}/rest/v1/haftalik_menu",
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
                return True, [satir_menu_kaydina_donustur(r) for r in donen]

        return True, liste
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
