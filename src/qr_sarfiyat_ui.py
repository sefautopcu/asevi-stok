import time

from .qr_utils import qr_png_bytesi_olustur


def qr_kod_ile_hizli_sarfiyat_sayfasi(
    st, salt_okunur_modu, fifo_sarfiyat_dus, simdi_tr_str,
    verileri_kaydet, loglari_kaydet,
):
    if salt_okunur_modu:
        st.warning("⚠️ Salt okunur moddasınız. Stok düşümü yapamazsınız.")
    else:
        st.header("📷 QR Kod ile Hızlı Stok Düşümü")
        st.markdown("Depodaki ürünlerin üzerindeki QR kodu okutarak, fatura/ürün detayına saniyeler içinde ulaşıp stok düşümü yapabilirsiniz.")

        try:
            import cv2
            import qrcode
            import numpy as np
            from PIL import Image
        except ImportError:
            st.error("Lütfen terminale `pip install opencv-python-headless qrcode[pil] numpy` yazarak gerekli kütüphaneleri yükleyin.")
            st.stop()

        tab1, tab2 = st.tabs(["📸 QR Kod Okut (Sarfiyat)", "🖨️ QR Kod Üret & Yazdır"])

        with tab1:
            col_kamera, col_bilgi = st.columns([1, 1.2])
            with col_kamera:
                st.markdown("**Kamerayı Açın ve QR Kodu Gösterin**")
                img_file_buffer = st.camera_input("Kamera", label_visibility="collapsed")
                qr_okunan_id = None
                if img_file_buffer is not None:
                    bytes_data = img_file_buffer.getvalue()
                    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                    detector = cv2.QRCodeDetector()
                    data, bbox, _ = detector.detectAndDecode(cv2_img)
                    if data:
                        qr_okunan_id = data.strip()
                        st.success(f"✅ QR Kod Başarıyla Okundu! (ID: {qr_okunan_id})")
                    else:
                        st.warning("⏳ QR Kod aranıyor... Lütfen kodu kameraya net bir şekilde odaklayın.")

            with col_bilgi:
                if qr_okunan_id:
                    ilgili_girisler = [g for g in st.session_state.girisler if g.get("id") == qr_okunan_id]
                    if not ilgili_girisler:
                        st.error(f"❌ Sistemde `{qr_okunan_id}` ID'sine ait bir ürün/fatura bulunamadı!")
                    else:
                        urun_obj = ilgili_girisler[0]
                        toplam_kalan = sum(float(g.get("kalan", 0)) for g in ilgili_girisler)
                        st.info(f"**Ürün Adı:** {urun_obj.get('urun')}\n\n**Kategori:** {urun_obj.get('kategori')}\n\n**Mevcut Stok:** {toplam_kalan} {urun_obj.get('birim')}")
                        if toplam_kalan <= 0:
                            st.warning("⚠️ Bu ürünün stoğu tükenmiş!")
                        else:
                            with st.form("qr_stok_dus_formu"):
                                st.markdown("**Kullanım / Sarfiyat Bilgisi**")
                                # Streamlit'in max_value sınırını aşmamak için 1M sınırı uygula
                                max_acceptable_dus = min(toplam_kalan, 1_000_000) if toplam_kalan > 0 else 0.001
                                dusulecek_miktar = st.number_input(f"Kullanılan Miktar ({urun_obj.get('birim')})", min_value=0.1, max_value=max(max_acceptable_dus, 0.001), value=1.0, step=0.1)
                                aciklama = st.text_input("Açıklama (Örn: Öğle yemeği için kullanıldı)")
                                dus_btn = st.form_submit_button("Stoktan Düş ve Kaydet", type="primary")
                                if dus_btn:
                                    harcanan_tutar = fifo_sarfiyat_dus(ilgili_girisler, dusulecek_miktar)
                                    yeni_log = {
                                        "tarih": simdi_tr_str("%Y-%m-%d %H:%M"),
                                        "urun": urun_obj.get("urun"),
                                        "tur": f"QR Sarfiyat ({aciklama or 'Hızlı Düşüm'})",
                                        "miktar": dusulecek_miktar,
                                        "tutar": harcanan_tutar,
                                        "islem_yapan": st.session_state.aktif_kullanici,
                                    }
                                    st.session_state.kullanim_loglari.append(yeni_log)
                                    verileri_kaydet(st.session_state.girisler)
                                    loglari_kaydet(st.session_state.kullanim_loglari)
                                    st.success(f"🎉 Başarılı! {dusulecek_miktar} {urun_obj.get('birim')} {urun_obj.get('urun')} stoktan düşüldü.")
                                    time.sleep(1.5)
                                    st.rerun()

        with tab2:
            st.markdown("Stoktaki ürünlerin/faturaların etiketlerini oluşturup yazıcıdan çıkarabilirsiniz.")
            if not st.session_state.girisler:
                st.info("Sistemde kayıtlı ürün bulunmuyor.")
            else:
                secenekler_qr = [f"{g['id']} - {g['urun']} (Fatura: {g.get('fatura_no', '-')})" for g in st.session_state.girisler]
                secilen_qr_urun = st.selectbox("QR Kodu Oluşturulacak Kaydı Seçin", secenekler_qr, index=None, placeholder="Seçiniz...")
                if secilen_qr_urun:
                    secilen_id_qr = secilen_qr_urun.split(" - ")[0]
                    img_bytes = qr_png_bytesi_olustur(qrcode, secilen_id_qr)
                    col_qr_img, col_qr_btn = st.columns([1, 2])
                    with col_qr_img:
                        st.image(img_bytes, caption=f"Etiket: {secilen_id_qr}", width=200)
                    with col_qr_btn:
                        st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
                        st.download_button(label="📥 QR Kodu İndir (PNG)", data=img_bytes, file_name=f"QR_{secilen_id_qr}.png", mime="image/png", type="primary")
