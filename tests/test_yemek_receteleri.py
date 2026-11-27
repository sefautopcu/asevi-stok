import ast
from pathlib import Path
import pytest

from src.veri_yonetimi import (
    veri_recete_kalori_maliyet_hesapla,
    veri_yemek_receteleri_getir,
    veri_yemek_recetesi_kaydet,
)
from src.yemek_receteleri_sql import (
    hesapla_kalori_ve_maliyet,
    yemek_receteleri_sql_kaydet,
    yemek_receteleri_sql_oku,
)
from src.yemek_receteleri_ui import (
    SAYFA_BASLIGI_YEMEK_RECETELERI,
    yemek_receteleri_sayfasi,
)


def _app_runtime_recete_fonksiyonlarini_yukle():
    """
    src/app_runtime.py dosyasındaki üst düzey Streamlit arayüz kodunu
    çalıştırmadan yalnızca Faz 1 sabit ve fonksiyon tanımlarını izole yükler.
    """
    kaynak_yol = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    kaynak_kod = kaynak_yol.read_text(encoding="utf-8")
    agac = ast.parse(kaynak_kod, filename=str(kaynak_yol))

    hedef_isimler = {
        "SAYFA_ANAHTARI_YEMEK_RECETELERI",
        "MENU_GRUBU_URETIM_MUTFAK",
        "maskeli_sayfalari_recete_icin_hazirla",
        "uretim_mutfak_menulerini_hazirla",
        "yemek_receteleri_sayfasini_ac",
    }

    secili_dugumler = []
    for dugum in agac.body:
        if isinstance(dugum, ast.FunctionDef) and dugum.name in hedef_isimler:
            secili_dugumler.append(dugum)
        elif isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name) and hedef.id in hedef_isimler:
                    secili_dugumler.append(dugum)

    izole_modul = ast.Module(body=secili_dugumler, type_ignores=[])
    ast.fix_missing_locations(izole_modul)

    ad_alani = {
        "SAYFA_BASLIGI_YEMEK_RECETELERI": SAYFA_BASLIGI_YEMEK_RECETELERI,
        "yemek_receteleri_sayfasi": yemek_receteleri_sayfasi,
    }
    exec(compile(izole_modul, str(kaynak_yol), "exec"), ad_alani)
    return ad_alani


_runtime_ns = _app_runtime_recete_fonksiyonlarini_yukle()
SAYFA_ANAHTARI_YEMEK_RECETELERI = _runtime_ns["SAYFA_ANAHTARI_YEMEK_RECETELERI"]
uretim_mutfak_menulerini_hazirla = _runtime_ns["uretim_mutfak_menulerini_hazirla"]
yemek_receteleri_sayfasini_ac = _runtime_ns["yemek_receteleri_sayfasini_ac"]


def test_recete_kaydet_guncelle_ve_oku_bellek_depo():
    depo = []
    ilk_kayit = yemek_receteleri_sql_kaydet(
        recete={
            "recete_kodu": "REC-001",
            "yemek_adi": "Mercimek Çorbası",
            "kategori": "Çorba",
            "porsiyon_sayisi": 100.0,
            "kalemler": [
                {
                    "urun_adi": "Kırmızı Mercimek",
                    "birim": "kg",
                    "miktar": 8.0,
                    "kalori": 3500.0,
                    "kaynak": "STOK",
                    "birim_fiyat": 45.0,
                }
            ],
        },
        bellek_depo=depo,
    )

    assert ilk_kayit["recete_kodu"] == "REC-001"
    assert ilk_kayit["toplam_kalori"] == pytest.approx(28000.0)
    assert ilk_kayit["porsiyon_basi_kalori"] == pytest.approx(280.0)
    assert ilk_kayit["toplam_maliyet"] == pytest.approx(360.0)
    assert ilk_kayit["porsiyon_basi_maliyet"] == pytest.approx(3.6)

    yemek_receteleri_sql_kaydet(
        recete={
            "recete_kodu": "REC-001",
            "yemek_adi": "Süzme Mercimek Çorbası",
            "kategori": "Çorba",
            "porsiyon_sayisi": 100.0,
            "kalemler": [
                {
                    "urun_adi": "Kırmızı Mercimek",
                    "birim": "kg",
                    "miktar": 10.0,
                    "kalori": 3500.0,
                    "kaynak": "STOK",
                    "birim_fiyat": 45.0,
                }
            ],
        },
        bellek_depo=depo,
    )

    okunan = yemek_receteleri_sql_oku(bellek_depo=depo)
    assert len(okunan) == 1
    assert okunan[0]["yemek_adi"] == "Süzme Mercimek Çorbası"
    assert okunan[0]["toplam_maliyet"] == pytest.approx(450.0)


def test_bagis_ve_sifir_fiyat_kurali_korunur():
    sonuc = hesapla_kalori_ve_maliyet(
        kalemler=[
            {
                "urun_adi": "Bağış Pirinç",
                "birim": "kg",
                "miktar": 15.0,
                "kalori": 3600.0,
                "kaynak": "BAĞIŞ",
                "birim_fiyat": 70.0,
            },
            {
                "urun_adi": "Sıfır Fiyatlı Tuz",
                "birim": "kg",
                "miktar": 1.0,
                "kalori": 0.0,
                "kaynak": "STOK",
                "birim_fiyat": 0.0,
            },
            {
                "urun_adi": "Tereyağı",
                "birim": "kg",
                "miktar": 2.0,
                "kalori": 7170.0,
                "kaynak": "SATIN_ALMA",
                "birim_fiyat": 300.0,
            },
        ],
        porsiyon_sayisi=100.0,
    )

    assert sonuc["toplam_maliyet"] == pytest.approx(600.0)
    assert sonuc["porsiyon_basi_maliyet"] == pytest.approx(6.0)
    assert sonuc["toplam_kalori"] == pytest.approx(54000.0 + 14340.0)


def test_veri_yonetimi_ve_son_fiyat_saglayici():
    depo = []
    fiyatlar = {"Nohut": 60.0, "Salça": 80.0}

    veri_yemek_recetesi_kaydet(
        recete={
            "recete_kodu": "REC-002",
            "yemek_adi": "Etli Nohut",
            "kategori": "Ana Yemek",
            "porsiyon_sayisi": 100.0,
            "kalemler": [
                {
                    "urun_adi": "Nohut",
                    "birim": "kg",
                    "miktar": 12.0,
                    "kalori": 3640.0,
                    "kaynak": "STOK",
                },
                {
                    "urun_adi": "Salça",
                    "birim": "kg",
                    "miktar": 2.0,
                    "kalori": 820.0,
                    "kaynak": "STOK",
                },
            ],
        },
        bellek_depo=depo,
        son_fiyat_saglayici=lambda urun: fiyatlar.get(urun, 0.0),
    )

    kayitlar = veri_yemek_receteleri_getir(bellek_depo=depo, filtre_aktif=True)
    assert len(kayitlar) == 1
    assert kayitlar[0]["toplam_maliyet"] == pytest.approx(12.0 * 60.0 + 2.0 * 80.0)

    hesap = veri_recete_kalori_maliyet_hesapla(
        kalemler=[{"urun_adi": "Nohut", "miktar": 5.0, "kalori": 3640.0, "kaynak": "STOK"}],
        porsiyon_sayisi=50.0,
        son_fiyat_saglayici=lambda urun: fiyatlar.get(urun, 0.0),
    )
    assert hesap["toplam_maliyet"] == pytest.approx(300.0)


def test_uretim_mutfak_menusu_ve_sayfa_maskeleme():
    alt_menuler = uretim_mutfak_menulerini_hazirla(
        mevcut_alt_sayfalar=[
            "Günlük Yemek Üretimi & Maliyet Raporu",
            "Kalori Hesaplama Aracı",
        ],
        maskeli_sayfalar=[],
    )
    assert "Hazır Yemek Reçeteleri" in alt_menuler

    maskeli_menuler = uretim_mutfak_menulerini_hazirla(
        mevcut_alt_sayfalar=[
            "Günlük Yemek Üretimi & Maliyet Raporu",
            "Kalori Hesaplama Aracı",
        ],
        maskeli_sayfalar=[SAYFA_ANAHTARI_YEMEK_RECETELERI],
    )
    assert "Hazır Yemek Reçeteleri" not in maskeli_menuler

    assert (
        yemek_receteleri_sayfasini_ac(
            SAYFA_ANAHTARI_YEMEK_RECETELERI,
            maskeli_sayfalar=[SAYFA_ANAHTARI_YEMEK_RECETELERI],
        )
        is False
    )


def test_bos_recete_kodu_veya_yemek_adi_hata_verir():
    with pytest.raises(ValueError):
        yemek_receteleri_sql_kaydet(
            recete={"recete_kodu": "", "yemek_adi": "Test Yemek"},
            bellek_depo=[],
        )
    with pytest.raises(ValueError):
        yemek_receteleri_sql_kaydet(
            recete={"recete_kodu": "REC-999", "yemek_adi": ""},
            bellek_depo=[],
        )
def test_bom_fire_sifir_maliyet_olcekleme_revizyon_ve_alerjen():
    from src.yemek_receteleri_sql import (
        alerjenleri_otomatik_tespit_et,
        recete_kalemlerini_olcekle,
    )

    depo = []
    kayit_v1 = veri_yemek_recetesi_kaydet(
        recete={
            "recete_kodu": "REC-BOM-01",
            "yemek_adi": "Yayla Çorbası",
            "kategori": "Çorba",
            "porsiyon_sayisi": 100.0,
            "durum": "Onaylandı / Aktif",
            "kalemler": [
                {
                    "urun_adi": "Soğan",
                    "birim": "kg",
                    "miktar": 10.0,
                    "fire_orani": 20.0,
                    "kalori": 400.0,
                    "kaynak": "STOK",
                    "birim_fiyat": 15.0,
                },
                {
                    "urun_adi": "Yoğurt",
                    "birim": "kg",
                    "miktar": 5.0,
                    "fire_orani": 0.0,
                    "kalori": 600.0,
                    "kaynak": "STOK",
                    "birim_fiyat": 40.0,
                },
                {
                    "urun_adi": "Buğday Unu",
                    "birim": "kg",
                    "miktar": 2.0,
                    "fire_orani": 0.0,
                    "kalori": 3640.0,
                    "kaynak": "STOK",
                    "birim_fiyat": 20.0,
                },
                {
                    "urun_adi": "Su",
                    "birim": "lt",
                    "miktar": 30.0,
                    "fire_orani": 0.0,
                    "kalori": 0.0,
                    "kaynak": "SIFIR MALİYET",
                    "birim_fiyat": 99.0,
                },
            ],
        },
        bellek_depo=depo,
    )

    # Maliyet brüt miktar üzerinden (10*15 + 5*40 + 2*20 + 0 = 390 TL)
    assert kayit_v1["toplam_maliyet"] == pytest.approx(390.0)
    # Kalori fire sonrası net miktar üzerinden (8*400 + 5*600 + 2*3640 = 13480 kcal)
    assert kayit_v1["toplam_kalori"] == pytest.approx(13480.0)
    assert kayit_v1["revizyon_no"] == 1
    assert "Gluten" in kayit_v1["alerjenler"]
    assert "Laktoz / Süt" in kayit_v1["alerjenler"]

    # Porsiyon ölçekleme 100 -> 200 (miktarlar 2 katına çıkmalı)
    olcekli = recete_kalemlerini_olcekle(kayit_v1["kalemler"], 100.0, 200.0)
    assert olcekli[0]["miktar"] == pytest.approx(20.0)

    # Aynı reçete koduyla tekrar kaydedildiğinde Revizyon 2 olmalı
    kayit_v2 = veri_yemek_recetesi_kaydet(
        recete={
            "recete_kodu": "REC-BOM-01",
            "yemek_adi": "Yayla Çorbası",
            "porsiyon_sayisi": 200.0,
            "kalemler": olcekli,
        },
        bellek_depo=depo,
    )
    assert kayit_v2["revizyon_no"] == 2
    assert len(kayit_v2["revizyon_gecmisi"]) == 1
    assert "Gluten" in alerjenleri_otomatik_tespit_et(olcekli)
