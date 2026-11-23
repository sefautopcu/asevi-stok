import datetime
import time

def fire_zayiat_sayfasi(st, menu, misafir_modu, salt_okunur_modu, otomatik_yedek_al, verileri_kaydet, loglari_kaydet, fifo_miktar_dus_detayli, aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Fire / Zayiat Bildirimi")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda fire düşemezsiniz.")
        else:
            # Son Fire İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_fire_kaydi"):
                son_fire = st.session_state["son_fire_kaydi"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Fire Kaydı:** {son_fire.get('urun')} ({son_fire.get('miktar')} Miktar - Zarar: {son_fire.get('tutar', 0):,.2f} ₺ - Tarih: {son_fire.get('tarih')})")
                with c_undo2:
                    if st.button("↩️ Son Fire İşlemini Geri Al", type="secondary", key="btn_undo_fire_son"):
                        otomatik_yedek_al("Fire girişi geri alma: " + str(son_fire.get("urun")))
                    
                        # Düşülen miktarları orijinal stok girişlerine iade et
                        for item in son_fire.get("dusulen_kayitlar", []):
                            for g in st.session_state.girisler:
                                if g.get("id") == item["id"]:
                                    g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                        # Kullanım loglarından sil
                        log_target = son_fire.get("log_objesi")
                        if log_target and log_target in st.session_state.kullanim_loglari:
                            st.session_state.kullanim_loglari.remove(log_target)

                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)
                    
                        st.session_state.pop("son_fire_kaydi", None)
                        st.success(f"🎉 {son_fire.get('urun')} için girilen fire bildirimi geri alındı ve stok iade edildi!")
                        time.sleep(1)
                        st.rerun()

            benzersiz_urunler = sorted(
                list(set(str(g.get("urun", "")).strip().upper() for g in st.session_state.girisler if g.get("urun")))
            )
        
            if not benzersiz_urunler:
                st.info("Sistemde kayıtlı ürün bulunmuyor.")
            else:
                col_f_t1, col_f_t2 = st.columns(2)
                with col_f_t1:
                    fire_tarihi_secim = st.date_input("📅 Fire / Zayiat Tarihi", value=datetime.date.today(), key="fire_tarih_inp")
                with col_f_t2:
                    fire_saati_secim = st.time_input("⏰ Fire Saati", value=datetime.datetime.now().time(), key="fire_saat_inp")
                fire_tarih_str = f"{fire_tarihi_secim.strftime('%Y-%m-%d')} {fire_saati_secim.strftime('%H:%M')}"

                secilen_gercek_urun = st.selectbox(
                    "Fire Düşülecek Ürünü Seçin",
                    benzersiz_urunler,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="fire_urun_secim_box"
                )
            
                if secilen_gercek_urun:
                    ilgili_girisler = [
                        g
                        for g in st.session_state.girisler
                        if str(g.get("urun", "")).strip().upper() == str(secilen_gercek_urun).strip().upper()
                    ]
                    toplam_stok = sum(float(g.get("kalan", 0)) for g in ilgili_girisler)
                    aktif_ilgili_girisler = [g for g in ilgili_girisler if float(g.get("kalan", 0)) > 0]

                    en_son_fiyat = 0.0
                    if ilgili_girisler:
                        en_son_kayit = max(
                            ilgili_girisler, key=lambda x: str(x.get("tarih", ""))
                        )
                        en_son_fiyat = float(en_son_kayit.get("fiyat", 0.0))

                    st.info(
                        f"Güncel Toplam Stok ({secilen_gercek_urun}): {toplam_stok} | Baz Alınan Birim Fiyat: {en_son_fiyat:,.2f} ₺"
                    )
                
                    fire_miktari = st.number_input(
                        "Fire Miktarı",
                        min_value=0.1,
                        value=1.0,
                        step=0.1,
                        key="fire_miktar_inp"
                    )
                    fire_aciklama = st.text_input(
                        "Fire Açıklaması / Nedeni",
                        placeholder="Örn: Bozuldu, döküldü, son kullanma tarihi geçti...",
                        key="fire_aciklama_inp"
                    ).strip()

                    if st.button("Fireyi Düş ve Kaydet", type="primary", key="fire_kaydet_button"):
                        if fire_miktari <= 0:
                            st.error("⚠️ Lütfen 0'dan büyük bir fire miktarı girin!")
                        elif fire_miktari > toplam_stok:
                            st.error(f"⚠️ Hata: Girilen fire miktarı ({fire_miktari}), güncel toplam stoktan ({toplam_stok}) büyük olamaz!")
                        else:
                            dusulen_kayitlar = fifo_miktar_dus_detayli(
                                aktif_ilgili_girisler, fire_miktari
                            )

                            toplam_zarar = fire_miktari * en_son_fiyat
                            dusulen_idler = {str(item.get("id")) for item in dusulen_kayitlar}
                            fatura_nolari = list(dict.fromkeys(
                                str(g.get("fatura_no", "")).strip()
                                for g in aktif_ilgili_girisler
                                if str(g.get("id")) in dusulen_idler and str(g.get("fatura_no", "")).strip()
                            ))

                            yeni_log = {
                                "tarih": fire_tarih_str,
                                "urun": secilen_gercek_urun,
                                "fatura_no": ", ".join(fatura_nolari) if fatura_nolari else "-",
                                "tur": "Fire/Zayiat",
                                "miktar": fire_miktari,
                                "tutar": toplam_zarar,
                                "aciklama": (fire_aciklama if fire_aciklama else "Belirtilmedi"),
                                "islem_yapan": st.session_state.aktif_kullanici,
                            }

                            st.session_state.kullanim_loglari.append(yeni_log)
                        
                            # Son fire kaydını session_state içinde sakla
                            st.session_state["son_fire_kaydi"] = {
                                "urun": secilen_gercek_urun,
                                "miktar": fire_miktari,
                                "tutar": toplam_zarar,
                                "tarih": fire_tarih_str,
                                "dusulen_kayitlar": dusulen_kayitlar,
                                "log_objesi": yeni_log
                            }

                            verileri_kaydet(st.session_state.girisler)
                            loglari_kaydet(st.session_state.kullanim_loglari)

                            st.success(
                                f"🎉 Başarılı! {secilen_gercek_urun} için fire düşüldü ({fire_tarih_str}). Toplam zarar: {toplam_zarar:,.2f} ₺"
                            )
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

        st.markdown("---")
    
        col_b_fire, col_indir_fire = st.columns([2, 2])
        with col_b_fire:
            st.subheader("📋 Kayıtlı Fire ve Zayiatlar Listesi")
    
        if "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi" in aktif_k_maskeleri:
            st.info("🔒 Kayıtlı Fire ve Zayiatlar Listesi tablosu bu kullanıcı için tamamen maskelenmiştir (gizlenmiştir).")
        else:
            fire_loglari = [
                l
                for l in st.session_state.kullanim_loglari
                if l.get("tur") == "Fire/Zayiat"
            ]
            if fire_loglari:
                fire_tablo_verisi = []
                for f_log in reversed(fire_loglari):
                    fire_tablo_verisi.append({
                        "Tarih / Saat": f_log.get("tarih", "-"),
                        "Ürün Adı": f_log.get("urun", "-"),
                        "Fatura No": f_log.get("fatura_no", "-"),
                        "Fire Miktarı": f"{f_log.get('miktar', 0)}",
                        "Toplam Tutar": f"{f_log.get('tutar', 0):,.2f} ₺",
                        "İşlemi Yapan": f_log.get("islem_yapan", "admin"),
                        "Açıklama": f_log.get("aciklama", "—"),
                    })
            
                excel_fire_data = tablo_to_excel_bytes(fire_tablo_verisi, "Aziziye Aşevi - Fire ve Zayiat Raporu")
                pdf_fire_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Fire ve Zayiat Raporu", fire_tablo_verisi)
                with col_indir_fire:
                    ortak_indirme_alani(excel_fire_data, pdf_fire_data, "fire_ve_zayiat_listesi", "fire_arsiv_sayfasi")

                ozel_html_tablo_goster(fire_tablo_verisi)
            else:
                st.info("Sistemde kayıtlı fire / zayiat bulunmuyor.")
