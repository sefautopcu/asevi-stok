import datetime
import time

def toplu_stok_dusumu_sayfasi(st, misafir_modu, salt_okunur_modu, otomatik_yedek_al, fifo_sarfiyat_dus_detayli, verileri_kaydet, loglari_kaydet, ozel_html_tablo_goster):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🔄 Toplu Stok Düşümü ve Kullanılan Ürünler")
        st.markdown("Geçmiş yemek tarifleri seçmek zorunda kalmadan, kullanılan malzemeleri ve miktarlarını seçerek doğrudan stoktan düşürebilir ve kullanılan ürünler listesine ekleyebilirsiniz.")
    
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda toplu stok düşümü yapamazsınız.")
        else:
            # Son Sarfiyat İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_toplu_sarfiyat_kaydi"):
                son_sarf = st.session_state["son_toplu_sarfiyat_kaydi"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Sarfiyat Kaydı:** {son_sarf.get('urun')} ({son_sarf.get('miktar')} Miktar - Tutar: {son_sarf.get('tutar', 0):,.2f} ₺ - Tarih: {son_sarf.get('tarih')})")
                with c_undo2:
                    if st.button("↩️ Son Sarfiyat İşlemini Geri Al", type="secondary", key="btn_undo_toplu_sarf_son"):
                        otomatik_yedek_al("Toplu sarfiyat geri alma: " + str(son_sarf.get("urun")))
                    
                        # Düşülen miktarları orijinal stok girişlerine iade et
                        for item in son_sarf.get("dusulen_kayitlar", []):
                            for g in st.session_state.girisler:
                                if g.get("id") == item["id"]:
                                    g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                        # Kullanım loglarından sil
                        log_target = son_sarf.get("log_objesi")
                        if log_target and log_target in st.session_state.kullanim_loglari:
                            st.session_state.kullanim_loglari.remove(log_target)

                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)
                    
                        st.session_state.pop("son_toplu_sarfiyat_kaydi", None)
                        st.success(f"🎉 {son_sarf.get('urun')} için yapılan stok düşümü geri alındı ve stok iade edildi!")
                        time.sleep(1)
                        st.rerun()

            col_form1, col_form2 = st.columns(2)
        
            with col_form1:
                st.subheader("Malzeme Çıkış Formu")
                benzersiz_urunler_toplu = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
            
                if benzersiz_urunler_toplu:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        toplu_tarih_secim = st.date_input("📅 Sarfiyat Tarihi", value=datetime.date.today(), key="toplu_tarih_inp")
                    with col_t2:
                        toplu_saat_secim = st.time_input("⏰ Sarfiyat Saati", value=datetime.datetime.now().time(), key="toplu_saat_inp")
                    toplu_tarih_str = f"{toplu_tarih_secim.strftime('%Y-%m-%d')} {toplu_saat_secim.strftime('%H:%M')}"

                    selected_item = st.selectbox(
                        "Malzeme Seçin",
                        benzersiz_urunler_toplu,
                        index=None,
                        placeholder="Malzeme Seçiniz...",
                        key="toplu_malzeme_selectbox"
                    )
                
                    if selected_item:
                        ilgili_girisler_toplu = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == selected_item.strip().upper()]
                        current_stock = sum(float(g.get("kalan", 0)) for g in ilgili_girisler_toplu)
                        aktif_ilgili_toplu = [g for g in ilgili_girisler_toplu if float(g.get("kalan", 0)) > 0]
                    
                        unit = ilgili_girisler_toplu[0].get("birim", "Kg") if ilgili_girisler_toplu else "Kg"
                    
                        st.info(f"Mevcut Toplam Stok ({selected_item}): {current_stock} {unit}")
                    
                        used_amount = st.number_input(f"Kullanılan Miktar ({unit})", min_value=0.1, value=1.0, step=0.5)
                        description = st.text_input("Açıklama / Not (Örn: Kazan yemeği, günlük dağıtım vb.)", "Günlük Aşevi Üretimi")
                    
                        if st.button("Stoktan Düş ve Kullanılanlara Ekle", type="primary"):
                            if used_amount <= 0:
                                st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                            elif used_amount > current_stock:
                                st.error(f"⚠️ Hata: Kullanılan miktar ({used_amount}), mevcut toplam stoktan ({current_stock}) büyük olamaz!")
                            else:
                                harcanan_tutar, dusulen_kayitlar = (
                                    fifo_sarfiyat_dus_detayli(aktif_ilgili_toplu, used_amount)
                                )
                            
                                yeni_log = {
                                    "tarih": toplu_tarih_str,
                                    "urun": selected_item,
                                    "tur": f"Toplu Sarfiyat ({description})",
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                }

                                st.session_state.kullanim_loglari.append(yeni_log)
                            
                                # Son sarfiyat kaydını session_state içinde sakla
                                st.session_state["son_toplu_sarfiyat_kaydi"] = {
                                    "urun": selected_item,
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "tarih": toplu_tarih_str,
                                    "dusulen_kayitlar": dusulen_kayitlar,
                                    "log_objesi": yeni_log
                                }

                                verileri_kaydet(st.session_state.girisler)
                                loglari_kaydet(st.session_state.kullanim_loglari)
                            
                                st.success(f"🎉 Başarılı! {toplu_tarih_str} tarihli {used_amount} {unit} {selected_item} stoktan düşüldü ve loglara eklendi!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("Depoda kayıtlı ürün bulunmuyor.")

            with col_form2:
                st.subheader("Geçmişte Kullanılan Ürünler (Sarfiyat Logu)")
                toplu_sarfiyat_loglari = [l for l in st.session_state.kullanim_loglari if "Toplu Sarfiyat" in l.get("tur", "")]
                if toplu_sarfiyat_loglari:
                    tablo_sarf = []
                    for s_log in reversed(toplu_sarfiyat_loglari):
                        tablo_sarf.append({
                            "Tarih / Saat": s_log.get("tarih", "-"),
                            "Malzeme": s_log.get("urun", "-"),
                            "Miktar": f"{s_log.get('miktar', 0)}",
                            "Tutar": f"{s_log.get('tutar', 0):,.2f} ₺",
                            "Açıklama": s_log.get("tur", "-"),
                            "İşlemi Yapan": s_log.get("islem_yapan", "-"),
                        })
                    ozel_html_tablo_goster(tablo_sarf)
                else:
                    st.info("Henüz toplu stok düşümü yapılmadı.")
