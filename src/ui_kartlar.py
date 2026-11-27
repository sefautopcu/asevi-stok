# src/ui_kartlar.py
import html

TEMA_PALETLERI = {
    "yesil": {
        "bg_start": "rgba(16, 185, 129, 0.18)",
        "bg_end": "rgba(14, 165, 233, 0.10)",
        "border": "rgba(16, 185, 129, 0.32)",
        "icon_bg": "rgba(16, 185, 129, 0.20)",
        "accent": "#10b981",
    },
    "mavi": {
        "bg_start": "rgba(56, 189, 248, 0.18)",
        "bg_end": "rgba(99, 102, 241, 0.10)",
        "border": "rgba(56, 189, 248, 0.32)",
        "icon_bg": "rgba(56, 189, 248, 0.20)",
        "accent": "#38bdf8",
    },
    "amber": {
        "bg_start": "rgba(245, 158, 11, 0.18)",
        "bg_end": "rgba(234, 88, 12, 0.10)",
        "border": "rgba(245, 158, 11, 0.32)",
        "icon_bg": "rgba(245, 158, 11, 0.20)",
        "accent": "#f59e0b",
    },
    "mor": {
        "bg_start": "rgba(168, 85, 247, 0.18)",
        "bg_end": "rgba(236, 72, 153, 0.10)",
        "border": "rgba(168, 85, 247, 0.32)",
        "icon_bg": "rgba(168, 85, 247, 0.20)",
        "accent": "#a855f7",
    },
    "kirmizi": {
        "bg_start": "rgba(244, 63, 94, 0.18)",
        "bg_end": "rgba(251, 113, 133, 0.10)",
        "border": "rgba(244, 63, 94, 0.32)",
        "icon_bg": "rgba(244, 63, 94, 0.20)",
        "accent": "#f43f5e",
    },
}

SVG_IKONLAR = {
    "logo": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11h18"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M8 7c0-1.5 1-2 1-3.5"/><path d="M12 7c0-1.5 1-2 1-3.5"/><path d="M16 7c0-1.5 1-2 1-3.5"/><path d="M7 19h10"/></svg>',
    "fatura": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16l4-2 4 2 4-2 4 2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/></svg>',
    "stok": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "depo": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21V9l9-6 9 6v12"/><path d="M9 21v-6h6v6"/><path d="M9 10h6"/></svg>',
    "demirbas": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    "tedarikci": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h3v3H7z"/><path d="M14 7h3v3h-3z"/><path d="M7 14h3v3H7z"/><path d="M14 14h3v3h-3z"/></svg>',
    "para": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M9 10h6"/><path d="M9 14h6"/><path d="M12 7v10"/></svg>',
    "liste": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 12h6"/><path d="M9 16h6"/></svg>',
    "mutfak": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11h16v5a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-5z"/><path d="M2 11h20"/><path d="M9 7V5"/><path d="M12 7V4"/><path d="M15 7V5"/></svg>',
    "uyari": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "rapor": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "kullanici": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "takvim": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><circle cx="12" cy="15" r="1"/></svg>',
    "kalkan": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
    "yetki": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="7" r="4"/><path d="M2 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/><circle cx="19" cy="11" r="2"/><path d="M19 8v1"/><path d="M19 13v1"/><path d="m21.6 9.5-.9.5"/><path d="m17.3 12-.9.5"/><path d="m21.6 12.5-.9-.5"/><path d="m17.3 10-.9-.5"/></svg>',
    "maske": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="m1 1 22 22"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/></svg>',
    "kilit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/></svg>',
    "kullanici_ekle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>',
    "tac": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>',
}

EMOJI_SVG_ESLESME = {
    "🧾": "fatura",
    "📦": "stok",
    "🏭": "depo",
    "🛠️": "demirbas",
    "🏢": "tedarikci",
    "💰": "para",
    "📋": "liste",
    "🍳": "mutfak",
    "🍲": "mutfak",
    "🔥": "uyari",
    "⚠️": "uyari",
    "📊": "rapor",
    "👥": "kullanici",
    "📅": "takvim",
    "🛡️": "kalkan",
    "🔐": "kilit",
    "🔒": "maske",
    "👑": "tac",
}


def _temiz_html(blok):
    """Streamlit Markdown'ın girintili satırları kod bloğu sanmasını önler."""
    return "\n".join(satir.strip() for satir in blok.splitlines() if satir.strip())


def ikon_rozeti_html(ikon, renk="#10b981", boyut=38):
    """Verilen ikon anahtarını veya emojiyi cam efektli vektörel ikon kutusuna dönüştürür."""
    anahtar = EMOJI_SVG_ESLESME.get(str(ikon).strip(), str(ikon).strip().lower())
    svg_kod = SVG_IKONLAR.get(anahtar)
    ikon_boyut = max(16, int(boyut * 0.54))

    if svg_kod:
        ic_html = svg_kod.replace(
            "<svg ",
            f'<svg width="{ikon_boyut}" height="{ikon_boyut}" style="color:{renk};display:block;" ',
        )
    else:
        ic_html = f'<span style="font-size:{ikon_boyut}px;line-height:1;">{html.escape(str(ikon))}</span>'

    return (
        f'<div style="width:{boyut}px;height:{boyut}px;min-width:{boyut}px;'
        f'border-radius:11px;background:rgba(15,23,42,0.75);'
        f'border:1px solid {renk}55;box-shadow:0 0 14px {renk}22;'
        f'display:flex;align-items:center;justify-content:center;">{ic_html}</div>'
    )


def kurumsal_logo_baslik_goster(st, kurum_adi="AZİZİYE AŞEVİ", alt_baslik="Stok, Depo & Mutfak Yönetim Sistemi"):
    """Uygulama üstü veya yan menü için vektörel logolu kurumsal başlık kartı çizer."""
    logo_svg = SVG_IKONLAR["logo"].replace(
        "<svg ",
        '<svg width="26" height="26" style="color:#10b981;display:block;" ',
    )
    html_cikti = f"""
    <div style="display:flex;align-items:center;gap:14px;background:linear-gradient(90deg,rgba(16,185,129,0.16) 0%,rgba(56,189,248,0.08) 100%);border:1px solid rgba(16,185,129,0.32);border-radius:14px;padding:12px 16px;margin-bottom:12px;">
        <div style="width:46px;height:46px;min-width:46px;border-radius:12px;background:linear-gradient(135deg,#064e3b 0%,#0f172a 100%);border:1px solid #10b98166;box-shadow:0 0 18px rgba(16,185,129,0.28);display:flex;align-items:center;justify-content:center;">
            {logo_svg}
        </div>
        <div>
            <div style="font-size:1.05rem;font-weight:800;letter-spacing:0.6px;color:#f8fafc;">{html.escape(str(kurum_adi))}</div>
            <div style="font-size:0.78rem;color:#94a3b8;margin-top:2px;">{html.escape(str(alt_baslik))}</div>
        </div>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)


def hosgeldiniz_tarih_bari_goster(st, tarih_metni, kullanici_adi=""):
    """Üst karşılama ve vektörel takvim ikonlu tarih şeridini çizer."""
    takvim_rozet = ikon_rozeti_html("takvim", renk="#38bdf8", boyut=28)
    kullanici_ek = (
        f'<span style="color:#10b981;font-weight:700;margin-left:4px;">{html.escape(str(kullanici_adi))}</span>'
        if kullanici_adi
        else ""
    )
    html_cikti = f"""
    <div style="display:inline-flex;align-items:center;gap:10px;background:rgba(15,23,42,0.65);border:1px solid rgba(148,163,184,0.20);border-radius:11px;padding:7px 14px;margin:2px 0 8px 0;">
        <span style="font-size:0.90rem;font-weight:700;color:#f8fafc;">Hoş geldiniz{kullanici_ek}</span>
        <span style="color:rgba(148,163,184,0.35);font-weight:400;">|</span>
        {takvim_rozet}
        <span style="font-size:0.88rem;font-weight:600;color:#cbd5e1;">{html.escape(str(tarih_metni))}</span>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)


def sayfa_ust_banner_goster(st, ikon, baslik, alt_baslik, tema="yesil"):
    """Sayfa üstünde özel vektörel ikon kutulu koyu tema gradyan başlık bandı gösterir."""
    palet = TEMA_PALETLERI.get(tema, TEMA_PALETLERI["yesil"])
    rozet = ikon_rozeti_html(ikon, renk=palet["accent"], boyut=46)
    html_cikti = f"""
    <div style="display:flex;align-items:center;gap:16px;background:linear-gradient(90deg,{palet['bg_start']} 0%,{palet['bg_end']} 100%);border:1px solid {palet['border']};border-radius:14px;padding:15px 20px;margin-bottom:14px;">
        {rozet}
        <div>
            <div style="font-size:1.38rem;font-weight:800;color:#f8fafc;line-height:1.2;">{html.escape(str(baslik))}</div>
            <div style="font-size:0.86rem;color:#94a3b8;margin-top:4px;">{html.escape(str(alt_baslik))}</div>
        </div>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)


def kullanici_ayarlari_luks_banner_goster(st, toplam_kullanici=0):
    """Kullanıcı Ayarları sekmesi için özel çift halkalı altın-zümrüt güvenlik arması ve lüks üst kart çizer."""
    arma_svg = (
        '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
        '<defs>'
        '<linearGradient id="luksGold" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#fbbf24"/>'
        '<stop offset="50%" stop-color="#f59e0b"/>'
        '<stop offset="100%" stop-color="#10b981"/>'
        '</linearGradient>'
        '</defs>'
        '<circle cx="18" cy="18" r="16.5" stroke="url(#luksGold)" stroke-width="1.4" stroke-dasharray="3 2"/>'
        '<path d="M18 6.5L27.5 10.2V17.4C27.5 23.3 23.4 28.4 18 30C12.6 28.4 8.5 23.3 8.5 17.4V10.2L18 6.5Z" '
        'fill="rgba(245,158,11,0.12)" stroke="url(#luksGold)" stroke-width="1.9" stroke-linejoin="round"/>'
        '<path d="M14.2 18.2L16.8 20.8L22.2 15.2" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )
    html_cikti = f"""
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;background:linear-gradient(120deg,rgba(15,23,42,0.96) 0%,rgba(30,41,59,0.92) 55%,rgba(6,78,59,0.42) 100%);border:1px solid rgba(245,158,11,0.38);box-shadow:0 10px 28px rgba(0,0,0,0.38),inset 0 1px 0 rgba(251,191,36,0.18);border-radius:16px;padding:18px 22px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:16px;">
            <div style="width:58px;height:58px;min-width:58px;border-radius:15px;background:radial-gradient(circle at 30% 25%,rgba(251,191,36,0.22),rgba(15,23,42,0.95) 72%);border:1px solid rgba(251,191,36,0.45);box-shadow:0 0 22px rgba(245,158,11,0.24);display:flex;align-items:center;justify-content:center;">
                {arma_svg}
            </div>
            <div>
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <span style="font-size:0.70rem;font-weight:800;letter-spacing:1.3px;text-transform:uppercase;color:#fbbf24;background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.35);padding:2px 9px;border-radius:999px;">YETKİ & GÜVENLİK MERKEZİ</span>
                    <span style="font-size:0.72rem;font-weight:600;color:#10b981;">● Aktif Koruma</span>
                </div>
                <div style="font-size:1.36rem;font-weight:800;color:#f8fafc;letter-spacing:0.2px;margin-top:5px;">Kullanıcı Ayarları, Rol & Alan Maskeleme Yönetimi</div>
                <div style="font-size:0.84rem;color:#94a3b8;margin-top:3px;">Sistem kullanıcılarının erişim rollerini, sayfa kısıtlamalarını, veri maskeleme kurallarını ve şifre güvenlik politikalarını yönetin</div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;background:rgba(15,23,42,0.78);border:1px solid rgba(148,163,184,0.22);border-radius:12px;padding:10px 14px;">
            <div style="text-align:right;">
                <div style="font-size:0.72rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.6px;">Kayıtlı Hesap</div>
                <div style="font-size:1.18rem;font-weight:800;color:#fbbf24;">{int(toplam_kullanici)} Kullanıcı</div>
            </div>
        </div>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)


def kpi_karti_html(ikon, baslik, deger, alt_bilgi, vurgu_renk="#10b981"):
    """Vektörel ikon rozetli tek bir KPI özet kartının HTML çıktısını üretir."""
    mini_rozet = ikon_rozeti_html(ikon, renk=vurgu_renk, boyut=32)
    html_cikti = f"""
    <div style="background:linear-gradient(145deg,#0f172a 0%,#1e293b 100%);border:1px solid rgba(148,163,184,0.18);border-left:4px solid {vurgu_renk};border-radius:12px;padding:15px 17px;margin-bottom:10px;box-shadow:0 4px 14px rgba(0,0,0,0.28);">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;">
            <span style="font-size:0.84rem;color:#94a3b8;font-weight:600;">{html.escape(str(baslik))}</span>
            {mini_rozet}
        </div>
        <div style="font-size:1.58rem;color:#f8fafc;font-weight:700;line-height:1.2;">{html.escape(str(deger))}</div>
        <div style="font-size:0.77rem;color:#64748b;margin-top:6px;">{html.escape(str(alt_bilgi))}</div>
    </div>
    """
    return _temiz_html(html_cikti)


def kpi_satiri_goster(st, kartlar):
    """Verilen [(ikon, baslik, deger, alt_bilgi, renk), ...] listesini yan yana KPI kartları olarak çizer."""
    if not kartlar:
        return
    kolonlar = st.columns(len(kartlar))
    for kol, kart in zip(kolonlar, kartlar):
        ikon, baslik, deger, alt_bilgi, renk = kart
        with kol:
            st.markdown(
                kpi_karti_html(ikon, baslik, deger, alt_bilgi, renk),
                unsafe_allow_html=True,
            )


def bolum_basligi_goster(st, ikon, baslik, alt_aciklama="", vurgu_renk="#38bdf8"):
    """Sayfa içindeki alt bölümler için vektörel ikon kutulu sol şeritli başlık gösterir."""
    rozet = ikon_rozeti_html(ikon, renk=vurgu_renk, boyut=34)
    alt_html = (
        f'<div style="font-size:0.81rem;color:#94a3b8;margin-top:2px;">{html.escape(str(alt_aciklama))}</div>'
        if alt_aciklama
        else ""
    )
    html_cikti = f"""
    <div style="display:flex;align-items:center;gap:12px;border-left:4px solid {vurgu_renk};padding:8px 14px;margin:14px 0 10px 0;background:rgba(15,23,42,0.58);border-radius:0 12px 12px 0;">
        {rozet}
        <div>
            <div style="font-size:1.08rem;font-weight:700;color:#f8fafc;">{html.escape(str(baslik))}</div>
            {alt_html}
        </div>
    </div>
    """
    st.markdown(_temiz_html(html_cikti), unsafe_allow_html=True)
