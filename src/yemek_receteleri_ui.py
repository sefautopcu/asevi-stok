from __future__ import annotations

from datetime import datetime
import html
import re
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from src.ui_kartlar import (
    bolum_basligi_goster,
    ikon_rozeti_html,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)
from src.yemek_receteleri_sql import (
    ALERJEN_SOZLUGU,
    RECETE_DURUMLARI,
    alerjenleri_otomatik_tespit_et,
    hesapla_kalori_ve_maliyet,
    recete_kalemlerini_olcekle,
    yemek_receteleri_sql_kaydet,
    yemek_receteleri_sql_oku,
)

SAYFA_BASLIGI_YEMEK_RECETELERI = "Hazır Yemek Reçeteleri"

_KAYNAK_SECENEKLERI = [
    "STOK",
    "BAĞIŞ",
    "SIFIR MALİYET",
    "SATIN_ALMA",
    "YARI_MAMUL",
]
_BIRIM_SECENEKLERI = ["kg", "lt", "adet", "gr", "ml", "porsiyon"]
_KATEGORI_SECENEKLERI = ["Çorba", "Ana Yemek", "Pilav / Makarna", "Tatlı / İçecek", "Yarı Mamul / Sos"]


def _temiz_html(blok: str) -> str:
    return "\n".join(satir.strip() for satir in blok.splitlines() if satir.strip())


def _sonraki_recete_kodunu_uret(kayitli_receteler: List[Dict[str, Any]]) -> str:
    """Mevcut REC-XXX kodlarını tarayıp bir sonraki sıradaki kodu (ör. REC-001) üretir."""
    en_buyuk = 0
    for r in kayitli_receteler or []:
        kod = str(r.get("recete_kodu", "")).strip().upper()
        eslesme = re.search(r"(\d+)$", kod)
        if eslesme:
            en_buyuk = max(en_buyuk, int(eslesme.group(1)))
    return f"REC-{en_buyuk + 1:03d}"


def _varsayilan_bom_satiri() -> Dict[str, Any]:
    return {
        "urun_adi": "",
        "birim": "kg",
        "miktar": 0.0,
        "fire_orani": 0.0,
        "kalori": 0.0,
        "kaynak": "STOK",
        "fiyat_birimi": "oto_kg_lt",
        "birim_fiyat": 0.0,
    }


def _bom_durumunu_baslat(
    kayitli_receteler: List[Dict[str, Any]],
    son_fiyat_saglayici: Optional[Callable[[str], Optional[float]]] = None,
    kalori_saglayici: Optional[Callable[[str, str], Optional[float]]] = None,
) -> None:
    bekleyen = st.session_state.pop("bom_bekleyen_yukleme", None)
    if isinstance(bekleyen, dict):
        if bekleyen.get("_temizle"):
            st.session_state["bom_recete_kodu"] = _sonraki_recete_kodunu_uret(kayitli_receteler)
            st.session_state["bom_yemek_adi"] = ""
            st.session_state["bom_notlar"] = ""
            st.session_state["bom_sunum_notu"] = ""
            st.session_state["bom_maliyet_kilidi"] = False
            st.session_state["bom_manuel_alerjen"] = []
            st.session_state["bom_hedef_revizyon"] = 1
            st.session_state["bom_satirlari"] = [_varsayilan_bom_satiri()]
        else:
            _recete_formuna_yukle(bekleyen)

    if not st.session_state.get("bom_recete_kodu"):
        st.session_state["bom_recete_kodu"] = _sonraki_recete_kodunu_uret(kayitli_receteler)

    if "bom_satirlari" not in st.session_state or not st.session_state["bom_satirlari"]:
        st.session_state["bom_satirlari"] = [_varsayilan_bom_satiri()]
    st.session_state.setdefault("bom_porsiyon_son", 100.0)
    st.session_state.setdefault("bom_hedef_revizyon", 1)


def _recete_formuna_yukle(recete: Dict[str, Any]) -> None:
    """Kayıtlı bir reçeteyi düzenleme / yeni revizyon (Rev + 1) için BOM editörüne yükler."""
    st.session_state["bom_recete_kodu"] = str(recete.get("recete_kodu", ""))
    st.session_state["bom_yemek_adi"] = str(recete.get("yemek_adi", ""))
    kat = str(recete.get("kategori", "Çorba"))
    st.session_state["bom_kategori"] = kat if kat in _KATEGORI_SECENEKLERI else "Çorba"
    porsiyon = float(recete.get("porsiyon_sayisi", 100.0) or 100.0)
    st.session_state["bom_porsiyon"] = porsiyon
    st.session_state["bom_porsiyon_son"] = porsiyon
    durum = str(recete.get("durum", "Onaylandı / Aktif"))
    st.session_state["bom_durum"] = durum if durum in RECETE_DURUMLARI else "Onaylandı / Aktif"
    st.session_state["bom_yayinda"] = bool(recete.get("aktif", True))
    st.session_state["bom_notlar"] = str(recete.get("notlar", ""))
    st.session_state["bom_sunum_notu"] = str(recete.get("sunum_notu", ""))
    st.session_state["bom_maliyet_kilidi"] = bool(recete.get("maliyet_kilidi", False))
    st.session_state["bom_manuel_alerjen"] = list(recete.get("alerjenler") or [])
    mevcut_rev = int(recete.get("revizyon_no", 1) or 1)
    st.session_state["bom_hedef_revizyon"] = mevcut_rev + 1

    kalemler = list(recete.get("kalemler") or [])
    if kalemler:
        st.session_state["bom_satirlari"] = [
            {
                "urun_adi": str(k.get("urun_adi", "")),
                "birim": str(k.get("birim", "kg")) if str(k.get("birim", "kg")) in _BIRIM_SECENEKLERI else "kg",
                "miktar": float(k.get("miktar", 0.0) or 0.0),
                "fire_orani": float(k.get("fire_orani", 0.0) or 0.0),
                "kalori": float(k.get("kalori", 0.0) or 0.0),
                "kaynak": str(k.get("kaynak", "STOK")) if str(k.get("kaynak", "STOK")) in _KAYNAK_SECENEKLERI else "STOK",
                "fiyat_birimi": k.get("fiyat_birimi", "oto_kg_lt"),
                "birim_fiyat": float(k.get("birim_fiyat", 0.0) or 0.0),
            }
            for k in kalemler
        ]
    else:
        st.session_state["bom_satirlari"] = [_varsayilan_bom_satiri()]


def _durum_rozeti_stili(durum: str) -> tuple[str, str]:
    harita = {
        "Onaylandı / Aktif": ("#10b981", "rgba(16,185,129,0.14)"),
        "Onay Bekliyor": ("#f59e0b", "rgba(245,158,11,0.14)"),
        "Taslak": ("#38bdf8", "rgba(56,189,248,0.14)"),
        "Arşivlendi": ("#94a3b8", "rgba(148,163,184,0.14)"),
    }
    return harita.get(durum, ("#10b981", "rgba(16,185,129,0.14)"))


def _mutfak_uretim_fisi_html(recete: Dict[str, Any]) -> str:
    """Mutfak personeli için yazdırılabilir üretim fişi HTML çıktısı üretir."""
    kod = html.escape(str(recete.get("recete_kodu", "-")))
    ad = html.escape(str(recete.get("yemek_adi", "-")))
    kat = html.escape(str(recete.get("kategori", "-")))
    porsiyon = float(recete.get("porsiyon_sayisi", 100) or 100)
    rev_no = int(recete.get("revizyon_no", 1) or 1)
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    notlar = html.escape(str(recete.get("notlar", "") or "-"))
    sunum = html.escape(str(recete.get("sunum_notu", "") or "-"))
    alerjenler = ", ".join(recete.get("alerjenler") or []) or "Tespit Edilmedi"

    satir_html = []
    for i, k in enumerate(recete.get("kalemler") or [], start=1):
        brut = float(k.get("miktar", 0) or 0)
        fire = float(k.get("fire_orani", 0) or 0)
        net = round(brut * (1.0 - fire / 100.0), 3)
        satir_html.append(
            f"<tr><td>{i}</td><td>{html.escape(str(k.get('urun_adi', '-')))}</td>"
            f"<td>{brut:.3f} {html.escape(str(k.get('birim', 'kg')))}</td>"
            f"<td>%{fire:.0f}</td><td>{net:.3f} {html.escape(str(k.get('birim', 'kg')))}</td>"
            f"<td>{html.escape(str(k.get('kaynak', 'STOK')))}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><title>Üretim Fişi - {kod}</title>
<style>
body{{font-family:Arial,sans-serif;padding:24px;color:#0f172a}}
h1{{margin:0 0 4px 0;font-size:20px}}
.meta{{font-size:13px;color:#334155;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}}
th,td{{border:1px solid #94a3b8;padding:7px 9px;text-align:left}}
th{{background:#e2e8f0}}
.box{{margin-top:14px;padding:10px;border:1px solid #cbd5e1;background:#f8fafc;font-size:13px}}
</style></head><body onload="window.print()">
<h1>AZİZİYE AŞEVİ — MUTFAK ÜRETİM REÇETE FİŞİ</h1>
<div class="meta"><strong>Reçete:</strong> {kod} • {ad} ({kat}) | <strong>Revizyon:</strong> Rev:{rev_no:02d} | <strong>Standart:</strong> {porsiyon:.0f} Porsiyon | <strong>Tarih:</strong> {tarih}</div>
<table><thead><tr><th>#</th><th>Malzeme</th><th>Brüt Miktar</th><th>Fire</th><th>Net Miktar</th><th>Kaynak</th></tr></thead>
<tbody>{''.join(satir_html)}</tbody></table>
<div class="box"><strong>Hazırlık &amp; Pişirme Talimatı:</strong> {notlar}<br><br>
<strong>Porsiyonlama &amp; Sunum:</strong> {sunum}<br><br>
<strong>Alerjen Uyarıları:</strong> {html.escape(alerjenler)}</div>
</body></html>"""


def _dagitim_etiketi_html(recete: Dict[str, Any]) -> str:
    """Dağıtım kapları için alerjen, kalori ve üretim tarihli etiket HTML çıktısı üretir."""
    kod = html.escape(str(recete.get("recete_kodu", "-")))
    ad = html.escape(str(recete.get("yemek_adi", "-")))
    kalori = float(recete.get("porsiyon_basi_kalori", 0) or 0)
    gram = float(recete.get("porsiyon_basi_gram", 0) or 0)
    tarih = datetime.now().strftime("%d.%m.%Y")
    alerjenler = ", ".join(recete.get("alerjenler") or []) or "Alerjen Bildirimi Yok"

    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><title>Dağıtım Etiketi - {kod}</title>
<style>
body{{font-family:Arial,sans-serif;padding:20px}}
.etiket{{width:340px;border:2px solid #0f172a;border-radius:10px;padding:14px}}
.baslik{{font-size:15px;font-weight:700;border-bottom:1px solid #0f172a;padding-bottom:6px;margin-bottom:8px}}
.yemek{{font-size:18px;font-weight:800;margin-bottom:8px}}
.satir{{font-size:13px;margin:4px 0}}
.alerjen{{margin-top:8px;padding:6px;background:#fee2e2;border:1px solid #ef4444;font-size:12px;font-weight:700}}
</style></head><body onload="window.print()">
<div class="etiket">
<div class="baslik">AZİZİYE AŞEVİ • SICAK YEMEK DAĞITIM ETİKETİ</div>
<div class="yemek">{ad} ({kod})</div>
<div class="satir"><strong>Üretim Tarihi:</strong> {tarih} (Aynı gün tüketiniz)</div>
<div class="satir"><strong>1 Porsiyon Enerji:</strong> {kalori:.1f} kcal | <strong>Net Gramaj:</strong> {gram:.0f} g</div>
<div class="alerjen">⚠️ ALERJEN UYARISI: {html.escape(alerjenler)}</div>
</div></body></html>"""


def _recete_ozet_rozeti_goster(
    recete: Dict[str, Any],
    aktif_k_maskeleri: Optional[List[str]] = None,
) -> None:
    """Kayıtlı reçeteler için koyu cam kart + revizyon + alerjen + vektörel ikon rozeti çizer."""
    maskeler = set(aktif_k_maskeleri or [])
    kalori_gizli = "3. Sayfa: Hazır Yemek Reçeteleri - Kalori" in maskeler
    maliyet_gizli = "3. Sayfa: Hazır Yemek Reçeteleri - Maliyet" in maskeler

    kod = html.escape(str(recete.get("recete_kodu", "-")))
    ad = html.escape(str(recete.get("yemek_adi", "İsimsiz Reçete")))
    kategori = html.escape(str(recete.get("kategori", "Ana Yemek")))
    porsiyon = float(recete.get("porsiyon_sayisi", 100) or 100)
    kalori_porsiyon = float(recete.get("porsiyon_basi_kalori", 0) or 0)
    maliyet_porsiyon = float(recete.get("porsiyon_basi_maliyet", 0) or 0)
    gram_porsiyon = float(recete.get("porsiyon_basi_gram", 0) or 0)
    rev_no = int(recete.get("revizyon_no", 1) or 1)
    durum = str(recete.get("durum") or ("Onaylandı / Aktif" if recete.get("aktif", True) else "Taslak"))
    alerjenler = list(recete.get("alerjenler") or [])
    kilitli_mi = bool(recete.get("maliyet_kilidi", False))

    kalori_metni = "🔒 Gizli" if kalori_gizli else f"{kalori_porsiyon:.1f} kcal"
    maliyet_metni = "🔒 Gizli" if maliyet_gizli else f"{maliyet_porsiyon:.2f} TL{' 🔒' if kilitli_mi else ''}"
    gram_metni = f"{gram_porsiyon:.0f} g" if gram_porsiyon > 0 else "-"

    durum_renk, durum_bg = _durum_rozeti_stili(durum)
    rozet = ikon_rozeti_html("mutfak", renk=durum_renk, boyut=38)

    alerjen_etiketleri = ""
    if alerjenler:
        rozetler = "".join(
            f"<span style='font-size:0.70rem;font-weight:700;color:#fca5a5;background:rgba(244,63,94,0.16);"
            f"border:1px solid rgba(244,63,94,0.38);padding:2px 8px;border-radius:999px;'>⚠ {html.escape(a)}</span>"
            for a in alerjenler
        )
        alerjen_etiketleri = f"<div style='display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;'>{rozetler}</div>"

    html_cikti = f"""
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;background:linear-gradient(135deg,rgba(15,23,42,0.92) 0%,rgba(30,41,59,0.78) 100%);border:1px solid rgba(148,163,184,0.20);border-left:4px solid {durum_renk};border-radius:12px;padding:12px 16px;margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:12px;">
            {rozet}
            <div>
                <div style="font-size:0.75rem;font-weight:700;color:#38bdf8;letter-spacing:0.6px;">
                    {kod} • {kategori} • <span style="color:#fbbf24;">Rev: {rev_no:02d}</span>
                </div>
                <div style="font-size:1.02rem;font-weight:700;color:#f8fafc;">{ad}</div>
                {alerjen_etiketleri}
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-size:0.83rem;color:#cbd5e1;">
            <span>Porsiyon: <strong style="color:#f8fafc;">{porsiyon:.0f}</strong></span>
            <span>Net Gramaj: <strong style="color:#38bdf8;">{gram_metni}</strong></span>
            <span>Kalori/Pors: <strong style="color:#10b981;">{kalori_metni}</strong></span>
            <span>Maliyet/Pors: <strong style="color:#fbbf24;">{maliyet_metni}</strong></span>
            <span style="font-size:0.75rem;font-weight:700;color:{durum_renk};background:{durum_bg};border:1px solid {durum_renk}55;padding:3px 10px;border-radius:999px;">{html.escape(durum)}</span>
        </div>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)


def _receteyi_kaydet_islemi(
    recete_kodu: str,
    yemek_adi: str,
    kategori: str,
    porsiyon_sayisi: float,
    durum: str,
    yayinda: bool,
    notlar: str,
    sunum_notu: str,
    maliyet_kilidi: bool,
    manuel_alerjenler: List[str],
    client: Any,
    bellek_depo: Optional[List[Dict[str, Any]]],
    son_fiyat_saglayici: Optional[Callable[[str], Optional[float]]],
    yari_mamul_sozlugu: Dict[str, Dict[str, Any]],
) -> None:
    try:
        kaydedilen = yemek_receteleri_sql_kaydet(
            recete={
                "recete_kodu": recete_kodu,
                "yemek_adi": yemek_adi,
                "kategori": kategori,
                "porsiyon_sayisi": porsiyon_sayisi,
                "durum": durum,
                "aktif": yayinda,
                "notlar": notlar,
                "sunum_notu": sunum_notu,
                "maliyet_kilidi": maliyet_kilidi,
                "alerjenler": manuel_alerjenler,
                "kalemler": st.session_state.get("bom_satirlari", []),
            },
            client=client,
            bellek_depo=bellek_depo,
            son_fiyat_saglayici=son_fiyat_saglayici,
            yari_mamul_sozlugu=yari_mamul_sozlugu,
        )
        rev_no = int(kaydedilen.get("revizyon_no", 1) or 1)
        st.session_state["bom_hedef_revizyon"] = rev_no + 1
        st.session_state["bom_son_mesaj"] = (
            f"✅ Reçete kalıcı olarak kaydedildi: **{kaydedilen.get('recete_kodu')}** "
            f"(Aktif Sürüm: **Rev: {rev_no:02d}**)"
        )
        talepler = kaydedilen.get("satin_alma_talepleri") or []
        if talepler:
            st.session_state["bom_satin_alma_uyari"] = talepler
        else:
            st.session_state.pop("bom_satin_alma_uyari", None)
    except (ValueError, RuntimeError) as exc:
        st.session_state["bom_hata_mesaj"] = str(exc)


def yemek_receteleri_sayfasi(
    client: Any = None,
    bellek_depo: Optional[List[Dict[str, Any]]] = None,
    son_fiyat_saglayici: Optional[Callable[[str], Optional[float]]] = None,
    kalori_saglayici: Optional[Callable[[str, str], Optional[float]]] = None,
    stok_urunleri: Optional[List[str]] = None,
    aktif_k_maskeleri: Optional[List[str]] = None,
) -> None:
    """Aziziye Aşevi Dinamik BOM & Hazır Yemek Reçeteleri Kontrol Paneli — Yalnızca Dark Tema."""
    kayitli_receteler = yemek_receteleri_sql_oku(
        client=client, bellek_depo=bellek_depo
    )
    _bom_durumunu_baslat(
        kayitli_receteler,
        son_fiyat_saglayici=son_fiyat_saglayici,
        kalori_saglayici=kalori_saglayici,
    )

    maskeler = set(aktif_k_maskeleri or [])
    kalori_gizli = "3. Sayfa: Hazır Yemek Reçeteleri - Kalori" in maskeler
    maliyet_gizli = "3. Sayfa: Hazır Yemek Reçeteleri - Maliyet" in maskeler
    liste_gizli = "3. Sayfa: Hazır Yemek Reçeteleri - Liste" in maskeler

    benzersiz_stok_urunleri = sorted(
        list(set(str(u).strip() for u in (stok_urunleri or []) if str(u).strip()))
    )

    st.markdown(
        _temiz_html(
            """
            <style>
                div[data-testid="stVerticalBlock"] > div:has(> .bom-sticky-anchor) {
                    position: sticky;
                    top: 3.2rem;
                    z-index: 40;
                    background: rgba(4, 7, 17, 0.92);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(16, 185, 129, 0.28);
                    border-radius: 12px;
                    padding: 8px 14px;
                    margin-bottom: 10px;
                }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )

    sayfa_ust_banner_goster(
        st,
        ikon="mutfak",
        baslik="Aziziye Aşevi • Hazır Yemek Reçeteleri (BOM Kontrol Paneli)",
        alt_baslik="Çoklu malzeme reçetesi, otomatik stok fiyat/kalori çekimi, birim dönüşümü, fire hesabı ve üretim fişi çıktıları",
        tema="yesil",
    )

    aktif_sayisi = sum(1 for r in kayitli_receteler if bool(r.get("aktif", True)))
    yari_mamul_sozlugu: Dict[str, Dict[str, Any]] = {
        str(r.get("yemek_adi", "")).strip(): r
        for r in kayitli_receteler
        if str(r.get("yemek_adi", "")).strip()
    }

    # --- 1. CANLI KPI ÖZET KARTLARI (YALNIZCA GEÇERLİ SEÇİLMİŞ SATIRLAR HESAPLANIR) ---
    aktif_porsiyon = float(st.session_state.get("bom_porsiyon", 100.0) or 100.0)
    gecerli_satirlar = [
        s for s in st.session_state["bom_satirlari"] if str(s.get("urun_adi", "")).strip()
    ]
    canli_ozet = hesapla_kalori_ve_maliyet(
        gecerli_satirlar,
        porsiyon_sayisi=aktif_porsiyon,
        son_fiyat_saglayici=son_fiyat_saglayici,
        yari_mamul_sozlugu=yari_mamul_sozlugu,
    )

    kpi_satiri_goster(
        st,
        [
            (
                "mutfak",
                "Kayıtlı Reçete",
                f"{len(kayitli_receteler)} Adet",
                f"Yayında: {aktif_sayisi} şablon",
                "#10b981",
            ),
            (
                "rapor",
                "Editör Canlı Kalori",
                "🔒 Gizli" if kalori_gizli else f"{canli_ozet['toplam_kalori']:.0f} kcal",
                "🔒 Gizli" if kalori_gizli else f"Porsiyon başı: {canli_ozet['porsiyon_basi_kalori']:.1f} kcal",
                "#38bdf8",
            ),
            (
                "para",
                "Editör Canlı Maliyet",
                "🔒 Gizli" if maliyet_gizli else f"{canli_ozet['toplam_maliyet']:.2f} TL",
                "🔒 Gizli" if maliyet_gizli else f"Porsiyon başı: {canli_ozet['porsiyon_basi_maliyet']:.2f} TL",
                "#f59e0b",
            ),
            (
                "stok",
                "Porsiyon Net Gramaj",
                f"{canli_ozet['porsiyon_basi_gram']:.0f} g",
                f"Fire sonrası toplam: {canli_ozet['toplam_net_gram'] / 1000.0:.2f} kg",
                "#a855f7",
            ),
        ],
    )

    # --- 2. YAPIŞKAN HIZLI KAYDET & İŞ AKIŞI ÜST ÇUBUĞU ---
    ust_bar = st.container()
    with ust_bar:
        st.markdown('<span class="bom-sticky-anchor"></span>', unsafe_allow_html=True)
        sb_col1, sb_col2, sb_col3 = st.columns([2.4, 1.3, 1.3])
        with sb_col1:
            aktif_kod_gosterim = st.session_state.get("bom_recete_kodu", "").strip() or "Yeni Reçete"
            aktif_ad_gosterim = st.session_state.get("bom_yemek_adi", "").strip() or "İsimsiz Şablon"
            hedef_rev = int(st.session_state.get("bom_hedef_revizyon", 1) or 1)
            st.markdown(
                f"<div style='padding-top:6px;font-size:0.90rem;color:#cbd5e1;'>"
                f"Aktif Editör: <strong style='color:#10b981;'>{html.escape(aktif_kod_gosterim)}</strong> — "
                f"<strong style='color:#f8fafc;'>{html.escape(aktif_ad_gosterim)}</strong> "
                f"<span style='color:#fbbf24;font-weight:700;'>(Hedef Sürüm: Rev: {hedef_rev:02d})</span></div>",
                unsafe_allow_html=True,
            )
        with sb_col2:
            if st.button("🧹 Yeni Reçete / Temizle", use_container_width=True, key="bom_yeni_temizle_btn"):
                st.session_state["bom_bekleyen_yukleme"] = {"_temizle": True}
                st.rerun()
        with sb_col3:
            ust_kaydet_basildi = st.button(
                "💾 Reçeteyi Kaydet",
                type="primary",
                use_container_width=True,
                key="bom_ust_kaydet_btn",
            )

    if st.session_state.get("bom_son_mesaj"):
        st.success(st.session_state.pop("bom_son_mesaj"))
    if st.session_state.get("bom_hata_mesaj"):
        st.error(st.session_state.pop("bom_hata_mesaj"))
    if st.session_state.get("bom_satin_alma_uyari"):
        talepler = st.session_state.pop("bom_satin_alma_uyari")
        talep_metni = ", ".join(
            f"{t['urun_adi']} ({t['talep_miktari']} {t['birim']})" for t in talepler
        )
        st.warning(f"🛒 Satın Alma Talebi Oluşturuldu: {talep_metni}")

    # --- 3. REÇETE ÜST BİLGİLERİ, PORSİYON ÖLÇEKLEME VE İŞ AKIŞI ---
    bolum_basligi_goster(
        st,
        ikon="liste",
        baslik="Reçete Kimliği, Porsiyon Ölçekleme ve İş Akışı",
        alt_aciklama="Reçete kodu otomatik atanır; aynı kodla tekrar kaydedildiğinde eski sürüm arşivlenip yeni revizyon oluşur",
        vurgu_renk="#38bdf8",
    )

    c1, c2, c3 = st.columns([1.1, 1.6, 1.3])
    with c1:
        recete_kodu = st.text_input(
            "Reçete Kodu (Otomatik)",
            key="bom_recete_kodu",
        )
    with c2:
        yemek_adi = st.text_input(
            "Yemek Adı",
            placeholder="Mercimek Çorbası",
            key="bom_yemek_adi",
        )
    with c3:
        kategori = st.selectbox(
            "Kategori",
            options=_KATEGORI_SECENEKLERI,
            key="bom_kategori",
        )

    p1, p2, p3, p4 = st.columns([1.1, 1.1, 1.2, 1.2])
    with p1:
        porsiyon_sayisi = st.number_input(
            "Standart Porsiyon Sayısı",
            min_value=1.0,
            value=float(st.session_state.get("bom_porsiyon", 100.0)),
            step=10.0,
            key="bom_porsiyon",
        )
    with p2:
        olcekleme_kilidi = st.checkbox(
            "🔒 Porsiyon değişince miktarları otomatik ölçekle",
            value=True,
            key="bom_olcekleme_kilidi",
        )
    with p3:
        durum = st.selectbox(
            "İş Akışı Durumu",
            options=RECETE_DURUMLARI,
            index=2,
            key="bom_durum",
        )
    with p4:
        st.markdown("<div style='margin-top:26px;'></div>", unsafe_allow_html=True)
        yayinda = st.toggle(
            "Yayında / Kullanımda",
            value=True,
            key="bom_yayinda",
        )

    onceki_porsiyon = float(st.session_state.get("bom_porsiyon_son", porsiyon_sayisi) or porsiyon_sayisi)
    if abs(porsiyon_sayisi - onceki_porsiyon) > 1e-6:
        if olcekleme_kilidi:
            st.session_state["bom_satirlari"] = recete_kalemlerini_olcekle(
                st.session_state["bom_satirlari"],
                eski_porsiyon=onceki_porsiyon,
                yeni_porsiyon=porsiyon_sayisi,
            )
            st.session_state["bom_porsiyon_son"] = porsiyon_sayisi
            st.rerun()
        st.session_state["bom_porsiyon_son"] = porsiyon_sayisi

    # --- 4. DİNAMİK MALZEME TABLOSU (BOM - BILL OF MATERIALS) ---
    bolum_basligi_goster(
        st,
        ikon="stok",
        baslik="Dinamik Malzeme Listesi (BOM) & Birim Dönüşümü",
        alt_aciklama="Malzeme seçilmeden miktar girilmez; gr/ml seçildiğinde kg/lt birim fiyatı otomatik oranlanır",
        vurgu_renk="#f59e0b",
    )

    h_cols = st.columns([2.2, 0.9, 1.0, 0.9, 1.0, 1.3, 1.1, 1.1])
    basliklar = [
        "Malzeme / Yarı Mamul",
        "Birim",
        "Brüt Miktar",
        "Fire (%)",
        "Birim Kalori",
        "Kaynak",
        "Birim Fiyat (TL)",
        "İşlem (Sıra / Sil)",
    ]
    for col_obj, baslik_txt in zip(h_cols, basliklar):
        col_obj.markdown(
            f"<div style='font-size:0.76rem;font-weight:700;color:#94a3b8;padding:4px 2px;border-bottom:1px solid rgba(148,163,184,0.22);'>{baslik_txt}</div>",
            unsafe_allow_html=True,
        )

    satirlar = st.session_state["bom_satirlari"]
    degisiklik_oldu = False
    maliyet_kilidi_aktif = bool(st.session_state.get("bom_maliyet_kilidi", False))

    for idx, satir in enumerate(satirlar):
        r_cols = st.columns([2.2, 0.9, 1.0, 0.9, 1.0, 1.3, 1.1, 1.1])

        with r_cols[5]:
            mevcut_kaynak = satir.get("kaynak", "STOK")
            kaynak_idx = _KAYNAK_SECENEKLERI.index(mevcut_kaynak) if mevcut_kaynak in _KAYNAK_SECENEKLERI else 0
            yeni_kaynak = st.selectbox(
                "Kaynak",
                options=_KAYNAK_SECENEKLERI,
                index=kaynak_idx,
                key=f"bom_kaynak_{idx}",
                label_visibility="collapsed",
            )

        with r_cols[0]:
            if yeni_kaynak == "YARI_MAMUL" and yari_mamul_sozlugu:
                ym_secenekler = list(yari_mamul_sozlugu.keys())
                ym_idx = ym_secenekler.index(satir.get("urun_adi")) if satir.get("urun_adi") in ym_secenekler else None
                secilen_ym = st.selectbox(
                    "Yarı Mamul",
                    options=ym_secenekler,
                    index=ym_idx,
                    placeholder="🍲 Yarı mamul reçete seçin...",
                    format_func=lambda x: f"🍲 [YARI MAMUL] {yari_mamul_sozlugu[x].get('recete_kodu', '')} • {x}",
                    key=f"bom_ym_{idx}",
                    label_visibility="collapsed",
                )
                yeni_urun = secilen_ym or ""
            elif yeni_kaynak in ("STOK", "SATIN_ALMA") and benzersiz_stok_urunleri:
                mevcut_u = str(satir.get("urun_adi", "")).strip()
                secenek_listesi = list(benzersiz_stok_urunleri)
                if mevcut_u and mevcut_u not in secenek_listesi:
                    secenek_listesi.insert(0, mevcut_u)
                u_idx = secenek_listesi.index(mevcut_u) if mevcut_u in secenek_listesi else None
                secilen_stok_u = st.selectbox(
                    "Stok Ürünü",
                    options=secenek_listesi,
                    index=u_idx,
                    placeholder="📦 Depodan hammadde seçin...",
                    format_func=lambda x: f"📦 {x}",
                    key=f"bom_stok_sel_{idx}",
                    label_visibility="collapsed",
                )
                yeni_urun = secilen_stok_u or ""
            else:
                yeni_urun = st.text_input(
                    "Malzeme",
                    value=str(satir.get("urun_adi", "")),
                    placeholder="Örn: Su, Tuz, Baharat...",
                    key=f"bom_urun_{idx}",
                    label_visibility="collapsed",
                )

        malzeme_secili = bool(yeni_urun.strip())
        urun_degisti = yeni_urun.strip() != str(satir.get("urun_adi", "")).strip()

        with r_cols[1]:
            mevcut_birim = satir.get("birim", "kg")
            birim_idx = _BIRIM_SECENEKLERI.index(mevcut_birim) if mevcut_birim in _BIRIM_SECENEKLERI else 0
            yeni_birim = st.selectbox(
                "Birim",
                options=_BIRIM_SECENEKLERI,
                index=birim_idx,
                disabled=not malzeme_secili,
                key=f"bom_birim_{idx}",
                label_visibility="collapsed",
            )

        with r_cols[2]:
            yeni_miktar = st.number_input(
                "Miktar",
                min_value=0.0,
                value=float(satir.get("miktar", 0.0) or 0.0) if malzeme_secili else 0.0,
                step=0.5,
                disabled=not malzeme_secili,
                key=f"bom_miktar_{idx}",
                label_visibility="collapsed",
            )

        with r_cols[3]:
            yeni_fire = st.number_input(
                "Fire %",
                min_value=0.0,
                max_value=95.0,
                value=float(satir.get("fire_orani", 0.0) or 0.0) if malzeme_secili else 0.0,
                step=1.0,
                disabled=not malzeme_secili,
                key=f"bom_fire_{idx}",
                label_visibility="collapsed",
            )

        with r_cols[4]:
            varsayilan_kalori = float(satir.get("kalori", 0.0) or 0.0) if malzeme_secili else 0.0
            if malzeme_secili:
                if yeni_kaynak == "YARI_MAMUL" and yeni_urun in yari_mamul_sozlugu and (urun_degisti or varsayilan_kalori <= 0):
                    varsayilan_kalori = float(yari_mamul_sozlugu[yeni_urun].get("porsiyon_basi_kalori", 0.0) or 0.0)
                elif kalori_saglayici and (urun_degisti or varsayilan_kalori <= 0):
                    oto_kalori = kalori_saglayici(yeni_urun, yeni_birim)
                    if oto_kalori is not None and float(oto_kalori) > 0:
                        varsayilan_kalori = float(oto_kalori)

            yeni_kalori = st.number_input(
                "Kalori",
                min_value=0.0,
                value=varsayilan_kalori,
                step=10.0,
                disabled=not malzeme_secili,
                key=f"bom_kalori_{idx}_{yeni_urun}",
                label_visibility="collapsed",
            )

        with r_cols[6]:
            sifir_kaynak_mi = (not malzeme_secili) or (yeni_kaynak in ("BAĞIŞ", "SIFIR MALİYET"))
            varsayilan_fiyat = 0.0 if sifir_kaynak_mi else float(satir.get("birim_fiyat", 0.0) or 0.0)
            if not sifir_kaynak_mi:
                if yeni_kaynak == "YARI_MAMUL" and yeni_urun in yari_mamul_sozlugu and (urun_degisti or varsayilan_fiyat <= 0):
                    varsayilan_fiyat = float(yari_mamul_sozlugu[yeni_urun].get("porsiyon_basi_maliyet", 0.0) or 0.0)
                elif son_fiyat_saglayici and (urun_degisti or varsayilan_fiyat <= 0):
                    oto_fiyat = son_fiyat_saglayici(yeni_urun)
                    if oto_fiyat is not None and float(oto_fiyat) > 0:
                        varsayilan_fiyat = float(oto_fiyat)

            yeni_fiyat = st.number_input(
                "Fiyat",
                min_value=0.0,
                value=varsayilan_fiyat,
                step=1.0,
                disabled=sifir_kaynak_mi or maliyet_kilidi_aktif,
                key=f"bom_fiyat_{idx}_{yeni_urun}_{yeni_kaynak}",
                label_visibility="collapsed",
            )

        yeni_satir = {
            "urun_adi": yeni_urun,
            "birim": yeni_birim,
            "miktar": yeni_miktar,
            "fire_orani": yeni_fire,
            "kalori": yeni_kalori,
            "kaynak": yeni_kaynak,
            "fiyat_birimi": "oto_kg_lt",
            "birim_fiyat": 0.0 if sifir_kaynak_mi else yeni_fiyat,
        }
        if yeni_satir != satir:
            satirlar[idx] = yeni_satir
            degisiklik_oldu = True

        with r_cols[7]:
            act_c1, act_c2, act_c3 = st.columns(3)
            with act_c1:
                if st.button("▲", key=f"bom_up_{idx}", disabled=(idx == 0), help="Satırı bir üste taşı"):
                    satirlar[idx - 1], satirlar[idx] = satirlar[idx], satirlar[idx - 1]
                    st.rerun()
            with act_c2:
                if st.button("▼", key=f"bom_down_{idx}", disabled=(idx == len(satirlar) - 1), help="Satırı bir alta taşı"):
                    satirlar[idx + 1], satirlar[idx] = satirlar[idx], satirlar[idx + 1]
                    st.rerun()
            with act_c3:
                if st.button("🗑", key=f"bom_del_{idx}", disabled=(len(satirlar) <= 1), help="Bu malzeme satırını sil"):
                    satirlar.pop(idx)
                    st.rerun()

    if degisiklik_oldu:
        st.rerun()

    ekle_col1, ekle_col2 = st.columns([1.4, 3.6])
    with ekle_col1:
        if st.button("➕ Yeni Malzeme Ekle", use_container_width=True, key="bom_satir_ekle_btn"):
            st.session_state["bom_satirlari"].append(_varsayilan_bom_satiri())
            st.rerun()
    with ekle_col2:
        if st.button("💧 Su / Tuz (Sıfır Maliyet) Ekle", key="bom_sifir_ekle_btn"):
            st.session_state["bom_satirlari"].append(
                {
                    "urun_adi": "Su",
                    "birim": "lt",
                    "miktar": 10.0,
                    "fire_orani": 0.0,
                    "kalori": 0.0,
                    "kaynak": "SIFIR MALİYET",
                    "fiyat_birimi": "oto_kg_lt",
                    "birim_fiyat": 0.0,
                }
            )
            st.rerun()

    # --- 5. ALERJEN TESPİTİ, SUNUM NOTU & MALİYET KİLİDİ ---
    otomatik_alerjenler = alerjenleri_otomatik_tespit_et(
        gecerli_satirlar,
        st.session_state.get("bom_manuel_alerjen", []),
    )
    a_col1, a_col2 = st.columns([1.5, 1.5])
    with a_col1:
        manuel_alerjenler = st.multiselect(
            "🩺 Alerjen Uyarıları (Malzemelerden otomatik algılanır + ek seçim)",
            options=sorted(ALERJEN_SOZLUGU.keys()),
            default=otomatik_alerjenler,
            placeholder="Alerjen Seçin veya Ekleyin",
            key="bom_manuel_alerjen",
        )
        maliyet_kilidi = st.toggle(
            "🔒 Maliyet Kilidi (Birim fiyatları sabitle)",
            value=bool(st.session_state.get("bom_maliyet_kilidi", False)),
            key="bom_maliyet_kilidi",
        )
    with a_col2:
        notlar = st.text_area(
            "Hazırlık & Pişirme Talimatı",
            placeholder="Pişirme süresi, sıcaklık ve kazan talimatları...",
            height=68,
            key="bom_notlar",
        )
        sunum_notu = st.text_area(
            "🍽️ Porsiyonlama ve Sunum Talimatı",
            placeholder="Örn: Her kasenin üzerine 1 tutam maydanoz ve limon dilimi konulacak...",
            height=68,
            key="bom_sunum_notu",
        )

    alt_kaydet_basildi = st.button(
        "💾 Reçeteyi Kaydet ve Revizyonu Onayla",
        type="primary",
        key="bom_alt_kaydet_btn",
    )

    if ust_kaydet_basildi or alt_kaydet_basildi:
        _receteyi_kaydet_islemi(
            recete_kodu=recete_kodu,
            yemek_adi=yemek_adi,
            kategori=kategori,
            porsiyon_sayisi=porsiyon_sayisi,
            durum=durum,
            yayinda=yayinda,
            notlar=notlar,
            sunum_notu=sunum_notu,
            maliyet_kilidi=maliyet_kilidi,
            manuel_alerjenler=manuel_alerjenler,
            client=client,
            bellek_depo=bellek_depo,
            son_fiyat_saglayici=son_fiyat_saglayici,
            yari_mamul_sozlugu=yari_mamul_sozlugu,
        )
        st.rerun()

    # --- 6. KAYITLI REÇETELER, REVİZYON GEÇMİŞİ VE YAZDIRMA ÇIKTILARI ---
    st.markdown("---")
    bolum_basligi_goster(
        st,
        ikon="liste",
        baslik="Kayıtlı Hazır Yemek Reçeteleri, Yazdırma & Revizyon Arşivi",
        alt_aciklama="Mutfak üretim fişi ve kap dağıtım etiketi alabilir, mevcut reçeteyi revize edebilirsiniz",
        vurgu_renk="#a855f7",
    )

    if liste_gizli:
        st.info("🔒 Kayıtlı hazır yemek reçeteleri listesi yetkiniz gereği gizlenmiştir.")
    elif kayitli_receteler:
        for r_idx, kayit in enumerate(kayitli_receteler):
            _recete_ozet_rozeti_goster(kayit, aktif_k_maskeleri=aktif_k_maskeleri)
            kalemler = kayit.get("kalemler") or []
            not_metni = str(kayit.get("notlar", "")).strip()
            sunum_metni = str(kayit.get("sunum_notu", "")).strip()
            rev_gecmisi = list(kayit.get("revizyon_gecmisi") or [])

            d_col1, d_col2, d_col3, d_col4 = st.columns([2.8, 0.9, 0.9, 0.9])
            with d_col1:
                with st.expander(
                    f"📋 {kayit.get('recete_kodu', '')} • {kayit.get('yemek_adi', '')} — BOM Malzeme, Fire & Revizyon Detayı",
                    expanded=False,
                ):
                    if not_metni:
                        st.caption(f"📝 Hazırlık Notu: {not_metni}")
                    if sunum_metni:
                        st.caption(f"🍽️ Porsiyonlama & Sunum: {sunum_metni}")
                    if kalemler:
                        porsiyon = float(kayit.get("porsiyon_sayisi", 100) or 100)
                        temiz_kalemler = []
                        for k in kalemler:
                            brut = (
                                float(k.get("miktar", 0) or 0)
                                if "miktar" in k
                                else float(k.get("porsiyon_basi_miktar", 0) or 0) * porsiyon
                            )
                            fire = float(k.get("fire_orani", 0) or 0)
                            net = round(brut * (1.0 - fire / 100.0), 3)
                            temiz_kalemler.append(
                                {
                                    "Malzeme Adı": k.get("urun_adi", "-"),
                                    "Brüt Miktar": round(brut, 3),
                                    "Fire (%)": f"%{fire:.0f}",
                                    "Net Miktar": net,
                                    "Birim": k.get("birim", "kg"),
                                    "Kaynak": k.get("kaynak", "STOK"),
                                }
                            )
                        st.dataframe(temiz_kalemler, use_container_width=True, hide_index=True)
                    if rev_gecmisi:
                        st.caption("🕒 Arşivlenen Eski Revizyonlar:")
                        rev_tablo = [
                            {
                                "Revizyon": f"Rev: {int(rv.get('revizyon_no', 1)):02d}",
                                "Tarih": str(rv.get("tarih", "-"))[:19],
                                "Yemek Adı": rv.get("yemek_adi", "-"),
                                "Porsiyon": rv.get("porsiyon_sayisi", 100),
                                "Toplam Maliyet": "🔒 Gizli" if maliyet_gizli else f"{float(rv.get('toplam_maliyet', 0)):.2f} TL",
                                "Toplam Kalori": "🔒 Gizli" if kalori_gizli else f"{float(rv.get('toplam_kalori', 0)):.0f} kcal",
                                "Durum": rv.get("durum", "Arşivlendi (Eski Sürüm)"),
                            }
                            for rv in reversed(rev_gecmisi)
                        ]
                        st.dataframe(rev_tablo, use_container_width=True, hide_index=True)
            with d_col2:
                st.download_button(
                    "🖨️ Üretim Fişi",
                    data=_mutfak_uretim_fisi_html(kayit).encode("utf-8"),
                    file_name=f"uretim_fisi_{kayit.get('recete_kodu', 'rec')}.html",
                    mime="text/html",
                    key=f"bom_fis_btn_{r_idx}_{kayit.get('recete_kodu', '')}",
                    use_container_width=True,
                )
            with d_col3:
                st.download_button(
                    "🏷️ Kap Etiketi",
                    data=_dagitim_etiketi_html(kayit).encode("utf-8"),
                    file_name=f"dagitim_etiketi_{kayit.get('recete_kodu', 'rec')}.html",
                    mime="text/html",
                    key=f"bom_etiket_btn_{r_idx}_{kayit.get('recete_kodu', '')}",
                    use_container_width=True,
                )
            with d_col4:
                if st.button(
                    "✏️ Düzenle / Revize Et",
                    key=f"bom_yukle_btn_{r_idx}_{kayit.get('recete_kodu', '')}",
                    use_container_width=True,
                ):
                    st.session_state["bom_bekleyen_yukleme"] = dict(kayit)
                    st.rerun()
    else:
        st.info("Henüz kayıtlı hazır yemek reçetesi bulunmuyor.")
