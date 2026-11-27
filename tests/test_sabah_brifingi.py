from unittest.mock import MagicMock

from src.sabah_brifingi_sql import (
    sabah_brifingi_sql_kaydet,
    sabah_brifingi_sql_oku,
    sabah_uyarisini_satira_donustur,
    satir_sabah_uyarisina_donustur,
)
from src.sabah_brifingi_ui import (
    SAYFA_ETIKETI_SABAH_BRIFINGI,
    _sayfa_maskeli_mi,
    otomatik_uyarilari_tara,
)
from src.veri_yonetimi import sabah_brifingi_uyarisi_olustur


def test_sabah_uyarisi_satir_donusumleri():
    kayit = {
        "id": "BRF-0001",
        "tarih": "2026-11-27",
        "kategori": "Kritik Stok",
        "onem_seviyesi": "Kritik",
        "baslik": "Pirinç kritik seviyede",
        "detay": "Kalan miktar 5 kg",
        "kaynak_id": "STK-PRN",
        "durum": "Aktif",
        "guncelleyen": "admin",
    }
    satir = sabah_uyarisini_satira_donustur(kayit, sira=1)
    assert satir["id"] == "BRF-0001"
    assert satir["tarih"] == "2026-11-27"
    assert satir["onem_seviyesi"] == "Kritik"

    geri = satir_sabah_uyarisina_donustur(satir)
    assert geri["id"] == "BRF-0001"
    assert geri["baslik"] == "Pirinç kritik seviyede"
    assert geri["guncelleyen"] == "admin"


def test_sabah_brifingi_sql_oku_ve_kaydet():
    mock_session = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [
        {
            "id": "BRF-ESKI",
            "tarih": "2026-11-26",
            "kategori": "Genel",
            "onem_seviyesi": "Orta",
            "baslik": "Eski uyarı",
            "durum": "Okundu",
        },
        {
            "id": "BRF-0001",
            "tarih": "2026-11-27",
            "kategori": "Kritik Stok",
            "onem_seviyesi": "Kritik",
            "baslik": "Kuru fasulye kritik",
            "durum": "Aktif",
        },
    ]
    mock_session.get.return_value = get_resp

    durum, liste = sabah_brifingi_sql_oku(
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
            "id": "BRF-0001",
            "tarih": "2026-11-27",
            "kategori": "Kritik Stok",
            "onem_seviyesi": "Kritik",
            "baslik": "Kuru fasulye kritik",
            "durum": "Aktif",
        }
    ]
    mock_session.post.return_value = post_resp

    ok, guncel = sabah_brifingi_sql_kaydet(
        [
            {
                "id": "BRF-0001",
                "tarih": "2026-11-27",
                "kategori": "Kritik Stok",
                "onem_seviyesi": "Kritik",
                "baslik": "Kuru fasulye kritik",
                "durum": "Aktif",
            }
        ],
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert ok is True
    assert len(guncel) == 1
    assert guncel[0]["id"] == "BRF-0001"
    mock_session.delete.assert_called_once()


def test_sabah_brifingi_uyarisi_olustur_ve_otomatik_tarama():
    ilk = sabah_brifingi_uyarisi_olustur(
        [],
        baslik="Fırın bakımı kontrolü",
        kategori="Menü & Üretim",
        onem_seviyesi="Yüksek",
        kaynak_id="FRN-01",
        tarih="2026-11-27",
    )
    assert len(ilk) == 1

    # Aynı kaynak_id için mükerrer kayıt eklenmemeli
    tekrar = sabah_brifingi_uyarisi_olustur(
        ilk,
        baslik="Fırın bakımı kontrolü",
        kategori="Menü & Üretim",
        onem_seviyesi="Yüksek",
        kaynak_id="FRN-01",
        tarih="2026-11-27",
    )
    assert len(tekrar) == 1

    ornek_state = {
        "girisler": [
            {
                "id": "FAT-01",
                "urun_adi": "Mercimek",
                "kalan_miktar": 4,
                "son_tuketim_tarihi": "2026-11-28",
            }
        ],
        "kritik_seviyeler": {"Mercimek": 10},
        "haftalik_menu": [{"tarih": "2026-11-26", "yemek": "Tavuk Sote"}],
        "rota_teslimat": [{"id": "RTS-01", "teslim_durumu": "Bekliyor"}],
    }
    uyarilar = otomatik_uyarilari_tara(ornek_state, referans_tarih="2026-11-27")
    kategoriler = {u["kategori"] for u in uyarilar}
    assert "Kritik Stok" in kategoriler
    assert "SKT / Tüketim" in kategoriler
    assert "Menü & Üretim" in kategoriler
    assert "Rota & Teslimat" in kategoriler


def test_sabah_brifingi_sayfa_maskeleme():
    assert _sayfa_maskeli_mi(["sabah_brifingi"]) is True
    assert _sayfa_maskeli_mi([SAYFA_ETIKETI_SABAH_BRIFINGI]) is True
    assert _sayfa_maskeli_mi(["Güncel Stok Durumu"]) is False
