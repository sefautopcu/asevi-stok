import time

def urun_sil_duzenle_sayfasi(st, misafir_modu, salt_okunur_modu, yonetici_modu, verileri_kaydet, silinen_urun_loglarini_kaydet, otomatik_yedek_al, simdi_tr_str, silme_onay_kutusu, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda silme işlemi gerçekleştiremezsiniz.")
        elif not yonetici_modu:
            st.warning("⚠️ Bu ekrana erişmek için **Admin** hesabıyla giriş yapmalısınız.")
        else:
            if st.session_state.silme_mesaji:
                st.success(st.session_state.silme_mesaji)
                st.session_state.silme_mesaji = ""

            # Son Silme İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_silinen_kayit"):
                son_silinen = st.session_state["son_silinen_kayit"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Silinen Kayıt:** {son_silinen.get('urun')} (ID: {son_silinen.get('id')} - Kalan: {son_silinen.get('kalan')} {son_silinen.get('birim')})")
                with c_undo2:
                    if st.button("↩️ Silme İşlemini Geri Al", type="secondary", key="btn_undo_silme_son"):
                        # Silinen kaydı depoya geri ekle
                        st.session_state.girisler.append(son_silinen)
                        verileri_kaydet(st.session_state.girisler)

                        # Silinen ürün loglarından ilgili kaydı temizle
                        silinen_id = son_silinen.get("id")
                        st.session_state.silinen_urun_loglari = [
                            l for l in st.session_state.silinen_urun_loglari if l.get("kayit_id") != silinen_id
                        ]
                        silinen_urun_loglarini_kaydet(st.session_state.silinen_urun_loglari)

                        st.session_state.pop("son_silinen_kayit", None)
                        st.success(f"🎉 Kayıt ID {silinen_id} ({son_silinen.get('urun')}) depoya ve sisteme geri yüklendi!")
                        time.sleep(1)
                        st.rerun()

            if not st.session_state.girisler:
                st.info("Sistemde silinecek kayıt bulunmuyor.")
            else:
                with st.form("urun_silme_formu"):
                    secenekler = [
                        f"{g['id']} - {g['urun']} (Eklenme: {g.get('tarih', '-')}, Kalan: {g['kalan']} {g['birim']}, Fiyat: {g.get('fiyat', 0)} TL)"
                        for g in st.session_state.girisler
                    ]
                    secilen_kayit_str = st.selectbox(
                        "Silmek İstediğiniz Kaydı / Faturayı Seçin",
                        secenekler,
                        index=None,
                        placeholder="Silinecek kaydı seçiniz...",
                        key="urun_silme_select_box"
                    )
                    silme_nedeni_input = st.text_input(
                        "Silme Nedeni / Gerekçesi", "Örn: Yanlış giriş"
                    )
                    onay_sil_onay_btn = silme_onay_kutusu("onay_urun_sil")
                    sil_onay_btn = st.form_submit_button(
                        "Seçilen Kaydı Kalıcı Olarak Sil", type="primary"
                    )

                    if sil_onay_btn:
                        if not secilen_kayit_str:
                            st.error("⚠️ Lütfen silmek istediğiniz kaydı listeden seçin!")
                        elif not onay_sil_onay_btn:
                            st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                        else:
                            secilen_id = secilen_kayit_str.split(" - ")[0]
                            ilgili_oge = next(
                                (g for g in st.session_state.girisler if g["id"] == secilen_id),
                                None,
                            )
                            if ilgili_oge:
                                otomatik_yedek_al("Kayıt silme: " + str(ilgili_oge.get("id")))
                                silinen_urun_adi = ilgili_oge["urun"]
                            
                                # Son silinen kaydı sakla (Geri Al için)
                                st.session_state["son_silinen_kayit"] = ilgili_oge.copy()

                                st.session_state.silinen_urun_loglari.append({
                                    "tarih": simdi_tr_str("%Y-%m-%d %H:%M"),
                                    "urun": silinen_urun_adi,
                                    "kayit_id": ilgili_oge["id"],
                                    "fatura_no": ilgili_oge.get("fatura_no", "-"),
                                    "neden": (
                                        silme_nedeni_input
                                        if silme_nedeni_input
                                        else "Belirtilmedi"
                                    ),
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                })
                                silinen_urun_loglarini_kaydet(
                                    st.session_state.silinen_urun_loglari
                                )
                                st.session_state.girisler = [
                                    g
                                    for g in st.session_state.girisler
                                    if g["id"] != secilen_id
                                ]
                                verileri_kaydet(st.session_state.girisler)
                                st.session_state.silme_mesaji = (
                                    f"🎉 Başarılı! {silinen_urun_adi} kayıt ID {secilen_id} sistemden silindi."
                                )
                                st.balloons()
                                time.sleep(1)
                                st.rerun()

        st.markdown("---")
    
        col_b_silinen, col_indir_silinen = st.columns([2, 2])
        with col_b_silinen:
            st.subheader("📋 Silinen Ürünler Arşivi")

        if st.session_state.silinen_urun_loglari:
            silinen_tablo_verisi = [
                {
                    "Silinme Tarihi": sl["tarih"],
                    "Kayıt ID": sl.get("kayit_id", "-"),
                    "Ürün Adı": sl["urun"],
                    "Silme Nedeni": sl["neden"],
                    "İşlemi Yapan": sl.get("islem_yapan", "admin"),
                }
                for sl in st.session_state.silinen_urun_loglari
            ]
        
            excel_silinen_data = tablo_to_excel_bytes(silinen_tablo_verisi, "Aziziye Aşevi - Silinen Ürünler Arşivi")
            pdf_silinen_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Silinen Ürünler Arşivi", silinen_tablo_verisi)
            with col_indir_silinen:
                ortak_indirme_alani(excel_silinen_data, pdf_silinen_data, "silinen_urunler_arsivi", "silinen_arsiv_sayfasi")

            ozel_html_tablo_goster(silinen_tablo_verisi)
        else:
            st.info("Silinmiş ürün kaydı bulunmuyor.")
