import datetime
import html
import json
import time

SAYFA_ETIKETI_DENETIM_IZI = "Denetim İzi (Audit Log)"

MODUL_KOLEKSIYON_HARITASI = {
    "haftalik_menu": "haftalik_menu",
    "haftalık menü": "haftalik_menu",
    "rota_teslimat": "rota_teslimat",
    "rota & teslimat": "rota_teslimat",
    "arac_seferleri": "arac_seferleri",
    "araç sefer": "arac_seferleri",
    "yemek_receteleri": "yemek_receteleri",
    "reçeteler": "yemek_receteleri",
    "stok": "girisler",
    "girisler": "girisler",
    "personeller": "personeller",
}


def _sayfa_maskeli_mi(aktif_k_maskeleri):
    """Kullanıcı bazlı sayfa maskeleme / gizleme kontrolünü yapar."""
    if not isinstance(aktif_k_maskeleri, list):
        return False
    hedef = SAYFA_ETIKETI_DENETIM_IZI.lower()
    for maske in aktif_k_maskeleri:
        m_str = str(maske or "").strip().lower()
        if m_str in ("denetim_izi", "denetim izi", "audit log", "audit_log") or hedef in m_str:
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


def _json_ayristir(veri):
    if veri is None or veri == "":
        return None
    if isinstance(veri, (dict, list)):
        return veri
    if isinstance(veri, str):
        metin = veri.strip()
        if not metin:
            return None
        try:
            return json.loads(metin)
        except Exception:
            return metin
    return veri


def mevcut_kayitlari_denetim_izine_aktar(session_state, mevcut_denetim_listesi=None):
    """Sistemdeki eski kullanım, silme, fire ve üretim loglarını denetim_izi formatına dönüştürür."""
    mevcut_liste = list(mevcut_denetim_listesi) if isinstance(mevcut_denetim_listesi, list) else []
    mevcut_idler = {
        str(k.get("id") or "").strip()
        for k in mevcut_liste
        if isinstance(k, dict) and str(k.get("id") or "").strip()
    }
    eklenen_sayisi = 0

    def _ekle_eger_yoksa(kayit_sozlugu):
        nonlocal eklenen_sayisi
        kid = str(kayit_sozlugu.get("id") or "").strip()
        if not kid or kid in mevcut_idler:
            return
        mevcut_liste.append(kayit_sozlugu)
        mevcut_idler.add(kid)
        eklenen_sayisi += 1

    # 1. Silinen Ürün Logları
    silinenler = _state_al(session_state, "silinen_urun_loglari", [])
    if isinstance(silinenler, list):
        for idx, s in enumerate(silinenler, start=1):
            if not isinstance(s, dict):
                continue
            urun = str(s.get("urun") or s.get("urun_adi") or "Bilinmeyen Ürün").strip()
            miktar = s.get("miktar") or s.get("silinen_miktar") or "-"
            birim = s.get("birim") or ""
            zaman = str(s.get("tarih") or s.get("zaman") or s.get("silinme_tarihi") or "").strip()
            kullanici = str(s.get("kullanici") or s.get("silen") or "sistem").strip() or "sistem"
            orijinal_id = str(s.get("id") or f"SIL-{idx}").strip()
            _ekle_eger_yoksa(
                {
                    "id": f"SYNC-SIL-{orijinal_id}",
                    "zaman": zaman,
                    "kullanici": kullanici,
                    "rol": "",
                    "modul": "Stok & Depo",
                    "islem": "Silme",
                    "kayit_id": orijinal_id,
                    "onceki_veri": json.dumps(s, ensure_ascii=False),
                    "sonraki_veri": f"{urun} ({miktar} {birim}) stoktan silindi".strip(),
                }
            )

    # 2. Stok Kullanım Logları
    kullanimlar = _state_al(session_state, "kullanim_loglari", [])
    if isinstance(kullanimlar, list):
        for idx, k in enumerate(kullanimlar, start=1):
            if not isinstance(k, dict):
                continue
            urun = str(k.get("urun") or k.get("urun_adi") or "Malzeme").strip()
            miktar = k.get("miktar") or k.get("kullanilan_miktar") or "-"
            birim = k.get("birim") or ""
            zaman = str(k.get("tarih") or k.get("zaman") or "").strip()
            kullanici = str(k.get("kullanici") or "sistem").strip() or "sistem"
            orijinal_id = str(k.get("id") or f"KUL-{idx}").strip()
            _ekle_eger_yoksa(
                {
                    "id": f"SYNC-KUL-{orijinal_id}",
                    "zaman": zaman,
                    "kullanici": kullanici,
                    "rol": "",
                    "modul": "Stok & Depo",
                    "islem": "Güncelleme",
                    "kayit_id": orijinal_id,
                    "onceki_veri": "",
                    "sonraki_veri": f"{urun} çıkışı / kullanımı: {miktar} {birim}".strip(),
                }
            )

    # 3. Fire ve Zayi Kayıtları
    fireler = _state_al(session_state, "fire_kayitlari", [])
    if isinstance(fireler, list):
        for idx, f in enumerate(fireler, start=1):
            if not isinstance(f, dict):
                continue
            urun = str(f.get("urun") or f.get("urun_adi") or "Ürün").strip()
            miktar = f.get("miktar") or "-"
            birim = f.get("birim") or ""
            neden = str(f.get("neden") or f.get("aciklama") or "").strip()
            zaman = str(f.get("tarih") or f.get("zaman") or "").strip()
            kullanici = str(f.get("kullanici") or "sistem").strip() or "sistem"
            orijinal_id = str(f.get("id") or f"FIR-{idx}").strip()
            _ekle_eger_yoksa(
                {
                    "id": f"SYNC-FIR-{orijinal_id}",
                    "zaman": zaman,
                    "kullanici": kullanici,
                    "rol": "",
                    "modul": "Stok & Depo",
                    "islem": "Silme",
                    "kayit_id": orijinal_id,
                    "onceki_veri": json.dumps(f, ensure_ascii=False),
                    "sonraki_veri": f"Fire/İade: {urun} ({miktar} {birim}) - {neden}".strip(" -"),
                }
            )

    # 4. Günlük Yemek Üretim Logları
    uretimler = _state_al(session_state, "uretim_loglari", [])
    if isinstance(uretimler, list):
        for idx, u in enumerate(uretimler, start=1):
            if not isinstance(u, dict):
                continue
            yemek = str(u.get("yemek_adi") or u.get("yemek") or u.get("menu") or "Günlük Üretim").strip()
            porsiyon = u.get("porsiyon") or u.get("kisi_sayisi") or "-"
            zaman = str(u.get("tarih") or u.get("zaman") or "").strip()
            kullanici = str(u.get("kullanici") or "sistem").strip() or "sistem"
            orijinal_id = str(u.get("id") or f"URT-{idx}").strip()
            _ekle_eger_yoksa(
                {
                    "id": f"SYNC-URT-{orijinal_id}",
                    "zaman": zaman,
                    "kullanici": kullanici,
                    "rol": "",
                    "modul": "Günlük Yemek Üretimi",
                    "islem": "Ekleme",
                    "kayit_id": orijinal_id,
                    "onceki_veri": "",
                    "sonraki_veri": f"Üretim: {yemek} ({porsiyon} porsiyon)",
                }
            )

    mevcut_liste.sort(key=lambda x: str(x.get("zaman") or ""), reverse=True)
    return mevcut_liste, eklenen_sayisi


def _profil_ve_kullanicilari_topla(st, kayitlar):
    """Denetim kayıtlarındaki ve sistemdeki (admin, asci, yonetim, misafir vb.) kullanıcıları döndürür."""
    log_kullanicilari = {
        str(k.get("kullanici") or k.get("kullanici_adi") or "").strip()
        for k in (kayitlar or [])
        if isinstance(k, dict) and str(k.get("kullanici") or k.get("kullanici_adi") or "").strip()
    }

    tanimli_kullanicilar = set()
    for anahtar in ("kullanicilar", "kullanici_hesaplari", "kullanici_yetkileri", "users"):
        deger = _state_al(st.session_state, anahtar)
        if isinstance(deger, dict):
            for k_ad, k_icerik in deger.items():
                ad_str = str(k_ad or "").strip()
                if ad_str and not ad_str.startswith("_"):
                    tanimli_kullanicilar.add(ad_str)
                if isinstance(k_icerik, dict):
                    ic_ad = str(
                        k_icerik.get("kullanici")
                        or k_icerik.get("kullanici_adi")
                        or k_icerik.get("ad")
                        or ""
                    ).strip()
                    if ic_ad:
                        tanimli_kullanicilar.add(ic_ad)
        elif isinstance(deger, list):
            for item in deger:
                if isinstance(item, dict):
                    ic_ad = str(
                        item.get("kullanici")
                        or item.get("kullanici_adi")
                        or item.get("ad")
                        or ""
                    ).strip()
                    if ic_ad:
                        tanimli_kullanicilar.add(ic_ad)
                elif isinstance(item, str) and item.strip():
                    tanimli_kullanicilar.add(item.strip())

    if not tanimli_kullanicilar:
        try:
            from src.kullanici_yonetimi import kullanıcıları_yukle

            yuklenen = kullanıcıları_yukle()
            if isinstance(yuklenen, dict):
                for k_ad in yuklenen.keys():
                    ad_str = str(k_ad or "").strip()
                    if ad_str and not ad_str.startswith("_"):
                        tanimli_kullanicilar.add(ad_str)
        except Exception:
            pass

    if not tanimli_kullanicilar:
        tanimli_kullanicilar.update({"admin", "asci", "yonetim", "misafir"})

    aktif_k = str(_state_al(st.session_state, "aktif_kullanici") or "").strip()
    if aktif_k:
        tanimli_kullanicilar.add(aktif_k)

    tum_kullanicilar = sorted(log_kullanicilari | tanimli_kullanicilar)
    return log_kullanicilari, tum_kullanicilar


def denetim_kayitlarini_filtrele(kayitlar, kullanici="Tümü", modul="Tümü", islem="Tümü", arama=""):
    """Denetim izi kayıtlarını kullanıcı, modül, işlem ve arama metnine göre filtreler."""
    k_filtre = str(kullanici or "Tümü").strip()
    m_filtre = str(modul or "Tümü").strip()
    i_filtre = str(islem or "Tümü").strip()
    q_filtre = str(arama or "").strip().lower()

    sonuc = []
    for kayit in (kayitlar or []):
        if not isinstance(kayit, dict):
            continue
        k_val = str(kayit.get("kullanici") or "").strip()
        m_val = str(kayit.get("modul") or "").strip()
        i_val = str(kayit.get("islem") or "").strip()

        if k_filtre != "Tümü" and k_val != k_filtre:
            continue
        if m_filtre != "Tümü" and m_val != m_filtre:
            continue
        if i_filtre != "Tümü" and i_val != i_filtre:
            continue

        if q_filtre:
            birlesik = " ".join(
                [
                    str(kayit.get("id") or ""),
                    str(kayit.get("zaman") or ""),
                    k_val,
                    m_val,
                    i_val,
                    str(kayit.get("kayit_id") or ""),
                    str(kayit.get("onceki_veri") or ""),
                    str(kayit.get("sonraki_veri") or ""),
                ]
            ).lower()
            if q_filtre not in birlesik:
                continue

        sonuc.append(kayit)
    return sonuc


def hedef_koleksiyon_bul(modul_adi):
    """Modül adına karşılık gelen session_state koleksiyon anahtarını döndürür."""
    m = str(modul_adi or "").strip().lower()
    if m in MODUL_KOLEKSIYON_HARITASI:
        return MODUL_KOLEKSIYON_HARITASI[m]
    for anahtar, koleksiyon in MODUL_KOLEKSIYON_HARITASI.items():
        if anahtar in m:
            return koleksiyon
    return None


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


def denetim_izi_sayfasi(
    st,
    misafir_modu,
    salt_okunur_modu,
    yonetici_modu,
    aktif_k_maskeleri,
    otomatik_yedek_al,
    denetim_izi_kaydet,
    yeni_id_uret,
    silme_onay_kutusu,
    tablo_to_excel_bytes,
    tablo_to_html_pdf_bytes,
    ortak_indirme_alani,
    ozel_html_tablo_goster,
    denetim_kaydi_ekle_fn=None,
    aktif_kullanici="sistem",
    aktif_rol="",
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
        return

    if _sayfa_maskeli_mi(aktif_k_maskeleri):
        st.info("🔒 Denetim İzi (Audit Log) sayfası bu kullanıcı profili için maskelenmiştir.")
        return

    if "denetim_izi" not in st.session_state or not isinstance(st.session_state.denetim_izi, list):
        st.session_state.denetim_izi = []

    kayitlar = st.session_state.denetim_izi

    col_baslik, col_indir = st.columns([2.2, 1.8])
    with col_baslik:
        st.markdown(
            """
            <div style="
                background: linear-gradient(90deg, rgba(168,85,247,0.18) 0%, rgba(56,189,248,0.14) 100%);
                border: 1px solid rgba(168,85,247,0.32);
                border-radius: 14px;
                padding: 14px 20px;
                margin-bottom: 12px;
            ">
                <div style="font-size: 1.42rem; font-weight: 800; color: #f8fafc;">
                    🕵️ Gelişmiş Denetim İzi (Audit Log) ve İşlem Geçmişi
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 4px;">
                    Kullanıcı bazlı işlem geçmişi, işlem öncesi/sonrası değer incelemesi ve seçili kaydı geri alma
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    varsayilan_moduller = {
        "Stok & Depo",
        "Günlük Yemek Üretimi",
        "Hazır Yemek Reçeteleri",
        "Haftalık Menü Planlama",
        "Sıcak Yemek Seferleri",
        "Rota & Teslimat",
        "Personel & İzin",
        "Kullanıcı & Yetki",
        "Sabah Brifingi",
        "Genel",
    }
    varsayilan_islemler = {
        "Ekleme",
        "Güncelleme",
        "Silme",
        "Geri Alma (Restore)",
        "Manuel Not / Kontrol",
    }

    log_kullanicilari, tum_kullanicilar = _profil_ve_kullanicilari_topla(st, kayitlar)
    aktif_moduller = sorted(
        varsayilan_moduller
        | {str(k.get("modul") or "").strip() for k in kayitlar if isinstance(k, dict) and str(k.get("modul") or "").strip()}
    )
    aktif_islemler = sorted(
        varsayilan_islemler
        | {str(k.get("islem") or "").strip() for k in kayitlar if isinstance(k, dict) and str(k.get("islem") or "").strip()}
    )
    geri_alinabilir_sayisi = sum(
        1 for k in kayitlar if isinstance(k, dict) and k.get("onceki_veri")
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            _kpi_karti_html("📜", "Toplam Denetim Kaydı", len(kayitlar), "Kayıtlı işlem izi", "#38bdf8"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            _kpi_karti_html("👤", "Aktif Kullanıcı", len(log_kullanicilari), "İşlem yapan hesap sayısı", "#10b981"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            _kpi_karti_html("🧩", "Kapsanan Modül", len(aktif_moduller), "İzlenen sistem modülü", "#f59e0b"),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            _kpi_karti_html("⏪", "Geri Alınabilir Kayıt", geri_alinabilir_sayisi, "Önceki veri içeren kayıt", "#a855f7"),
            unsafe_allow_html=True,
        )

    if kayitlar:
        export_satirlari = [
            {
                "Log ID": k.get("id", "-"),
                "Zaman": k.get("zaman", "-"),
                "Kullanıcı": k.get("kullanici", "-"),
                "Rol": k.get("rol") or "-",
                "Modül": k.get("modul", "-"),
                "İşlem": k.get("islem", "-"),
                "Kayıt ID": k.get("kayit_id") or "-",
                "Önceki Veri": str(k.get("onceki_veri") or "-"),
                "Sonraki Veri": str(k.get("sonraki_veri") or "-"),
            }
            for k in kayitlar
        ]
        excel_bytes = tablo_to_excel_bytes(export_satirlari, "Aziziye Aşevi - Denetim İzi (Audit Log)")
        pdf_bytes = tablo_to_html_pdf_bytes("Aziziye Aşevi - Denetim İzi (Audit Log)", export_satirlari)
        with col_indir:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            ortak_indirme_alani(excel_bytes, pdf_bytes, "denetim_izi_audit_log", "denetim_izi_sayfasi")

    if not salt_okunur_modu:
        if st.button(
            "🔄 Mevcut Sistem Loglarını Denetim İzine Aktar (Senkronize Et)",
            key="dnt_senkronize_btn",
        ):
            yeni_liste, eklenen = mevcut_kayitlari_denetim_izine_aktar(
                st.session_state, st.session_state.denetim_izi
            )
            st.session_state.denetim_izi = yeni_liste
            denetim_izi_kaydet(st.session_state.denetim_izi)
            st.success(f"✅ Senkronizasyon tamamlandı! **{eklenen}** adet mevcut işlem kaydı Denetim İzine aktarıldı.")
            time.sleep(0.6)
            st.rerun()

    st.markdown("---")

    sekme_gecmis, sekme_detay, sekme_manuel = st.tabs(
        [
            "📜 İşlem Geçmişi & Filtreler",
            "🔍 Önceki / Sonraki Değer & Geri Alma",
            "📝 Manuel Denetim Notu Ekle",
        ]
    )

    # ---------------------------------------------------------
    # SEKME 1: İŞLEM GEÇMİŞİ & FİLTRELER
    # ---------------------------------------------------------
    with sekme_gecmis:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            sec_k = st.selectbox("👤 Kullanıcı", ["Tümü"] + tum_kullanicilar, key="dnt_f_kul")
        with f2:
            sec_m = st.selectbox("🧩 Modül", ["Tümü"] + aktif_moduller, key="dnt_f_mod")
        with f3:
            sec_i = st.selectbox("⚡ İşlem", ["Tümü"] + aktif_islemler, key="dnt_f_isl")
        with f4:
            arama_metni = st.text_input("🔎 Kayıt ID / Metin Ara", placeholder="Örn: RTS-01, Silme", key="dnt_f_ara")

        filtrelenmis = denetim_kayitlarini_filtrele(kayitlar, sec_k, sec_m, sec_i, arama_metni)
        if filtrelenmis:
            tablo = [
                {
                    "Log ID": k.get("id", "-"),
                    "Zaman": k.get("zaman", "-"),
                    "Kullanıcı": k.get("kullanici", "-"),
                    "Rol": k.get("rol") or "-",
                    "Modül": k.get("modul", "-"),
                    "İşlem": k.get("islem", "-"),
                    "Kayıt ID": k.get("kayit_id") or "-",
                    "Özet": str(k.get("sonraki_veri") or k.get("onceki_veri") or "-")[:90],
                }
                for k in filtrelenmis
            ]
            ozel_html_tablo_goster(tablo)
        else:
            st.info("📭 Filtre kriterlerine uygun denetim kaydı bulunmuyor.")

    # ---------------------------------------------------------
    # SEKME 2: ÖNCEKİ / SONRAKI DEĞER & GERİ ALMA
    # ---------------------------------------------------------
    with sekme_detay:
        if not kayitlar:
            st.info("📭 İncelenecek denetim kaydı bulunmuyor.")
        else:
            kayit_secenekleri = {
                f"{k.get('id')} | {k.get('zaman')} | {k.get('modul')} - {k.get('islem')} ({k.get('kayit_id') or '-'})": k
                for k in kayitlar
            }
            sec_etiket = st.selectbox("📌 İncelenecek Denetim Kaydı", list(kayit_secenekleri.keys()), key="dnt_detay_sec")
            hedef_log = kayit_secenekleri[sec_etiket]

            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown("**⬅️ İşlem Öncesi Veri (`onceki_veri`)**")
                onceki_parsed = _json_ayristir(hedef_log.get("onceki_veri"))
                if isinstance(onceki_parsed, (dict, list)):
                    st.json(onceki_parsed)
                else:
                    st.code(str(onceki_parsed or "Kayıt yok"), language="text")

            with dc2:
                st.markdown("**➡️ İşlem Sonrası Veri (`sonraki_veri`)**")
                sonraki_parsed = _json_ayristir(hedef_log.get("sonraki_veri"))
                if isinstance(sonraki_parsed, (dict, list)):
                    st.json(sonraki_parsed)
                else:
                    st.code(str(sonraki_parsed or "Kayıt yok"), language="text")

            if yonetici_modu and not salt_okunur_modu:
                st.markdown("---")
                koleksiyon_adi = hedef_koleksiyon_bul(hedef_log.get("modul"))
                if isinstance(onceki_parsed, dict) and koleksiyon_adi and onceki_parsed.get("id"):
                    if st.button(
                        f"⏪ Önceki Kaydı Geri Yükle ({koleksiyon_adi} -> {onceki_parsed.get('id')})",
                        type="primary",
                        key="dnt_geri_al_btn",
                    ):
                        otomatik_yedek_al(f"Denetim izinden geri yükleme: {onceki_parsed.get('id')}")
                        hedef_liste = st.session_state.get(koleksiyon_adi)
                        if not isinstance(hedef_liste, list):
                            hedef_liste = []
                            st.session_state[koleksiyon_adi] = hedef_liste

                        hedef_kayit_id = str(onceki_parsed.get("id"))
                        guncellendi = False
                        for idx, item in enumerate(hedef_liste):
                            if isinstance(item, dict) and str(item.get("id") or "") == hedef_kayit_id:
                                hedef_liste[idx] = onceki_parsed
                                guncellendi = True
                                break
                        if not guncellendi:
                            hedef_liste.append(onceki_parsed)

                        kaydet_fn = globals().get(f"{koleksiyon_adi}_kaydet")
                        if callable(kaydet_fn):
                            kaydet_fn(hedef_liste)

                        if callable(denetim_kaydi_ekle_fn):
                            st.session_state.denetim_izi = denetim_kaydi_ekle_fn(
                                st.session_state.denetim_izi,
                                modul=hedef_log.get("modul") or koleksiyon_adi,
                                islem="Geri Alma (Restore)",
                                kullanici=aktif_kullanici,
                                rol=aktif_rol,
                                kayit_id=hedef_kayit_id,
                                onceki_veri=sonraki_parsed,
                                sonraki_veri=onceki_parsed,
                            )
                            denetim_izi_kaydet(st.session_state.denetim_izi)

                        st.success(f"✅ **{hedef_kayit_id}** kaydı önceki haline geri yüklendi!")
                        time.sleep(0.7)
                        st.rerun()

                st.markdown("---")
                onay_dnt = silme_onay_kutusu("onay_dnt_sil")
                if st.button("🗑️ Seçili Denetim Kaydını Sil", key="dnt_sil_btn"):
                    if not onay_dnt:
                        st.error("⚠️ Silmek için önce onay kutusunu işaretleyin.")
                    else:
                        sil_id = hedef_log.get("id")
                        otomatik_yedek_al(f"Denetim kaydı silindi: {sil_id}")
                        st.session_state.denetim_izi = [
                            k for k in st.session_state.denetim_izi if k.get("id") != sil_id
                        ]
                        denetim_izi_kaydet(st.session_state.denetim_izi)
                        st.warning(f"🗑️ **{sil_id}** denetim kaydı silindi.")
                        time.sleep(0.6)
                        st.rerun()

    # ---------------------------------------------------------
    # SEKME 3: MANUEL DENETİM NOTU EKLE
    # ---------------------------------------------------------
    with sekme_manuel:
        if salt_okunur_modu:
            st.warning("🔒 Salt okunur modda denetim kaydı eklenemez.")
        else:
            with st.form("manuel_denetim_kaydi_formu", clear_on_submit=True):
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    m_modul = st.text_input("🧩 Modül Adı *", value="Genel", placeholder="Örn: Stok, Üretim, Rota").strip()
                with mc2:
                    m_islem = st.text_input("⚡ İşlem Türü *", value="Manuel Not / Kontrol", placeholder="Örn: Sayım Kontrolü").strip()
                with mc3:
                    m_kayit_id = st.text_input("🔖 İlgili Kayıt ID", placeholder="Örn: STK-001").strip()

                m_aciklama = st.text_area("📝 İşlem / Denetim Açıklaması *", placeholder="Yapılan işlem veya tespit edilen durum...", height=90).strip()

                ekle_dnt_btn = st.form_submit_button("💾 Denetim Kaydı Ekle", type="primary", use_container_width=True)
                if ekle_dnt_btn:
                    if not m_modul or not m_islem or not m_aciklama:
                        st.error("⚠️ Lütfen modül, işlem türü ve açıklama alanlarını doldurun.")
                    else:
                        if callable(denetim_kaydi_ekle_fn):
                            st.session_state.denetim_izi = denetim_kaydi_ekle_fn(
                                st.session_state.denetim_izi,
                                modul=m_modul,
                                islem=m_islem,
                                kullanici=aktif_kullanici,
                                rol=aktif_rol,
                                kayit_id=m_kayit_id,
                                sonraki_veri={"not": m_aciklama},
                            )
                        else:
                            y_id = yeni_id_uret("DNT-", st.session_state.denetim_izi)
                            st.session_state.denetim_izi.insert(
                                0,
                                {
                                    "id": y_id,
                                    "zaman": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "kullanici": aktif_kullanici,
                                    "rol": aktif_rol,
                                    "modul": m_modul,
                                    "islem": m_islem,
                                    "kayit_id": m_kayit_id,
                                    "onceki_veri": "",
                                    "sonraki_veri": m_aciklama,
                                },
                            )
                        denetim_izi_kaydet(st.session_state.denetim_izi)
                        st.success("✅ Denetim kaydı eklendi!")
                        time.sleep(0.6)
                        st.rerun()
