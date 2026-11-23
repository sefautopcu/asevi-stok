def manuel_rapor_gonderim_alani(st, manuel_rapor_maili_gonder):
    st.markdown("### 📧 Manuel Rapor Gönderimi")
    st.caption("Aşağıdaki butonlar sadece o anki verileri size gönderir. Otomatik sabah 08:30 mailini etkilemez.")

    # CSS ile buton tasarımı (Dar, koyu arka plan, yeşil kenarlık ve hover)
    st.markdown("""
    <style>
        /* Buton kapsayıcısını sola yasla ve butonlar arasına boşluk koy */
        div.stButton {
            text-align: left;
            margin-right: 10px;
            display: inline-block;
        }
        /* Butonun Kendi Tasarımı */
        div.stButton > button {
            background-color: #0b1329 !important; /* Koyu Lacivert Arka Plan */
            border: 1px solid #10b981 !important; /* Yeşil Kenarlık */
            border-radius: 20px !important; /* Yuvarlak Köşeler */
            padding: 8px 20px !important;
            color: #10b981 !important; /* Yeşil Yazı */
            font-weight: 600 !important;
            font-size: 14px !important;
            transition: all 0.3s ease !important;
            width: auto !important; /* İçeriği kadar genişlik */
        }
        /* Hover Efekti */
        div.stButton > button:hover {
            background-color: rgba(16, 185, 129, 0.15) !important; /* Hover'da Hafif Yeşil Arka Plan */
            color: #ffffff !important; /* Hover'da Beyaz Yazı */
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.5) !important; /* Işıldama */
            border-color: #34d399 !important; /* Daha Parlak Yeşil Kenarlık */
            transform: translateY(-2px) !important; /* Hafif Yukarı Kayma */
        }
    </style>
    """, unsafe_allow_html=True)

    # Butonları yan yana dizmek için boşluklu columns kullanıyoruz
    c1, c2, c3, _ = st.columns([1.2, 1.2, 1.2, 2])

    with c1:
        if st.button("📅 Dünün Raporunu Gönder", key="btn_manuel_gunluk"):
            st.session_state["manuel_mail_tetik"] = "gunluk"
    with c2:
        if st.button("🗓️ Haftalık Raporu Gönder", key="btn_manuel_haftalik"):
            st.session_state["manuel_mail_tetik"] = "haftalik"
    with c3:
        if st.button("📆 Aylık Raporu Gönder", key="btn_manuel_aylik"):
            st.session_state["manuel_mail_tetik"] = "aylik"

    # Mail Gönderme Tetikleyicisi
    if st.session_state.get("manuel_mail_tetik"):
        mail_tipi = st.session_state.pop("manuel_mail_tetik") 
        with st.spinner(f"{mail_tipi.capitalize()} raporu hazırlanıyor ve gönderiliyor..."):
            if manuel_rapor_maili_gonder(mail_tipi):
                st.success(f"🎉 Rapor başarıyla gönderildi! Lütfen mail kutunuzu kontrol edin.")
            else:
                st.error("❌ Mail gönderilemedi. Lütfen konsol loglarını kontrol edin.")
