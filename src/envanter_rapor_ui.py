def kapsamli_envanter_rapor_sayfasi(st, misafir_modu, girisler, kapsamli_envanter_liste_olustur, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_env, col_indir_env = st.columns([2, 2])
        with col_b_env:
            st.header("📋 Kapsamlı Envanter ve Hareket Raporu")

        kapsamli_liste = kapsamli_envanter_liste_olustur(girisler)

        excel_kapsamli_data = tablo_to_excel_bytes(
            kapsamli_liste, "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu"
        )
        pdf_kapsamli_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu", kapsamli_liste
        )

        with col_indir_env:
            ortak_indirme_alani(
                excel_kapsamli_data,
                pdf_kapsamli_data,
                "kapsamli_envanter_ve_hareket_raporu",
                "kapsamli_envanter_sayfasi",
            )

        if kapsamli_liste:
            ozel_html_tablo_goster(kapsamli_liste)
        else:
            st.info("Kapsamlı rapor için kayıt bulunmuyor.")

