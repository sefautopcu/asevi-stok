def giris_kayitlari_sekmesini_goster(sekme_l, st, SUPABASE_URL, SUPABASE_KEY, _supa_basliklar, _supabase_ham_oku, requests, tablo_to_excel_bytes, tablo_to_html_pdf_bytes, ortak_indirme_alani, ozel_html_tablo_goster, giris_denemesini_sifirla, giris_logla):
    with sekme_l:
        st.subheader("📋 Giriş ve Güvenlik Kayıtları (son 200)")

        if not SUPABASE_URL or not SUPABASE_KEY:
            st.info("Kayıtlar için Supabase bağlantısı gerekir.")
        else:
            # Yeni SQL tablosundan son 200 kaydı çek
            try:
                r = requests.get(
                    f"{SUPABASE_URL}/rest/v1/giris_kayitlari",
                    headers=_supa_basliklar(),
                    params={"select": "*", "order": "zaman.desc", "limit": "200"},
                    timeout=10
                )
                giris_kayitlari = r.json() if r.status_code == 200 else []
            except Exception:
                giris_kayitlari = []

            # Eski JSON loglarını da listeye ekle (Geçmiş kayıtlar kaybolmasın diye)
            _, eski_loglar = _supabase_ham_oku("giris_loglari")
            if isinstance(eski_loglar, list):
                for e in eski_loglar:
                    giris_kayitlari.append({
                        "zaman": e.get("zaman", "-"),
                        "kullanici": e.get("kullanici", "-"),
                        "durum": e.get("durum", "-"),
                        "ip": e.get("ip", "-"),
                        "xff": e.get("xff", "")
                    })

            # Tarihe göre yeniden eskiye sırala ve tablo formatına çevir
            giris_kayitlari = sorted(giris_kayitlari, key=lambda x: str(x.get("zaman", "")), reverse=True)[:200]

            log_satirlari = [
                {
                    "Zaman": g.get("zaman", "-"),
                    "Kullanıcı": g.get("kullanici", "-"),
                    "Olay": g.get("durum", "-"),
                    "IP": g.get("ip", "-"),
                    "X-Forwarded-For": g.get("xff", ""),
                }
                for g in giris_kayitlari
            ]

            if log_satirlari:
                ortak_indirme_alani(
                    tablo_to_excel_bytes(log_satirlari, "Aziziye Aşevi - Giriş Kayıtları"),
                    tablo_to_html_pdf_bytes("Aziziye Aşevi - Giriş Kayıtları", log_satirlari),
                    "giris_kayitlari", "giris_kayit_sayfasi",
                )
                ozel_html_tablo_goster(log_satirlari)
            else:
                st.info("Henüz giriş kaydı yok.")
                if log_satirlari:
                    ortak_indirme_alani(
                        tablo_to_excel_bytes(log_satirlari, "Aziziye Aşevi - Giriş Kayıtları"),
                        tablo_to_html_pdf_bytes("Aziziye Aşevi - Giriş Kayıtları", log_satirlari),
                        "giris_kayitlari", "giris_kayit_sayfasi",
                    )
                    ozel_html_tablo_goster(log_satirlari)
                else:
                    st.info("Henüz giriş kaydı yok.")

                st.markdown("---")
                st.markdown("**🔓 Kilitleri Temizle** – Hatalı girişlerden kalan tüm geçici kilitleri kaldırır.")
                if st.button("Tüm Giriş Kilitlerini Temizle", key="kilit_temizle_btn"):
                    giris_denemesini_sifirla()
                    giris_logla("admin", "giriş kilitleri temizlendi")
                    st.success("Kilitler temizlendi.")
