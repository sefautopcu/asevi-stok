import datetime
import zoneinfo

def dagitim_sayac_tabini_goster(tab3, st, aktif_k_maskeleri, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    with tab3:
        col_b_sayac, col_indir_sayac = st.columns([2, 2])
        with col_b_sayac:
            st.subheader("📊 Kişi Bazlı Günlük, Haftalık ve Aylık Sayaç Raporu")

        simdi_dt = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")) if hasattr(datetime, "datetime") else datetime.datetime.now()
        bugun_str = simdi_dt.strftime("%Y-%m-%d")
        yedi_gun_once = (simdi_dt - datetime.timedelta(days=7)).date()
        bu_yil_ay = simdi_dt.strftime("%Y-%m")

        sayac_tablosu = []
        excel_sayac_liste = []

        for k in st.session_state.ihtiyac_sahipleri:
            kisi_adi = k["ad_soyad"]
            k_loglari = [
                d
                for d in st.session_state.dagitim_loglari
                if d.get("kisi") == kisi_adi
            ]

            gunluk_sefer = 0
            gunluk_porsiyon = 0
            haftalik_sefer = 0
            haftalik_porsiyon = 0
            aylik_sefer = 0
            aylik_porsiyon = 0

            for d in k_loglari:
                tarih_saat_str = d.get("tarih", "")
                pors = int(d.get("porsiyon", 1))
                if not tarih_saat_str:
                    continue
                try:
                    d_tarih = datetime.datetime.strptime(
                        tarih_saat_str.split()[0], "%Y-%m-%d"
                    ).date()
                except:
                    continue

                if tarih_saat_str.startswith(bugun_str):
                    gunluk_sefer += 1
                    gunluk_porsiyon += pors

                if yedi_gun_once <= d_tarih <= simdi_dt.date():
                    haftalik_sefer += 1
                    haftalik_porsiyon += pors

                if tarih_saat_str.startswith(bu_yil_ay):
                    aylik_sefer += 1
                    aylik_porsiyon += pors

            tc_hane_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "-")
            kisi_ad_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - İhtiyaç Sahibi" in aktif_k_maskeleri else kisi_adi
            gunluk_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Günlük Alım" in aktif_k_maskeleri else f"{gunluk_sefer} Kez / {gunluk_porsiyon} Pors."
            haftalik_maskele = "🔒 Gizli" if "4. Sayfa: Haftalık Alım" in aktif_k_maskeleri else f"{haftalik_sefer} Kez / {haftalik_porsiyon} Pors."
            aylik_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Aylık Alım" in aktif_k_maskeleri else f"{aylik_sefer} Kez / {aylik_porsiyon} Pors."

            sayac_tablosu.append({
                "T.C. / Hane No": tc_hane_maskele,
                "İhtiyaç Sahibi": kisi_ad_maskele,
                "Günlük Alım (Kez / Porsiyon)": gunluk_maskele,
                "Haftalık Alım (Kez / Porsiyon)": haftalik_maskele,
                "Aylık Alım (Kez / Porsiyon)": aylik_maskele,
            })

            excel_sayac_liste.append({
                "T.C. / Hane No": tc_hane_maskele,
                "İhtiyaç Sahibi": kisi_ad_maskele,
                "Günlük Kez": gunluk_sefer,
                "Günlük Porsiyon": gunluk_porsiyon,
                "Haftalık Kez": haftalik_sefer,
                "Haftalık Porsiyon": haftalik_porsiyon,
                "Aylık Kez": aylik_sefer,
                "Aylık Porsiyon": aylik_porsiyon,
            })

        excel_sayac_data = tablo_to_excel_bytes(
            excel_sayac_liste,
            "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
        )
        pdf_sayac_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
            excel_sayac_liste,
        )

        with col_indir_sayac:
            ortak_indirme_alani(
                excel_sayac_data,
                pdf_sayac_data,
                "kisi_bazli_yemek_sayac_raporu",
                "sayac_sayfasi",
            )

        if sayac_tablosu:
            ozel_html_tablo_goster(sayac_tablosu)
        else:
            st.info("Listelenecek ihtiyaç sahibi veya dağıtım verisi bulunmuyor.")
