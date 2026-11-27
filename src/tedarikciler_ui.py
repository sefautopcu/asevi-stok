# src/tedarikciler_ui.py
import html
import time
from src.tedarikciler_sql import (
    TEDARIKCI_KATEGORILERI,
    tedarikci_alim_istatistikleri,
    tedarikci_dogrula,
    yeni_tedarikci_id_uret,
)

TEDARIKCI_SAYFA_ETIKETI = "Tedarikçi ve Firma Rehberi"

KATEGORI_RENKLERI = {
    "🥩 Et ve Tavuk Ürünleri": "#ef4444",
    "🌾 Bakliyat ve Kuru Gıda": "#f59e0b",
    "🥬 Sebze ve Meyve": "#10b981",
    "🥛 Süt ve Kahvaltılık": "#38bdf8",
    "🫒 Yağ, Salça ve Baharat": "#eab308",
    "🍞 Unlu Mamuller ve Ekmek": "#d97706",
    "📦 Ambalaj ve Temizlik": "#a855f7",
    "🏪 Genel Gıda": "#14b8a6",
}


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = TEDARIKCI_SAYFA_ETIKETI.lower()
    for maske in aktif_k_maskeleri:
        if hedef in str(maske or "").lower():
            return True
    return False


def _kpi_karti_html(ikon, baslik, deger, alt_bilgi, vurgu_renk="#10b981"):
    return f"""
    <div style="
        background: linear-gradient(145deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-left: 4px solid {vurgu_renk};
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 8px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
    ">
        <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 6px;">
            {ikon} {html.escape(str(baslik))}
        </div>
        <div style="font-size: 1.65rem; color: #f8fafc; font-weight: 700; line-height: 1.2;">
            {html.escape(str(deger))}
        </div>
        <div style="font-size: 0.78rem; color: #64748b; margin-top: 6px;">
            {html.escape(str(alt_bilgi))}
        </div>
    </div>
    """


def _firma_karti_html(kayit):
    firma_adi = html.escape(str(kayit.get("firma_adi", "-")))
    kid = html.escape(str(kayit.get("id", "-")))
    kategori = str(kayit.get("kategori", "🏪 Genel Gıda"))
    kategori_esc = html.escape(kategori)
    yetkili = html.escape(str(kayit.get("yetkili_kisi") or "Belirtilmedi"))
    telefon = html.escape(str(kayit.get("telefon") or "Belirtilmedi"))
    vergi_no = html.escape(str(kayit.get("vergi_no") or "Belirtilmedi"))
    adres = html.escape(str(kayit.get("adres") or "Adres girilmemiş"))
    notlar = html.escape(str(kayit.get("notlar") or ""))
    aktif = bool(kayit.get("aktif", True))

    renk = KATEGORI_RENKLERI.get(kategori, "#14b8a6")
    durum_rozet = (
        '<span style="background: rgba(16,185,129,0.16); color: #34d399; border: 1px solid rgba(16,185,129,0.35); '
        'padding: 3px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;">✅ Aktif Firma</span>'
        if aktif
        else '<span style="background: rgba(244,63,94,0.16); color: #fb7185; border: 1px solid rgba(244,63,94,0.35); '
        'padding: 3px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;">⏸️ Pasif / Arşiv</span>'
    )
    not_satiri = (
        f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(148,163,184,0.2); '
        f'font-size: 0.82rem; color: #cbd5e1;">📝 <i>{notlar}</i></div>'
        if notlar
        else ""
    )

    return f"""
    <div style="
        background: linear-gradient(145deg, #0b1220 0%, #131c31 100%);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-left: 5px solid {renk};
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
            <div>
                <span style="background: rgba(56,189,248,0.14); color: #7dd3fc; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin-right: 8px;">
                    {kid}
                </span>
                <span style="font-size: 1.08rem; font-weight: 700; color: #f8fafc;">
                    🏢 {firma_adi}
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="background: rgba(148,163,184,0.14); color: #e2e8f0; padding: 3px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;">
                    {kategori_esc}
                </span>
                {durum_rozet}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; font-size: 0.86rem; color: #cbd5e1;">
            <div>👤 <b>Yetkili:</b> {yetkili}</div>
            <div>📞 <b>Telefon:</b> {telefon}</div>
            <div>🧾 <b>Vergi / TC No:</b> {vergi_no}</div>
            <div>📍 <b>Adres:</b> {adres}</div>
        </div>
        {not_satiri}
    </div>
    """


def tedarikci_rehberi_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    tedarikcileri_kaydet,
    simdi_tr_str,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    yonetici_modu,
):
    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Tedarikçi ve Firma Rehberi sayfası bu kullanıcı profili için maskelenmiştir (gizlenmiştir).")
        return

    if "tedarikciler" not in st.session_state or not isinstance(st.session_state.tedarikciler, list):
        st.session_state.tedarikciler = []

    tedarikciler = st.session_state.tedarikciler

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(16,185,129,0.16) 0%, rgba(14,165,233,0.10) 100%);
                border: 1px solid rgba(16,185,129,0.28);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.45rem; font-weight: 800; color: #f8fafc;">
                    🏢 Tedarikçi ve Firma Rehberi
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Onaylı tedarikçi ağı, yetkili iletişim bilgileri, kategori dağılımı ve ürün bazlı alım geçmişi
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    toplam_sayi = len(tedarikciler)
    aktif_sayi = sum(1 for t in tedarikciler if bool(t.get("aktif", True)))
    pasif_sayi = toplam_sayi - aktif_sayi
    kategori_sayi = len({t.get("kategori", "🏪 Genel Gıda") for t in tedarikciler if t.get("kategori")})

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("🏢", "Toplam Firma", toplam_sayi, "Rehbere kayıtlı tüm tedarikçiler", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("✅", "Aktif Tedarikçi", aktif_sayi, "Mal alımında seçilebilir firmalar", "#10b981"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("⏸️", "Pasif / Arşiv", pasif_sayi, "Geçici olarak durdurulan firmalar", "#f43f5e"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("🗂️", "Tedarik Kategorisi", kategori_sayi, "Aktif çalışılan ürün grupları", "#f59e0b"),
            unsafe_allow_html=True,
        )

    if tedarikciler:
        export_satirlari = [
            {
                "Kod": t.get("id", "-"),
                "Firma Adı": t.get("firma_adi", "-"),
                "Kategori": t.get("kategori", "-"),
                "Yetkili Kişi": t.get("yetkili_kisi") or "-",
                "Telefon": t.get("telefon") or "-",
                "Vergi / TC No": t.get("vergi_no") or "-",
                "Durum": "Aktif" if bool(t.get("aktif", True)) else "Pasif",
                "Adres": t.get("adres") or "-",
                "Notlar": t.get("notlar") or "-",
            }
            for t in tedarikciler
        ]
        excel_bytes = tablo_to_excel_bytes(export_satirlari, "Aziziye Aşevi - Tedarikçi ve Firma Rehberi")
        pdf_bytes = tablo_to_html_pdf_bytes("Aziziye Aşevi - Tedarikçi ve Firma Rehberi", export_satirlari)
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "tedarikci_rehberi", "tedarikciler_sayfasi")

    st.markdown("---")

    sekme_rehber, sekme_ekle, sekme_duzenle, sekme_analiz = st.tabs(
        [
            "📋 Firma Rehberi & Kartlar",
            "➕ Yeni Tedarikçi Ekle",
            "✏️ Düzenle / Durum Yönetimi",
            "📊 Tedarikçi Alım & Fiyat Analizi",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: FİRMA REHBERİ & KART GÖRÜNÜMÜ
    # ---------------------------------------------------------
    with sekme_rehber:
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.4, 1.1, 1.2])
        with f_col1:
            arama_metni = st.text_input(
                "🔍 Hızlı Arama",
                placeholder="Firma adı, yetkili, telefon veya vergi no ara...",
                key="ted_arama_input",
            )
        with f_col2:
            secilen_kat_filtre = st.selectbox(
                "🗂️ Kategori Filtresi",
                ["Tümü"] + TEDARIKCI_KATEGORILERI,
                key="ted_kat_filtre",
            )
        with f_col3:
            durum_filtre = st.selectbox(
                "🚦 Durum",
                ["Tümü", "✅ Aktif", "⏸️ Pasif"],
                key="ted_durum_filtre",
            )
        with f_col4:
            gorunum_tipi = st.radio(
                "👁️ Görünüm",
                ["Kartlar", "Tablo"],
                horizontal=True,
                key="ted_gorunum_tipi",
            )

        filtrelenmis = []
        aranan_kucuk = arama_metni.strip().replace("İ", "i").replace("I", "ı").lower()
        for t in tedarikciler:
            if secilen_kat_filtre != "Tümü" and t.get("kategori") != secilen_kat_filtre:
                continue
            aktif_mi = bool(t.get("aktif", True))
            if durum_filtre == "✅ Aktif" and not aktif_mi:
                continue
            if durum_filtre == "⏸️ Pasif" and aktif_mi:
                continue
            if aranan_kucuk:
                birlesik = " ".join(
                    str(t.get(alan, ""))
                    for alan in ("id", "firma_adi", "yetkili_kisi", "telefon", "vergi_no", "adres", "notlar")
                ).replace("İ", "i").replace("I", "ı").lower()
                if aranan_kucuk not in birlesik:
                    continue
            filtrelenmis.append(t)

        if not filtrelenmis:
            st.info("📭 Kriterlere uygun kayıtlı tedarikçi bulunmuyor. 'Yeni Tedarikçi Ekle' sekmesinden firma ekleyebilirsiniz.")
        else:
            st.caption(f"Gösterilen kayıt sayısı: **{len(filtrelenmis)}** / {toplam_sayi}")
            if gorunum_tipi == "Kartlar":
                for kayit in filtrelenmis:
                    st.markdown(_firma_karti_html(kayit), unsafe_allow_html=True)
            else:
                tablo_verisi = [
                    {
                        "Kod": t.get("id", "-"),
                        "Firma Adı": t.get("firma_adi", "-"),
                        "Kategori": t.get("kategori", "-"),
                        "Yetkili Kişi": t.get("yetkili_kisi") or "-",
                        "Telefon": t.get("telefon") or "-",
                        "Vergi No": t.get("vergi_no") or "-",
                        "Durum": "✅ Aktif" if bool(t.get("aktif", True)) else "⏸️ Pasif",
                        "Adres": t.get("adres") or "-",
                    }
                    for t in filtrelenmis
                ]
                ozel_html_tablo_goster(tablo_verisi)

    # ---------------------------------------------------------
    # SEKME 2: YENİ TEDARİKÇİ EKLE
    # ---------------------------------------------------------
    with sekme_ekle:
        if misafir_modu or salt_okunur_modu:
            st.warning("🔒 Misafir veya salt okunur modda yeni tedarikçi kaydı oluşturulamaz.")
        else:
            sonraki_id = yeni_tedarikci_id_uret(tedarikciler)
            st.info(f"🆔 Otomatik Atanacak Firma Kodu: **{sonraki_id}**")

            with st.form("yeni_tedarikci_formu", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    yeni_firma_adi = st.text_input("🏢 Firma Ünvanı / Adı *", placeholder="Örn: Erzurum Et ve Süt Kurumu")
                    yeni_yetkili = st.text_input("👤 Yetkili Kişi", placeholder="Örn: Ahmet Yılmaz")
                    yeni_telefon = st.text_input("📞 Telefon Numarası", placeholder="Örn: 0532 000 00 00")
                with c2:
                    yeni_kategori = st.selectbox("🗂️ Tedarik Kategorisi", TEDARIKCI_KATEGORILERI)
                    yeni_vergi_no = st.text_input("🧾 Vergi No / T.C. Kimlik No", placeholder="10 veya 11 haneli numara")
                    yeni_aktif = st.checkbox("✅ Aktif tedarikçi olarak işaretle", value=True)

                yeni_adres = st.text_input("📍 Firma Adresi", placeholder="İlçe / Mahalle / Cadde bilgisi")
                yeni_notlar = st.text_area("📝 Özel Notlar (Teslimat günü, IBAN, ödeme koşulu vb.)", height=80)

                kaydet_btn = st.form_submit_button("💾 Tedarikçiyi Rehbere Kaydet", type="primary", use_container_width=True)

                if kaydet_btn:
                    gecerli, hata = tedarikci_dogrula(
                        yeni_firma_adi,
                        telefon=yeni_telefon,
                        vergi_no=yeni_vergi_no,
                        mevcut_listesi=tedarikciler,
                    )
                    if not gecerli:
                        st.error(f"⚠️ {hata}")
                    else:
                        zaman_str = simdi_tr_str("%Y-%m-%d %H:%M")
                        yeni_kayit = {
                            "id": yeni_tedarikci_id_uret(tedarikciler),
                            "firma_adi": yeni_firma_adi.strip(),
                            "yetkili_kisi": yeni_yetkili.strip(),
                            "telefon": yeni_telefon.strip(),
                            "vergi_no": yeni_vergi_no.strip(),
                            "kategori": yeni_kategori,
                            "adres": yeni_adres.strip(),
                            "aktif": bool(yeni_aktif),
                            "notlar": yeni_notlar.strip(),
                            "olusturma_tarihi": zaman_str,
                            "guncelleme_tarihi": zaman_str,
                        }
                        otomatik_yedek_al(f"Yeni tedarikçi eklendi: {yeni_kayit['firma_adi']}")
                        st.session_state.tedarikciler.append(yeni_kayit)
                        tedarikcileri_kaydet(st.session_state.tedarikciler)
                        st.success(f"🎉 **{yeni_kayit['firma_adi']}** ({yeni_kayit['id']}) başarıyla rehbere eklendi!")
                        time.sleep(0.8)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 3: DÜZENLE / DURUM YÖNETİMİ
    # ---------------------------------------------------------
    with sekme_duzenle:
        if misafir_modu or salt_okunur_modu:
            st.warning("🔒 Misafir veya salt okunur modda düzenleme yapılamaz.")
        elif not tedarikciler:
            st.info("📭 Düzenlenecek kayıtlı tedarikçi bulunmuyor.")
        else:
            secenek_haritasi = {
                f"{t.get('id')} - {t.get('firma_adi')} ({'Aktif' if t.get('aktif', True) else 'Pasif'})": t
                for t in tedarikciler
            }
            secilen_etiket = st.selectbox(
                "✏️ Düzenlenecek Firmayı Seçin",
                list(secenek_haritasi.keys()),
                key="ted_duzenle_secim",
            )
            secilen_kayit = secenek_haritasi[secilen_etiket]
            mevcut_kat = secilen_kayit.get("kategori", "🏪 Genel Gıda")
            kat_index = TEDARIKCI_KATEGORILERI.index(mevcut_kat) if mevcut_kat in TEDARIKCI_KATEGORILERI else 0

            with st.form("tedarikci_guncelle_formu"):
                g1, g2 = st.columns(2)
                with g1:
                    duz_ad = st.text_input("🏢 Firma Ünvanı / Adı *", value=secilen_kayit.get("firma_adi") or "")
                    duz_yetkili = st.text_input("👤 Yetkili Kişi", value=secilen_kayit.get("yetkili_kisi") or "")
                    duz_telefon = st.text_input("📞 Telefon Numarası", value=secilen_kayit.get("telefon") or "")
                with g2:
                    duz_kategori = st.selectbox("🗂️ Tedarik Kategorisi", TEDARIKCI_KATEGORILERI, index=kat_index)
                    duz_vergi_no = st.text_input("🧾 Vergi No / T.C. Kimlik No", value=secilen_kayit.get("vergi_no") or "")
                    duz_aktif = st.checkbox("✅ Firma Aktif", value=bool(secilen_kayit.get("aktif", True)))

                duz_adres = st.text_input("📍 Firma Adresi", value=secilen_kayit.get("adres") or "")
                duz_notlar = st.text_area("📝 Özel Notlar", value=secilen_kayit.get("notlar") or "", height=80)

                b_guncelle, b_sil = st.columns([3, 1])
                with b_guncelle:
                    guncelle_onay = st.form_submit_button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True)
                with b_sil:
                    sil_onay = st.form_submit_button("🗑️ Firmayı Sil", use_container_width=True)

                if guncelle_onay:
                    gecerli, hata = tedarikci_dogrula(
                        duz_ad,
                        telefon=duz_telefon,
                        vergi_no=duz_vergi_no,
                        mevcut_listesi=tedarikciler,
                        haric_id=secilen_kayit.get("id"),
                    )
                    if not gecerli:
                        st.error(f"⚠️ {hata}")
                    else:
                        otomatik_yedek_al(f"Tedarikçi güncellendi: {duz_ad.strip()}")
                        secilen_kayit["firma_adi"] = duz_ad.strip()
                        secilen_kayit["yetkili_kisi"] = duz_yetkili.strip()
                        secilen_kayit["telefon"] = duz_telefon.strip()
                        secilen_kayit["vergi_no"] = duz_vergi_no.strip()
                        secilen_kayit["kategori"] = duz_kategori
                        secilen_kayit["adres"] = duz_adres.strip()
                        secilen_kayit["aktif"] = bool(duz_aktif)
                        secilen_kayit["notlar"] = duz_notlar.strip()
                        secilen_kayit["guncelleme_tarihi"] = simdi_tr_str("%Y-%m-%d %H:%M")

                        tedarikcileri_kaydet(st.session_state.tedarikciler)
                        st.success(f"✅ **{secilen_kayit['firma_adi']}** bilgileri güncellendi!")
                        time.sleep(0.8)
                        st.rerun()

                if sil_onay:
                    if not yonetici_modu:
                        st.error("🔒 Tedarikçi silme işlemi yalnızca yönetici (admin) yetkisiyle yapılabilir.")
                    else:
                        silinen_ad = secilen_kayit.get("firma_adi", "-")
                        otomatik_yedek_al(f"Tedarikçi silindi: {silinen_ad}")
                        st.session_state.tedarikciler.remove(secilen_kayit)
                        tedarikcileri_kaydet(st.session_state.tedarikciler)
                        st.warning(f"🗑️ **{silinen_ad}** rehberden silindi.")
                        time.sleep(0.8)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 4: TEDARİKÇİ ALIM & FİYAT ANALİZİ
    # ---------------------------------------------------------
    with sekme_analiz:
        if not tedarikciler:
            st.info("📭 Analiz için önce tedarikçi kaydı oluşturun.")
        else:
            firma_adlari = [t.get("firma_adi", "") for t in tedarikciler if t.get("firma_adi")]
            secilen_analiz_firma = st.selectbox(
                "📊 Analiz Edilecek Tedarikçi Firmayı Seçin",
                firma_adlari,
                key="ted_analiz_firma_sec",
            )
            girisler = st.session_state.get("girisler", [])
            istatistik = tedarikci_alim_istatistikleri(secilen_analiz_firma, girisler)

            a1, a2, a3 = st.columns(3)
            with a1:
                st.metric("🧾 Toplam Fatura Sayısı", istatistik["fatura_sayisi"])
            with a2:
                st.metric("💰 Toplam Alım Tutarı", f"{istatistik['toplam_tutar']:,.2f} ₺")
            with a3:
                st.metric("📦 Tedarik Edilen Ürün Çeşidi", len(istatistik["urun_ozeti"]))

            if not istatistik["urun_ozeti"]:
                st.info(
                    "ℹ️ Bu firmaya ait eşleşen mal alım kaydı henüz bulunmuyor. "
                    "Mal Alımı ekranında firma seçimi bağlandığında yapılan alımlar burada otomatik listelenecektir."
                )
            else:
                analiz_tablo = [
                    {
                        "Ürün Adı": u["urun"],
                        "Alım Sayısı": u["alim_sayisi"],
                        "Toplam Miktar": f"{u['toplam_miktar']:,.2f} {u['birim']}",
                        "Son Birim Fiyat": f"{u['son_birim_fiyat']:,.2f} ₺",
                        "Toplam Tutar": f"{u['toplam_tutar']:,.2f} ₺",
                        "Son Alım Tarihi": u["son_tarih"] or "-",
                    }
                    for u in istatistik["urun_ozeti"]
                ]
                ozel_html_tablo_goster(analiz_tablo)
