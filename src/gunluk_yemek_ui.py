import datetime
import time
from src.yemek_utils import giris_birim_fiyati_al, yemek_sepeti_maliyet_hesapla

# Yemek menüsünün 4 ana bölümü
MENU_KISIMLARI = ("ana_yemek", "yardimci_yemek", "corba", "tatli_meyve_yogurt")
MENU_KISIM_ETIKETLERI = {
    "ana_yemek": "Ana Yemek",
    "yardimci_yemek": "Ara Yemek / Tatlı",
    "corba": "Çorba",
    "tatli_meyve_yogurt": "Tatlı / Meyve / Yoğurt",
}


def gunluk_yemek_uretim_sayfasi(st, misafir_modu, salt_okunur_modu, aktif_k_maskeleri, otomatik_yedek_al, verileri_kaydet, loglari_kaydet, yemek_uretim_arsivini_kaydet, simdi_tr_str, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster, urun_kalori_hesapla, yonetici_modu, yemek_malzeme_kullanim_istatistikleri, yemek_malzeme_kullanim_uyarilari, yemek_sepeti_stok_hatalari):
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
            secilen_tarih_str = f"{bas_tarih_filt} - {bit_tarih_filt}"
        else:
            secilen_tarih_str = "TÜMÜ"

    if not misafir_modu:
        st.markdown("---")
        st.subheader("🍲 Yeni Yemek Üretim Planı ve Malzeme Düşümü")

        # 4'lü Menü Bölümü
        st.markdown("### 🍽️ Menü Bölümleri (4 Kısım)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            ana_yemek_ad = st.text_input("🥘 Ana Yemek", value="", placeholder="Örn: Ispanak Yemeği", key="menu_ana_yemek_input")
        with col_m2:
            yardimci_yemek_ad = st.text_input("🍛 Ara Yemek / Tatlı", value="", placeholder="Örn: Mercimlek, Baklava", key="menu_yardimci_yemek_input")
        with col_m3:
            corba_ad = st.text_input("🍲 Çorba", value="", placeholder="Örn: Mercimek Çorbası", key="menu_corba_input")
        with col_m4:
            tatli_meyve_yogurt_ad = st.text_input("🍨 Tatlı / Meyve / Yoğurt", value="", placeholder="Örn: Yoğurt, Muhallebi", key="menu_tatli_input")

        # Birleştirilmiş Yemek Adı
        menulari_birlestir = [f"{etiket}: {ad}" for ad, etiket in [
            (ana_yemek_ad, MENU_KISIM_ETIKETLERI["ana_yemek"]),
            (yardimci_yemek_ad, MENU_KISIM_ETIKETLERI["yardimci_yemek"]),
            (corba_ad, MENU_KISIM_ETIKETLERI["corba"]),
            (tatli_meyve_yogurt_ad, MENU_KISIM_ETIKETLERI["tatli_meyve_yogurt"]),
        ] if ad.strip()]
        yemek_adi = "; ".join(menulari_birlestir) if menulari_birlestir else (ana_yemek_ad or yardimci_yemek_ad or corba_ad or tatli_meyve_yogurt_ad or "Yemek Planı")

        kisi_sayisi = st.number_input(
            "Yararlanan Kişi Sayısı", min_value=1, max_value=10000, value=200
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

                    sepet_kullanimi = sum(
                        float(item.get("miktar", 0) or 0)
                        for item in st.session_state.sepet
                        if str(item.get("urun", "")).strip().upper()
                        == str(secilen_urun or "").strip().upper()
                    )
                    kalan_stok = max(float(stok_max) - sepet_kullanimi, 0.0)
                    # Streamlit'in max_value sınırını aşmamak için 1M sınırı uygula
                    max_acceptable = min(kalan_stok, 1_000_000.0)
                    max_input = max(max_acceptable, 0.001)
                    try:
                        mevcut_miktar = float(
                            st.session_state.get("yemek_miktar_manuel", 1.0)
                        )
                    except (TypeError, ValueError):
                        mevcut_miktar = 1.0
                    st.session_state["yemek_miktar_manuel"] = min(
                        max(mevcut_miktar, 0.0), max_input
                    )
                    kullanilacak_miktar = st.number_input(
                        f"Miktar (Toplam Stok: {stok_max})",
                        min_value=0.0,
                        max_value=max_input,
                        step=0.1,
                        key="yemek_miktar_manuel",
                    )
                with col3:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Sepete Ekle", use_container_width=True, key="btn_sepete_ekle_manuel"):
                        if not secilen_urun:
                            st.error("⚠️ Lütfen sepete eklemek için bir malzeme seçin!")
                        elif kullanilacak_miktar <= 0:
                            st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                        else:
                            yeni_item = {
                                "urun": secilen_urun,
                                "miktar": kullanilacak_miktar,
                            }
                            try:
                                stok_hatalari = yemek_sepeti_stok_hatalari(
                                    st.session_state.girisler,
                                    [*st.session_state.sepet, yeni_item],
                                )
                            except ValueError as hata:
                                st.error(f"⚠️ Stok kontrolü yapılamadı: {hata}")
                            else:
                                if stok_hatalari:
                                    st.error(f"⚠️ {stok_hatalari[0]}")
                                else:
                                    st.session_state.sepet.append(yeni_item)
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
                                    # Streamlit'in max_value sınırını aşmamak için 1M sınırı uygula
                                    max_acceptable_paket = min(
                                        max(float(kalan_paket), 0.0), 1_000_000.0
                                    )
                                    max_input_paket = max(max_acceptable_paket, 0.1)
                                    try:
                                        mevcut_paket_miktari = float(
                                            st.session_state.get("qr_miktar_manuel", 1.0)
                                        )
                                    except (TypeError, ValueError):
                                        mevcut_paket_miktari = 1.0
                                    st.session_state["qr_miktar_manuel"] = min(
                                        max(mevcut_paket_miktari, 0.1),
                                        max_input_paket,
                                    )
                                    kullanilacak_miktar = st.number_input(
                                        f"Kullanılacak Miktar ({ilgili_g.get('birim')})",
                                        min_value=0.1,
                                        max_value=max_input_paket,
                                        step=0.1,
                                        key="qr_miktar_manuel",
                                    )
                                
                                    if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr"):
                                        yeni_item = {
                                            "urun": urun_adi, 
                                            "miktar": kullanilacak_miktar,
                                            "paket_id": secilen_paket_id,
                                            "fatura_id": secilen_fatura_id
                                        }
                                        stok_hatalari = yemek_sepeti_stok_hatalari(
                                            st.session_state.girisler,
                                            [*st.session_state.sepet, yeni_item],
                                        )
                                        if stok_hatalari:
                                            st.error(f"⚠️ {stok_hatalari[0]}")
                                        else:
                                            st.session_state.sepet.append(yeni_item)
                                            st.success("QR ile Eklendi!")
                                            st.rerun()
                            else:
                                # Dökme ürün
                                toplam_kalan = float(ilgili_g.get("kalan", 0))
                                st.info(f"**Dökme Ürün** | **Toplam Stok:** {toplam_kalan} {ilgili_g.get('birim')}")
                                secilen_urun = urun_adi
                                # Streamlit'in max_value sınırını aşmamak için 1M sınırı uygula
                                max_acceptable_dokme = min(
                                    max(float(toplam_kalan), 0.0), 1_000_000.0
                                )
                                max_input_dokme = max(max_acceptable_dokme, 0.1)
                                try:
                                    mevcut_dokme_miktari = float(
                                        st.session_state.get("qr_miktar_dokme", 1.0)
                                    )
                                except (TypeError, ValueError):
                                    mevcut_dokme_miktari = 1.0
                                st.session_state["qr_miktar_dokme"] = min(
                                    max(mevcut_dokme_miktari, 0.1),
                                    max_input_dokme,
                                )
                                kullanilacak_miktar = st.number_input(
                                    f"Kullanılacak Miktar ({ilgili_g.get('birim')})",
                                    min_value=0.1,
                                    max_value=max_input_dokme,
                                    step=0.1,
                                    key="qr_miktar_dokme",
                                )
                            
                                if st.button("Sepete Ekle (QR)", use_container_width=True, key="btn_sepete_ekle_qr_dokme"):
                                    yeni_item = {"urun": urun_adi, "miktar": kullanilacak_miktar}
                                    stok_hatalari = yemek_sepeti_stok_hatalari(
                                        st.session_state.girisler,
                                        [*st.session_state.sepet, yeni_item],
                                    )
                                    if stok_hatalari:
                                        st.error(f"⚠️ {stok_hatalari[0]}")
                                    else:
                                        st.session_state.sepet.append(yeni_item)
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

            kalem_maliyetleri, toplam_maliyet = yemek_sepeti_maliyet_hesapla(
                st.session_state.girisler, st.session_state.sepet
            )
            toplam_kalori = 0.0
            excel_sepet_liste = []

            silinecek_index = None
            for idx, item in enumerate(st.session_state.sepet):
                urun = item["urun"]
                istenen = item["miktar"]

                ilgili_girisler = [
                    g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper()
                ]

                item_maliyeti = kalem_maliyetleri[idx]
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

            gecmis_istatistikleri = {}
            gecmis_kontrol_mesajlari = []
            if not salt_okunur_modu:
                mevcut_menu = {
                    "ana_yemek": ana_yemek_ad,
                    "yardimci_yemek": yardimci_yemek_ad,
                    "corba": corba_ad,
                    "tatli_meyve_yogurt": tatli_meyve_yogurt_ad,
                }
                gecmis_istatistikleri = yemek_malzeme_kullanim_istatistikleri(
                    st.session_state.yemek_uretim_arsivi,
                    mevcut_menu,
                    kisi_sayisi,
                    uretim_tarih_str,
                )
                sepet_miktarlari = {}
                sepet_adlari = {}
                sepet_birimleri = {}
                for item in st.session_state.sepet:
                    malzeme_anahtari = "".join(
                        str(item.get("urun", "")).split()
                    ).upper()
                    if not malzeme_anahtari:
                        continue
                    sepet_miktarlari[malzeme_anahtari] = (
                        sepet_miktarlari.get(malzeme_anahtari, 0.0)
                        + float(item.get("miktar", 0) or 0)
                    )
                    sepet_adlari[malzeme_anahtari] = str(item.get("urun", "")).strip()
                    sepet_birimleri[malzeme_anahtari] = next(
                        (
                            g.get("birim", "Kg")
                            for g in st.session_state.girisler
                            if str(g.get("urun", "")).strip().upper()
                            == str(item.get("urun", "")).strip().upper()
                        ),
                        "Kg",
                    )

                for malzeme_anahtari, istatistik in gecmis_istatistikleri.items():
                    if malzeme_anahtari not in sepet_miktarlari:
                        continue
                    miktar = sepet_miktarlari[malzeme_anahtari]
                    birim = sepet_birimleri.get(malzeme_anahtari, "")
                    birim_eki = f" {birim}" if birim else ""
                    gecmis_kontrol_mesajlari.append(
                        f"**{sepet_adlari[malzeme_anahtari]}**: Geçmişte "
                        f"{istatistik['uretim_sayisi']} üretimde kişi başı ortalama "
                        f"{istatistik['ortalama_kisi_basi']:g}{birim_eki}/kişi "
                        f"kullanılmıştı. {kisi_sayisi:g} kişi için beklenen miktar "
                        f"yaklaşık **{istatistik['beklenen_miktar']:g}{birim_eki}**; "
                        f"bu üretimde **{miktar:g}{birim_eki}** girildi."
                    )

                if gecmis_kontrol_mesajlari:
                    gecmis_uyarilari = yemek_malzeme_kullanim_uyarilari(
                        gecmis_istatistikleri,
                        st.session_state.sepet,
                        kisi_sayisi,
                        sepet_birimleri,
                    )
                    if gecmis_uyarilari:
                        st.warning(
                            "⚠️ **Geçmiş kullanım kontrolü:** Üretimi tamamlamadan "
                            "önce aşağıdaki sapmaları inceleyin."
                        )
                    else:
                        st.info(
                            "ℹ️ **Geçmiş kullanım kontrolü:** Önceki üretim "
                            "ortalamasıyla karşılaştırma yapıldı."
                        )
                    for mesaj in gecmis_kontrol_mesajlari[:5]:
                        st.markdown(mesaj)
                    kontrol_imzasi = (
                        yemek_adi,
                        str(kisi_sayisi),
                        tuple(sorted(sepet_miktarlari.items())),
                    )
                    kontrol_anahtari = (
                        "yemek_gecmis_kontrol_onayi_"
                        + str(abs(hash(kontrol_imzasi)))
                    )
                    kontrol_okundu = st.checkbox(
                        "Geçmiş kullanım kontrolünü okudum, üretime devam et",
                        key=kontrol_anahtari,
                    )
                else:
                    kontrol_okundu = True
            else:
                kontrol_okundu = True

            if not salt_okunur_modu:
                if st.button("🍲 Üretimi Tamamla ve Stoktan / Kullanıma Düş", type="primary"):
                    if gecmis_kontrol_mesajlari and not kontrol_okundu:
                        st.error(
                            "⚠️ Üretimi tamamlamak için geçmiş kullanım "
                            "karşılaştırmasını okuyup onaylayın."
                        )
                    elif not numune_durumu:
                        st.error("⚠️ Lütfen üretimi tamamlamadan önce 'Numune Alındı / Alınmadı' seçeneğini işaretleyin!")
                    else:
                        tarih_simdi = simdi_tr_str("%Y-%m-%d %H:%M")

                        arsiv_malzemeler = []
                        dusulen_kayitlar = []
                        eklenen_loglar = []

                        uretim_islem_id = f"URM-{int(time.time() * 1000)}"

                        for item in st.session_state.sepet:
                            urun = item["urun"]
                            istenen = item["miktar"]
                            kalan_dusulecek = istenen
                            item_tutar = 0.0
                            item_partiler = []
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
                                    
                                    g_birim_f = giris_birim_fiyati_al(g)
                                    item_tutar += dusulecek * g_birim_f
                                    
                                    kalan_dusulecek -= dusulecek
                                
                                    dusulen_kayitlar.append({"id": g["id"], "miktar": dusulecek, "paket_id": paket_id})
                                    item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": dusulecek, "paket_id": paket_id})
                                else:
                                    # Manuel eklendiyse (FIFO mantığıyla genel stoktan düş)
                                    g_birim_f = giris_birim_fiyati_al(g)

                                    if float(g["kalan"]) >= kalan_dusulecek:
                                        g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                        item_tutar += kalan_dusulecek * g_birim_f
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek, "paket_id": None})
                                        item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": kalan_dusulecek, "paket_id": None})
                                        kalan_dusulecek = 0
                                    else:
                                        dusulen = float(g["kalan"])
                                        g["kalan"] = 0.0
                                        item_tutar += dusulen * g_birim_f
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen, "paket_id": None})
                                        item_partiler.append({"fatura_id": g["id"], "dusulen_miktar": dusulen, "paket_id": None})
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
                                    "partiler": list(item_partiler),
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
                                "uretim_id": uretim_islem_id,
                                "tarih": f"{uretim_tarih_str} 12:00",
                                "urun": urun,
                                "tur": f"Günlük Kullanım ({yemek_adi})",
                                "miktar": istenen,
                                "tutar": item_tutar,
                                "partiler": list(item_partiler),
                                "islem_yapan": st.session_state.aktif_kullanici,
                            }
                            st.session_state.kullanim_loglari.append(log_obj)
                            eklenen_loglar.append(log_obj)

                        gercek_toplam_maliyet = sum(
                            float(m.get("tutar", 0) or 0) for m in arsiv_malzemeler
                        )

                        arsiv_obj = {
                            "uretim_id": uretim_islem_id,
                            "tarih": uretim_tarih_str,
                            "zaman": tarih_simdi,
                            "yemek_adi": yemek_adi,
                            "menu_ana_yemek": ana_yemek_ad.strip() if ana_yemek_ad.strip() else None,
                            "menu_yardimci_yemek": yardimci_yemek_ad.strip() if yardimci_yemek_ad.strip() else None,
                            "menu_corba": corba_ad.strip() if corba_ad.strip() else None,
                            "menu_tatli_meyve_yogurt": tatli_meyve_yogurt_ad.strip() if tatli_meyve_yogurt_ad.strip() else None,
                            "kisi_sayisi": kisi_sayisi,
                            "numune_durumu": numune_durumu,
                            "malzemeler": arsiv_malzemeler,
                            "partiler": [
                                {
                                    "fatura_id": d["id"],
                                    "dusulen_miktar": d["miktar"],
                                    "paket_id": d.get("paket_id"),
                                }
                                for d in dusulen_kayitlar
                            ],
                            "toplam_maliyet": gercek_toplam_maliyet,
                            "toplam_kalori": toplam_kalori,
                            "kisi_basi_kalori": (
                                toplam_kalori / kisi_sayisi if kisi_sayisi > 0 else 0.0
                            ),
                            "islem_yapan": st.session_state.aktif_kullanici,
                        }
                        st.session_state.yemek_uretim_arsivi.append(arsiv_obj)

                        st.session_state["son_yemek_uretim_kaydi"] = {
                            "yemek_adi": yemek_adi,
                            "kisi_sayisi": kisi_sayisi,
                            "toplam_maliyet": gercek_toplam_maliyet,
                            "tarih": uretim_tarih_str,
                            "menu_ana_yemek": ana_yemek_ad.strip() if ana_yemek_ad.strip() else None,
                            "menu_yardimci_yemek": yardimci_yemek_ad.strip() if yardimci_yemek_ad.strip() else None,
                            "menu_corba": corba_ad.strip() if corba_ad.strip() else None,
                            "menu_tatli_meyve_yogurt": tatli_meyve_yogurt_ad.strip() if tatli_meyve_yogurt_ad.strip() else None,
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

            if not salt_okunur_modu:
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
                        "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                        "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                        "Çorba": u_kayit.get("menu_corba", "-"),
                        "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                        "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                    })
                    excel_arsiv_listesi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                        "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                        "Çorba": u_kayit.get("menu_corba", "-"),
                        "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                        "Numune Durumu": u_kayit.get("numune_durumu", "-"),
                    })
                else:
                    for m in u_kayit.get("malzemeler", []):
                        arsiv_tablo_verisi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                            "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                            "Çorba": u_kayit.get("menu_corba", "-"),
                            "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"),
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
                            "Ana Yemek": u_kayit.get("menu_ana_yemek", "-"),
                            "Ara Yemek / Tatlı": u_kayit.get("menu_yardimci_yemek", "-"),
                            "Çorba": u_kayit.get("menu_corba", "-"),
                            "Tatlı / Meyve / Yoğurt": u_kayit.get("menu_tatli_meyve_yogurt", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Numune Durumu": u_kayit.get("numune_durumu", "-"),
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

    # 6. MALZEME Kullanım Uyarısı Algoritması
    # ========================================
    st.markdown("---")
    st.subheader("⚠️ Malzeme Kullanım Uyarısı (Geçmiş Veri Karşılaştırması)")

    if "malzeme_uyari_aktif" not in st.session_state:
        st.session_state.malzeme_uyari_aktif = True

    # Maskelenmiş alan kontrolü - aktif_k_maskeleri bir liste olabilir
    aktif_maskeler = aktif_k_maskeleri if isinstance(aktif_k_maskeleri, list) else []

    if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" not in aktif_maskeler:
        if st.session_state.yemek_uretim_arsivi:
            # Son yemek kaydını kontrol et
            son_yemek = st.session_state.yemek_uretim_arsivi[-1] if st.session_state.yemek_uretim_arsivi else None

            if son_yemek and st.session_state.malzeme_uyari_aktif:
                menu_ogeleri = {
                    "ana_yemek": son_yemek.get("menu_ana_yemek") or "",
                    "yardimci_yemek": son_yemek.get("menu_yardimci_yemek") or "",
                    "corba": son_yemek.get("menu_corba") or "",
                    "tatli_meyve_yogurt": son_yemek.get("menu_tatli_meyve_yogurt") or "",
                }
                if not any(menu_ogeleri.values()):
                    menu_ogeleri = son_yemek.get("yemek_adi", "")

                kisi_sayisi_uyari = son_yemek.get("kisi_sayisi", 0)
                istatistikler = yemek_malzeme_kullanim_istatistikleri(
                    st.session_state.yemek_uretim_arsivi,
                    menu_ogeleri,
                    kisi_sayisi_uyari,
                    son_yemek.get("tarih"),
                    son_yemek.get("zaman"),
                )
                birimler = {
                    "".join(str(item.get("urun", "")).split()).upper(): item.get("birim", "")
                    for item in son_yemek.get("malzemeler", [])
                    if isinstance(item, dict) and item.get("urun")
                }
                uyarilar = yemek_malzeme_kullanim_uyarilari(
                    istatistikler,
                    son_yemek.get("malzemeler", []),
                    kisi_sayisi_uyari,
                    birimler,
                )

                if uyarilar:
                    st.warning("🔍 **Malzeme Kullanım Uyarısı** (Kişi başı geçmiş ortalaması, tolerans: %±10)")
                    for uyari in uyarilar[:5]:
                        st.markdown(uyari)

                    if len(uyarilar) > 5:
                        st.caption(f"... ve {len(uyarilar) - 5} daha fazla uyarı")

    # 7. MENÜ GÜNCELLEME ARACI (ADMIN)
    # =====================================
    # Maskelenmiş alan kontrolü - aktif_k_maskeleri bir liste olabilir
    aktif_maskeler = aktif_k_maskeleri if isinstance(aktif_k_maskeleri, list) else []

    if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" not in aktif_maskeler:
        if yonetici_modu:
            with st.expander("🔧 Menü Düzenleme ve Güncelleme Aracı"):
                st.markdown("**Varolan yemek kayıtlarını güncelleyebilirsiniz.**")
                st.markdown("Bu araç yalnızca **admin** kullanıcılar için görünürdür.")

                # Mevcut kayıtları listele
                uretim_arsivi = st.session_state.yemek_uretim_arsivi if "yemek_uretim_arsivi" in st.session_state else []
                if not uretim_arsivi:
                    st.info("Henüz kayıtlı yemek üretim kaydı bulunmuyor.")
                else:
                    # Tarih aralığı filtresi
                    col_filt1, col_filt2 = st.columns(2)
                    with col_filt1:
                        filtre_tarih = st.date_input(
                            "📅 Tarih Süzgesi (İsteğe bağlı)",
                            value=None,
                            key="menu_guncelle_tarih_filt"
                        )
                    with col_filt2:
                        if st.button("🔄 Tümünü Yeniden Düzenle", key="btn_yeniden_duzelt_tum"):
                            # Tüm kayıtları yeni formata çevir
                            for kayit in uretim_arsivi:
                                if kayit.get("yemek_adi") and not kayit.get("menu_ana_yemek"):
                                    eski_yemek = kayit.get("yemek_adi", "")
                                    kayit["menu_ana_yemek"] = eski_yemek
                                    kayit["menu_yardimci_yemek"] = None
                                    kayit["menu_corba"] = None
                                    kayit["menu_tatli_meyve_yogurt"] = None
                                    kayit["menu_ana_yemek"] = eski_yemek
                            st.success(f"✅ {len(uretim_arsivi)} kayıt yeni formata çevrildi!")
                            yemek_uretim_arsivini_kaydet(uretim_arsivi)
                            st.rerun()

                    # Kayıtları filtrele
                    gosterilecek_kayitlar = uretim_arsivi
                    if filtre_tarih:
                        gosterilecek_kayitlar = [
                            k for k in uretim_arsivi
                            if k.get("tarih") == filtre_tarih.strftime("%Y-%m-%d")
                        ]

                    if not gosterilecek_kayitlar:
                        st.info("Seçilen tarihte kayıt bulunmuyor.")
                    else:
                        st.markdown(f"🗂️ **{len(gosterilecek_kayitlar)} kayıt bulundu**")

                        # Her kayıt için düzenleme
                        for idx, kayit in enumerate(gosterilecek_kayitlar):
                            tarih = kayit.get("tarih", "-")
                            eski_yemek = kayit.get("yemek_adi", "")

                            # Eğer zaten yeni formattaysa göster
                            zaten_yeni_format = any([
                                kayit.get("menu_ana_yemek"),
                                kayit.get("menu_yardimci_yemek"),
                                kayit.get("menu_corba"),
                                kayit.get("menu_tatli_meyve_yogurt")
                            ])

                            if zaten_yeni_format:
                                # Yeni format - mevcut değerleri göster
                                col1, col2, col3, col4, col_btn = st.columns([2, 2, 2, 2, 1])
                                with col1:
                                    yeni_ana = st.text_input(
                                        f"🥘 Ana Yemek ({tarih})",
                                        value=kayit.get("menu_ana_yemek", ""),
                                        key=f"duz_alt_{idx}",
                                        label_visibility="collapsed"
                                    )
                                with col2:
                                    yeni_yardimci = st.text_input(
                                        f"🍛 Ara Yemek ({tarih})",
                                        value=kayit.get("menu_yardimci_yemek", ""),
                                        key=f"duz_aryad_{idx}",
                                        label_visibility="collapsed"
                                    )
                                with col3:
                                    yeni_corba = st.text_input(
                                        f"🍲 Çorba ({tarih})",
                                        value=kayit.get("menu_corba", ""),
                                        key=f"duz_corba_{idx}",
                                        label_visibility="collapsed"
                                    )
                                with col4:
                                    yeni_tatlilar = st.text_input(
                                        f"🍨 Tatlı/Meyve/Yoğurt ({tarih})",
                                        value=kayit.get("menu_tatli_meyve_yogurt", ""),
                                        key=f"duz_tatlilar_{idx}",
                                        label_visibility="collapsed"
                                    )
                                with col_btn:
                                    if st.button("💾 Kaydet", key=f"btn_kaydet_{idx}"):
                                        kayit["menu_ana_yemek"] = yeni_ana.strip() or None
                                        kayit["menu_yardimci_yemek"] = yeni_yardimci.strip() or None
                                        kayit["menu_corba"] = yeni_corba.strip() or None
                                        kayit["menu_tatli_meyve_yogurt"] = yeni_tatlilar.strip() or None
                                        # yemek_adi'yi güncelle
                                        bolumler = []
                                        if yeni_ana.strip():
                                            bolumler.append(f"Ana Yemek: {yeni_ana.strip()}")
                                        if yeni_yardimci.strip():
                                            bolumler.append(f"Ara Yemek / Tatlı: {yeni_yardimci.strip()}")
                                        if yeni_corba.strip():
                                            bolumler.append(f"Çorba: {yeni_corba.strip()}")
                                        if yeni_tatlilar.strip():
                                            bolumler.append(f"Tatlı / Meyve / Yoğurt: {yeni_tatlilar.strip()}")
                                        kayit["yemek_adi"] = "; ".join(bolumler) if bolumler else eski_yemek

                                        yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                        st.success(f"✅ {tarih} tarihli kayıt güncellendi!")
                                        st.rerun()

                                # Sil butonu
                                if st.button("🗑️ Sil", key=f"btn_sil_{idx}", type="secondary"):
                                    uretim_arsivi.remove(kayit)
                                    yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                    st.warning(f"🗑️ {tarih} tarihli kayıt silindi!")
                                    st.rerun()

                            else:
                                # Eski format - tek alanlı göster ve düzenle
                                col_old1, col_old2, col_old3 = st.columns([3, 3, 1])
                                with col_old1:
                                    st.markdown(f"**📅 {tarih}**")
                                    st.markdown(f"Eski kayıt: `{eski_yemek}`")

                                with col_old2:
                                    st.markdown("### 4'lü formatta dönüştür:")
                                    c_a, c_b, c_c, c_d = st.columns(4)
                                    with c_a:
                                        yeni_ana = st.text_input("Ana Yemek", key=f"cevir_alt_{idx}", label_visibility="collapsed")
                                    with c_b:
                                        yeni_yardimci = st.text_input("Ara Yemek", key=f"cevir_aryad_{idx}", label_visibility="collapsed")
                                    with c_c:
                                        yeni_corba = st.text_input("Çorba", key=f"cevir_corba_{idx}", label_visibility="collapsed")
                                    with c_d:
                                        yeni_tatlilar = st.text_input("Tatlı/Meyve", key=f"cevir_tatlilar_{idx}", label_visibility="collapsed")

                                with col_old3:
                                    if st.button("🔄 Çevir", key=f"btn_cevir_{idx}"):
                                        kayit["menu_ana_yemek"] = yeni_ana.strip() or None
                                        kayit["menu_yardimci_yemek"] = yeni_yardimci.strip() or None
                                        kayit["menu_corba"] = yeni_corba.strip() or None
                                        kayit["menu_tatli_meyve_yogurt"] = yeni_tatlilar.strip() or None

                                        bolumler = []
                                        if yeni_ana.strip():
                                            bolumler.append(f"Ana Yemek: {yeni_ana.strip()}")
                                        if yeni_yardimci.strip():
                                            bolumler.append(f"Ara Yemek / Tatlı: {yeni_yardimci.strip()}")
                                        if yeni_corba.strip():
                                            bolumler.append(f"Çorba: {yeni_corba.strip()}")
                                        if yeni_tatlilar.strip():
                                            bolumler.append(f"Tatlı / Meyve / Yoğurt: {yeni_tatlilar.strip()}")
                                        kayit["yemek_adi"] = "; ".join(bolumler) if bolumler else eski_yemek

                                        yemek_uretim_arsivini_kaydet(uretim_arsivi)
                                        st.success(f"✅ {tarih} kaydı yeni formata çevrildi!")
                                        st.rerun()
