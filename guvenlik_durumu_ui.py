def guvenlik_durumu_rozetlerini_goster(st, SUPABASE_URL, SUPABASE_KEY, supabase_anahtar_rolu, cerez_kontrol, html_escape, bosta_kalma_suresi_sn, kullanici_db, ESKI_VARSAYILAN_HASHLER):
    # GÜVENLİK DURUMU - LOGO VE HOVER (ÜZERİNE GELİNCE GÖSTERİM) ROZETLERİ
    # ------------------------------------------------------------------
    st.subheader("🛡️ Güvenlik Durumu")

    # 1. Supabase Durum Hesaplaması
    if not SUPABASE_URL or not SUPABASE_KEY:
        sb_badge = ("❌", "Supabase Bağlantısı Yok", "Supabase bağlı değil: veriler kalıcı olarak saklanmıyor ve yedek/giriş kaydı çalışmıyor.", "background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #f87171;")
    else:
        _rol = supabase_anahtar_rolu()
        if _rol == "anon":
            sb_badge = ("⚠️", "Supabase (Anon)", "Supabase'de herkese açık (anon) anahtar kullanılıyor. RLS'yi açın ve `service_role` anahtarına geçin (`supabase_guvenlik.sql`).", "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")
        elif _rol == "service_role":
            sb_badge = ("🔑", "Supabase (service_role)", "Supabase anahtarı: service_role (doğru). RLS'nin açık olduğundan emin olun.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
        else:
            sb_badge = ("ℹ️", "Supabase (Belirsiz)", "Supabase anahtarının rolü belirlenemedi; panelden RLS'nin açık olduğunu kontrol edin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

    # 2. Çerez Oturumu Hesaplaması
    if cerez_kontrol is not None:
        ck_badge = ("🍪", "Çerez Oturumu", "Oturum anahtarı çerezde tutuluyor (adres çubuğunda görünmez).", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
    else:
        ck_badge = ("🔗", "Adres Çubuğu Oturumu", "Oturum anahtarı hâlâ adres çubuğunda. Çerez desteği için `requirements.txt` dosyasına `streamlit-cookies-controller` ekleyin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

    # 3. Master Recovery Key Hesaplaması
    if str(st.secrets.get("MASTER_RECOVERY_KEY", "") or ""):
        mr_badge = ("🛡️", "Kurtarma Anahtarı", "MASTER_RECOVERY_KEY tanımlı.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
    else:
        mr_badge = ("⚠️", "Kurtarma Anahtarı Yok", "MASTER_RECOVERY_KEY tanımlı değil: şifre kurtarma devre dışı. Ekledim diyorsanız secrets'a TANI_MODU = \"1\" ekleyip adrese ?tani=1 yazarak kontrol edin.", "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")

    # 4. Boşta Kalma Süresi
    bosta_dk = bosta_kalma_suresi_sn() // 60
    it_badge = ("⏱️", f"Boşta Kalma: {bosta_dk} dk", f"Boşta kalma süresi: {bosta_dk} dk (işlem yapılmazsa oturum kapanır). Değiştirmek için secrets'a BOSTA_KALMA_DAKIKA = \"20\" gibi bir satır ekleyin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

    # 5. Şifre Durumu Hesaplaması
    _zayif = [
        k for k, v in kullanici_db.items()
        if v.get("sifre_degistirilmeli") or v.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
    ]
    if _zayif:
        pw_badge = ("🚨", f"Şifre Yenileme ({len(_zayif)})", "Şifresini değiştirmesi beklenen hesaplar: " + ", ".join(_zayif), "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")
    else:
        pw_badge = ("✅", "Şifre Durumu Güvenli", "Eski varsayılan şifreyle kalan hesap yok.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")

    # HTML Rozet Paneli Gösterimi
    st.markdown(
        f"""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; margin-top: 5px;">
            <div title="{html_escape(sb_badge[2])}" style="{sb_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                <span>{sb_badge[0]}</span> <span>{sb_badge[1]}</span>
            </div>
            <div title="{html_escape(ck_badge[2])}" style="{ck_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                <span>{ck_badge[0]}</span> <span>{ck_badge[1]}</span>
            </div>
            <div title="{html_escape(mr_badge[2])}" style="{mr_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                <span>{mr_badge[0]}</span> <span>{mr_badge[1]}</span>
            </div>
            <div title="{html_escape(it_badge[2])}" style="{it_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                <span>{it_badge[0]}</span> <span>{it_badge[1]}</span>
            </div>
            <div title="{html_escape(pw_badge[2])}" style="{pw_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                <span>{pw_badge[0]}</span> <span>{pw_badge[1]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
