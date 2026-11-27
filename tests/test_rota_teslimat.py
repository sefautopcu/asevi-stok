from unittest.mock import MagicMock

from src.rota_teslimat_sql import (
    rota_teslimat_kaydini_satira_donustur,
    rota_teslimat_sql_kaydet,
    rota_teslimat_sql_oku,
    satir_rota_teslimat_kaydina_donustur,
)
from src.rota_teslimat_ui import (
    SAYFA_ETIKETI_ROTA_TESLIMAT,
    _sayfa_maskeli_mi,
    mahalle_rota_ozeti_hesapla,
)


def test_rota_teslimat_satir_donusumleri():
    kayit = {
        "tarih": "2026-11-27",
        "mahalle": "Dadaşkent",
        "sefer_id": "SFR-01",
        "arac_plaka": "25 abc 123",
        "hane_id": "HNE-12",
        "hane_adi": "Ayşe Yılmaz",
        "adres": "14. Sokak No: 5",
        "hane_nufusu": "4",
        "planlanan_porsiyon": "4",
        "teslim_edilen_porsiyon": "4",
        "teslim_durumu": "Teslim Edildi",
        "notlar": "Zemin kat",
    }
    satir = rota_teslimat_kaydini_satira_donustur(kayit, sira=3)
    assert satir["id"] == "RTS-SQL-3"
    assert satir["arac_plaka"] == "25 ABC 123"
    assert satir["hane_nufusu"] == 4
    assert satir["planlanan_porsiyon"] == 4
    assert satir["teslim_durumu"] == "Teslim Edildi"

    geri = satir_rota_teslimat_kaydina_donustur(satir)
    assert geri["id"] == "RTS-SQL-3"
    assert geri["hane_adi"] == "Ayşe Yılmaz"
    assert geri["teslim_edilen_porsiyon"] == 4


def test_rota_teslimat_sql_oku_ve_kaydet():
    mock_session = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [
        {
            "id": "RTS-ESKI",
            "tarih": "2026-11-26",
            "mahalle": "Ilıca",
            "hane_adi": "Eski Hane",
            "hane_nufusu": 2,
            "planlanan_porsiyon": 2,
        },
        {
            "id": "RTS-1",
            "tarih": "2026-11-27",
            "mahalle": "Dadaşkent",
            "hane_adi": "Mehmet Öz",
            "hane_nufusu": 3,
            "planlanan_porsiyon": 3,
            "teslim_edilen_porsiyon": 3,
            "teslim_durumu": "Teslim Edildi",
        },
    ]
    mock_session.get.return_value = get_resp

    durum, liste = rota_teslimat_sql_oku(
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert durum == "ok"
    assert len(liste) == 2

    del_resp = MagicMock()
    del_resp.status_code = 204
    mock_session.delete.return_value = del_resp

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = [
        {
            "id": "RTS-1",
            "tarih": "2026-11-27",
            "mahalle": "Dadaşkent",
            "hane_adi": "Mehmet Öz",
            "hane_nufusu": 3,
            "planlanan_porsiyon": 3,
            "teslim_edilen_porsiyon": 3,
            "teslim_durumu": "Teslim Edildi",
        }
    ]
    mock_session.post.return_value = post_resp

    ok, guncel = rota_teslimat_sql_kaydet(
        [
            {
                "id": "RTS-1",
                "tarih": "2026-11-27",
                "mahalle": "Dadaşkent",
                "hane_adi": "Mehmet Öz",
                "hane_nufusu": 3,
                "planlanan_porsiyon": 3,
                "teslim_edilen_porsiyon": 3,
                "teslim_durumu": "Teslim Edildi",
            }
        ],
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert ok is True
    assert len(guncel) == 1
    assert guncel[0]["id"] == "RTS-1"
    mock_session.delete.assert_called_once()


def test_mahalle_rota_ozeti_hesapla():
    kayitlar = [
        {
            "id": "RTS-1",
            "tarih": "2026-11-27",
            "mahalle": "Dadaşkent",
            "hane_adi": "Hane 1",
            "planlanan_porsiyon": 4,
            "teslim_edilen_porsiyon": 4,
            "teslim_durumu": "Teslim Edildi",
        },
        {
            "id": "RTS-2",
            "tarih": "2026-11-27",
            "mahalle": "Dadaşkent",
            "hane_adi": "Hane 2",
            "planlanan_porsiyon": 3,
            "teslim_edilen_porsiyon": 0,
            "teslim_durumu": "Evde Yok",
        },
        {
            "id": "RTS-3",
            "tarih": "2026-11-26",
            "mahalle": "Ilıca",
            "hane_adi": "Hane 3",
            "planlanan_porsiyon": 5,
            "teslim_edilen_porsiyon": 5,
            "teslim_durumu": "Teslim Edildi",
        },
    ]

    ozet = mahalle_rota_ozeti_hesapla(kayitlar, "2026-11-27")
    assert ozet["toplam_hane"] == 2
    assert ozet["toplam_planlanan"] == 7
    assert ozet["toplam_teslim"] == 4
    assert ozet["teslim_edilen_hane"] == 1
    assert len(ozet["mahalle_listesi"]) == 1
    assert ozet["mahalle_listesi"][0]["Mahalle / Güzergâh"] == "Dadaşkent"
    assert ozet["mahalle_listesi"][0]["Bekleyen / Sorunlu"] == 1


def test_rota_teslimat_sayfa_maskeleme():
    assert _sayfa_maskeli_mi(["rota_teslimat"]) is True
    assert _sayfa_maskeli_mi([SAYFA_ETIKETI_ROTA_TESLIMAT]) is True
    assert _sayfa_maskeli_mi(["Güncel Stok Durumu"]) is False
