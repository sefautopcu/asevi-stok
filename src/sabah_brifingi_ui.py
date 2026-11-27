import datetime
import html
import time

SAYFA_ETIKETI_SABAH_BRIFINGI = "Kritik Uyarı Merkezi & Sabah Brifingi"

VARSAYILAN_KATEGORILER = [
    "Kritik Stok",
    "Kritik Seviyeye Yaklaşan",
    "SKT / Tüketim",
    "Menü & Üretim",
    "Rota & Teslimat",
    "Genel",
]


def _bugun_tarih():
    try:
        from zoneinfo import ZoneInfo

        return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).date()
    except Exception:
        return datetime.datetime.now().date()


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = SAYFA_ETIKETI_SABAH_BRIFINGI.lower()
    for maske in aktif_k_maskeleri:
        m_str = str(maske or "").strip().lower()
        if (
            m_str in ("sabah_brifingi", "sabah brifingi", "kritik_uyari", "kritik uyari")
            or hedef in m_str
        ):
            return True
    return False


def _state_al(state, anahtar, varsayilan=None):
    """Hem Python dict hem de Streamlit session_state nesnelerinden güvenli okuma yapar."""
    if state is None:
        return varsayilan
    try:
        if isinstance(state, dict):
            return state.get(anahtar, varsayilan)
        return state[anahtar] if anahtar in state else varsayilan
    except Exception:
        try:
            return getattr(state, anahtar, varsayilan)
        except Exception:
            return varsayilan


def _sayi_guvenli(deger, varsayilan=0.0):
    if deger is None or deger == "":
        return float(varsayilan)
    if isinstance(deger, (int, float)):
        return float(deger)
    metin = str(deger).strip().replace(" ", "")
    if "," in metin and "." not in metin:
        metin = metin.replace(",", ".")
    elif "," in metin and "." in metin:
        metin = metin.replace(".", "").replace(",", ".")
    try:
        return float(metin)
    except (TypeError, ValueError):
        return float(varsayilan)


def _tarih_ayristir(deger):
    if isinstance(deger, datetime.datetime):
        return deger.date()
    if isinstance(deger, datetime.date):
        return deger
    metin = str(deger or "").strip()[:10]
    if not metin:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(metin, fmt).date()
        except ValueError:
            continue
    return None


def _urun_norm(ad):
    return str(ad or "").strip().upper()


def _esik_sozlugune_ekle(esik_haritasi, ad, deger):
    ad_norm = _urun_norm(ad)
    if not ad_norm:
        return
    if isinstance(deger, dict):
        ham = (
            deger.get("kritik_miktar")
            if deger.get("kritik_miktar") is not None
            else (
                deger.get("kritik_seviye")
                if deger.get("kritik_seviye") is not None
                else (
                    deger.get("esik")
                    if deger.get("esik") is not None
                    else (
                        deger.get("miktar")
                        if deger.get("miktar") is not None
                        else deger.get("seviye")
                    )
                )
            )
        )
        sayi = _sayi_guvenli(ham, 10.0)
    else:
        sayi = _sayi_guvenli(deger, 10.0)

    if sayi >= 0:
        if ad_norm in esik_haritasi:
            esik_haritasi[ad_norm] = max(esik_haritasi[ad_norm], sayi)
        else:
            esik_haritasi[ad_norm] = sayi


def _kritik_seviyeleri_topla(state, aktif_urunler):
    """`kritik_seviyeler` ve aktif ürünlerden büyük harf normalize edilmiş eşik haritası üretir."""
    esik_haritasi = {}

    for u_norm in aktif_urunler:
        esik_haritasi[u_norm] = 10.0

    kaynak = _state_al(state, "kritik_seviyeler", {})
    if isinstance(kaynak, dict):
        for k_ad, k_deger in kaynak.items():
            _esik_sozlugune_ekle(esik_haritasi, k_ad, k_deger)
    elif isinstance(kaynak, list):
        for item in kaynak:
            if isinstance(item, dict):
                _esik_sozlugune_ekle(
                    esik_haritasi,
                    item.get("urun_anahtari")
                    or item.get("urun_adi")
                    or item.get("urun")
                    or item.get("ad"),
                    item,
                )

    return esik_haritasi


def otomatik_uyarilari_tara(session_state, referans_tarih=None):
    """Mevcut session_state verilerinden kritik/yaklaşan stok, SKT ve operasyon uyarıları üretir."""
    bugun = _tarih_ayristir(referans_tarih) or _bugun_tarih()
    bugun_str = bugun.strftime("%Y-%m-%d")
    uretilen = []

    girisler = _state_al(session_state, "girisler", None)
    if not isinstance(girisler, list) or not girisler:
        for yedek_anahtar in ("stok_listesi", "guncel_stok", "urunler"):
            yedek_veri = _state_al(session_state, yedek_anahtar, None)
            if isinstance(yedek_veri, list) and yedek_veri:
                girisler = yedek_veri
                break

    if isinstance(girisler, list):
        urun_miktarlari = {}
        urun_birimleri = {}
        urun_sktleri = []

        for idx, g in enumerate(girisler, start=1):
            if not isinstance(g, dict):
                continue
            urun_norm = _urun_norm(
                g.get("urun")
                or g.get("urun_adi")
                or g.get("ad")
                or g.get("malzeme_adi")
            )
            if not urun_norm:
                continue

            ham_miktar = None
            for m_alan in ("kalan", "kalan_miktar", "miktar", "stok_miktari", "adet"):
                if g.get(m_alan) is not None and g.get(m_alan) != "":
                    ham_miktar = g.get(m_alan)
                    break

            kalan = _sayi_guvenli(ham_miktar, 0.0)
            urun_miktarlari[urun_norm] = urun_miktarlari.get(urun_norm, 0.0) + kalan
            if urun_norm not in urun_birimleri:
                urun_birimleri[urun_norm] = str(g.get("birim") or "Kg").strip() or "Kg"

            skt_tarih = _tarih_ayristir(
                g.get("skt")
                or g.get("son_tuketim_tarihi")
                or g.get("son_kullanma_tarihi")
                or g.get("stt")
            )
            if skt_tarih and kalan > 0:
                kalan_gun = (skt_tarih - bugun).days
                if kalan_gun <= 7:
                    kaynak_id = str(g.get("id") or f"SKT-{idx}")
                    onem = "Kritik" if kalan_gun <= 0 else ("Yüksek" if kalan_gun <= 3 else "Orta")
                    durum_notu = (
                        "SKT bugün veya geçmiş!"
                        if kalan_gun <= 0
                        else f"SKT'ye {kalan_gun} gün kaldı ({skt_tarih.strftime('%Y-%m-%d')})"
                    )
                    urun_sktleri.append(
                        {
                            "id": f"AUTO-{kaynak_id}",
                            "tarih": bugun_str,
                            "kategori": "SKT / Tüketim",
                            "onem_seviyesi": onem,
                            "baslik": f"{urun_norm} — {durum_notu}",
                            "detay": f"Parti/Kayıt: {kaynak_id} | Kalan: {kalan:g} {urun_birimleri[urun_norm]}",
                            "kaynak_id": kaynak_id,
                            "durum": "Aktif",
                        }
                    )

        esik_haritasi = _kritik_seviyeleri_topla(session_state, set(urun_miktarlari.keys()))

        for urun_ad, esik in sorted(esik_haritasi.items()):
            if esik <= 0:
                continue
            toplam_kalan = urun_miktarlari.get(urun_ad, 0.0)
            birim = urun_birimleri.get(urun_ad, "Kg")
            yaklasim_siniri = esik * 1.2

            if toplam_kalan <= esik:
                onem = "Kritik" if toplam_kalan <= 0 else "Yüksek"
                kaynak_id = f"STK-KRITIK-{urun_ad}"
                uretilen.append(
                    {
                        "id": f"AUTO-{abs(hash(kaynak_id)) % 100000:05d}",
                        "tarih": bugun_str,
                        "kategori": "Kritik Stok",
                        "onem_seviyesi": onem,
                        "baslik": f"{urun_ad} kritik stok seviyesinde ({toplam_kalan:g} {birim} / Eşik: {esik:g} {birim})",
                        "detay": f"Mevcut toplam stok {toplam_kalan:g} {birim}, kritik eşik {esik:g} {birim}.",
                        "kaynak_id": kaynak_id,
                        "durum": "Aktif",
                    }
                )
            elif toplam_kalan <= yaklasim_siniri:
                kaynak_id = f"STK-YAKLASAN-{urun_ad}"
                uretilen.append(
                    {
                        "id": f"AUTO-{abs(hash(kaynak_id)) % 100000:05d}",
                        "tarih": bugun_str,
                        "kategori": "Kritik Seviyeye Yaklaşan",
                        "onem_seviyesi": "Orta",
                        "baslik": f"{urun_ad} kritik seviyeye yaklaşıyor ({toplam_kalan:g} {birim} / Eşik: {esik:g} {birim})",
                        "detay": f"Mevcut toplam stok {toplam_kalan:g} {birim}, kritik eşik {esik:g} {birim} (yaklaşım sınırı: {yaklasim_siniri:g} {birim}).",
                        "kaynak_id": kaynak_id,
                        "durum": "Aktif",
                    }
                )

        uretilen.extend(urun_sktleri)

    # 2. Günün menü planı kontrolü
    haftalik_menu = _state_al(session_state, "haftalik_menu", [])
    bugun_menu_var = False
    if isinstance(haftalik_menu, list):
        for m in haftalik_menu:
            if isinstance(m, dict):
                m_tarih = _tarih_ayristir(m.get("tarih") or m.get("gun_tarihi"))
                if m_tarih == bugun:
                    bugun_menu_var = True
                    break
    if isinstance(haftalik_menu, list) and len(haftalik_menu) > 0 and not bugun_menu_var:
        kaynak_id = f"MENU-YOK-{bugun_str}"
        uretilen.append(
            {
                "id": f"AUTO-{abs(hash(kaynak_id)) % 100000:05d}",
                "tarih": bugun_str,
                "kategori": "Menü & Üretim",
                "onem_seviyesi": "Orta",
                "baslik": f"{bugun_str} tarihi için haftalık menü kaydı bulunmuyor",
                "detay": "Sabah üretim planlaması için bugünün yemek menüsünü kontrol edin.",
                "kaynak_id": kaynak_id,
                "durum": "Aktif",
            }
        )

    # 3. Teslimat ve sefer durumu kontrolü
    rota_teslimat = _state_al(session_state, "rota_teslimat", [])
    if isinstance(rota_teslimat, list):
        bekleyen_rotalar = [
            r
            for r in rota_teslimat
            if isinstance(r, dict)
            and str(r.get("teslim_durumu") or r.get("durum") or "").strip().lower()
            not in ("teslim edildi", "tamamlandı", "tamamlandi", "iptal")
        ]
        if bekleyen_rotalar:
            kaynak_id = f"ROTA-BEKLEYEN-{bugun_str}"
            uretilen.append(
                {
                    "id": f"AUTO-{abs(hash(kaynak_id)) % 100000:05d}",
                    "tarih": bugun_str,
                    "kategori": "Rota & Teslimat",
                    "onem_seviyesi": "Orta",
                    "baslik": f"{len(bekleyen_rotalar)} adet bekleyen teslimat rotası bulunuyor",
                    "detay": "Dağıtım araçları ve teslimat noktalarının durumunu sabah brifinginde doğrulayın.",
                    "kaynak_id": kaynak_id,
                    "durum": "Aktif",
                }
            )

    return uretilen


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


def sabah_brifingi_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    sabah_brifingi_kaydet,
    yeni_id_uret,
    silme_onay_kutusu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    uyari_olustur_fn=None,
    denetim_kaydi_ekle_fn=None,
    denetim_izi_kaydet_fn=None,
    aktif_kullanici="sistem",
    aktif_rol="",
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Kritik Uyarı Merkezi & Sabah Brifingi sayfası bu kullanıcı profili için maskelenmiştir.")
        return

    if "sabah_brifingi_uyarilari" not in st.session_state or not isinstance(
        st.session_state.sabah_brifingi_uyarilari, list
    ):
        st.session_state.sabah_brifingi_uyarilari = []

    uyarilar = st.session_state.sabah_brifingi_uyarilari
    bugun_str = _bugun_tarih().strftime("%Y-%m-%d")

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(90deg, rgba(245,158,11,0.18) 0%, rgba(16,185,129,0.14) 100%);
                border: 1px solid rgba(245,158,11,0.32);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.42rem; font-weight: 800; color: #f8fafc;">
                    🌅 Kritik Uyarı Merkezi ve Günlük Sabah Brifingi
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Vardiya başlangıç özeti • Brifing Tarihi: {html.escape(bugun_str)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    aktif_uyarilar = [
        u for u in uyarilar if isinstance(u, dict) and str(u.get("durum") or "Aktif") != "Okundu"
    ]
    kritik_sayisi = sum(
        1
        for u in aktif_uyarilar
        if str(u.get("onem_seviyesi") or "").strip().lower() in ("kritik", "yüksek", "yuksek")
    )
    okunmus_sayisi = sum(
        1 for u in uyarilar if isinstance(u, dict) and str(u.get("durum") or "") == "Okundu"
    )
    bugunku_sayisi = sum(
        1 for u in uyarilar if isinstance(u, dict) and str(u.get("tarih") or "") == bugun_str
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("🚨", "Aktif Uyarı", len(aktif_uyarilar), "Bekleyen sabah maddesi", "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("🔥", "Kritik / Yüksek", kritik_sayisi, "Öncelikli müdahale", "#ef4444"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("📅", "Bugünkü Brifing", bugunku_sayisi, f"Tarih: {bugun_str}", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("✅", "Okundu / İşlendi", okunmus_sayisi, "Tamamlanan uyarı", "#10b981"),
            unsafe_allow_html=True,
        )

    if uyarilar:
        export_satirlari = [
            {
                "ID": u.get("id", "-"),
                "Tarih": u.get("tarih", "-"),
                "Kategori": u.get("kategori", "-"),
                "Önem": u.get("onem_seviyesi", "-"),
                "Başlık": u.get("baslik", "-"),
                "Detay": u.get("detay") or "-",
                "Durum": u.get("durum", "Aktif"),
                "Güncelleyen": u.get("guncelleyen") or "-",
            }
            for u in uyarilar
        ]
        excel_bytes = tablo_to_excel_bytes(
            export_satirlari, f"Aziziye Asevi - Sabah Brifingi ({bugun_str})"
        )
        pdf_bytes = tablo_to_html_pdf_bytes(
            f"Aziziye Asevi - Sabah Brifingi ({bugun_str})", export_satirlari
        )
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "gunluk_sabah_brifingi", "sabah_brifingi_sayfasi")

    st.markdown("---")

    sekme_brifing, sekme_ekle, sekme_yonetim = st.tabs(
        [
            "📋 Sabah Brifingi & Uyarılar",
            "➕ Yeni Brifing / Uyarı Ekle",
            "⚙️ Otomatik Tarama & Bakım",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: SABAH BRİFİNGİ & UYARILAR
    # ---------------------------------------------------------
    with sekme_brifing:
        f1, f2, f3 = st.columns(3)
        with f1:
            kayit_kategorileri = {
                str(u.get("kategori") or "").strip()
                for u in uyarilar
                if isinstance(u, dict) and str(u.get("kategori") or "").strip()
            }
            kategoriler = ["Tümü"] + sorted(set(VARSAYILAN_KATEGORILER) | kayit_kategorileri)
            sec_kat = st.selectbox("🧩 Kategori", kategoriler, key="brf_f_kat")
        with f2:
            sec_onem = st.selectbox(
                "🔥 Önem Seviyesi", ["Tümü", "Kritik", "Yüksek", "Orta", "Düşük"], key="brf_f_onem"
            )
        with f3:
            sec_durum = st.selectbox("📌 Durum", ["Tümü", "Aktif", "Okundu"], key="brf_f_durum")

        filtrelenmis = []
        for u in uyarilar:
            if not isinstance(u, dict):
                continue
            if sec_kat != "Tümü" and str(u.get("kategori") or "") != sec_kat:
                continue
            if sec_onem != "Tümü" and str(u.get("onem_seviyesi") or "") != sec_onem:
                continue
            if sec_durum != "Tümü" and str(u.get("durum") or "Aktif") != sec_durum:
                continue
            filtrelenmis.append(u)

        if filtrelenmis:
            tablo = [
                {
                    "ID": u.get("id", "-"),
                    "Tarih": u.get("tarih", "-"),
                    "Kategori": u.get("kategori", "-"),
                    "Önem": u.get("onem_seviyesi", "-"),
                    "Başlık": u.get("baslik", "-"),
                    "Detay": u.get("detay") or "-",
                    "Durum": u.get("durum", "Aktif"),
                }
                for u in filtrelenmis
            ]
            ozel_html_tablo_goster(tablo)

            if not salt_okunur_modu:
                st.markdown("---")
                secenekler = {
                    f"{u.get('id')} | [{u.get('durum', 'Aktif')}] {u.get('baslik')}": u
                    for u in filtrelenmis
                }
                sec_uyari_etiket = st.selectbox(
                    "✅ Durumu Güncellenecek Uyarıyı Seçin",
                    list(secenekler.keys()),
                    key="brf_durum_sec",
                )
                hedef_u = secenekler[sec_uyari_etiket]
                yeni_durum = "Okundu" if str(hedef_u.get("durum") or "Aktif") != "Okundu" else "Aktif"
                if st.button(f"🔄 '{yeni_durum}' Olarak İşaretle", key="brf_durum_btn"):
                    otomatik_yedek_al(f"Sabah uyarısı durumu: {hedef_u.get('id')} -> {yeni_durum}")
                    for item in st.session_state.sabah_brifingi_uyarilari:
                        if isinstance(item, dict) and item.get("id") == hedef_u.get("id"):
                            item["durum"] = yeni_durum
                            item["guncelleyen"] = aktif_kullanici
                            item["guncelleme_zamani"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            break
                    sabah_brifingi_kaydet(st.session_state.sabah_brifingi_uyarilari)
                    if callable(denetim_kaydi_ekle_fn) and "denetim_izi" in st.session_state:
                        st.session_state.denetim_izi = denetim_kaydi_ekle_fn(
                            st.session_state.denetim_izi,
                            modul="Sabah Brifingi",
                            islem="Güncelleme",
                            kullanici=aktif_kullanici,
                            rol=aktif_rol,
                            kayit_id=str(hedef_u.get("id") or ""),
                            sonraki_veri={"durum": yeni_durum},
                        )
                        if callable(denetim_izi_kaydet_fn):
                            denetim_izi_kaydet_fn(st.session_state.denetim_izi)
                    st.success("✅ Uyarı durumu güncellendi!")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("📭 Seçili filtrelere uygun brifing veya uyarı kaydı bulunmuyor.")

    # ---------------------------------------------------------
    # SEKME 2: YENİ BRİFİNG / UYARI EKLE
    # ---------------------------------------------------------
    with sekme_ekle:
        if salt_okunur_modu:
            st.warning("🔒 Salt okunur modda yeni uyarı eklenemez.")
        else:
            with st.form("yeni_sabah_uyarisi_formu", clear_on_submit=True):
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    y_kat = st.selectbox(
                        "🧩 Kategori",
                        VARSAYILAN_KATEGORILER,
                        key="brf_y_kat",
                    )
                with fc2:
                    y_onem = st.selectbox(
                        "🔥 Önem Seviyesi",
                        ["Kritik", "Yüksek", "Orta", "Düşük"],
                        index=1,
                        key="brf_y_onem",
                    )
                with fc3:
                    y_tarih = st.date_input("📅 Tarih", value=_bugun_tarih(), key="brf_y_tarih").strftime(
                        "%Y-%m-%d"
                    )

                y_baslik = st.text_input(
                    "📌 Brifing / Uyarı Başlığı *",
                    placeholder="Örn: Kuru bakliyat stok kontrolü veya sabah fırın çıkışı",
                ).strip()
                y_detay = st.text_area(
                    "📝 Detay / Aksiyon Notu",
                    placeholder="Vardiya ekibine iletilecek ek bilgi...",
                    height=85,
                ).strip()

                kaydet_btn = st.form_submit_button(
                    "💾 Brifing Maddesi Ekle", type="primary", use_container_width=True
                )
                if kaydet_btn:
                    if not y_baslik:
                        st.error("⚠️ Lütfen en azından bir başlık girin.")
                    else:
                        if callable(uyari_olustur_fn):
                            st.session_state.sabah_brifingi_uyarilari = uyari_olustur_fn(
                                st.session_state.sabah_brifingi_uyarilari,
                                baslik=y_baslik,
                                kategori=y_kat,
                                onem_seviyesi=y_onem,
                                detay=y_detay,
                                tarih=y_tarih,
                                guncelleyen=aktif_kullanici,
                            )
                        else:
                            y_id = yeni_id_uret("BRF-", st.session_state.sabah_brifingi_uyarilari)
                            st.session_state.sabah_brifingi_uyarilari.insert(
                                0,
                                {
                                    "id": y_id,
                                    "tarih": y_tarih,
                                    "kategori": y_kat,
                                    "onem_seviyesi": y_onem,
                                    "baslik": y_baslik,
                                    "detay": y_detay,
                                    "kaynak_id": "",
                                    "durum": "Aktif",
                                    "guncelleyen": aktif_kullanici,
                                },
                            )
                        sabah_brifingi_kaydet(st.session_state.sabah_brifingi_uyarilari)
                        if callable(denetim_kaydi_ekle_fn) and "denetim_izi" in st.session_state:
                            st.session_state.denetim_izi = denetim_kaydi_ekle_fn(
                                st.session_state.denetim_izi,
                                modul="Sabah Brifingi",
                                islem="Ekleme",
                                kullanici=aktif_kullanici,
                                rol=aktif_rol,
                                sonraki_veri={"baslik": y_baslik, "onem": y_onem},
                            )
                            if callable(denetim_izi_kaydet_fn):
                                denetim_izi_kaydet_fn(st.session_state.denetim_izi)
                        st.success("✅ Sabah brifingi maddesi eklendi!")
                        time.sleep(0.5)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 3: OTOMATİK TARAMA & BAKIM
    # ---------------------------------------------------------
    with sekme_yonetim:
        if salt_okunur_modu:
            st.warning("🔒 Salt okunur modda otomatik tarama veya temizleme yapılamaz.")
        else:
            st.markdown("Mevcut stok, kritik eşik, SKT, menü ve teslimat kayıtlarını tarayarak yeni uyarılar üretir.")
            if st.button("🔎 Sistem Verilerini Şimdi Tara", type="primary", key="brf_tara_btn"):
                bulunan = otomatik_uyarilari_tara(st.session_state, referans_tarih=bugun_str)
                mevcut_kaynaklar = {
                    str(u.get("kaynak_id") or "").strip()
                    for u in st.session_state.sabah_brifingi_uyarilari
                    if isinstance(u, dict) and str(u.get("kaynak_id") or "").strip()
                }
                eklenen = 0
                for aday in bulunan:
                    kid = str(aday.get("kaynak_id") or "").strip()
                    if kid and kid in mevcut_kaynaklar:
                        continue
                    st.session_state.sabah_brifingi_uyarilari.insert(0, aday)
                    if kid:
                        mevcut_kaynaklar.add(kid)
                    eklenen += 1
                sabah_brifingi_kaydet(st.session_state.sabah_brifingi_uyarilari)
                st.success(
                    f"✅ Tarama tamamlandı! **{eklenen}** yeni uyarı eklendi "
                    f"(Toplam aday: {len(bulunan)})."
                )
                time.sleep(0.6)
                st.rerun()

            if yonetici_modu:
                st.markdown("---")
                onay_temizle = silme_onay_kutusu("onay_brf_okunmus_sil")
                if st.button("🧹 Okunmuş Uyarıları Temizle", key="brf_okunmus_sil_btn"):
                    if not onay_temizle:
                        st.error("⚠️ Temizlemek için önce onay kutusunu işaretleyin.")
                    else:
                        otomatik_yedek_al("Okunmuş sabah brifingi uyarıları temizlendi")
                        st.session_state.sabah_brifingi_uyarilari = [
                            u
                            for u in st.session_state.sabah_brifingi_uyarilari
                            if isinstance(u, dict) and str(u.get("durum") or "Aktif") != "Okundu"
                        ]
                        sabah_brifingi_kaydet(st.session_state.sabah_brifingi_uyarilari)
                        st.warning("🧹 Okunmuş uyarılar temizlendi.")
                        time.sleep(0.5)
                        st.rerun()
