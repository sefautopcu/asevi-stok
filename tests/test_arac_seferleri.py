import datetime
from unittest.mock import MagicMock

from src.arac_sefer_ui import (
    SAYFA_ETIKETI_ARAC_SEFER,
    _belge_durum_rozeti,
    _sayfa_maskeli_mi,
    _tarih_kalan_gun,
    aylik_sefer_analizi_hesapla,
)
from src.arac_seferleri_sql import (
    arac_seferleri_sql_kaydet,
    arac_seferleri_sql_oku,
    satir_sefer_kaydina_donustur,
    sefer_kaydini_satira_donustur,
)


def test_sefer_kaydini_satira_donustur_varsayilanlar_ve_durum():
    acik_kayit = {
        "tarih": "2026-11-27",
        "arac_plaka": "25 abc 123",
        "sofor_adi": "Mehmet Kaya",
        "dagitim_personeli": "Ali Demir",
        "guzergah_mahalle": "Dadaşkent",
        "cikis_saati": "11:30",
        "sefertas_porsiyon_sayisi": "60",
        "baslangic_km": "14250,5",
    }
    satir = sefer_kaydini_satira_donustur(acik_kayit, sira=7)

    assert satir["id"] == "SFR-SQL-7"
    assert satir["arac_plaka"] == "25 ABC 123"
    assert satir["sefertas_porsiyon_sayisi"] == 60
    assert satir["baslangic_km"] == 14250.5
    assert satir["bitis_km"] == 0.0
    assert satir["durum"] == "Devam Ediyor"

    kapali_kayit = dict(acik_kayit)
    kapali_kayit["id"] = "SFR-001"
    kapali_kayit["donus_saati"] = "13:45"
    kapali_kayit["bitis_km"] = 14282.0
    kapali_kayit["teslim_edilen_porsiyon"] = 58

    kapali_satir = sefer_kaydini_satira_donustur(kapali_kayit)
    assert kapali_satir["id"] == "SFR-001"
    assert kapali_satir["durum"] == "Tamamlandı"
    assert kapali_satir["teslim_edilen_porsiyon"] == 58


def test_satir_sefer_kaydina_donustur_yapilan_km_hesabi():
    satir = {
        "id": "SFR-002",
        "tarih": "2026-11-27",
        "arac_plaka": "25 AEV 01",
        "baslangic_km": 1000.0,
        "bitis_km": 1034.6,
        "sefertas_porsiyon_sayisi": 45,
        "teslim_edilen_porsiyon": 45,
        "durum": "Tamamlandı",
    }
    kayit = satir_sefer_kaydina_donustur(satir)

    assert kayit["yapilan_km"] == 34.6
    assert kayit["durum"] == "Tamamlandı"

    # Açık seferde bitis_km 0 iken negatif km üretmemeli
    acik_satir = {
        "id": "SFR-003",
        "baslangic_km": 1034.6,
        "bitis_km": 0,
    }
    acik_kayit = satir_sefer_kaydina_donustur(acik_satir)
    assert acik_kayit["yapilan_km"] == 0.0


def test_arac_seferleri_sql_oku_basarili_ve_hatali():
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "id": "SFR-10",
            "tarih": "2026-11-27",
            "arac_plaka": "25 XYZ 99",
            "baslangic_km": 500,
            "bitis_km": 525,
            "sefertas_porsiyon_sayisi": 40,
            "teslim_edilen_porsiyon": 40,
        }
    ]
    mock_session.get.return_value = mock_resp

    durum, sonuc = arac_seferleri_sql_oku(
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert durum == "ok"
    assert len(sonuc) == 1
    assert sonuc[0]["id"] == "SFR-10"
    assert sonuc[0]["yapilan_km"] == 25.0

    # HTTP hata durumu
    mock_resp.status_code = 500
    durum_hata, mesaj = arac_seferleri_sql_oku(
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )
    assert durum_hata == "hata"
    assert "HTTP 500" in mesaj


def test_arac_seferleri_sql_kaydet_senkronizasyon():
    mock_session = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = [{"id": "SFR-ESKI"}, {"id": "SFR-1"}]
    mock_session.get.return_value = get_resp

    del_resp = MagicMock()
    del_resp.status_code = 204
    mock_session.delete.return_value = del_resp

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = [
        {
            "id": "SFR-1",
            "tarih": "2026-11-27",
            "arac_plaka": "25 AZ 001",
            "baslangic_km": 100,
            "bitis_km": 120,
            "sefertas_porsiyon_sayisi": 30,
            "teslim_edilen_porsiyon": 30,
            "durum": "Tamamlandı",
        }
    ]
    mock_session.post.return_value = post_resp

    ok, kayitlar = arac_seferleri_sql_kaydet(
        [
            {
                "id": "SFR-1",
                "tarih": "2026-11-27",
                "arac_plaka": "25 az 001",
                "baslangic_km": 100,
                "bitis_km": 120,
                "sefertas_porsiyon_sayisi": 30,
                "teslim_edilen_porsiyon": 30,
            }
        ],
        "https://example.supabase.co",
        lambda extra=None: {"apikey": "test"},
        lambda: mock_session,
    )

    assert ok is True
    assert len(kayitlar) == 1
    assert kayitlar[0]["yapilan_km"] == 20.0
    # Artık aktif listede olmayan SFR-ESKI veritabanından silinmiş olmalı
    mock_session.delete.assert_called_once()


def test_aylik_sefer_analizi_hesapla():
    ornek_seferler = [
        {
            "id": "SFR-1",
            "tarih": "2026-11-05",
            "arac_plaka": "25 AA 111",
            "guzergah_mahalle": "Dadaşkent",
            "sefertas_porsiyon_sayisi": 50,
            "teslim_edilen_porsiyon": 48,
            "baslangic_km": 1000,
            "bitis_km": 1020,
        },
        {
            "id": "SFR-2",
            "tarih": "2026-11-18",
            "arac_plaka": "25 AA 111",
            "guzergah_mahalle": "Ilıca",
            "sefertas_porsiyon_sayisi": 40,
            "teslim_edilen_porsiyon": 40,
            "baslangic_km": 1020,
            "bitis_km": 1055,
        },
        {
            "id": "SFR-3",
            "tarih": "2026-10-29",
            "arac_plaka": "25 BB 222",
            "guzergah_mahalle": "Dadaşkent",
            "sefertas_porsiyon_sayisi": 60,
            "teslim_edilen_porsiyon": 60,
            "baslangic_km": 500,
            "bitis_km": 515,
        },
    ]

    analiz = aylik_sefer_analizi_hesapla(ornek_seferler, "2026-11")
    assert analiz["toplam_sefer"] == 2
    assert analiz["toplam_porsiyon"] == 88
    assert analiz["toplam_km"] == 55.0

    assert len(analiz["arac_listesi"]) == 1
    assert analiz["arac_listesi"][0]["Araç Plakası"] == "25 AA 111"
    assert analiz["arac_listesi"][0]["Toplam Sefer"] == 2

    assert len(analiz["mahalle_listesi"]) == 2
    assert analiz["mahalle_listesi"][0]["Güzergâh / Mahalle"] == "Dadaşkent"
    assert analiz["mahalle_listesi"][0]["Dağıtılan Kap / Porsiyon"] == 48


def test_sigorta_muayene_uyari_ve_sayfa_maskeleme():
    bugun = datetime.date.today()
    gecmis_tarih = str(bugun - datetime.timedelta(days=3))
    yakin_tarih = str(bugun + datetime.timedelta(days=10))
    uzak_tarih = str(bugun + datetime.timedelta(days=120))

    assert _tarih_kalan_gun(gecmis_tarih) == -3
    assert "Süresi Doldu" in _belge_durum_rozeti("Sigorta", gecmis_tarih)
    assert "10 gün kaldı" in _belge_durum_rozeti("Muayene", yakin_tarih)
    assert "✅ Sigorta" in _belge_durum_rozeti("Sigorta", uzak_tarih)

    assert _sayfa_maskeli_mi(["arac_seferleri"]) is True
    assert _sayfa_maskeli_mi([SAYFA_ETIKETI_ARAC_SEFER]) is True
    assert _sayfa_maskeli_mi(["Güncel Stok Durumu"]) is False
