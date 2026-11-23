import datetime
import time


def demirbas_yonetim_sayfasi(st, misafir_modu, salt_okunur_modu, yonetici_modu, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster, otomatik_yedek_al, demirbaslari_kaydet, yeni_id_uret, silme_onay_kutusu):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🛠️ Aşevi Demirbaş ve Ekipman Yönetimi")
        st.markdown("Aşevinde bulunan demirbaşları, mutfak ekipmanlarını ve malzemeleri buradan ekleyebilir, durumlarını (Sağlam, Bakımda vb.) takip edebilirsiniz.")

        # Son Demirbaş İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_demirbas_islem"):
            son_islem = st.session_state["son_demirbas_islem"]
            tur = son_islem.get("tur")
            d_obj = son_islem.get("obje")
            
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "ekle":
                    st.info(f"💡 **Son İşlem:** '{d_obj.get('ad')}' demirbaşı eklendi (ID: {d_obj.get('id')}).")
                elif tur == "sil":
                    st.info(f"💡 **Son İşlem:** '{d_obj.get('ad')}' demirbaş kaydı silindi (ID: {d_obj.get('id')}).")
            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_dem_son"):
                    otomatik_yedek_al("Demirbaş işlemi geri alma: " + str(d_obj.get("id")))
                    
                    if tur == "ekle":
                        st.session_state.demirbaslar = [d for d in st.session_state.demirbaslar if d.get("id") != d_obj.get("id")]
                    elif tur == "sil":
                        if not any(d.get("id") == d_obj.get("id") for d in st.session_state.demirbaslar):
                            st.session_state.demirbaslar.append(d_obj)
                    
                    demirbaslari_kaydet(st.session_state.demirbaslar)
                    st.session_state.pop("son_demirbas_islem", None)
                    st.success(f"🎉 '{d_obj.get('ad')}' kaydı üzerine yapılan işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        col_b_dem, col_indir_dem = st.columns([2, 2])
        with col_b_dem:
            st.subheader("📋 Kayıtlı Demirbaş Listesi")

        demirbas_tablo = []
        excel_demirbas_listesi = []
        for d in st.session_state.demirbaslar:
            demirbas_tablo.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })
            excel_demirbas_listesi.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })

        excel_dem_data = tablo_to_excel_bytes(excel_demirbas_listesi, "Aziziye Aşevi - Demirbaş Listesi")
        pdf_dem_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Demirbaş Listesi", excel_demirbas_listesi)

        with col_indir_dem:
            ortak_indirme_alani(excel_dem_data, pdf_dem_data, "demirbas_listesi_raporu", "demirbas_sayfasi")

        if salt_okunur_modu:
            st.warning("👀 Salt okunur modundasınız. Yeni demirbaş ekleyemez veya düzenleyemezsiniz.")
        else:
            col_dem_ekle, col_dem_sil = st.columns(2)
            with col_dem_ekle:
                with st.form("demirbas_ekle_form"):
                    st.markdown("**➕ Yeni Demirbaş Ekle**")
                    d_ad = st.text_input("Demirbaş Adı (Örn: Sanayi Tipi Fırın)").strip()
                    d_kat = st.selectbox("Kategori", ["Mutfak Ekipmanı", "Elektronik", "Mobilya", "Taşıt / Lojistik", "Diğer"])
                    d_adet = st.number_input("Adet", min_value=1, value=1, step=1)
                    d_durum = st.selectbox("Durumu", ["Sağlam", "Bakımda", "Hurda / Kullanılamaz"])
                    d_zimmet = st.text_input("Zimmetli Sorumlu / Yer (Örn: Aşçıbaşı)").strip()
                    d_tarih = st.date_input("Kayıt Tarihi", value=datetime.date.today())

                    dem_ekle_btn = st.form_submit_button("Demirbaş Kaydet", type="primary")
                    if dem_ekle_btn and d_ad:
                        yeni_d_id = yeni_id_uret("DEM-", st.session_state.demirbaslar)
                        yeni_dem_obj = {
                            "id": yeni_d_id,
                            "ad": d_ad,
                            "kategori": d_kat,
                            "adet": int(d_adet),
                            "durum": d_durum,
                            "zimmet": d_zimmet if d_zimmet else "Belirtilmemiş",
                            "tarih": str(d_tarih)
                        }
                        st.session_state.demirbaslar.append(yeni_dem_obj)
                        demirbaslari_kaydet(st.session_state.demirbaslar)
                        
                        st.session_state["son_demirbas_islem"] = {
                            "tur": "ekle",
                            "obje": yeni_dem_obj
                        }
                        
                        st.success(f"🎉 Başarılı! '{d_ad}' demirbaş listesine eklendi.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

            with col_dem_sil:
                if not yonetici_modu:
                    st.info("🗑️ Demirbaş silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("demirbas_sil_form"):
                        st.markdown("**🗑️ Demirbaş Sil**")
                        if st.session_state.demirbaslar:
                            dem_secenekleri = [f"{d['id']} - {d['ad']} ({d['kategori']})" for d in st.session_state.demirbaslar]
                            secilen_sil_dem = st.selectbox(
                                "Silinecek Demirbaşı Seçin",
                                dem_secenekleri,
                                index=None,
                                placeholder="Demirbaş Seçiniz...",
                                key="dem_sil_selectbox"
                            )
                            onay_dem_sil_btn = silme_onay_kutusu("onay_demirbas_sil")
                            dem_sil_btn = st.form_submit_button("Seçilen Demirbaş Kaydını Sil", type="primary")

                            if dem_sil_btn:
                                if not secilen_sil_dem:
                                    st.error("⚠️ Lütfen silmek istediğiniz demirbaşı seçin!")
                                elif not onay_dem_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                else:
                                    otomatik_yedek_al("Demirbaş silme: " + str(secilen_sil_dem))
                                    sil_id = secilen_sil_dem.split(" - ")[0]
                                    silinen_obj = next((d for d in st.session_state.demirbaslar if d["id"] == sil_id), None)
                                    
                                    if silinen_obj:
                                        st.session_state.demirbaslar = [d for d in st.session_state.demirbaslar if d["id"] != sil_id]
                                        demirbaslari_kaydet(st.session_state.demirbaslar)
                                        
                                        st.session_state["son_demirbas_islem"] = {
                                            "tur": "sil",
                                            "obje": silinen_obj
                                        }

                                        st.success("🎉 Başarılı! Demirbaş kaydı silindi.")
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            st.info("Silinecek demirbaş bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Demirbaş Tablosu")
        if demirbas_tablo:
            ozel_html_tablo_goster(demirbas_tablo)
        else:
            st.info("Kayıtlı demirbaş bulunmuyor.")

