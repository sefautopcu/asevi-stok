import base64
import requests as requests_lib
import streamlit as streamlit_lib


@streamlit_lib.cache_data(ttl=1800, show_spinner=False)
def _hava_durumu_verisini_getir(url):
    response = requests_lib.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def _hava_durumu_svg_ve_etiket(yagis_mm, ort_sicaklik):
    """Yağış miktarı ve ortalama sıcaklığa göre özel katmanlı SVG hava ikonu, durum etiketi ve vurgu rengi döndürür."""
    if yagis_mm <= 0.1:
        if ort_sicaklik <= 2:
            svg = (
                '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
                '<circle cx="18" cy="18" r="11" fill="rgba(251,191,36,0.16)"/>'
                '<circle cx="18" cy="18" r="6.5" fill="#fbbf24" stroke="#fde68a" stroke-width="1.2"/>'
                '<g stroke="#fbbf24" stroke-width="1.8" stroke-linecap="round">'
                '<line x1="18" y1="4" x2="18" y2="7"/><line x1="18" y1="29" x2="18" y2="32"/>'
                '<line x1="4" y1="18" x2="7" y2="18"/><line x1="29" y1="18" x2="32" y2="18"/>'
                '<line x1="8.1" y1="8.1" x2="10.2" y2="10.2"/><line x1="25.8" y1="25.8" x2="27.9" y2="27.9"/>'
                '<line x1="27.9" y1="8.1" x2="25.8" y2="10.2"/><line x1="10.2" y1="25.8" x2="8.1" y2="27.9"/>'
                '</g>'
                '</svg>'
            )
            return svg, "Açık · Ayaz", "#38bdf8"
        svg = (
            '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
            '<circle cx="18" cy="18" r="12" fill="rgba(245,158,11,0.20)"/>'
            '<circle cx="18" cy="18" r="7" fill="#fbbf24" stroke="#fef08a" stroke-width="1.3"/>'
            '<g stroke="#fbbf24" stroke-width="2" stroke-linecap="round">'
            '<line x1="18" y1="3.5" x2="18" y2="6.8"/><line x1="18" y1="29.2" x2="18" y2="32.5"/>'
            '<line x1="3.5" y1="18" x2="6.8" y2="18"/><line x1="29.2" y1="18" x2="32.5" y2="18"/>'
            '<line x1="7.8" y1="7.8" x2="10.1" y2="10.1"/><line x1="25.9" y1="25.9" x2="28.2" y2="28.2"/>'
            '<line x1="28.2" y1="7.8" x2="25.9" y2="10.1"/><line x1="10.1" y1="25.9" x2="7.8" y2="28.2"/>'
            '</g>'
            '</svg>'
        )
        return svg, "Güneşli", "#fbbf24"

    if ort_sicaklik <= 1.5:
        svg = (
            '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
            '<path d="M11 23H25.5C28.5 23 31 20.6 31 17.6C31 14.8 28.9 12.5 26.1 12.2C25.1 8.6 21.8 6 18 6C13.6 6 10 9.4 9.7 13.7C7.3 14.3 5.5 16.4 5.5 19C5.5 21.2 7.3 23 11 23Z" fill="rgba(56,189,248,0.22)" stroke="#7dd3fc" stroke-width="1.7" stroke-linejoin="round"/>'
            '<g fill="#e0f2fe">'
            '<circle cx="12.5" cy="27.5" r="1.4"/><circle cx="18" cy="29.5" r="1.4"/><circle cx="23.5" cy="27.5" r="1.4"/>'
            '</g>'
            '</svg>'
        )
        return svg, "Kar Yağışlı", "#7dd3fc"

    if yagis_mm < 10:
        svg = (
            '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
            '<path d="M11 22.5H25.5C28.5 22.5 31 20.1 31 17.1C31 14.3 28.9 12 26.1 11.7C25.1 8.1 21.8 5.5 18 5.5C13.6 5.5 10 8.9 9.7 13.2C7.3 13.8 5.5 15.9 5.5 18.5C5.5 20.7 7.3 22.5 11 22.5Z" fill="rgba(56,189,248,0.20)" stroke="#38bdf8" stroke-width="1.7" stroke-linejoin="round"/>'
            '<g stroke="#38bdf8" stroke-width="1.9" stroke-linecap="round">'
            '<line x1="13" y1="25.5" x2="11.5" y2="29.5"/><line x1="18.5" y1="25.5" x2="17" y2="29.5"/><line x1="24" y1="25.5" x2="22.5" y2="29.5"/>'
            '</g>'
            '</svg>'
        )
        return svg, "Yağmurlu", "#38bdf8"

    svg = (
        '<svg width="34" height="34" viewBox="0 0 36 36" fill="none">'
        '<path d="M11 22H25.5C28.5 22 31 19.6 31 16.6C31 13.8 28.9 11.5 26.1 11.2C25.1 7.6 21.8 5 18 5C13.6 5 10 8.4 9.7 12.7C7.3 13.3 5.5 15.4 5.5 18C5.5 20.2 7.3 22 11 22Z" fill="rgba(99,102,241,0.24)" stroke="#818cf8" stroke-width="1.7" stroke-linejoin="round"/>'
        '<path d="M18.5 22.5L15.5 27.5H19L17 32" stroke="#fbbf24" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'
        '<line x1="12" y1="25" x2="10.5" y2="29.5" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round"/>'
        '<line x1="24.5" y1="25" x2="23" y2="29.5" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round"/>'
        '</svg>'
    )
    return svg, "Sağanak", "#818cf8"


def dashboard_sayfasi(
    st,
    aktif_k_maskeleri,
    yonetici_modu,
    components,
    dashboard_ozet_hesapla,
    dashboard_operasyonel_istatistikleri,
    anlik_hava_gosterge,
    requests,
    datetime,
    html_escape,
):
    panel_bg = "rgba(10, 15, 29, 0.75)"
    panel_strong_bg = "rgba(6, 10, 20, 0.85)"
    panel_border = "rgba(16, 185, 129, 0.35)"
    panel_text = "#f4f4f5"
    panel_muted = "#94a3b8"
    panel_accent = "#10b981"
    panel_shadow = "rgba(16,185,129,.25)"

    # Üstteki varsayılan Streamlit boşluğunu kaldır
    st.markdown(
        "<style>div.block-container { padding-top: 1.5rem !important; } hr { margin-top: 0rem !important; margin-bottom: 0rem !important; }</style>",
        unsafe_allow_html=True,
    )

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
    stok_degeri_gosterim = (
        "🔒 Gizli"
        if stok_maskeli
        else f"{toplam_stok_degeri:,.2f} ₺".replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    urun_cesidi_gosterim = (
        "🔒 Gizli" if urun_maskeli else f"{urun_cesidi_sayisi} Çeşit"
    )
    personel_gosterim = (
        "🔒 Gizli" if personel_maskeli else f"{aktif_personel_sayisi} Kişi"
    )

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

    # --- ERZURUM AZİZİYE 7 GÜNLÜK HAVA DURUMU VERİSİ ---
    hava_durumu_html = ""
    anlik_hava_gosterge = ""
    hafta_aralik_metni = "Canlı Meteoroloji"
    try:
        hava_url = "https://api.open-meteo.com/v1/forecast?latitude=39.95&longitude=41.10&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&current_weather=true&timezone=Europe/Istanbul&forecast_days=7"
        hava_veri = _hava_durumu_verisini_getir(hava_url)

        if "current_weather" in hava_veri:
            cw = hava_veri["current_weather"]
            a_temp = cw.get("temperature", 0)
            a_code = cw.get("weathercode", 0)

            if a_code == 0:
                a_emoji = "☀️"
            elif a_code in [1, 2, 3]:
                a_emoji = "🌤️"
            elif a_code in [45, 48]:
                a_emoji = "🌫️"
            elif a_code in [51, 53, 55, 56, 57]:
                a_emoji = "🌦️"
            elif a_code in [61, 63, 65, 66, 67, 80, 81, 82]:
                a_emoji = "🌧️"
            elif a_code in [71, 73, 75, 77, 85, 86]:
                a_emoji = "🌨️"
            elif a_code in [95, 96, 99]:
                a_emoji = "⛈️"
            else:
                a_emoji = "🌡️"

            anlik_hava_gosterge = f"{a_emoji} {a_temp}°C"

        if "daily" in hava_veri:
            gunler = hava_veri["daily"]["time"]
            max_temp = hava_veri["daily"]["temperature_2m_max"]
            min_temp = hava_veri["daily"]["temperature_2m_min"]
            yagis = hava_veri["daily"]["precipitation_sum"]

            aylar_tr_kisa = {
                "01": "Oca", "02": "Şub", "03": "Mar", "04": "Nis",
                "05": "May", "06": "Haz", "07": "Tem", "08": "Ağu",
                "09": "Eyl", "10": "Eki", "11": "Kas", "12": "Ara",
            }
            hafta_gunleri_tr = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

            hafta_min = min(min_temp) if min_temp else -10
            hafta_max = max(max_temp) if max_temp else 20
            sicaklik_aralik = max(hafta_max - hafta_min, 1)

            h_min_str = f"{0 if round(hafta_min) == 0 else int(round(hafta_min))}°C"
            h_max_str = f"{0 if round(hafta_max) == 0 else int(round(hafta_max))}°C"
            hafta_aralik_metni = f"Haftalık Aralık: {h_min_str} / {h_max_str}"

            for i in range(len(gunler)):
                tarih_obj = datetime.datetime.strptime(gunler[i], "%Y-%m-%d")
                gun_adi = f"{tarih_obj.day} {aylar_tr_kisa.get(f'{tarih_obj.month:02d}', '')}"
                hafta_gunu = hafta_gunleri_tr[tarih_obj.weekday()]

                ort_temp = (max_temp[i] + min_temp[i]) / 2
                svg_ikon, durum_etiket, vurgu_renk = _hava_durumu_svg_ve_etiket(yagis[i], ort_temp)

                m_val = 0 if round(max_temp[i]) == 0 else int(round(max_temp[i]))
                n_val = 0 if round(min_temp[i]) == 0 else int(round(min_temp[i]))
                m_temp = f"{m_val}°"
                n_temp = f"{n_val}°"

                # Dinamik termal aralık çubuğu konumu ve genişliği
                sol_yuzde = max(0, min(82, int(((min_temp[i] - hafta_min) / sicaklik_aralik) * 100)))
                genislik_yuzde = max(18, min(100 - sol_yuzde, int(((max_temp[i] - min_temp[i]) / sicaklik_aralik) * 100)))
                bar_gradient = (
                    "linear-gradient(90deg, #38bdf8 0%, #10b981 55%, #fbbf24 100%)"
                    if max_temp[i] > 2
                    else "linear-gradient(90deg, #60a5fa 0%, #38bdf8 100%)"
                )

                bugun_mu = i == 0
                kart_border = "1px solid rgba(16, 185, 129, 0.58)" if bugun_mu else "1px solid rgba(148, 163, 184, 0.16)"
                kart_bg = (
                    "linear-gradient(160deg, rgba(16, 185, 129, 0.16) 0%, rgba(15, 23, 42, 0.88) 100%)"
                    if bugun_mu
                    else "linear-gradient(160deg, rgba(15, 23, 42, 0.84) 0%, rgba(10, 15, 29, 0.72) 100%)"
                )
                ust_rozet = (
                    '<span style="font-size: 9.5px; font-weight: 800; letter-spacing: 0.7px; color: #10b981; background: rgba(16, 185, 129, 0.18); border: 1px solid rgba(16, 185, 129, 0.42); padding: 2px 7px; border-radius: 999px;">BUGÜN</span>'
                    if bugun_mu
                    else f'<span style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">{hafta_gunu}</span>'
                )

                hava_durumu_html += f"""
                    <div class="weather-day-card" style="background: {kart_bg}; border: {kart_border};">
                        <div style="margin-bottom: 8px;">{ust_rozet}</div>
                        <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(15, 23, 42, 0.78); border: 1px solid {vurgu_renk}33; display: flex; align-items: center; justify-content: center; margin-bottom: 8px;">
                            {svg_ikon}
                        </div>
                        <div style="font-size: 10.5px; font-weight: 600; color: {vurgu_renk}; margin-bottom: 6px;">{durum_etiket}</div>
                        <div style="display: flex; align-items: baseline; justify-content: center; gap: 6px; margin-bottom: 8px;">
                            <span style="font-size: 16px; font-weight: 800; color: #f8fafc;">{m_temp}</span>
                            <span style="font-size: 12px; font-weight: 600; color: #64748b;">/</span>
                            <span style="font-size: 12.5px; font-weight: 600; color: #94a3b8;">{n_temp}</span>
                        </div>
                        <div style="width: 100%; height: 6px; background: rgba(15, 23, 42, 0.95); border-radius: 999px; position: relative; overflow: hidden; margin-bottom: 8px; border: 1px solid rgba(148, 163, 184, 0.14);">
                            <div style="position: absolute; left: {sol_yuzde}%; width: {genislik_yuzde}%; height: 100%; background: {bar_gradient}; border-radius: 999px;"></div>
                        </div>
                        <div style="font-size: 11px; font-weight: 600; color: #cbd5e1;">{gun_adi}</div>
                    </div>
                """
    except Exception:
        hava_durumu_html = "<div style='color: #94a3b8; text-align: center; width: 100%; padding: 20px;'>Hava durumu verisi alınamadı.</div>"

    kat_icerik = (
        '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>'
        if kat_maskeli
        else f'<div class="progress-row"><div class="progress-title"><span>1. Kuru Gıda</span><span class="text-white">{yuzde_gida}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_gida}%; background: #10b981;"></div></div></div><div class="progress-row"><div class="progress-title"><span>2. Sebze</span><span class="text-white">{yuzde_sebze}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_sebze}%; background: #38bdf8;"></div></div></div><div class="progress-row"><div class="progress-title"><span>3. Yağ</span><span class="text-white">{yuzde_yag}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_yag}%; background: #a855f7;"></div></div></div>'
    )

    depo_icerik = (
        '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>'
        if depo_maskeli
        else depo_html_satirlari
    )

    op_icerik = (
        '<div style="text-align: center; color: #ef4444; margin-top: 30px;">🔒 Bu alan maskelenmiştir.</div>'
        if op_maskeli
        else f'<div class="progress-row"><div class="progress-title"><span>Kritik Seviyede</span><span class="text-white">{kritik_urun_sayisi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_kritik}%; background: #ef4444;"></div></div></div><div class="progress-row"><div class="progress-title"><span>Güvenli Stokta</span><span class="text-white">{guvenli_urun_sayisi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_guvenli}%; background: #10b981;"></div></div></div><div class="progress-row"><div class="progress-title"><span>🔴 SKT Süresi Geçen</span><span class="text-white">{skt_kirmizi} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_kirmizi*10, 100)}%; background: #ef4444;"></div></div></div><div class="progress-row"><div class="progress-title"><span>🟠 SKT\'si Yaklaşan</span><span class="text-white">{skt_turuncu} Ürün</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_turuncu*10, 100)}%; background: #f59e0b;"></div></div></div>'
    )

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

        .weather-panel {{
            background: linear-gradient(135deg, rgba(10, 15, 29, 0.92) 0%, rgba(15, 23, 42, 0.86) 60%, rgba(6, 78, 59, 0.35) 100%);
            border: 1px solid rgba(56, 189, 248, 0.34);
            border-radius: 18px;
            padding: 20px 22px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.32);
            transition: all 0.3s ease;
        }}
        .weather-panel:hover {{
            border-color: rgba(56, 189, 248, 0.65);
            box-shadow: 0 0 32px -4px rgba(56, 189, 248, 0.32);
        }}
        .weather-grid {{
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 10px;
            margin-top: 14px;
        }}
        .weather-day-card {{
            border-radius: 14px;
            padding: 12px 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
            backdrop-filter: blur(8px);
        }}
        .weather-day-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(56, 189, 248, 0.6) !important;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
        }}
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

            <!-- CANLI HAVA DURUMU KARTLARI -->
            <div class="weather-panel">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 42px; height: 42px; border-radius: 12px; background: radial-gradient(circle at 30% 25%, rgba(251, 191, 36, 0.25), rgba(15, 23, 42, 0.95) 75%); border: 1px solid rgba(251, 191, 36, 0.42); display: flex; align-items: center; justify-content: center;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                <circle cx="9.5" cy="9.5" r="4" fill="#fbbf24"/>
                                <path d="M9.5 3V4.5M9.5 14.5V16M3 9.5H4.5M14.5 9.5H16M4.9 4.9L6 6M13 13L14.1 14.1M14.1 4.9L13 6" stroke="#fbbf24" stroke-width="1.6" stroke-linecap="round"/>
                                <path d="M9 19H18.5C20.4 19 22 17.4 22 15.5C22 13.7 20.6 12.2 18.8 12C18.2 9.7 16.1 8 13.6 8C10.8 8 8.5 10.2 8.3 12.9C6.7 13.3 5.5 14.7 5.5 16.4C5.5 17.8 6.7 19 9 19Z" fill="rgba(56,189,248,0.25)" stroke="#38bdf8" stroke-width="1.6" stroke-linejoin="round"/>
                            </svg>
                        </div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 10px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; color: #38bdf8; background: rgba(56, 189, 248, 0.14); border: 1px solid rgba(56, 189, 248, 0.34); padding: 2px 8px; border-radius: 999px;">ERZURUM / AZİZİYE</span>
                            </div>
                            <div style="font-size: 1.12rem; font-weight: 800; color: #f8fafc; margin-top: 3px;">7 Günlük Hava Tahmini & Sevkiyat Koşulları</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 11.5px; font-weight: 700; color: #fbbf24; background: rgba(245, 158, 11, 0.14); border: 1px solid rgba(245, 158, 11, 0.34); padding: 5px 12px; border-radius: 10px;">{hafta_aralik_metni}</span>
                    </div>
                </div>
                <div class="weather-grid">
                    {hava_durumu_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(hero_html, height=1260, scrolling=False)

    # --- 3. BÖLÜM: EN ALT (YEMEK SEÇİMİ + CANLI MALİYET ÖZET PANELİ) ---
    st.markdown("---")
    st.markdown(
        """
<div style="display:flex;align-items:center;gap:12px;margin:14px 0 12px 0;">
<div style="width:40px;height:40px;min-width:40px;border-radius:12px;background:radial-gradient(circle at 30% 25%,rgba(16,185,129,0.25),rgba(15,23,42,0.96) 75%);border:1px solid rgba(16,185,129,0.42);box-shadow:0 0 18px rgba(16,185,129,0.20);display:flex;align-items:center;justify-content:center;">
<svg width="21" height="21" viewBox="0 0 24 24" fill="none">
<rect x="4" y="2" width="16" height="20" rx="3" stroke="#10b981" stroke-width="1.9"/>
<rect x="7.5" y="5.5" width="9" height="3.5" rx="1" fill="rgba(251,191,36,0.24)" stroke="#fbbf24" stroke-width="1.5"/>
<circle cx="8.5" cy="13" r="1" fill="#38bdf8"/><circle cx="12" cy="13" r="1" fill="#38bdf8"/><circle cx="15.5" cy="13" r="1" fill="#38bdf8"/>
<circle cx="8.5" cy="17" r="1" fill="#10b981"/><circle cx="12" cy="17" r="1" fill="#10b981"/><circle cx="15.5" cy="17" r="1" fill="#fbbf24"/>
</svg>
</div>
<div>
<span style="font-size:0.66rem;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;color:#10b981;background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.34);padding:2px 8px;border-radius:999px;">MENÜ MALİYET SİMÜLATÖRÜ</span>
<div style="font-size:1.05rem;font-weight:800;color:#f8fafc;margin-top:2px;">Geçmiş Üretim Reçetesi &amp; Porsiyon Ölçekleme</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    menu_secenekleri = {}
    if gecmis_uretimler:
        for item in gecmis_uretimler:
            if not item:
                continue
            top_mal = float(item.get("toplam_maliyet", 0)) or sum(
                float(m.get("tutar", 0)) for m in item.get("malzemeler", [])
            )
            kisi = int(item.get("kisi_sayisi", 1) or 1)
            item["kisi_basi"] = top_mal / kisi if kisi > 0 else 0.0
            item["kalem_sayisi"] = len(item.get("malzemeler", []))
            menu_secenekleri[
                f"{item.get('tarih', '-')} | {item.get('yemek_adi', '-')} ({kisi} Kişi)"
            ] = item

    if not menu_secenekleri:
        menu_secenekleri = {
            "Henüz Kayıt Yok": {
                "tarih": "-",
                "yemek_adi": "Kayıt Yok",
                "kisi_basi": 0.0,
                "kalem_sayisi": 0,
            }
        }

    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        secilen_key = st.selectbox(
            "📋 Geçmişte Çıkan Yemeği / Menüyü Seçin",
            options=list(menu_secenekleri.keys()),
        )
    with col_sel2:
        kisi_sayisi = st.slider(
            "Yararlanılan Kişi Sayısı (Simülasyon)", 10, 1000, 230, step=10
        )

    secilen_veri = menu_secenekleri[secilen_key]
    toplam_tl = secilen_veri.get("kisi_basi", 0.0) * kisi_sayisi

    st.markdown(
        f"""
<style>
.cost-panel {{ background: rgba(10, 15, 29, 0.85); background: linear-gradient(135deg, rgba(10, 15, 29, 0.94) 0%, rgba(15, 23, 42, 0.88) 60%, rgba(6, 78, 59, 0.34) 100%); border: 1px solid rgba(16, 185, 129, 0.38); border-radius: 20px; padding: 24px 26px; box-shadow: 0 12px 32px rgba(0, 0, 0, 0.36), inset 0 1px 0 rgba(52, 211, 153, 0.14); margin-top: 8px; margin-bottom: 26px; }}
.cost-top-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 18px;
}}
.cost-header {{
    font-size: 1.2rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.01em;
}}
.cost-meta-pills {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}}
.cost-pill {{
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 11px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}}
.inner-box {{
    background: linear-gradient(160deg, rgba(6, 10, 20, 0.84) 0%, rgba(15, 23, 42, 0.78) 100%);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 16px;
    padding: 20px;
}}
.cost-row {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 16px;
}}
.cost-card {{
    background: linear-gradient(155deg, rgba(15, 23, 42, 0.94) 0%, rgba(30, 41, 59, 0.80) 100%);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 15px;
    padding: 18px 20px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.24);
    transition: transform 0.22s ease, border-color 0.22s ease;
}}
.cost-card:hover {{
    transform: translateY(-3px);
}}
.cost-num-green {{
    font-size: 1.75rem;
    font-weight: 800;
    color: #10b981;
    margin-top: 6px;
    letter-spacing: -0.02em;
}}
.cost-num-blue {{
    font-size: 1.75rem;
    font-weight: 800;
    color: #38bdf8;
    margin-top: 6px;
    letter-spacing: -0.02em;
}}
</style>
<div class="cost-panel">
    <div class="cost-top-bar">
        <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:46px;height:46px;min-width:46px;border-radius:14px;background:radial-gradient(circle at 30% 25%,rgba(251,191,36,0.24),rgba(15,23,42,0.96) 75%);border:1px solid rgba(251,191,36,0.44);box-shadow:0 0 20px rgba(251,191,36,0.18);display:flex;align-items:center;justify-content:center;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <defs>
                        <linearGradient id="costPanelGrad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stop-color="#34d399"/>
                            <stop offset="55%" stop-color="#10b981"/>
                            <stop offset="100%" stop-color="#fbbf24"/>
                        </linearGradient>
                    </defs>
                    <path d="M3 3v18h18" stroke="url(#costPanelGrad)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 15l4-4 3 3 6-7" stroke="#fbbf24" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="20" cy="7" r="2" fill="#34d399"/>
                </svg>
            </div>
            <div>
                <span style="font-size:0.65rem;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;color:#fbbf24;background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.34);padding:2px 8px;border-radius:999px;">CANLI REÇETE ANALİZİ</span>
                <div class="cost-header" style="margin-top:3px;">Canlı Maliyet Özet Paneli</div>
            </div>
        </div>
        <div class="cost-meta-pills">
            <span class="cost-pill" style="color:#cbd5e1;background:rgba(148,163,184,0.12);border:1px solid rgba(148,163,184,0.26);">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                Tarih: {html_escape(str(secilen_veri.get('tarih', '-')))}
            </span>
            <span class="cost-pill" style="color:#38bdf8;background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.32);">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
                {secilen_veri.get('kalem_sayisi', 0)} Kalem Malzeme
            </span>
            <span class="cost-pill" style="color:#10b981;background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.34);">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                Simülasyon: {kisi_sayisi} Kişi
            </span>
        </div>
    </div>
    <div class="inner-box">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid rgba(148,163,184,0.14);">
            <div style="width:36px;height:36px;min-width:36px;border-radius:10px;background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.34);display:flex;align-items:center;justify-content:center;">
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16a1 1 0 0 1 1 1v2a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6v-2a1 1 0 0 1 1-1Z"/><path d="M8 7c0-1.5 1-2 1-3.5"/><path d="M12 7c0-1.5 1-2 1-3.5"/><path d="M16 7c0-1.5 1-2 1-3.5"/></svg>
            </div>
            <div>
                <div style="font-size:10.5px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#94a3b8;">SEÇİLİ YEMEK MENÜSÜ</div>
                <div style="font-size:1.18rem;font-weight:800;color:#ffffff;line-height:1.3;margin-top:2px;">{html_escape(str(secilen_veri.get('yemek_adi', '-')))}</div>
            </div>
        </div>
        <div class="cost-row">
            <div class="cost-card" style="border-top:3px solid #10b981;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <span style="font-size:11px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;">Menü Toplam Maliyeti</span>
                    <div style="width:32px;height:32px;border-radius:9px;background:rgba(16,185,129,0.14);border:1px solid rgba(16,185,129,0.34);display:flex;align-items:center;justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>
                    </div>
                </div>
                <div class="cost-num-green">{toplam_tl:,.2f} ₺</div>
                <div style="font-size:11.5px;color:#64748b;margin-top:4px;">{kisi_sayisi} kişilik toplam hammadde tutarı</div>
            </div>
            <div class="cost-card" style="border-top:3px solid #38bdf8;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <span style="font-size:11px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;">Kişi Başı Maliyet ({kisi_sayisi} Kişi)</span>
                    <div style="width:32px;height:32px;border-radius:9px;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.34);display:flex;align-items:center;justify-content:center;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                    </div>
                </div>
                <div class="cost-num-blue">{secilen_veri.get('kisi_basi', 0.0):,.2f} ₺</div>
                <div style="font-size:11.5px;color:#64748b;margin-top:4px;">1 porsiyon birim üretim maliyeti</div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;background:rgba(16,185,129,0.10);border:1px solid rgba(16,185,129,0.28);border-left:4px solid #10b981;padding:11px 14px;border-radius:10px;font-size:12.5px;color:#cbd5e1;">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" style="min-width:17px;"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>
            <span><b style="color:#f8fafc;">Son İşlem Geri Alma Desteği:</b> Hatalı girilen günlük üretim kaydı tek tıkla depoya iade edilebilir.</span>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # --- 4. BÖLÜM: SİSTEM ÖZELLİKLERİ (HOVER EFEKTLİ) ---
    st.markdown(
        """
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin:8px 0 14px 0;">
<div style="display:flex;align-items:center;gap:14px;">
<div style="width:46px;height:46px;min-width:46px;border-radius:14px;background:radial-gradient(circle at 30% 25%,rgba(56,189,248,0.25),rgba(15,23,42,0.96) 75%);border:1px solid rgba(56,189,248,0.42);box-shadow:0 0 20px rgba(56,189,248,0.20);display:flex;align-items:center;justify-content:center;">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
<defs>
<linearGradient id="sysModGrad" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
<stop offset="0%" stop-color="#38bdf8"/>
<stop offset="55%" stop-color="#10b981"/>
<stop offset="100%" stop-color="#fbbf24"/>
</linearGradient>
</defs>
<rect x="3" y="3" width="7" height="7" rx="2" stroke="url(#sysModGrad)" stroke-width="1.9"/>
<rect x="14" y="3" width="7" height="7" rx="2" stroke="url(#sysModGrad)" stroke-width="1.9"/>
<rect x="3" y="14" width="7" height="7" rx="2" stroke="url(#sysModGrad)" stroke-width="1.9"/>
<path d="M17.5 14v7M14 17.5h7" stroke="#fbbf24" stroke-width="2" stroke-linecap="round"/>
</svg>
</div>
<div>
<span style="font-size:0.66rem;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;color:#38bdf8;background:rgba(56,189,248,0.14);border:1px solid rgba(56,189,248,0.34);padding:2px 8px;border-radius:999px;">ÇEKİRDEK ALTYAPI</span>
<div style="font-size:1.25rem;font-weight:800;color:#f8fafc;margin-top:3px;">Sistem Özellikleri ve Modüller</div>
<div style="font-size:0.82rem;color:#94a3b8;margin-top:1px;">Uçtan uca aşevi stok, üretim, sosyal dağıtım ve veri güvenliği mimarisi</div>
</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    ozellikler_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }
        body { background: transparent; margin: 0; padding: 4px 2px; }
        .feature-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .mod-card {
            background: linear-gradient(155deg, rgba(15, 23, 42, 0.92) 0%, rgba(10, 15, 29, 0.84) 100%);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 18px;
            padding: 15px 18px;
            min-height: 168px;
            height: 174px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.28s ease, border-color 0.28s ease, box-shadow 0.28s ease;
            backdrop-filter: blur(12px);
        }
        .mod-card:hover { transform: translateY(-5px); }
        .mod-emerald { border-top: 3px solid #10b981; }
        .mod-emerald:hover { border-color: rgba(16, 185, 129, 0.72); box-shadow: 0 10px 28px -4px rgba(16, 185, 129, 0.34); }
        .mod-amber { border-top: 3px solid #fbbf24; }
        .mod-amber:hover { border-color: rgba(251, 191, 36, 0.72); box-shadow: 0 10px 28px -4px rgba(251, 191, 36, 0.30); }
        .mod-purple { border-top: 3px solid #a855f7; }
        .mod-purple:hover { border-color: rgba(168, 85, 247, 0.72); box-shadow: 0 10px 28px -4px rgba(168, 85, 247, 0.32); }
        .mod-sky { border-top: 3px solid #38bdf8; }
        .mod-sky:hover { border-color: rgba(56, 189, 248, 0.72); box-shadow: 0 10px 28px -4px rgba(56, 189, 248, 0.34); }
        .mod-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
        .mod-icon-box {
            width: 40px; height: 40px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
        }
        .mod-tag {
            font-size: 9.5px; font-weight: 800; letter-spacing: 0.8px;
            padding: 3px 8px; border-radius: 999px; text-transform: uppercase;
        }
        .feature-title { font-size: 15.5px; font-weight: 800; color: #f8fafc; margin-bottom: 4px; }
        .feature-desc { font-size: 12px; color: #94a3b8; line-height: 1.44; }
    </style>
    </head>
    <body>
        <div class="feature-grid">
            <div class="mod-card mod-emerald">
                <div class="mod-top">
                    <div class="mod-icon-box" style="background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.38); box-shadow: 0 0 16px rgba(16, 185, 129, 0.18);">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                    </div>
                    <span class="mod-tag" style="color: #10b981; background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.32);">FIFO ENVANTER</span>
                </div>
                <div>
                    <div class="feature-title">Stok Yönetimi</div>
                    <div class="feature-desc">FIFO mantığı ile anlık depo takibi, kritik seviye uyarıları.</div>
                </div>
            </div>
            <div class="mod-card mod-amber">
                <div class="mod-top">
                    <div class="mod-icon-box" style="background: rgba(251, 191, 36, 0.14); border: 1px solid rgba(251, 191, 36, 0.38); box-shadow: 0 0 16px rgba(251, 191, 36, 0.18);">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12h16a1 1 0 0 1 1 1v2a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6v-2a1 1 0 0 1 1-1Z"/><path d="M8 7c0-1.5 1-2 1-3.5"/><path d="M12 7c0-1.5 1-2 1-3.5"/><path d="M16 7c0-1.5 1-2 1-3.5"/></svg>
                    </div>
                    <span class="mod-tag" style="color: #fbbf24; background: rgba(251, 191, 36, 0.14); border: 1px solid rgba(251, 191, 36, 0.32);">REÇETE &amp; KALORİ</span>
                </div>
                <div>
                    <div class="feature-title">Yemek Üretimi</div>
                    <div class="feature-desc">Reçete bazlı otomatik maliyet hesaplama ve stok düşümü.</div>
                </div>
            </div>
            <div class="mod-card mod-purple">
                <div class="mod-top">
                    <div class="mod-icon-box" style="background: rgba(168, 85, 247, 0.14); border: 1px solid rgba(168, 85, 247, 0.38); box-shadow: 0 0 16px rgba(168, 85, 247, 0.18);">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    </div>
                    <span class="mod-tag" style="color: #c084fc; background: rgba(168, 85, 247, 0.14); border: 1px solid rgba(168, 85, 247, 0.32);">SOSYAL DAĞITIM</span>
                </div>
                <div>
                    <div class="feature-title">İhtiyaç Sahipleri</div>
                    <div class="feature-desc">Şifreli veri saklama ile güvenli kayıt ve porsiyon dağıtımı.</div>
                </div>
            </div>
            <div class="mod-card mod-sky">
                <div class="mod-top">
                    <div class="mod-icon-box" style="background: rgba(56, 189, 248, 0.14); border: 1px solid rgba(56, 189, 248, 0.38); box-shadow: 0 0 16px rgba(56, 189, 248, 0.18);">
                        <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><rect x="9.5" y="10.5" width="5" height="4" rx="1"/><path d="M10.5 10.5V9a1.5 1.5 0 0 1 3 0v1.5"/></svg>
                    </div>
                    <span class="mod-tag" style="color: #38bdf8; background: rgba(56, 189, 248, 0.14); border: 1px solid rgba(56, 189, 248, 0.32);">UÇTAN UCA ŞİFRELEME</span>
                </div>
                <div>
                    <div class="feature-title">Gelişmiş Güvenlik</div>
                    <div class="feature-desc">scrypt hash, Fernet şifreleme, oturum yönetimi ve maskeleme.</div>
                </div>
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
            yeni_resim = st.file_uploader(
                "Yeni arka plan resmi yükleyin (JPG, PNG)",
                type=["jpg", "jpeg", "png"],
                key="dashboard_bg_uploader",
            )
            if yeni_resim is not None:
                b64 = base64.b64encode(yeni_resim.getvalue()).decode()
                yeni_uri = f"data:{yeni_resim.type};base64,{b64}"
                if st.session_state.dashboard_arka_plan != yeni_uri:
                    st.session_state.dashboard_arka_plan = yeni_uri
                    st.rerun()
                st.success("✅ Arka plan resmi güncellendi!")
            if st.button("🔄 Varsayılan Resme Dön", key="dashboard_bg_reset"):
                st.session_state.dashboard_arka_plan = varsayilan_arka_plan
                st.rerun()
