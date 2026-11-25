import calendar
import datetime
import time


def _personel_aktif_mi(personel):
    """Personel kaydının aktiflik durumunu döndürür (varsayılan: True)."""
    if not isinstance(personel, dict):
        return True
    if "aktif" in personel:
        return bool(personel.get("aktif"))
    durum = str(personel.get("durum", "Aktif")).strip().lower()
    return durum not in {"pasif", "pasif (izinli/ayrıldı)", "ayrıldı", "false", "0"}


def personel_ve_calisma_suresi_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    idleri_benzersiz_yap,
    otomatik_yedek_al,
    personelleri_kaydet,
    personel_izinlerini_kaydet,
    yeni_id_uret,
    simdi_tr_str,
    silme_onay_kutusu,
    net_calisma_raporu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    supabase_veri_kaydet,
):
    import calendar

    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    st.header("👥 Personel ve Çalışma Süresi Takibi")
    st.markdown(
        "Aşevi personelinin kayıtlarını tutun, aktif/pasif durumlarını yönetin, izin/rapor günlerini girin ve net çalışma günlerini takip edin."
    )

    if "personeller" not in st.session_state or st.session_state.personeller is None:
        st.session_state.personeller = []

    st.session_state.personeller = idleri_benzersiz_yap(
        st.session_state.personeller, "PER-"
    )

    if (
        "personel_izinleri" not in st.session_state
        or st.session_state.personel_izinleri is None
    ):
        st.session_state.personel_izinleri = []

    # Üst özet sayaçları (aktif / pasif / toplam)
    toplam_p = len(st.session_state.personeller)
    aktif_p = sum(1 for p in st.session_state.personeller if _personel_aktif_mi(p))
    pasif_p = toplam_p - aktif_p

    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Personel", toplam_p)
    m2.metric("Aktif Personel", aktif_p)
    m3.metric("Pasif Personel", pasif_p)

    # Son Personel / İzin İşlemini Geri Al Butonu ve Bildirimi
    if st.session_state.get("son_personel_islem"):
        son_p_islem = st.session_state["son_personel_islem"]
        tur = son_p_islem.get("tur")
        p_obj = son_p_islem.get("obje", {})

        c_undo1, c_undo2 = st.columns([3, 1])
        with c_undo1:
            if tur == "personel_ekle":
                st.info(
                    f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli eklendi."
                )
            elif tur == "personel_durum":
                yeni_durum_etiket = "Aktif" if _personel_aktif_mi(p_obj) else "Pasif"
                st.info(
                    f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personelinin durumu '{yeni_durum_etiket}' olarak güncellendi."
                )
            elif tur == "personel_sil":
                st.info(
                    f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli silindi."
                )
            elif tur == "izin_ekle":
                st.info(
                    f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' için {p_obj.get('gun_sayisi', 0)} günlük {p_obj.get('izin_turu', '-')} eklendi."
                )
            elif tur == "izin_sil":
                st.info(
                    f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' kişisine ait izin kaydı silindi."
                )

        with c_undo2:
            if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_personel_son"):
                otomatik_yedek_al("Personel işlemi geri alma: " + str(tur))

                if tur == "personel_ekle":
                    st.session_state.personeller = [
                        p
                        for p in st.session_state.personeller
                        if str(p.get("id")) != str(p_obj.get("id"))
                    ]
                elif tur == "personel_durum":
                    onceki_obj = son_p_islem.get("onceki_obje")
                    if isinstance(onceki_obj, dict):
                        st.session_state.personeller = [
                            onceki_obj if str(p.get("id")) == str(onceki_obj.get("id")) else p
                            for p in st.session_state.personeller
                        ]
                elif tur == "personel_sil":
                    if not any(
                        str(p.get("id")) == str(p_obj.get("id"))
                        for p in st.session_state.personeller
                    ):
                        st.session_state.personeller.append(p_obj)
                elif tur == "izin_ekle":
                    st.session_state.personel_izinleri = [
                        iz
                        for iz in st.session_state.personel_izinleri
                        if str(iz.get("id")) != str(p_obj.get("id"))
                    ]
                elif tur == "izin_sil":
                    if not any(
                        str(iz.get("id")) == str(p_obj.get("id"))
                        for iz in st.session_state.personel_izinleri
                    ):
                        st.session_state.personel_izinleri.append(p_obj)

                personelleri_kaydet(st.session_state.personeller)
                personel_izinlerini_kaydet(st.session_state.personel_izinleri)

                st.session_state.pop("son_personel_islem", None)
                st.success("🎉 Yapılan son işlem başarıyla geri alındı!")
                time.sleep(1)
                st.rerun()

    tab_p1, tab_p2, tab_p3 = st.tabs([
        "📋 Personel Listesi ve Ekle/Düzenle/Sil",
        "📅 İzin & Rapor Girişi ve Takibi",
        "📊 Net Çalışma Günü Raporu",
    ])

    # TAB 1: PERSONEL LİSTESİ VE EKLE / DÜZENLE / SİL
    with tab_p1:
        col_b_pers, col_indir_pers = st.columns([2, 2])
        with col_b_pers:
            st.subheader("📋 Personel Kayıtları ve Yönetimi")
            durum_filtre = st.selectbox(
                "Durum Filtresi",
                ["Tümü", "Aktif", "Pasif"],
                key="personel_durum_filtre",
            )

        personel_gosterim = []
        for p in st.session_state.personeller:
            aktif_mi = _personel_aktif_mi(p)
            if durum_filtre == "Aktif" and not aktif_mi:
                continue
            if durum_filtre == "Pasif" and aktif_mi:
                continue

            ad_soyad_val = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
            tc_p = (
                "🔒 Gizli"
                if "5. Sayfa: Personel - T.C. No" in aktif_k_maskeleri
                else (p.get("tc_no") or p.get("tc") or "-")
            )
            ad_p = (
                "🔒 Gizli"
                if "5. Sayfa: Personel - Adı Soyadı" in aktif_k_maskeleri
                else ad_soyad_val
            )
            tel_p = (
                "🔒 Gizli"
                if "5. Sayfa: Personel - Telefon" in aktif_k_maskeleri
                else (p.get("telefon") or "-")
            )
            gorev_p = p.get("gorev") or p.get("gorevi") or "-"
            tarih_p = (
                p.get("baslama_tarihi")
                or p.get("baslama")
                or p.get("ise_baslama_tarihi")
                or p.get("tarih")
                or "-"
            )
            durum_etiket = "🟢 Aktif" if aktif_mi else "🔴 Pasif"

            personel_gosterim.append({
                "Personel ID": p.get("id", "-"),
                "Durum": durum_etiket,
                "T.C. Kimlik No": tc_p,
                "Adı Soyadı": ad_p,
                "Görevi / Unvanı": gorev_p,
                "Telefon": tel_p,
                "İşe Başlama Tarihi": tarih_p,
            })

        excel_p_data = tablo_to_excel_bytes(
            personel_gosterim, "Aziziye Aşevi - Personel Listesi"
        )
        pdf_p_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Personel Listesi", personel_gosterim
        )
        with col_indir_pers:
            ortak_indirme_alani(
                excel_p_data,
                pdf_p_data,
                "personel_listesi_raporu",
                "personel_sayfasi",
            )

        if not salt_okunur_modu:
            col_p_ekle, col_p_durum_sil = st.columns(2)
            with col_p_ekle:
                with st.form("yeni_personel_form"):
                    st.markdown("**➕ Yeni Personel Ekle**")
                    p_tc = st.text_input("T.C. Kimlik No").strip()
                    p_ad = st.text_input("Adı Soyadı").strip().upper()
                    p_gorev = st.text_input(
                        "Görevi / Unvanı (Örn: Aşçıbaşı, Şoför)"
                    ).strip()
                    p_tel = st.text_input("Telefon Numarası")
                    p_tarih = st.date_input(
                        "İşe Başlama Tarihi", value=datetime.date.today()
                    )
                    p_aktif_yeni = st.checkbox("Personel Aktif", value=True)

                    p_ekle_btn = st.form_submit_button(
                        "Personeli Kaydet", type="primary"
                    )
                    if p_ekle_btn and p_ad:
                        yeni_p_id = yeni_id_uret("PER-", st.session_state.personeller)
                        yeni_p_obj = {
                            "id": yeni_p_id,
                            "tc_no": p_tc,
                            "tc": p_tc,
                            "ad_soyad": p_ad,
                            "gorev": p_gorev if p_gorev else "Personel",
                            "telefon": p_tel,
                            "baslama_tarihi": str(p_tarih),
                            "baslama": str(p_tarih),
                            "ise_baslama_tarihi": str(p_tarih),
                            "aktif": bool(p_aktif_yeni),
                            "durum": "Aktif" if p_aktif_yeni else "Pasif",
                            "eklenme_zamanı": simdi_tr_str("%Y-%m-%d %H:%M"),
                        }
                        st.session_state.personeller.append(yeni_p_obj)
                        personelleri_kaydet(st.session_state.personeller)

                        st.session_state["son_personel_islem"] = {
                            "tur": "personel_ekle",
                            "obje": yeni_p_obj,
                        }

                        st.success(f"🎉 Başarılı! {p_ad} personel olarak kaydedildi.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

            with col_p_durum_sil:
                # Aktif / Pasif Durum Güncelleme Formu
                with st.form("personel_durum_guncelle_form"):
                    st.markdown("**🔄 Aktif / Pasif Durum Güncelle**")
                    if st.session_state.personeller:
                        p_durum_secenekler = {
                            f"{p.get('id', '-')} - {p.get('ad_soyad') or p.get('ad') or '-'} ({'Aktif' if _personel_aktif_mi(p) else 'Pasif'})": p
                            for p in st.session_state.personeller
                        }
                        secilen_durum_etiket = st.selectbox(
                            "Durumu Değiştirilecek Personel",
                            list(p_durum_secenekler.keys()),
                            key="personel_durum_selectbox",
                        )
                        secilen_p_kayit = p_durum_secenekler[secilen_durum_etiket]
                        yeni_aktif_durum = st.selectbox(
                            "Yeni Durum",
                            ["Aktif", "Pasif"],
                            index=0 if _personel_aktif_mi(secilen_p_kayit) else 1,
                            key="personel_yeni_durum_select",
                        )
                        durum_kaydet_btn = st.form_submit_button(
                            "Durumu Güncelle", type="primary"
                        )
                        if durum_kaydet_btn:
                            onceki_kayit = dict(secilen_p_kayit)
                            hedef_aktif = yeni_aktif_durum == "Aktif"
                            for p_item in st.session_state.personeller:
                                if str(p_item.get("id")) == str(
                                    secilen_p_kayit.get("id")
                                ):
                                    p_item["aktif"] = hedef_aktif
                                    p_item["durum"] = (
                                        "Aktif" if hedef_aktif else "Pasif"
                                    )
                                    guncel_p_obj = dict(p_item)
                                    break
                            else:
                                guncel_p_obj = onceki_kayit

                            personelleri_kaydet(st.session_state.personeller)
                            st.session_state["son_personel_islem"] = {
                                "tur": "personel_durum",
                                "obje": guncel_p_obj,
                                "onceki_obje": onceki_kayit,
                            }
                            st.success(
                                f"✅ {guncel_p_obj.get('ad_soyad', '-')} durumu '{yeni_aktif_durum}' olarak güncellendi."
                            )
                            time.sleep(0.8)
                            st.rerun()
                    else:
                        st.info("Güncellenecek personel bulunmuyor.")

                # Silme Formu (Sadece Admin)
                if not yonetici_modu:
                    st.info("🗑️ Personel silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("personel_sil_form"):
                        st.markdown("**🗑️ Kayıtlı Personeli Sil**")
                        if st.session_state.personeller:
                            p_secenekler_sil = [
                                f"{p.get('id', '-')} - {p.get('ad_soyad') or p.get('ad') or p.get('isim') or '-'} ({p.get('gorev') or p.get('gorevi') or '-'})"
                                for p in st.session_state.personeller
                            ]
                            secilen_sil_p = st.selectbox(
                                "Silinecek Personeli Seçin",
                                p_secenekler_sil,
                                index=None,
                                placeholder="Personel Seçiniz...",
                                key="personel_sil_selectbox",
                            )
                            onay_p_sil_btn = silme_onay_kutusu("onay_personel_sil")
                            p_sil_btn = st.form_submit_button(
                                "Seçilen Personeli Sil", type="primary"
                            )

                            if p_sil_btn:
                                if not secilen_sil_p:
                                    st.error("⚠️ Lütfen silinecek personeli seçin!")
                                elif not onay_p_sil_btn:
                                    st.error(
                                        "⚠️ Silmek için onay kutusunu işaretleyin."
                                    )
                                else:
                                    otomatik_yedek_al(
                                        "Personel silme: " + str(secilen_sil_p)
                                    )
                                    sil_p_id = secilen_sil_p.split(" - ")[0]
                                    silinen_p_obj = next(
                                        (
                                            p
                                            for p in st.session_state.personeller
                                            if str(p.get("id", "")) == str(sil_p_id)
                                            or f"{p.get('id', '-')} - {p.get('ad_soyad') or p.get('ad') or '-'}"
                                            in secilen_sil_p
                                        ),
                                        None,
                                    )

                                    if silinen_p_obj:
                                        st.session_state.personeller = [
                                            p
                                            for p in st.session_state.personeller
                                            if p != silinen_p_obj
                                            and str(p.get("id", "")) != str(sil_p_id)
                                        ]

                                        personelleri_kaydet(
                                            st.session_state.personeller
                                        )

                                        st.session_state["son_personel_islem"] = {
                                            "tur": "personel_sil",
                                            "obje": silinen_p_obj,
                                        }

                                        st.success(
                                            "🎉 Başarılı! Personel kaydı silindi."
                                        )
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            st.info("Silinecek personel bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Personel Tablosu")
        if personel_gosterim:
            ozel_html_tablo_goster(personel_gosterim)
        else:
            st.info("Kayıtlı personel bulunmuyor.")

    # TAB 2: İZİN & RAPOR GİRİŞİ VE TAKİBİ
    with tab_p2:
        st.subheader("📅 Personel İzin ve Rapor Girişi")

        if not st.session_state.personeller:
            st.warning("İzin girmek için öncelikle personel eklemelisiniz.")
        else:
            if not salt_okunur_modu:
                col_iz_ekle, col_iz_sil = st.columns(2)
                with col_iz_ekle:
                    with st.form("yeni_izin_form"):
                        st.markdown("**➕ İzin / Rapor Kaydı Ekle**")
                        p_isimler = [
                            p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
                            for p in st.session_state.personeller
                        ]
                        secilen_p_ad = st.selectbox(
                            "Personel Seçin",
                            p_isimler,
                            index=None,
                            placeholder="Personel Seçiniz...",
                            key="izin_personel_select",
                        )
                        izin_turu = st.selectbox(
                            "İzin / Mazeret Türü",
                            [
                                "Yıllık İzin",
                                "Mazeret İzni",
                                "Hastalık / Rapor",
                                "Ücretsiz İzin",
                                "Resmi Görev / Diğer",
                            ],
                            index=None,
                            placeholder="İzin Türü Seçiniz...",
                            key="izin_turu_select",
                        )
                        c_iz_bas, c_iz_bit = st.columns(2)
                        with c_iz_bas:
                            iz_bas_tarih = st.date_input(
                                "İzin Başlangıç Tarihi",
                                value=datetime.date.today(),
                            )
                        with c_iz_bit:
                            iz_bit_tarih = st.date_input(
                                "İzin Bitiş Tarihi", value=datetime.date.today()
                            )

                        iz_aciklama = st.text_input(
                            "Açıklama / Not", "Yıllık İzin Kullanımı"
                        ).strip()
                        iz_ekle_btn = st.form_submit_button(
                            "İzni Kaydet", type="primary"
                        )

                        if iz_ekle_btn:
                            if not secilen_p_ad:
                                st.error("⚠️ Lütfen bir personel seçin!")
                            elif not izin_turu:
                                st.error("⚠️ Lütfen izin türünü seçin!")
                            elif iz_bit_tarih < iz_bas_tarih:
                                st.error(
                                    "⚠️ Bitiş tarihi başlangıç tarihinden önce olamaz!"
                                )
                            else:
                                gun_sayisi = (iz_bit_tarih - iz_bas_tarih).days + 1
                                yeni_iz_id = yeni_id_uret(
                                    "IZN-", st.session_state.personel_izinleri
                                )
                                yeni_iz_obj = {
                                    "id": yeni_iz_id,
                                    "personel_ad": secilen_p_ad,
                                    "izin_turu": izin_turu,
                                    "baslangic": str(iz_bas_tarih),
                                    "bitis": str(iz_bit_tarih),
                                    "gun_sayisi": gun_sayisi,
                                    "aciklama": iz_aciklama,
                                    "ekleme_tarihi": simdi_tr_str("%Y-%m-%d %H:%M"),
                                }
                                st.session_state.personel_izinleri.append(
                                    yeni_iz_obj
                                )

                                personel_izinlerini_kaydet(
                                    st.session_state.personel_izinleri
                                )

                                st.session_state["son_personel_islem"] = {
                                    "tur": "izin_ekle",
                                    "obje": yeni_iz_obj,
                                }

                                st.success(
                                    f"🎉 Başarılı! {secilen_p_ad} için {gun_sayisi} günlük {izin_turu} kaydedildi."
                                )
                                st.balloons()
                                time.sleep(1)
                                st.rerun()

                with col_iz_sil:
                    if not yonetici_modu:
                        st.info("🗑️ İzin silme yetkisi yalnızca Admin'e aittir.")
                    else:
                        with st.form("izin_sil_form"):
                            st.markdown("**🗑️ İzin Kaydı Sil**")
                            if st.session_state.personel_izinleri:
                                iz_secenekler = [
                                    f"{iz.get('id', '-')} - {iz.get('personel_ad', '-')} ({iz.get('izin_turu', '-')}: {iz.get('baslangic', '-')} / {iz.get('bitis', '-')})"
                                    for iz in st.session_state.personel_izinleri
                                ]
                                secilen_sil_iz = st.selectbox(
                                    "Silinecek İzin Kaydını Seçin",
                                    iz_secenekler,
                                    index=None,
                                    placeholder="İzin Kaydı Seçiniz...",
                                    key="izin_sil_select",
                                )
                                onay_iz_sil_btn = silme_onay_kutusu("onay_izin_sil")
                                iz_sil_btn = st.form_submit_button(
                                    "İzin Kaydını Sil", type="primary"
                                )

                                if iz_sil_btn:
                                    if not secilen_sil_iz:
                                        st.error(
                                            "⚠️ Lütfen silinecek izin kaydını seçin!"
                                        )
                                    elif not onay_iz_sil_btn:
                                        st.error(
                                            "⚠️ Silmek için onay kutusunu işaretleyin."
                                        )
                                    else:
                                        sil_iz_id = secilen_sil_iz.split(" - ")[0]
                                        silinen_iz_obj = next(
                                            (
                                                iz
                                                for iz in st.session_state.personel_izinleri
                                                if str(iz.get("id"))
                                                == str(sil_iz_id)
                                            ),
                                            None,
                                        )

                                        if silinen_iz_obj:
                                            st.session_state.personel_izinleri = [
                                                iz
                                                for iz in st.session_state.personel_izinleri
                                                if str(iz.get("id"))
                                                != str(sil_iz_id)
                                            ]

                                            personel_izinlerini_kaydet(
                                                st.session_state.personel_izinleri
                                            )

                                            st.session_state["son_personel_islem"] = {
                                                "tur": "izin_sil",
                                                "obje": silinen_iz_obj,
                                            }

                                            st.success(
                                                "🎉 Başarılı! İzin kaydı silindi."
                                            )
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()
                            else:
                                st.info("Silinecek izin kaydı bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı İzin ve Raporlar Tablosu")
        if st.session_state.personel_izinleri:
            iz_tablo = []
            for iz in reversed(st.session_state.personel_izinleri):
                iz_tablo.append({
                    "Kayıt ID": iz.get("id", "-"),
                    "Personel Adı": iz.get("personel_ad", "-"),
                    "İzin Türü": iz.get("izin_turu", "-"),
                    "Başlangıç": iz.get("baslangic", "-"),
                    "Bitiş": iz.get("bitis", "-"),
                    "Gün Sayısı": iz.get("gun_sayisi", 0),
                    "Açıklama": iz.get("aciklama", "-"),
                })
            ozel_html_tablo_goster(iz_tablo)
        else:
            st.info("Kayıtlı izin veya rapor bulunmuyor.")

    # TAB 3: NET ÇALIŞMA GÜNÜ RAPORU
    with tab_p3:
        st.subheader("📊 Personel Net Çalışma Günü Raporu")

        sorgu_ay = st.date_input(
            "Sorgulanacak Ay ve Yıl Seçin",
            value=datetime.date.today(),
            key="sorgu_ay_picker",
        )
        sorgu_yil_ay_str = sorgu_ay.strftime("%Y-%m")
        sadece_aktif_rapor = st.checkbox(
            "Raporda yalnızca aktif personeli göster",
            value=True,
            key="rapor_sadece_aktif_cb",
        )

        toplam_ay_gunu = calendar.monthrange(sorgu_ay.year, sorgu_ay.month)[1]
        ay_baslangic = datetime.date(sorgu_ay.year, sorgu_ay.month, 1)
        ay_bitis = datetime.date(sorgu_ay.year, sorgu_ay.month, toplam_ay_gunu)
        resmi_tatil_listesi = st.session_state.get("resmi_tatiller", [])
        tatil_tarih_seti = set()
        for t in resmi_tatil_listesi:
            t_str = str(t.get("tarih", ""))[:10] if isinstance(t, dict) else str(t)[:10]
            try:
                tatil_tarih_seti.add(datetime.datetime.strptime(t_str, "%Y-%m-%d").date())
            except ValueError:
                pass

        hafta_ici_is_gunu = sum(
            1
            for gun_no in range(1, toplam_ay_gunu + 1)
            if datetime.date(sorgu_ay.year, sorgu_ay.month, gun_no).weekday() < 5
            and datetime.date(sorgu_ay.year, sorgu_ay.month, gun_no) not in tatil_tarih_seti
        )

        net_calisma_listesi = []
        for p in st.session_state.personeller:
            aktif_mi = _personel_aktif_mi(p)
            if sadece_aktif_rapor and not aktif_mi:
                continue

            p_ad = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"

            p_izinleri = []
            for iz in st.session_state.personel_izinleri:
                if iz.get("personel_ad") == p_ad:
                    iz_kopya = dict(iz)
                    if "tur" not in iz_kopya and "izin_turu" in iz_kopya:
                        iz_kopya["tur"] = iz_kopya["izin_turu"]
                    p_izinleri.append(iz_kopya)

            if aktif_mi:
                hesap_baslangic = ay_baslangic
                baslama_str = str(
                    p.get("baslama_tarihi")
                    or p.get("ise_baslama_tarihi")
                    or p.get("baslama")
                    or ""
                )[:10]
                if baslama_str:
                    try:
                        ise_giris_t = datetime.datetime.strptime(baslama_str, "%Y-%m-%d").date()
                        if ise_giris_t > hesap_baslangic:
                            hesap_baslangic = ise_giris_t
                    except ValueError:
                        pass

                net_gun, tam_gun_izin, rapor_gun, _ = net_calisma_raporu(
                    hesap_baslangic,
                    ay_bitis,
                    p_izinleri,
                    [{"tarih": d.strftime("%Y-%m-%d")} for d in tatil_tarih_seti],
                )
                kullandigi_izin_gunu = sum(
                    1
                    for gun_no in range(1, toplam_ay_gunu + 1)
                    if datetime.date(sorgu_ay.year, sorgu_ay.month, gun_no).weekday() < 5
                    and datetime.date(sorgu_ay.year, sorgu_ay.month, gun_no) not in tatil_tarih_seti
                    and any(
                        datetime.datetime.strptime(str(iz.get("baslangic", ""))[:10], "%Y-%m-%d").date()
                        <= datetime.date(sorgu_ay.year, sorgu_ay.month, gun_no)
                        <= datetime.datetime.strptime(str(iz.get("bitis", ""))[:10], "%Y-%m-%d").date()
                        for iz in p_izinleri
                        if str(iz.get("baslangic", ""))[:10] and str(iz.get("bitis", ""))[:10]
                        and iz.get("tur", iz.get("izin_turu", "")) != "Saatlik İzin"
                    )
                )
            else:
                net_gun = 0
                kullandigi_izin_gunu = 0

            if net_gun < 0:
                net_gun = 0

            net_calisma_listesi.append({
                "Personel Adı": p_ad,
                "Durum": "Aktif" if aktif_mi else "Pasif",
                "Görevi": p.get("gorev") or p.get("gorevi") or "-",
                "Dönem": sorgu_yil_ay_str,
                "Toplam Ay Günü": toplam_ay_gunu,
                "Hafta İçi İş Günü": hafta_ici_is_gunu,
                "Kullanılan İzin / Rapor (Gün)": kullandigi_izin_gunu,
                "Net Çalışma Günü": net_gun,
            })

        if net_calisma_listesi:
            excel_p_calisma = tablo_to_excel_bytes(
                net_calisma_listesi,
                f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})",
            )
            pdf_p_calisma = tablo_to_html_pdf_bytes(
                f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})",
                net_calisma_listesi,
            )

            ortak_indirme_alani(
                excel_p_calisma,
                pdf_p_calisma,
                f"personel_net_calisma_{sorgu_yil_ay_str}",
                "personel_calisma_raporu_sayfasi",
            )
            ozel_html_tablo_goster(net_calisma_listesi)
        else:
            st.info("Raporlanacak personel bulunmuyor.")
