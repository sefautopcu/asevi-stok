import datetime
import time

def gunluk_yemek_uretim_sayfasi(st, misafir_modu, salt_okunur_modu, aktif_k_maskeleri, otomatik_yedek_al, verileri_kaydet, loglari_kaydet, yemek_uretim_arsivini_kaydet, simdi_tr_str, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster, urun_kalori_hesapla):
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi")

    # Son Yemek Üretim İşlemini Geri Al Butonu ve Bildirimi
    if st.session_state.get("son_yemek_uretim_kaydi"):
        son_uretim = st.session_state["son_yemek_uretim_kaydi"]
        c_undo1, c_undo2 = st.columns([3, 1])
        with c_undo1:
            st.info(
                f"💡 **Son Yemek Üretimi:** '{son_uretim.get('yemek_adi')}' ({son_uretim.get('kisi_sayisi')} Kişilik) - "
                f"Toplam Maliyet: {son_uretim.get('toplam_maliyet', 0):,.2f} ₺ - Tarih: {son_uretim.get('tarih')}"
            )
        with c_undo2:
            if st.button("↩️ Son Üretimi Geri Al", type="secondary", key="btn_undo_uretim_son"):
                otomatik_yedek_al("Yemek üretimi geri alma: " + str(son_uretim.get("yemek_adi")))
            
                # 1. Stoktan düşülen miktarları depoya iade et (Paketli sistem uyumlu)
                for item in son_uretim.get("dusulen_kayitlar", []):
                    for g in st.session_state.girisler:
                        if g.get("id") == item["id"]:
                            g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])
                            # Eğer paketli düşüm yapıldıysa paket durumunu da geri al
                            if item.get("paket_id"):
                                if "paket_durumlari" not in g: g["paket_durumlari"] = {}
                                eski_paket = g["paket_durumlari"].get(item["paket_id"], 0.0)
                                g["paket_durumlari"][item["paket_id"]] = eski_paket + float(item["miktar"])

                # 2. Yemek üretim arşivinden kaydı sil
                arsiv_target = son_uretim.get("arsiv_objesi")
                if arsiv_target and arsiv_target in st.session_state.yemek_uretim_arsivi:
                    st.session_state.yemek_uretim_arsivi.remove(arsiv_target)

                # 3. Kullanım loglarından ilgili kayıtları sil
                eklenen_loglar = son_uretim.get("eklenen_loglar", [])
                for log_item in eklenen_loglar:
                    if log_item in st.session_state.kullanim_loglari:
                        st.session_state.kullanim_loglari.remove(log_item)

                # 4. Değişiklikleri veritabanına kaydet
                verileri_kaydet(st.session_state.girisler)
                loglari_kaydet(st.session_state.kullanim_loglari)
                yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)

                st.session_state.pop("son_yemek_uretim_kaydi", None)
                st.success(f"🎉 '{son_uretim.get('yemek_adi')}' üretimi geri alındı, malzemeler stoğa iade edildi ve arşiv temizlendi!")
                time.sleep(1)
                st.rerun()

    col_tarih_mod, col_tarih_sec = st.columns([1.2, 1.8])
    with col_tarih_mod:
        zaman_modu = st.radio(
            "Arşiv Görünüm Modu", ["Tek Tarih", "Tarih Aralığı", "Tüm Zamanlar"], horizontal=True
        )
    with col_tarih_sec:
        if zaman_modu == "Tek Tarih":
            secilen_tarih_filtresi = st.date_input(
                "📅 Sorgulanacak Tarihi Seçin", value=datetime.date.today()
            )
            secilen_tarih_str = secilen_tarih_filtresi.strftime("%Y-%m-%d")
        elif zaman_modu == "Tarih Aralığı":
            c_bas, c_bit = st.columns(2)
            with c_bas:
                bas_tarih_filt = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7))
            with c_bit:
                bit_tarih_filt = st.date_input("Bitiş Tarihi", value=datetime.date.today())
        else:
            secilen_tarih_str = "TÜMÜ"

    if not misafir_modu:
        st.markdown("---")
        st.subheader("🍲 Yeni Yemek Üretim Planı ve Malzeme Düşümü")
        yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
        kisi_sayisi = st.number_input(
            "Yararlanan Kişi Sayısı", min_value=1, value=200
        )
        # Zorunlu Numune Seçimi
        numune_durumu = st.radio(
            "🧪 Numune Alındı mı? (Zorunlu)",
            ["Numune Alındı", "Numune Alınmadı"],
            index=None,
            horizontal=True,
            key="numune_secim_radio"
        )
    
        uretim_tarihi_input = st.date_input(
            "📅 Yemeğin Yapıldığı Tarih (Geçmiş / Bugün)",
            value=datetime.date.today(),
        )
        uretim_tarih_str = uretim_tarihi_input.strftime("%Y-%m-%d")

        benzersiz_urunler = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )

        if "sepet" not in st.session_state:
            st.session_state.sepet = []

        if not salt_okunur_modu:
            # YENİ: SEÇİM ALANI (MANUEL VEYA QR)
            st.markdown("#### 🛒 Malzeme Ekleme Yöntemi")
            ekleme_yontemi = st.radio("Nasıl eklemek istersiniz?", ["Manuel Seçim", "📷 QR Kod ile Okut"], horizontal=True)
        
            secilen_urun = None
            kullanilacak_miktar = 0.0
            secilen_paket_id = None 
            secilen_fatura_id = None

            if ekleme_yontemi == "Manuel Seçim":
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    secilen_urun = st.selectbox(
                        "Malzeme Seç",
                        benzersiz_urunler if benzersiz_urunler else [],
                        index=None,
                        placeholder="Malzeme Seçiniz...",
                        key="yemek_urun_manuel"
                    )
                with col2:
                    stok_max = 0.0
                    if secilen_urun:
                        ilgili_girisler = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == secilen_urun.strip().upper()]
                        stok_max = sum(g.get("kalan", 0) for g in ilgili_girisler)
                
                    kullanilacak_miktar = st.number_input(
                        f"Miktar (Toplam Stok: {stok_max})",
                        min_value=0.0, value=1.0, step=0.1, key="yemek_miktar_manuel",
                    )
                with col3:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Sepete Ekle", use_container_width=True, key="btn_sepete_ekle_manuel"):
                        if not secilen_urun:
                            st.error("⚠️ Lütfen sepete eklemek için bir malzeme seçin!")
                        elif kullanilacak_miktar <= 0:
                            st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                        else:
                            st.session_state.sepet.append({"urun": secilen_urun, "miktar": kullanilacak_miktar})
                            st.success("Eklendi!")
                            st.rerun()

            elif ekleme_yontemi == "📷 QR Kod ile Okut":
                st.info("Kamerayı açın ve paket üzerindeki QR kodu okutun. (Telefon veya Bilgisayar kamerası)")
                img_file_buffer = st.camera_input("Kamera", label_visibility="collapsed", key="yemek_uretim_kamera")
            
                if img_file_buffer is not None:
                    try:
                        import cv2
                        import numpy as np
                    except ImportError:
                        st.error("OpenCV kütüphanesi eksik. Lütfen requirements.txt dosyasını kontrol edin.")
                        st.stop()
                    
                    bytes_data = img_file_buffer.getvalue()
                    cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
                    detector = cv2.QRCodeDetector()
                    data, bbox, _ = detector.detectAndDecode(cv2_img)
                
                    if data:
                        qr_okunan_id = data.strip()
                        st.success(f"✅ Okundu: {qr_okunan_id}")
                    
                        ana_id = qr_okunan_id.split("-P")[0] if "-P" in qr_okunan_id else qr_okunan_id
                        ilgili_g = next((g for g in st.session_state.girisler if g.get("id") == ana_id), None)
                    
                        if ilgili_g:
                            urun_adi = ilgili_g.get("urun")
                        
                            # --- FIFO UYARISI (İlk Giren İlk Çıkar) ---
                            tum_ayni_urunler = [g for g in st.session_state.girisler if g.get("urun") == urun_adi and float(g.get("kalan", 0)) > 0]
                            en_eski_urun = min(tum_ayni_urunler, key=lambda x: str(x.get("tarih", ""))) if tum_ayni_urunler else None
                        
                            if en_eski_urun and en_eski_urun["id"] != ana_id:
                                st.warning(f"⚠️ **FIFO UYARISI:** Depoda bu üründen daha eski bir parti var (Fatura: {en_eski_urun['id']}, Tarih: {en_eski_urun.get('tarih')}). Lütfen önce eski partiyi tüketin!")
                        
                            # --- AÇIK PAKET UYARISI ---
                            if "-P" in qr_okunan_id:
                                if "paket_durumlari" not in ilgili_g:
                                    ilgili_g["paket_durumlari"] = {}
                                
                                paket_miktari = float(ilgili_g.get("paket_miktari", 0))
                                kalan_paket = ilgili_g["paket_durumlari"].get(qr_okunan_id, paket_miktari)
                            
                                # Başka açık paket var mı?
                                acik_paketler = [(p_id, p_kg) for p_id, p_kg in ilgili_g.get("paket_durumlari", {}).items() if p_kg > 0 and p_kg < paket_miktari]
                                if acik_paketler and acik_paketler[0][0] != qr_okunan_id:
                                    st.warning(f"⚠️ **AÇIK PAKET UYARISI:** Bu ürüne ait açık bir paket var! ({acik_paketler[0][0]} - Kalan: {acik_paketler[0][1]} {ilgili_g.get('birim')}). Önce onu kullanmalısınız!")
                            
                                if kalan_paket <= 0:
                                    st.error("❌ Bu paket tamamen tükenmiş! Lütfen başka bir paket okutun.")
                                else:
                                    st.info(f"**Paket:** {qr_okunan_id} | **Kalan:** {kalan_paket} {ilgili_g.get('birim')}")
                                    secilen_urun = urun_adi
                                    secilen_paket_id = qr_okunan_id
                                    secilen_fatura_id = ana_id
                                    kullanilacak_miktar = st.number_input(f"Kullanılacak Miktar ({ilgili_g.get('birim')})", min_value=0.1, max_value=kalan_paket, value=1.0, step=0.1, key="qr_miktar_manuel")
                                
                                    if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr"):
                                        st.session_state.sepet.append({
                                            "urun": urun_adi, 
                                            "miktar": kullanilacak_miktar,
                                            "paket_id": secilen_paket_id,
                                            "fatura_id": secilen_fatura_id
                                        })
                                        st.success("QR ile Eklendi!")
                                        st.rerun()
                            else:
                                # Dökme ürün
                                toplam_kalan = float(ilgili_g.get("kalan", 0))
                                st.info(f"**Dökme Ürün** | **Toplam Stok:** {toplam_kalan} {ilgili_g.get('birim')}")
                                secilen_urun = urun_adi
                                kullanilacak_miktar = st.number_input(f"Kullanılacak Miktar ({ilgili_g.get('birim')})", min_value=0.1, max_value=toplam_kalan, value=1.0, step=0.1, key="qr_miktar_dokme")
                            
                                if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr_dokme"):
                                    st.session_state.sepet.append({"urun": urun_adi, "miktar": kullanilacak_miktar})
                                    st.success("QR ile Eklendi!")
                                    st.rerun()
                        else:
                            st.error("Sistemde böyle bir kayıt bulunamadı.")
                    else:
                        st.warning("⏳ QR Kod aranıyor... Kamerayı koda odaklayın.")

        st.markdown("---")
        st.subheader("Seçilen Malzemeler")

        if st.session_state.sepet:
            if not salt_okunur_modu:
                if st.button("🔄 Tümünü Sıfırla"):
                    st.session_state.sepet = []
                    st.rerun()

            toplam_maliyet = 0.0
            toplam_kalori = 0.0
            excel_sepet_liste = []

            silinecek_index = None
            for idx, item in enumerate(st.session_state.sepet):
                urun = item["urun"]
                istenen = item["miktar"]

                ilgili_girisler = [
                    g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper()
                ]
                ortalama_fiyat = 0.0
                if ilgili_girisler:
                    toplam_fiyat_degeri = sum(
                        g.get("fiyat", 0) * g.get("miktar", 0) for g in ilgili_girisler
                    )
                    toplam_miktar_degeri = sum(g.get("miktar", 0) for g in ilgili_girisler)
                    ortalama_fiyat = (
                        toplam_fiyat_degeri / toplam_miktar_degeri
                        if toplam_miktar_degeri > 0
                        else 0.0
                    )

                item_maliyeti = istenen * ortalama_fiyat
                toplam_maliyet += item_maliyeti
                birim = ilgili_girisler[0].get("birim", "Kg") if ilgili_girisler else "Kg"
                item_kalorisi = urun_kalori_hesapla(urun, istenen, birim)
                toplam_kalori += item_kalorisi

                c_item_ad, c_item_mik, c_item_mal, c_item_sil = st.columns([3, 2, 2, 1])
                with c_item_ad:
                    st.markdown(f"• **{urun}**")
                with c_item_mik:
                    st.markdown(f"Miktar: {istenen}")
                with c_item_mal:
                    st.markdown(f"Maliyet: **{item_maliyeti:,.2f} ₺**")
                    st.caption(f"Kalori: {item_kalorisi:,.0f} kcal")
                with c_item_sil:
                    if not salt_okunur_modu:
                        if st.button("❌", key=f"sil_item_{idx}"):
                            silinecek_index = idx

                excel_sepet_liste.append({
                    "Malzeme": urun,
                    "Miktar": f"{istenen} {birim}",
                    "Maliyet (TL)": round(item_maliyeti, 2),
                    "Kalori (kcal)": round(item_kalorisi, 2),
                })

            if silinecek_index is not None:
                st.session_state.sepet.pop(silinecek_index)
                st.rerun()

            if not salt_okunur_modu:
                if st.button("🍲 Üretimi Tamamla ve Stoktan / Kullanıma Düş", type="primary"):
                    if not numune_durumu:
                        st.error("⚠️ Lütfen üretimi tamamlamadan önce 'Numune Alındı / Alınmadı' seçeneğini işaretleyin!")
                    else:
                        tarih_simdi = simdi_tr_str("%Y-%m-%d %H:%M")

                        arsiv_malzemeler = []
                        dusulen_kayitlar = []
                        eklenen_loglar = []

                        for item in st.session_state.sepet:
                            urun = item["urun"]
                            istenen = item["miktar"]
                            kalan_dusulecek = istenen
                            item_tutar = 0.0
                            paket_id = item.get("paket_id")
                            fatura_id = item.get("fatura_id")

                            ilgili_g = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper() and g.get("kalan", 0) > 0]
                        
                            if paket_id and fatura_id:
                                ilgili_g = [g for g in ilgili_g if g["id"] == fatura_id]

                            for g in ilgili_g:
                                if kalan_dusulecek <= 0: break
                            
                                if paket_id and g["id"] == fatura_id:
                                    # Paketli ürün düşümü
                                    if "paket_durumlari" not in g: g["paket_durumlari"] = {}
                                    mevcut_paket = g["paket_durumlari"].get(paket_id, float(g.get("paket_miktari", 0)))
                                
                                    dusulecek = min(kalan_dusulecek, mevcut_paket)
                                    g["paket_durumlari"][paket_id] = mevcut_paket - dusulecek
                                    g["kalan"] = float(g["kalan"]) - dusulecek
                                    item_tutar += dusulecek * float(g["fiyat"])
                                    kalan_dusulecek -= dusulecek
                                
                                    dusulen_kayitlar.append({"id": g["id"], "miktar": dusulecek, "paket_id": paket_id})
                                else:
                                    # Manuel eklendiyse (FIFO mantığıyla genel stoktan düş)
                                    if float(g["kalan"]) >= kalan_dusulecek:
                                        g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                        item_tutar += kalan_dusulecek * float(g["fiyat"])
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek, "paket_id": None})
                                        kalan_dusulecek = 0
                                    else:
                                        dusulen = float(g["kalan"])
                                        g["kalan"] = 0.0
                                        item_tutar += dusulen * float(g["fiyat"])
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen, "paket_id": None})
                                        kalan_dusulecek -= dusulen

                            arsiv_malzemeler.append(
                                {
                                    "urun": urun,
                                    "miktar": istenen,
                                    "birim": next(
                                        (
                                            g.get("birim", "Kg")
                                            for g in st.session_state.girisler
                                            if g.get("urun", "").strip().upper() == urun.strip().upper()
                                        ),
                                        "Kg",
                                    ),
                                    "tutar": item_tutar,
                                    "kalori": urun_kalori_hesapla(
                                        urun,
                                        istenen,
                                        next(
                                            (
                                                g.get("birim", "Kg")
                                                for g in st.session_state.girisler
                                                if g.get("urun", "").strip().upper() == urun.strip().upper()
                                            ),
                                            "Kg",
                                        ),
                                    ),
                                }
                            )

                            log_obj = {
                                "tarih": f"{uretim_tarih_str} 12:00",
                                "urun": urun,
                                "tur": f"Günlük Kullanım ({yemek_adi})",
                                "miktar": istenen,
                                "tutar": item_tutar,
                                "islem_yapan": st.session_state.aktif_kullanici,
                            }
                            st.session_state.kullanim_loglari.append(log_obj)
                            eklenen_loglar.append(log_obj)

                        arsiv_obj = {
                            "tarih": uretim_tarih_str,
                            "zaman": tarih_simdi,
                            "yemek_adi": yemek_adi,
                            "kisi_sayisi": kisi_sayisi,
                            "numune_durumu": numune_durumu,
                            "malzemeler": arsiv_malzemeler,
                            "toplam_maliyet": toplam_maliyet,
                            "toplam_kalori": toplam_kalori,
                            "kisi_basi_kalori": (
                                toplam_kalori / kisi_sayisi if kisi_sayisi > 0 else 0.0
                            ),
                            "islem_yapan": st.session_state.aktif_kullanici,
                        }
                        st.session_state.yemek_uretim_arsivi.append(arsiv_obj)

                        # Son yemek üretim kaydını sakla (Geri Al için)
                        st.session_state["son_yemek_uretim_kaydi"] = {
                            "yemek_adi": yemek_adi,
                            "kisi_sayisi": kisi_sayisi,
                            "toplam_maliyet": toplam_maliyet,
                            "tarih": uretim_tarih_str,
                            "dusulen_kayitlar": dusulen_kayitlar,
                            "arsiv_objesi": arsiv_obj,
                            "eklenen_loglar": eklenen_loglar
                        }

                        yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)
                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)
                        st.session_state.sepet = []
                        st.success(
                            f"🎉 Başarılı! {uretim_tarih_str} tarihli üretim arşive kaydedildi."
                        )
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

            st.markdown("---")
            kisi_basi_maliyet = (
                toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0.0
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Toplam Maliyet", f"{toplam_maliyet:,.2f} ₺")
            with m2:
                st.metric("Kişi Başı Maliyet", f"{kisi_basi_maliyet:,.2f} ₺")
            m3, m4 = st.columns(2)
            with m3:
                st.metric("Toplam Kalori", f"{toplam_kalori:,.0f} kcal")
            with m4:
                st.metric(
                    "Kişi Başı Kalori",
                    f"{(toplam_kalori / kisi_sayisi if kisi_sayisi > 0 else 0):,.0f} kcal",
                )

            pdf_data = tablo_to_html_pdf_bytes(
                f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste
            )
            excel_sepet_data = tablo_to_excel_bytes(
                excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}"
            )
            with col_indir_alan:
                ortak_indirme_alani(
                    excel_sepet_data,
                    pdf_data,
                    "yemek_maliyet_raporu",
                    "yemek_sayfasi",
                )
        else:
            st.info("Henüz sepete malzeme eklenmedi.")

    st.markdown("---")

    col_b_arsiv, col_indir_arsiv = st.columns([2, 2])
    with col_b_arsiv:
        if zaman_modu == "Tüm Zamanlar":
            st.subheader("📚 Tüm Zamanların Yemek Üretim ve Maliyet Arşivi")
            secilen_gun_uretimleri = st.session_state.yemek_uretim_arsivi
        elif zaman_modu == "Tek Tarih":
            st.subheader(
                f"📅 Seçilen Tarihteki ({secilen_tarih_str}) Yemek Üretim ve Maliyet Arşivi"
            )
            secilen_gun_uretimleri = [
                u
                for u in st.session_state.yemek_uretim_arsivi
                if u.get("tarih") == secilen_tarih_str
            ]
        else:
            st.subheader(f"📅 Tarih Aralığı Arşivi ({bas_tarih_filt} ile {bit_tarih_filt} arası)")
            secilen_gun_uretimleri = []
            for u in st.session_state.yemek_uretim_arsivi:
                t_str = u.get("tarih", "")
                try:
                    t_dt = datetime.datetime.strptime(t_str, "%Y-%m-%d").date()
                    if bas_tarih_filt <= t_dt <= bit_tarih_filt:
                        secilen_gun_uretimleri.append(u)
                except:
                    pass

    if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" in aktif_k_maskeleri:
        st.info("🔒 Yemek Üretim ve Maliyet Arşivi bu kullanıcı için maskelenmiştir (gizlenmiştir).")
    else:
        if secilen_gun_uretimleri:
            arsiv_tablo_verisi = []
            excel_arsiv_listesi = []
            for u_kayit in secilen_gun_uretimleri:
                toplam_maliyet_degeri = float(u_kayit.get("toplam_maliyet", 0))
                if toplam_maliyet_degeri == 0 and u_kayit.get("malzemeler"):
                    toplam_maliyet_degeri = sum(float(m.get("tutar", 0)) for m in u_kayit.get("malzemeler", []))
            
                kisi_sayisi_degeri = int(u_kayit.get("kisi_sayisi", 1) or 1)
                kisi_basi_maliyet = toplam_maliyet_degeri / kisi_sayisi_degeri if kisi_sayisi_degeri > 0 else 0.0
                toplam_kalori_degeri = float(u_kayit.get("toplam_kalori", 0))
                kisi_basi_kalori_degeri = (
                    float(u_kayit.get("kisi_basi_kalori", 0))
                    or (toplam_kalori_degeri / kisi_sayisi_degeri if kisi_sayisi_degeri > 0 else 0.0)
                )

                if misafir_modu:
                    arsiv_tablo_verisi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                        "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                    })
                    excel_arsiv_listesi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                        "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                    })
                else:
                    for m in u_kayit.get("malzemeler", []):
                        arsiv_tablo_verisi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"), # YENİ EKLENDİ
                            "Kullanılan Malzeme": f"{m.get('urun', '-')} ({m.get('miktar', '-')} {m.get('birim', '')})".strip(),
                            "Malzeme Maliyeti": f"{m.get('tutar', 0):,.2f} ₺",
                            "Menü Toplam Maliyeti": f"{toplam_maliyet_degeri:,.2f} ₺",
                            "Kişi Başı Maliyet": f"{kisi_basi_maliyet:,.2f} ₺",
                            "Menü Toplam Kalorisi": f"{toplam_kalori_degeri:,.0f} kcal",
                            "Kişi Başı Kalori": f"{kisi_basi_kalori_degeri:,.0f} kcal",
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })
                        excel_arsiv_listesi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"), # YENİ EKLENDİ
                            "Kullanılan Malzeme": f"{m.get('urun', '-')} ({m.get('miktar', '-')} {m.get('birim', '')})".strip(),
                            "Malzeme Maliyeti (TL)": round(m.get("tutar", 0), 2),
                            "Menü Toplam Maliyeti (TL)": round(toplam_maliyet_degeri, 2),
                            "Kişi Başı Maliyet (TL)": round(kisi_basi_maliyet, 2),
                            "Menü Toplam Kalorisi (kcal)": round(toplam_kalori_degeri, 2),
                            "Kişi Başı Kalori (kcal)": round(kisi_basi_kalori_degeri, 2),
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })

            rapor_adi_etiketi = "yemek_uretim_raporu_arsiv"
            baslik_etiketi = "Aziziye Aşevi - Yemek Üretim Raporu Arşivi"

            excel_arsiv_data = tablo_to_excel_bytes(
                excel_arsiv_listesi, baslik_etiketi
            )
            pdf_arsiv_data = tablo_to_html_pdf_bytes(baslik_etiketi, excel_arsiv_listesi)

            with col_indir_arsiv:
                ortak_indirme_alani(
                    excel_arsiv_data,
                    pdf_arsiv_data,
                    rapor_adi_etiketi,
                    "arsiv_tarih_araligi",
                )

            ozel_html_tablo_goster(arsiv_tablo_verisi)
        else:
            st.info("Seçilen tarih aralığında kayıtlı yemek üretim ve maliyet arşivi bulunmuyor.")

    # 6. KALORİ HESAPLAMA ARACI
