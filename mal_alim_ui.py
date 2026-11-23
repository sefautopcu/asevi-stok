import datetime
import difflib
import time

def mal_alimi_sayfasi(st, salt_okunur_modu, otomatik_yedek_al, verileri_kaydet, yeni_id_uret, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    if salt_okunur_modu:
        st.warning(
            "⚠️ Bu sayfaya yalnızca gözlem amaçlı erişebilirsiniz. Salt okunur (Yönetim/Misafir) modda işlem yapamazsınız."
        )
    else:
        st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
        st.markdown("Her yeni mal alımı ayrı bir kayıt olarak depoya eklenir; böylece aynı ürün eklendiğinde stoğunuz artar ve geçmiş alım fiyatlarınız/tarihçeniz korunur.")
    
        # Son Eklenen İşlemi Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_eklenen_fatura_id"):
            son_id = st.session_state["son_eklenen_fatura_id"]
            son_fatura = next((g for g in st.session_state.girisler if g.get("id") == son_id), None)
            if son_fatura:
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Eklenen Kayıt:** {son_fatura.get('urun')} ({son_fatura.get('miktar')} {son_fatura.get('birim')} - Fatura No: {son_fatura.get('fatura_no')})")
                with c_undo2:
                    if st.button("↩️ Son Mal Alımını Geri Al", type="secondary", key="btn_undo_fatura_son"):
                        otomatik_yedek_al("Fatura ekleme geri alma: " + str(son_id))
                        st.session_state.girisler = [g for g in st.session_state.girisler if g.get("id") != son_id]
                        verileri_kaydet(st.session_state.girisler)
                        st.session_state.pop("son_eklenen_fatura_id", None)
                        st.success(f"🎉 {son_id} numaralı mal alım kaydı başarıyla geri alındı ve silindi!")
                        time.sleep(1)
                        st.rerun()

        with st.form("fatura_formu"):
            fatura_tarihi_secim = st.date_input("📅 Fatura / Alım Tarihi", value=datetime.date.today())
            fatura_saati_secim = st.time_input("⏰ Alım Saati", value=datetime.datetime.now().time())
            tarih_giris = f"{fatura_tarihi_secim.strftime('%Y-%m-%d')} {fatura_saati_secim.strftime('%H:%M')}"

            fatura_no_input = st.text_input(
                "Fatura No / Belge No (Örn: FAT-2026-105)"
            ).strip().upper()
        
            mevcut_urun_listesi = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
        
            yeni_urun_secimi = st.checkbox("➕ Listede Olmayan Yepyeni Bir Ürün Ekle")
        
            if yeni_urun_secimi or not mevcut_urun_listesi:
                urun = st.text_input(
                    "Yeni Ürün Adı (Örn: KIRMIZI MERCİMEK - Büyük Harfle)"
                ).strip().upper()
            else:
                urun = st.selectbox(
                    "Mevcut Ürünlerden Seçin",
                    mevcut_urun_listesi,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="fatura_urun_selectbox"
                )

            kategori = st.selectbox(
                "Kategori",
                [
                    "SEBZE",
                    "MEYVE",
                    "KURU GIDA",
                    "BAHARAT",
                    "SÜT/SÜT ÜRÜNLERİ",
                    "KASAP / ŞARKÜTERİ",
                    "YAĞ",
                ],
            )
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"])
        
            skt_tarihi = st.date_input("📅 Son Tüketim Tarihi (SKT / STT) - Zorunlu", value=None)

            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)
        
            # YENİ EKLENEN: Paket Başına Miktar
            paket_miktari_input = st.number_input("Paket Başına Miktar (Kg/Lt) - Dökme ise 0", min_value=0.0, value=0.0, step=1.0, help="Eğer ürün paketli geliyorsa (örn: 2.5 kg un), buraya paket ağırlığını yazın. Dökme ürünler için 0 bırakın.")

            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted:
                if not urun:
                    st.error("⚠️ Lütfen listeden bir ürün seçin veya yeni bir ürün adı girin!")
                elif skt_tarihi is None:
                    st.error("⚠️ Lütfen ürünün Son Tüketim Tarihini (SKT/STT) seçin! Bu alan zorunludur.")
                else:
                    urun_temiz = urun.strip().upper()
                
                    if yeni_urun_secimi and mevcut_urun_listesi:
                        benzerler = difflib.get_close_matches(urun_temiz, mevcut_urun_listesi, n=1, cutoff=0.7)
                        if benzerler:
                            st.warning(f"⚠️ Dikkat! Yazdığınız ürün mevcut '{benzerler[0]}' adına çok benziyor.")

                    islem_yapan_kisi = st.session_state.aktif_kullanici
                    fatura_no_degeri = fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
                    yeni_kayit_id = yeni_id_uret("FAT-", st.session_state.girisler)
                
                    yeni_kayit_obj = {
                        "id": yeni_kayit_id,
                        "tarih": tarih_giris,
                        "fatura_no": fatura_no_degeri,
                        "urun": urun_temiz,
                        "kategori": kategori,
                        "birim": birim,
                        "miktar": miktar,
                        "kalan": miktar,
                        "birim_fiyat": fiyat,
                        "fiyat": fiyat*miktar,    
                        "paket_miktari": paket_miktari_input, # YENİ EKLENDİ
                        "depo": depo,
                        "skt": str(skt_tarihi),
                        "islem_yapan": islem_yapan_kisi,
                    }
                
                    st.session_state.girisler.append(yeni_kayit_obj)
                    st.session_state["son_eklenen_fatura_id"] = yeni_kayit_id
                    verileri_kaydet(st.session_state.girisler)
                
                    st.markdown(
                    """
                    <div style="background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; padding: 14px 18px; border-radius: 14px; margin: 16px 0; font-weight: 600; font-size: 15px;">
                    🎉 Başarılı! Yeni mal alımı faturası ve ürün SKT/STT tarihi ile birlikte depoya eklendi.
                    </div>
                    """,
                    unsafe_allow_html=True
                    )
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        # --- KAYIT GÜNCELLEME (DÜZENLEME) BÖLÜMÜ ---
        st.markdown("---")
        with st.expander("✏️ Hatalı / Eksik Kaydı Güncelle (Silmeden Düzelt)"):
            if not st.session_state.girisler:
                st.info("Sistemde güncellenecek kayıt bulunmuyor.")
            else:
                secenekler_guncelle = [
                    f"{g['id']} - {g['urun']} (Fatura: {g.get('fatura_no', '-')}, Kalan: {g.get('kalan', 0)} {g.get('birim', '')})"
                    for g in st.session_state.girisler
                ]
                secilen_kayit_guncelle = st.selectbox(
                    "Güncellenecek Kaydı Seçin", 
                    secenekler_guncelle, 
                    index=None, 
                    placeholder="Düzeltilecek fatura/ürünü seçin...",
                    key="gncl_secim_box"
                )

                if secilen_kayit_guncelle:
                    secilen_id_g = secilen_kayit_guncelle.split(" - ")[0]
                    ilgili_g = next((g for g in st.session_state.girisler if g["id"] == secilen_id_g), None)

                    if ilgili_g:
                        st.markdown(f"**Kayıt ID:** `{ilgili_g['id']}` | **İlk Giriş Tarihi:** `{ilgili_g.get('tarih', '-')}`")
                    
                        c_g1, c_g2, c_g3 = st.columns(3)
                        with c_g1:
                            g_fatura_no = st.text_input("Fatura No", value=ilgili_g.get("fatura_no", ""), key="g_fat_no")
                            g_miktar = st.number_input("Toplam Miktar", min_value=0.1, value=float(ilgili_g.get("miktar", 1.0)), step=1.0, key="g_miktar")
                            g_paket_miktari = st.number_input("Paket Başına Miktar (Kg/Lt - Dökme ise 0)", min_value=0.0, value=float(ilgili_g.get("paket_miktari", 0.0)), step=1.0, key="g_paket")
                        with c_g2:
                            mevcut_kategoriler = ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"]
                            if ilgili_g.get("kategori") and ilgili_g.get("kategori") not in mevcut_kategoriler:
                                mevcut_kategoriler.append(ilgili_g.get("kategori"))
                            kat_idx = mevcut_kategoriler.index(ilgili_g.get("kategori")) if ilgili_g.get("kategori") in mevcut_kategoriler else 0
                            g_kategori = st.selectbox("Kategori", mevcut_kategoriler, index=kat_idx, key="g_kategori")
                        
                            birimler = ["Kg", "Adet", "Lt"]
                            brm_idx = birimler.index(ilgili_g.get("birim")) if ilgili_g.get("birim") in birimler else 0
                            g_birim = st.selectbox("Birim", birimler, index=brm_idx, key="g_birim")
                        with c_g3:
                            g_fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, value=float(ilgili_g.get("fiyat", 0.01)), step=0.1, key="g_fiyat")
                        
                            depolar_list = st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"]
                            depo_idx = depolar_list.index(ilgili_g.get("depo")) if ilgili_g.get("depo") in depolar_list else 0
                            g_depo = st.selectbox("Depo Yeri", depolar_list, index=depo_idx, key="g_depo")

                        skt_mevcut = ilgili_g.get("skt")
                        try:
                            skt_dt_obj = datetime.datetime.strptime(skt_mevcut, "%Y-%m-%d").date() if skt_mevcut else None
                        except:
                            skt_dt_obj = None
                        g_skt = st.date_input("📅 Son Tüketim Tarihi (SKT / STT)", value=skt_dt_obj, key="g_skt")

                        if st.button("Değişiklikleri Kaydet", type="primary", key="g_kaydet_btn"):
                            eski_miktar = float(ilgili_g.get("miktar", 1.0))
                            eski_kalan = float(ilgili_g.get("kalan", 1.0))
                            fark = g_miktar - eski_miktar
                            yeni_kalan = eski_kalan + fark
                        
                            if yeni_kalan < 0:
                                st.error(f"⚠️ Hata: Yeni miktar, stokta kalan miktardan ({eski_kalan}) daha az olamaz!")
                            else:
                                ilgili_g["fatura_no"] = g_fatura_no if g_fatura_no else "BELİRTİLMEMİŞ"
                                ilgili_g["miktar"] = g_miktar
                                ilgili_g["kalan"] = yeni_kalan
                                ilgili_g["fiyat"] = g_fiyat
                                ilgili_g["kategori"] = g_kategori
                                ilgili_g["birim"] = g_birim
                                ilgili_g["depo"] = g_depo
                                ilgili_g["skt"] = str(g_skt) if g_skt else ""
                            
                                if ilgili_g.get("paket_miktari") != g_paket_miktari:
                                    ilgili_g["paket_miktari"] = g_paket_miktari
                                    ilgili_g.pop("paket_durumlari", None)

                                verileri_kaydet(st.session_state.girisler)
                                st.success("🎉 Başarılı! Kayıt başarıyla güncellendi.")
                                time.sleep(1)
                                st.rerun()

        # --- FATURA ARŞİVİ TABLOSU ---
        st.markdown("---")
        st.subheader("📋 Kayıtlı Fatura ve Mal Alım Arşivi")
    
    if st.session_state.girisler:
        fatura_tablo_verisi = []
        for g in reversed(st.session_state.girisler):
            try:
                # 1. Paket bilgisini güvenli hesapla
                paket_bilgi = "Dökme (Paketsiz)"
                try:
                    paket_miktari = float(g.get("paket_miktari") or 0)
                    if paket_miktari > 0:
                        durumlar = g.get("paket_durumlari", {})
                        paket_sayisi = int(float(g.get("miktar") or 0) // paket_miktari)
                        ozet_liste = []
                        for i in range(1, paket_sayisi + 1):
                            p_id = f"{g.get('id')}-P{i}"
                            if p_id in durumlar:
                                kalan = durumlar[p_id]
                                if kalan == paket_miktari:
                                    ozet_liste.append(f"P{i}: Tam")
                                elif kalan == 0:
                                    ozet_liste.append(f"P{i}: Bitti")
                                else:
                                    ozet_liste.append(f"P{i}: {kalan} {g.get('birim', '')} kaldı")
                            else:
                                ozet_liste.append(f"P{i}: Tam")
                        paket_bilgi = f"{paket_miktari} {g.get('birim', 'Kg')} | (" + ", ".join(ozet_liste) + ")"
                except Exception:
                    pass # Paket hesabında hata olursa dökme kabul et, döngüyü durdurma

                # 2. Fiyatları güvenli çek (Eski ve Yeni kayıt mantığı)
                try:
                    if g.get("birim_fiyat") is not None:
                        # YENİ KAYIT: Birim fiyat ve toplam tutar ayrı kaydedilmiş
                        birim_fiyat = float(g.get("birim_fiyat") or 0)
                        toplam_tutar = float(g.get("fiyat") or 0)
                    else:
                        # ESKİ KAYIT: Veritabanındaki 'fiyat' aslında Birim Fiyat'tır!
                        birim_fiyat = float(g.get("fiyat") or 0)
                        miktar_degeri = float(g.get("miktar") or 0)
                        toplam_tutar = birim_fiyat * miktar_degeri
                except (ValueError, TypeError):
                    birim_fiyat = 0.0
                    toplam_tutar = 0.0

                # 3. Veriyi tabloya ekle
                fatura_tablo_verisi.append({
                    "Kayıt ID": g.get("id", "-"),
                    "Tarih / Saat": g.get("tarih", "-"),
                    "Fatura No": g.get("fatura_no", "-"),
                    "Ürün Adı": g.get("urun", "-"),
                    "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                    "Paket Yapısı": paket_bilgi,
                    "SKT / STT": g.get("skt", "-"),
                    "Depo": g.get("depo", "-"),
                    "Birim Fiyat": f"{birim_fiyat:,.2f} ₺",
                    "Toplam Tutar": f"{toplam_tutar:,.2f} ₺",
                    "İşlemi Yapan": g.get("islem_yapan", "admin"),
                })
            except Exception as e:
                # Ne olursa olsun sistem çökmesin, diğer ürünlere geçsin
                pass
    
    if fatura_tablo_verisi:
        excel_fatura_data = tablo_to_excel_bytes(fatura_tablo_verisi, "Aziziye Aşevi - Fatura Arşivi")
        pdf_fatura_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Fatura Arşivi", fatura_tablo_verisi)

        col_b_fat, col_indir_fat = st.columns([2, 2])
        with col_indir_fat:
            ortak_indirme_alani(excel_fatura_data, pdf_fatura_data, "fatura_mal_alim_arsivi", "fatura_arsiv_sayfasi")

        ozel_html_tablo_goster(fatura_tablo_verisi)
    else:
        st.info("Sistemde kayıtlı fatura veya mal alımı bulunmuyor.")
