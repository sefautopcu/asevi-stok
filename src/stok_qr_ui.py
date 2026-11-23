from .qr_utils import qr_png_bytesi_olustur


def mevcut_urunler_qr_etiket_araci(st, benzersiz_urunler, verileri_kaydet):
    # --- YENİ EKLENEN: MEVCUT ÜRÜNLER İÇİN QR KOD ÜRETİMİ ---
    st.markdown("---")
    st.markdown("### 🖨️ Mevcut Paketli Ürünler İçin QR Etiket Üret")
    st.info("Deponuzda daha önceden kayıtlı olan paketli ürünler için (örn: eski faturalar) buradan QR etiketlerini üretebilirsiniz. Paket miktarını sisteme girdiğinizde, sistem faturaya bağlı P1, P2... şeklinde etiketler oluşturur.")

    try:
        import qrcode
    except ImportError:
        st.error("QR Kod kütüphanesi eksik. Lütfen `requirements.txt` dosyasına `qrcode[pil]` ekleyin.")
        qrcode = None

    if qrcode and benzersiz_urunler:
        secilen_qr_urun = st.selectbox("QR Kodu Üretilecek Ürünü Seçin", benzersiz_urunler, index=None, placeholder="Ürün Seçiniz...", key="qr_stok_secim")

        if secilen_qr_urun:
            ilgili_faturalar = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == secilen_qr_urun and float(g.get("kalan", 0)) > 0]

            if not ilgili_faturalar:
                st.warning("Bu ürünün stokta kalan aktif bir partisi (faturası) bulunmuyor.")
            else:
                fatura_secenekleri = {f"{f['id']} - (Kalan: {f['kalan']} {f['birim']}, Fiyat: {f.get('fiyat', 0)} TL)": f for f in ilgili_faturalar}
                secilen_fatura_str = st.selectbox("Hangi Faturaya (Partiye) Ait QR Kod Üretilecek?", list(fatura_secenekleri.keys()), key="qr_fatura_secim")

                if secilen_fatura_str:
                    secilen_fatura = fatura_secenekleri[secilen_fatura_str]

                    mevcut_paket_miktari = float(secilen_fatura.get("paket_miktari", 0))

                    yeni_paket_miktari = st.number_input("Bu Ürünün Paket Miktarı (Kg/Lt)", min_value=0.1, value=mevcut_paket_miktari if mevcut_paket_miktari > 0 else 1.0, step=1.0, help="Sadece bu fatura/parti için geçerlidir.")

                    if st.button("Paket Miktarını Kaydet ve QR Üret", type="primary"):
                        secilen_fatura["paket_miktari"] = yeni_paket_miktari
                        verileri_kaydet(st.session_state.girisler)
                        st.success("Paket miktarı kaydedildi! QR kodlar aşağıda oluşturuldu.")
                        st.rerun()

                    if mevcut_paket_miktari > 0 or yeni_paket_miktari > 0:
                        toplam_miktar = float(secilen_fatura.get("miktar", 0))
                        paket_sayisi = int(toplam_miktar // yeni_paket_miktari)

                        if paket_sayisi == 0:
                            st.warning("Toplam miktar, paket miktarından küçük. Lütfen paket miktarını kontrol edin.")
                        else:
                            st.markdown(f"**Toplam {paket_sayisi} adet paket etiketi oluşturulacak.**")

                            if "paket_durumlari" not in secilen_fatura:
                                secilen_fatura["paket_durumlari"] = {}

                            cols = st.columns(4)
                            for i in range(1, paket_sayisi + 1):
                                p_id = f"{secilen_fatura['id']}-P{i}"

                                kalan_paket_kg = secilen_fatura["paket_durumlari"].get(p_id, yeni_paket_miktari)

                                img_bytes = qr_png_bytesi_olustur(qrcode, p_id)

                                with cols[(i - 1) % 4]:
                                    st.image(img_bytes, caption=f"{p_id} | Kalan: {kalan_paket_kg} {secilen_fatura['birim']}", width=140)
                                    st.download_button(
                                        label=f"📥 {p_id} İndir",
                                        data=img_bytes,
                                        file_name=f"QR_{p_id}.png",
                                        mime="image/png",
                                        key=f"dl_{p_id}"
                                    )

