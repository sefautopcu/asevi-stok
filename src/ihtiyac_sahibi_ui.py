import time
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def ihtiyac_sahibi_listesi_tabini_goster(
    tab1,
    st,
    aktif_k_maskeleri,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    salt_okunur_modu,
    yonetim_modu,
    simdi_tr_str,
    yeni_id_uret,
    ihtiyac_sahiplerini_kaydet,
    yonetici_modu,
    silme_onay_kutusu,
    otomatik_yedek_al,
    ozel_html_tablo_goster,
):
    with tab1:
        tum_kisiler = st.session_state.get("ihtiyac_sahipleri", []) or []
        toplam_kisi = len(tum_kisiler)
        aktif_kisi = sum(1 for k in tum_kisiler if k.get("aktif", True))
        pasif_kisi = toplam_kisi - aktif_kisi
        birey_gizli = "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı" in aktif_k_maskeleri
        toplam_birey_aktif = sum(
            int(k.get("birey_sayisi", 1) or 1)
            for k in tum_kisiler
            if k.get("aktif", True)
        )

        sayfa_ust_banner_goster(
            st,
            "kullanici",
            "İhtiyaç Sahibi Listesi ve Hane Yönetimi",
            "Kayıtlı ihtiyaç sahibi haneleri, aktif/pasif durumlarını ve aile birey sayılarını yönetin",
            tema="mavi",
        )

        kpi_satiri_goster(
            st,
            [
                ("kullanici", "Toplam Kayıtlı Hane", toplam_kisi, "Sistemdeki tüm ihtiyaç sahibi kayıtları", "#38bdf8"),
                ("mutfak", "Aktif Hane / Kişi", aktif_kisi, "Düzenli yemek yardımı alan aktif kayıt", "#10b981"),
                ("uyari", "Pasif Hane / Kişi", pasif_kisi, "Yardımı durdurulan veya pasif kayıt", "#f43f5e"),
                (
                    "liste",
                    "Aktif Faydalanan Birey",
                    "🔒 Gizli" if birey_gizli else f"{toplam_birey_aktif:,}",
                    "Aktif hanelerdeki toplam kişi sayısı",
                    "#f59e0b",
                ),
            ],
        )

        col_b_kisi, col_indir_kisi = st.columns([2, 2])
        with col_b_kisi:
            bolum_basligi_goster(
                st,
                "kullanici",
                "İhtiyaç Sahibi İşlemleri ve Dışa Aktarım",
                "Listeyi Excel/PDF olarak indirin veya yeni hane kaydı oluşturun",
                vurgu_renk="#38bdf8",
            )

        if st.session_state.kisi_silme_mesaji:
            st.success(st.session_state.kisi_silme_mesaji)
            st.session_state.kisi_silme_mesaji = ""

        kisi_liste_gosterim = []
        for k in st.session_state.ihtiyac_sahipleri:
            tc_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "")
            ad_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adı Soyadı" in aktif_k_maskeleri else k.get("ad_soyad", "")
            tel_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Telefon" in aktif_k_maskeleri else k.get("telefon", "")
            adres_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adres" in aktif_k_maskeleri else k.get("adres", "")
            birey_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı" in aktif_k_maskeleri else k.get("birey_sayisi", "")
            durum_str = "🟢 Aktif" if k.get("aktif", True) else "🔴 Pasif"

            kisi_liste_gosterim.append({
                "Kayıt No": k["id"],
                "Durumu": durum_str,
                "T.C. Kimlik No / Hane No": tc_maskele,
                "Adı Soyadı": ad_maskele,
                "Telefon": tel_maskele,
                "Adres": adres_maskele,
                "Birey Sayısı": birey_maskele,
                "Eklenme Zamanı": k.get("eklenme_tarihi", "-"),
                "İşlemi Yapan": k.get("islem_yapan", "admin"),
            })

        excel_kisi_data = tablo_to_excel_bytes(
            kisi_liste_gosterim, "Aziziye Aşevi - İhtiyaç Sahipleri Listesi"
        )
        pdf_kisi_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - İhtiyaç Sahipleri Listesi", kisi_liste_gosterim
        )

        with col_indir_kisi:
            ortak_indirme_alani(
                excel_kisi_data,
                pdf_kisi_data,
                "ihtiyac_sahipleri_listesi",
                "ihtiyac_kisi_sayfasi",
            )

        if not salt_okunur_modu:
            with st.expander("🔄 Vatandaşın Aktif / Pasif Durumunu Değiştir"):
                with st.form("aktif_pasif_form"):
                    kisi_sec_list = [
                        f"{k['id']} - {k['ad_soyad']} (Mevcut: {'Aktif' if k.get('aktif', True) else 'Pasif'})"
                        for k in st.session_state.ihtiyac_sahipleri
                    ]
                    secilen_kisi_durum_str = st.selectbox(
                        "Vatandaş Seçin",
                        kisi_sec_list if kisi_sec_list else [],
                        index=None,
                        placeholder="Vatandaş Seçiniz...",
                        key="kisi_durum_selectbox",
                    )
                    yeni_durum_secim = st.radio("Yeni Durum", ["Aktif Yap", "Pasif Yap"], horizontal=True)
                    durum_degis_btn = st.form_submit_button("Durumu Güncelle", type="primary")

                    if durum_degis_btn:
                        if not secilen_kisi_durum_str:
                            st.error("⚠️ Lütfen durumu güncellenecek vatandaşı seçin!")
                        else:
                            h_id = secilen_kisi_durum_str.split(" - ")[0]
                            for k in st.session_state.ihtiyac_sahipleri:
                                if k["id"] == h_id:
                                    k["aktif"] = yeni_durum_secim == "Aktif Yap"
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.success("🎉 Başarılı! Vatandaşın aktif/pasif durumu güncellendi.")
                            st.rerun()

        if yonetim_modu:
            st.info("👀 Yönetim modundasınız. Bu ekranda yalnızca kayıtlı ihtiyaç sahiplerini gözlemleyebilirsiniz.")
        else:
            col_form_ekle, col_form_sil = st.columns(2)
            with col_form_ekle:
                with st.form("ihtiyac_sahibi_formu"):
                    st.markdown("**➕ Yeni İhtiyaç Sahibi / Hane Ekle**")
                    yeni_hane = st.text_input("Hane No").strip()
                    yeni_ad = (
                        st.text_input("Adı Soyadı / Hane Unvanı").strip().upper()
                    )
                    yeni_tel = st.text_input("Telefon Numarası")
                    yeni_adres = st.text_input("Açık Adres")
                    yeni_birey = st.number_input(
                        "Aile / Hane Birey Sayısı", min_value=1, value=1
                    )

                    kaydet_btn = st.form_submit_button("İhtiyaç Sahibini Kaydet")
                    if kaydet_btn and yeni_ad:
                        islem_tarihi_str = simdi_tr_str("%Y-%m-%d %H:%M")
                        islem_yapan_kisi = st.session_state.aktif_kullanici
                        st.session_state.ihtiyac_sahipleri.append({
                            "id": yeni_id_uret("IHT-", st.session_state.ihtiyac_sahipleri),
                            "hane": yeni_hane,
                            "ad_soyad": yeni_ad,
                            "telefon": yeni_tel,
                            "adres": yeni_adres,
                            "birey_sayisi": yeni_birey,
                            "aktif": True,
                            "eklenme_tarihi": islem_tarihi_str,
                            "islem_yapan": islem_yapan_kisi,
                        })
                        ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                        st.success(f"🎉 Başarılı! {yeni_ad} kaydedildi.")
                        st.balloons()
                        st.rerun()

            with col_form_sil:
                if not yonetici_modu:
                    st.info("🗑️ İhtiyaç sahibi silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("ihtiyac_sahibi_sil_formu"):
                        st.markdown("**🗑️ Kayıtlı İhtiyaç Sahibini Sil**")
                        if st.session_state.ihtiyac_sahipleri:
                            kisi_secenekleri_sil = [
                                f"{k['id']} - {k['ad_soyad']} (T.C./Hane: {k.get('tc_hane', '-')})"
                                for k in st.session_state.ihtiyac_sahipleri
                            ]
                            secilen_silinecek = st.selectbox(
                                "Silinecek Kişiyi / Haneyi Seçin",
                                kisi_secenekleri_sil,
                                index=None,
                                placeholder="Kişi Seçiniz...",
                                key="ihtiyac_sil_selectbox",
                            )
                            onay_sil_btn = silme_onay_kutusu("onay_ihtiyac_sil")
                            sil_btn = st.form_submit_button(
                                "Seçilen Kişiyi Sistemden Sil", type="primary"
                            )

                            if sil_btn:
                                if not secilen_silinecek:
                                    st.error("⚠️ Lütfen silinecek kişi/haneyi seçin!")
                                elif not onay_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                else:
                                    otomatik_yedek_al("İhtiyaç sahibi silme: " + str(secilen_silinecek))
                                    silinecek_id = secilen_silinecek.split(" - ")[0]
                                    silinen_kisi_obj = next(
                                        (
                                            k
                                            for k in st.session_state.ihtiyac_sahipleri
                                            if k["id"] == silinecek_id
                                        ),
                                        None,
                                    )
                                    if silinen_kisi_obj:
                                        # Geri al butonu için sakla
                                        st.session_state["son_silinen_ihtiyac_sahibi"] = silinen_kisi_obj.copy()

                                        silinen_isim = silinen_kisi_obj["ad_soyad"]
                                        st.session_state.ihtiyac_sahipleri = [
                                            k
                                            for k in st.session_state.ihtiyac_sahipleri
                                            if k["id"] != silinecek_id
                                        ]
                                        ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                                        st.session_state.kisi_silme_mesaji = (
                                            f"🎉 Başarılı! {silinen_isim} silindi."
                                        )
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            st.info("Silinecek kayıt bulunmuyor.")

        st.markdown("---")
        bolum_basligi_goster(
            st,
            "liste",
            "Kayıtlı İhtiyaç Sahipleri Tablosu",
            "Tüm hane kayıtları, iletişim bilgileri ve aktiflik durumları",
            vurgu_renk="#10b981",
        )
        if kisi_liste_gosterim:
            ozel_html_tablo_goster(kisi_liste_gosterim)
        else:
            st.info("Sistemde kayıtlı ihtiyaç sahibi bulunmuyor.")
