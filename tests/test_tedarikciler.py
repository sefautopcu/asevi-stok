# tests/test_tedarikciler.py
from src.tedarikciler_sql import (
    tedarikci_alim_istatistikleri,
    tedarikci_dogrula,
    tedarikciler_sql_kaydet,
    tedarikciler_sql_oku,
    yeni_tedarikci_id_uret,
)
from src.tedarikciler_ui import _sayfa_maskeli_mi


def test_yeni_tedarikci_id_uret():
    assert yeni_tedarikci_id_uret([]) == "TED-001"
    mevcut = [{"id": "TED-001"}, {"id": "TED-004"}]
    assert yeni_tedarikci_id_uret(mevcut) == "TED-005"


def test_tedarikci_dogrula_ve_mukerrer_kontrolu():
    mevcut = [{"id": "TED-001", "firma_adi": "İkbal Gıda Ltd."}]

    ok, mesaj = tedarikci_dogrula("A", mevcut_listesi=mevcut)
    assert not ok
    assert "en az 2 karakter" in mesaj

    ok_dup, mesaj_dup = tedarikci_dogrula("ikbal gıda ltd.", mevcut_listesi=mevcut)
    assert not ok_dup
    assert "zaten kayıtlı" in mesaj_dup

    ok_edit, _ = tedarikci_dogrula(
        "İkbal Gıda Ltd.",
        telefon="05321112233",
        vergi_no="1234567890",
        mevcut_listesi=mevcut,
        haric_id="TED-001",
    )
    assert ok_edit


def test_tedarikci_alim_istatistikleri():
    girisler = [
        {
            "id": "FAT-001",
            "fatura_no": "F-100",
            "tedarikci": "Anadolu Et",
            "urun": "KUŞBAŞI ET",
            "miktar": 50,
            "birim": "Kg",
            "fiyat": 570,
            "tarih": "2026-11-10",
        },
        {
            "id": "FAT-002",
            "fatura_no": "F-101",
            "tedarikci": "anadolu et",
            "urun": "KUŞBAŞI ET",
            "miktar": 20,
            "birim": "Kg",
            "fiyat": 580,
            "tarih": "2026-11-20",
        },
    ]
    ozet = tedarikci_alim_istatistikleri("ANADOLU ET", girisler)
    assert ozet["fatura_sayisi"] == 2
    assert ozet["toplam_tutar"] == 50 * 570 + 20 * 580
    assert ozet["urun_ozeti"][0]["son_birim_fiyat"] == 580


def test_tedarikciler_sql_oku_ve_kaydet():
    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class FakeSession:
        def __init__(self):
            self.deleted_params = []
            self.posted_json = None

        def get(self, url, headers=None, params=None, timeout=10):
            if params and params.get("select") == "id":
                return FakeResponse(200, [{"id": "TED-001"}, {"id": "TED-002"}])
            return FakeResponse(200, [{"id": "TED-001", "firma_adi": "Test A.Ş.", "aktif": True}])

        def delete(self, url, headers=None, params=None, timeout=10):
            self.deleted_params.append(params)
            return FakeResponse(200, [])

        def post(self, url, headers=None, json=None, timeout=10):
            self.posted_json = json
            return FakeResponse(201, json)

    fake_session = FakeSession()
    durum, veriler = tedarikciler_sql_oku("https://example.supabase.co", lambda e=None: {}, lambda: fake_session)
    assert durum == "ok"
    assert len(veriler) == 1

    ok, _ = tedarikciler_sql_kaydet(
        [{"id": "TED-001", "firma_adi": "Test A.Ş.", "aktif": True}],
        "https://example.supabase.co",
        lambda e=None: {},
        lambda: fake_session,
    )
    assert ok
    assert fake_session.deleted_params == [{"id": "eq.TED-002"}]
    assert fake_session.posted_json[0]["id"] == "TED-001"


def test_sayfa_maskeleme_kontrolu():
    assert not _sayfa_maskeli_mi([])
    assert not _sayfa_maskeli_mi(["Güncel Stok Durumu"])
    assert _sayfa_maskeli_mi(["Tedarikçi ve Firma Rehberi"])
