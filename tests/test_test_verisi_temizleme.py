import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


class _SessionState(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def _temizleme_fonksiyonlarini_yukle(state):
    app_path = Path(__file__).resolve().parents[1] / "src" / "app_runtime.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    hedefler = {
        "test_verisi_kayit_uygun_mu",
        "test_verisi_kayit_etiketi_olustur",
        "test_verisi_sayfa_koleksiyonlari",
        "test_verilerini_temizle",
    }
    fonksiyonlar = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in hedefler
    ]
    module = ast.fix_missing_locations(
        ast.Module(body=fonksiyonlar, type_ignores=[])
    )
    namespace = {
        "st": SimpleNamespace(session_state=state),
        "verileri_kaydet": Mock(),
        "silinen_urun_loglarini_kaydet": Mock(),
        "loglari_kaydet": Mock(),
        "depoları_kaydet": Mock(),
        "supabase_veri_kaydet": Mock(),
        "demirbasları_kaydet": Mock(),
        "yemek_uretim_arsivini_kaydet": Mock(),
        "ihtiyac_sahiplerini_kaydet": Mock(),
        "dagitim_loglarini_kaydet": Mock(),
        "personelleri_kaydet": Mock(),
        "personel_izinlerini_kaydet": Mock(),
    }
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace


def test_stok_temizligi_sadece_secilen_partiyi_siler():
    state = _SessionState(
        girisler=[
            {"id": "FAT-1", "urun": "DENEME ÜRÜNÜ"},
            {"id": "FAT-2", "urun": "PİRİNÇ"},
        ],
        kullanim_loglari=[{"urun": "PİRİNÇ", "tur": "Fire/Zayiat"}],
    )
    namespace = _temizleme_fonksiyonlarini_yukle(state)

    silinen = namespace["test_verilerini_temizle"](
        "Güncel Stok Durumu",
        {"stok": ["0"]},
    )

    assert silinen == 1
    assert state["girisler"] == [{"id": "FAT-2", "urun": "PİRİNÇ"}]
    assert len(state["kullanim_loglari"]) == 1
    namespace["verileri_kaydet"].assert_called_once_with(state["girisler"])
    namespace["loglari_kaydet"].assert_not_called()


def test_fire_sayfasi_diger_kullanim_loglarini_korur():
    state = _SessionState(
        kullanim_loglari=[
            {"urun": "PİRİNÇ", "tur": "Günlük Kullanım (Pilav)"},
            {"urun": "TEST YAĞ", "tur": "Fire/Zayiat"},
        ],
        girisler=[],
    )
    namespace = _temizleme_fonksiyonlarini_yukle(state)

    silinen = namespace["test_verilerini_temizle"](
        "Fire / Zayiat Girişi",
        {"fire": ["0", "1"]},
    )

    assert silinen == 1
    assert state["kullanim_loglari"] == [
        {"urun": "PİRİNÇ", "tur": "Günlük Kullanım (Pilav)"}
    ]
    namespace["loglari_kaydet"].assert_called_once_with(state["kullanim_loglari"])


def test_depo_temizligi_kullanilan_depo_ve_kategoriyi_korur():
    state = _SessionState(
        depolar=["Merkez Depo", "Deneme Depo"],
        kategoriler=["KURU GIDA", "DENEME KATEGORİ"],
        girisler=[{"depo": "Merkez Depo", "kategori": "Kuru Gıda"}],
    )
    namespace = _temizleme_fonksiyonlarini_yukle(state)

    silinen = namespace["test_verilerini_temizle"](
        "Depo Yönetimi",
        {"depolar": ["0", "1"], "kategoriler": ["0", "1"]},
    )

    assert silinen == 2
    assert state["depolar"] == ["Merkez Depo"]
    assert state["kategoriler"] == ["KURU GIDA"]
    namespace["depoları_kaydet"].assert_called_once_with(["Merkez Depo"])
    namespace["supabase_veri_kaydet"].assert_called_once_with(
        "kategoriler_listesi", ["KURU GIDA"]
    )


def test_gecersiz_sayfa_icin_temizlik_yapilmaz():
    namespace = _temizleme_fonksiyonlarini_yukle(_SessionState())

    with pytest.raises(ValueError, match="geçersiz sayfa"):
        namespace["test_verilerini_temizle"]("Bütün Sistem", {})


def test_temizleme_araci_istenen_dokuz_sayfayi_sunar():
    namespace = _temizleme_fonksiyonlarini_yukle(_SessionState())

    assert set(namespace["test_verisi_sayfa_koleksiyonlari"]()) == {
        "Güncel Stok Durumu",
        "Yeni Mal Alımı / Fatura Ekle",
        "Ürün Sil / Düzenle",
        "Fire / Zayiat Girişi",
        "Depo Yönetimi",
        "Demirbaş Yönetimi",
        "Tedarikçi ve Firma Rehberi",
        "Günlük Yemek Üretimi & Maliyet Raporu",
        "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
        "Personel & Çalışma Süresi Takibi",
    }


def test_personel_kayit_etiketi_hassas_tc_ve_telefonu_gostermez():
    namespace = _temizleme_fonksiyonlarini_yukle(_SessionState())

    etiket = namespace["test_verisi_kayit_etiketi_olustur"](
        "personeller",
        {
            "id": "PER-1",
            "ad_soyad": "DENEME PERSONEL",
            "gorev": "Aşçı",
            "tc": "11111111111",
            "telefon": "5550000000",
        },
        0,
    )

    assert "DENEME PERSONEL" in etiket
    assert "11111111111" not in etiket
    assert "5550000000" not in etiket
