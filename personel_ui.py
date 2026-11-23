import calendar
import datetime
import time

def personel_ve_calisma_suresi_sayfasi(st, misafir_modu, salt_okunur_modu, yonetici_modu, aktif_k_maskeleri, idleri_benzersiz_yap, otomatik_yedek_al, personelleri_kaydet, personel_izinlerini_kaydet, yeni_id_uret, simdi_tr_str, silme_onay_kutusu, net_calisma_raporu, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster, supabase_veri_kaydet):
    import calendar
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 Personel ve Çalışma Süresi Takibi")
        st.markdown(
            "Aşevi personelinin kayıtlarını tutun, izin/rapor günlerini girin ve net çalışma günlerini takip edin."
        )

        # Session State Güvenlik Kontrolleri ve Otomatik ID Ataması
        if "personeller" not in st.session_state or st.session_state.personeller is None:
            st.session_state.personeller = []
    
        # ID'si eksik olan eski kayıtlar varsa anında benzersiz PER- ID'si atanır
        st.session_state.personeller = idleri_benzersiz_yap(st.session_state.personeller, "PER-")

        if "personel_izinleri" not in st.session_state or st.session_state.personel_izinleri is None:
            st.session_state.personel_izinleri = []

        # Son Personel / İzin İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_personel_islem"):
            son_p_islem = st.session_state["son_personel_islem"]
            tur = son_p_islem.get("tur")
            p_obj = son_p_islem.get("obje", {})
        
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "personel_ekle":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli eklendi.")
                elif tur == "personel_sil":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli silindi.")
                elif tur == "izin_ekle":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' için {p_obj.get('gun_sayisi', 0)} günlük {p_obj.get('izin_turu', '-')} eklendi.")
                elif tur == "izin_sil":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' kişisine ait izin kaydı silindi.")

            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_personel_son"):
                    otomatik_yedek_al("Personel işlemi geri alma: " + str(tur))
                
                    if tur == "personel_ekle":
                        st.session_state.personeller = [p for p in st.session_state.personeller if str(p.get("id")) != str(p_obj.get("id"))]
                    elif tur == "personel_sil":
                        if not any(str(p.get("id")) == str(p_obj.get("id")) for p in st.session_state.personeller):
                            st.session_state.personeller.append(p_obj)
                    elif tur == "izin_ekle":
                        st.session_state.personel_izinleri = [iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) != str(p_obj.get("id"))]
                    elif tur == "izin_sil":
                        if not any(str(iz.get("id")) == str(p_obj.get("id")) for iz in st.session_state.personel_izinleri):
                            st.session_state.personel_izinleri.append(p_obj)

                    personelleri_kaydet(st.session_state.personeller)
                    personel_izinlerini_kaydet(st.session_state.personel_izinleri)

                    st.session_state.pop("son_personel_islem", None)
                    st.success("🎉 Yapılan son işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        tab_p1, tab_p2, tab_p3 = st.tabs([
            "📋 Personel Listesi ve Ekle/Sil",
            "📅 İzin & Rapor Girişi ve Takibi",
            "📊 Net Çalışma Günü Raporu"
        ])

        # TAB 1: PERSONEL LİSTESİ VE EKLE / SİL
        with tab_p1:
            col_b_pers, col_indir_pers = st.columns([2, 2])
            with col_b_pers:
                st.subheader("📋 Personel Kayıtları ve Yönetimi")

            personel_gosterim = []
            for p in st.session_state.personeller:
                ad_soyad_val = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
                tc_p = "🔒 Gizli" if "5. Sayfa: Personel - T.C. No" in aktif_k_maskeleri else (p.get("tc_no") or p.get("tc") or "-")
                ad_p = "🔒 Gizli" if "5. Sayfa: Personel - Adı Soyadı" in aktif_k_maskeleri else ad_soyad_val
                tel_p = "🔒 Gizli" if "5. Sayfa: Personel - Telefon" in aktif_k_maskeleri else (p.get("telefon") or "-")
                gorev_p = p.get("gorev") or p.get("gorevi") or "-"
                tarih_p = p.get("baslama_tarihi") or p.get("baslama") or p.get("ise_baslama_tarihi") or p.get("tarih") or "-"

                personel_gosterim.append({
                    "Personel ID": p.get("id", "-"),
                    "T.C. Kimlik No": tc_p,
                    "Adı Soyadı": ad_p,
                    "Görevi / Unvanı": gorev_p,
                    "Telefon": tel_p,
                    "İşe Başlama Tarihi": tarih_p,
                })

            excel_p_data = tablo_to_excel_bytes(personel_gosterim, "Aziziye Aşevi - Personel Listesi")
            pdf_p_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Personel Listesi", personel_gosterim)
            with col_indir_pers:
                ortak_indirme_alani(excel_p_data, pdf_p_data, "personel_listesi_raporu", "personel_sayfasi")

            if not salt_okunur_modu:
                col_p_ekle, col_p_sil = st.columns(2)
                with col_p_ekle:
                    with st.form("yeni_personel_form"):
                        st.markdown("**➕ Yeni Personel Ekle**")
                        p_tc = st.text_input("T.C. Kimlik No").strip()
                        p_ad = st.text_input("Adı Soyadı").strip().upper()
                        p_gorev = st.text_input("Görevi / Unvanı (Örn: Aşçıbaşı, Şoför)").strip()
                        p_tel = st.text_input("Telefon Numarası")
                        p_tarih = st.date_input("İşe Başlama Tarihi", value=datetime.date.today())

                        p_ekle_btn = st.form_submit_button("Personeli Kaydet", type="primary")
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
                                "eklenme_zamanı": simdi_tr_str("%Y-%m-%d %H:%M")
                            }
                            st.session_state.personeller.append(yeni_p_obj)
                        
                            personelleri_kaydet(st.session_state.personeller)

                            st.session_state["son_personel_islem"] = {
                                "tur": "personel_ekle",
                                "obje": yeni_p_obj
                            }

                            st.success(f"🎉 Başarılı! {p_ad} personel olarak kaydedildi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

                with col_p_sil:
                    if not yonetici_modu:
                        st.info("🗑️ Personel silme yetkisi yalnızca Admin'e aittir.")
                    else:
                        with st.form("personel_sil_form"):
                            st.markdown("**🗑️ Kayıtlı Personeli Sil**")
                            if st.session_state.personeller:
                                p_secenekler_sil = [
                                    f"{p.get('id', '-') } - {p.get('ad_soyad') or p.get('ad') or p.get('isim') or '-'} ({p.get('gorev') or p.get('gorevi') or '-'})"
                                    for p in st.session_state.personeller
                                ]
                                secilen_sil_p = st.selectbox(
                                    "Silinecek Personeli Seçin",
                                    p_secenekler_sil,
                                    index=None,
                                    placeholder="Personel Seçiniz...",
                                    key="personel_sil_selectbox"
                                )
                                onay_p_sil_btn = silme_onay_kutusu("onay_personel_sil")
                                p_sil_btn = st.form_submit_button("Seçilen Personeli Sil", type="primary")

                                if p_sil_btn:
                                    if not secilen_sil_p:
                                        st.error("⚠️ Lütfen silinecek personeli seçin!")
                                    elif not onay_p_sil_btn:
                                        st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                    else:
                                        otomatik_yedek_al("Personel silme: " + str(secilen_sil_p))
                                        sil_p_id = secilen_sil_p.split(" - ")[0]
                                        silinen_p_obj = next(
                                            (p for p in st.session_state.personeller if str(p.get("id", "")) == str(sil_p_id) or f"{p.get('id', '-')} - {p.get('ad_soyad') or p.get('ad') or '-'}" in secilen_sil_p), 
                                            None
                                        )
                                    
                                        if silinen_p_obj:
                                            st.session_state.personeller = [
                                                p for p in st.session_state.personeller 
                                                if p != silinen_p_obj and str(p.get("id", "")) != str(sil_p_id)
                                            ]
                                        
                                            personelleri_kaydet(st.session_state.personeller)
                                        
                                            st.session_state["son_personel_islem"] = {
                                                "tur": "personel_sil",
                                                "obje": silinen_p_obj
                                            }

                                            st.success("🎉 Başarılı! Personel kaydı silindi.")
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
                            p_isimler = [p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-" for p in st.session_state.personeller]
                            secilen_p_ad = st.selectbox(
                                "Personel Seçin",
                                p_isimler,
                                index=None,
                                placeholder="Personel Seçiniz...",
                                key="izin_personel_select"
                            )
                            izin_turu = st.selectbox(
                                "İzin / Mazeret Türü",
                                ["Yıllık İzin", "Mazeret İzni", "Hastalık / Rapor", "Ücretsiz İzin", "Resmi Görev / Diğer"],
                                index=None,
                                placeholder="İzin Türü Seçiniz...",
                                key="izin_turu_select"
                            )
                            c_iz_bas, c_iz_bit = st.columns(2)
                            with c_iz_bas:
                                iz_bas_tarih = st.date_input("İzin Başlangıç Tarihi", value=datetime.date.today())
                            with c_iz_bit:
                                iz_bit_tarih = st.date_input("İzin Bitiş Tarihi", value=datetime.date.today())
                        
                            iz_aciklama = st.text_input("Açıklama / Not", "Yıllık İzin Kullanımı").strip()
                            iz_ekle_btn = st.form_submit_button("İznı Kaydet", type="primary")

                            if iz_ekle_btn:
                                if not secilen_p_ad:
                                    st.error("⚠️ Lütfen bir personel seçin!")
                                elif not izin_turu:
                                    st.error("⚠️ Lütfen izin türünü seçin!")
                                elif iz_bit_tarih < iz_bas_tarih:
                                    st.error("⚠️ Bitiş tarihi başlangıç tarihinden önce olamaz!")
                                else:
                                    gun_sayisi = (iz_bit_tarih - iz_bas_tarih).days + 1
                                    yeni_iz_id = yeni_id_uret("IZN-", st.session_state.personel_izinleri)
                                    yeni_iz_obj = {
                                        "id": yeni_iz_id,
                                        "personel_ad": secilen_p_ad,
                                        "izin_turu": izin_turu,
                                        "baslangic": str(iz_bas_tarih),
                                        "bitis": str(iz_bit_tarih),
                                        "gun_sayisi": gun_sayisi,
                                        "aciklama": iz_aciklama,
                                        "ekleme_tarihi": simdi_tr_str("%Y-%m-%d %H:%M")
                                    }
                                    st.session_state.personel_izinleri.append(yeni_iz_obj)
                                
                                    personel_izinlerini_kaydet(st.session_state.personel_izinleri)

                                    st.session_state["son_personel_islem"] = {
                                        "tur": "izin_ekle",
                                        "obje": yeni_iz_obj
                                    }

                                    st.success(f"🎉 Başarılı! {secilen_p_ad} için {gun_sayisi} günlük {izin_turu} kaydedildi.")
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
                                        f"{iz.get('id', '-') } - {iz.get('personel_ad', '-') } ({iz.get('izin_turu', '-') }: {iz.get('baslangic', '-') } / {iz.get('bitis', '-') })"
                                        for iz in st.session_state.personel_izinleri
                                    ]
                                    secilen_sil_iz = st.selectbox(
                                        "Silinecek İzin Kaydını Seçin",
                                        iz_secenekler,
                                        index=None,
                                        placeholder="İzin Kaydı Seçiniz...",
                                        key="izin_sil_select"
                                    )
                                    onay_iz_sil_btn = silme_onay_kutusu("onay_izin_sil")
                                    iz_sil_btn = st.form_submit_button("İzin Kaydını Sil", type="primary")

                                    if iz_sil_btn:
                                        if not secilen_sil_iz:
                                            st.error("⚠️ Lütfen silinecek izin kaydını seçin!")
                                        elif not onay_iz_sil_btn:
                                            st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                        else:
                                            sil_iz_id = secilen_sil_iz.split(" - ")[0]
                                            silinen_iz_obj = next((iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) == str(sil_iz_id)), None)
                                        
                                            if silinen_iz_obj:
                                                st.session_state.personel_izinleri = [iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) != str(sil_iz_id)]
                                            
                                                personel_izinlerini_kaydet(st.session_state.personel_izinleri)

                                                st.session_state["son_personel_islem"] = {
                                                    "tur": "izin_sil",
                                                    "obje": silinen_iz_obj
                                                }

                                                st.success("🎉 Başarılı! İzin kaydı silindi.")
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
        
            sorgu_ay = st.date_input("Sorgulanacak Ay ve Yıl Seçin", value=datetime.date.today(), key="sorgu_ay_picker")
            sorgu_yil_ay_str = sorgu_ay.strftime("%Y-%m")
        
            toplam_ay_gunu = calendar.monthrange(sorgu_ay.year, sorgu_ay.month)[1]
        
            net_calisma_raporu = []
            for p in st.session_state.personeller:
                p_ad = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
            
                kullandigi_izin_gunu = 0
                for iz in st.session_state.personel_izinleri:
                    if iz.get("personel_ad") == p_ad:
                        bas_t = iz.get("baslangic", "")
                        if bas_t.startswith(sorgu_yil_ay_str):
                            kullandigi_izin_gunu += int(iz.get("gun_sayisi", 0))

                net_gun = toplam_ay_gunu - kullandigi_izin_gunu
                if net_gun < 0:
                    net_gun = 0

                net_calisma_raporu.append({
                    "Personel Adı": p_ad,
                    "Görevi": p.get("gorev") or p.get("gorevi") or "-",
                    "Dönem": sorgu_yil_ay_str,
                    "Toplam Ay Günü": toplam_ay_gunu,
                    "Kullanılan İzin / Rapor (Gün)": kullandigi_izin_gunu,
                    "Net Çalışma Günü": net_gun
                })

            if net_calisma_raporu:
                excel_p_calisma = tablo_to_excel_bytes(net_calisma_raporu, f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})")
                pdf_p_calisma = tablo_to_html_pdf_bytes(f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})", net_calisma_raporu)
            
                ortak_indirme_alani(excel_p_calisma, pdf_p_calisma, f"personel_net_calisma_{sorgu_yil_ay_str}", "personel_calisma_raporu_sayfasi")
                ozel_html_tablo_goster(net_calisma_raporu)
            else:
                st.info("Raporlanacak personel bulunmuyor.")
            
    # 9. KULLANIM TAKİBİ
