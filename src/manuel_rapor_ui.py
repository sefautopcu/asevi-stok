from src.ui_kartlar import bolum_basligi_goster


def _html_satir_temizle(blok):
    return "\n".join(s.strip() for s in blok.splitlines() if s.strip())


def manuel_rapor_gonderim_alani(st, manuel_rapor_maili_gonder):
    bolum_basligi_goster(
        st,
        "rapor",
        "Manuel Rapor Gönderimi",
        "Aşağıdaki butonlar sadece o anki verileri size gönderir. Otomatik sabah 08:30 mailini etkilemez.",
        vurgu_renk="#10b981",
    )

    st.markdown(
        _html_satir_temizle("""
        <style>
            .st-key-btn_manuel_gunluk button,
            .st-key-btn_manuel_haftalik button,
            .st-key-btn_manuel_aylik button {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.16) 0%, rgba(15, 23, 42, 0.95) 100%) !important;
                border: 1px solid rgba(16, 185, 129, 0.45) !important;
                border-radius: 12px !important;
                padding: 10px 16px !important;
                color: #34d399 !important;
                font-weight: 700 !important;
                font-size: 13.5px !important;
                letter-spacing: 0.2px !important;
                transition: all 0.25s ease !important;
                width: 100% !important;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
            }
            .st-key-btn_manuel_gunluk button:hover,
            .st-key-btn_manuel_haftalik button:hover,
            .st-key-btn_manuel_aylik button:hover {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.30) 0%, rgba(6, 78, 59, 0.85) 100%) !important;
                color: #ffffff !important;
                border-color: #34d399 !important;
                box-shadow: 0 0 18px rgba(16, 185, 129, 0.42) !important;
                transform: translateY(-2px) !important;
            }
        </style>
        """),
        unsafe_allow_html=True,
    )

    rapor_kartlari = [
        (
            "GÜNLÜK ÖZET",
            "#10b981",
            "Dünün Raporu",
            "Dünkü stok hareketleri, günlük üretim ve dağıtım özeti",
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/></svg>',
            "📅 Dünün Raporunu Gönder",
            "btn_manuel_gunluk",
            "gunluk",
        ),
        (
            "7 GÜNLÜK DÖNEM",
            "#38bdf8",
            "Haftalık Rapor",
            "Son 7 günlük malzeme sarfiyatı, maliyet ve porsiyon analizi",
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/></svg>',
            "🗓️ Haftalık Raporu Gönder",
            "btn_manuel_haftalik",
            "haftalik",
        ),
        (
            "30 GÜNLÜK DÖNEM",
            "#fbbf24",
            "Aylık Rapor",
            "Aylık genel envanter bilançosu, harcama ve üretim dökümü",
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
            "📆 Aylık Raporu Gönder",
            "btn_manuel_aylik",
            "aylik",
        ),
    ]

    kolonlar = st.columns(3)
    for kol, (etiket, renk, baslik, aciklama, svg_ikon, btn_metin, btn_key, tetik_deger) in zip(kolonlar, rapor_kartlari):
        with kol:
            st.markdown(
                _html_satir_temizle(f"""
                <div style="background:linear-gradient(145deg,rgba(15,23,42,0.92) 0%,rgba(30,41,59,0.78) 100%);border:1px solid rgba(148,163,184,0.18);border-top:3px solid {renk};border-radius:14px;padding:14px 16px;margin-bottom:8px;box-shadow:0 6px 18px rgba(0,0,0,0.24);">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(15,23,42,0.85);border:1px solid {renk}55;display:flex;align-items:center;justify-content:center;">
                            {svg_ikon}
                        </div>
                        <span style="font-size:0.68rem;font-weight:800;letter-spacing:0.9px;color:{renk};background:{renk}1a;border:1px solid {renk}44;padding:3px 9px;border-radius:999px;">{etiket}</span>
                    </div>
                    <div style="font-size:1.0rem;font-weight:700;color:#f8fafc;">{baslik}</div>
                    <div style="font-size:0.78rem;color:#94a3b8;margin-top:3px;min-height:32px;">{aciklama}</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
            if st.button(btn_metin, key=btn_key, use_container_width=True):
                st.session_state["manuel_mail_tetik"] = tetik_deger

    # Mail Gönderme Tetikleyicisi
    if st.session_state.get("manuel_mail_tetik"):
        mail_tipi = st.session_state.pop("manuel_mail_tetik")
        with st.spinner(f"{mail_tipi.capitalize()} raporu hazırlanıyor ve gönderiliyor..."):
            if manuel_rapor_maili_gonder(mail_tipi):
                st.success("🎉 Rapor başarıyla gönderildi! Lütfen mail kutunuzu kontrol edin.")
            else:
                st.error("❌ Mail gönderilemedi. Lütfen konsol loglarını kontrol edin.")
