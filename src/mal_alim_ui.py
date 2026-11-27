import datetime
import difflib
import time
from src.tedarikciler_sql import (
    TEDARIKCI_KATEGORILERI,
    tedarikci_dogrula,
    yeni_tedarikci_id_uret,
)
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def mal_alimi_sayfasi(
    st,
    salt_okunur_modu,
    otomatik_yedek_al,
    verileri_kaydet,
    yeni_id_uret,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    tedarikcileri_kaydet=None,
    simdi_tr_str=None,
):
    if "tedarikciler" not in st.session_state or not isinstance(st.session_state.tedarikciler, list):
        st.session_state.tedarikciler = []

    if salt_okunur_modu:
        st.warning(
            "⚠️ Bu sayfaya yalnızca gözlem amaçlı erişebilirsiniz. Salt okunur (Yönetim/Misafir) modda işlem yapamazsınız."
        )
    else:
        sayfa_ust_banner_goster(
            st,
            "🧾",
            "Yeni Fatura ve Mal Alımı Girişi",
            "Her yeni mal alımı ayrı kayıt olarak depoya işlenir; stok miktarı artar, tedarikçi ve fiyat tarihçesi korunur",
            tema="mavi",
        )

        girisler_liste = st.session_state.get("girisler", []) or []
        toplam_kalem_sayisi = len(girisler_liste)
        toplam_alim_tutari = 0.0
        for _g in girisler_liste:
            try:
                if _g.get("birim_fiyat") is not None:
                    toplam_alim_tutari += float(_g.get("fiyat") or 0)
                else:
                    toplam_alim_tutari += float(_g.get("fiyat") or 0) * float(_g.get("miktar") or 0)
            except (TypeError, ValueError):
                pass
        cesit_sayisi = len({str(_g.get("urun", "")).strip().upper() for _g in girisler_liste if _g.get("urun")})
        aktif_ted_sayisi = sum(
            1 for _t in st.session_state.get("tedarikciler", [])
            if isinstance(_t, dict) and bool(_t.get("aktif", True))
        )

        kpi_satiri_goster(
            st,
            [
                ("🧾", "Toplam Alım Kalemi", toplam_kalem_sayisi, "Sisteme işlenen fatura satırları", "#38bdf8"),
                ("💰", "Toplam Alım Tutarı", f"{toplam_alim_tutari:,.2f} ₺", "Kümülatif mal alım bedeli", "#10b981"),
                ("📦", "Ürün Çeşidi", cesit_sayisi, "Farklı stok kalemi sayısı", "#f59e0b"),
                ("🏢", "Aktif Tedarikçi", aktif_ted_sayisi, "Rehberde seçilebilir firma", "#a855f7"),
            ],
        )

        # Son Eklenen İşlemi Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_eklenen_fatura_id"):
            son_id = st.session_state["son_eklenen_fatura_id"]
            son_fatura = next((g for g in st.session_state.girisler if g.get("id") == son_id), None)
            if son_fatura:
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    ted_bilgi = f" | Satıcı: {son_fatura.get('tedarikci')}" if son_fatura.get("tedarikci") else ""
                    st.info(
                        f"💡 **Son Eklenen Kayıt:** {son_fatura.get('urun')} "
                        f"({son_fatura.get('miktar')} {son_fatura.get('birim')} - Fatura No: {son_fatura.get('fatura_no')}{ted_bilgi})"
                    )
                with c_undo2:
                    if st.button("↩️ Son Mal Alımını Geri Al", type="secondary", key="btn_undo_fatura_son"):
                        otomatik_yedek_al("Fatura ekleme geri alma: " + str(son_id))
                        st.session_state.girisler = [g for g in st.session_state.girisler if g.get("id") != son_id]
                        verileri_kaydet(st.session_state.girisler)
                        st.session_state.pop("son_eklenen_fatura_id", None)
                        st.success(f"🎉 {son_id} numaralı mal alım kaydı başarıyla geri alındı ve silindi!")
                        time.sleep(1)
                        st.rerun()

        aktif_tedarikciler = [
            t for t in st.session_state.tedarikciler
            if isinstance(t, dict) and bool(t.get("aktif", True)) and t.get("firma_adi")
        ]

        c_toggle1, c_toggle2 = st.columns(2)
        with c_toggle1:
            yeni_tedarikci_secimi = st.checkbox(
                "🏢 Rehberde Olmayan Yeni Satıcı / Tedarikçi Ekle",
                value=(len(aktif_tedarikciler) == 0),
                key="mal_alim_yeni_tedarikci_chk",
            )
        with c_toggle2:
            mevcut_urun_listesi = sorted(
                list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
            )
            yeni_urun_secimi = st.checkbox(
                "➕ Listede Olmayan Yepyeni Bir Ürün Ekle",
                value=(len(mevcut_urun_listesi) == 0),
                key="mal_alim_yeni_urun_chk",
            )

        with st.form("fatura_formu"):
            c_t1, c_t2, c_t3 = st.columns(3)
            with c_t1:
                fatura_tarihi_secim = st.date_input("📅 Fatura / Alım Tarihi", value=datetime.date.today())
            with c_t2:
                fatura_saati_secim = st.time_input("⏰ Alım Saati", value=datetime.datetime.now().time())
            with c_t3:
                fatura_no_input = st.text_input(
                    "🧾 Fatura No / Belge No (Örn: FAT-2026-105)"
                ).strip().upper()

            tarih_giris = f"{fatura_tarihi_secim.strftime('%Y-%m-%d')} {fatura_saati_secim.strftime('%H:%M')}"

            # --- SATICI / TEDARİKÇİ SEÇİMİ VEYA HIZLI EKLEME ---
            st.markdown("##### 🏢 Tedarikçi / Satıcı Firma Bilgisi")
            secilen_tedarikci_obj = None
            yeni_ted_firma_adi = ""
            yeni_ted_kategori = "🏪 Genel Gıda"
            yeni_ted_yetkili = ""
            yeni_ted_telefon = ""
            yeni_ted_vergi_no = ""

            if yeni_tedarikci_secimi:
                nt1, nt2 = st.columns(2)
                with nt1:
                    yeni_ted_firma_adi = st.text_input(
                        "🏢 Yeni Satıcı / Firma Ünvanı (İsteğe Bağlı)",
                        placeholder="Örn: Palandöken Gıda Paz. Ltd. Şti.",
                    ).strip()
                    yeni_ted_yetkili = st.text_input("👤 Yetkili Kişi", placeholder="Örn: Mehmet Demir").strip()
                with nt2:
                    yeni_ted_kategori = st.selectbox("🗂️ Tedarik Kategorisi", TEDARIKCI_KATEGORILERI)
                    nt_sub1, nt_sub2 = st.columns(2)
                    with nt_sub1:
                        yeni_ted_telefon = st.text_input("📞 Telefon", placeholder="0532 000 00 00").strip()
                    with nt_sub2:
                        yeni_ted_vergi_no = st.text_input("🧾 Vergi / TC No", placeholder="10 veya 11 hane").strip()
                st.caption("ℹ️ Firma ünvanı girerseniz hem bu faturaya işlenir hem de Tedarikçi Rehberi'ne otomatik kaydedilir.")
            else:
                ted_secenek_map = {
                    f"{t.get('id', '-')} - {t.get('firma_adi')} ({t.get('kategori', '🏪 Genel Gıda')})": t
                    for t in aktif_tedarikciler
                }
                secilen_ted_etiket = st.selectbox(
                    "🏢 Tedarikçi Firma Seçin",
                    list(ted_secenek_map.keys()),
                    index=None,
                    placeholder="Rehberden satıcı seçin (veya yukarıdan yeni satıcı ekleyin)...",
                    key="fatura_tedarikci_selectbox",
                )
                if secilen_ted_etiket:
                    secilen_tedarikci_obj = ted_secenek_map[secilen_ted_etiket]

            st.markdown("##### 📦 Ürün ve Stok Bilgileri")
            if yeni_urun_secimi or not mevcut_urun_listesi:
                urun = st.text_input(
                    "Yeni Ürün Adı (Örn: KIRMIZI MERCİMEK - Büyük Harfle)"
                ).strip().upper()
            else:
                urun = st.selectbox(
                    "Mevcut Ürünlerden Seçin",
                    mevcut_urun_listesi,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="fatura_urun_selectbox",
                )

            kategori = st.selectbox(
                "Kategori",
                [
                    "SEBZE",
                    "MEYVE",
                    "KURU GIDA",
                    "BAHARAT",
                    "SÜT/SÜT ÜRÜNLERİ",
                    "KASAP / ŞARKÜTERİ",
                    "YAĞ",
                ],
            )
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"])

            skt_tarihi = st.date_input("📅 Son Tüketim Tarihi (SKT / STT) - Zorunlu", value=None)

            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)

            paket_miktari_input = st.number_input(
                "Paket Başına Miktar (Kg/Lt) - Dökme ise 0",
                min_value=0.0,
                value=0.0,
                step=1.0,
                help="Eğer ürün paketli geliyorsa (örn: 2.5 kg un), buraya paket ağırlığını yazın. Dökme ürünler için 0 bırakın.",
            )

            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle", type="primary", use_container_width=True)
            if submitted:
                tedarikci_dogrulama_hatasi = ""
                if yeni_tedarikci_secimi and yeni_ted_firma_adi:
                    gecerli_ted, ted_hata = tedarikci_dogrula(
                        yeni_ted_firma_adi,
                        telefon=yeni_ted_telefon,
                        vergi_no=yeni_ted_vergi_no,
                        mevcut_listesi=st.session_state.tedarikciler,
                    )
                    if not gecerli_ted:
                        tedarikci_dogrulama_hatasi = ted_hata

                if not urun:
                    st.error("⚠️ Lütfen listeden bir ürün seçin veya yeni bir ürün adı girin!")
                elif skt_tarihi is None:
                    st.error("⚠️ Lütfen ürünün Son Tüketim Tarihini (SKT/STT) seçin! Bu alan zorunludur.")
                elif tedarikci_dogrulama_hatasi:
                    st.error(f"⚠️ Tedarikçi Bilgisi Hatası: {tedarikci_dogrulama_hatasi}")
                else:
                    urun_temiz = urun.strip().upper()

                    if yeni_urun_secimi and mevcut_urun_listesi:
                        benzerler = difflib.get_close_matches(urun_temiz, mevcut_urun_listesi, n=1, cutoff=0.7)
                        if benzerler:
                            st.warning(f"⚠️ Dikkat! Yazdığınız ürün mevcut '{benzerler[0]}' adına çok benziyor.")

                    tedarikci_adi_kayit = ""
                    tedarikci_id_kayit = ""
                    yeni_firma_eklendi_mi = False

                    if yeni_tedarikci_secimi and yeni_ted_firma_adi:
                        zaman_str = (
                            simdi_tr_str("%Y-%m-%d %H:%M")
                            if callable(simdi_tr_str)
                            else datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        )
                        yeni_ted_id = yeni_tedarikci_id_uret(st.session_state.tedarikciler)
                        yeni_ted_obj = {
                            "id": yeni_ted_id,
                            "firma_adi": yeni_ted_firma_adi,
                            "yetkili_kisi": yeni_ted_yetkili,
                            "telefon": yeni_ted_telefon,
                            "vergi_no": yeni_ted_vergi_no,
                            "kategori": yeni_ted_kategori,
                            "adres": "",
                            "aktif": True,
                            "notlar": "Mal alımı ekranından eklendi.",
                            "olusturma_tarihi": zaman_str,
                            "guncelleme_tarihi": zaman_str,
                        }
                        st.session_state.tedarikciler.append(yeni_ted_obj)
                        if callable(tedarikcileri_kaydet):
                            tedarikcileri_kaydet(st.session_state.tedarikciler)
                        tedarikci_adi_kayit = yeni_ted_firma_adi
                        tedarikci_id_kayit = yeni_ted_id
                        yeni_firma_eklendi_mi = True
                    elif secilen_tedarikci_obj:
                        tedarikci_adi_kayit = str(secilen_tedarikci_obj.get("firma_adi", "")).strip()
                        tedarikci_id_kayit = str(secilen_tedarikci_obj.get("id", "")).strip()

                    islem_yapan_kisi = st.session_state.aktif_kullanici
                    fatura_no_degeri = fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
                    yeni_kayit_id = yeni_id_uret("FAT-", st.session_state.girisler)

                    yeni_kayit_obj = {
                        "id": yeni_kayit_id,
                        "tarih": tarih_giris,
                        "fatura_no": fatura_no_degeri,
                        "tedarikci": tedarikci_adi_kayit,
                        "tedarikci_id": tedarikci_id_kayit,
                        "urun": urun_temiz,
                        "kategori": kategori,
                        "birim": birim,
                        "miktar": miktar,
                        "kalan": miktar,
                        "birim_fiyat": fiyat,
                        "fiyat": fiyat * miktar,
                        "paket_miktari": paket_miktari_input,
                        "depo": depo,
                        "skt": str(skt_tarihi),
                        "islem_yapan": islem_yapan_kisi,
                    }

                    st.session_state.girisler.append(yeni_kayit_obj)
                    st.session_state["son_eklenen_fatura_id"] = yeni_kayit_id
                    verileri_kaydet(st.session_state.girisler)

                    ek_bilgi = (
                        f" Ayrıca <b>{tedarikci_adi_kayit}</b> ({tedarikci_id_kayit}) Tedarikçi Rehberi'ne kaydedildi."
                        if yeni_firma_eklendi_mi
                        else ""
                    )
                    st.markdown(
                        f"""
                        <div style="background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; padding: 14px 18px; border-radius: 14px; margin: 16px 0; font-weight: 600; font-size: 15px;">
                        🎉 Başarılı! Yeni mal alımı faturası ve ürün SKT/STT tarihi ile birlikte depoya eklendi.{ek_bilgi}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        # --- KAYIT GÜNCELLEME (DÜZENLEME) BÖLÜMÜ ---
        st.markdown("---")
        with st.expander("✏️ Hatalı / Eksik Kaydı Güncelle (Silmeden Düzelt)"):
            if not st.session_state.girisler:
                st.info("Sistemde güncellenecek kayıt bulunmuyor.")
            else:
                secenekler_guncelle = [
                    f"{g['id']} - {g['urun']} (Fatura: {g.get('fatura_no', '-')}, Kalan: {g.get('kalan', 0)} {g.get('birim', '')})"
                    for g in st.session_state.girisler
                ]
                secilen_kayit_guncelle = st.selectbox(
                    "Güncellenecek Kaydı Seçin",
                    secenekler_guncelle,
                    index=None,
                    placeholder="Düzeltilecek fatura/ürünü seçin...",
                    key="gncl_secim_box",
                )

                if secilen_kayit_guncelle:
                    secilen_id_g = secilen_kayit_guncelle.split(" - ")[0]
                    ilgili_g = next((g for g in st.session_state.girisler if g["id"] == secilen_id_g), None)

                    if ilgili_g:
                        st.markdown(f"**Kayıt ID:** `{ilgili_g['id']}` | **İlk Giriş Tarihi:** `{ilgili_g.get('tarih', '-')}`")

                        c_g1, c_g2, c_g3 = st.columns(3)
                        with c_g1:
                            g_fatura_no = st.text_input("Fatura No", value=ilgili_g.get("fatura_no", ""), key="g_fat_no")
                            g_miktar = st.number_input(
                                "Toplam Miktar",
                                min_value=0.1,
                                value=float(ilgili_g.get("miktar", 1.0)),
                                step=1.0,
                                key="g_miktar",
                            )
                            g_paket_miktari = st.number_input(
                                "Paket Başına Miktar (Kg/Lt - Dökme ise 0)",
                                min_value=0.0,
                                value=float(ilgili_g.get("paket_miktari", 0.0)),
                                step=1.0,
                                key="g_paket",
                            )
                        with c_g2:
                            mevcut_kategoriler = [
                                "SEBZE",
                                "MEYVE",
                                "KURU GIDA",
                                "BAHARAT",
                                "SÜT/SÜT ÜRÜNLERİ",
                                "KASAP / ŞARKÜTERİ",
                                "YAĞ",
                            ]
                            if ilgili_g.get("kategori") and ilgili_g.get("kategori") not in mevcut_kategoriler:
                                mevcut_kategoriler.append(ilgili_g.get("kategori"))
                            kat_idx = (
                                mevcut_kategoriler.index(ilgili_g.get("kategori"))
                                if ilgili_g.get("kategori") in mevcut_kategoriler
                                else 0
                            )
                            g_kategori = st.selectbox("Kategori", mevcut_kategoriler, index=kat_idx, key="g_kategori")

                            birimler = ["Kg", "Adet", "Lt"]
                            brm_idx = birimler.index(ilgili_g.get("birim")) if ilgili_g.get("birim") in birimler else 0
                            g_birim = st.selectbox("Birim", birimler, index=brm_idx, key="g_birim")
                        with c_g3:
                            mevcut_birim_fiyat = ilgili_g.get("birim_fiyat")
                            if mevcut_birim_fiyat in (None, ""):
                                mevcut_birim_fiyat = float(ilgili_g.get("fiyat", 0.01) or 0.01)
                            g_fiyat = st.number_input(
                                "Birim Fiyat (TL)",
                                min_value=0.01,
                                value=float(mevcut_birim_fiyat),
                                step=0.1,
                                key="g_fiyat",
                            )

                            depolar_list = st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"]
                            depo_idx = depolar_list.index(ilgili_g.get("depo")) if ilgili_g.get("depo") in depolar_list else 0
                            g_depo = st.selectbox("Depo Yeri", depolar_list, index=depo_idx, key="g_depo")

                        c_g4, c_g5 = st.columns(2)
                        with c_g4:
                            skt_mevcut = ilgili_g.get("skt")
                            try:
                                skt_dt_obj = datetime.datetime.strptime(skt_mevcut, "%Y-%m-%d").date() if skt_mevcut else None
                            except Exception:
                                skt_dt_obj = None
                            g_skt = st.date_input("📅 Son Tüketim Tarihi (SKT / STT)", value=skt_dt_obj, key="g_skt")
                        with c_g5:
                            rehber_firma_adlari = [
                                t.get("firma_adi", "").strip()
                                for t in st.session_state.tedarikciler
                                if isinstance(t, dict) and t.get("firma_adi")
                            ]
                            mevcut_ted_adi = str(ilgili_g.get("tedarikci") or "").strip()
                            ted_secenekleri = ["Belirtilmedi"] + rehber_firma_adlari
                            if mevcut_ted_adi and mevcut_ted_adi not in ted_secenekleri:
                                ted_secenekleri.append(mevcut_ted_adi)
                            ted_idx = ted_secenekleri.index(mevcut_ted_adi) if mevcut_ted_adi in ted_secenekleri else 0
                            g_tedarikci_sec = st.selectbox("🏢 Tedarikçi / Satıcı Firma", ted_secenekleri, index=ted_idx, key="g_tedarikci")

                        if st.button("Değişiklikleri Kaydet", type="primary", key="g_kaydet_btn"):
                            eski_miktar = float(ilgili_g.get("miktar", 1.0))
                            eski_kalan = float(ilgili_g.get("kalan", 1.0))
                            fark = g_miktar - eski_miktar
                            yeni_kalan = eski_kalan + fark

                            if yeni_kalan < 0:
                                st.error(f"⚠️ Hata: Yeni miktar, stokta kalan miktardan ({eski_kalan}) daha az olamaz!")
                            else:
                                ilgili_g["fatura_no"] = g_fatura_no if g_fatura_no else "BELİRTİLMEMİŞ"
                                ilgili_g["miktar"] = g_miktar
                                ilgili_g["kalan"] = yeni_kalan
                                ilgili_g["birim_fiyat"] = g_fiyat
                                ilgili_g["fiyat"] = g_miktar * g_fiyat
                                ilgili_g["kategori"] = g_kategori
                                ilgili_g["birim"] = g_birim
                                ilgili_g["depo"] = g_depo
                                ilgili_g["skt"] = str(g_skt) if g_skt else ""

                                if g_tedarikci_sec == "Belirtilmedi":
                                    ilgili_g["tedarikci"] = ""
                                    ilgili_g["tedarikci_id"] = ""
                                else:
                                    ilgili_g["tedarikci"] = g_tedarikci_sec
                                    eslesen_ted = next(
                                        (
                                            t for t in st.session_state.tedarikciler
                                            if isinstance(t, dict) and str(t.get("firma_adi", "")).strip() == g_tedarikci_sec
                                        ),
                                        None,
                                    )
                                    ilgili_g["tedarikci_id"] = eslesen_ted.get("id", "") if eslesen_ted else ""

                                if ilgili_g.get("paket_miktari") != g_paket_miktari:
                                    ilgili_g["paket_miktari"] = g_paket_miktari
                                    ilgili_g.pop("paket_durumlari", None)

                                verileri_kaydet(st.session_state.girisler)
                                st.success("🎉 Başarılı! Kayıt başarıyla güncellendi.")
                                time.sleep(1)
                                st.rerun()

        # --- FATURA ARŞİVİ TABLOSU ---
        st.markdown("---")
        bolum_basligi_goster(
            st,
            "📋",
            "Kayıtlı Fatura ve Mal Alım Arşivi",
            "Geçmiş alım faturaları, tedarikçi detayları ve paket bazlı stok girişleri",
            vurgu_renk="#38bdf8",
        )

    fatura_tablo_verisi = []
    if st.session_state.girisler:
        for g in reversed(st.session_state.girisler):
            try:
                paket_bilgi = "Dökme (Paketsiz)"
                try:
                    paket_miktari = float(g.get("paket_miktari") or 0)
                    if paket_miktari > 0:
                        durumlar = g.get("paket_durumlari", {})
                        paket_sayisi = int(float(g.get("miktar") or 0) // paket_miktari)
                        ozet_liste = []
                        for i in range(1, paket_sayisi + 1):
                            p_id = f"{g.get('id')}-P{i}"
                            if p_id in durumlar:
                                kalan = durumlar[p_id]
                                if kalan == paket_miktari:
                                    ozet_liste.append(f"P{i}: Tam")
                                elif kalan == 0:
                                    ozet_liste.append(f"P{i}: Bitti")
                                else:
                                    ozet_liste.append(f"P{i}: {kalan} {g.get('birim', '')} kaldı")
                            else:
                                ozet_liste.append(f"P{i}: Tam")
                        paket_bilgi = f"{paket_miktari} {g.get('birim', 'Kg')} | (" + ", ".join(ozet_liste) + ")"
                except Exception:
                    pass

                try:
                    if g.get("birim_fiyat") is not None:
                        birim_fiyat = float(g.get("birim_fiyat") or 0)
                        toplam_tutar = float(g.get("fiyat") or 0)
                    else:
                        birim_fiyat = float(g.get("fiyat") or 0)
                        miktar_degeri = float(g.get("miktar") or 0)
                        toplam_tutar = birim_fiyat * miktar_degeri
                except (ValueError, TypeError):
                    birim_fiyat = 0.0
                    toplam_tutar = 0.0

                fatura_tablo_verisi.append({
                    "Kayıt ID": g.get("id", "-"),
                    "Tarih / Saat": g.get("tarih", "-"),
                    "Fatura No": g.get("fatura_no", "-"),
                    "Tedarikçi / Firma": g.get("tedarikci") or "-",
                    "Ürün Adı": g.get("urun", "-"),
                    "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                    "Paket Yapısı": paket_bilgi,
                    "SKT / STT": g.get("skt", "-"),
                    "Depo": g.get("depo", "-"),
                    "Birim Fiyat": f"{birim_fiyat:,.2f} ₺",
                    "Toplam Tutar": f"{toplam_tutar:,.2f} ₺",
                    "İşlemi Yapan": g.get("islem_yapan", "admin"),
                })
            except Exception:
                pass

    if fatura_tablo_verisi:
        excel_fatura_data = tablo_to_excel_bytes(fatura_tablo_verisi, "Aziziye Aşevi - Fatura Arşivi")
        pdf_fatura_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Fatura Arşivi", fatura_tablo_verisi)

        col_b_fat, col_indir_fat = st.columns([2, 2])
        with col_indir_fat:
            ortak_indirme_alani(excel_fatura_data, pdf_fatura_data, "fatura_mal_alim_arsivi", "fatura_arsiv_sayfasi")

        ozel_html_tablo_goster(fatura_tablo_verisi)
    else:
        st.info("Sistemde kayıtlı fatura veya mal alımı bulunmuyor.")
