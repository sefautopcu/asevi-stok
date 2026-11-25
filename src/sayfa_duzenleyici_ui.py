import hashlib
import json
import secrets

import pandas as pd

ARAYUZ_SAYFA_AYARLARI_ID = "arayuz_sayfa_ayarlari"
SAYFA_GRUPLARI = (
    "🏠 Genel Bakış",
    "📦 Depo & Stok Yönetimi",
    "🍲 Üretim & Mutfak",
    "👥 Sosyal & İnsan Kaynakları",
    "📈 Raporlar & Arşiv",
    "⚙️ Sistem Ayarları",
)
VARSAYILAN_BASLIK_RENKLERI = ("#F4F4F5", "#10B981", "#94A3B8", "#38BDF8")
SAYFA_VARSAYILAN_BASLIKLARI = {
    "Kurumsal Dashboard & Özet": "Genel Bakış & Operasyonel Özet",
    "Genel Bakış": "Genel Bakış & Operasyonel Özet",
    "Güncel Stok Durumu": "📦 Güncel Depo Envanteri ve Kritik Stoklar",
    "Yeni Mal Alımı / Fatura Ekle": "📝 Yeni Fatura ve Mal Alımı Girişi",
    "Depo Yönetimi": "🏢 Depo ve Kategori Yönetimi",
    "Demirbaş Yönetimi": "🛠️ Aşevi Demirbaş ve Ekipman Yönetimi",
    "QR Kod ile Hızlı Sarfiyat": "📷 QR Kod ile Hızlı Stok Düşümü",
    "Ürün Sil / Düzenle": "🗑️ Sistemden Ürün veya Kayıt Silme",
    "Fire / Zayiat Girişi": "🗑️ Fire / Zayiat Bildirimi",
    "Toplu Stok Düşümü & Sarfiyat": "🔄 Toplu Stok Düşümü ve Kullanılan Ürünler",
    "Günlük Yemek Üretimi & Maliyet Raporu": (
        "🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi"
    ),
    "Kalori Hesaplama Aracı": "🔥 Reçete ve Kalori Analiz Merkezi",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi": (
        "👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi"
    ),
    "Personel & Çalışma Süresi Takibi": "👥 Personel ve Çalışma Süresi Takibi",
    "Kullanım Takibi": "📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi",
    "Kapsamlı Envanter ve Hareket Raporu": (
        "📋 Kapsamlı Envanter ve Hareket Raporu"
    ),
    "Ürün Birim Fiyatları & Ay Analizi": (
        "💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi"
    ),
    "Kullanıcı Ayarları": "⚙️ Kullanıcı Yönetimi, Güvenlik ve Yedekleme",
}


def _arayuz_renk_kodu_gecerli_mi(deger):
    return (
        isinstance(deger, str)
        and len(deger) == 7
        and deger[0] == "#"
        and all(karakter in "0123456789abcdefABCDEF" for karakter in deger[1:])
    )


def _arayuz_sayisini_sinirla(deger, varsayilan, en_az, en_cok):
    try:
        sayi = int(deger)
    except (TypeError, ValueError):
        sayi = varsayilan
    return max(en_az, min(sayi, en_cok))


def arayuz_sayfa_ayarlarini_duzenle(veri):
    if not isinstance(veri, dict):
        veri = {}

    sayfalar = {}
    ham_sayfalar = veri.get("sayfalar", {})
    if isinstance(ham_sayfalar, dict):
        for sayfa_id, ham_ayar in ham_sayfalar.items():
            if not isinstance(sayfa_id, str) or not isinstance(ham_ayar, dict):
                continue
            grup = ham_ayar.get("grup")
            renkler = ham_ayar.get("baslik_renkleri")
            if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
                renkler = VARSAYILAN_BASLIK_RENKLERI
            renkler = tuple(
                renk if _arayuz_renk_kodu_gecerli_mi(renk) else varsayilan
                for renk, varsayilan in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)
            )
            sayfalar[sayfa_id] = {
                "etiket": str(ham_ayar.get("etiket", ""))[:100],
                "baslik_metni": str(ham_ayar.get("baslik_metni", ""))[:160],
                "grup": grup if grup in SAYFA_GRUPLARI else "",
                "sira": _arayuz_sayisini_sinirla(
                    ham_ayar.get("sira", 0), 0, 0, 999
                ),
                "gorunur": bool(ham_ayar.get("gorunur", True)),
                "baslik_renkleri": list(renkler),
                "baslik_puntosu": _arayuz_sayisini_sinirla(
                    ham_ayar.get("baslik_puntosu", 30), 30, 16, 56
                ),
            }

    ozel_sayfalar = []
    ham_ozel_sayfalar = veri.get("ozel_sayfalar", [])
    if isinstance(ham_ozel_sayfalar, list):
        kullanilan_idler = set()
        for ham_sayfa in ham_ozel_sayfalar[:50]:
            if not isinstance(ham_sayfa, dict):
                continue
            sayfa_id = ham_sayfa.get("id")
            if (
                not isinstance(sayfa_id, str)
                or not sayfa_id.startswith("ozel-")
                or not sayfa_id[5:].isalnum()
                or sayfa_id in kullanilan_idler
            ):
                continue
            baslik = str(ham_sayfa.get("baslik", "")).strip()[:100]
            if not baslik:
                continue
            bloklar = []
            ham_bloklar = ham_sayfa.get("bloklar", [])
            if isinstance(ham_bloklar, list):
                for blok in ham_bloklar[:100]:
                    if not isinstance(blok, dict):
                        continue
                    tur = blok.get("tur")
                    metin = blok.get("metin")
                    if tur not in ("baslik", "metin") or not isinstance(metin, str):
                        continue
                    bloklar.append({"tur": tur, "metin": metin[:4000]})
            grup = ham_sayfa.get("grup")
            ozel_sayfalar.append(
                {
                    "id": sayfa_id,
                    "baslik": baslik,
                    "grup": grup if grup in SAYFA_GRUPLARI[:-1] else SAYFA_GRUPLARI[0],
                    "sira": _arayuz_sayisini_sinirla(
                        ham_sayfa.get("sira", 0), 0, 0, 999
                    ),
                    "gorunur": bool(ham_sayfa.get("gorunur", True)),
                    "bloklar": bloklar,
                }
            )
            kullanilan_idler.add(sayfa_id)

    return {"sayfalar": sayfalar, "ozel_sayfalar": ozel_sayfalar}


def arayuz_sayfa_ayarlarini_yukle(supabase_veri_oku):
    ham_veri = supabase_veri_oku(ARAYUZ_SAYFA_AYARLARI_ID, {}, kritik=False)
    return arayuz_sayfa_ayarlarini_duzenle(ham_veri)


def arayuz_sayfa_ayarlarini_kaydet(veri, supabase_veri_kaydet):
    temiz_veri = arayuz_sayfa_ayarlarini_duzenle(veri)
    supabase_veri_kaydet(ARAYUZ_SAYFA_AYARLARI_ID, temiz_veri)
    return temiz_veri


def arayuz_sayfa_ayari_al(ayarlar, sayfa_id):
    sayfalar = ayarlar.get("sayfalar", {}) if isinstance(ayarlar, dict) else {}
    ayar = sayfalar.get(sayfa_id, {}) if isinstance(sayfalar, dict) else {}
    renkler = ayar.get("baslik_renkleri", VARSAYILAN_BASLIK_RENKLERI)
    if not isinstance(renkler, (list, tuple)) or len(renkler) != 4:
        renkler = VARSAYILAN_BASLIK_RENKLERI
    temiz_renkler = [
        renk if _arayuz_renk_kodu_gecerli_mi(renk) else varsayilan
        for renk, varsayilan in zip(renkler, VARSAYILAN_BASLIK_RENKLERI)
    ]
    return {
        "etiket": str(ayar.get("etiket", "")),
        "baslik_metni": str(ayar.get("baslik_metni", "")),
        "grup": ayar.get("grup", ""),
        "sira": _arayuz_sayisini_sinirla(ayar.get("sira", 0), 0, 0, 999),
        "gorunur": bool(ayar.get("gorunur", True)),
        "baslik_renkleri": temiz_renkler,
        "baslik_puntosu": _arayuz_sayisini_sinirla(
            ayar.get("baslik_puntosu", 30), 30, 16, 56
        ),
    }


def sayfa_baslik_metnini_al(ayarlar, sayfa_id):
    sayfalar = ayarlar.get("sayfalar", {}) if isinstance(ayarlar, dict) else {}
    sayfa = sayfalar.get(sayfa_id, {}) if isinstance(sayfalar, dict) else {}
    duzenlenmis = str(sayfa.get("baslik_metni", "")).strip()
    return duzenlenmis or SAYFA_VARSAYILAN_BASLIKLARI.get(sayfa_id, sayfa_id)


def admin_sayfa_duzenleyici(
    st,
    gecerli_menuler,
    menu_gorunen_etiketler,
    menu_varsayilan_gruplari,
    menu_varsayilan_siralari,
    supabase_url,
    supabase_key,
    supabase_veri_kaydet,
):
    st.markdown("### 🧩 Kod Yazmadan Sayfa Düzenleyici")
    st.caption(
        "Mevcut iş akışlarının kodunu değiştirmeden sayfa menülerini ve başlık görünümünü "
        "yönetin; özel metin sayfaları oluşturun. Yerleşik sayfalar silinmez, menüden gizlenir. "
        "Python kodu veya HTML çalıştırılamaz."
    )
    arayuz = json.loads(
        json.dumps(st.session_state.arayuz_sayfa_ayarlari, ensure_ascii=False)
    )
    ozel_sayfalar = arayuz["ozel_sayfalar"]
    yerlesik_sayfalar = [
        sayfa_id for sayfa_id in gecerli_menuler
        if not sayfa_id.startswith("ozel-")
    ]
    sayfa_secenekleri = yerlesik_sayfalar + [
        sayfa["id"] for sayfa in ozel_sayfalar
    ]
    gorunen_etiketler = dict(menu_gorunen_etiketler)
    gorunen_etiketler.update(
        {sayfa["id"]: sayfa["baslik"] for sayfa in ozel_sayfalar}
    )
    secici_surumu = hashlib.sha256(
        "|".join(sayfa_secenekleri).encode("utf-8")
    ).hexdigest()[:10]
    secilen_sayfa_id = st.selectbox(
        "Düzenlenecek sayfa",
        sayfa_secenekleri,
        format_func=lambda sayfa_id: gorunen_etiketler.get(sayfa_id, sayfa_id),
        key=f"arayuz_sayfa_sec_{secici_surumu}",
    )
    sayfa_ayari = arayuz_sayfa_ayari_al(arayuz, secilen_sayfa_id)
    ozel_sayfa = next(
        (sayfa for sayfa in ozel_sayfalar if sayfa["id"] == secilen_sayfa_id),
        None,
    )
    varsayilan_grup = (
        sayfa_ayari["grup"]
        or (
            ozel_sayfa["grup"]
            if ozel_sayfa
            else menu_varsayilan_gruplari.get(secilen_sayfa_id, SAYFA_GRUPLARI[0])
        )
    )
    if varsayilan_grup not in SAYFA_GRUPLARI:
        varsayilan_grup = SAYFA_GRUPLARI[0]
    grup_secenekleri = SAYFA_GRUPLARI[:-1] if ozel_sayfa else SAYFA_GRUPLARI
    sayfa_basligi = (
        ozel_sayfa["baslik"] if ozel_sayfa
        else sayfa_baslik_metnini_al(arayuz, secilen_sayfa_id)
    )
    varsayilan_sira = sayfa_ayari["sira"]
    if secilen_sayfa_id not in arayuz["sayfalar"]:
        varsayilan_sira = menu_varsayilan_siralari.get(secilen_sayfa_id, 0)

    with st.form(f"arayuz_sayfa_duzenle_{secilen_sayfa_id}"):
        yeni_menu_etiketi = st.text_input(
            "Menüde görünen sayfa adı",
            value=sayfa_ayari["etiket"] or gorunen_etiketler.get(
                secilen_sayfa_id, secilen_sayfa_id
            ),
            max_chars=100,
        )
        yeni_baslik = sayfa_basligi
        if ozel_sayfa:
            yeni_baslik = st.text_input(
                "Özel sayfanın ana başlığı",
                value=ozel_sayfa["baslik"],
                max_chars=100,
            )
        else:
            yeni_baslik = st.text_input(
                "Sayfa içerik başlığı",
                value=sayfa_basligi,
                max_chars=160,
            )
        grup_secimi = st.selectbox(
            "Menü grubu",
            grup_secenekleri,
            index=(
                grup_secenekleri.index(varsayilan_grup)
                if varsayilan_grup in grup_secenekleri else 0
            ),
        )
        yeni_sira = st.number_input(
            "Menü sırası (küçük sayı üstte)",
            min_value=0,
            max_value=999,
            value=varsayilan_sira,
            step=1,
        )
        gorunur = st.checkbox(
            "Menüde göster",
            value=sayfa_ayari["gorunur"],
            disabled=secilen_sayfa_id == "Kullanıcı Ayarları",
        )
        yeni_punto = st.slider(
            "Başlık punto boyutu",
            min_value=16,
            max_value=56,
            value=sayfa_ayari["baslik_puntosu"],
            step=1,
        )
        renk_sutunlari = st.columns(4)
        yeni_renkler = []
        renk_adlari = ("Başlangıç rengi", "Yeşil", "Gri", "Mavi")
        for indeks, sutun in enumerate(renk_sutunlari):
            with sutun:
                yeni_renkler.append(
                    st.color_picker(
                        renk_adlari[indeks],
                        value=sayfa_ayari["baslik_renkleri"][indeks],
                    )
                )

        duzenlenmis_bloklar = None
        if ozel_sayfa:
            st.markdown("**Sayfa satırları**")
            st.caption("Satır eklemek için tablo altındaki + düğmesini, silmek için satır seçimini kullanın.")
            blok_tablosu = pd.DataFrame(
                ozel_sayfa["bloklar"], columns=["tur", "metin"]
            )
            duzenlenmis_bloklar = st.data_editor(
                blok_tablosu,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "tur": st.column_config.SelectboxColumn(
                        "Satır türü", options=["baslik", "metin"], required=True
                    ),
                    "metin": st.column_config.TextColumn(
                        "İçerik", width="large", max_chars=4000
                    ),
                },
                key=f"ozel_sayfa_satirlari_{secilen_sayfa_id}",
            )
        kaydet = st.form_submit_button("Sayfa ayarlarını kaydet", type="primary")

    if kaydet:
        if not supabase_url or not supabase_key:
            st.error("Sayfa ayarlarını kalıcı kaydetmek için Supabase bağlantısı gereklidir.")
        else:
            arayuz["sayfalar"][secilen_sayfa_id] = {
                "etiket": yeni_menu_etiketi.strip(),
                "baslik_metni": yeni_baslik.strip(),
                "grup": grup_secimi,
                "sira": int(yeni_sira),
                "gorunur": gorunur,
                "baslik_renkleri": yeni_renkler,
                "baslik_puntosu": yeni_punto,
            }
            if ozel_sayfa:
                ozel_sayfa["baslik"] = yeni_baslik.strip() or "Yeni Sayfa"
                ozel_sayfa["grup"] = grup_secimi
                ozel_sayfa["sira"] = int(yeni_sira)
                ozel_sayfa["gorunur"] = gorunur
                ozel_sayfa["bloklar"] = duzenlenmis_bloklar.to_dict("records")
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                arayuz, supabase_veri_kaydet
            )
            st.success("Sayfa ayarları kaydedildi.")
            st.rerun()

    st.markdown("---")
    with st.form("ozel_sayfa_olustur"):
        st.markdown("**Yeni metin sayfası oluştur**")
        yeni_sayfa_adi = st.text_input(
            "Sayfa adı", max_chars=100, key="yeni_ozel_sayfa_adi"
        )
        yeni_sayfa_grubu = st.selectbox(
            "Sayfa grubu",
            SAYFA_GRUPLARI[:-1],
            key="yeni_ozel_sayfa_grubu",
        )
        olustur = st.form_submit_button("Özel sayfa ekle")
    if olustur:
        if not supabase_url or not supabase_key:
            st.error("Özel sayfa oluşturmak için kalıcı Supabase bağlantısı gereklidir.")
        elif not yeni_sayfa_adi.strip():
            st.error("Özel sayfa için bir ad girin.")
        else:
            yeni_id = f"ozel-{secrets.token_hex(8)}"
            arayuz["ozel_sayfalar"].append(
                {
                    "id": yeni_id,
                    "baslik": yeni_sayfa_adi.strip(),
                    "grup": yeni_sayfa_grubu,
                    "sira": 999,
                    "gorunur": True,
                    "bloklar": [],
                }
            )
            arayuz["sayfalar"][yeni_id] = {
                "etiket": yeni_sayfa_adi.strip(),
                "grup": yeni_sayfa_grubu,
                "sira": 999,
                "gorunur": True,
                "baslik_renkleri": list(VARSAYILAN_BASLIK_RENKLERI),
                "baslik_puntosu": 30,
            }
            st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                arayuz, supabase_veri_kaydet
            )
            st.success("Özel sayfa oluşturuldu.")
            st.rerun()

    if arayuz["ozel_sayfalar"]:
        with st.form("ozel_sayfa_sil"):
            st.markdown("**Özel sayfa sil**")
            silinecek_id = st.selectbox(
                "Silinecek özel sayfa",
                [sayfa["id"] for sayfa in arayuz["ozel_sayfalar"]],
                format_func=lambda sayfa_id: next(
                    sayfa["baslik"]
                    for sayfa in arayuz["ozel_sayfalar"]
                    if sayfa["id"] == sayfa_id
                ),
            )
            silme_onayi = st.checkbox(
                "Bu özel sayfanın kalıcı olarak silinmesini onaylıyorum."
            )
            sil = st.form_submit_button("Özel sayfayı sil")
        if sil:
            if not silme_onayi:
                st.error("Silmek için önce onay kutusunu işaretleyin.")
            elif not supabase_url or not supabase_key:
                st.error("Sayfa silmek için kalıcı Supabase bağlantısı gereklidir.")
            else:
                arayuz["ozel_sayfalar"] = [
                    sayfa for sayfa in arayuz["ozel_sayfalar"]
                    if sayfa["id"] != silinecek_id
                ]
                arayuz["sayfalar"].pop(silinecek_id, None)
                st.session_state.arayuz_sayfa_ayarlari = arayuz_sayfa_ayarlarini_kaydet(
                    arayuz, supabase_veri_kaydet
                )
                st.success("Özel sayfa silindi.")
                st.rerun()
