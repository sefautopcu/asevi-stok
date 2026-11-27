import datetime
import html
import json
from pathlib import Path
import time
from src.rapor_utils import para_formatla_tr
from src.yemek_utils import en_son_urun_birim_fiyati, yemek_sepeti_maliyet_hesapla
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)
from src.yemek_receteleri_sql import (
    recete_kalemlerini_olcekle,
    yemek_receteleri_sql_oku,
)

# Yemek menüsünün 4 ana bölümü
MENU_KISIMLARI = ("ana_yemek", "yardimci_yemek", "corba", "tatli_meyve_yogurt")
MENU_KISIM_ETIKETLERI = {
    "ana_yemek": "Ana Yemek",
    "yardimci_yemek": "Ara Yemek / Tatlı",
    "corba": "Çorba",
    "tatli_meyve_yogurt": "Tatlı / Meyve / Yoğurt",
}

_TASLAK_DOSYA_YOLU = Path("data/aktif_uretim_taslagi.json")


def _uretim_taslagini_kaydet(st) -> None:
    """F5 sonrası kaybı önlemek için aktif sepeti ve menü taslağını diske yazar."""
    try:
        _TASLAK_DOSYA_YOLU.parent.mkdir(parents=True, exist_ok=True)
        veri = {
            "sepet": st.session_state.get("sepet", []),
            "uretim_bolum_chipleri": st.session_state.get("uretim_bolum_chipleri", {}),
            "ozel_menu_bolumleri": st.session_state.get("ozel_menu_bolumleri", []),
            "ozel_menu_degerleri": st.session_state.get("ozel_menu_degerleri", {}),
            "menu_ana_yemek": st.session_state.get("menu_ana_yemek_input", ""),
            "menu_yardimci_yemek": st.session_state.get("menu_yardimci_yemek_input", ""),
            "menu_corba": st.session_state.get("menu_corba_input", ""),
            "menu_tatli": st.session_state.get("menu_tatli_input", ""),
        }
        _TASLAK_DOSYA_YOLU.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _uretim_taslagini_yukle(st) -> None:
    """Tarayıcı F5 ile yenilendiğinde varsa kayıtlı sepet ve menü taslağını geri yükler."""
    if st.session_state.get("_uretim_taslagi_yuklendi"):
        return
    st.session_state["_uretim_taslagi_yuklendi"] = True
    try:
        if _TASLAK_DOSYA_YOLU.exists():
            veri = json.loads(_TASLAK_DOSYA_YOLU.read_text(encoding="utf-8"))
            if isinstance(veri, dict):
                if veri.get("sepet") and not st.session_state.get("sepet"):
                    st.session_state["sepet"] = veri["sepet"]
                if veri.get("uretim_bolum_chipleri") and not st.session_state.get("uretim_bolum_chipleri"):
                    st.session_state["uretim_bolum_chipleri"] = veri["uretim_bolum_chipleri"]
                if veri.get("ozel_menu_bolumleri") and not st.session_state.get("ozel_menu_bolumleri"):
                    st.session_state["ozel_menu_bolumleri"] = veri["ozel_menu_bolumleri"]
                if veri.get("ozel_menu_degerleri") and not st.session_state.get("ozel_menu_degerleri"):
                    st.session_state["ozel_menu_degerleri"] = veri["ozel_menu_degerleri"]
                for anahtar, input_key in [
                    ("menu_ana_yemek", "menu_ana_yemek_input"),
                    ("menu_yardimci_yemek", "menu_yardimci_yemek_input"),
                    ("menu_corba", "menu_corba_input"),
                    ("menu_tatli", "menu_tatli_input"),
                ]:
                    if veri.get(anahtar) and not st.session_state.get(input_key):
                        st.session_state[input_key] = veri[anahtar]
    except Exception:
        pass


def _qr_moduna_gec_callback(st) -> None:
    """Widget oluşturulduktan sonra hata vermemesi için radio seçimini callback içinde günceller."""
    st.session_state["yemek_ekleme_yontemi_radio"] = "📷 QR Kod ile Okut"


def _bolum_chip_goster(st, bolum_anahtari: str, chip_bilgi: dict) -> bool:
    """Bölüm kutusunun altında reçete etiketini (chip) çizer; silme (✕) basılırsa True döner."""
    kod = html.escape(str(chip_bilgi.get("recete_kodu", "-")))
    ad = html.escape(str(chip_bilgi.get("yemek_adi", "-")))
    pors = int(chip_bilgi.get("porsiyon", 0) or 0)
    kalori = float(chip_bilgi.get("toplam_kalori", 0) or 0)
    maliyet = float(chip_bilgi.get("toplam_maliyet", 0) or 0)

    c_chip, c_sil = st.columns([5.2, 1.0])
    with c_chip:
        st.markdown(
            f"<div style='display:flex;align-items:center;justify-content:space-between;gap:8px;"
            f"background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.45);"
            f"border-radius:10px;padding:6px 12px;margin-top:4px;font-size:0.78rem;color:#ecfdf5;'>"
            f"<span>🍲 <strong>{kod}</strong> • {ad} <strong>({pors} Pors)</strong></span>"
            f"<span style='color:#6ee7b7;white-space:nowrap;'>{para_formatla_tr(maliyet)} • {kalori:,.0f} kcal</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c_sil:
        return st.button("✕", key=f"chip_sil_{bolum_anahtari}", help="Bu reçeteyi bölümden ve sepetten çıkar")


def _receteyi_bolume_uygula(
    st,
    hedef_bolum: str,
    secili_rec: dict,
    hedef_porsiyon: int,
    eski_chip_varsa_temizle: bool = True,
) -> None:
    """Seçilen reçeteyi ilgili menü bölümüne chip olarak bağlar ve ölçekli malzemeleri sepete aktarır."""
    chipler = st.session_state.setdefault("uretim_bolum_chipleri", {})

    if eski_chip_varsa_temizle and hedef_bolum in chipler:
        eski_kod = chipler[hedef_bolum].get("recete_kodu")
        st.session_state.sepet = [
            s for s in st.session_state.sepet if s.get("recete_kodu") != eski_kod
        ]

    baz_porsiyon = float(secili_rec.get("porsiyon_sayisi", 100.0) or 100.0)
    olcekli_kalemler = recete_kalemlerini_olcekle(
        secili_rec.get("kalemler") or [],
        eski_porsiyon=baz_porsiyon,
        yeni_porsiyon=float(hedef_porsiyon),
    )

    y_ad = str(secili_rec.get("yemek_adi", "")).strip()
    r_kod = str(secili_rec.get("recete_kodu", "")).strip()

    bolum_input_haritasi = {
        "ana_yemek": "menu_ana_yemek_input",
        "yardimci_yemek": "menu_yardimci_yemek_input",
        "corba": "menu_corba_input",
        "tatli_meyve_yogurt": "menu_tatli_input",
    }
    if hedef_bolum in bolum_input_haritasi:
        st.session_state[bolum_input_haritasi[hedef_bolum]] = y_ad
    else:
        ozel_degerler = st.session_state.setdefault("ozel_menu_degerleri", {})
        ozel_degerler[hedef_bolum] = y_ad

    eklenen_sayisi = 0
    eksik_uyarilar = []
    sifir_maliyet_notlar = []

    stok_haritasi = {}
    for g in st.session_state.girisler:
        u_key = str(g.get("urun", "")).strip().upper()
        if u_key:
            stok_haritasi[u_key] = stok_haritasi.get(u_key, 0.0) + float(g.get("kalan", 0) or 0)

    for k in olcekli_kalemler:
        u_ad = str(k.get("urun_adi", "")).strip()
        u_key = u_ad.upper()
        miktar = round(float(k.get("miktar", 0.0) or 0.0), 3)
        kaynak = str(k.get("kaynak", "STOK")).strip().upper()
        if not u_ad or miktar <= 0:
            continue

        if kaynak in ("SIFIR MALİYET", "SIFIR_MALIYET") and u_key not in stok_haritasi:
            sifir_maliyet_notlar.append(f"{u_ad} ({miktar} {k.get('birim', '')})")
            continue

        mevcut_stok = stok_haritasi.get(u_key, 0.0)
        sepet_mevcut = sum(
            float(s.get("miktar", 0) or 0)
            for s in st.session_state.sepet
            if str(s.get("urun", "")).strip().upper() == u_key
        )
        kullanilabilir = max(mevcut_stok - sepet_mevcut, 0.0)

        if kullanilabilir >= miktar:
            st.session_state.sepet.append(
                {
                    "urun": u_key,
                    "miktar": miktar,
                    "recete_kodu": r_kod,
                    "bolum": hedef_bolum,
                }
            )
            eklenen_sayisi += 1
        else:
            eksik_uyarilar.append(
                f"{u_ad}: Gerekli {miktar} {k.get('birim', '')}, Depoda kalan {kullanilabilir:.2f}"
            )

    oran = float(hedef_porsiyon) / baz_porsiyon if baz_porsiyon > 0 else 1.0
    chipler[hedef_bolum] = {
        "recete_kodu": r_kod,
        "yemek_adi": y_ad,
        "porsiyon": int(hedef_porsiyon),
        "toplam_kalori": round(float(secili_rec.get("toplam_kalori", 0) or 0) * oran, 1),
        "toplam_maliyet": round(float(secili_rec.get("toplam_maliyet", 0) or 0) * oran, 2),
        "alerjenler": list(secili_rec.get("alerjenler") or []),
    }

    st.session_state["uretim_recete_bildirim"] = {
        "eklenen": eklenen_sayisi,
        "eksik": eksik_uyarilar,
        "sifir": sifir_maliyet_notlar,
        "yemek": y_ad,
        "porsiyon": hedef_porsiyon,
    }
    _uretim_taslagini_kaydet(st)


def gunluk_yemek_uretim_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    verileri_kaydet,
    loglari_kaydet,
    yemek_uretim_arsivini_kaydet,
    simdi_tr_str,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    urun_kalori_hesapla,
    yonetici_modu,
    yemek_malzeme_kullanim_istatistikleri,
    yemek_malzeme_kullanim_uyarilari,
    yemek_sepeti_stok_hatalari,
):
    sayfa_ust_banner_goster(
        st,
        "mutfak",
        "Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi",
        "Esnek bölümlü menü planlama, FIFO / QR malzeme düşümü, anlık porsiyon maliyeti ve alerjen takibi",
        tema="yesil",
    )

    st.session_state.setdefault("sepet", [])
    st.session_state.setdefault("uretim_bolum_chipleri", {})
    st.session_state.setdefault("ozel_menu_bolumleri", [])
    st.session_state.setdefault("ozel_menu_degerleri", {})
    _uretim_taslagini_yukle(st)

    arsiv_liste = st.session_state.get("yemek_uretim_arsivi", []) or []
    sepet_liste = st.session_state.get("sepet", []) or []
    toplam_uretim_sayisi = len(arsiv_liste)
    toplam_porsiyon = sum(int(_u.get("kisi_sayisi", 0) or 0) for _u in arsiv_liste)
    toplam_uretim_maliyeti = sum(float(_u.get("toplam_maliyet", 0) or 0) for _u in arsiv_liste)

    kpi_satiri_goster(
        st,
        [
            ("mutfak", "Kayıtlı Menü Üretimi", toplam_uretim_sayisi, "Arşivdeki toplam yemek üretim kaydı", "#10b981"),
            ("kullanici", "Toplam Porsiyon", f"{toplam_porsiyon:,}", "Hizmet verilen toplam kişi sayısı", "#38bdf8"),
            ("para", "Toplam Üretim Maliyeti", para_formatla_tr(toplam_uretim_maliyeti), "Arşivlenen üretimlerin malzeme tutarı", "#f59e0b"),
            ("liste", "Aktif Sepet Kalemi", len(sepet_liste), "Planlanan menüdeki malzeme adedi", "#a855f7"),
        ],
    )

    # Son Yemek Üretim İşlemini Geri Al Butonu ve Bildirimi
    if st.session_state.get("son_yemek_uretim_kaydi"):
        son_uretim = st.session_state["son_yemek_uretim_kaydi"]
        c_undo1, c_undo2 = st.columns([3.5, 1.0])
        with c_undo1:
            st.info(
                f"💡 **Son Yemek Üretimi:** '{son_uretim.get('yemek_adi')}' ({son_uretim.get('kisi_sayisi')} Kişilik) • "
                f"Tutar: {para_formatla_tr(son_uretim.get('toplam_maliyet', 0))} • Tarih: {son_uretim.get('tarih')}"
            )
        with c_undo2:
            if st.button("↩️ Son Üretimi Geri Al", type="secondary", use_container_width=True, key="btn_undo_uretim_son"):
                otomatik_yedek_al("Yemek üretimi geri alma: " + str(son_uretim.get("yemek_adi")))

                for item in son_uretim.get("dusulen_kayitlar", []):
                    for g in st.session_state.girisler:
                        if g.get("id") == item["id"]:
                            g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])
                            if item.get("paket_id"):
                                if "paket_durumlari" not in g:
                                    g["paket_durumlari"] = {}
                                eski_paket = g["paket_durumlari"].get(item["paket_id"], 0.0)
                                g["paket_durumlari"][item["paket_id"]] = eski_paket + float(item["miktar"])

                arsiv_target = son_uretim.get("arsiv_objesi")
                if arsiv_target and arsiv_target in st.session_state.yemek_uretim_arsivi:
                    st.session_state.yemek_uretim_arsivi.remove(arsiv_target)

                eklenen_loglar = son_uretim.get("eklenen_loglar", [])
                for log_item in eklenen_loglar:
                    if log_item in st.session_state.kullanim_loglari:
                        st.session_state.kullanim_loglari.remove(log_item)

                verileri_kaydet(st.session_state.girisler)
                loglari_kaydet(st.session_state.kullanim_loglari)
                yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)

                st.session_state.pop("son_yemek_uretim_kaydi", None)
                st.success(f"🎉 '{son_uretim.get('yemek_adi')}' üretimi geri alındı, malzemeler stoğa iade edildi ve arşiv temizlendi!")
                time.sleep(1)
                st.rerun()

    # =========================================================================
    # ANA SAYFA YERLEŞİMİ: 3 DÜZENLİ SEKME
    # =========================================================================
    if not misafir_modu:
        tab_uretim, tab_arsiv, tab_analiz = st.tabs(
            [
                "🍲 Yeni Yemek Üretimi & Planlama",
                "📊 Üretim & Maliyet Arşivi",
                "🔍 Sapma Uyarıları & Menü Düzenleme",
            ]
        )
    else:
        tab_uretim = None
        tab_arsiv, tab_analiz = st.tabs(
            [
                "📊 Üretim & Maliyet Arşivi",
                "🔍 Sapma Uyarıları",
            ]
        )

    # =========================================================================
    # SEKME 1: YENİ YEMEK ÜRETİMİ & PLANLAMA (2 KOLONLU FERAH ÇALIŞMA ALANI)
    # =========================================================================
    if not misafir_modu and tab_uretim is not None:
        with tab_uretim:
            sol_calisma, sag_sepet_ozet = st.columns([1.55, 1.15], gap="large")

            # -----------------------------------------------------------------
            # SOL KOLON: 1) HAZIR REÇETE  2) MENÜ BÖLÜMLERİ  3) PARAMETRELER  4) MALZEME EKLE
            # -----------------------------------------------------------------
            with sol_calisma:
                if not salt_okunur_modu:
                    try:
                        aktif_receteler = [
                            r
                            for r in yemek_receteleri_sql_oku(filtre_aktif=True)
                            if str(r.get("durum", "Onaylandı / Aktif")) == "Onaylandı / Aktif"
                        ]
                    except Exception:
                        aktif_receteler = []

                    tum_bolum_secenekleri = {
                        "ana_yemek": "🥘 Ana Yemek",
                        "yardimci_yemek": "🍛 Ara Yemek / Tatlı",
                        "corba": "🍲 Çorba",
                        "tatli_meyve_yogurt": "🍨 Tatlı / Meyve / Yoğurt",
                        **{
                            f"ozel_{b}": f"🍽️ {b}"
                            for b in st.session_state["ozel_menu_bolumleri"]
                        },
                    }

                    if aktif_receteler:
                        with st.expander("📋 Hazır Reçeteden Hızlı Üretim Uygula", expanded=True):
                            recete_secenek_haritasi = {
                                f"{r.get('recete_kodu', '-')} • {r.get('yemek_adi', '-')} ({r.get('kategori', 'Ana Yemek')} | Rev: {int(r.get('revizyon_no', 1)):02d})": r
                                for r in aktif_receteler
                            }
                            rc_r1_c1, rc_r1_c2 = st.columns([1.6, 1.0])
                            with rc_r1_c1:
                                secilen_recete_etiket = st.selectbox(
                                    "Onaylı Hazır Reçete",
                                    options=list(recete_secenek_haritasi.keys()),
                                    index=None,
                                    placeholder="Reçete seçiniz...",
                                    key="uretim_hazir_recete_secim",
                                )
                            with rc_r1_c2:
                                varsayilan_bolum = "corba"
                                if secilen_recete_etiket:
                                    kat_oto = str(recete_secenek_haritasi[secilen_recete_etiket].get("kategori", ""))
                                    if kat_oto == "Çorba":
                                        varsayilan_bolum = "corba"
                                    elif kat_oto == "Tatlı / İçecek":
                                        varsayilan_bolum = "tatli_meyve_yogurt"
                                    elif kat_oto == "Pilav / Makarna":
                                        varsayilan_bolum = "yardimci_yemek"
                                    else:
                                        varsayilan_bolum = "ana_yemek"
                                bolum_anahtarlari = list(tum_bolum_secenekleri.keys())
                                hedef_bolum = st.selectbox(
                                    "Hedef Menü Bölümü",
                                    options=bolum_anahtarlari,
                                    index=bolum_anahtarlari.index(varsayilan_bolum) if varsayilan_bolum in bolum_anahtarlari else 0,
                                    format_func=lambda k: tum_bolum_secenekleri[k],
                                    key="uretim_hedef_bolum_secim",
                                )

                            rc_r2_c1, rc_r2_c2 = st.columns([1.0, 1.6])
                            with rc_r2_c1:
                                hedef_porsiyon = st.number_input(
                                    "Üretilecek Porsiyon / Kişi",
                                    min_value=1,
                                    max_value=10000,
                                    value=200,
                                    step=10,
                                    key="uretim_hazir_recete_porsiyon",
                                )
                            with rc_r2_c2:
                                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                                recete_uygula_btn = st.button(
                                    "⚡ Reçeteyi Bölüme & Sepete Aktar",
                                    type="primary",
                                    use_container_width=True,
                                    key="btn_uretim_recete_uygula",
                                )

                            if secilen_recete_etiket:
                                secili_rec = recete_secenek_haritasi[secilen_recete_etiket]
                                baz_porsiyon = float(secili_rec.get("porsiyon_sayisi", 100.0) or 100.0)
                                alerjen_listesi = secili_rec.get("alerjenler") or []
                                alerjen_bilgi = (
                                    f" | ⚠️ Alerjenler: {', '.join(alerjen_listesi)}"
                                    if alerjen_listesi
                                    else ""
                                )
                                st.caption(
                                    f"Baz Reçete: {baz_porsiyon:.0f} porsiyon → Hedef: {hedef_porsiyon} porsiyon{alerjen_bilgi}"
                                )

                                if recete_uygula_btn:
                                    mevcut_chipler = st.session_state.get("uretim_bolum_chipleri", {})
                                    if (
                                        hedef_bolum in mevcut_chipler
                                        and mevcut_chipler[hedef_bolum].get("recete_kodu") != secili_rec.get("recete_kodu")
                                    ):
                                        st.session_state["uretim_cakisma_onay"] = {
                                            "hedef_bolum": hedef_bolum,
                                            "bolum_etiket": tum_bolum_secenekleri[hedef_bolum],
                                            "eski_ad": mevcut_chipler[hedef_bolum].get("yemek_adi", "-"),
                                            "yeni_recete": secili_rec,
                                            "porsiyon": int(hedef_porsiyon),
                                        }
                                        st.rerun()
                                    else:
                                        _receteyi_bolume_uygula(
                                            st,
                                            hedef_bolum=hedef_bolum,
                                            secili_rec=secili_rec,
                                            hedef_porsiyon=int(hedef_porsiyon),
                                        )
                                        st.rerun()

                            if st.session_state.get("uretim_cakisma_onay"):
                                cakisma = st.session_state["uretim_cakisma_onay"]
                                st.warning(
                                    f"⚠️ **{cakisma['bolum_etiket']}** bölümüne zaten **'{cakisma['eski_ad']}'** eklendi. "
                                    f"**'{cakisma['yeni_recete'].get('yemek_adi')}'** ile değiştirmek ister misiniz?"
                                )
                                ck1, ck2 = st.columns([1.3, 2.7])
                                with ck1:
                                    if st.button("🔄 Evet, Değiştir", type="primary", key="btn_cakisma_degistir"):
                                        _receteyi_bolume_uygula(
                                            st,
                                            hedef_bolum=cakisma["hedef_bolum"],
                                            secili_rec=cakisma["yeni_recete"],
                                            hedef_porsiyon=cakisma["porsiyon"],
                                            eski_chip_varsa_temizle=True,
                                        )
                                        st.session_state.pop("uretim_cakisma_onay", None)
                                        st.rerun()
                                with ck2:
                                    if st.button("İptal", key="btn_cakisma_iptal"):
                                        st.session_state.pop("uretim_cakisma_onay", None)
                                        st.rerun()

                    if st.session_state.get("uretim_recete_bildirim"):
                        bildirim = st.session_state.pop("uretim_recete_bildirim")
                        if bildirim["eklenen"] > 0:
                            st.success(
                                f"✅ '{bildirim['yemek']}' ({bildirim['porsiyon']} kişi) bölüme etiketlendi ve "
                                f"{bildirim['eklenen']} malzeme sepete aktarıldı!"
                            )
                        if bildirim["sifir"]:
                            st.info(
                                f"💧 Sıfır maliyetli (stok dışı) kalemler: {', '.join(bildirim['sifir'])}"
                            )
                        if bildirim["eksik"]:
                            st.warning(
                                "⚠️ Depo stoğu yetersiz olduğu için sepete eklenemeyen kalemler:\n- "
                                + "\n- ".join(bildirim["eksik"])
                            )

                # 2. MENÜ BÖLÜMLERİ (2x2 FERAH IZGARA + ÖZEL BÖLÜMLER)
                mb_col1, mb_col2 = st.columns([2.4, 1.3])
                with mb_col1:
                    bolum_basligi_goster(
                        st,
                        "mutfak",
                        "1. Menü Bölümleri",
                        "Yemek adlarını yazın veya yukarıdan hazır reçete aktarın",
                        vurgu_renk="#10b981",
                    )
                with mb_col2:
                    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                    with st.popover("➕ Yeni Menü Bölümü", use_container_width=True):
                        yeni_bolum_adi = st.text_input(
                            "Bölüm Adı",
                            placeholder="Örn: Kahvaltılık, Ekstra Garnitür...",
                            key="yeni_ozel_bolum_input",
                        )
                        if st.button("Bölümü Ekle", type="primary", key="btn_ozel_bolum_ekle"):
                            temiz_b = yeni_bolum_adi.strip()
                            if temiz_b and temiz_b not in st.session_state["ozel_menu_bolumleri"]:
                                st.session_state["ozel_menu_bolumleri"].append(temiz_b)
                                _uretim_taslagini_kaydet(st)
                                st.rerun()

                chipler = st.session_state.get("uretim_bolum_chipleri", {})
                silinecek_chip_bolumu = None

                row1_m1, row1_m2 = st.columns(2)
                with row1_m1:
                    ana_yemek_ad = st.text_input("🥘 Ana Yemek", value="", placeholder="Örn: Ispanak Yemeği", key="menu_ana_yemek_input")
                    if "ana_yemek" in chipler:
                        if _bolum_chip_goster(st, "ana_yemek", chipler["ana_yemek"]):
                            silinecek_chip_bolumu = "ana_yemek"
                with row1_m2:
                    yardimci_yemek_ad = st.text_input("🍛 Ara Yemek / Tatlı", value="", placeholder="Örn: Mercimek, Baklava", key="menu_yardimci_yemek_input")
                    if "yardimci_yemek" in chipler:
                        if _bolum_chip_goster(st, "yardimci_yemek", chipler["yardimci_yemek"]):
                            silinecek_chip_bolumu = "yardimci_yemek"

                row2_m1, row2_m2 = st.columns(2)
                with row2_m1:
                    corba_ad = st.text_input("🍲 Çorba", value="", placeholder="Örn: Mercimek Çorbası", key="menu_corba_input")
                    if "corba" in chipler:
                        if _bolum_chip_goster(st, "corba", chipler["corba"]):
                            silinecek_chip_bolumu = "corba"
                with row2_m2:
                    tatli_meyve_yogurt_ad = st.text_input("🍨 Tatlı / Meyve / Yoğurt", value="", placeholder="Örn: Yoğurt, Muhallebi", key="menu_tatli_input")
                    if "tatli_meyve_yogurt" in chipler:
                        if _bolum_chip_goster(st, "tatli_meyve_yogurt", chipler["tatli_meyve_yogurt"]):
                            silinecek_chip_bolumu = "tatli_meyve_yogurt"

                ozel_bolum_girdileri = []
                if st.session_state["ozel_menu_bolumleri"]:
                    ozel_cols = st.columns(2)
                    for o_idx, o_ad in enumerate(st.session_state["ozel_menu_bolumleri"]):
                        o_key = f"ozel_{o_ad}"
                        with ozel_cols[o_idx % 2]:
                            girilen_o = st.text_input(
                                f"🍽️ {o_ad}",
                                value=st.session_state["ozel_menu_degerleri"].get(o_key, ""),
                                placeholder=f"Örn: {o_ad} içeriği...",
                                key=f"menu_ozel_input_{o_idx}_{o_ad}",
                            )
                            st.session_state["ozel_menu_degerleri"][o_key] = girilen_o
                            if girilen_o.strip():
                                ozel_bolum_girdileri.append(f"{o_ad}: {girilen_o.strip()}")
                            if o_key in chipler:
                                if _bolum_chip_goster(st, o_key, chipler[o_key]):
                                    silinecek_chip_bolumu = o_key

                if silinecek_chip_bolumu is not None:
                    silinen_chip = chipler.pop(silinecek_chip_bolumu, None)
                    if silinen_chip:
                        silinen_kod = silinen_chip.get("recete_kodu")
                        st.session_state.sepet = [
                            s for s in st.session_state.sepet if s.get("recete_kodu") != silinen_kod
                        ]
                    _uretim_taslagini_kaydet(st)
                    st.rerun()

                menulari_birlestir = [
                    f"{etiket}: {ad}"
                    for ad, etiket in [
                        (ana_yemek_ad, MENU_KISIM_ETIKETLERI["ana_yemek"]),
                        (yardimci_yemek_ad, MENU_KISIM_ETIKETLERI["yardimci_yemek"]),
                        (corba_ad, MENU_KISIM_ETIKETLERI["corba"]),
                        (tatli_meyve_yogurt_ad, MENU_KISIM_ETIKETLERI["tatli_meyve_yogurt"]),
                    ]
                    if ad.strip()
                ] + ozel_bolum_girdileri
                yemek_adi = "; ".join(menulari_birlestir) if menulari_birlestir else (ana_yemek_ad or yardimci_yemek_ad or corba_ad or tatli_meyve_yogurt_ad or "Yemek Planı")

                # 3. ÜRETİM PARAMETRELERİ (KİŞİ SAYISI, TARİH, NUMUNE)
                st.markdown("---")
                bolum_basligi_goster(
                    st,
                    "takvim",
                    "2. Üretim Parametreleri & Numune Onayı",
                    "Kişi sayısı, üretim tarihi ve zorunlu şahit numune bilgisini girin",
                    vurgu_renk="#38bdf8",
                )
                p_c1, p_c2 = st.columns(2)
                with p_c1:
                    kisi_sayisi = st.number_input(
                        "Yararlanan Kişi Sayısı", min_value=1, max_value=10000, value=200
                    )
                with p_c2:
                    uretim_tarihi_input = st.date_input(
                        "📅 Yemeğin Yapıldığı Tarih",
                        value=datetime.date.today(),
                    )
                uretim_tarih_str = uretim_tarihi_input.strftime("%Y-%m-%d")

                numune_durumu = st.radio(
                    "🧪 Numune Alındı mı? (Zorunlu)",
                    ["Numune Alındı", "Numune Alınmadı"],
                    index=None,
                    horizontal=True,
                    key="numune_secim_radio",
                )

                # 4. DEPODAN MALZEME EKLEME (MANUEL VEYA QR)
                benzersiz_urunler = sorted(
                    list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
                )

                if not salt_okunur_modu:
                    st.markdown("---")
                    bolum_basligi_goster(
                        st,
                        "stok",
                        "3. Depodan Malzeme Ekle (Manuel / QR)",
                        "Reçete harici veya QR kodlu ürünleri sepete ekleyin",
                        vurgu_renk="#f59e0b",
                    )
                    ekleme_yontemi = st.radio(
                        "Malzeme Ekleme Yöntemi",
                        ["Manuel Seçim", "📷 QR Kod ile Okut"],
                        horizontal=True,
                        key="yemek_ekleme_yontemi_radio",
                    )

                    secilen_urun = None
                    kullanilacak_miktar = 0.0
                    secilen_paket_id = None
                    secilen_fatura_id = None

                    if ekleme_yontemi == "Manuel Seçim":
                        col1, col2, col3 = st.columns([2.0, 1.3, 1.1])
                        with col1:
                            secilen_urun = st.selectbox(
                                "Malzeme Seç",
                                benzersiz_urunler if benzersiz_urunler else [],
                                index=None,
                                placeholder="Malzeme Seçiniz...",
                                key="yemek_urun_manuel",
                            )
                        with col2:
                            stok_max = 0.0
                            if secilen_urun:
                                ilgili_girisler = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == secilen_urun.strip().upper()]
                                stok_max = sum(g.get("kalan", 0) for g in ilgili_girisler)

                            sepet_kullanimi = sum(
                                float(item.get("miktar", 0) or 0)
                                for item in st.session_state.sepet
                                if str(item.get("urun", "")).strip().upper()
                                == str(secilen_urun or "").strip().upper()
                            )
                            kalan_stok = max(float(stok_max) - sepet_kullanimi, 0.0)
                            max_acceptable = min(kalan_stok, 1_000_000.0)
                            max_input = max(max_acceptable, 0.001)
                            try:
                                mevcut_miktar = float(
                                    st.session_state.get("yemek_miktar_manuel", 1.0)
                                )
                            except (TypeError, ValueError):
                                mevcut_miktar = 1.0
                            st.session_state["yemek_miktar_manuel"] = min(
                                max(mevcut_miktar, 0.0), max_input
                            )
                            kullanilacak_miktar = st.number_input(
                                f"Miktar (Stok: {stok_max})",
                                min_value=0.0,
                                max_value=max_input,
                                step=0.1,
                                key="yemek_miktar_manuel",
                            )
                        with col3:
                            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("➕ Sepete Ekle", use_container_width=True, key="btn_sepete_ekle_manuel"):
                                if not secilen_urun:
                                    st.error("⚠️ Lütfen sepete eklemek için bir malzeme seçin!")
                                elif kullanilacak_miktar <= 0:
                                    st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                                else:
                                    yeni_item = {
                                        "urun": secilen_urun,
                                        "miktar": kullanilacak_miktar,
                                    }
                                    try:
                                        stok_hatalari = yemek_sepeti_stok_hatalari(
                                            st.session_state.girisler,
                                            [*st.session_state.sepet, yeni_item],
                                        )
                                    except ValueError as hata:
                                        st.error(f"⚠️ Stok kontrolü yapılamadı: {hata}")
                                    else:
                                        if stok_hatalari:
                                            st.error(f"⚠️ {stok_hatalari[0]}")
                                        else:
                                            st.session_state.sepet.append(yeni_item)
                                            _uretim_taslagini_kaydet(st)
                                            st.success("Eklendi!")
                                            st.rerun()

                    elif ekleme_yontemi == "📷 QR Kod ile Okut":
                        st.info("Kamerayı açın ve paket üzerindeki QR kodu okutun. (Telefon veya Bilgisayar kamerası)")
                        img_file_buffer = st.camera_input("Kamera", label_visibility="collapsed", key="yemek_uretim_kamera")

                        if img_file_buffer is not None:
                            try:
                                import cv2
                                import numpy as np
                            except ImportError:
                                st.error("OpenCV kütüphanesi eksik. Lütfen requirements.txt dosyasını kontrol edin.")
                                st.stop()

                            bytes_data = img_file_buffer.getvalue()
                            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                            detector = cv2.QRCodeDetector()
                            data, bbox, _ = detector.detectAndDecode(cv2_img)

                            if data:
                                qr_okunan_id = data.strip()
                                st.success(f"✅ Okundu: {qr_okunan_id}")

                                ana_id = qr_okunan_id.split("-P")[0] if "-P" in qr_okunan_id else qr_okunan_id
                                ilgili_g = next((g for g in st.session_state.girisler if g.get("id") == ana_id), None)

                                if ilgili_g:
                                    urun_adi = ilgili_g.get("urun")

                                    tum_ayni_urunler = [g for g in st.session_state.girisler if g.get("urun") == urun_adi and float(g.get("kalan", 0)) > 0]
                                    en_eski_urun = min(tum_ayni_urunler, key=lambda x: str(x.get("tarih", ""))) if tum_ayni_urunler else None

                                    if en_eski_urun and en_eski_urun["id"] != ana_id:
                                        st.warning(f"⚠️ **FIFO UYARISI:** Depoda bu üründen daha eski bir parti var (Fatura: {en_eski_urun['id']}, Tarih: {en_eski_urun.get('tarih')}). Lütfen önce eski partiyi tüketin!")

                                    if "-P" in qr_okunan_id:
                                        if "paket_durumlari" not in ilgili_g:
                                            ilgili_g["paket_durumlari"] = {}

                                        paket_miktari = float(ilgili_g.get("paket_miktari", 0))
                                        kalan_paket = ilgili_g["paket_durumlari"].get(qr_okunan_id, paket_miktari)

                                        acik_paketler = [(p_id, p_kg) for p_id, p_kg in ilgili_g.get("paket_durumlari", {}).items() if p_kg > 0 and p_kg < paket_miktari]
                                        if acik_paketler and acik_paketler[0][0] != qr_okunan_id:
                                            st.warning(f"⚠️ **AÇIK PAKET UYARISI:** Bu ürüne ait açık bir paket var! ({acik_paketler[0][0]} - Kalan: {acik_paketler[0][1]} {ilgili_g.get('birim')}). Önce onu kullanmalısınız!")

                                        if kalan_paket <= 0:
                                            st.error("❌ Bu paket tamamen tükenmiş! Lütfen başka bir paket okutun.")
                                        else:
                                            st.info(f"**Paket:** {qr_okunan_id} | **Kalan:** {kalan_paket} {ilgili_g.get('birim')}")
                                            secilen_urun = urun_adi
                                            secilen_paket_id = qr_okunan_id
                                            secilen_fatura_id = ana_id
                                            max_acceptable_paket = min(
                                                max(float(kalan_paket), 0.0), 1_000_000.0
                                            )
                                            max_input_paket = max(max_acceptable_paket, 0.1)
                                            try:
                                                mevcut_paket_miktari = float(
                                                    st.session_state.get("qr_miktar_manuel", 1.0)
                                                )
                                            except (TypeError, ValueError):
                                                mevcut_paket_miktari = 1.0
                                            st.session_state["qr_miktar_manuel"] = min(
                                                max(mevcut_paket_miktari, 0.1),
                                                max_input_paket,
                                            )
                                            kullanilacak_miktar = st.number_input(
                                                f"Kullanılacak Miktar ({ilgili_g.get('birim')})",
                                                min_value=0.1,
                                                max_value=max_input_paket,
                                                step=0.1,
                                                key="qr_miktar_manuel",
                                            )

                                            if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr"):
                                                yeni_item = {
                                                    "urun": urun_adi,
                                                    "miktar": kullanilacak_miktar,
                                                    "paket_id": secilen_paket_id,
                                                    "fatura_id": secilen_fatura_id,
                                                }
                                                stok_hatalari = yemek_sepeti_stok_hatalari(
                                                    st.session_state.girisler,
                                                    [*st.session_state.sepet, yeni_item],
                                                )
                                                if stok_hatalari:
                                                    st.error(f"⚠️ {stok_hatalari[0]}")
                                                else:
                                                    st.session_state.sepet.append(yeni_item)
                                                    _uretim_taslagini_kaydet(st)
                                                    st.success("QR ile Eklendi!")
                                                    st.rerun()
                                    else:
                                        toplam_kalan = float(ilgili_g.get("kalan", 0))
                                        st.info(f"**Dökme Ürün** | **Toplam Stok:** {toplam_kalan} {ilgili_g.get('birim')}")
                                        secilen_urun = urun_adi
                                        max_acceptable_dokme = min(
                                            max(float(toplam_kalan), 0.0), 1_000_000.0
                                        )
                                        max_input_dokme = max(max_acceptable_dokme, 0.1)
                                        try:
                                            mevcut_dokme_miktari = float(
                                                st.session_state.get("qr_miktar_dokme", 1.0)
                                            )
                                        except (TypeError, ValueError):
                                            mevcut_dokme_miktari = 1.0
                                        st.session_state["qr_miktar_dokme"] = min(
                                            max(mevcut_dokme_miktari, 0.1),
                                            max_input_dokme,
                                        )
                                        kullanilacak_miktar = st.number_input(
                                            f"Kullanılacak Miktar ({ilgili_g.get('birim')})",
                                            min_value=0.1,
                                            max_value=max_input_dokme,
                                            step=0.1,
                                            key="qr_miktar_dokme",
                                        )

                                        if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr_dokme"):
                                            yeni_item = {"urun": urun_adi, "miktar": kullanilacak_miktar}
                                            stok_hatalari = yemek_sepeti_stok_hatalari(
                                                st.session_state.girisler,
                                                [*st.session_state.sepet, yeni_item],
                                            )
                                            if stok_hatalari:
                                                st.error(f"⚠️ {stok_hatalari[0]}")
                                            else:
                                                st.session_state.sepet.append(yeni_item)
                                                _uretim_taslagini_kaydet(st)
                                                st.success("QR ile Eklendi!")
                                                st.rerun()
                                else:
                                    st.error("Sistemde böyle bir kayıt bulunamadı.")
                            else:
                                st.warning("⏳ QR Kod aranıyor... Kamerayı koda odaklayın.")

            # -----------------------------------------------------------------
            # SAĞ KOLON: CANLI MENÜ ÖZETİ KARTI + SEPET + ÜRETİMİ TAMAMLA
            # -----------------------------------------------------------------
            with sag_sepet_ozet:
                kalem_maliyetleri, anlik_sepet_maliyet = yemek_sepeti_maliyet_hesapla(
                    st.session_state.girisler, st.session_state.sepet
                )
                anlik_sepet_kalori = 0.0
                for s_item in st.session_state.sepet:
                    s_urun = str(s_item.get("urun", "")).strip()
                    s_mik = float(s_item.get("miktar", 0) or 0)
                    s_birim = next(
                        (
                            g.get("birim", "Kg")
                            for g in st.session_state.girisler
                            if str(g.get("urun", "")).strip().upper() == s_urun.upper()
                        ),
                        "Kg",
                    )
                    anlik_sepet_kalori += float(urun_kalori_hesapla(s_urun, s_mik, s_birim) or 0)

                kisi_basi_plan_maliyet = anlik_sepet_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0.0
                kisi_basi_plan_kalori = anlik_sepet_kalori / kisi_sayisi if kisi_sayisi > 0 else 0.0

                birlesik_alerjenler = sorted(
                    list(
                        set(
                            a
                            for ch in chipler.values()
                            for a in (ch.get("alerjenler") or [])
                        )
                    )
                )
                alerjen_html = (
                    " ".join(
                        f"<span style='display:inline-block;background:rgba(244,63,94,0.18);border:1px solid rgba(244,63,94,0.45);"
                        f"color:#fca5a5;padding:2px 8px;border-radius:999px;font-size:0.72rem;font-weight:700;margin:2px;'>⚠ {html.escape(a)}</span>"
                        for a in birlesik_alerjenler
                    )
                    if birlesik_alerjenler
                    else "<span style='color:#94a3b8;font-size:0.76rem;'>Alerjen uyarısı yok</span>"
                )

                st.markdown(
                    f"""
                    <div style="background:linear-gradient(135deg,rgba(15,23,42,0.96) 0%,rgba(30,41,59,0.88) 100%);
                    border:1px solid rgba(56,189,248,0.38);border-left:4px solid #38bdf8;border-radius:12px;padding:16px;margin-bottom:12px;">
                        <div style="font-size:0.84rem;font-weight:700;color:#38bdf8;letter-spacing:0.5px;margin-bottom:10px;">
                            📊 PLANLANAN MENÜ ÖZETİ (CANLI SEPET HESABI)
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:0.86rem;color:#e2e8f0;">
                            <div style="background:rgba(15,23,42,0.55);padding:8px 10px;border-radius:8px;">
                                <div style="font-size:0.72rem;color:#94a3b8;">Toplam Plan Maliyeti</div>
                                <strong style="font-size:1.0rem;color:#fbbf24;">{para_formatla_tr(anlik_sepet_maliyet)}</strong>
                            </div>
                            <div style="background:rgba(15,23,42,0.55);padding:8px 10px;border-radius:8px;">
                                <div style="font-size:0.72rem;color:#94a3b8;">Kişi Başı Maliyet</div>
                                <strong style="font-size:1.0rem;color:#fbbf24;">{para_formatla_tr(kisi_basi_plan_maliyet)}</strong>
                            </div>
                            <div style="background:rgba(15,23,42,0.55);padding:8px 10px;border-radius:8px;">
                                <div style="font-size:0.72rem;color:#94a3b8;">Toplam Plan Kalori</div>
                                <strong style="font-size:1.0rem;color:#10b981;">{anlik_sepet_kalori:,.0f} kcal</strong>
                            </div>
                            <div style="background:rgba(15,23,42,0.55);padding:8px 10px;border-radius:8px;">
                                <div style="font-size:0.72rem;color:#94a3b8;">Kişi Başı Kalori</div>
                                <strong style="font-size:1.0rem;color:#10b981;">{kisi_basi_plan_kalori:,.0f} kcal</strong>
                            </div>
                        </div>
                        <div style="margin-top:10px;padding-top:8px;border-top:1px solid rgba(148,163,184,0.2);">
                            <span style="font-size:0.76rem;color:#cbd5e1;margin-right:6px;">🩺 Menü Alerjenleri:</span>{alerjen_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not salt_okunur_modu:
                    st.button(
                        "📷 QR ile Malzeme Teslim Al",
                        use_container_width=True,
                        key="btn_hizli_qr_teslim_al",
                        on_click=_qr_moduna_gec_callback,
                        args=(st,),
                    )

                st.markdown("---")
                sp_h1, sp_h2 = st.columns([2.2, 1.2])
                with sp_h1:
                    st.markdown(f"#### 🛒 Aktif Üretim Sepeti ({len(st.session_state.sepet)} Kalem)")
                with sp_h2:
                    if st.session_state.sepet and not salt_okunur_modu:
                        if st.button("🔄 Sıfırla", use_container_width=True, key="btn_sepet_sifirla"):
                            st.session_state.sepet = []
                            st.session_state["uretim_bolum_chipleri"] = {}
                            _uretim_taslagini_kaydet(st)
                            st.rerun()

                if st.session_state.sepet:
                    excel_sepet_liste = []
                    silinecek_index = None

                    for idx, item in enumerate(st.session_state.sepet):
                        urun = item["urun"]
                        istenen = item["miktar"]

                        ilgili_girisler = [
                            g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper()
                        ]
                        son_birim_f = en_son_urun_birim_fiyati(st.session_state.girisler, urun)
                        item_maliyeti = kalem_maliyetleri[idx]
                        birim = ilgili_girisler[0].get("birim", "Kg") if ilgili_girisler else "Kg"
                        item_kalorisi = urun_kalori_hesapla(urun, istenen, birim)

                        c_item_bilgi, c_item_sil = st.columns([4.5, 0.9])
                        with c_item_bilgi:
                            st.markdown(
                                f"**• {urun}** — `{istenen} {birim}` • **{para_formatla_tr(item_maliyeti)}**"
                            )
                            st.caption(f"Birim: {para_formatla_tr(son_birim_f)} | Kalori: {item_kalorisi:,.0f} kcal")
                        with c_item_sil:
                            if not salt_okunur_modu:
                                if st.button("❌", key=f"sil_item_{idx}"):
                                    silinecek_index = idx

                        excel_sepet_liste.append({
                            "Malzeme": urun,
                            "Miktar": f"{istenen} {birim}",
                            "Maliyet (TL)": round(item_maliyeti, 2),
                            "Kalori (kcal)": round(item_kalorisi, 2),
                        })

                    if silinecek_index is not None:
                        st.session_state.sepet.pop(silinecek_index)
                        _uretim_taslagini_kaydet(st)
                        st.rerun()

                    # Geçmiş kullanım sapma kontrolü
                    gecmis_istatistikleri = {}
                    gecmis_kontrol_mesajlari = []
                    if not salt_okunur_modu:
                        mevcut_menu = {
                            "ana_yemek": ana_yemek_ad,
                            "yardimci_yemek": yardimci_yemek_ad,
                            "corba": corba_ad,
                            "tatli_meyve_yogurt": tatli_meyve_yogurt_ad,
                        }
                        gecmis_istatistikleri = yemek_malzeme_kullanim_istatistikleri(
                            st.session_state.yemek_uretim_arsivi,
                            mevcut_menu,
                            kisi_sayisi,
                            uretim_tarih_str,
                        )
                        sepet_miktarlari = {}
                        sepet_adlari = {}
                        sepet_birimleri = {}
                        for item in st.session_state.sepet:
                            malzeme_anahtari = "".join(
                                str(item.get("urun", "")).split()
                            ).upper()
                            if not malzeme_anahtari:
                                continue
                            sepet_miktarlari[malzeme_anahtari] = (
                                sepet_miktarlari.get(malzeme_anahtari, 0.0)
                                + float(item.get("miktar", 0) or 0)
                            )
                            sepet_adlari[malzeme_anahtari] = str(item.get("urun", "")).strip()
                            sepet_birimleri[malzeme_anahtari] = next(
                                (
                                    g.get("birim", "Kg")
                                    for g in st.session_state.girisler
                                    if str(g.get("urun", "")).strip().upper()
                                    == str(item.get("urun", "")).strip().upper()
                                ),
                                "Kg",
                            )

                        for malzeme_anahtari, istatistik in gecmis_istatistikleri.items():
                            if malzeme_anahtari not in sepet_miktarlari:
                                continue
                            miktar = sepet_miktarlari[malzeme_anahtari]
                            birim = sepet_birimleri.get(malzeme_anahtari, "")
                            birim_eki = f" {birim}" if birim else ""
                            gecmis_kontrol_mesajlari.append(
                                f"**{sepet_adlari[malzeme_anahtari]}**: Geçmişte "
                                f"{istatistik['uretim_sayisi']} üretimde kişi başı ortalama "
                                f"{istatistik['ortalama_kisi_basi']:g}{birim_eki}/kişi "
                                f"kullanılmıştı. {kisi_sayisi:g} kişi için beklenen miktar "
                                f"yaklaşık **{istatistik['beklenen_miktar']:g}{birim_eki}**; "
                                f"bu üretimde **{miktar:g}{birim_eki}** girildi."
                            )

                        if gecmis_kontrol_mesajlari:
                            gecmis_uyarilari = yemek_malzeme_kullanim_uyarilari(
                                gecmis_istatistikleri,
                                st.session_state.sepet,
                                kisi_sayisi,
                                sepet_birimleri,
                            )
                            if gecmis_uyarilari:
                                st.warning(
                                    "⚠️ **Geçmiş kullanım kontrolü:** Üretimi tamamlamadan "
                                    "önce aşağıdaki sapmaları inceleyin."
                                )
                            else:
                                st.info(
                                    "ℹ️ **Geçmiş kullanım kontrolü:** Önceki üretim "
                                    "ortalamasıyla karşılaştırma yapıldı."
                                )
                            for mesaj in gecmis_kontrol_mesajlari[:5]:
                                st.markdown(mesaj)
                            kontrol_imzasi = (
                                yemek_adi,
                                str(kisi_sayisi),
                                tuple(sorted(sepet_miktarlari.items())),
                            )
                            kontrol_anahtari = (
                                "yemek_gecmis_kontrol_onayi_"
                                + str(abs(hash(kontrol_imzasi)))
                            )
                            kontrol_okundu = st.checkbox(
                                "Geçmiş kullanım kontrolünü okudum, üretime devam et",
                                key=kontrol_anahtari,
                            )
                        else:
                            kontrol_okundu = True
                    else:
                        kontrol_okundu = True

                    if not salt_okunur_modu:
                        st.markdown("---")
                        if st.button(
                            "🍲 Üretimi Tamamla ve Stoktan / Kullanıma Düş",
                            type="primary",
                            use_container_width=True,
                        ):
                            if gecmis_kontrol_mesajlari and not kontrol_okundu:
                                st.error(
                                    "⚠️ Üretimi tamamlamak için geçmiş kullanım "
                                    "karşılaştırmasını okuyup onaylayın."
                                )
                            elif not numune_durumu:
                                st.error("⚠️ Lütfen üretimi tamamlamadan önce 'Numune Alındı / Alınmadı' seçeneğini işaretleyin!")
                            else:
                                tarih_simdi = simdi_tr_str("%Y-%m-%d %H:%M")

                                arsiv_malzemeler = []
                                dusulen_kayitlar = []
                                eklenen_loglar = []

                                uretim_islem_id = f"URM-{int(time.time() * 1000)}"

                                for item in st.session_state.sepet:
                                    urun = item["urun"]
                                    istenen = item["miktar"]
                                    kalan_dusulecek = istenen
                                    son_birim_f = en_son_urun_birim_fiyati(st.session_state.girisler, urun)
                                    item_tutar = float(istenen) * son_birim_f
                                    item_partiler = []
                                    paket_id = item.get("paket_id")
                                    fatura_id = item.get("fatura_id")

                                    ilgili_g = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper() and g.get("kalan", 0) > 0]

                                    if paket_id and fatura_id:
                                        ilgili_g = [g for g in ilgili_g if g["id"] == fatura_id]

                                    for g in ilgili_g:
                                        if kalan_dusulecek <= 0:
                                            break

                                        if paket_id and g["id"] == fatura_id:
                                            if "paket_durumlari" not in g:
                                                g["paket_durumlari"] = {}
                                            mevcut_paket = g["paket_durumlari"].get(paket_id, float(g.get("paket_miktari", 0)))

                                            dusulecek = min(kalan_dusulecek, mevcut_paket)
                                            g["paket_durumlari"][paket_id] = mevcut_paket - dusulecek
                                            g["kalan"] = float(g["kalan"]) - dusulecek

                                            kalan_dusulecek -= dusulecek

                                            dusulen_kayitlar.append({"id": g["id"], "miktar": dusulecek, "paket_id": paket_id})
                                            item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": dusulecek, "paket_id": paket_id})
                                        else:
                                            if float(g["kalan"]) >= kalan_dusulecek:
                                                g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                                dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek, "paket_id": None})
                                                item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": kalan_dusulecek, "paket_id": None})
                                                kalan_dusulecek = 0
                                            else:
                                                dusulen = float(g["kalan"])
                                                g["kalan"] = 0.0
                                                dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen, "paket_id": None})
                                                item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": dusulen, "paket_id": None})
                                                kalan_dusulecek -= dusulen

                                    arsiv_malzemeler.append(
                                        {
                                            "urun": urun,
                                            "miktar": istenen,
                                            "birim": next(
                                                (
                                                    g.get("birim", "Kg")
                                                    for g in st.session_state.girisler
                                                    if g.get("urun", "").strip().upper() == urun.strip().upper()
                                                ),
                                                "Kg",
                                            ),
                                            "tutar": item_tutar,
                                            "partiler": list(item_partiler),
                                            "kalori": urun_kalori_hesapla(
                                                urun,
                                                istenen,
                                                next(
                                                    (
                                                        g.get("birim", "Kg")
                                                        for g in st.session_state.girisler
                                                        if g.get("urun", "").strip().upper() == urun.strip().upper()
                                                    ),
                                                    "Kg",
                                                ),
                                            ),
                                        }
                                    )

                                    log_obj = {
                                        "uretim_id": uretim_islem_id,
                                        "tarih": f"{uretim_tarih_str} 12:00",
                                        "urun": urun,
                                        "tur": f"Günlük Kullanım ({yemek_adi})",
                                        "miktar": istenen,
                                        "tutar": item_tutar,
                                        "partiler": list(item_partiler),
                                        "islem_yapan": st.session_state.aktif_kullanici,
                                    }
                                    st.session_state.kullanim_loglari.append(log_obj)
                                    eklenen_loglar.append(log_obj)

                                gercek_toplam_maliyet = sum(
                                    float(m.get("tutar", 0) or 0) for m in arsiv_malzemeler
                                )

                                arsiv_obj = {
                                    "uretim_id": uretim_islem_id,
                                    "tarih": uretim_tarih_str,
                                    "zaman": tarih_simdi,
                                    "yemek_adi": yemek_adi,
                                    "menu_ana_yemek": ana_yemek_ad.strip() if ana_yemek_ad.strip() else None,
                                    "menu_yardimci_yemek": yardimci_yemek_ad.strip() if yardimci_yemek_ad.strip() else None,
                                    "menu_corba": corba_ad.strip() if corba_ad.strip() else None,
                                    "menu_tatli_meyve_yogurt": tatli_meyve_yogurt_ad.strip() if tatli_meyve_yogurt_ad.strip() else None,
                                    "kisi_sayisi": kisi_sayisi,
                                    "numune_durumu": numune_durumu,
                                    "malzemeler": arsiv_malzemeler,
                                    "partiler": [
                                        {
                                            "fatura_id": d["id"],
                                            "dusulen_miktar": d["miktar"],
                                            "paket_id": d.get("paket_id"),
                                        }
                                        for d in dusulen_kayitlar
                                    ],
                                    "toplam_maliyet": gercek_toplam_maliyet,
                                    "toplam_kalori": anlik_sepet_kalori,
                                    "kisi_basi_kalori": (
                                        anlik_sepet_kalori / kisi_sayisi if kisi_sayisi > 0 else 0.0
                                    ),
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                }
                                st.session_state.yemek_uretim_arsivi.append(arsiv_obj)

                                st.session_state["son_yemek_uretim_kaydi"] = {
                                    "yemek_adi": yemek_adi,
                                    "kisi_sayisi": kisi_sayisi,
                                    "toplam_maliyet": gercek_toplam_maliyet,
                                    "tarih": uretim_tarih_str,
                                    "menu_ana_yemek": ana_yemek_ad.strip() if ana_yemek_ad.strip() else None,
                                    "menu_yardimci_yemek": yardimci_yemek_ad.strip() if yardimci_yemek_ad.strip() else None,
                                    "menu_corba": corba_ad.strip() if corba_ad.strip() else None,
                                    "menu_tatli_meyve_yogurt": tatli_meyve_yogurt_ad.strip() if tatli_meyve_yogurt_ad.strip() else None,
                                    "dusulen_kayitlar": dusulen_kayitlar,
                                    "arsiv_objesi": arsiv_obj,
                                    "eklenen_loglar": eklenen_loglar,
                                }

                                yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)
                                verileri_kaydet(st.session_state.girisler)
                                loglari_kaydet(st.session_state.kullanim_loglari)
                                st.session_state.sepet = []
                                st.session_state["uretim_bolum_chipleri"] = {}
                                _uretim_taslagini_kaydet(st)
                                st.success(
                                    f"🎉 Başarılı! {uretim_tarih_str} tarihli üretim arşive kaydedildi."
                                )
                                st.balloons()
                                time.sleep(1)
                                st.rerun()

                        pdf_data = tablo_to_html_pdf_bytes(
                            f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste
                        )
                        excel_sepet_data = tablo_to_excel_bytes(
                            excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}"
                        )
                        ortak_indirme_alani(
                            excel_sepet_data,
                            pdf_data,
                            "yemek_maliyet_raporu",
                            "yemek_sayfasi",
                        )
                else:
                    st.info("Henüz sepete malzeme eklenmedi. Soldan hazır reçete seçin veya manuel/QR malzeme ekleyin.")

    # =========================================================================
    # SEKME 2: ÜRETİM & MALİYET ARŞİVİ VE TARİH ARALIĞI RAPORLAMA
    # =========================================================================
    with tab_arsiv:
        col_tarih_mod, col_tarih_sec = st.columns([1.2, 1.8])
        with col_tarih_mod:
            zaman_modu = st.radio(
                "Arşiv Görünüm Modu", ["Tek Tarih", "Tarih Aralığı", "Tüm Zamanlar"], horizontal=True
            )
        with col_tarih_sec:
            if zaman_modu == "Tek Tarih":
                secilen_tarih_filtresi = st.date_input(
                    "📅 Sorgulanacak Tarihi Seçin", value=datetime.date.today()
                )
                secilen_tarih_str = secilen_tarih_filtresi.strftime("%Y-%m-%d")
            elif zaman_modu == "Tarih Aralığı":
                c_bas, c_bit = st.columns(2)
                with c_bas:
                    bas_tarih_filt = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7))
                with c_bit:
                    bit_tarih_filt = st.date_input("Bitiş Tarihi", value=datetime.date.today())
                secilen_tarih_str = f"{bas_tarih_filt} - {bit_tarih_filt}"
            else:
                secilen_tarih_str = "TÜMÜ"

        st.markdown("---")
        col_b_arsiv, col_indir_arsiv = st.columns([2, 2])
        with col_b_arsiv:
            if zaman_modu == "Tüm Zamanlar":
                bolum_basligi_goster(
                    st,
                    "rapor",
                    "Tüm Zamanların Yemek Üretim ve Maliyet Arşivi",
                    "Sistemde kayıtlı bütün menü üretimlerinin maliyet ve porsiyon dökümü",
                    vurgu_renk="#f59e0b",
                )
                secilen_gun_uretimleri = st.session_state.yemek_uretim_arsivi
            elif zaman_modu == "Tek Tarih":
                bolum_basligi_goster(
                    st,
                    "takvim",
                    f"Seçilen Tarihteki ({secilen_tarih_str}) Yemek Üretim ve Maliyet Arşivi",
                    "Seçili güne ait menü, malzeme ve porsiyon analiz tablosu",
                    vurgu_renk="#f59e0b",
                )
                secilen_gun_uretimleri = [
                    u
                    for u in st.session_state.yemek_uretim_arsivi
                    if u.get("tarih") == secilen_tarih_str
                ]
            else:
                bolum_basligi_goster(
                    st,
                    "takvim",
                    f"Tarih Aralığı Arşivi ({bas_tarih_filt} ile {bit_tarih_filt} arası)",
                    "Belirtilen tarih aralığındaki tüm üretim ve maliyet kayıtları",
                    vurgu_renk="#f59e0b",
                )
                secilen_gun_uretimleri = []
                for u in st.session_state.yemek_uretim_arsivi:
                    t_str = u.get("tarih", "")
                    try:
                        t_dt = datetime.datetime.strptime(t_str, "%Y-%m-%d").date()
                        if bas_tarih_filt <= t_dt <= bit_tarih_filt:
                            secilen_gun_uretimleri.append(u)
                    except Exception:
                        pass

        if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" in aktif_k_maskeleri:
            st.info("🔒 Yemek Üretim ve Maliyet Arşivi bu kullanıcı için maskelenmiştir (gizlenmiştir).")
        else:
            if secilen_gun_uretimleri:
                arsiv_tablo_verisi = []
                excel_arsiv_listesi = []
                for u_kayit in secilen_gun_uretimleri:
                    toplam_maliyet_degeri = float(u_kayit.get("toplam_maliyet", 0))
                    if toplam_maliyet_degeri == 0 and u_kayit.get("malzemeler"):
                        toplam_maliyet_degeri = sum(float(m.get("tutar", 0)) for m in u_kayit.get("malzemeler", []))

                    kisi_sayisi_degeri = int(u_kayit.get("kisi_sayisi", 1) or 1)
                    kisi_basi_maliyet = toplam_maliyet_degeri / kisi_sayisi_degeri if kisi_sayisi_degeri > 0 else 0.0
                    toplam_kalori_degeri = float(u_kayit.get("toplam_kalori", 0))
                    kisi_basi_kalori_degeri = (
                        float(u_kayit.get("kisi_basi_kalori", 0))
                        or (toplam_kalori_degeri / kisi_sayisi_degeri if kisi_sayisi_degeri > 0 else 0.0)
                    )

                    if misafir_modu:
                        arsiv_tablo_verisi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                            "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                            "Çorba": u_kayit.get("menu_corba", "-"),
                            "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                        })
                        excel_arsiv_listesi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                            "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                            "Çorba": u_kayit.get("menu_corba", "-"),
                            "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                        })
                    else:
                        for m in u_kayit.get("malzemeler", []):
                            arsiv_tablo_verisi.append({
                                "Tarih": u_kayit.get("tarih", "-"),
                                "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                                "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                                "Çorba": u_kayit.get("menu_corba", "-"),
                                "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                                "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                                "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                                "Kullanılan Malzeme": f"{m.get('urun', '-')} ({m.get('miktar', '-')} {m.get('birim', '')})".strip(),
                                "Malzeme Maliyeti": para_formatla_tr(m.get("tutar", 0)),
                                "Menü Toplam Maliyeti": para_formatla_tr(toplam_maliyet_degeri),
                                "Kişi Başı Maliyet": para_formatla_tr(kisi_basi_maliyet),
                                "Menü Toplam Kalorisi": f"{toplam_kalori_degeri:,.0f} kcal",
                                "Kişi Başı Kalori": f"{kisi_basi_kalori_degeri:,.0f} kcal",
                                "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                            })
                            excel_arsiv_listesi.append({
                                "Tarih": u_kayit.get("tarih", "-"),
                                "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                                "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                                "Çorba": u_kayit.get("menu_corba", "-"),
                                "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                                "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                                "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                                "Kullanılan Malzeme": f"{m.get('urun', '-')} ({m.get('miktar', '-')} {m.get('birim', '')})".strip(),
                                "Malzeme Maliyeti (TL)": round(m.get("tutar", 0), 2),
                                "Menü Toplam Maliyeti (TL)": round(toplam_maliyet_degeri, 2),
                                "Kişi Başı Maliyet (TL)": round(kisi_basi_maliyet, 2),
                                "Menü Toplam Kalorisi (kcal)": round(toplam_kalori_degeri, 2),
                                "Kişi Başı Kalori (kcal)": round(kisi_basi_kalori_degeri, 2),
                                "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                            })

                rapor_adi_etiketi = "yemek_uretim_raporu_arsiv"
                baslik_etiketi = "Aziziye Aşevi - Yemek Üretim Raporu Arşivi"

                excel_arsiv_data = tablo_to_excel_bytes(
                    excel_arsiv_listesi, baslik_etiketi
                )
                pdf_arsiv_data = tablo_to_html_pdf_bytes(baslik_etiketi, excel_arsiv_listesi)

                with col_indir_arsiv:
                    ortak_indirme_alani(
                        excel_arsiv_data,
                        pdf_arsiv_data,
                        rapor_adi_etiketi,
                        "arsiv_tarih_araligi",
                    )

                ozel_html_tablo_goster(arsiv_tablo_verisi)
            else:
                st.info("Seçilen tarih aralığında kayıtlı yemek üretim ve maliyet arşivi bulunmuyor.")

    # =========================================================================
    # SEKME 3: SAPMA UYARILARI & ADMIN MENÜ DÜZENLEME ARACI
    # =========================================================================
    with tab_analiz:
        bolum_basligi_goster(
            st,
            "uyari",
            "Malzeme Kullanım Uyarısı (Geçmiş Veri Karşılaştırması)",
            "Kişi başı geçmiş üretim ortalamalarına göre ±%10 sapma kontrolü",
            vurgu_renk="#f43f5e",
        )

        if "malzeme_uyari_aktif" not in st.session_state:
            st.session_state.malzeme_uyari_aktif = True

        aktif_maskeler = aktif_k_maskeleri if isinstance(aktif_k_maskeleri, list) else []

        if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" not in aktif_maskeler:
            if st.session_state.yemek_uretim_arsivi:
                son_yemek = st.session_state.yemek_uretim_arsivi[-1] if st.session_state.yemek_uretim_arsivi else None

                if son_yemek and st.session_state.malzeme_uyari_aktif:
                    menu_ogeleri = {
                        "ana_yemek": son_yemek.get("menu_ana_yemek") or "",
                        "yardimci_yemek": son_yemek.get("menu_yardimci_yemek") or "",
                        "corba": son_yemek.get("menu_corba") or "",
                        "tatli_meyve_yogurt": son_yemek.get("menu_tatli_meyve_yogurt") or "",
                    }
                    if not any(menu_ogeleri.values()):
                        menu_ogeleri = son_yemek.get("yemek_adi", "")

                    kisi_sayisi_uyari = son_yemek.get("kisi_sayisi", 0)
                    istatistikler = yemek_malzeme_kullanim_istatistikleri(
                        st.session_state.yemek_uretim_arsivi,
                        menu_ogeleri,
                        kisi_sayisi_uyari,
                        son_yemek.get("tarih"),
                        son_yemek.get("zaman"),
                    )
                    birimler = {
                        "".join(str(item.get("urun", "")).split()).upper(): item.get("birim", "")
                        for item in son_yemek.get("malzemeler", [])
                        if isinstance(item, dict) and item.get("urun")
                    }
                    uyarilar = yemek_malzeme_kullanim_uyarilari(
                        istatistikler,
                        son_yemek.get("malzemeler", []),
                        kisi_sayisi_uyari,
                        birimler,
                    )

                    if uyarilar:
                        st.warning("🔍 **Malzeme Kullanım Uyarısı** (Kişi başı geçmiş ortalaması, tolerans: %±10)")
                        for uyari in uyarilar[:5]:
                            st.markdown(uyari)

                        if len(uyarilar) > 5:
                            st.caption(f"... ve {len(uyarilar) - 5} daha fazla uyarı")
                    else:
                        st.success("✅ Son üretimde geçmiş ortalamalara göre ±%10 üzeri sapma tespit edilmedi.")
            else:
                st.info("Karşılaştırma yapılacak geçmiş üretim kaydı bulunmuyor.")

        if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" not in aktif_maskeler:
            if yonetici_modu:
                st.markdown("---")
                with st.expander("🔧 Menü Düzenleme ve Güncelleme Aracı", expanded=True):
                    st.markdown("**Varolan yemek kayıtlarını güncelleyebilirsiniz.**")
                    st.markdown("Bu araç yalnızca **admin** kullanıcılar için görünürdür.")

                    uretim_arsivi = st.session_state.yemek_uretim_arsivi if "yemek_uretim_arsivi" in st.session_state else []
                    if not uretim_arsivi:
                        st.info("Henüz kayıtlı yemek üretim kaydı bulunmuyor.")
                    else:
                        col_filt1, col_filt2 = st.columns(2)
                        with col_filt1:
                            filtre_tarih = st.date_input(
                                "📅 Tarih Süzgesi (İsteğe bağlı)",
                                value=None,
                                key="menu_guncelle_tarih_filt",
                            )
                        with col_filt2:
                            if st.button("🔄 Tümünü Yeniden Düzenle", key="btn_yeniden_duzelt_tum"):
                                for kayit in uretim_arsivi:
                                    zaten_var = any([
                                        kayit.get("menu_ana_yemek"),
                                        kayit.get("menu_yardimci_yemek"),
                                        kayit.get("menu_corba"),
                                        kayit.get("menu_tatli_meyve_yogurt"),
                                    ])
                                    if kayit.get("yemek_adi") and not zaten_var:
                                        eski_yemek = kayit.get("yemek_adi", "")
                                        kayit["menu_ana_yemek"] = eski_yemek
                                        kayit["menu_yardimci_yemek"] = None
                                        kayit["menu_corba"] = None
                                        kayit["menu_tatli_meyve_yogurt"] = None
                                st.success(f"✅ {len(uretim_arsivi)} kayıt yeni formata çevrildi!")
                                yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                st.rerun()

                        gosterilecek_kayitlar = uretim_arsivi
                        if filtre_tarih:
                            gosterilecek_kayitlar = [
                                k for k in uretim_arsivi
                                if k.get("tarih") == filtre_tarih.strftime("%Y-%m-%d")
                            ]

                        if not gosterilecek_kayitlar:
                            st.info("Seçilen tarihte kayıt bulunmuyor.")
                        else:
                            st.markdown(f"🗂️ **{len(gosterilecek_kayitlar)} kayıt bulundu**")

                            for idx, kayit in enumerate(gosterilecek_kayitlar):
                                tarih = kayit.get("tarih", "-")
                                eski_yemek = kayit.get("yemek_adi", "")
                                kayit_key = f"{kayit.get('uretim_id', 'k')}_{idx}"

                                zaten_yeni_format = any([
                                    kayit.get("menu_ana_yemek"),
                                    kayit.get("menu_yardimci_yemek"),
                                    kayit.get("menu_corba"),
                                    kayit.get("menu_tatli_meyve_yogurt"),
                                ])

                                if zaten_yeni_format:
                                    col1, col2, col3, col4, col_btn = st.columns([2, 2, 2, 2, 1])
                                    with col1:
                                        yeni_ana = st.text_input(
                                            f"🥘 Ana Yemek ({tarih})",
                                            value=kayit.get("menu_ana_yemek") or "",
                                            key=f"duz_alt_{kayit_key}",
                                            label_visibility="collapsed",
                                        )
                                    with col2:
                                        yeni_yardimci = st.text_input(
                                            f"🍛 Ara Yemek ({tarih})",
                                            value=kayit.get("menu_yardimci_yemek") or "",
                                            key=f"duz_aryad_{kayit_key}",
                                            label_visibility="collapsed",
                                        )
                                    with col3:
                                        yeni_corba = st.text_input(
                                            f"🍲 Çorba ({tarih})",
                                            value=kayit.get("menu_corba") or "",
                                            key=f"duz_corba_{kayit_key}",
                                            label_visibility="collapsed",
                                        )
                                    with col4:
                                        yeni_tatlilar = st.text_input(
                                            f"🍨 Tatlı/Meyve/Yoğurt ({tarih})",
                                            value=kayit.get("menu_tatli_meyve_yogurt") or "",
                                            key=f"duz_tatlilar_{kayit_key}",
                                            label_visibility="collapsed",
                                        )
                                    with col_btn:
                                        if st.button("💾 Kaydet", key=f"btn_kaydet_{kayit_key}"):
                                            temiz_ana = (yeni_ana or "").strip()
                                            temiz_yardimci = (yeni_yardimci or "").strip()
                                            temiz_corba = (yeni_corba or "").strip()
                                            temiz_tatlilar = (yeni_tatlilar or "").strip()

                                            kayit["menu_ana_yemek"] = temiz_ana or None
                                            kayit["menu_yardimci_yemek"] = temiz_yardimci or None
                                            kayit["menu_corba"] = temiz_corba or None
                                            kayit["menu_tatli_meyve_yogurt"] = temiz_tatlilar or None

                                            bolumler = []
                                            if temiz_ana:
                                                bolumler.append(f"Ana Yemek: {temiz_ana}")
                                            if temiz_yardimci:
                                                bolumler.append(f"Ara Yemek / Tatlı: {temiz_yardimci}")
                                            if temiz_corba:
                                                bolumler.append(f"Çorba: {temiz_corba}")
                                            if temiz_tatlilar:
                                                bolumler.append(f"Tatlı / Meyve / Yoğurt: {temiz_tatlilar}")
                                            kayit["yemek_adi"] = "; ".join(bolumler) if bolumler else eski_yemek

                                            yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                            st.success(f"✅ {tarih} tarihli kayıt güncellendi!")
                                            st.rerun()

                                    if st.button("🗑️ Sil", key=f"btn_sil_{kayit_key}", type="secondary"):
                                        uretim_arsivi.remove(kayit)
                                        yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                        st.warning(f"🗑️ {tarih} tarihli kayıt silindi!")
                                        st.rerun()

                                else:
                                    col_old1, col_old2, col_old3 = st.columns([3, 3, 1])
                                    with col_old1:
                                        st.markdown(f"**📅 {tarih}**")
                                        st.markdown(f"Eski kayıt: `{eski_yemek}`")

                                    with col_old2:
                                        st.markdown("### 4'lü formatta dönüştür:")
                                        c_a, c_b, c_c, c_d = st.columns(4)
                                        with c_a:
                                            yeni_ana = st.text_input("Ana Yemek", value="", key=f"cevir_alt_{kayit_key}", label_visibility="collapsed")
                                        with c_b:
                                            yeni_yardimci = st.text_input("Ara Yemek", value="", key=f"cevir_aryad_{kayit_key}", label_visibility="collapsed")
                                        with c_c:
                                            yeni_corba = st.text_input("Çorba", value="", key=f"cevir_corba_{kayit_key}", label_visibility="collapsed")
                                        with c_d:
                                            yeni_tatlilar = st.text_input("Tatlı/Meyve", value="", key=f"cevir_tatlilar_{kayit_key}", label_visibility="collapsed")

                                    with col_old3:
                                        if st.button("🔄 Çevir", key=f"btn_cevir_{kayit_key}"):
                                            temiz_ana = (yeni_ana or "").strip()
                                            temiz_yardimci = (yeni_yardimci or "").strip()
                                            temiz_corba = (yeni_corba or "").strip()
                                            temiz_tatlilar = (yeni_tatlilar or "").strip()

                                            kayit["menu_ana_yemek"] = temiz_ana or None
                                            kayit["menu_yardimci_yemek"] = temiz_yardimci or None
                                            kayit["menu_corba"] = temiz_corba or None
                                            kayit["menu_tatli_meyve_yogurt"] = temiz_tatlilar or None

                                            bolumler = []
                                            if temiz_ana:
                                                bolumler.append(f"Ana Yemek: {temiz_ana}")
                                            if temiz_yardimci:
                                                bolumler.append(f"Ara Yemek / Tatlı: {temiz_yardimci}")
                                            if temiz_corba:
                                                bolumler.append(f"Çorba: {temiz_corba}")
                                            if temiz_tatlilar:
                                                bolumler.append(f"Tatlı / Meyve / Yoğurt: {temiz_tatlilar}")
                                            kayit["yemek_adi"] = "; ".join(bolumler) if bolumler else eski_yemek

                                            yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                            st.success(f"✅ {tarih} kaydı yeni formata çevrildi!")
                                            st.rerun()
