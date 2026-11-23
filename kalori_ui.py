import time


def kalori_hesaplama_sayfasi(st, supabase_veri_oku, supabase_veri_kaydet, urun_kalori_hesapla, yeni_id_uret, simdi_tr_str, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ozel_html_tablo_goster, ortak_indirme_alani):
    st.header("🔥 Reçete ve Kalori Analiz Merkezi")
    st.info("ℹ️ **Not:** Kalori değerleri, standart 100 gram/ml başına ortalama besin değerleri baz alınarak **yaklaşık olarak** hesaplanmaktadır. Tıbbi veya resmi diyet programları için kesin sonuç vermez.")
    
    if "kalori_sepeti" not in st.session_state:
        st.session_state.kalori_sepeti = []
    if "kalori_arsivi" not in st.session_state:
        st.session_state.kalori_arsivi = supabase_veri_oku("kalori_receteleri", [])

    col_form, col_sepet = st.columns([1, 1.5])
    
    with col_form:
        st.subheader("🍲 Reçete Detayları")
        recete_adi = st.text_input("Reçete / Yemek Adı", placeholder="Örn: Mercimek Çorbası", key="kalori_recete_adi")
        kisi_sayisi_kalori = st.number_input("Kaç Kişilik?", min_value=1, value=4, step=1, key="kalori_kisi_sayisi")
        
        st.markdown("---")
        st.subheader("➕ Malzeme Ekle")
        benzersiz_urunler_kalori = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )
        
        if not benzersiz_urunler_kalori:
            st.warning("Sistemde kayıtlı ürün bulunmuyor. Lütfen önce stok girişi yapın.")
        else:
            col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
            with col_m1:
                secilen_kalori_urun = st.selectbox(
                    "Malzeme", benzersiz_urunler_kalori, index=None, placeholder="Seçiniz...", key="kalori_urun_sec"
                )
            with col_m2:
                kalori_miktar_input = st.number_input(
                    "Miktar", min_value=0.1, value=1.0, step=0.5, key="kalori_mik"
                )
            with col_m3:
                kalori_birim_input = st.selectbox(
                    "Birim", ["Kg", "Adet", "Lt"], key="kalori_brm"
                )
                
            if st.button("Sepete Ekle", type="primary", use_container_width=True):
                if not secilen_kalori_urun:
                    st.error("Lütfen bir malzeme seçin.")
                else:
                    kalori_degeri = urun_kalori_hesapla(secilen_kalori_urun, kalori_miktar_input, kalori_birim_input)
                    st.session_state.kalori_sepeti.append({
                        "urun": secilen_kalori_urun,
                        "miktar": kalori_miktar_input,
                        "birim": kalori_birim_input,
                        "kalori": kalori_degeri
                    })
                    st.success("Malzeme eklendi!")
                    st.rerun()

    with col_sepet:
        st.subheader("📋 Malzeme Sepeti ve Analiz")
        if not st.session_state.kalori_sepeti:
            st.info("Henüz malzeme eklenmedi.")
        else:
            toplam_kalori = sum(item["kalori"] for item in st.session_state.kalori_sepeti)
            kisi_basi_kalori = toplam_kalori / kisi_sayisi_kalori if kisi_sayisi_kalori > 0 else 0
            
            # Özet Metrikler
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Toplam Kalori (Yaklaşık)", f"{toplam_kalori:,.0f} kcal")
            with m2:
                st.metric(f"Kişi Başı (Yaklaşık, {kisi_sayisi_kalori} Kişi)", f"{kisi_basi_kalori:,.0f} kcal")
            
            # Sepet Tablosu
            sepet_tablo = []
            for idx, item in enumerate(st.session_state.kalori_sepeti):
                sepet_tablo.append({
                    "Malzeme": item["urun"],
                    "Miktar": f"{item['miktar']} {item['birim']}",
                    "Kalori (kcal)": f"{item['kalori']:,.0f}"
                })
            
            ozel_html_tablo_goster(sepet_tablo)
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("🗑️ Sepeti Temizle", use_container_width=True):
                    st.session_state.kalori_sepeti = []
                    st.rerun()
            with c2:
                if st.button("💾 Reçeteyi Kaydet", type="primary", use_container_width=True):
                    if not recete_adi:
                        st.error("Lütfen reçeteye bir isim verin!")
                    else:
                        yeni_recete = {
                            "id": yeni_id_uret("REC-", st.session_state.kalori_arsivi),
                            "tarih": simdi_tr_str("%Y-%m-%d %H:%M"),
                            "recete_adi": recete_adi,
                            "kisi_sayisi": kisi_sayisi_kalori,
                            "toplam_kalori": toplam_kalori,
                            "kisi_basi_kalori": kisi_basi_kalori,
                            "malzemeler": st.session_state.kalori_sepeti,
                            "islem_yapan": st.session_state.aktif_kullanici
                        }
                        st.session_state.kalori_arsivi.append(yeni_recete)
                        supabase_veri_kaydet("kalori_receteleri", st.session_state.kalori_arsivi)
                        st.session_state.kalori_sepeti = []
                        st.success("🎉 Reçete başarıyla kaydedildi!")
                        time.sleep(1)
                        st.rerun()
            with c3:
                # Anlık sepeti indirme (Uyarı notu eklendi)
                rapor_basligi = f"Kalori Raporu - {recete_adi or 'Isimsiz'} (Not: Kalori değerleri yaklaşık olarak hesaplanmıştır.)"
                excel_sepet = tablo_to_excel_bytes(sepet_tablo, rapor_basligi)
                pdf_sepet = tablo_to_html_pdf_bytes(rapor_basligi, sepet_tablo)
                st.download_button(
                    "📥 Raporu İndir", 
                    data=excel_sepet, 
                    file_name="kalori_raporu.xlsx", 
                    use_container_width=True,
                    key="kalori_anlik_indir"
                )

    st.markdown("---")
    
    # --- GEÇMİŞ REÇETELER ARŞİVİ ---
    st.subheader("📚 Kayıtlı Reçeteler Arşivi")
    
    if not st.session_state.kalori_arsivi:
        st.info("Henüz kaydedilmiş bir reçete bulunmuyor.")
    else:
        arsiv_tablo_verisi = []
        for r in reversed(st.session_state.kalori_arsivi):
            arsiv_tablo_verisi.append({
                "Reçete ID": r.get("id", "-"),
                "Tarih": r.get("tarih", "-"),
                "Reçete Adı": r.get("recete_adi", "-"),
                "Kişi Sayısı": r.get("kisi_sayisi", 1),
                "Toplam Kalori": f"{r.get('toplam_kalori', 0):,.0f}",
                "Kişi Başı Kalori": f"{r.get('kisi_basi_kalori', 0):,.0f}",
                "İşlemi Yapan": r.get("islem_yapan", "-")
            })
        
        col_arsiv_bas, col_arsiv_indir = st.columns([2, 2])
        with col_arsiv_indir:
            arsiv_basligi = "Kayıtlı Reçeteler Arşivi (Not: Kalori değerleri yaklaşık olarak hesaplanmıştır.)"
            excel_arsiv = tablo_to_excel_bytes(arsiv_tablo_verisi, arsiv_basligi)
            pdf_arsiv = tablo_to_html_pdf_bytes(arsiv_basligi, arsiv_tablo_verisi)
            ortak_indirme_alani(excel_arsiv, pdf_arsiv, "kalori_recete_arsivi", "kalori_arsiv_indir_btn")
            
        ozel_html_tablo_goster(arsiv_tablo_verisi)
        
        # Reçete detayı görüntüleme ve silme
        with st.expander("🔍 Geçmiş Reçete Detaylarını İncele / Sil"):
            secilen_recete_id = st.selectbox(
                "İncelemek istediğiniz reçeteyi seçin",
                [r["id"] for r in st.session_state.kalori_arsivi],
                index=None,
                placeholder="Reçete Seçiniz...",
                key="kalori_arsiv_secim"
            )
            if secilen_recete_id:
                secilen_r = next((r for r in st.session_state.kalori_arsivi if r["id"] == secilen_recete_id), None)
                if secilen_r:
                    st.markdown(f"**Reçete:** {secilen_r['recete_adi']} | **Toplam Kalori:** {secilen_r['toplam_kalori']:,.0f} kcal | **Kişi Başı:** {secilen_r['kisi_basi_kalori']:,.0f} kcal")
                    
                    detay_tablo = [{"Malzeme": m["urun"], "Miktar": f"{m['miktar']} {m['birim']}", "Kalori": f"{m['kalori']:,.0f} kcal"} for m in secilen_r.get("malzemeler", [])]
                    ozel_html_tablo_goster(detay_tablo)
                    
                    if st.button("🗑️ Bu Reçeteyi Sil", type="primary", key="recete_sil_btn"):
                        st.session_state.kalori_arsivi = [r for r in st.session_state.kalori_arsivi if r["id"] != secilen_recete_id]
                        supabase_veri_kaydet("kalori_receteleri", st.session_state.kalori_arsivi)
                        st.success("Reçete silindi!")
                        time.sleep(1)
                        st.rerun()

