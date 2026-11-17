import pytest

from cekirdek import (
    qr_acik_paketleri_bul,
    qr_paket_kalanini_hesapla,
    qr_paket_secim_engeli,
)


def test_acik_paket_baska_faturadaki_ayni_urun_paketini_engeller():
    girisler = [
        {
            "id": "FAT-001",
            "urun": "UN",
            "birim": "Kg",
            "paket_miktari": 5,
            "paket_durumlari": {"FAT-001-P1": 2},
        },
        {
            "id": "FAT-002",
            "urun": "UN",
            "birim": "Kg",
            "paket_miktari": 5,
            "paket_durumlari": {},
        },
    ]

    acik_paketler = qr_acik_paketleri_bul(girisler, [], "un")

    assert acik_paketler == [{
        "paket_id": "FAT-001-P1",
        "fatura_id": "FAT-001",
        "kalan": 2,
        "birim": "Kg",
    }]


def test_sepet_acik_paketi_hesaba_katar_ve_biten_paketi_engel_saymaz():
    giris = {
        "id": "FAT-001",
        "urun": "UN",
        "paket_miktari": 5,
        "paket_durumlari": {},
    }
    sepet = [{
        "urun": "UN",
        "fatura_id": "FAT-001",
        "paket_id": "FAT-001-P1",
        "miktar": 3,
    }]

    assert qr_paket_kalanini_hesapla(giris, sepet, "FAT-001-P1") == 2
    assert qr_acik_paketleri_bul([giris], sepet, "UN")[0]["paket_id"] == "FAT-001-P1"

    sepet.append({
        "urun": "UN",
        "fatura_id": "FAT-001",
        "paket_id": "FAT-001-P1",
        "miktar": 2,
    })
    assert qr_paket_kalanini_hesapla(giris, sepet, "FAT-001-P1") == 0
    assert qr_acik_paketleri_bul([giris], sepet, "UN") == []


def test_acik_paket_miktar_bilgisi_bozuksa_hata_verir():
    with pytest.raises(ValueError, match="geçersiz"):
        qr_paket_kalanini_hesapla(
            {"id": "FAT-001", "paket_miktari": "bozuk"},
            [],
            "FAT-001-P1",
        )


def test_acik_paket_bitmeden_farkli_paket_secimi_engellenir():
    girisler = [{
        "id": "FAT-001",
        "urun": "UN",
        "paket_miktari": 5,
        "paket_durumlari": {"FAT-001-P1": 2},
    }]

    engel = qr_paket_secim_engeli(girisler, [], "UN", "FAT-001-P2")

    assert engel["paket_id"] == "FAT-001-P1"


def test_acik_paket_secilebilir_ve_sepet_dahilinde_bitince_engel_kalkar():
    girisler = [{
        "id": "FAT-001",
        "urun": "UN",
        "paket_miktari": 5,
        "paket_durumlari": {"FAT-001-P1": 2},
    }]
    assert qr_paket_secim_engeli(
        girisler, [], "UN", "FAT-001-P1"
    ) is None

    sepet = [{
        "fatura_id": "FAT-001",
        "paket_id": "FAT-001-P1",
        "miktar": 2,
    }]
    assert qr_paket_secim_engeli(
        girisler, sepet, "UN", "FAT-001-P2"
    ) is None
