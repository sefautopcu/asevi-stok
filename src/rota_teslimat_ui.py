import datetime
import html
import time

SAYFA_ETIKETI_ROTA_TESLIMAT = "Rota & Teslimat Takibi"

TESLIMAT_DURUMLARI = (
    "Bekliyor",
    "Teslim Edildi",
    "Evde Yok",
    "Adres Değişti",
)


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = SAYFA_ETIKETI_ROTA_TESLIMAT.lower()
    for maske in aktif_k_maskeleri:
        m_str = str(maske or "").strip().lower()
        if m_str in ("rota_teslimat", "rota teslimat") or hedef in m_str:
            return True
    return False


def _tam_sayi(deger, varsayilan=0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return int(float(str(deger).replace(",", ".")))
    except (TypeError, ValueError):
        return varsayilan


def mahalle_rota_ozeti_hesapla(teslimat_kayitlari, tarih_filtre=None):
    """Seçili tarih (veya tüm kayıtlar) için mahalle bazlı hane ve porsiyon özeti üretir."""
    filtre_str = str(tarih_filtre or "").strip()[:10]
    kayitlar = [
        k for k in (teslimat_kayitlari or [])
        if isinstance(k, dict) and (not filtre_str or str(k.get("tarih") or "")[:10] == filtre_str)
    ]

    mahalle_map = {}
    toplam_hane = len(kayitlar)
    toplam_planlanan = 0
    toplam_teslim = 0
    teslim_edilen_hane = 0

    for k in kayitlar:
        mahalle = str(k.get("mahalle") or "Belirtilmemiş").strip() or "Belirtilmemiş"
        planlanan = max(0, _tam_sayi(k.get("planlanan_porsiyon"), 0))
        teslim = max(0, _tam_sayi(k.get("teslim_edilen_porsiyon"), 0))
        durum = str(k.get("teslim_durumu") or "Bekliyor").strip()

        toplam_planlanan += planlanan
        toplam_teslim += teslim
        if durum == "Teslim Edildi":
            teslim_edilen_hane += 1

        if mahalle not in mahalle_map:
            mahalle_map[mahalle] = {
                "Mahalle / Güzergâh": mahalle,
                "Hane Sayısı": 0,
                "Planlanan Porsiyon": 0,
                "Teslim Edilen Porsiyon": 0,
                "Teslim Edilen Hane": 0,
                "Bekleyen / Sorunlu": 0,
            }
        m_satir = mahalle_map[mahalle]
        m_satir["Hane Sayısı"] += 1
        m_satir["Planlanan Porsiyon"] += planlanan
        m_satir["Teslim Edilen Porsiyon"] += teslim
        if durum == "Teslim Edildi":
            m_satir["Teslim Edilen Hane"] += 1
        else:
            m_satir["Bekleyen / Sorunlu"] += 1

    mahalle_listesi = sorted(
        mahalle_map.values(),
        key=lambda x: (-x["Planlanan Porsiyon"], x["Mahalle / Güzergâh"]),
    )

    return {
        "toplam_hane": toplam_hane,
        "toplam_planlanan": toplam_planlanan,
        "toplam_teslim": toplam_teslim,
        "teslim_edilen_hane": teslim_edilen_hane,
        "mahalle_listesi": mahalle_listesi,
    }


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


def rota_teslimat_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    rota_teslimat_kaydet,
    yeni_id_uret,
    silme_onay_kutusu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    ihtiyac_sahiplerini_kaydet_fn=None,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Rota & Teslimat Takibi sayfası bu kullanıcı profili için maskelenmiştir.")
        return

    if "rota_teslimat" not in st.session_state or not isinstance(st.session_state.rota_teslimat, list):
        st.session_state.rota_teslimat = []

    teslimat_listesi = st.session_state.rota_teslimat
    haneler = st.session_state.get("ihtiyac_sahipleri", []) or []
    seferler = st.session_state.get("arac_seferleri", []) or []

    bugun_str = datetime.date.today().isoformat()
    ozet = mahalle_rota_ozeti_hesapla(teslimat_listesi, bugun_str)

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(56,189,248,0.16) 0%, rgba(16,185,129,0.14) 100%);
                border: 1px solid rgba(56,189,248,0.28);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.42rem; font-weight: 800; color: #f8fafc;">
                    🗺️ İhtiyaç Sahibi Haneleri: Rota, Teslimat Teyidi ve Hanehalkı Güncelleme
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Mahalle ve sefer bazlı dağıtım rotaları, kapı teslimat teyidi ve hane nüfusu/porsiyon senkronizasyonu
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("🏠", "Bugünkü Rota Haneleri", ozet["toplam_hane"], f"Tarih: {bugun_str}", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("🍲", "Planlanan Porsiyon", f"{ozet['toplam_planlanan']:,}", "Bugünkü dağıtım çıkışı", "#10b981"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("✅", "Teslim Edilen Porsiyon", f"{ozet['toplam_teslim']:,}", f"{ozet['teslim_edilen_hane']} hane onaylandı", "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("📍", "Aktif Mahalle Rotası", len(ozet["mahalle_listesi"]), "Bugün sefer çıkan mahalle", "#a855f7"),
            unsafe_allow_html=True,
        )

    if teslimat_listesi:
        export_satirlari = [
            {
                "ID": k.get("id", "-"),
                "Tarih": k.get("tarih", "-"),
                "Mahalle": k.get("mahalle", "-"),
                "Sefer ID": k.get("sefer_id") or "-",
                "Araç Plaka": k.get("arac_plaka") or "-",
                "Hane Adı": k.get("hane_adi", "-"),
                "Hane Nüfusu": _tam_sayi(k.get("hane_nufusu"), 1),
                "Planlanan Porsiyon": _tam_sayi(k.get("planlanan_porsiyon"), 0),
                "Teslim Porsiyon": _tam_sayi(k.get("teslim_edilen_porsiyon"), 0),
                "Teslim Durumu": k.get("teslim_durumu", "Bekliyor"),
                "Adres": k.get("adres") or "-",
                "Notlar": k.get("notlar") or "-",
            }
            for k in teslimat_listesi
        ]
        excel_bytes = tablo_to_excel_bytes(export_satirlari, "Aziziye Aşevi - Rota ve Teslimat Takibi")
        pdf_bytes = tablo_to_html_pdf_bytes("Aziziye Aşevi - Rota ve Teslimat Takibi", export_satirlari)
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "rota_teslimat_takibi", "rota_teslimat_sayfasi")

    st.markdown("---")

    sekme_rota, sekme_teyid, sekme_hane, sekme_ozet = st.tabs(
        [
            "🗺️ Rota Planla & Fiş Oluştur",
            "✅ Teslimat Teyidi & Durum",
            "👨‍👩‍👧‍👦 Hanehalkı & Porsiyon Güncelle",
            "📊 Mahalle Bazlı Dağıtım Özeti",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: ROTA PLANLA & FİŞ OLUŞTUR
    # ---------------------------------------------------------
    with sekme_rota:
        if not salt_okunur_modu:
            hane_secenekleri = ["Manuel Hane Girişi"]
            hane_haritasi = {}
            for h in haneler:
                if not isinstance(h, dict):
                    continue
                hid = str(h.get("id") or "").strip()
                had = str(h.get("ad_soyad") or h.get("hane_adi") or h.get("ad") or "").strip()
                mah = str(h.get("mahalle") or "").strip()
                if had:
                    etiket = f"{had} ({mah})" if mah else had
                    if hid:
                        etiket = f"{etiket} [{hid}]"
                    hane_secenekleri.append(etiket)
                    hane_haritasi[etiket] = h

            sefer_secenekleri = ["Sefer Seçilmedi"]
            sefer_haritasi = {}
            for s in seferler:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("id") or "").strip()
                plaka = str(s.get("arac_plaka") or "").strip()
                guz = str(s.get("guzergah_mahalle") or "").strip()
                etiket = f"{sid} | {plaka} -> {guz}".strip()
                sefer_secenekleri.append(etiket)
                sefer_haritasi[etiket] = s

            secili_hane_etiket = st.selectbox(
                "🏠 Kayıtlı İhtiyaç Sahibi Hanesinden Seç (İsteğe bağlı)",
                hane_secenekleri,
                key="rt_hane_sec",
            )
            secili_hane = hane_haritasi.get(secili_hane_etiket)

            secili_sefer_etiket = st.selectbox(
                "🚐 İlişkili Araç Seferi (İsteğe bağlı)",
                sefer_secenekleri,
                key="rt_sefer_sec",
            )
            secili_sefer = sefer_haritasi.get(secili_sefer_etiket)

            hane_dict = secili_hane if isinstance(secili_hane, dict) else {}
            sefer_dict = secili_sefer if isinstance(secili_sefer, dict) else {}

            varsayilan_hane_adi = str(
                hane_dict.get("ad_soyad") or hane_dict.get("hane_adi") or hane_dict.get("ad") or ""
            ).strip()
            varsayilan_mahalle = (
                str(hane_dict.get("mahalle") or "").strip()
                or str(sefer_dict.get("guzergah_mahalle") or "").strip()
            )            
            varsayilan_adres = str(secili_hane.get("adres") or "").strip() if secili_hane else ""
            varsayilan_nufus = (
                max(1, _tam_sayi(secili_hane.get("kisi_sayisi") or secili_hane.get("hane_nufusu"), 3))
                if secili_hane
                else 3
            )
            varsayilan_porsiyon = (
                max(1, _tam_sayi(secili_hane.get("porsiyon_sayisi") or secili_hane.get("planlanan_porsiyon"), varsayilan_nufus))
                if secili_hane
                else varsayilan_nufus
            )

            with st.form("yeni_rota_teslimat_formu", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    r_tarih = st.date_input("📅 Dağıtım Tarihi", value=datetime.date.today())
                    r_mahalle = st.text_input("📍 Mahalle / Güzergâh *", value=varsayilan_mahalle, placeholder="Örn: Dadaşkent").strip()
                    r_hane_adi = st.text_input("🏠 Hane Sahibi / Aile Adı *", value=varsayilan_hane_adi, placeholder="Örn: Ayşe Yılmaz").strip()
                with c2:
                    r_nufus = st.number_input("👨‍👩‍👧‍👦 Hanehalkı Kişi Sayısı", min_value=1, value=varsayilan_nufus, step=1)
                    r_planlanan = st.number_input("🍲 Planlanan Porsiyon", min_value=1, value=varsayilan_porsiyon, step=1)
                    r_adres = st.text_input("🗺️ Açık Adres / Sokak", value=varsayilan_adres, placeholder="Sokak, bina, daire no").strip()
                with c3:
                    r_notlar = st.text_area("📝 Dağıtım / Rota Notu", placeholder="Yaşlı hane, zemin kat, sefertas sayısı vb.", height=118).strip()

                kaydet_btn = st.form_submit_button("💾 Rota Kaydı Ekle", type="primary", use_container_width=True)
                if kaydet_btn:
                    if not r_mahalle or not r_hane_adi:
                        st.error("⚠️ Lütfen mahalle/güzergâh ve hane adı bilgilerini girin.")
                    else:
                        yeni_id = yeni_id_uret("RTS-", st.session_state.rota_teslimat)
                        yeni_kayit = {
                            "id": yeni_id,
                            "tarih": str(r_tarih),
                            "mahalle": r_mahalle,
                            "sefer_id": str(secili_sefer.get("id") or "") if secili_sefer else "",
                            "arac_plaka": str(secili_sefer.get("arac_plaka") or "").strip().upper() if secili_sefer else "",
                            "hane_id": str(secili_hane.get("id") or "") if secili_hane else "",
                            "hane_adi": r_hane_adi,
                            "adres": r_adres,
                            "hane_nufusu": int(r_nufus),
                            "planlanan_porsiyon": int(r_planlanan),
                            "teslim_edilen_porsiyon": 0,
                            "teslim_durumu": "Bekliyor",
                            "notlar": r_notlar,
                        }
                        otomatik_yedek_al(f"Rota kaydı eklendi: {r_hane_adi} ({r_mahalle})")
                        st.session_state.rota_teslimat.append(yeni_kayit)
                        rota_teslimat_kaydet(st.session_state.rota_teslimat)
                        st.success(f"🎉 **{r_hane_adi}** için rota kaydı oluşturuldu (`{yeni_id}`).")
                        time.sleep(0.7)
                        st.rerun()

        st.markdown("#### 📋 Kayıtlı Rota ve Teslimat Listesi")
        if teslimat_listesi:
            filtre_mahalleler = ["Tümü"] + sorted({str(k.get("mahalle") or "") for k in teslimat_listesi if k.get("mahalle")})
            sec_mah_filtre = st.selectbox("📍 Mahalle Filtresi", filtre_mahalleler, key="rt_liste_mah_filtre")
            gosterilecek = [
                k for k in teslimat_listesi
                if sec_mah_filtre == "Tümü" or str(k.get("mahalle") or "") == sec_mah_filtre
            ]
            tablo = [
                {
                    "ID": k.get("id", "-"),
                    "Tarih": k.get("tarih", "-"),
                    "Mahalle": k.get("mahalle", "-"),
                    "Hane": k.get("hane_adi", "-"),
                    "Nüfus": _tam_sayi(k.get("hane_nufusu"), 1),
                    "Planlanan": _tam_sayi(k.get("planlanan_porsiyon"), 0),
                    "Teslim": _tam_sayi(k.get("teslim_edilen_porsiyon"), 0),
                    "Durum": k.get("teslim_durumu", "Bekliyor"),
                    "Sefer": k.get("sefer_id") or "-",
                    "Not": k.get("notlar") or "-",
                }
                for k in gosterilecek
            ]
            ozel_html_tablo_goster(tablo)
        else:
            st.info("📭 Henüz rota/teslimat kaydı bulunmuyor.")

    # ---------------------------------------------------------
    # SEKME 2: TESLİMAT TEYİDİ & DURUM GÜNCELLEME
    # ---------------------------------------------------------
    with sekme_teyid:
        st.markdown("#### ✅ Kapı Teslimat Teyidi ve Durum İşleme")
        if not teslimat_listesi:
            st.info("📭 Teyit edilecek rota kaydı bulunmuyor.")
        elif salt_okunur_modu:
            st.warning("🔒 Salt okunur modda teslimat teyidi yapılamaz.")
        else:
            kayit_map = {
                f"{k.get('id')} | {k.get('tarih')} | {k.get('mahalle')} - {k.get('hane_adi')} [{k.get('teslim_durumu')}]": k
                for k in teslimat_listesi
            }
            secili_teyid_etiket = st.selectbox("📌 Teslimat Kaydı Seçin", list(kayit_map.keys()), key="rt_teyid_sec")
            hedef_k = kayit_map[secili_teyid_etiket]

            mevcut_durum = hedef_k.get("teslim_durumu") if hedef_k.get("teslim_durumu") in TESLIMAT_DURUMLARI else "Bekliyor"
            yeni_durum = st.selectbox("🚦 Teslimat Durumu", TESLIMAT_DURUMLARI, index=TESLIMAT_DURUMLARI.index(mevcut_durum), key="rt_teyid_durum")
            varsayilan_teslim_pors = (
                _tam_sayi(hedef_k.get("planlanan_porsiyon"), 0)
                if yeni_durum == "Teslim Edildi" and _tam_sayi(hedef_k.get("teslim_edilen_porsiyon"), 0) == 0
                else _tam_sayi(hedef_k.get("teslim_edilen_porsiyon"), 0)
            )
            yeni_teslim_pors = st.number_input(
                "🍲 Teslim Edilen Porsiyon Sayısı",
                min_value=0,
                value=varsayilan_teslim_pors,
                step=1,
                key="rt_teyid_pors",
            )
            yeni_not = st.text_input("📝 Teslimat Notu", value=str(hedef_k.get("notlar") or ""), key="rt_teyid_not").strip()

            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                if st.button("✅ Teslimat Teyidini Kaydet", type="primary", use_container_width=True, key="rt_teyid_kaydet_btn"):
                    otomatik_yedek_al(f"Teslimat teyidi güncellendi: {hedef_k.get('id')} -> {yeni_durum}")
                    hedef_k["teslim_durumu"] = yeni_durum
                    hedef_k["teslim_edilen_porsiyon"] = 0 if yeni_durum == "Evde Yok" else int(yeni_teslim_pors)
                    hedef_k["notlar"] = yeni_not
                    rota_teslimat_kaydet(st.session_state.rota_teslimat)
                    st.success("✅ Teslimat teyidi kaydedildi!")
                    time.sleep(0.6)
                    st.rerun()

            if yonetici_modu:
                with col_b2:
                    onay_s = silme_onay_kutusu("onay_rt_sil")
                    if st.button("🗑️ Kaydı Sil", use_container_width=True, key="rt_sil_btn"):
                        if not onay_s:
                            st.error("⚠️ Önce silme onay kutusunu işaretleyin.")
                        else:
                            sil_id = hedef_k.get("id")
                            otomatik_yedek_al(f"Rota kaydı silindi: {sil_id}")
                            st.session_state.rota_teslimat = [
                                k for k in st.session_state.rota_teslimat if k.get("id") != sil_id
                            ]
                            rota_teslimat_kaydet(st.session_state.rota_teslimat)
                            st.warning(f"🗑️ **{sil_id}** silindi.")
                            time.sleep(0.6)
                            st.rerun()

    # ---------------------------------------------------------
    # SEKME 3: HANEHALKI & PORSİYON GÜNCELLEME
    # ---------------------------------------------------------
    with sekme_hane:
        st.markdown("#### 👨‍👩‍👧‍👦 Hanehalkı Nüfusu ve Porsiyon Sayısı Güncelleme")
        st.caption(
            "Hane nüfusu veya porsiyon ihtiyacı değiştiğinde rota kaydını günceller; "
            "eşleşen kayıtlı ihtiyaç sahibi hanesi varsa (`hane_id` veya hane adı) ana hane kaydına da yansıtır."
        )
        if not teslimat_listesi:
            st.info("📭 Güncellenecek hane/rota kaydı bulunmuyor.")
        elif salt_okunur_modu:
            st.warning("🔒 Salt okunur modda hanehalkı güncellemesi yapılamaz.")
        else:
            hane_kayit_map = {
                f"{k.get('id')} | {k.get('hane_adi')} ({k.get('mahalle')}) — Nüfus: {_tam_sayi(k.get('hane_nufusu'), 1)}, Porsiyon: {_tam_sayi(k.get('planlanan_porsiyon'), 0)}": k
                for k in teslimat_listesi
            }
            sec_h_etiket = st.selectbox("🏠 Güncellenecek Hane Kaydını Seçin", list(hane_kayit_map.keys()), key="rt_hane_gunc_sec")
            hedef_h = hane_kayit_map[sec_h_etiket]

            hc1, hc2, hc3 = st.columns(3)
            with hc1:
                g_nufus = st.number_input(
                    "👨‍👩‍👧‍👦 Yeni Hane Nüfusu",
                    min_value=1,
                    value=max(1, _tam_sayi(hedef_h.get("hane_nufusu"), 1)),
                    step=1,
                    key="rt_g_nufus",
                )
            with hc2:
                g_porsiyon = st.number_input(
                    "🍲 Yeni Planlanan Porsiyon",
                    min_value=1,
                    value=max(1, _tam_sayi(hedef_h.get("planlanan_porsiyon"), 1)),
                    step=1,
                    key="rt_g_porsiyon",
                )
            with hc3:
                g_mahalle = st.text_input(
                    "📍 Güncel Mahalle",
                    value=str(hedef_h.get("mahalle") or ""),
                    key="rt_g_mahalle",
                ).strip()

            g_adres = st.text_input("🗺️ Güncel Adres", value=str(hedef_h.get("adres") or ""), key="rt_g_adres").strip()
            ana_haneyi_de_guncelle = st.checkbox("🔗 Bağlı İhtiyaç Sahibi hane kaydını da güncelle", value=True, key="rt_ana_hane_sync")

            if st.button("💾 Hanehalkı ve Porsiyon Bilgilerini Güncelle", type="primary", key="rt_hane_kaydet_btn"):
                otomatik_yedek_al(f"Hanehalkı güncellendi: {hedef_h.get('hane_adi')}")
                hedef_h["hane_nufusu"] = int(g_nufus)
                hedef_h["planlanan_porsiyon"] = int(g_porsiyon)
                if g_mahalle:
                    hedef_h["mahalle"] = g_mahalle
                hedef_h["adres"] = g_adres
                rota_teslimat_kaydet(st.session_state.rota_teslimat)

                if ana_haneyi_de_guncelle and isinstance(st.session_state.get("ihtiyac_sahipleri"), list):
                    hedef_hid = str(hedef_h.get("hane_id") or "").strip()
                    hedef_had = str(hedef_h.get("hane_adi") or "").strip().lower()
                    guncellenen_hane = False
                    for h_kayit in st.session_state.ihtiyac_sahipleri:
                        if not isinstance(h_kayit, dict):
                            continue
                        kayit_hid = str(h_kayit.get("id") or "").strip()
                        kayit_had = str(h_kayit.get("ad_soyad") or h_kayit.get("hane_adi") or h_kayit.get("ad") or "").strip().lower()
                        if (hedef_hid and kayit_hid == hedef_hid) or (hedef_had and kayit_had == hedef_had):
                            if "kisi_sayisi" in h_kayit:
                                h_kayit["kisi_sayisi"] = int(g_nufus)
                            if "hane_nufusu" in h_kayit:
                                h_kayit["hane_nufusu"] = int(g_nufus)
                            if "porsiyon_sayisi" in h_kayit:
                                h_kayit["porsiyon_sayisi"] = int(g_porsiyon)
                            if g_mahalle and "mahalle" in h_kayit:
                                h_kayit["mahalle"] = g_mahalle
                            if "adres" in h_kayit:
                                h_kayit["adres"] = g_adres
                            guncellenen_hane = True
                    if guncellenen_hane and callable(ihtiyac_sahiplerini_kaydet_fn):
                        ihtiyac_sahiplerini_kaydet_fn(st.session_state.ihtiyac_sahipleri)

                st.success("✅ Hanehalkı ve porsiyon bilgileri güncellendi!")
                time.sleep(0.6)
                st.rerun()

    # ---------------------------------------------------------
    # SEKME 4: MAHALLE BAZLI DAĞITIM ÖZETİ
    # ---------------------------------------------------------
    with sekme_ozet:
        st.markdown("#### 📊 Mahalle / Güzergâh Bazlı Dağıtım Performansı")
        tarihler = sorted({str(k.get("tarih") or "") for k in teslimat_listesi if k.get("tarih")}, reverse=True)
        sec_tarih_ops = ["Tüm Tarihler"] + tarihler
        sec_tarih = st.selectbox("📅 Analiz Tarihi", sec_tarih_ops, key="rt_ozet_tarih")
        ozet_secili = mahalle_rota_ozeti_hesapla(
            teslimat_listesi, None if sec_tarih == "Tüm Tarihler" else sec_tarih
        )
        if ozet_secili["mahalle_listesi"]:
            ozel_html_tablo_goster(ozet_secili["mahalle_listesi"])
        else:
            st.info("📭 Seçili kriterlere uygun mahalle dağıtım verisi bulunmuyor.")
