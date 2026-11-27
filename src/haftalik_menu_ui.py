import datetime
import html
import time

SAYFA_ETIKETI_HAFTALIK_MENU = "Haftalık Menü Planlama"

GUN_ADLARI = (
    "Pazartesi",
    "Salı",
    "Çarşamba",
    "Perşembe",
    "Cuma",
    "Cumartesi",
    "Pazar",
)

OGUN_TURLERI = (
    "Ana Öğün",
    "Çorba",
    "Ana Yemek",
    "Yardımcı / Tatlı",
    "Kumanya / Kahvaltı",
)


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = SAYFA_ETIKETI_HAFTALIK_MENU.lower()
    for maske in aktif_k_maskeleri:
        m_str = str(maske or "").strip().lower()
        if m_str in ("haftalik_menu", "haftalık menü") or hedef in m_str:
            return True
    return False


def _sayi_yap(deger, varsayilan=0.0):
    if deger is None or deger == "":
        return varsayilan
    try:
        return float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        return varsayilan


def hafta_baslangici_str(tarih_degeri):
    """Verilen tarih için haftanın Pazartesi gününü YYYY-MM-DD biçiminde döndürür."""
    if isinstance(tarih_degeri, datetime.datetime):
        d = tarih_degeri.date()
    elif isinstance(tarih_degeri, datetime.date):
        d = tarih_degeri
    else:
        try:
            d = datetime.date.fromisoformat(str(tarih_degeri or "").strip()[:10])
        except ValueError:
            d = datetime.date.today()
    return (d - datetime.timedelta(days=d.weekday())).isoformat()


def recete_malzeme_ihtiyaci_hesapla(menu_kayitlari, receteler, girisler, kritik_seviyeler=None):
    """
    Haftalık menüdeki porsiyon sayıları ve reçete kalemlerine göre malzeme ihtiyacını
    hesaplar; mevcut depo stoğu ve kritik seviyelerle karşılaştırıp eksik listesini üretir.
    """
    kritik_map = kritik_seviyeler if isinstance(kritik_seviyeler, dict) else {}

    # Reçeteleri ID ve yemek adına göre indeksle
    recete_by_id = {}
    recete_by_ad = {}
    for r in (receteler or []):
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "").strip()
        rad = str(r.get("yemek_adi") or r.get("ad") or r.get("baslik") or "").strip().lower()
        if rid:
            recete_by_id[rid] = r
        if rad:
            recete_by_ad[rad] = r

    # Mevcut depo stoklarını ürün adına göre topla
    stok_toplam = {}
    stok_birim = {}
    for g in (girisler or []):
        if not isinstance(g, dict):
            continue
        urun = str(g.get("urun") or g.get("urun_adi") or "").strip()
        if not urun:
            continue
        anahtar = urun.lower()
        kalan = max(0.0, _sayi_yap(g.get("kalan", g.get("miktar", 0.0)), 0.0))
        stok_toplam[anahtar] = round(stok_toplam.get(anahtar, 0.0) + kalan, 3)
        if anahtar not in stok_birim and g.get("birim"):
            stok_birim[anahtar] = str(g.get("birim")).strip()

    # Menü kayıtlarından toplam malzeme ihtiyacını çıkar
    ihtiyac_toplam = {}
    ihtiyac_birim = {}
    ihtiyac_etiket = {}
    eslesen_menu_sayisi = 0

    for m in (menu_kayitlari or []):
        if not isinstance(m, dict):
            continue
        porsiyon = max(0.0, _sayi_yap(m.get("tahmini_porsiyon"), 0.0))
        if porsiyon <= 0:
            continue

        rid = str(m.get("recete_id") or "").strip()
        yemek_adi = str(m.get("yemek_adi") or "").strip().lower()
        recete = recete_by_id.get(rid) or recete_by_ad.get(yemek_adi)
        if not recete:
            continue

        eslesen_menu_sayisi += 1
        recete_porsiyon = max(1.0, _sayi_yap(recete.get("porsiyon_sayisi") or recete.get("porsiyon"), 1.0))
        carpan = porsiyon / recete_porsiyon

        kalemler = (
            recete.get("malzemeler")
            or recete.get("kalemler")
            or recete.get("icerik")
            or []
        )
        if not isinstance(kalemler, list):
            continue

        for kalem in kalemler:
            if not isinstance(kalem, dict):
                continue
            malzeme_ad = str(
                kalem.get("urun")
                or kalem.get("malzeme")
                or kalem.get("ad")
                or ""
            ).strip()
            if not malzeme_ad:
                continue
            miktar_birim = _sayi_yap(kalem.get("miktar"), 0.0)
            if miktar_birim <= 0:
                continue

            toplam_gerekli = round(miktar_birim * carpan, 3)
            anahtar = malzeme_ad.lower()
            ihtiyac_toplam[anahtar] = round(ihtiyac_toplam.get(anahtar, 0.0) + toplam_gerekli, 3)
            ihtiyac_etiket[anahtar] = malzeme_ad
            birim_str = str(kalem.get("birim") or stok_birim.get(anahtar) or "adet").strip()
            ihtiyac_birim[anahtar] = birim_str

    ihtiyac_satirlari = []
    eksik_satirlari = []

    for anahtar, gerekli in sorted(ihtiyac_toplam.items(), key=lambda x: x[1], reverse=True):
        ad = ihtiyac_etiket.get(anahtar, anahtar)
        birim = ihtiyac_birim.get(anahtar, "adet")
        mevcut_stok = round(stok_toplam.get(anahtar, 0.0), 3)
        kritik_esik = max(0.0, _sayi_yap(kritik_map.get(ad) or kritik_map.get(anahtar), 0.0))
        hedef_stok = gerekli + kritik_esik
        eksik_miktar = round(max(0.0, hedef_stok - mevcut_stok), 3)

        durum = "✅ Yeterli"
        if eksik_miktar > 0:
            durum = "🚨 Eksik / Satın Alınmalı"
        elif mevcut_stok < gerekli * 1.15:
            durum = "⚠️ Sınırda"

        satir = {
            "Malzeme": ad,
            "Birim": birim,
            "Haftalık İhtiyaç": gerekli,
            "Mevcut Depo Stoğu": mevcut_stok,
            "Kritik Eşik": kritik_esik,
            "Eksik / Alınacak": eksik_miktar,
            "Durum": durum,
        }
        ihtiyac_satirlari.append(satir)
        if eksik_miktar > 0:
            eksik_satirlari.append(satir)

    return {
        "eslesen_menu_sayisi": eslesen_menu_sayisi,
        "ihtiyac_satirlari": ihtiyac_satirlari,
        "eksik_satirlari": eksik_satirlari,
        "eksik_cesit_sayisi": len(eksik_satirlari),
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


def haftalik_menu_planlama_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    haftalik_menu_kaydet,
    yeni_id_uret,
    silme_onay_kutusu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    yemek_receteleri_yukle_fn=None,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Haftalık Menü Planlama sayfası bu kullanıcı profili için maskelenmiştir.")
        return

    if "haftalik_menu" not in st.session_state or not isinstance(st.session_state.haftalik_menu, list):
        st.session_state.haftalik_menu = []

    if "yemek_receteleri" not in st.session_state and callable(yemek_receteleri_yukle_fn):
        try:
            st.session_state.yemek_receteleri = yemek_receteleri_yukle_fn()
        except Exception:
            st.session_state.yemek_receteleri = []

    menu_listesi = st.session_state.haftalik_menu
    receteler = st.session_state.get("yemek_receteleri", []) or []
    girisler = st.session_state.get("girisler", []) or []
    kritik_seviyeler = st.session_state.get("kritik_seviyeler", {}) or {}

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(16,185,129,0.16) 0%, rgba(245,158,11,0.12) 100%);
                border: 1px solid rgba(16,185,129,0.28);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.42rem; font-weight: 800; color: #f8fafc;">
                    📅 Haftalık Menü Planlama ve Malzeme İhtiyaç Listesi
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Haftalık öğün takvimi, reçete porsiyon ölçekleme ve depo stoğu ile otomatik satın alma ihtiyacı hesabı
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    aktif_hafta = hafta_baslangici_str(datetime.date.today())
    haftalik_kayitlar = [
        m for m in menu_listesi if str(m.get("hafta_baslangic") or hafta_baslangici_str(m.get("tarih"))) == aktif_hafta
    ]
    haftalik_porsiyon = sum(int(_sayi_yap(m.get("tahmini_porsiyon"), 0)) for m in haftalik_kayitlar)

    analiz = recete_malzeme_ihtiyaci_hesapla(
        haftalik_kayitlar, receteler, girisler, kritik_seviyeler
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("📅", "Bu Hafta Planlanan Öğün", len(haftalik_kayitlar), f"Hafta başı: {aktif_hafta}", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("🍲", "Haftalık Tahmini Porsiyon", f"{haftalik_porsiyon:,}", "Planlanan toplam yemek porsiyonu", "#10b981"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("🧾", "Hesaplanan Malzeme", len(analiz["ihtiyac_satirlari"]), f"{analiz['eslesen_menu_sayisi']} reçete eşleşti", "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("🛒", "Eksik / Satın Alınacak", analiz["eksik_cesit_sayisi"], "Depo/kritik stok altında kalem", "#f43f5e"),
            unsafe_allow_html=True,
        )

    if menu_listesi:
        export_satirlari = [
            {
                "ID": m.get("id", "-"),
                "Hafta Başlangıcı": m.get("hafta_baslangic") or hafta_baslangici_str(m.get("tarih")),
                "Gün": m.get("gun_adi") or "-",
                "Tarih": m.get("tarih") or "-",
                "Öğün Türü": m.get("ogun_turu") or "Ana Öğün",
                "Yemek / Menü Adı": m.get("yemek_adi") or "-",
                "Tahmini Porsiyon": int(_sayi_yap(m.get("tahmini_porsiyon"), 0)),
                "Durum": m.get("durum") or "Planlandı",
                "Notlar": m.get("notlar") or "-",
            }
            for m in menu_listesi
        ]
        excel_bytes = tablo_to_excel_bytes(export_satirlari, "Aziziye Aşevi - Haftalık Menü Planı")
        pdf_bytes = tablo_to_html_pdf_bytes("Aziziye Aşevi - Haftalık Menü Planı", export_satirlari)
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "haftalik_menu_plani", "haftalik_menu_sayfasi")

    st.markdown("---")

    sekme_plan, sekme_ihtiyac, sekme_yonet = st.tabs(
        [
            "➕ Öğün Planla & Haftalık Takvim",
            "🛒 Otomatik Malzeme & Satın Alma Listesi",
            "🗑️ Kayıt Silme & Durum Güncelleme",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: ÖĞÜN PLANLAMA & HAFTALIK TAKVİM
    # ---------------------------------------------------------
    with sekme_plan:
        if not salt_okunur_modu:
            recete_secenekleri = ["Manuel Menü Girişi"]
            recete_haritasi = {}
            for r in receteler:
                if not isinstance(r, dict):
                    continue
                rad = str(r.get("yemek_adi") or r.get("ad") or r.get("baslik") or "").strip()
                rid = str(r.get("id") or "").strip()
                if rad:
                    etiket = f"{rad} ({rid})" if rid else rad
                    recete_secenekleri.append(etiket)
                    recete_haritasi[etiket] = r

            secili_recete_etiket = st.selectbox(
                "🍲 Hazır Yemek Reçetesinden Seç (İsteğe bağlı)",
                recete_secenekleri,
                key="hmenu_recete_sec",
            )
            secili_recete = recete_haritasi.get(secili_recete_etiket)
            varsayilan_yemek_adi = (
                str(secili_recete.get("yemek_adi") or secili_recete.get("ad") or "").strip()
                if secili_recete
                else ""
            )
            varsayilan_porsiyon = (
                max(1, int(_sayi_yap(secili_recete.get("porsiyon_sayisi") or secili_recete.get("porsiyon"), 250)))
                if secili_recete
                else 250
            )

            with st.form("yeni_haftalik_menu_formu", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    m_tarih = st.date_input("📅 Öğün Tarihi", value=datetime.date.today())
                    m_gun = st.selectbox(
                        "🗓️ Gün",
                        GUN_ADLARI,
                        index=datetime.date.today().weekday(),
                    )
                    m_ogun = st.selectbox("🍽️ Öğün Türü", OGUN_TURLERI)
                with c2:
                    m_yemek_adi = st.text_input(
                        "🍲 Yemek / Menü Adı *",
                        value=varsayilan_yemek_adi,
                        placeholder="Örn: Mercimek Çorbası, Etli Nohut, Pilav",
                    ).strip()
                    m_porsiyon = st.number_input(
                        "👥 Tahmini Porsiyon Sayısı *",
                        min_value=1,
                        value=varsayilan_porsiyon,
                        step=10,
                    )
                    m_durum = st.selectbox("🚦 Durum", ["Planlandı", "Onaylandı", "Üretildi"])
                with c3:
                    m_notlar = st.text_area("📝 Planlama Notu", placeholder="Özel gün, kumanya detayı vb.", height=118).strip()

                ekle_btn = st.form_submit_button("💾 Haftalık Menüye Ekle", type="primary", use_container_width=True)
                if ekle_btn:
                    if not m_yemek_adi:
                        st.error("⚠️ Lütfen yemek / menü adını girin.")
                    else:
                        yeni_id = yeni_id_uret("HMN-", st.session_state.haftalik_menu)
                        yeni_satir = {
                            "id": yeni_id,
                            "hafta_baslangic": hafta_baslangici_str(m_tarih),
                            "gun_adi": m_gun,
                            "tarih": str(m_tarih),
                            "ogun_turu": m_ogun,
                            "recete_id": str(secili_recete.get("id") or "") if secili_recete else "",
                            "yemek_adi": m_yemek_adi,
                            "tahmini_porsiyon": int(m_porsiyon),
                            "durum": m_durum,
                            "notlar": m_notlar,
                        }
                        otomatik_yedek_al(f"Haftalık menü eklendi: {m_yemek_adi} ({m_tarih})")
                        st.session_state.haftalik_menu.append(yeni_satir)
                        haftalik_menu_kaydet(st.session_state.haftalik_menu)
                        st.success(f"🎉 **{m_yemek_adi}** ({str(m_tarih)}) haftalık menüye eklendi!")
                        time.sleep(0.7)
                        st.rerun()

        st.markdown("#### 🗓️ Kayıtlı Haftalık Menü Takvimi")
        haftalar = sorted(
            {str(m.get("hafta_baslangic") or hafta_baslangici_str(m.get("tarih"))) for m in menu_listesi if m.get("tarih") or m.get("hafta_baslangic")},
            reverse=True,
        )
        if aktif_hafta not in haftalar:
            haftalar.insert(0, aktif_hafta)
        secili_hafta = st.selectbox("📆 Görüntülenecek Hafta (Pazartesi)", haftalar, key="hmenu_filtre_hafta")

        gosterilecek = [
            m for m in menu_listesi
            if str(m.get("hafta_baslangic") or hafta_baslangici_str(m.get("tarih"))) == secili_hafta
        ]
        if gosterilecek:
            tablo = [
                {
                    "ID": m.get("id", "-"),
                    "Gün": m.get("gun_adi") or "-",
                    "Tarih": m.get("tarih") or "-",
                    "Öğün": m.get("ogun_turu") or "Ana Öğün",
                    "Yemek / Menü": m.get("yemek_adi") or "-",
                    "Tahmini Porsiyon": int(_sayi_yap(m.get("tahmini_porsiyon"), 0)),
                    "Reçete ID": m.get("recete_id") or "-",
                    "Durum": m.get("durum") or "Planlandı",
                    "Notlar": m.get("notlar") or "-",
                }
                for m in gosterilecek
            ]
            ozel_html_tablo_goster(tablo)
        else:
            st.info("📭 Seçili hafta için planlanmış menü kaydı bulunmuyor.")

    # ---------------------------------------------------------
    # SEKME 2: OTOMATİK MALZEME & SATIN ALMA LİSTESİ
    # ---------------------------------------------------------
    with sekme_ihtiyac:
        st.markdown("#### 🛒 Seçili Hafta İçin Otomatik Malzeme İhtiyaç ve Eksik Stok Analizi")
        st.caption(
            "Kayıtlı **Hazır Yemek Reçeteleri** malzeme gramajları, planlanan porsiyon sayılarıyla çarpılır; "
            "mevcut depo stoğu ve kritik eşiklerle kıyaslanır."
        )
        if not receteler:
            st.info("ℹ️ Reçete malzeme çarpanlarının hesaplanabilmesi için 'Hazır Yemek Reçeteleri' modülünde reçete tanımlı olmalıdır.")

        if analiz["ihtiyac_satirlari"]:
            st.markdown("**📋 Tüm Malzeme İhtiyaç Tablosu**")
            ozel_html_tablo_goster(analiz["ihtiyac_satirlari"])

            st.markdown("**🚨 Satın Alınması Gereken Eksik Malzemeler**")
            if analiz["eksik_satirlari"]:
                ozel_html_tablo_goster(analiz["eksik_satirlari"])
                eksik_excel = tablo_to_excel_bytes(
                    analiz["eksik_satirlari"],
                    f"Aziziye Aşevi - Eksik Malzeme Satın Alma Listesi ({secili_hafta})",
                )
                eksik_pdf = tablo_to_html_pdf_bytes(
                    f"Aziziye Aşevi - Eksik Malzeme Satın Alma Listesi ({secili_hafta})",
                    analiz["eksik_satirlari"],
                )
                ortak_indirme_alani(eksik_excel, eksik_pdf, f"eksik_malzeme_{secili_hafta}", "eksik_malzeme_rapor")
            else:
                st.success("✅ Seçili haftadaki tüm reçete malzemeleri için mevcut depo stoğu ve kritik eşik yeterlidir!")
        else:
            st.info("📭 Hesaplanacak eşleşmiş reçete/malzeme ihtiyacı bulunmuyor.")

    # ---------------------------------------------------------
    # SEKME 3: DURUM GÜNCELLEME & SİLME
    # ---------------------------------------------------------
    with sekme_yonet:
        if not menu_listesi:
            st.info("📭 Yönetilecek menü kaydı bulunmuyor.")
        elif salt_okunur_modu:
            st.warning("🔒 Salt okunur modda güncelleme/silme işlemi yapılamaz.")
        else:
            secenek_map = {
                f"{m.get('id')} | {m.get('tarih')} ({m.get('gun_adi')}) - {m.get('yemek_adi')} [{m.get('durum')}]": m
                for m in menu_listesi
            }
            secili_etiket = st.selectbox("✏️ Kayıt Seçin", list(secenek_map.keys()), key="hmenu_yonet_sec")
            hedef = secenek_map[secili_etiket]

            yeni_durum = st.selectbox(
                "🚦 Yeni Durum",
                ["Planlandı", "Onaylandı", "Üretildi"],
                index=["Planlandı", "Onaylandı", "Üretildi"].index(hedef.get("durum") if hedef.get("durum") in ["Planlandı", "Onaylandı", "Üretildi"] else "Planlandı"),
                key="hmenu_yeni_durum",
            )
            if st.button("💾 Durumu Güncelle", type="primary", key="hmenu_durum_btn"):
                otomatik_yedek_al(f"Haftalık menü durumu güncellendi: {hedef.get('id')}")
                hedef["durum"] = yeni_durum
                haftalik_menu_kaydet(st.session_state.haftalik_menu)
                st.success("✅ Menü durumu güncellendi!")
                time.sleep(0.6)
                st.rerun()

            if yonetici_modu:
                st.markdown("---")
                onay_sil = silme_onay_kutusu("onay_hmenu_sil")
                if st.button("🗑️ Seçili Menü Kaydını Sil", key="hmenu_sil_btn"):
                    if not onay_sil:
                        st.error("⚠️ Silmek için önce onay kutusunu işaretleyin.")
                    else:
                        sil_id = hedef.get("id")
                        otomatik_yedek_al(f"Haftalık menü kaydı silindi: {sil_id}")
                        st.session_state.haftalik_menu = [
                            m for m in st.session_state.haftalik_menu if m.get("id") != sil_id
                        ]
                        haftalik_menu_kaydet(st.session_state.haftalik_menu)
                        st.warning(f"🗑️ **{sil_id}** kaydı silindi.")
                        time.sleep(0.6)
                        st.rerun()
