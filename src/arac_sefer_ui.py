import datetime
import html
import time

SAYFA_ETIKETI_ARAC_SEFER = "Sıcak Yemek Dağıtım Araç ve Sefer Takibi"


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = SAYFA_ETIKETI_ARAC_SEFER.lower()
    for maske in aktif_k_maskeleri:
        m_str = str(maske or "").strip().lower()
        if m_str in ("arac_seferleri", "arac_sefer") or hedef in m_str:
            return True
    return False


def _tarih_kalan_gun(tarih_str):
    """YYYY-MM-DD biçimindeki tarihe kaç gün kaldığını döndürür."""
    metin = str(tarih_str or "").strip()[:10]
    if not metin:
        return None
    try:
        hedef = datetime.date.fromisoformat(metin)
        return (hedef - datetime.date.today()).days
    except ValueError:
        return None


def _belge_durum_rozeti(etiket, tarih_str):
    kalan = _tarih_kalan_gun(tarih_str)
    if kalan is None:
        return (
            f'<span style="background: rgba(148,163,184,0.14); color: #94a3b8; '
            f'padding: 2px 8px; border-radius: 999px; font-size: 0.74rem;">'
            f'{html.escape(etiket)}: Kayıt Yok</span>'
        )
    if kalan < 0:
        return (
            f'<span style="background: rgba(244,63,94,0.18); color: #fb7185; '
            f'border: 1px solid rgba(244,63,94,0.4); padding: 2px 8px; border-radius: 999px; '
            f'font-size: 0.74rem; font-weight: 600;">⚠️ {html.escape(etiket)} Süresi Doldu ({html.escape(tarih_str)})</span>'
        )
    if kalan <= 30:
        return (
            f'<span style="background: rgba(245,158,11,0.18); color: #fbbf24; '
            f'border: 1px solid rgba(245,158,11,0.4); padding: 2px 8px; border-radius: 999px; '
            f'font-size: 0.74rem; font-weight: 600;">⏳ {html.escape(etiket)}: {kalan} gün kaldı ({html.escape(tarih_str)})</span>'
        )
    return (
        f'<span style="background: rgba(16,185,129,0.14); color: #34d399; '
        f'padding: 2px 8px; border-radius: 999px; font-size: 0.74rem;">'
        f'✅ {html.escape(etiket)}: {html.escape(tarih_str)}</span>'
    )


def _kpi_karti_html(ikon, baslik, deger, alt_bilgi, vurgu_renk="#10b981"):
    return f"""
    <div style="
        background: linear-gradient(145deg, #0b1220 0%, #131c31 100%);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-left: 4px solid {vurgu_renk};
        border-radius: 12px;
        padding: 15px 17px;
        margin-bottom: 8px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.30);
    ">
        <div style="font-size: 0.84rem; color: #94a3b8; font-weight: 600; margin-bottom: 5px;">
            {ikon} {html.escape(str(baslik))}
        </div>
        <div style="font-size: 1.6rem; color: #f8fafc; font-weight: 700; line-height: 1.2;">
            {html.escape(str(deger))}
        </div>
        <div style="font-size: 0.77rem; color: #64748b; margin-top: 5px;">
            {html.escape(str(alt_bilgi))}
        </div>
    </div>
    """


def _sefer_karti_html(kayit):
    sid = html.escape(str(kayit.get("id", "-")))
    tarih = html.escape(str(kayit.get("tarih", "-")))
    plaka = html.escape(str(kayit.get("arac_plaka", "-")))
    sofor = html.escape(str(kayit.get("sofor_adi") or "Belirtilmedi"))
    personel = html.escape(str(kayit.get("dagitim_personeli") or "Belirtilmedi"))
    mahalle = html.escape(str(kayit.get("guzergah_mahalle") or "-"))
    cikis = html.escape(str(kayit.get("cikis_saati") or "-"))
    donus = html.escape(str(kayit.get("donus_saati") or "Yolda"))
    cikan_porsiyon = int(kayit.get("sefertas_porsiyon_sayisi") or 0)
    teslim_porsiyon = int(kayit.get("teslim_edilen_porsiyon") or 0)
    bas_km = float(kayit.get("baslangic_km") or 0.0)
    bit_km = float(kayit.get("bitis_km") or 0.0)
    yapilan_km = round(max(0.0, bit_km - bas_km), 1) if bit_km > 0 else 0.0
    durum = str(kayit.get("durum") or "Devam Ediyor")
    notlar = html.escape(str(kayit.get("notlar") or ""))

    tamamlandi = durum == "Tamamlandı"
    vurgu = "#10b981" if tamamlandi else "#f59e0b"
    durum_rozet = (
        '<span style="background: rgba(16,185,129,0.16); color: #34d399; '
        'border: 1px solid rgba(16,185,129,0.35); padding: 3px 10px; '
        'border-radius: 999px; font-size: 0.76rem; font-weight: 600;">✅ Tamamlandı</span>'
        if tamamlandi
        else '<span style="background: rgba(245,158,11,0.16); color: #fbbf24; '
        'border: 1px solid rgba(245,158,11,0.35); padding: 3px 10px; '
        'border-radius: 999px; font-size: 0.76rem; font-weight: 600;">🚚 Dağıtımda (Açık Sefer)</span>'
    )

    sigorta_rozet = _belge_durum_rozeti("Sigorta", kayit.get("sigorta_bitis_tarihi"))
    muayene_rozet = _belge_durum_rozeti("Muayene", kayit.get("muayene_bitis_tarihi"))

    not_html = (
        f'<div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(148,163,184,0.2); '
        f'font-size: 0.82rem; color: #cbd5e1;">📝 <i>{notlar}</i></div>'
        if notlar
        else ""
    )

    return f"""
    <div style="
        background: linear-gradient(145deg, #0b1220 0%, #131c31 100%);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-left: 5px solid {vurgu};
        border-radius: 12px;
        padding: 15px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
            <div>
                <span style="background: rgba(56,189,248,0.14); color: #7dd3fc; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; margin-right: 8px;">
                    {sid}
                </span>
                <span style="font-size: 1.06rem; font-weight: 700; color: #f8fafc;">
                    🚐 {plaka} — {mahalle}
                </span>
                <span style="font-size: 0.82rem; color: #94a3b8; margin-left: 8px;">({tarih})</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                {sigorta_rozet}
                {muayene_rozet}
                {durum_rozet}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(195px, 1fr)); gap: 8px; font-size: 0.85rem; color: #cbd5e1;">
            <div>🧑‍✈️ <b>Şoför:</b> {sofor}</div>
            <div>🤝 <b>Dağıtım Pers.:</b> {personel}</div>
            <div>🕒 <b>Saat:</b> {cikis} → {donus}</div>
            <div>🍲 <b>Porsiyon:</b> {teslim_porsiyon} / {cikan_porsiyon} kap</div>
            <div>🛣️ <b>Kilometre:</b> {bas_km:,.1f} → {bit_km:,.1f} km (<b>+{yapilan_km:,.1f} km</b>)</div>
        </div>
        {not_html}
    </div>
    """


def aylik_sefer_analizi_hesapla(seferler, yil_ay):
    """Belirtilen YYYY-MM ayı için araç ve mahalle bazlı özet istatistik üretir."""
    filtreli = [
        s for s in (seferler or [])
        if str(s.get("tarih") or "").startswith(str(yil_ay))
    ]

    arac_ozet = {}
    mahalle_ozet = {}

    for s in filtreli:
        plaka = str(s.get("arac_plaka") or "Bilinmeyen Araç").strip().upper()
        mahalle = str(s.get("guzergah_mahalle") or "Belirtilmemiş").strip()
        cikan = int(s.get("sefertas_porsiyon_sayisi") or 0)
        teslim = int(s.get("teslim_edilen_porsiyon") or 0)
        etkili_porsiyon = teslim if teslim > 0 else cikan
        bas_km = float(s.get("baslangic_km") or 0.0)
        bit_km = float(s.get("bitis_km") or 0.0)
        km = round(max(0.0, bit_km - bas_km), 2) if bit_km > 0 else 0.0

        if plaka not in arac_ozet:
            arac_ozet[plaka] = {
                "Araç Plakası": plaka,
                "Toplam Sefer": 0,
                "Çıkan Sefertas / Porsiyon": 0,
                "Teslim Edilen Porsiyon": 0,
                "Toplam Km": 0.0,
            }
        arac_ozet[plaka]["Toplam Sefer"] += 1
        arac_ozet[plaka]["Çıkan Sefertas / Porsiyon"] += cikan
        arac_ozet[plaka]["Teslim Edilen Porsiyon"] += etkili_porsiyon
        arac_ozet[plaka]["Toplam Km"] = round(arac_ozet[plaka]["Toplam Km"] + km, 2)

        if mahalle not in mahalle_ozet:
            mahalle_ozet[mahalle] = {
                "Güzergâh / Mahalle": mahalle,
                "Toplam Sefer": 0,
                "Dağıtılan Kap / Porsiyon": 0,
                "Toplam Km": 0.0,
            }
        mahalle_ozet[mahalle]["Toplam Sefer"] += 1
        mahalle_ozet[mahalle]["Dağıtılan Kap / Porsiyon"] += etkili_porsiyon
        mahalle_ozet[mahalle]["Toplam Km"] = round(
            mahalle_ozet[mahalle]["Toplam Km"] + km, 2
        )

    return {
        "toplam_sefer": len(filtreli),
        "toplam_porsiyon": sum(x["Teslim Edilen Porsiyon"] for x in arac_ozet.values()),
        "toplam_km": round(sum(x["Toplam Km"] for x in arac_ozet.values()), 2),
        "arac_listesi": sorted(
            arac_ozet.values(), key=lambda x: x["Toplam Sefer"], reverse=True
        ),
        "mahalle_listesi": sorted(
            mahalle_ozet.values(),
            key=lambda x: x["Dağıtılan Kap / Porsiyon"],
            reverse=True,
        ),
    }


def arac_sefer_takip_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    arac_seferlerini_kaydet,
    yeni_id_uret,
    simdi_tr_str,
    silme_onay_kutusu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Sıcak Yemek Dağıtım Araç ve Sefer Takibi sayfası bu kullanıcı profili için maskelenmiştir.")
        return

    if "arac_seferleri" not in st.session_state or not isinstance(st.session_state.arac_seferleri, list):
        st.session_state.arac_seferleri = []

    seferler = st.session_state.arac_seferleri

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(16,185,129,0.16) 0%, rgba(56,189,248,0.10) 100%);
                border: 1px solid rgba(16,185,129,0.28);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.42rem; font-weight: 800; color: #f8fafc;">
                    🚐 Sıcak Yemek Dağıtım Araç ve Sefer Takibi
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Günlük sefer başlatma, dönüş kilometre ve porsiyon kapatma, sigorta/muayene ve aylık güzergâh analizi
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    bugun_str = str(datetime.date.today())
    bugunku_seferler = [s for s in seferler if str(s.get("tarih") or "") == bugun_str]
    acik_seferler = [s for s in seferler if str(s.get("durum") or "Devam Ediyor") != "Tamamlandı"]
    bugun_porsiyon = sum(
        int(s.get("teslim_edilen_porsiyon") or s.get("sefertas_porsiyon_sayisi") or 0)
        for s in bugunku_seferler
    )
    toplam_km_tum = round(
        sum(
            max(0.0, float(s.get("bitis_km") or 0.0) - float(s.get("baslangic_km") or 0.0))
            for s in seferler
            if float(s.get("bitis_km") or 0.0) > 0
        ),
        1,
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("🚐", "Bugünkü Sefer", len(bugunku_seferler), f"{bugun_str} tarihli çıkışlar", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("⏳", "Dağıtımdaki Araç", len(acik_seferler), "Dönüş kaydı bekleyen açık sefer", "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("🍲", "Bugün Dağıtılan Kap", bugun_porsiyon, "Günlük sıcak yemek sefertas/porsiyon", "#10b981"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("🛣️", "Kayıtlı Toplam Km", f"{toplam_km_tum:,.1f} km", "Tamamlanan tüm seferlerin mesafesi", "#a855f7"),
            unsafe_allow_html=True,
        )

    if seferler:
        export_satirlari = [
            {
                "Sefer ID": s.get("id", "-"),
                "Tarih": s.get("tarih", "-"),
                "Araç Plaka": s.get("arac_plaka", "-"),
                "Şoför": s.get("sofor_adi") or "-",
                "Dağıtım Personeli": s.get("dagitim_personeli") or "-",
                "Güzergâh / Mahalle": s.get("guzergah_mahalle") or "-",
                "Çıkış Saati": s.get("cikis_saati") or "-",
                "Dönüş Saati": s.get("donus_saati") or "-",
                "Çıkan Porsiyon": int(s.get("sefertas_porsiyon_sayisi") or 0),
                "Teslim Edilen Porsiyon": int(s.get("teslim_edilen_porsiyon") or 0),
                "Başlangıç Km": float(s.get("baslangic_km") or 0.0),
                "Bitiş Km": float(s.get("bitis_km") or 0.0),
                "Yapılan Km": round(
                    max(0.0, float(s.get("bitis_km") or 0.0) - float(s.get("baslangic_km") or 0.0)),
                    1,
                ) if float(s.get("bitis_km") or 0.0) > 0 else 0.0,
                "Sigorta Bitiş": s.get("sigorta_bitis_tarihi") or "-",
                "Muayene Bitiş": s.get("muayene_bitis_tarihi") or "-",
                "Durum": s.get("durum") or "Devam Ediyor",
                "Notlar": s.get("notlar") or "-",
            }
            for s in seferler
        ]
        excel_bytes = tablo_to_excel_bytes(export_satirlari, "Aziziye Aşevi - Araç ve Sefer Takip Raporu")
        pdf_bytes = tablo_to_html_pdf_bytes("Aziziye Aşevi - Araç ve Sefer Takip Raporu", export_satirlari)
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "arac_sefer_takibi", "arac_sefer_sayfasi")

    # Araç bazlı en son sigorta/muayene bilgilerini hafızada topla (otomatik tamamlama ve uyarı için)
    arac_belge_haritasi = {}
    uyari_mesajlari = []
    for s in seferler:
        plaka = str(s.get("arac_plaka") or "").strip().upper()
        if not plaka:
            continue
        if plaka not in arac_belge_haritasi:
            arac_belge_haritasi[plaka] = {
                "sigorta": str(s.get("sigorta_bitis_tarihi") or "").strip(),
                "muayene": str(s.get("muayene_bitis_tarihi") or "").strip(),
                "son_km": float(s.get("bitis_km") or s.get("baslangic_km") or 0.0),
            }

    for plaka, bilgi in arac_belge_haritasi.items():
        for belge_ad, alan in (("Trafik Sigortası", "sigorta"), ("Araç Muayenesi", "muayene")):
            kalan = _tarih_kalan_gun(bilgi[alan])
            if kalan is not None and kalan < 0:
                uyari_mesajlari.append(f"🚨 **{plaka}** plakalı aracın **{belge_ad}** süresi dolmuş ({bilgi[alan]})!")
            elif kalan is not None and kalan <= 30:
                uyari_mesajlari.append(f"⚠️ **{plaka}** plakalı aracın **{belge_ad}** bitimine **{kalan} gün** kaldı ({bilgi[alan]}).")

    for uyari in uyari_mesajlari:
        st.warning(uyari)

    st.markdown("---")

    sekme_baslat, sekme_kapat, sekme_liste, sekme_analiz = st.tabs(
        [
            "🚀 Sefer Başlat (Çıkış)",
            "🏁 Sefer Kapat (Dönüş)",
            "📋 Sefer Kayıtları & Araç Belgeleri",
            "📊 Aylık Araç & Mahalle Analizi",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: GÜNLÜK SEFER BAŞLATMA
    # ---------------------------------------------------------
    with sekme_baslat:
        if salt_okunur_modu:
            st.warning("🔒 Salt okunur modda yeni sefer başlatılamaz.")
        else:
            kayitli_plakalar = sorted(arac_belge_haritasi.keys())
            secilen_hazir_plaka = st.selectbox(
                "🚐 Kayıtlı Araç Seçin (Yeni plaka girmek için 'Yeni Araç Plakası Gir' seçin)",
                ["Yeni Araç Plakası Gir"] + kayitli_plakalar,
                key="sefer_hazir_plaka_sec",
            )
            varsayilan_plaka = "" if secilen_hazir_plaka == "Yeni Araç Plakası Gir" else secilen_hazir_plaka
            varsayilan_belge = arac_belge_haritasi.get(varsayilan_plaka, {})

            with st.form("yeni_sefer_baslat_formu", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    s_tarih = st.date_input("📅 Sefer Tarihi", value=datetime.date.today())
                    s_plaka = st.text_input(
                        "🚐 Araç Plakası *",
                        value=varsayilan_plaka,
                        placeholder="Örn: 25 ABC 123",
                    ).strip().upper()
                    s_sofor = st.text_input("🧑‍✈️ Şoför Adı Soyadı *", placeholder="Örn: Mehmet Kaya").strip()
                    s_personel = st.text_input("🤝 Dağıtım Personeli", placeholder="Örn: Ali Demir").strip()
                with c2:
                    s_mahalle = st.text_input(
                        "📍 Güzergâh / Mahalleler *",
                        placeholder="Örn: Dadaşkent, Saltuklu, Ilıca Mahalleleri",
                    ).strip()
                    s_cikis_saati = st.text_input(
                        "🕒 Aşevinden Çıkış Saati *",
                        value=simdi_tr_str("%H:%M"),
                        placeholder="Örn: 11:30",
                    ).strip()
                    s_porsiyon = st.number_input(
                        "🍲 Yüklenen Sefertas / Porsiyon Sayısı *",
                        min_value=1,
                        value=50,
                        step=1,
                    )
                    s_bas_km = st.number_input(
                        "🛣️ Başlangıç Kilometresi (Km) *",
                        min_value=0.0,
                        value=float(varsayilan_belge.get("son_km") or 0.0),
                        step=1.0,
                    )

                b1, b2 = st.columns(2)
                with b1:
                    s_sigorta = st.text_input(
                        "🛡️ Sigorta Bitiş Tarihi (YYYY-AA-GG)",
                        value=varsayilan_belge.get("sigorta", ""),
                        placeholder="Örn: 2027-05-15",
                    ).strip()
                with b2:
                    s_muayene = st.text_input(
                        "🔧 Muayene Bitiş Tarihi (YYYY-AA-GG)",
                        value=varsayilan_belge.get("muayene", ""),
                        placeholder="Örn: 2027-08-20",
                    ).strip()

                s_notlar = st.text_area("📝 Sefer Notları", placeholder="Özel teslimat noktası, sıcak kutu adedi vb.", height=70)

                baslat_btn = st.form_submit_button("🚀 Seferi Başlat ve Kaydet", type="primary", use_container_width=True)
                if baslat_btn:
                    if not s_plaka or not s_sofor or not s_mahalle:
                        st.error("⚠️ Lütfen Araç Plakası, Şoför Adı ve Güzergâh/Mahalle alanlarını doldurun.")
                    else:
                        yeni_sefer_id = yeni_id_uret("SFR-", st.session_state.arac_seferleri)
                        yeni_kayit = {
                            "id": yeni_sefer_id,
                            "tarih": str(s_tarih),
                            "arac_plaka": s_plaka,
                            "sofor_adi": s_sofor,
                            "dagitim_personeli": s_personel,
                            "guzergah_mahalle": s_mahalle,
                            "cikis_saati": s_cikis_saati,
                            "donus_saati": "",
                            "sefertas_porsiyon_sayisi": int(s_porsiyon),
                            "teslim_edilen_porsiyon": 0,
                            "baslangic_km": float(s_bas_km),
                            "bitis_km": 0.0,
                            "yapilan_km": 0.0,
                            "sigorta_bitis_tarihi": s_sigorta,
                            "muayene_bitis_tarihi": s_muayene,
                            "durum": "Devam Ediyor",
                            "notlar": s_notlar.strip(),
                        }
                        otomatik_yedek_al(f"Yeni araç seferi başlatıldı: {yeni_sefer_id} ({s_plaka})")
                        st.session_state.arac_seferleri.insert(0, yeni_kayit)
                        arac_seferlerini_kaydet(st.session_state.arac_seferleri)
                        st.success(f"🎉 **{s_plaka}** plakalı araç için **{yeni_sefer_id}** kodlu sefer başlatıldı!")
                        time.sleep(0.8)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 2: DÖNÜŞTE SEFER KAPATMA (BİTİŞ KM & TESLİM EDİLEN PORSİYON)
    # ---------------------------------------------------------
    with sekme_kapat:
        if salt_okunur_modu:
            st.warning("🔒 Salt okunur modda sefer kapatma işlemi yapılamaz.")
        elif not acik_seferler:
            st.info("✅ Şu anda dönüş kaydı bekleyen açık (devam eden) sefer bulunmuyor.")
        else:
            acik_harita = {
                f"{s.get('id')} | {s.get('arac_plaka')} - {s.get('guzergah_mahalle')} (Çıkış: {s.get('cikis_saati')}, {s.get('sefertas_porsiyon_sayisi')} kap)": s
                for s in acik_seferler
            }
            secilen_acik_etiket = st.selectbox(
                "🚚 Kapatılacak Açık Seferi Seçin",
                list(acik_harita.keys()),
                key="kapatilacak_sefer_sec",
            )
            hedef_sefer = acik_harita[secilen_acik_etiket]
            bas_km_val = float(hedef_sefer.get("baslangic_km") or 0.0)
            cikan_porsiyon_val = int(hedef_sefer.get("sefertas_porsiyon_sayisi") or 0)

            with st.form("sefer_kapat_formu"):
                k_col1, k_col2, k_col3 = st.columns(3)
                with k_col1:
                    donus_saati_inp = st.text_input(
                        "🕒 Aşevine Dönüş Saati *",
                        value=simdi_tr_str("%H:%M"),
                    ).strip()
                with k_col2:
                    bitis_km_inp = st.number_input(
                        f"🛣️ Dönüş Bitiş Km * (Başlangıç: {bas_km_val:,.1f} km)",
                        min_value=bas_km_val,
                        value=bas_km_val,
                        step=1.0,
                    )
                with k_col3:
                    teslim_porsiyon_inp = st.number_input(
                        f"🍲 Teslim Edilen Porsiyon * (Çıkan: {cikan_porsiyon_val})",
                        min_value=0,
                        max_value=max(cikan_porsiyon_val, 10000),
                        value=cikan_porsiyon_val,
                        step=1,
                    )

                kapanis_notu = st.text_input(
                    "📝 Dönüş / Teslimat Notu",
                    value=str(hedef_sefer.get("notlar") or ""),
                    placeholder="İade dönen kap varsa veya güzergâh notu ekleyin...",
                ).strip()

                kapat_btn = st.form_submit_button("🏁 Seferi Tamamla ve Kapat", type="primary", use_container_width=True)
                if kapat_btn:
                    if float(bitis_km_inp) < bas_km_val:
                        st.error("⚠️ Bitiş kilometresi başlangıç kilometresinden küçük olamaz.")
                    else:
                        otomatik_yedek_al(f"Araç seferi kapatıldı: {hedef_sefer.get('id')}")
                        hedef_sefer["donus_saati"] = donus_saati_inp
                        hedef_sefer["bitis_km"] = float(bitis_km_inp)
                        hedef_sefer["yapilan_km"] = round(max(0.0, float(bitis_km_inp) - bas_km_val), 2)
                        hedef_sefer["teslim_edilen_porsiyon"] = int(teslim_porsiyon_inp)
                        hedef_sefer["durum"] = "Tamamlandı"
                        hedef_sefer["notlar"] = kapanis_notu

                        arac_seferlerini_kaydet(st.session_state.arac_seferleri)
                        st.success(
                            f"✅ **{hedef_sefer.get('id')}** seferi kapatıldı! "
                            f"Yapılan yol: **{hedef_sefer['yapilan_km']:,.1f} km**, "
                            f"Teslim edilen: **{teslim_porsiyon_inp} porsiyon**."
                        )
                        time.sleep(0.8)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 3: SEFER KAYITLARI VE SİLME
    # ---------------------------------------------------------
    with sekme_liste:
        f1, f2, f3, f4 = st.columns([1.6, 1.2, 1.2, 1.0])
        with f1:
            arama_q = st.text_input("🔍 Sefer Ara", placeholder="Plaka, şoför, mahalle veya ID...", key="sefer_arama_q").strip().lower()
        with f2:
            durum_f = st.selectbox("🚦 Sefer Durumu", ["Tümü", "Devam Ediyor", "Tamamlandı"], key="sefer_durum_f")
        with f3:
            ay_f = st.text_input("📅 Ay Filtresi (YYYY-AA)", placeholder="Örn: 2026-11", key="sefer_ay_f").strip()
        with f4:
            gorunum = st.radio("👁️ Görünüm", ["Kartlar", "Tablo"], horizontal=True, key="sefer_gorunum_r")

        filtrelenmis_seferler = []
        for s in seferler:
            if durum_f != "Tümü" and str(s.get("durum") or "Devam Ediyor") != durum_f:
                continue
            if ay_f and not str(s.get("tarih") or "").startswith(ay_f):
                continue
            if arama_q:
                birlesik = " ".join(
                    str(s.get(k, ""))
                    for k in ("id", "arac_plaka", "sofor_adi", "dagitim_personeli", "guzergah_mahalle", "notlar")
                ).lower()
                if arama_q not in birlesik:
                    continue
            filtrelenmis_seferler.append(s)

        if not filtrelenmis_seferler:
            st.info("📭 Seçilen kriterlere uygun sefer kaydı bulunmuyor.")
        else:
            st.caption(f"Gösterilen sefer sayısı: **{len(filtrelenmis_seferler)}** / {len(seferler)}")
            if gorunum == "Kartlar":
                for s in filtrelenmis_seferler:
                    st.markdown(_sefer_karti_html(s), unsafe_allow_html=True)
            else:
                tablo_satirlari = [
                    {
                        "ID": s.get("id", "-"),
                        "Tarih": s.get("tarih", "-"),
                        "Plaka": s.get("arac_plaka", "-"),
                        "Şoför": s.get("sofor_adi") or "-",
                        "Güzergâh": s.get("guzergah_mahalle") or "-",
                        "Çıkış/Dönüş": f"{s.get('cikis_saati') or '-'} → {s.get('donus_saati') or 'Yolda'}",
                        "Porsiyon": f"{int(s.get('teslim_edilen_porsiyon') or 0)} / {int(s.get('sefertas_porsiyon_sayisi') or 0)}",
                        "Yapılan Km": f"{round(max(0.0, float(s.get('bitis_km') or 0.0) - float(s.get('baslangic_km') or 0.0)), 1) if float(s.get('bitis_km') or 0.0) > 0 else 0.0} km",
                        "Sigorta": s.get("sigorta_bitis_tarihi") or "-",
                        "Muayene": s.get("muayene_bitis_tarihi") or "-",
                        "Durum": s.get("durum") or "Devam Ediyor",
                    }
                    for s in filtrelenmis_seferler
                ]
                ozel_html_tablo_goster(tablo_satirlari)

        if yonetici_modu and seferler:
            st.markdown("---")
            with st.expander("🗑️ Sefer Kaydı Sil (Yönetici)", expanded=False):
                sil_secenek = [
                    f"{s.get('id')} - {s.get('tarih')} | {s.get('arac_plaka')} ({s.get('guzergah_mahalle')})"
                    for s in seferler
                ]
                secilen_sil_sefer = st.selectbox("Silinecek Sefer Kaydı", sil_secenek, key="sefer_sil_sec")
                onay_sefer_sil = silme_onay_kutusu("onay_arac_sefer_sil")
                if st.button("Seçili Seferi Sil", type="primary", key="btn_arac_sefer_sil"):
                    if not onay_sefer_sil:
                        st.error("⚠️ Silmek için önce onay kutusunu işaretleyin.")
                    else:
                        sil_id = secilen_sil_sefer.split(" - ")[0].strip()
                        otomatik_yedek_al(f"Araç seferi silindi: {sil_id}")
                        st.session_state.arac_seferleri = [
                            s for s in st.session_state.arac_seferleri if s.get("id") != sil_id
                        ]
                        arac_seferlerini_kaydet(st.session_state.arac_seferleri)
                        st.warning(f"🗑️ **{sil_id}** kodlu sefer kaydı silindi.")
                        time.sleep(0.8)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 4: ARAÇ VE MAHALLE BAZLI AYLIK ANALİZ
    # ---------------------------------------------------------
    with sekme_analiz:
        mevcut_aylar = sorted(
            {str(s.get("tarih") or "")[:7] for s in seferler if len(str(s.get("tarih") or "")) >= 7},
            reverse=True,
        )
        varsayilan_ay = datetime.date.today().strftime("%Y-%m")
        if varsayilan_ay not in mevcut_aylar:
            mevcut_aylar.insert(0, varsayilan_ay)

        secilen_ay = st.selectbox("📅 Analiz Dönemi (Yıl-Ay)", mevcut_aylar, key="sefer_analiz_ay")
        analiz = aylik_sefer_analizi_hesapla(seferler, secilen_ay)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("🚐 Aylık Toplam Sefer", analiz["toplam_sefer"])
        with m2:
            st.metric("🍲 Dağıtılan Kap / Porsiyon", f"{analiz['toplam_porsiyon']:,}")
        with m3:
            st.metric("🛣️ Aylık Toplam Kilometre", f"{analiz['toplam_km']:,.1f} km")

        st.markdown("#### 🚐 Araç Bazlı Aylık Dağıtım Özeti")
        if analiz["arac_listesi"]:
            ozel_html_tablo_goster(analiz["arac_listesi"])
        else:
            st.info("Bu ay için araç bazlı sefer kaydı bulunmuyor.")

        st.markdown("#### 📍 Mahalle / Güzergâh Bazlı Aylık Dağıtım Özeti")
        if analiz["mahalle_listesi"]:
            ozel_html_tablo_goster(analiz["mahalle_listesi"])
        else:
            st.info("Bu ay için mahalle bazlı sefer kaydı bulunmuyor.")
