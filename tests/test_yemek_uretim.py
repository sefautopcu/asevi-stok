import ast
import math
import statistics
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def yemek_helpers():
    app_path = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    names = {
        "yemek_sepeti_stok_hatalari",
        "_malzeme_kullanim_anahtari",
        "yemek_menu_alanlari",
        "yemek_menu_ogelerini_temizle",
        "yemek_menu_ogelerini_kayittan_al",
        "yemek_arsiv_menu_kolonlari",
        "yemek_kaydi_menu_ogelerini_guncelle",
        "yemek_malzeme_kullanim_istatistikleri",
        "yemek_malzeme_kullanim_uyarilari",
    }
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    namespace = {"math": math, "statistics": statistics}
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace


def test_uretim_sepeti_toplam_stogu_asarsa_blok_mesaji_uretir(yemek_helpers):
    stok = [{"id": "FAT-1", "urun": "ARPA ŞEHRİYE", "kalan": 20}]
    sepet = [{"urun": "ARPA ŞEHRİYE", "miktar": 30}]

    hatalar = yemek_helpers["yemek_sepeti_stok_hatalari"](stok, sepet)

    assert len(hatalar) == 1
    assert "30" in hatalar[0]
    assert "20" in hatalar[0]


def test_uretim_sepeti_ayni_urun_eklemelerini_toplayarak_stogu_kontrol_eder(yemek_helpers):
    stok = [{"id": "FAT-1", "urun": "UN", "kalan": 20}]
    sepet = [
        {"urun": "UN", "miktar": 12},
        {"urun": "un", "miktar": 9},
    ]

    hata = yemek_helpers["yemek_sepeti_stok_hatalari"](stok, sepet)
    assert hata
    assert "toplam istenen miktar (21)" in hata[0]


def test_yeterli_stokta_manuel_ve_qr_sepetine_izin_verir(yemek_helpers):
    stok = [
        {
            "id": "FAT-1",
            "urun": "UN",
            "kalan": 10,
            "paket_miktari": 5,
            "paket_durumlari": {"FAT-1-P1": 3},
        },
        {"id": "FAT-2", "urun": "UN", "kalan": 5},
    ]
    sepet = [
        {"urun": "UN", "miktar": 2, "fatura_id": "FAT-1", "paket_id": "FAT-1-P1"},
        {"urun": "UN", "miktar": 8},
    ]

    assert yemek_helpers["yemek_sepeti_stok_hatalari"](stok, sepet) == []


def test_qr_sepeti_secili_faturadaki_ve_paketteki_stogu_asamaz(yemek_helpers):
    stok = [{
        "id": "FAT-1",
        "urun": "NOHUT",
        "kalan": 10,
        "paket_miktari": 5,
        "paket_durumlari": {"FAT-1-P1": 1.5},
    }]
    sepet = [{
        "urun": "NOHUT",
        "miktar": 2,
        "fatura_id": "FAT-1",
        "paket_id": "FAT-1-P1",
    }]

    hatalar = yemek_helpers["yemek_sepeti_stok_hatalari"](stok, sepet)

    assert hatalar
    assert "paket kaydında" in hatalar[0]


def test_gecmis_ayni_yemek_kayitlarindan_kisi_basi_ortalama_ve_aralik_hesaplar(yemek_helpers):
    arsiv = [
        {
            "yemek_adi": "Ispanak Yemeği",
            "tarih": "2026-11-15",
            "kisi_sayisi": 100,
            "malzemeler": [
                {"urun": "Ispanak", "miktar": 20},
                {"urun": "Tereyağı", "miktar": 1},
            ],
        },
        {
            "yemek_adi": "ıSPANAK YEMEĞİ",
            "tarih": "2026-11-16",
            "kisi_sayisi": 200,
            "malzemeler": [
                {"urun": "ISPANAK", "miktar": 40},
                {"urun": "Tereyağı", "miktar": 2},
            ],
        },
        {
            "yemek_adi": "Mercimek Çorbası",
            "tarih": "2026-11-16",
            "kisi_sayisi": 200,
            "malzemeler": [{"urun": "Ispanak", "miktar": 200}],
        },
    ]

    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, "Ispanak Yemeği", 200, "2026-11-17"
    )

    assert stats["ISPANAK"]["ortalama_kisi_basi"] == pytest.approx(0.2)
    assert stats["ISPANAK"]["beklenen_miktar"] == pytest.approx(40)
    assert stats["ISPANAK"]["alt_sinir"] < 40 < stats["ISPANAK"]["ust_sinir"]
    assert stats["TEREYAĞI"]["ortalama_kisi_basi"] == pytest.approx(0.01)


def test_gecmis_kullanimdan_farkli_miktar_uyarir_ancak_stok_kontrolu_ayridir(yemek_helpers):
    arsiv = [{
        "yemek_adi": "Ispanak",
        "tarih": "2026-11-16",
        "kisi_sayisi": 200,
        "malzemeler": [{"urun": "Ispanak", "miktar": 50}],
    }]
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, "Ispanak", 200, "2026-11-17"
    )
    uyarilar = yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats,
        [{"urun": "Ispanak", "miktar": 60}],
        200,
        {"ISPANAK": "Kg"},
    )

    assert len(uyarilar) == 1
    assert "ortalama 0.25" in uyarilar[0]
    assert "beklenen yaklaşık miktar 50" in uyarilar[0]
    assert "kişi başı 0.3 Kg/kişi" in uyarilar[0]
    assert yemek_helpers["yemek_sepeti_stok_hatalari"](
        [{"id": "FAT-1", "urun": "Ispanak", "kalan": 100}],
        [{"urun": "Ispanak", "miktar": 60}],
    ) == []


@pytest.mark.parametrize("bugunku_miktar", [40, 60])
def test_ortalama_disi_kullanim_hem_dusuk_hem_yuksek_miktarda_uyarir(
    yemek_helpers, bugunku_miktar
):
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        [{
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-16",
            "kisi_sayisi": 200,
            "malzemeler": [{"urun": "Ispanak", "miktar": 50}],
        }],
        "Ispanak",
        200,
        "2026-11-17",
    )

    assert yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats,
        [{"urun": "Ispanak", "miktar": bugunku_miktar}],
        200,
    )


def test_standart_sapma_araligi_farkli_gecmis_kullanimlari_kapsar(yemek_helpers):
    arsiv = [
        {
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-15",
            "kisi_sayisi": 200,
            "malzemeler": [{"urun": "Ispanak", "miktar": 50}],
        },
        {
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-16",
            "kisi_sayisi": 200,
            "malzemeler": [{"urun": "Ispanak", "miktar": 60}],
        },
    ]
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, "Ispanak", 200, "2026-11-17"
    )

    assert yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats, [{"urun": "Ispanak", "miktar": 60}], 200
    ) == []
    assert yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats, [{"urun": "Ispanak", "miktar": 40}], 200
    )


def test_farkli_yemek_icin_gecmis_istatistik_bildirilmez(yemek_helpers):
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        [{
            "yemek_adi": "Mercimek Çorbası",
            "tarih": "2026-11-16",
            "kisi_sayisi": 10,
            "malzemeler": [{"urun": "Mercimek", "miktar": 2}],
        }],
        "Ispanak Yemeği",
        200,
        "2026-11-17",
    )

    assert stats == {}


def test_ayni_gun_onceki_ve_gelecekteki_uretimleri_zamana_gore_ayirir(yemek_helpers):
    arsiv = [
        {
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-16",
            "kisi_sayisi": 100,
            "malzemeler": [{"urun": "Ispanak", "miktar": 20}],
        },
        {
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-17",
            "zaman": "2026-11-17 09:00",
            "kisi_sayisi": 100,
            "malzemeler": [{"urun": "Ispanak", "miktar": 40}],
        },
        {
            "yemek_adi": "Ispanak",
            "tarih": "2026-11-17",
            "zaman": "2026-11-17 11:00",
            "kisi_sayisi": 100,
            "malzemeler": [{"urun": "Ispanak", "miktar": 100}],
        },
    ]

    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, "Ispanak", 200, "2026-11-17", "2026-11-17 10:00"
    )

    assert stats["ISPANAK"]["uretim_sayisi"] == 2
    assert stats["ISPANAK"]["ortalama_kisi_basi"] == pytest.approx(0.3)


def test_yeterli_stogu_asan_guncel_giris_uretim_sepetiyle_birlikte_bloklanir(
    yemek_helpers,
):
    stok = [{"id": "FAT-1", "urun": "ISPANAK", "kalan": 22}]
    sepet = [{"urun": "ISPANAK", "miktar": 1}]
    giris = {"urun": "ISPANAK", "miktar": 25}

    hatalar = yemek_helpers["yemek_sepeti_stok_hatalari"](
        stok, [*sepet, giris]
    )

    assert hatalar
    assert "26" in hatalar[0]
    assert "22" in hatalar[0]


def test_70_kg_giris_onceki_50_kg_uretimine_gore_uyari_uretir(yemek_helpers):
    arsiv = [{
        "yemek_adi": "Ispanak Yemeği",
        "tarih": "2026-11-16",
        "kisi_sayisi": 200,
        "malzemeler": [{"urun": "Ispanak", "miktar": 50}],
    }]
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, "Ispanak Yemeği", 200, "2026-11-17"
    )

    uyarilar = yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats,
        [{"urun": "Ispanak", "miktar": 70}],
        200,
        {"ISPANAK": "Kg"},
    )

    assert len(uyarilar) == 1
    assert "bugün 70 Kg" in uyarilar[0]
    assert "beklenen yaklaşık miktar 50" in uyarilar[0]


def test_arsivdeki_menu_adi_ve_malzeme_bosluk_farki_uyariyi_engellemez(
    yemek_helpers,
):
    arsiv = [{
        "yemek_adi": "Ispanak Yemeği / Makarna / Yoğurt",
        "menu_ogeleri": {
            "ana_yemek": "Ispanak Yemeği",
            "yardimci_yemek": "Makarna",
            "corba": "",
            "tatli_meyve_yogurt": "Yoğurt",
        },
        "tarih": "2026-11-02",
        "kisi_sayisi": 200,
        "malzemeler": [{"urun": "KUŞBAŞI ET", "miktar": 5}],
    }]
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv,
        {"ana_yemek": "Ispanak Yemeği", "yardimci_yemek": "Makarna"},
        200,
        "2026-11-18",
    )

    assert stats["KUŞBAŞIET"]["beklenen_miktar"] == pytest.approx(5)
    uyarilar = yemek_helpers["yemek_malzeme_kullanim_uyarilari"](
        stats,
        [{"urun": "KUŞBAŞIET", "miktar": 15}],
        200,
        {"KUŞBAŞIET": "Kg"},
    )

    assert len(uyarilar) == 1
    assert "bugün 15 Kg" in uyarilar[0]
    assert "beklenen yaklaşık miktar 5" in uyarilar[0]


def test_menu_ortalamasi_yalnizca_ayni_bolumdeki_eslesen_gecmisi_kullanir(
    yemek_helpers,
):
    arsiv = [
        {
            "menu_ogeleri": {
                "ana_yemek": "Ispanak",
                "yardimci_yemek": "Pilav",
            },
            "tarih": "2026-11-01",
            "kisi_sayisi": 100,
            "malzemeler": [{"urun": "ISPANAK", "miktar": 25}],
        },
        {
            "menu_ogeleri": {
                "ana_yemek": "Kuru Fasulye",
                "yardimci_yemek": "Ispanak",
            },
            "tarih": "2026-11-02",
            "kisi_sayisi": 100,
            "malzemeler": [{"urun": "ISPANAK", "miktar": 100}],
        },
    ]

    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        arsiv, {"ana_yemek": "Ispanak"}, 200, "2026-11-18"
    )

    assert stats["ISPANAK"]["beklenen_miktar"] == pytest.approx(50)
    assert stats["ISPANAK"]["uretim_sayisi"] == 1


def test_eski_birlesik_menu_kaydi_duzenlenip_dort_bolume_kaydedilebilir(
    yemek_helpers,
):
    kayit = {
        "yemek_adi": "Ispanak Yemeği / Makarna / Yoğurt",
        "tarih": "2026-11-02",
        "kisi_sayisi": 200,
        "malzemeler": [{"urun": "Kuşbaşı Et", "miktar": 5}],
    }

    assert yemek_helpers["yemek_menu_ogelerini_kayittan_al"](kayit) == {
        "ana_yemek": "",
        "yardimci_yemek": "",
        "corba": "",
        "tatli_meyve_yogurt": "",
    }
    assert yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        [kayit], {"ana_yemek": "Ispanak Yemeği"}, 200, "2026-11-18"
    ) == {}
    assert yemek_helpers["yemek_kaydi_menu_ogelerini_guncelle"](
        kayit,
        {
            "ana_yemek": "Ispanak Yemeği",
            "yardimci_yemek": "Makarna",
            "corba": "",
            "tatli_meyve_yogurt": "Yoğurt",
        },
    )

    assert kayit["yemek_adi"] == "Ispanak Yemeği / Makarna / Yoğurt"
    assert kayit["menu_ogeleri"]["ana_yemek"] == "Ispanak Yemeği"
    assert kayit["malzemeler"] == [{"urun": "Kuşbaşı Et", "miktar": 5}]
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        [kayit], {"ana_yemek": "Ispanak Yemeği"}, 200, "2026-11-18"
    )
    assert stats["KUŞBAŞIET"]["beklenen_miktar"] == pytest.approx(5)


def test_eski_tek_yemek_kaydi_ana_yemek_olarak_eslesir(yemek_helpers):
    stats = yemek_helpers["yemek_malzeme_kullanim_istatistikleri"](
        [{
            "yemek_adi": "Ispanak Yemeği",
            "tarih": "2026-11-02",
            "kisi_sayisi": 200,
            "malzemeler": [{"urun": "Ispanak", "miktar": 50}],
        }],
        {"ana_yemek": "Ispanak Yemeği"},
        200,
        "2026-11-18",
    )

    assert stats["ISPANAK"]["beklenen_miktar"] == pytest.approx(50)


def test_arsiv_tablo_menuyu_dort_ayri_sutunda_gosterir(yemek_helpers):
    kolonlar = yemek_helpers["yemek_arsiv_menu_kolonlari"]({
        "yemek_adi": "Ispanak Yemeği / Makarna / Yoğurt",
        "menu_ogeleri": {
            "ana_yemek": "Ispanak Yemeği",
            "yardimci_yemek": "Makarna",
            "corba": "",
            "tatli_meyve_yogurt": "Yoğurt",
        },
    })

    assert kolonlar == {
        "Ana Yemek": "Ispanak Yemeği",
        "Yardımcı Yemek / Ara Yemek": "Makarna",
        "Çorba": "-",
        "Tatlı / Meyve / Yoğurt": "Yoğurt",
    }


def test_kategorize_edilmemis_eski_menu_arsiv_tabloya_yanlis_dagitilmaz(
    yemek_helpers,
):
    kolonlar = yemek_helpers["yemek_arsiv_menu_kolonlari"]({
        "yemek_adi": "Ispanak Yemeği / Makarna / Yoğurt",
    })

    assert set(kolonlar) == {
        "Ana Yemek",
        "Yardımcı Yemek / Ara Yemek",
        "Çorba",
        "Tatlı / Meyve / Yoğurt",
    }
    assert set(kolonlar.values()) == {"-"}
