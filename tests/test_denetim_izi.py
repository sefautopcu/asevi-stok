from unittest.mock import MagicMock

from src.denetim_izi_sql import (
    denetim_izi_sql_kaydet,
    denetim_izi_sql_oku,
    denetim_kaydini_satira_donustur,
    satir_denetim_kaydina_donustur,
)
from src.denetim_izi_ui import (
    SAYFA_ETIKETI_DENETIM_IZI,
    _sayfa_maskeli_mi,
    denetim_kayitlarini_filtrele,
    hedef_koleksiyon_bul,
)
from src.veri_yonetimi import denetim_kaydi_ekle


def test_denetim_kaydi_satir_donusumleri():
    kayit = {
        "zaman": "2026-11-27 14:00:00",
        "kullanici": "sefa",
        "rol": "Admin",
        "modul": "rota_teslimat",
        "islem": "Güncelleme",
        "kayit_id": "RTS-01",
        "onceki_veri": {"teslim_durumu": "Bekliyor"},
        "sonraki_veri": {"teslim_durumu": "Teslim Edildi"},
    }
    satir = denetim_kaydini_satira_donustur(kayit, sira=2)
    assert satir["id"] == "DNT-SQL-2"
    assert satir["kullanici"] == "sefa"
    assert "Bekliyor" in satir["onceki_veri"]
    assert "Teslim Edildi" in satir["sonraki_veri"]

    geri = satir_denetim_kaydina_donustur(satir)
    assert geri["id"] == "DNT-SQL-2"
    assert geri["kayit_id"] == "RTS-01"


def test_denetim_izi_sql_oku_ve_kaydet():
    mock_session = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [
        {
            "id": "DNT-ESKI",
            "zaman": "2026-11-26 10:00:00",
            "kullanici": "admin",
            "modul": "haftalik_menu",
            "islem": "Ekleme",
        },
        {
            "id": "DNT-00001",
            "zaman": "2026-11-27 14:00:00",
            "kullanici": "admin",
            "modul": "rota_teslimat",
            "islem": "Güncelleme",
        },
    ]
    mock_session.get.return_value = get_resp

    durum, liste = denetim_izi_sql_oku(
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
            "id": "DNT-00001",
            "zaman": "2026-11-27 14:00:00",
            "kullanici": "admin",
            "modul": "rota_teslimat",
            "islem": "Güncelleme",
        }
    ]
    mock_session.post.return_value = post_resp

    ok, guncel = denetim_izi_sql_kaydet(
        [
            {
                "id": "DNT-00001",
                "zaman": "2026-11-27 14:00:00",
                "kullanici": "admin",
                "modul": "rota_teslimat",
                "islem": "Güncelleme",
            }
        ],
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert ok is True
    assert len(guncel) == 1
    assert guncel[0]["id"] == "DNT-00001"
    mock_session.delete.assert_called_once()


def test_denetim_kaydi_ekle_filtrele_ve_koleksiyon():
    ilk = denetim_kaydi_ekle(
        [],
        modul="haftalik_menu",
        islem="Ekleme",
        kullanici="admin",
        rol="Admin",
        kayit_id="HMN-01",
        sonraki_veri={"yemek_adi": "Mercimek Çorbası"},
    )
    ikinci = denetim_kaydi_ekle(
        ilk,
        modul="rota_teslimat",
        islem="Güncelleme",
        kullanici="personel1",
        rol="Personel",
        kayit_id="RTS-02",
        onceki_veri={"id": "RTS-02", "teslim_durumu": "Bekliyor"},
        sonraki_veri={"id": "RTS-02", "teslim_durumu": "Teslim Edildi"},
    )
    assert len(ikinci) == 2
    assert ikinci[0]["id"] != ikinci[1]["id"]
    assert ikinci[0]["kayit_id"] == "RTS-02"

    filtreli = denetim_kayitlarini_filtrele(ikinci, kullanici="personel1", modul="rota_teslimat")
    assert len(filtreli) == 1
    assert filtreli[0]["kayit_id"] == "RTS-02"

    arama_sonucu = denetim_kayitlarini_filtrele(ikinci, arama="Mercimek")
    assert len(arama_sonucu) == 1

    assert hedef_koleksiyon_bul("rota_teslimat") == "rota_teslimat"
    assert hedef_koleksiyon_bul("haftalik_menu") == "haftalik_menu"
    assert hedef_koleksiyon_bul("bilinmeyen_modul") is None


def test_denetim_izi_sayfa_maskeleme():
    assert _sayfa_maskeli_mi(["denetim_izi"]) is True
    assert _sayfa_maskeli_mi([SAYFA_ETIKETI_DENETIM_IZI]) is True
    assert _sayfa_maskeli_mi(["Güncel Stok Durumu"]) is False
