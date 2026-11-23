import json

def yedekleme_sekmesini_goster(sekme_y, st, SUPABASE_URL, SUPABASE_KEY, yedek_paketi_olustur, simdi_tr_str, giris_logla, yedek_geri_yukle, _supabase_ham_oku):
    # ------------------------------------------------ Yedekleme
    with sekme_y:
        st.subheader("💾 Yedekleme ve Geri Yükleme")
        if st.session_state.get("yedek_mesaj"):
            st.success(st.session_state.pop("yedek_mesaj"))
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.info("Yedekleme için Supabase bağlantısı gerekir.")
        else:
            st.caption(
                "Yedek dosyası kayıtlı kişilere ait bilgiler (ad-soyad, personel, stok vb.) içerir; "
                "T.C./telefon/adres alanları şifreli kalır. Kullanıcı şifreleri yedeğe GİRMEZ. "
                "Dosyayı güvenli bir yerde saklayın."
            )
            if st.button("📦 Tüm Veriyi Yedekle", key="yedek_hazirla_btn"):
                paket = yedek_paketi_olustur()
                if paket is None:
                    st.error("Yedek alınamadı: veritabanına ulaşılamadı.")
                else:
                    st.session_state["yedek_bytes"] = json.dumps(paket, ensure_ascii=False, indent=1).encode("utf-8")
                    st.session_state["yedek_adi"] = f"asevi_yedek_{simdi_tr_str('%Y%m%d_%H%M')}.json"
                    giris_logla("admin", "yedek alındı")
            if st.session_state.get("yedek_bytes"):
                st.download_button(
                    "⬇️ Yedek Dosyasını İndir",
                    data=st.session_state["yedek_bytes"],
                    file_name=st.session_state.get("yedek_adi", "asevi_yedek.json"),
                    mime="application/json",
                    key="yedek_indir_btn",
                )

            st.markdown("---")
            st.markdown("**♻️ Yedekten Geri Yükle** – Mevcut veriler yedekteki verilerle DEĞİŞTİRİLİR. İşlemden önce otomatik bir yedek alınır.")
            yuklenen_yedek = st.file_uploader("Yedek dosyası (.json)", type=["json"], key="yedek_yukle_dosya")
            geri_yukle_onay = st.checkbox("⚠️ Mevcut verilerin yedekle değiştirileceğini anlıyorum, onaylıyorum.", key="yedek_onay_chk")
            if st.button("Yedeği Geri Yükle", type="primary", key="yedek_geri_yukle_btn"):
                if yuklenen_yedek is None:
                    st.error("Önce bir yedek dosyası seçin.")
                elif not geri_yukle_onay:
                    st.error("Geri yüklemek için onay kutusunu işaretleyin.")
                elif yuklenen_yedek.size > 25 * 1024 * 1024:
                    st.error("Dosya çok büyük (en fazla 25 MB).")
                else:
                    try:
                        paket = json.loads(yuklenen_yedek.getvalue().decode("utf-8"))
                    except Exception:
                        paket = None
                    basarili, mesaj = yedek_geri_yukle(paket)
                    if basarili:
                        giris_logla("admin", "yedekten geri yüklendi")
                        st.session_state["yedek_mesaj"] = mesaj
                        st.rerun()
                    else:
                        st.error(mesaj)

            st.markdown("---")
            st.markdown("**⏪ Son Otomatik Yedek** – Silme ve geri yükleme işlemlerinden hemen önce otomatik alınır (yalnızca en son yedek tutulur).")
            oto_durum, oto_paket = _supabase_ham_oku("otomatik_yedek")
            if oto_durum == "ok" and isinstance(oto_paket, dict):
                _meta = oto_paket.get("_meta", {})
                st.info(f"Zaman: {_meta.get('zaman', '-')} | Neden: {_meta.get('neden', '-')}")
                oto_onay = st.checkbox("⚠️ Otomatik yedeğe dönmeyi onaylıyorum.", key="oto_yedek_onay_chk")
                if st.button("Son Otomatik Yedeğe Dön", key="oto_yedek_geri_btn"):
                    if not oto_onay:
                        st.error("Onay kutusunu işaretleyin.")
                    else:
                        basarili, mesaj = yedek_geri_yukle(oto_paket)
                        if basarili:
                            giris_logla("admin", "otomatik yedeğe dönüldü")
                            st.session_state["yedek_mesaj"] = mesaj
                            st.rerun()
                        else:
                            st.error(mesaj)
            elif oto_durum == "hata":
                st.error("Otomatik yedek bilgisi okunamadı.")
            else:
                st.caption("Henüz otomatik yedek alınmadı.")
