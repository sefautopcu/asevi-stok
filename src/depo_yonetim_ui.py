import time
from src.ui_kartlar import (
    bolum_basligi_goster,
    kpi_satiri_goster,
    sayfa_ust_banner_goster,
)


def depo_yonetim_sayfasi(
    st,
    misafir_modu,
    yonetici_modu,
    supabase_veri_oku,
    otomatik_yedek_al,
    depoları_kaydet,
    verileri_kaydet,
    supabase_veri_kaydet,
    silme_onay_kutusu,
    ozel_html_tablo_goster,
):
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        sayfa_ust_banner_goster(
            st,
            "depo",
            "Depo ve Kategori Yönetimi",
            "Sisteme yeni depolama alanları ve ürün kategorileri ekleyebilir, mevcut kayıtları yönetebilirsiniz",
            tema="amber",
        )

        # Varsayılan Kategoriler ve Session State Kontrolü
        varsayilan_kategoriler = ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"]
        if "kategoriler" not in st.session_state:
            st.session_state.kategoriler = supabase_veri_oku("kategoriler_listesi", varsayilan_kategoriler, kritik=False)
            if not isinstance(st.session_state.kategoriler, list) or not st.session_state.kategoriler:
                st.session_state.kategoriler = list(varsayilan_kategoriler)

        girisler_liste = st.session_state.get("girisler", []) or []
        aktif_parti_sayisi = sum(1 for _g in girisler_liste if float(_g.get("kalan", 0) or 0) > 0)
        kpi_satiri_goster(
            st,
            [
                ("depo", "Aktif Depo Sayısı", len(st.session_state.depolar), "Tanımlı fiziksel depolama alanı", "#f59e0b"),
                ("liste", "Ürün Kategorisi", len(st.session_state.kategoriler), "Sistemde kayıtlı ürün grupları", "#38bdf8"),
                ("stok", "Stoklu Parti", aktif_parti_sayisi, "Depolarda bakiyesi bulunan girişler", "#10b981"),
                ("fatura", "Toplam Hareket", len(girisler_liste), "Depolara işlenen toplam fatura kaydı", "#a855f7"),
            ],
        )

        # Son Depo veya Kategori İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_depo_kat_islem"):
            son_islem = st.session_state["son_depo_kat_islem"]
            tur = son_islem.get("tur")
            ad = son_islem.get("ad")

            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "depo_ekle":
                    st.info(f"💡 **Son İşlem:** '{ad}' deposu eklendi.")
                elif tur == "depo_sil":
                    st.info(f"💡 **Son İşlem:** '{ad}' deposu ve ilgili kayıtlar silindi.")
                elif tur == "kat_ekle":
                    st.info(f"💡 **Son İşlem:** '{ad}' kategorisi eklendi.")
                elif tur == "kat_sil":
                    st.info(f"💡 **Son İşlem:** '{ad}' kategorisi silindi.")

            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_depo_kat_son"):
                    otomatik_yedek_al("Depo/Kategori işlemi geri alma: " + str(ad))

                    if tur == "depo_ekle":
                        if ad in st.session_state.depolar:
                            st.session_state.depolar.remove(ad)
                            depoları_kaydet(st.session_state.depolar)
                    elif tur == "depo_sil":
                        if ad not in st.session_state.depolar:
                            st.session_state.depolar.append(ad)
                            depoları_kaydet(st.session_state.depolar)
                        # Silinen bağlı alım kayıtlarını geri yükle
                        silinen_girisler = son_islem.get("silinen_girisler", [])
                        if silinen_girisler:
                            st.session_state.girisler.extend(silinen_girisler)
                            verileri_kaydet(st.session_state.girisler)
                    elif tur == "kat_ekle":
                        if ad in st.session_state.kategoriler:
                            st.session_state.kategoriler.remove(ad)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)
                    elif tur == "kat_sil":
                        if ad not in st.session_state.kategoriler:
                            st.session_state.kategoriler.append(ad)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)

                    st.session_state.pop("son_depo_kat_islem", None)
                    st.success(f"🎉 '{ad}' üzerine yapılan son işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        depo_tab1, depo_tab2 = st.tabs(["🏢 Depo Yönetimi", "🏷️ Kategori Yönetimi"])

        # TAB 1: DEPO YÖNETİMİ
        with depo_tab1:
            col_depo_ekle, col_depo_sil = st.columns(2)
            with col_depo_ekle:
                with st.form("yeni_depo_ekle_form"):
                    st.markdown("**➕ Yeni Depo Ekle**")
                    yeni_depo_adi = st.text_input("Depo Adı (Örn: Soğuk Hava Deposu -20)").strip()
                    depo_ekle_btn = st.form_submit_button("Depoyu Kaydet", type="primary")

                    if depo_ekle_btn and yeni_depo_adi:
                        if yeni_depo_adi in st.session_state.depolar:
                            st.error("⚠️ Bu depo zaten mevcut!")
                        else:
                            st.session_state.depolar.append(yeni_depo_adi)
                            depoları_kaydet(st.session_state.depolar)

                            st.session_state["son_depo_kat_islem"] = {
                                "tur": "depo_ekle",
                                "ad": yeni_depo_adi,
                            }

                            st.success(f"🎉 Başarılı! '{yeni_depo_adi}' deposu eklendi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

            with col_depo_sil:
                if not yonetici_modu:
                    st.info("🗑️ Depo silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("depo_sil_form"):
                        st.markdown("**🗑️ Depo Sil**")
                        if st.session_state.depolar:
                            secilen_sil_depo = st.selectbox("Silinecek Depoyu Seçin", st.session_state.depolar)
                            onay_depo_sil_btn = silme_onay_kutusu("onay_depo_sil")
                            depo_sil_btn = st.form_submit_button("Seçilen Depoyu ve Bağlı Ürünleri Sil", type="primary")

                            if depo_sil_btn:
                                if not onay_depo_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                elif len(st.session_state.depolar) <= 1:
                                    st.error("⚠️ Sistemde en az 1 depo kalmalıdır, tamamen silemezsiniz!")
                                else:
                                    otomatik_yedek_al("Depo silme: " + str(secilen_sil_depo))

                                    # Silinecek depoya bağlı alım kayıtlarını sakla (Geri Al için)
                                    silinecek_girisler = [g for g in st.session_state.girisler if g.get("depo") == secilen_sil_depo]

                                    st.session_state.depolar.remove(secilen_sil_depo)
                                    depoları_kaydet(st.session_state.depolar)

                                    st.session_state.girisler = [g for g in st.session_state.girisler if g.get("depo") != secilen_sil_depo]
                                    verileri_kaydet(st.session_state.girisler)

                                    st.session_state["son_depo_kat_islem"] = {
                                        "tur": "depo_sil",
                                        "ad": secilen_sil_depo,
                                        "silinen_girisler": silinecek_girisler,
                                    }

                                    st.success(f"🎉 Başarılı! '{secilen_sil_depo}' deposu ve bağlı ürünler silindi.")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.info("Silinecek depo bulunmuyor.")

            st.markdown("---")
            bolum_basligi_goster(
                st,
                "depo",
                "Aktif Depolar Listesi",
                "Sistemde tanımlı tüm fiziksel depolama noktaları",
                vurgu_renk="#f59e0b",
            )
            depo_tablosu = [{"Depo Adı": d} for d in st.session_state.depolar]
            ozel_html_tablo_goster(depo_tablosu)

        # TAB 2: KATEGORİ YÖNETİMİ
        with depo_tab2:
            col_kat_ekle, col_kat_sil = st.columns(2)
            with col_kat_ekle:
                with st.form("yeni_kat_ekle_form"):
                    st.markdown("**➕ Yeni Ürün Kategorisi Ekle**")
                    yeni_kat_adi = st.text_input("Kategori Adı (Örn: TEK KULLANIMLIK / AMBALAJ)").strip().upper()
                    kat_ekle_btn = st.form_submit_button("Kategoriyi Kaydet", type="primary")

                    if kat_ekle_btn and yeni_kat_adi:
                        if yeni_kat_adi in st.session_state.kategoriler:
                            st.error("⚠️ Bu kategori zaten mevcut!")
                        else:
                            st.session_state.kategoriler.append(yeni_kat_adi)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)

                            st.session_state["son_depo_kat_islem"] = {
                                "tur": "kat_ekle",
                                "ad": yeni_kat_adi,
                            }

                            st.success(f"🎉 Başarılı! '{yeni_kat_adi}' kategorisi eklendi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

            with col_kat_sil:
                if not yonetici_modu:
                    st.info("🗑️ Kategori silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("kat_sil_form"):
                        st.markdown("**🗑️ Ürün Kategorisi Sil**")
                        if st.session_state.kategoriler:
                            secilen_sil_kat = st.selectbox("Silinecek Kategoriyi Seçin", st.session_state.kategoriler)
                            onay_kat_sil_btn = silme_onay_kutusu("onay_kat_sil")
                            kat_sil_btn = st.form_submit_button("Seçilen Kategoriyi Sil", type="primary")

                            if kat_sil_btn:
                                if not onay_kat_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                elif len(st.session_state.kategoriler) <= 1:
                                    st.error("⚠️ Sistemde en az 1 kategori kalmalıdır!")
                                else:
                                    st.session_state.kategoriler.remove(secilen_sil_kat)
                                    supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)

                                    st.session_state["son_depo_kat_islem"] = {
                                        "tur": "kat_sil",
                                        "ad": secilen_sil_kat,
                                    }

                                    st.success(f"🎉 Başarılı! '{secilen_sil_kat}' kategorisi silindi.")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.info("Silinecek kategori bulunmuyor.")

            st.markdown("---")
            bolum_basligi_goster(
                st,
                "liste",
                "Kayıtlı Ürün Kategorileri Listesi",
                "Mal alımı ve stok raporlamasında kullanılan ürün sınıflandırmaları",
                vurgu_renk="#38bdf8",
            )
            kat_tablosu = [{"Kategori Adı": k} for k in st.session_state.kategoriler]
            ozel_html_tablo_goster(kat_tablosu)
