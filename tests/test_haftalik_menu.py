from unittest.mock import MagicMock

from src.haftalik_menu_sql import (
    haftalik_menu_sql_kaydet,
    haftalik_menu_sql_oku,
    menu_kaydini_satira_donustur,
    satir_menu_kaydina_donustur,
)
from src.haftalik_menu_ui import (
    SAYFA_ETIKETI_HAFTALIK_MENU,
    _sayfa_maskeli_mi,
    hafta_baslangici_str,
    recete_malzeme_ihtiyaci_hesapla,
)


def test_hafta_baslangici_ve_satir_donusumleri():
    # 2026-11-27 Cuma -> Haftanın Pazartesi'si 2026-11-23
    assert hafta_baslangici_str("2026-11-27") == "2026-11-23"

    kayit = {
        "tarih": "2026-11-25",
        "gun_adi": "Çarşamba",
        "ogun_turu": "Ana Öğün",
        "recete_id": "RCT-01",
        "yemek_adi": "Mercimek Çorbası",
        "tahmini_porsiyon": "300",
        "durum": "Planlandı",
        "notlar": "Sıcak servis",
    }
    satir = menu_kaydini_satira_donustur(kayit, sira=4)
    assert satir["id"] == "HMN-SQL-4"
    assert satir["hafta_baslangic"] == "2026-11-23"
    assert satir["tahmini_porsiyon"] == 300

    geri = satir_menu_kaydina_donustur(satir)
    assert geri["id"] == "HMN-SQL-4"
    assert geri["yemek_adi"] == "Mercimek Çorbası"
    assert geri["tahmini_porsiyon"] == 300


def test_haftalik_menu_sql_oku_ve_kaydet():
    mock_session = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [
        {
            "id": "HMN-ESKI",
            "hafta_baslangic": "2026-11-23",
            "gun_adi": "Pazartesi",
            "tarih": "2026-11-23",
            "yemek_adi": "Eski Menü",
            "tahmini_porsiyon": 100,
        },
        {
            "id": "HMN-1",
            "hafta_baslangic": "2026-11-23",
            "gun_adi": "Salı",
            "tarih": "2026-11-24",
            "yemek_adi": "Tarhana Çorbası",
            "tahmini_porsiyon": 200,
        },
    ]
    mock_session.get.return_value = get_resp

    durum, liste = haftalik_menu_sql_oku(
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
            "id": "HMN-1",
            "hafta_baslangic": "2026-11-23",
            "gun_adi": "Salı",
            "tarih": "2026-11-24",
            "yemek_adi": "Tarhana Çorbası",
            "tahmini_porsiyon": 200,
        }
    ]
    mock_session.post.return_value = post_resp

    ok, guncel = haftalik_menu_sql_kaydet(
        [
            {
                "id": "HMN-1",
                "hafta_baslangic": "2026-11-23",
                "gun_adi": "Salı",
                "tarih": "2026-11-24",
                "yemek_adi": "Tarhana Çorbası",
                "tahmini_porsiyon": 200,
            }
        ],
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert ok is True
    assert len(guncel) == 1
    assert guncel[0]["id"] == "HMN-1"
    mock_session.delete.assert_called_once()


def test_recete_malzeme_ihtiyaci_ve_eksik_stok_hesabi():
    menu_kayitlari = [
        {
            "id": "HMN-1",
            "recete_id": "RCT-CORBA",
            "yemek_adi": "Mercimek Çorbası",
            "tahmini_porsiyon": 200,  # 100 porsiyonluk reçetenin 2 katı
        }
    ]
    receteler = [
        {
            "id": "RCT-CORBA",
            "yemek_adi": "Mercimek Çorbası",
            "porsiyon_sayisi": 100,
            "malzemeler": [
                {"urun": "Kırmızı Mercimek", "miktar": 10.0, "birim": "kg"},
                {"urun": "Ayçiçek Yağı", "miktar": 4.0, "birim": "lt"},
            ],
        }
    ]
    girisler = [
        {"urun": "Kırmızı Mercimek", "kalan": 12.0, "birim": "kg"},  # 20 lazım + 5 kritik = 25 -> 13 eksik
        {"urun": "Ayçiçek Yağı", "kalan": 20.0, "birim": "lt"},       # 8 lazım + 0 kritik -> yeterli
    ]
    kritik_seviyeler = {"Kırmızı Mercimek": 5.0}

    analiz = recete_malzeme_ihtiyaci_hesapla(
        menu_kayitlari, receteler, girisler, kritik_seviyeler
    )
    assert analiz["eslesen_menu_sayisi"] == 1
    assert analiz["eksik_cesit_sayisi"] == 1
    assert analiz["eksik_satirlari"][0]["Malzeme"] == "Kırmızı Mercimek"
    assert analiz["eksik_satirlari"][0]["Haftalık İhtiyaç"] == 20.0
    assert analiz["eksik_satirlari"][0]["Eksik / Alınacak"] == 13.0


def test_haftalik_menu_sayfa_maskeleme():
    assert _sayfa_maskeli_mi(["haftalik_menu"]) is True
    assert _sayfa_maskeli_mi([SAYFA_ETIKETI_HAFTALIK_MENU]) is True
    assert _sayfa_maskeli_mi(["Güncel Stok Durumu"]) is False
