from src.ui_kartlar import bolum_basligi_goster


def _html_satir_temizle(blok):
    return "\n".join(s.strip() for s in blok.splitlines() if s.strip())


def _guvenlik_karti_html(kategori, baslik, alt_durum, ipucu, renk, svg_ikon, html_escape):
    return _html_satir_temizle(f"""
    <div title="{html_escape(ipucu)}" style="background:linear-gradient(150deg,rgba(15,23,42,0.95) 0%,rgba(30,41,59,0.82) 100%);border:1px solid {renk}44;border-left:3.5px solid {renk};border-radius:13px;padding:12px 14px;cursor:help;box-shadow:0 4px 16px rgba(0,0,0,0.26);transition:all 0.2s ease;">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">
            <span style="font-size:0.67rem;font-weight:800;letter-spacing:0.8px;text-transform:uppercase;color:#94a3b8;">{html_escape(kategori)}</span>
            <div style="width:30px;height:30px;min-width:30px;border-radius:9px;background:rgba(15,23,42,0.88);border:1px solid {renk}55;box-shadow:0 0 12px {renk}22;display:flex;align-items:center;justify-content:center;">
                {svg_ikon}
            </div>
        </div>
        <div style="font-size:0.93rem;font-weight:700;color:#f8fafc;line-height:1.25;">{html_escape(baslik)}</div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:6px;">
            <span style="width:7px;height:7px;border-radius:50%;background:{renk};box-shadow:0 0 8px {renk};display:inline-block;"></span>
            <span style="font-size:0.75rem;font-weight:600;color:{renk};">{html_escape(alt_durum)}</span>
        </div>
    </div>
    """)


def guvenlik_durumu_rozetlerini_goster(st, SUPABASE_URL, SUPABASE_KEY, supabase_anahtar_rolu, cerez_kontrol, html_escape, bosta_kalma_suresi_sn, kullanici_db, ESKI_VARSAYILAN_HASHLER):
    bolum_basligi_goster(
        st,
        "kalkan",
        "Güvenlik Durumu ve Sistem Koruması",
        "Veritabanı anahtar yetkisi, oturum çerezi, kurtarma anahtarı ve şifre güvenliği canlı durumu (detay için kartların üzerine gelin)",
        vurgu_renk="#38bdf8",
    )

    # 1. Supabase Durum Hesaplaması
    if not SUPABASE_URL or not SUPABASE_KEY:
        sb_kart = (
            "VERİTABANI BAĞLANTISI",
            "Supabase Bağlantısı Yok",
            "Bağlantı Pasif",
            "Supabase bağlı değil: veriler kalıcı olarak saklanmıyor ve yedek/giriş kaydı çalışmıyor.",
            "#ef4444",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><line x1="2" y1="2" x2="22" y2="22"/></svg>',
        )
    else:
        _rol = supabase_anahtar_rolu()
        if _rol == "anon":
            sb_kart = (
                "VERİTABANI YETKİSİ",
                "Supabase (Anon)",
                "Düşük Yetki Uyarısı",
                "Supabase'de herkese açık (anon) anahtar kullanılıyor. RLS'yi açın ve `service_role` anahtarına geçin (`supabase_guvenlik.sql`).",
                "#f59e0b",
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            )
        elif _rol == "service_role":
            sb_kart = (
                "VERİTABANI YETKİSİ",
                "Supabase (service_role)",
                "Tam Yetkili Anahtar",
                "Supabase anahtarı: service_role (doğru). RLS'nin açık olduğundan emin olun.",
                "#10b981",
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
            )
        else:
            sb_kart = (
                "VERİTABANI YETKİSİ",
                "Supabase (Belirsiz)",
                "Rol Doğrulanamadı",
                "Supabase anahtarının rolü belirlenemedi; panelden RLS'nin açık olduğunu kontrol edin.",
                "#38bdf8",
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
            )

    # 2. Çerez Oturumu Hesaplaması
    if cerez_kontrol is not None:
        ck_kart = (
            "OTURUM KORUMASI",
            "Çerez Oturumu",
            "Şifreli Çerez Aktif",
            "Oturum anahtarı çerezde tutuluyor (adres çubuğunda görünmez).",
            "#10b981",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
        )
    else:
        ck_kart = (
            "OTURUM KORUMASI",
            "Adres Çubuğu Oturumu",
            "URL Token Modu",
            "Oturum anahtarı hâlâ adres çubuğunda. Çerez desteği için `requirements.txt` dosyasına `streamlit-cookies-controller` ekleyin.",
            "#38bdf8",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
        )

    # 3. Master Recovery Key Hesaplaması
    if str(st.secrets.get("MASTER_KEY", "") or ""):
        mr_kart = (
            "KURTARMA ANAHTARI",
            "Kurtarma Anahtarı",
            "MASTER_KEY Tanımlı",
            "MASTER_KEY tanımlı.",
            "#10b981",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
        )
    else:
        mr_kart = (
            "KURTARMA ANAHTARI",
            "Kurtarma Anahtarı Yok",
            "Tanımlı Değil",
            "MASTER_KEY tanımlı değil: şifre kurtarma devre dışı. Ekledim diyorsanız secrets'a TANI_MODU = \"1\" ekleyip adrese ?tani=1 yazarak kontrol edin.",
            "#f59e0b",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        )

    # 4. Boşta Kalma Süresi
    bosta_dk = bosta_kalma_suresi_sn() // 60
    it_kart = (
        "OTURUM ZAMAN AŞIMI",
        f"Boşta Kalma: {bosta_dk} dk",
        "Otomatik Kilit Aktif",
        f"Boşta kalma süresi: {bosta_dk} dk (işlem yapılmazsa oturum kapanır). Değiştirmek için secrets'a BOSTA_KALMA_DAKIKA = \"20\" gibi bir satır ekleyin.",
        "#38bdf8",
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    )

    # 5. Şifre Durumu Hesaplaması
    _zayif = [
        k for k, v in kullanici_db.items()
        if v.get("sifre_degistirilmeli") or v.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
    ]
    if _zayif:
        pw_kart = (
            "PAROLA POLİTİKASI",
            f"Şifre Yenileme ({len(_zayif)})",
            "Değişim Bekleniyor",
            "Şifresini değiştirmesi beklenen hesaplar: " + ", ".join(_zayif),
            "#f59e0b",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        )
    else:
        pw_kart = (
            "PAROLA POLİTİKASI",
            "Şifre Durumu Güvenli",
            "Tüm Hesaplar Güncel",
            "Eski varsayılan şifreyle kalan hesap yok.",
            "#10b981",
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        )

    kartlar_html = "".join(
        _guvenlik_karti_html(*kart, html_escape=html_escape)
        for kart in (sb_kart, ck_kart, mr_kart, it_kart, pw_kart)
    )

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:12px;margin:8px 0 18px 0;">{kartlar_html}</div>',
        unsafe_allow_html=True,
    )
