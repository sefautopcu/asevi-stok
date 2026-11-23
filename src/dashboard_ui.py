import base64
import requests as requests_lib
import streamlit as streamlit_lib


@streamlit_lib.cache_data(ttl=900, show_spinner=False)
def _hava_durumu_verisini_getir(url):
    response = requests_lib.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def dashboard_sayfasi(st, aktif_k_maskeleri, yonetici_modu, components, dashboard_ozet_hesapla, dashboard_operasyonel_istatistikleri, anlik_hava_gosterge, requests, datetime, html_escape):
    panel_bg = "rgba(10, 15, 29, 0.75)"
    panel_strong_bg = "rgba(6, 10, 20, 0.85)"
    panel_border = "rgba(16, 185, 129, 0.35)"
    panel_text = "#f4f4f5"
    panel_muted = "#94a3b8"
    panel_accent = "#10b981"
    panel_shadow = "rgba(16,185,129,.25)"

    import base64
        # Üstteki varsayılan Streamlit boşluğunu kaldır
    st.markdown("<style>div.block-container { padding-top: 1.5rem !important; } hr { margin-top: 0rem !important; margin-bottom: 0rem !important; }</style>", unsafe_allow_html=True)   

    # --- ARKA PLAN RESMİ YÖNETİMİ ---
    varsayilan_arka_plan = "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=1920&auto=format&fit=crop"

    if "dashboard_arka_plan" not in st.session_state:
        st.session_state.dashboard_arka_plan = varsayilan_arka_plan

    arka_plan_url = st.session_state.dashboard_arka_plan

    # --- VERİ HAZIRLIĞI ---
    gecmis_uretimler = st.session_state.get("yemek_uretim_arsivi", [])
    dashboard_ozeti = dashboard_ozet_hesapla(
        st.session_state.get("girisler", []),
        st.session_state.get("kullanim_loglari", []),
        st.session_state.get("personeller", []),
        st.session_state.get("depolar", []),
    )
    urun_cesidi_sayisi = dashboard_ozeti["urun_cesidi_sayisi"]
    toplam_stok_degeri = dashboard_ozeti["toplam_stok_degeri"]
    toplam_fire_kg = dashboard_ozeti["toplam_fire_kg"]
    toplam_fire_tl = dashboard_ozeti["toplam_fire_tl"]
    aktif_personel_sayisi = dashboard_ozeti["aktif_personel_sayisi"]

    # --- MASKELEME KONTROLÜ ---
    fire_maskeli = "1. Sayfa: Toplam Fire" in aktif_k_maskeleri
    stok_maskeli = "1. Sayfa: Stok Değeri" in aktif_k_maskeleri
    urun_maskeli = "1. Sayfa: Ürün Çeşidi" in aktif_k_maskeleri
    personel_maskeli = "1. Sayfa: Aktif Personel" in aktif_k_maskeleri
    grafik_maskeli = "1. Sayfa: Grafik Alanı" in aktif_k_maskeleri
    kat_maskeli = "1. Sayfa: Kategori Doluluk" in aktif_k_maskeleri
    depo_maskeli = "1. Sayfa: Depo Doluluk" in aktif_k_maskeleri
    op_maskeli = "1. Sayfa: Operasyonel Sağlık" in aktif_k_maskeleri

    fire_degeri_gosterim = "🔒 Gizli" if fire_maskeli else f"{toplam_fire_kg:.1f} Kg"
    fire_alt_gosterim = "" if fire_maskeli else f"({toplam_fire_tl:,.2f} ₺)"
    stok_degeri_gosterim = "🔒 Gizli" if stok_maskeli else f"{toplam_stok_degeri:,.2f} ₺".replace(',', 'X').replace('.', ',').replace('X', '.')
    urun_cesidi_gosterim = "🔒 Gizli" if urun_maskeli else f"{urun_cesidi_sayisi} Çeşit"
    personel_gosterim = "🔒 Gizli" if personel_maskeli else f"{aktif_personel_sayisi} Kişi"

    # --- GRAFİK VERİLERİ HESAPLAMA ---
    gida_toplam = dashboard_ozeti["gida_toplam"]
    sebze_toplam = dashboard_ozeti["sebze_toplam"]
    yag_toplam = dashboard_ozeti["yag_toplam"]
    genel_toplam = dashboard_ozeti["genel_toplam"]
    yuzde_gida = dashboard_ozeti["yuzde_gida"]
    yuzde_sebze = dashboard_ozeti["yuzde_sebze"]
    yuzde_yag = dashboard_ozeti["yuzde_yag"]
    depo_doluluk = dashboard_ozeti["depo_doluluk"]
    sirali_depolar = dashboard_ozeti["sirali_depolar"]
    renkler = ["#10b981", "#38bdf8", "#f59e0b"]

    depo_html_satirlari = ""
    for i, (d_adi, d_yuzde) in enumerate(sirali_depolar):
        renk = renkler[i % len(renkler)]
        depo_html_satirlari += f"""
            <div class="progress-row">
                <div class="progress-title"><span>{html_escape(d_adi)}</span><span class="text-white">{d_yuzde}%</span></div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {d_yuzde}%; background: {renk};"></div></div>
            </div>
        """

    # --- DİNAMİK KRİTİK SEVİYE VE OPERASYONEL SAĞLIK HESABI ---
    operasyonel_ozet = dashboard_operasyonel_istatistikleri(
        st.session_state.get("girisler", []),
        st.session_state.get("kritik_seviyeler", {}),
        st.session_state.get("dagitim_loglari", []),
        urun_cesidi_sayisi,
        datetime.date.today(),
    )
    kritik_urun_sayisi = operasyonel_ozet["kritik_urun_sayisi"]
    guvenli_urun_sayisi = operasyonel_ozet["guvenli_urun_sayisi"]
    skt_kirmizi = operasyonel_ozet["skt_kirmizi"]
    skt_turuncu = operasyonel_ozet["skt_turuncu"]
    yuzde_kritik = operasyonel_ozet["yuzde_kritik"]
    yuzde_guvenli = operasyonel_ozet["yuzde_guvenli"]
    aylik_barlar_html = operasyonel_ozet["aylik_barlar_html"]

    # --- TÜM TASARIM TEK BİR HTML İÇİNDE ---
    st.markdown("""
    <style>
        .table-panel { 
            background: rgba(10, 15, 29, 0.85); 
            border: 1px solid rgba(16, 185, 129, 0.35); 
            border-radius: 18px; 
            padding: 25px; 
            transition: all 0.3s ease; 
            display: flex; 
            flex-direction: column; 
            min-height: 320px; 
            height: 100%; 
        }
        .table-panel:hover { 
            transform: translateY(-5px); 
            border-color: rgba(16, 185, 129, 0.8); 
            box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); 
        }
    </style>
    """, unsafe_allow_html=True)
    # --- TÜM TASARIM TEK BİR HTML İÇİNDE ---
    # --- ERZURUM AZİZİYE 7 GÜNLÜK HAVA DURUMU VERİSİ ---
    hava_durumu_html = ""
    anlik_hava_gosterge = ""  # YENİ EKLENEN: Anlık hava durumu değişkeni
    try:
        # URL'ye &current_weather=true eklendi
        hava_url = "https://api.open-meteo.com/v1/forecast?latitude=39.95&longitude=41.10&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&current_weather=true&timezone=Europe/Istanbul&forecast_days=7"
        hava_veri = _hava_durumu_verisini_getir(hava_url)

        # YENİ EKLENEN: Anlık hava durumunu ayıkla ve emojiye çevir
        if "current_weather" in hava_veri:
            cw = hava_veri["current_weather"]
            a_temp = cw.get("temperature", 0)
            a_code = cw.get("weathercode", 0)

            # WMO Hava Durumu Kodları Haritası
            if a_code == 0: a_emoji = "☀️"
            elif a_code in [1, 2, 3]: a_emoji = "🌤️"
            elif a_code in [45, 48]: a_emoji = "🌫️"
            elif a_code in [51, 53, 55, 56, 57]: a_emoji = "🌦️"
            elif a_code in [61, 63, 65, 66, 67, 80, 81, 82]: a_emoji = "🌧️"
            elif a_code in [71, 73, 75, 77, 85, 86]: a_emoji = "🌨️"
            elif a_code in [95, 96, 99]: a_emoji = "⛈️"
            else: a_emoji = "🌡️"

            anlik_hava_gosterge = f"{a_emoji} {a_temp}°C"

        if "daily" in hava_veri:
            # ... (mevcut kodlarınız aynen buradan devam edecek)
            gunler = hava_veri["daily"]["time"]
            max_temp = hava_veri["daily"]["temperature_2m_max"]
            min_temp = hava_veri["daily"]["temperature_2m_min"]
            yagis = hava_veri["daily"]["precipitation_sum"]

            aylar_tr_kisa = {"01":"Oca", "02":"Şub", "03":"Mar", "04":"Nis", "05":"May", "06":"Haz", "07":"Tem", "08":"Ağu", "09":"Eyl", "10":"Eki", "11":"Kas", "12":"Ara"}

            for i in range(len(gunler)):
                tarih_obj = datetime.datetime.strptime(gunler[i], "%Y-%m-%d")
                gun_adi = f"{tarih_obj.day} {aylar_tr_kisa.get(f'{tarih_obj.month:02d}', '')}"

                ort_temp = (max_temp[i] + min_temp[i]) / 2
                if ort_temp > 15: renk = "#10b981" 
                elif ort_temp > 5: renk = "#38bdf8" 
                elif ort_temp > -5: renk = "#f59e0b" 
                else: renk = "#ef4444" 

                yagis_ikon = "☀️" if yagis[i] == 0 else ("🌧️" if yagis[i] < 10 else "🌧️🌧️")

                m_temp = f"{max_temp[i]:.0f}"
                n_temp = f"{min_temp[i]:.0f}"
                renk_alt = renk + "88"

                hava_durumu_html += f"""
                    <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%;">
                        <div style="font-size: 20px; margin-bottom: 5px;">{yagis_ikon}</div>
                        <div style="font-size: 14px; color: #f4f4f5; font-weight: bold;">{m_temp}°</div>
                        <div style="font-size: 12px; color: #94a3b8;">{n_temp}°</div>
                        <div style="width: 80%; background: linear-gradient(180deg, {renk} 0%, {renk_alt} 100%); border-radius: 6px 6px 0 0; height: 60%; margin-top: 8px;"></div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">{gun_adi}</div>
                    </div>
                """
    except Exception:
        hava_durumu_html = "<div style='color: #94a3b8; text-align: center; width: 100%;'>Hava durumu verisi alınamadı.</div>"
        # Maskeler için HTML içeriklerini hazırla
    kat_icerik = '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>' if kat_maskeli else f'<div class="progress-row"><div class="progress-title"><span>1. Kuru Gıda</span><span class="text-white">{yuzde_gida}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_gida}%; background: #10b981;"></div></div></div><div class="progress-row"><div class="progress-title"><span>2. Sebze</span><span class="text-white">{yuzde_sebze}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_sebze}%; background: #38bdf8;"></div></div></div><div class="progress-row"><div class="progress-title"><span>3. Yağ</span><span class="text-white">{yuzde_yag}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_yag}%; background: #a855f7;"></div></div></div>'

    depo_icerik = '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>' if depo_maskeli else depo_html_satirlari

    op_icerik = '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>' if op_maskeli else f'<div class="progress-row"><div class="progress-title"><span>Kritik Seviyede</span><span class="text-white">{kritik_urun_sayisi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_kritik}%; background: #ef4444;"></div></div></div><div class="progress-row"><div class="progress-title"><span>Güvenli Stokta</span><span class="text-white">{guvenli_urun_sayisi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_guvenli}%; background: #10b981;"></div></div></div><div class="progress-row"><div class="progress-title"><span>🔴 SKT Süresi Geçen</span><span class="text-white">{skt_kirmizi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_kirmizi*10, 100)}%; background: #ef4444;"></div></div></div><div class="progress-row"><div class="progress-title"><span>🟠 SKT\'si Yaklaşan</span><span class="text-white">{skt_turuncu} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_turuncu*10, 100)}%; background: #f59e0b;"></div></div></div>'    
    hero_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }}
        body {{ background: transparent; margin: 0; padding: 0; }}

        .main-hero-container {{
            background-image: linear-gradient(rgba(4, 7, 17, 0.75), rgba(4, 7, 17, 0.95)), url('{arka_plan_url}'); 
            background-size: cover; background-position: center; 
            border-radius: 24px; padding: 35px; margin-bottom: 25px; 
            border: 1px solid rgba(16, 185, 129, 0.4); box-shadow: 0 15px 40px -10px rgba(0,0,0,0.6); 
        }}
        .hero-badge {{ background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; margin-bottom: 15px; }}
        .hero-title {{ font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 8px; letter-spacing: -0.03em; }}
        .hero-subtitle {{ color: #cbd5e1; font-size: 14px; margin-bottom: 30px; }}

        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px; }}
        .metric-card {{ background: rgba(10, 15, 29, 0.75); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 18px; box-shadow: 0 0 25px -5px rgba(16, 185, 129, 0.25); transition: all 0.3s ease; backdrop-filter: blur(10px); }}
        .metric-card:hover {{ transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }}
        .metric-val {{ font-size: 1.4rem; font-weight: 800; color: #f4f4f5; margin: 6px 0; }}
        .metric-label {{ font-size: 12px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
        .metric-sub {{ font-size: 11px; color: #10b981; font-weight: 600; }}
        .metric-sub-red {{ font-size: 11px; color: #ef4444; font-weight: 600; }}

        .panel-title {{ font-size: 1.1rem; font-weight: 700; color: #f4f4f5; }}
        .panel-total {{ font-size: 1.6rem; font-weight: 800; color: #fff; line-height: 1.2; margin-top: 5px; }}
        .panel-sub {{ font-size: 12px; color: #94a3b8; margin-top: 4px; margin-bottom: 20px; }}

        .table-panel {{ background: rgba(10, 15, 29, 0.85); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 25px; transition: all 0.3s ease; display: flex; flex-direction: column; min-height: 340px; height: 100%; }}
        .table-panel:hover {{ transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }}

        .progress-row {{ margin-bottom: 15px; }}
        .progress-title {{ display: flex; justify-content: space-between; font-size: 13px; color: #cbd5e1; font-weight: 500; margin-bottom: 8px; }}
        .text-white {{ color: #fff; font-weight: 700; }}
        .progress-bar-bg {{ height: 6px; background: rgba(15, 23, 42, 0.9); border-radius: 4px; overflow: hidden; }}
        .progress-bar-fill {{ height: 100%; border-radius: 4px; }}

        .chart-container {{ display: flex; gap: 15px; align-items: flex-end; height: 120px; padding-bottom: 20px; }}
    </style>
    </head>
    <body>
        <div class="main-hero-container">
            <div class="hero-badge">📍 AZİZİYE AŞEVİ · KURUMSAL PANEL <span style="margin-left: 8px; padding-left: 8px; border-left: 1px solid rgba(16, 185, 129, 0.5); font-size: 11px; color: #cbd5e1; font-weight: 500;">{anlik_hava_gosterge}</span></div>
            <div class="hero-title">Genel Bakış & Operasyonel Özet</div>
            <div class="hero-subtitle">Canlı Stok ve Maliyet Takip Sistemi</div>

            <div class="metrics-grid">
                <div class="metric-card"><div class="metric-label">Günlük Sıcak Yemek</div><div class="metric-val">Aktif</div><div class="metric-sub">↑ Anlık Simülasyon</div></div>
                <div class="metric-card"><div class="metric-label">Ürün Çeşidi</div><div class="metric-val">{urun_cesidi_gosterim}</div><div class="metric-sub">↑ Güncel Stok Durumu</div></div>
                <div class="metric-card"><div class="metric-label">Toplam Fire / Zayiat</div><div class="metric-val">{fire_degeri_gosterim}</div><div class="metric-sub-red">{fire_alt_gosterim}</div></div>
                <div class="metric-card"><div class="metric-label">Stok Değeri</div><div class="metric-val">{stok_degeri_gosterim}</div><div class="metric-sub">↑ Güncel Depo Toplamı</div></div>
            </div>
            <div class="metrics-grid" style="margin-bottom: 30px;">
                <div class="metric-card"><div class="metric-label">Aktif Çalışan Personel</div><div class="metric-val">{personel_gosterim}</div><div class="metric-sub">↑ Personel Takip Tablosu</div></div>
                <div class="metric-card"><div class="metric-label">Depo Durumu</div><div class="metric-val">Senkronize</div><div class="metric-sub">↑ Supabase Realtime RLS</div></div>
                <div class="metric-card"><div class="metric-label">Son Birim Fiyat Mantığı</div><div class="metric-val">FIFO Mantığı</div><div class="metric-sub">↑ Reçete Hassasiyeti</div></div>
                <div class="metric-card"><div class="metric-label">Son İşlem Desteği</div><div class="metric-val">Aktif (Undo)</div><div class="metric-sub">↑ Tek Tıkla Geri Al</div></div>
            </div>

            <!-- 3'LÜ TABLO -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 20px;">

                <!-- Kategori Doluluk -->
                <div class="table-panel">
                    <div class="panel-title">Kategori Doluluk</div>
                    <div class="panel-total">Stok Dağılımı</div>
                    <div class="panel-sub">Maliyet bazlı oranlar</div>
                    {kat_icerik}
                </div>

                <!-- Depo Doluluk -->
                <div class="table-panel">
                    <div class="panel-title">Depo Doluluk</div>
                    <div class="panel-total">Ağırlıklı</div>
                    <div class="panel-sub">Fiziksel depo dolulukları</div>
                    {depo_icerik}
                </div>

                <!-- Operasyonel Sağlık -->
                <div class="table-panel">
                    <div class="panel-title">Operasyonel Sağlık</div>
                    <div class="panel-total">{urun_cesidi_sayisi if not op_maskeli else '🔒'}</div>
                    <div class="panel-sub">Kayıtlı çeşit üzerinden durum</div>
                    {op_icerik}
                </div>

            </div>

            <!-- CANLI HAVA DURUMU GRAFİĞİ -->
            <div class="table-panel">
                <div class="panel-title" style="margin-bottom: 15px;">🌤️ Erzurum / Aziziye - 7 Günlük Hava Durumu</div>
                <div class="chart-container" style="height: 140px;">
                    {hava_durumu_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(hero_html, height=1200, scrolling=False)

    # --- 3. BÖLÜM: EN ALT (YEMEK SEÇİMİ + CANLI MALİYET ÖZET PANELİ) ---
    st.markdown("---")
    menu_secenekleri = {}
    if gecmis_uretimler:
        for item in gecmis_uretimler:
            if not item: continue
            top_mal = float(item.get("toplam_maliyet", 0)) or sum(float(m.get("tutar", 0)) for m in item.get("malzemeler", []))
            kisi = int(item.get("kisi_sayisi", 1) or 1)
            item["kisi_basi"] = top_mal / kisi if kisi > 0 else 0.0
            item["kalem_sayisi"] = len(item.get("malzemeler", []))
            menu_secenekleri[f"{item.get('tarih', '-')} | {item.get('yemek_adi', '-')} ({kisi} Kişi)"] = item

    if not menu_secenekleri:
        menu_secenekleri = {"Henüz Kayıt Yok": {"tarih": "-", "yemek_adi": "Kayıt Yok", "kisi_basi": 0.0, "kalem_sayisi": 0}}

    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        secilen_key = st.selectbox("📋 Geçmişte Çıkan Yemeği / Menüyü Seçin", options=list(menu_secenekleri.keys()))
    with col_sel2:
        kisi_sayisi = st.slider("Yararlanılan Kişi Sayısı (Simülasyon)", 10, 1000, 230, step=10)

    secilen_veri = menu_secenekleri[secilen_key]
    toplam_tl = secilen_veri.get("kisi_basi", 0.0) * kisi_sayisi

    st.markdown(f"""
    <style>
        .cost-panel {{ background: rgba(10, 15, 29, 0.85); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 20px; padding: 25px; box-shadow: 0 0 35px -5px rgba(16, 185, 129, 0.35); margin-bottom: 25px; }}
        .cost-header {{ font-size: 1.2rem; font-weight: 700; color: #f4f4f5; }}
        .cost-meta {{ font-size: 12px; color: #94a3b8; margin: 4px 0 18px 0; text-transform: uppercase; }}
        .inner-box {{ background: rgba(6, 10, 20, 0.7); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 16px; padding: 20px; }}
        .cost-row {{ display: flex; gap: 16px; margin-bottom: 16px; }}
        .cost-card {{ flex: 1; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 14px; padding: 15px; }}
        .cost-num-green {{ font-size: 1.6rem; font-weight: 800; color: #10b981; margin-top: 4px; }}
        .cost-num-blue {{ font-size: 1.6rem; font-weight: 800; color: #38bdf8; margin-top: 4px; }}
    </style>
    <div class="cost-panel">
        <div class="cost-header">📊 Canlı Maliyet Özet Paneli</div>
        <div class="cost-meta">Tarih: {html_escape(str(secilen_veri.get('tarih', '-')))} | {secilen_veri.get('kalem_sayisi', 0)} Kalem Malzeme | Simülasyon: {kisi_sayisi} Kişi</div>
        <div class="inner-box">
            <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff; margin-bottom: 16px;">{html_escape(str(secilen_veri.get('yemek_adi', '-')))}</div>
            <div class="cost-row">
                <div class="cost-card"><div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Menü Toplam Maliyeti</div><div class="cost-num-green">{toplam_tl:,.2f} ₺</div></div>
                <div class="cost-card"><div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Kişi Başı Maliyet ({kisi_sayisi} Kişi)</div><div class="cost-num-blue">{secilen_veri.get('kisi_basi', 0.0):,.2f} ₺</div></div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.12); border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 8px; font-size: 12px; color: #cbd5e1;">🔄 <b>Son İşlem Geri Alma Desteği:</b> Hatalı girilen günlük üretim kaydı tek tıkla depoya iade edilebilir.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # --- 4. BÖLÜM: SİSTEM ÖZELLİKLERİ (HOVER EFEKTLİ) ---
    st.markdown("### 🌟 Sistem Özellikleri ve Modüller")
    st.markdown("<br>", unsafe_allow_html=True)

    ozellikler_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }
        body { background: transparent; margin: 0; padding: 0; }
        .feature-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
        .metric-card { background: rgba(10, 15, 29, 0.75); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 24px; height: 160px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.3s ease; backdrop-filter: blur(10px); }
        .metric-card:hover { transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }
        .feature-icon { font-size: 32px; }
        .feature-title { font-size: 16px; font-weight: 700; color: #f4f4f5; margin-bottom: 4px; }
        .feature-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    </style>
    </head>
    <body>
        <div class="feature-grid">
            <div class="metric-card">
                <div class="feature-icon">📦</div>
                <div><div class="feature-title">Stok Yönetimi</div><div class="feature-desc">FIFO mantığı ile anlık depo takibi, kritik seviye uyarıları.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">🍲</div>
                <div><div class="feature-title">Yemek Üretimi</div><div class="feature-desc">Reçete bazlı otomatik maliyet hesaplama ve stok düşümü.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">👥</div>
                <div><div class="feature-title">İhtiyaç Sahipleri</div><div class="feature-desc">Şifreli veri saklama ile güvenli kayıt ve porsiyon dağıtımı.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">🔒</div>
                <div><div class="feature-title">Gelişmiş Güvenlik</div><div class="feature-desc">scrypt hash, Fernet şifreleme, oturum yönetimi ve maskeleme.</div></div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(ozellikler_html, height=190, scrolling=False)


    # --- 5. BÖLÜM: EN ALTA TAŞINAN ARKA PLAN DEĞİŞTİRME ---
    if yonetici_modu:
        st.markdown("---")
        with st.expander("🎨 Dashboard Arka Plan Resmini Değiştir (Admin)"):
            yeni_resim = st.file_uploader("Yeni arka plan resmi yükleyin (JPG, PNG)", type=["jpg", "jpeg", "png"], key="dashboard_bg_uploader")
            if yeni_resim is not None:
                b64 = base64.b64encode(yeni_resim.getvalue()).decode()
                st.session_state.dashboard_arka_plan = f"data:{yeni_resim.type};base64,{b64}"
                st.success("✅ Arka plan resmi güncellendi!")
            if st.button("🔄 Varsayılan Resme Dön", key="dashboard_bg_reset"):
                st.session_state.dashboard_arka_plan = varsayilan_arka_plan
                st.rerun()

    # 1. GÜNCEL STOK DURUMU
