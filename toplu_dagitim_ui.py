import time

def toplu_yemek_dagitimi_tabini_goster(tab2, st, aktif_k_maskeleri, yonetim_modu, html_escape, simdi_tr_str, yeni_id_uret, dagitim_loglarini_kaydet, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    with tab2:
        col_b_dag, col_indir_dag = st.columns([2, 2])
        with col_b_dag:
            st.subheader("🍲 Toplu Yemek Dağıtımı Girişi ve Yönetimi")

        if st.session_state.dagitim_silme_mesaji:
            st.success(st.session_state.dagitim_silme_mesaji)
            st.session_state.dagitim_silme_mesaji = ""

        aktif_ihtiyac_sahipleri = [k for k in st.session_state.ihtiyac_sahipleri if k.get("aktif", True)]

        if yonetim_modu:
            st.info("👀 Yönetim modundasınız. Bu ekranda yeni dağıtım kaydı oluşturamazsınız.")
        elif not aktif_ihtiyac_sahipleri:
            st.warning("Aktif durumda kayıtlı ihtiyaç sahibi bulunmuyor.")
        else:
            st.markdown("##### ⚡ Toplu Dağıtım Paneli (Aktif Vatandaşlar)")
            with st.form("toplu_dagitim_formu"):
                menu_adi_toplu = st.text_input(
                    "Dağıtılacak Ortak Menü / Yemek Adı", "Yemeğin Adını Giriniz..."
                )
                st.markdown("---")
                st.markdown("**Aktif İhtiyaç Sahibi Listesi ve Porsiyon Belirleme**")

                secim_verileri = []
                for idx, k in enumerate(aktif_ihtiyac_sahipleri):
                    c1, c2, c3 = st.columns([0.5, 2.5, 1])
                    with c1:
                        secili_mi = st.checkbox("Seç", value=True, key=f"toplu_sec_{idx}", label_visibility="collapsed")
                    with c2:
                        st.markdown(f"**{html_escape(str(k['ad_soyad']))}** <span style='font-size:12px; opacity:0.6;'>(Hane/T.C: {html_escape(str(k.get('tc_hane', '-')))})</span>", unsafe_allow_html=True)
                    with c3:
                        varsayilan_porsiyon = int(k.get("birey_sayisi", 1))
                        pors_val = st.number_input("Porsiyon", min_value=1, value=varsayilan_porsiyon, key=f"toplu_pors_{idx}", label_visibility="collapsed")

                    secim_verileri.append({
                        "kisi": k["ad_soyad"],
                        "secili": secili_mi,
                        "porsiyon": pors_val
                    })

                st.markdown("---")
                toplu_kaydet_btn = st.form_submit_button("🚀 Seçilen Tüm Hanelere Toplu Dağıtımı Onayla ve Kaydet", type="primary")

                if toplu_kaydet_btn:
                    d_tarih_saat = simdi_tr_str("%Y-%m-%d %H:%M")
                    eklenen_sayisi = 0
                    eklenen_id_listesi = []

                    for sv in secim_verileri:
                        if sv["secili"]:
                            yeni_dag_id = yeni_id_uret("DAG-", st.session_state.dagitim_loglari)
                            st.session_state.dagitim_loglari.append({
                                "id": yeni_dag_id,
                                "tarih": d_tarih_saat,
                                "kisi": sv["kisi"],
                                "menu": menu_adi_toplu,
                                "porsiyon": sv["porsiyon"],
                                "islem_yapan": st.session_state.aktif_kullanici,
                            })
                            eklenen_id_listesi.append(yeni_dag_id)
                            eklenen_sayisi += 1

                    st.session_state["son_toplu_dagitim_kaydi"] = {
                        "tarih": d_tarih_saat,
                        "menu": menu_adi_toplu,
                        "sayi": eklenen_sayisi,
                        "eklenen_id_listesi": eklenen_id_listesi
                    }

                    dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                    st.success(f"🎉 Başarılı! Seçilen {eklenen_sayisi} haneye yemek dağıtımı işlendi.")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Kayıtlı Yemek Dağıtımları Tablosu")

        dagitim_gosterim_listesi = []
        for idx, d in enumerate(st.session_state.dagitim_loglari):
            tarih_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Tarih/Saat" in aktif_k_maskeleri else d.get("tarih", "-")
            kisi_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Kişi/Hane" in aktif_k_maskeleri else d.get("kisi", "-")
            menu_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Menü" in aktif_k_maskeleri else d.get("menu", "-")
            porsiyon_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Porsiyon" in aktif_k_maskeleri else d.get("porsiyon", 1)

            dagitim_gosterim_listesi.append({
                "Kayıt No": d.get("id", f"DAG-{idx+1:03d}"),
                "Tarih / Saat": tarih_maskele_d,
                "Kişi / Hane": kisi_maskele_d,
                "Menü": menu_maskele_d,
                "Porsiyon": porsiyon_maskele_d,
                "İşlemi Yapan": d.get("islem_yapan", "admin"),
            })

        excel_dag_data = tablo_to_excel_bytes(
            dagitim_gosterim_listesi, "Aziziye Aşevi - Yemek Dağıtım Listesi"
        )
        pdf_dag_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Yemek Dağıtım Listesi", dagitim_gosterim_listesi
        )

        with col_indir_dag:
            ortak_indirme_alani(
                excel_dag_data,
                pdf_dag_data,
                "yemek_dagitim_listesi",
                "dagitim_sayfasi",
            )

        if dagitim_gosterim_listesi:
            ozel_html_tablo_goster(dagitim_gosterim_listesi)
        else:
            st.info("Kayıtlı yemek dağıtımı bulunmuyor.")
