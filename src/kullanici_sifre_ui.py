def kendi_sifre_sekmesini_goster(sekme_s, st, kullanici_db, sifre_dogrula, sifre_politika_hatasi, sifre_degistir):
    # ------------------------------------------------ Kendi şifrem
    with sekme_s:
        st.subheader("🔑 Kendi Şifrenizi Değiştirin")
        with st.form("admin_sifre_degistir_formu"):
            eski_s = st.text_input("Mevcut Şifre", type="password")
            yeni_s1 = st.text_input("Yeni Şifre", type="password")
            yeni_s2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
            if st.form_submit_button("Şifremi Değiştir", type="primary"):
                _ben = st.session_state.aktif_kullanici
                if not sifre_dogrula(eski_s, kullanici_db.get(_ben, {}).get("sifre", "")):
                    st.error("Mevcut şifre hatalı.")
                elif sifre_politika_hatasi(yeni_s1):
                    st.error(sifre_politika_hatasi(yeni_s1))
                elif yeni_s1 != yeni_s2:
                    st.error("Yeni şifreler aynı değil.")
                elif yeni_s1 == eski_s:
                    st.error("Yeni şifre eskisiyle aynı olamaz.")
                else:
                    sifre_degistir(_ben, yeni_s1, haric_token=st.session_state.oturum_token)
                    st.success("Şifreniz değiştirildi. Diğer cihazlardaki oturumlarınız kapatıldı.")
