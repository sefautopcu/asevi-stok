import datetime
import time

def guncel_stok_sayfasi(st, misafir_modu, aktif_k_maskeleri, stok_excel_liste_olustur, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, stok_gorunum_listeleri_olustur, ozel_html_tablo_goster, verileri_kaydet, kritik_seviyeleri_kaydet, mevcut_urunler_qr_etiket_araci):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")
        bugun = datetime.date.today()

        # Excel ve Raporlama için Hazırlık
        benzersiz_urunler_Excel, excel_liste = stok_excel_liste_olustur(
            st.session_state.girisler, aktif_k_maskeleri
        )

        excel_data = tablo_to_excel_bytes(excel_liste, "Aziziye Aşevi - Güncel Stok Raporu")
        pdf_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Güncel Stok Raporu", excel_liste)

        col_baslik, col_indir_alan = st.columns([2, 2])
        with col_baslik:
            st.markdown("Aşağıda depodaki tüm ürünlerin toplam miktarları ve eski partilerden devreden bakiyeleri listelenmiştir.")
        with col_indir_alan:
            ortak_indirme_alani(excel_data, pdf_data, "asevi_guncel_stok_raporu", "stok_sayfasi")

        depolar = ["Tümü"] + st.session_state.depolar
        secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)

        benzersiz_urunler, stok_tablosu, kritik_urunler_tablosu = (
            stok_gorunum_listeleri_olustur(
                st.session_state.girisler, st.session_state.kritik_seviyeler,
                aktif_k_maskeleri, secilen_depo, bugun,
            )
        )

        st.markdown("### Envanter Listesi")
        ozel_html_tablo_goster(stok_tablosu)

        st.markdown("---")
        st.markdown("### ⚠️ Kritik Seviyenin Altındaki veya Tükenen Ürünler Tablosu")
        if kritik_urunler_tablosu:
            ozel_html_tablo_goster(kritik_urunler_tablosu)
        else:
            st.success("Tebrikler! Kritik seviyenin altında ürün bulunmuyor.")

        st.markdown("---")
    
        # --- YENİ EKLENEN: TOPLU SKT GÜNCELLEME FORMU ---
        st.markdown("### 📅 Son Tüketim Tarihi (SKT / STT) Güncelle")
        st.info("Sisteme daha önceden eklenmiş ve SKT tarihi girilmemiş ürünler için buradan toplu tarih güncellemesi yapabilirsiniz. Girilen tarih, seçilen ürünün en eski (en son kullanılacak) partisine atanır.")
    
        if not benzersiz_urunler:
            st.info("Sistemde kayıtlı ürün bulunmuyor.")
        else:
            with st.form("skt_guncelle_formu"):
                skt_sec_urun = st.selectbox("SKT Güncellenecek Ürünü Seçin", benzersiz_urunler, index=None, placeholder="Ürün Seçiniz...", key="skt_upd_urun")
                skt_yeni_tarih = st.date_input("Yeni SKT / STT Tarihi", value=None)
                skt_guncelle_btn = st.form_submit_button("SKT Tarihini Güncelle", type="primary")
            
                if skt_guncelle_btn:
                    if not skt_sec_urun:
                        st.error("⚠️ Lütfen SKT güncellenecek ürünü seçin!")
                    elif skt_yeni_tarih is None:
                        st.error("⚠️ Lütfen yeni SKT / STT tarihini seçin!")
                    else:
                        guncellendi = False
                        # İlgili ürünün stokta kalanı > 0 olan en eski partisini bul (FIFO)
                        ilgili_partiler = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == skt_sec_urun and g.get("kalan", 0) > 0]
                        
                        if ilgili_partiler:
                            # Seçilen ürünün stokta kalan TÜM partilerinin SKT'sini güncelle
                            for parti in ilgili_partiler:
                                parti["skt"] = str(skt_yeni_tarih)
                            guncellendi = True
                            # Tablonun anında güncellenmesi için session_state'i zorla tetikle
                            st.session_state.girisler = list(st.session_state.girisler)
                        
                        if guncellendi:
                            verileri_kaydet(st.session_state.girisler)
                            st.success(f"🎉 Başarılı! {skt_sec_urun} ürününün SKT tarihi {skt_yeni_tarih} olarak güncellendi.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ Seçilen ürünün stokta kalan partisi bulunmuyor, tarih atanamadı.")

        # --- YENİ EKLENEN: ÜRÜN BAZLI KRİTİK EŞİK SINIRI ---
        with st.expander("⚙️ Ürün Bazlı Kritik Eşik Sınırı Belirle"):
            with st.form("kritik_ayar_form"):
                secilen_k_urun = st.selectbox("Kritik Eşiği Değiştirilecek Ürün", benzersiz_urunler if benzersiz_urunler else ["Yok"])
                mevcut_esin = st.session_state.kritik_seviyeler.get(secilen_k_urun, 10.0)
                yeni_esin_deger = st.number_input("Kritik Miktar Sınırı", min_value=0.0, value=float(mevcut_esin), step=1.0)
                kritik_kaydet_btn = st.form_submit_button("Kritik Eşiği Güncelle", type="primary")

                if kritik_kaydet_btn and secilen_k_urun != "Yok":
                    st.session_state.kritik_seviyeler[secilen_k_urun] = yeni_esin_deger
                    kritik_seviyeleri_kaydet(st.session_state.kritik_seviyeler)
                    st.success("🎉 Başarılı! Kritik sınır güncellendi.")
                    st.balloons()
                    st.rerun()

        mevcut_urunler_qr_etiket_araci(
            st, benzersiz_urunler, verileri_kaydet
        )
