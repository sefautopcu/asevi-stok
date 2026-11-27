from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any, Callable, Dict, List, Optional

import requests

from src.supabase_db import SUPABASE_KEY, SUPABASE_URL, _supa_basliklar, get_http_session

_META_ETIKET_DESENI = re.compile(r"\s*<!--BOM_META:(.*?)-->\s*$", re.DOTALL)

ALERJEN_SOZLUGU: Dict[str, List[str]] = {
    "Gluten": ["un", "buğday", "bulgur", "irmik", "makarna", "şehriye", "erişte", "ekmek", "galeta", "arpa", "yulaf"],
    "Laktoz / Süt": ["süt", "yoğurt", "tereyağı", "tereyag", "peynir", "krema", "kaşar", "kaymak", "lor"],
    "Yumurta": ["yumurta"],
    "Kuruyemiş / Fıstık": ["ceviz", "fındık", "fıstık", "badem", "susam", "tahin"],
    "Kereviz": ["kereviz"],
    "Hardal": ["hardal"],
    "Soya": ["soya"],
}

RECETE_DURUMLARI = [
    "Taslak",
    "Onay Bekliyor",
    "Onaylandı / Aktif",
    "Arşivlendi",
]


def _guvenli_float(deger: Any, varsayilan: float = 0.0) -> float:
    if deger is None or deger == "":
        return varsayilan
    try:
        return float(deger)
    except (TypeError, ValueError):
        return varsayilan


def _not_ve_meta_ayir(ham_not: Any) -> tuple[str, Dict[str, Any]]:
    metin = str(ham_not or "")
    eslesme = _META_ETIKET_DESENI.search(metin)
    if not eslesme:
        return metin.strip(), {}
    temiz_not = _META_ETIKET_DESENI.sub("", metin).strip()
    try:
        meta = json.loads(eslesme.group(1))
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    return temiz_not, meta


def _not_ve_meta_birlestir(temiz_not: str, meta: Dict[str, Any]) -> str:
    temiz = str(temiz_not or "").strip()
    if not meta:
        return temiz
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    if temiz:
        return f"{temiz}\n<!--BOM_META:{meta_json}-->"
    return f"<!--BOM_META:{meta_json}-->"


def alerjenleri_otomatik_tespit_et(
    kalemler: List[Dict[str, Any]],
    manuel_alerjenler: Optional[List[str]] = None,
) -> List[str]:
    bulunanlar = set(str(a).strip() for a in (manuel_alerjenler or []) if str(a).strip())
    for k in kalemler or []:
        urun = str(k.get("urun_adi", "")).strip().lower()
        if not urun:
            continue
        for alerjen, anahtarlar in ALERJEN_SOZLUGU.items():
            if any(kelime in urun for kelime in anahtarlar):
                bulunanlar.add(alerjen)
    return sorted(bulunanlar)


def _birim_gramaja_cevir(miktar: float, birim: str) -> float:
    b = str(birim or "kg").strip().lower()
    if b in ("kg", "lt", "l"):
        return miktar * 1000.0
    if b in ("gr", "g", "ml"):
        return miktar
    return 0.0


def _birim_donusum_katsayisi(kullanilan_birim: str, fiyat_birimi: Optional[str] = None) -> float:
    """
    Kullanılan birim (ör. gr, ml) ile fiyat birimi (ör. kg, lt) farklıysa dönüşüm katsayısını döndürür.
    Örn: 50 gr kullanıldıysa ve fiyat kg bazındaysa 0.05 katsayısı döner.
    """
    kb = str(kullanilan_birim or "kg").strip().lower()
    fb = str(fiyat_birimi or "").strip().lower()

    if fb in ("kg", "lt", "l"):
        if kb in ("gr", "g", "ml"):
            return 0.001
        return 1.0
    if fb in ("gr", "g", "ml"):
        if kb in ("kg", "lt", "l"):
            return 1000.0
        return 1.0

    # Fiyat birimi belirtilmemişse bile gr/ml girildiğinde stok fiyatı standart olarak kg/lt bazlıdır
    if kb in ("gr", "g", "ml") and fb == "oto_kg_lt":
        return 0.001
    return 1.0


def recete_kalemlerini_olcekle(
    kalemler: List[Dict[str, Any]],
    eski_porsiyon: float,
    yeni_porsiyon: float,
) -> List[Dict[str, Any]]:
    """Standart porsiyon sayısı değiştiğinde malzeme miktarlarını orantılı ölçekler."""
    eski = _guvenli_float(eski_porsiyon, 100.0)
    yeni = _guvenli_float(yeni_porsiyon, 100.0)
    if eski <= 0 or yeni <= 0 or abs(eski - yeni) < 1e-9:
        return [dict(k) for k in (kalemler or [])]

    oran = yeni / eski
    olcekli: List[Dict[str, Any]] = []
    for k in kalemler or []:
        satir = dict(k)
        if "miktar" in satir:
            satir["miktar"] = round(_guvenli_float(satir.get("miktar"), 0.0) * oran, 4)
        if "porsiyon_basi_miktar" in satir:
            satir["porsiyon_basi_miktar"] = round(
                _guvenli_float(satir.get("porsiyon_basi_miktar"), 0.0), 6
            )
        olcekli.append(satir)
    return olcekli


def hesapla_kalori_ve_maliyet(
    kalemler: List[Dict[str, Any]],
    porsiyon_sayisi: float = 1.0,
    son_fiyat_saglayici: Optional[Callable[[str], Optional[float]]] = None,
    yari_mamul_sozlugu: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Reçete veya üretim kalemleri için toplam kalori, maliyet, fire sonrası net gramaj
    ve satın alma talebi listesini hesaplar.
    Boş malzeme satırları canlı hesaplamaya dahil edilmez.
    """
    porsiyon = _guvenli_float(porsiyon_sayisi, 1.0)
    if porsiyon <= 0:
        porsiyon = 1.0

    toplam_kalori = 0.0
    toplam_maliyet = 0.0
    toplam_net_gram = 0.0
    detay_satirlar: List[Dict[str, Any]] = []
    satin_alma_talepleri: List[Dict[str, Any]] = []

    for kalem in kalemler or []:
        urun_adi = str(kalem.get("urun_adi", "")).strip()
        if not urun_adi:
            continue

        birim = str(kalem.get("birim", "kg")).strip() or "kg"
        brut_miktar = _guvenli_float(
            kalem.get("miktar", kalem.get("porsiyon_basi_miktar", 0.0)), 0.0
        )
        fire_orani = min(max(_guvenli_float(kalem.get("fire_orani", 0.0), 0.0), 0.0), 99.0)
        net_miktar = round(brut_miktar * (1.0 - fire_orani / 100.0), 4)

        kalori_birim = _guvenli_float(
            kalem.get("kalori", kalem.get("porsiyon_basi_kalori", 0.0)), 0.0
        )
        kaynak = str(kalem.get("kaynak", "STOK")).strip().upper() or "STOK"
        fiyat_birimi = kalem.get("fiyat_birimi")

        ham_fiyat = kalem.get(
            "birim_fiyat", kalem.get("referans_birim_fiyat", None)
        )
        birim_fiyat = _guvenli_float(ham_fiyat, -1.0)

        if (
            kaynak in ("YARI_MAMUL", "YARI MAMUL")
            and yari_mamul_sozlugu
            and urun_adi in yari_mamul_sozlugu
        ):
            alt_recete = yari_mamul_sozlugu[urun_adi]
            if kalori_birim <= 0:
                kalori_birim = _guvenli_float(alt_recete.get("porsiyon_basi_kalori", 0.0), 0.0)
            if birim_fiyat < 0:
                birim_fiyat = _guvenli_float(alt_recete.get("porsiyon_basi_maliyet", 0.0), 0.0)

        if birim_fiyat < 0 and son_fiyat_saglayici is not None and urun_adi:
            bulunan_fiyat = son_fiyat_saglayici(urun_adi)
            birim_fiyat = _guvenli_float(bulunan_fiyat, 0.0)
            if not fiyat_birimi and birim.lower() in ("gr", "g", "ml"):
                fiyat_birimi = "oto_kg_lt"
        elif birim_fiyat < 0:
            birim_fiyat = 0.0

        if kaynak in ("BAĞIŞ", "BAGIS", "SIFIR MALİYET", "SIFIR_MALIYET") or birim_fiyat <= 0.0:
            efektif_birim_fiyat = 0.0
            if kaynak in ("BAĞIŞ", "BAGIS"):
                kaynak_norm = "BAĞIŞ"
            elif kaynak in ("SIFIR MALİYET", "SIFIR_MALIYET"):
                kaynak_norm = "SIFIR MALİYET"
            else:
                kaynak_norm = kaynak
        else:
            efektif_birim_fiyat = birim_fiyat
            kaynak_norm = kaynak

        fiyat_carpani = _birim_donusum_katsayisi(birim, fiyat_birimi)
        kalori_carpani = net_miktar if fire_orani > 0 else brut_miktar
        satir_kalori = round(kalori_carpani * kalori_birim, 2)
        satir_maliyet = round(brut_miktar * fiyat_carpani * efektif_birim_fiyat, 2)
        satir_net_gram = _birim_gramaja_cevir(net_miktar, birim)

        toplam_kalori += satir_kalori
        toplam_maliyet += satir_maliyet
        toplam_net_gram += satir_net_gram

        if kaynak_norm in ("SATIN_ALMA", "SATIN ALMA") and brut_miktar > 0 and urun_adi:
            satin_alma_talepleri.append(
                {
                    "urun_adi": urun_adi,
                    "birim": birim,
                    "talep_miktari": brut_miktar,
                    "tahmini_birim_fiyat": efektif_birim_fiyat,
                    "tahmini_tutar": satir_maliyet,
                }
            )

        detay_satirlar.append(
            {
                "urun_adi": urun_adi,
                "birim": birim,
                "miktar": brut_miktar,
                "fire_orani": fire_orani,
                "net_miktar": net_miktar,
                "kaynak": kaynak_norm,
                "fiyat_birimi": fiyat_birimi,
                "efektif_birim_fiyat": efektif_birim_fiyat,
                "satir_kalori": satir_kalori,
                "satir_maliyet": satir_maliyet,
            }
        )

    toplam_kalori = round(toplam_kalori, 2)
    toplam_maliyet = round(toplam_maliyet, 2)
    toplam_net_gram = round(toplam_net_gram, 2)

    return {
        "porsiyon_sayisi": porsiyon,
        "toplam_kalori": toplam_kalori,
        "porsiyon_basi_kalori": round(toplam_kalori / porsiyon, 2),
        "toplam_maliyet": toplam_maliyet,
        "porsiyon_basi_maliyet": round(toplam_maliyet / porsiyon, 2),
        "toplam_net_gram": toplam_net_gram,
        "porsiyon_basi_gram": round(toplam_net_gram / porsiyon, 1),
        "kalemler": detay_satirlar,
        "satin_alma_talepleri": satin_alma_talepleri,
    }


def _rest_supabase_aktif_mi() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _recete_kaydini_zenginlestir(ham_kayit: Dict[str, Any]) -> Dict[str, Any]:
    kayit = dict(ham_kayit)
    temiz_not, meta = _not_ve_meta_ayir(kayit.get("notlar", ""))
    kayit["notlar"] = temiz_not

    porsiyon = _guvenli_float(kayit.get("porsiyon_sayisi", 100.0), 100.0)
    db_kalemler = list(
        kayit.get("yemek_recete_kalemleri")
        or kayit.get("kalemler")
        or []
    )
    meta_kalemler = meta.get("kalemler_detay") if isinstance(meta.get("kalemler_detay"), list) else []

    birlesik_kalemler: List[Dict[str, Any]] = []
    kaynak_liste = meta_kalemler if meta_kalemler else db_kalemler
    for idx, k in enumerate(kaynak_liste):
        db_k = db_kalemler[idx] if idx < len(db_kalemler) else {}
        miktar = (
            _guvenli_float(k.get("miktar"), 0.0)
            if "miktar" in k
            else round(_guvenli_float(k.get("porsiyon_basi_miktar", db_k.get("porsiyon_basi_miktar", 0.0)), 0.0) * porsiyon, 4)
        )
        kalori = _guvenli_float(
            k.get("kalori", k.get("porsiyon_basi_kalori", db_k.get("porsiyon_basi_kalori", 0.0))),
            0.0,
        )
        birim_fiyat = _guvenli_float(
            k.get("birim_fiyat", k.get("referans_birim_fiyat", db_k.get("referans_birim_fiyat", 0.0))),
            0.0,
        )
        birlesik_kalemler.append(
            {
                "urun_adi": str(k.get("urun_adi", db_k.get("urun_adi", ""))).strip(),
                "birim": str(k.get("birim", db_k.get("birim", "kg"))).strip() or "kg",
                "miktar": miktar,
                "fire_orani": _guvenli_float(k.get("fire_orani", 0.0), 0.0),
                "kalori": kalori,
                "kaynak": str(k.get("kaynak", db_k.get("kaynak", "STOK"))).strip() or "STOK",
                "fiyat_birimi": k.get("fiyat_birimi"),
                "birim_fiyat": birim_fiyat,
            }
        )

    hesap = hesapla_kalori_ve_maliyet(birlesik_kalemler, porsiyon_sayisi=porsiyon)
    kayit["kalemler"] = birlesik_kalemler
    kayit["toplam_kalori"] = hesap["toplam_kalori"]
    kayit["porsiyon_basi_kalori"] = hesap["porsiyon_basi_kalori"]
    kayit["toplam_maliyet"] = hesap["toplam_maliyet"]
    kayit["porsiyon_basi_maliyet"] = hesap["porsiyon_basi_maliyet"]
    kayit["toplam_net_gram"] = hesap["toplam_net_gram"]
    kayit["porsiyon_basi_gram"] = hesap["porsiyon_basi_gram"]
    kayit["durum"] = meta.get(
        "durum",
        "Onaylandı / Aktif" if bool(kayit.get("aktif", True)) else "Taslak",
    )
    kayit["revizyon_no"] = int(meta.get("revizyon_no", 1) or 1)
    kayit["revizyon_gecmisi"] = list(meta.get("revizyon_gecmisi") or [])
    kayit["sunum_notu"] = str(meta.get("sunum_notu", "")).strip()
    kayit["maliyet_kilidi"] = bool(meta.get("maliyet_kilidi", False))
    kayit["alerjenler"] = alerjenleri_otomatik_tespit_et(
        birlesik_kalemler, meta.get("alerjenler")
    )
    return kayit


def _rest_receteleri_oku() -> List[Dict[str, Any]]:
    oturum = get_http_session()
    url = (
        f"{SUPABASE_URL}/rest/v1/yemek_receteleri"
        "?select=*,yemek_recete_kalemleri(*)&order=id.asc"
    )
    yanit = oturum.get(url, headers=_supa_basliklar(), timeout=10)
    if yanit.status_code not in (200, 206):
        raise RuntimeError(
            f"Supabase reçete okuma hatası (HTTP {yanit.status_code}): {yanit.text[:200]}"
        )
    satirlar = yanit.json()
    if not isinstance(satirlar, list):
        return []
    return [_recete_kaydini_zenginlestir(r) for r in satirlar]


def _rest_recete_kaydet(
    header_row: Dict[str, Any],
    kalemler: List[Dict[str, Any]],
    porsiyon_sayisi: float,
    simdi: str,
) -> Dict[str, Any]:
    oturum = get_http_session()
    basliklar = _supa_basliklar(
        {
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
    )
    url_baslik = f"{SUPABASE_URL}/rest/v1/yemek_receteleri?on_conflict=recete_kodu"
    yanit = oturum.post(url_baslik, headers=basliklar, json=header_row, timeout=10)
    if yanit.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase reçete başlığı kaydedilemedi (HTTP {yanit.status_code}): {yanit.text[:250]}"
        )

    kaydedilen_liste = yanit.json()
    kaydedilen_baslik = (
        kaydedilen_liste[0]
        if isinstance(kaydedilen_liste, list) and kaydedilen_liste
        else dict(header_row)
    )
    recete_id = kaydedilen_baslik.get("id")

    if recete_id is not None:
        sil_url = (
            f"{SUPABASE_URL}/rest/v1/yemek_recete_kalemleri?recete_id=eq.{recete_id}"
        )
        requests.delete(sil_url, headers=_supa_basliklar(), timeout=10)

        porsiyon = porsiyon_sayisi if porsiyon_sayisi > 0 else 1.0
        kalem_satirlari = []
        for k in kalemler:
            miktar = _guvenli_float(
                k.get("miktar", k.get("porsiyon_basi_miktar", 0.0)), 0.0
            )
            kalori = _guvenli_float(
                k.get("kalori", k.get("porsiyon_basi_kalori", 0.0)), 0.0
            )
            kaynak = str(k.get("kaynak", "STOK")).strip().upper() or "STOK"
            fiyat = _guvenli_float(
                k.get("birim_fiyat", k.get("referans_birim_fiyat", 0.0)), 0.0
            )
            if kaynak in ("BAĞIŞ", "BAGIS", "SIFIR MALİYET", "SIFIR_MALIYET") or fiyat <= 0.0:
                fiyat = 0.0
                kaynak_db = "BAĞIŞ" if kaynak in ("BAĞIŞ", "BAGIS") else "STOK"
            else:
                kaynak_db = kaynak if kaynak in ("STOK", "BAĞIŞ", "SATIN_ALMA") else "STOK"

            kalem_satirlari.append(
                {
                    "recete_id": recete_id,
                    "urun_adi": str(k.get("urun_adi", "")).strip() or "Malzeme",
                    "birim": str(k.get("birim", "kg")).strip() or "kg",
                    "porsiyon_basi_miktar": round(miktar / porsiyon, 6),
                    "porsiyon_basi_kalori": round(kalori, 4),
                    "kaynak": kaynak_db,
                    "referans_birim_fiyat": round(fiyat, 4),
                    "olusturulma_tarihi": simdi,
                }
            )

        if kalem_satirlari:
            kalem_url = f"{SUPABASE_URL}/rest/v1/yemek_recete_kalemleri"
            k_yanit = oturum.post(
                kalem_url,
                headers=_supa_basliklar(
                    {"Content-Type": "application/json", "Prefer": "return=representation"}
                ),
                json=kalem_satirlari,
                timeout=10,
            )
            if k_yanit.status_code not in (200, 201):
                raise RuntimeError(
                    f"Supabase reçete kalemleri kaydedilemedi (HTTP {k_yanit.status_code}): {k_yanit.text[:250]}"
                )

    return kaydedilen_baslik


def yemek_receteleri_sql_oku(
    client: Any = None,
    bellek_depo: Optional[List[Dict[str, Any]]] = None,
    filtre_aktif: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Supabase 'yemek_receteleri' tablosundan reçeteleri okur.
    Test veya çevrimdışı modda bellek_depo üzerinden çalışabilir.
    """
    if bellek_depo is not None:
        kayitlar = [_recete_kaydini_zenginlestir(r) for r in bellek_depo]
    elif client is not None:
        response = (
            client.table("yemek_receteleri")
            .select("*, yemek_recete_kalemleri(*)")
            .order("id", desc=False)
            .execute()
        )
        kayitlar = [
            _recete_kaydini_zenginlestir(r)
            for r in (getattr(response, "data", None) or [])
        ]
    elif _rest_supabase_aktif_mi():
        kayitlar = _rest_receteleri_oku()
    else:
        kayitlar = []

    if filtre_aktif is not None:
        kayitlar = [r for r in kayitlar if bool(r.get("aktif", True)) is filtre_aktif]

    return kayitlar


def yemek_receteleri_sql_kaydet(
    recete: Dict[str, Any],
    client: Any = None,
    bellek_depo: Optional[List[Dict[str, Any]]] = None,
    son_fiyat_saglayici: Optional[Callable[[str], Optional[float]]] = None,
    yari_mamul_sozlugu: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Yeni veya güncellenmiş yemek reçetesini kaydeder.
    Mevcut kayıtları silmez; recete_kodu bazında revizyon artırarak güncelleme veya ekleme yapar.
    """
    simdi = datetime.now(timezone.utc).isoformat()
    recete_kodu = str(recete.get("recete_kodu", "")).strip()
    yemek_adi = str(recete.get("yemek_adi", "")).strip()

    if not recete_kodu:
        raise ValueError("recete_kodu boş olamaz.")
    if not yemek_adi:
        raise ValueError("yemek_adi boş olamaz.")

    kalemler = [dict(k) for k in (recete.get("kalemler") or []) if str(k.get("urun_adi", "")).strip()]
    porsiyon_sayisi = _guvenli_float(recete.get("porsiyon_sayisi", 100), 100.0)
    ozet = hesapla_kalori_ve_maliyet(
        kalemler,
        porsiyon_sayisi=porsiyon_sayisi,
        son_fiyat_saglayici=son_fiyat_saglayici,
        yari_mamul_sozlugu=yari_mamul_sozlugu,
    )

    durum = str(recete.get("durum", "")).strip()
    if durum not in RECETE_DURUMLARI:
        durum = "Onaylandı / Aktif" if bool(recete.get("aktif", True)) else "Taslak"
    aktif_durum = bool(recete.get("aktif", durum == "Onaylandı / Aktif"))
    if durum == "Arşivlendi":
        aktif_durum = False

    alerjenler = alerjenleri_otomatik_tespit_et(kalemler, recete.get("alerjenler"))
    temiz_not, _ = _not_ve_meta_ayir(recete.get("notlar", ""))
    sunum_notu = str(recete.get("sunum_notu", "")).strip()
    maliyet_kilidi = bool(recete.get("maliyet_kilidi", False))

    mevcut_kayit = None
    if bellek_depo is not None:
        mevcut_kayit = next(
            (m for m in bellek_depo if str(m.get("recete_kodu", "")).strip() == recete_kodu),
            None,
        )
    elif client is None and _rest_supabase_aktif_mi():
        mevcut_liste = _rest_receteleri_oku()
        mevcut_kayit = next(
            (m for m in mevcut_liste if str(m.get("recete_kodu", "")).strip() == recete_kodu),
            None,
        )

    revizyon_gecmisi: List[Dict[str, Any]] = []
    if mevcut_kayit is not None:
        zengin_mevcut = _recete_kaydini_zenginlestir(mevcut_kayit)
        eski_rev = int(zengin_mevcut.get("revizyon_no", 1) or 1)
        revizyon_no = eski_rev + 1
        revizyon_gecmisi = list(zengin_mevcut.get("revizyon_gecmisi") or [])
        revizyon_gecmisi.append(
            {
                "revizyon_no": eski_rev,
                "tarih": zengin_mevcut.get("guncellenme_tarihi", simdi),
                "yemek_adi": zengin_mevcut.get("yemek_adi", yemek_adi),
                "porsiyon_sayisi": zengin_mevcut.get("porsiyon_sayisi", porsiyon_sayisi),
                "toplam_maliyet": zengin_mevcut.get("toplam_maliyet", 0.0),
                "toplam_kalori": zengin_mevcut.get("toplam_kalori", 0.0),
                "durum": "Arşivlendi (Eski Sürüm)",
            }
        )
        revizyon_gecmisi = revizyon_gecmisi[-15:]
    else:
        revizyon_no = int(recete.get("revizyon_no", 1) or 1)

    meta_veri = {
        "durum": durum,
        "revizyon_no": revizyon_no,
        "revizyon_gecmisi": revizyon_gecmisi,
        "alerjenler": alerjenler,
        "sunum_notu": sunum_notu,
        "maliyet_kilidi": maliyet_kilidi,
        "kalemler_detay": [
            {
                "urun_adi": d["urun_adi"],
                "birim": d["birim"],
                "miktar": d["miktar"],
                "fire_orani": d["fire_orani"],
                "kalori": _guvenli_float(
                    next(
                        (
                            k.get("kalori", 0.0)
                            for k in kalemler
                            if str(k.get("urun_adi", "")).strip() == d["urun_adi"]
                        ),
                        0.0,
                    ),
                    0.0,
                ),
                "kaynak": d["kaynak"],
                "fiyat_birimi": d.get("fiyat_birimi"),
                "birim_fiyat": d["efektif_birim_fiyat"],
            }
            for d in ozet["kalemler"]
        ],
    }

    kayit_payload: Dict[str, Any] = {
        "recete_kodu": recete_kodu,
        "yemek_adi": yemek_adi,
        "kategori": str(recete.get("kategori", "Ana Yemek")).strip() or "Ana Yemek",
        "porsiyon_sayisi": porsiyon_sayisi,
        "aktif": aktif_durum,
        "notlar": temiz_not,
        "sunum_notu": sunum_notu,
        "maliyet_kilidi": maliyet_kilidi,
        "durum": durum,
        "revizyon_no": revizyon_no,
        "revizyon_gecmisi": revizyon_gecmisi,
        "alerjenler": alerjenler,
        "toplam_kalori": ozet["toplam_kalori"],
        "porsiyon_basi_kalori": ozet["porsiyon_basi_kalori"],
        "toplam_maliyet": ozet["toplam_maliyet"],
        "porsiyon_basi_maliyet": ozet["porsiyon_basi_maliyet"],
        "toplam_net_gram": ozet["toplam_net_gram"],
        "porsiyon_basi_gram": ozet["porsiyon_basi_gram"],
        "satin_alma_talepleri": ozet["satin_alma_talepleri"],
        "kalemler": meta_veri["kalemler_detay"],
        "guncellenme_tarihi": simdi,
    }

    if bellek_depo is not None:
        for idx, mevcut in enumerate(bellek_depo):
            if str(mevcut.get("recete_kodu", "")).strip() == recete_kodu:
                guncel = {**mevcut, **kayit_payload}
                bellek_depo[idx] = guncel
                return guncel
        yeni_kayit = {
            "id": len(bellek_depo) + 1,
            "olusturulma_tarihi": simdi,
            **kayit_payload,
        }
        bellek_depo.append(yeni_kayit)
        return yeni_kayit

    header_row = {
        "recete_kodu": recete_kodu,
        "yemek_adi": yemek_adi,
        "kategori": kayit_payload["kategori"],
        "porsiyon_sayisi": porsiyon_sayisi,
        "aktif": aktif_durum,
        "notlar": _not_ve_meta_birlestir(temiz_not, meta_veri),
        "guncellenme_tarihi": simdi,
    }

    if client is not None:
        resp = (
            client.table("yemek_receteleri")
            .upsert(header_row, on_conflict="recete_kodu")
            .execute()
        )
        data = getattr(resp, "data", None) or [header_row]
        return {**kayit_payload, **(data[0] if isinstance(data, list) else {})}

    if _rest_supabase_aktif_mi():
        kaydedilen = _rest_recete_kaydet(
            header_row=header_row,
            kalemler=meta_veri["kalemler_detay"],
            porsiyon_sayisi=porsiyon_sayisi,
            simdi=simdi,
        )
        return {**kayit_payload, **kaydedilen, "notlar": temiz_not}

    return kayit_payload
