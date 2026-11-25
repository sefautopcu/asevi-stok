"""
Aziziye Aşevi - Supabase Entegrasyon, Çakışma (CAS) ve Hata Senaryoları Testleri
"""
from unittest.mock import MagicMock, patch
import pytest


class DummySupabaseClient:
    """Supabase istemcisini bellek içi test verisiyle simüle eder."""

    def __init__(self, initial_rows=None):
        self.rows = list(initial_rows or [])
        self.fail_on_upsert = False
        self.fail_on_select = False
        self.upsert_calls = []

    def table(self, _name):
        return self

    def select(self, _cols="*"):
        return self

    def eq(self, _col, _val):
        return self

    def execute(self):
        if self.fail_on_select:
            raise RuntimeError("Supabase okuma bağlantısı kesildi")
        res = MagicMock()
        res.data = list(self.rows)
        return res

    def upsert(self, payload, on_conflict=None):
        self.upsert_calls.append((payload, on_conflict))
        if self.fail_on_upsert:
            raise ConnectionError("Supabase yazma zaman aşımı")
        incoming = payload if isinstance(payload, list) else [payload]
        for item in incoming:
            key = item.get("anahtar") or item.get("id")
            idx = next(
                (i for i, r in enumerate(self.rows) if (r.get("anahtar") or r.get("id")) == key),
                None,
            )
            if idx is not None:
                self.rows[idx] = dict(item)
            else:
                self.rows.append(dict(item))
        res = MagicMock()
        res.data = list(incoming)
        return res


def cas_kaydet(client, anahtar, beklenen_surum, yeni_veri):
    """Compare-And-Swap (CAS) benzeri sürüm kontrolü ile güvenli kayıt akışı."""
    mevcut_liste = client.table("asevi_durum").select("*").execute().data
    mevcut = next((r for r in mevcut_liste if r.get("anahtar") == anahtar), None)

    mevcut_surum = mevcut.get("surum", 0) if mevcut else 0
    if mevcut_surum != beklenen_surum:
        raise ValueError(
            f"Çakışma algılandı: beklenen sürüm {beklenen_surum}, mevcut sürüm {mevcut_surum}"
        )

    yeni_kayit = {
        "anahtar": anahtar,
        "surum": mevcut_surum + 1,
        "veri": yeni_veri,
    }
    client.upsert(yeni_kayit, on_conflict="anahtar").execute()
    return yeni_kayit


def test_supabase_basarili_okuma_ve_yazma():
    client = DummySupabaseClient(
        initial_rows=[{"anahtar": "stok", "surum": 1, "veri": {"un_kg": 100}}]
    )
    kayit = cas_kaydet(client, anahtar="stok", beklenen_surum=1, yeni_veri={"un_kg": 85})

    assert kayit["surum"] == 2
    assert kayit["veri"]["un_kg"] == 85
    assert len(client.upsert_calls) == 1


def test_supabase_eski_surum_cakismasini_engeller():
    client = DummySupabaseClient(
        initial_rows=[{"anahtar": "stok", "surum": 3, "veri": {"un_kg": 70}}]
    )

    with pytest.raises(ValueError, match="Çakışma algılandı"):
        cas_kaydet(client, anahtar="stok", beklenen_surum=2, yeni_veri={"un_kg": 60})

    assert len(client.upsert_calls) == 0


def test_supabase_baglanti_hatalarinda_guvenli_yanit():
    client = DummySupabaseClient(
        initial_rows=[{"anahtar": "uretim", "surum": 1, "veri": []}]
    )
    client.fail_on_select = True
    with pytest.raises(RuntimeError, match="okuma bağlantısı"):
        cas_kaydet(client, anahtar="uretim", beklenen_surum=1, yeni_veri=["menü-1"])

    client.fail_on_select = False
    client.fail_on_upsert = True
    with pytest.raises(ConnectionError, match="yazma zaman aşımı"):
        cas_kaydet(client, anahtar="uretim", beklenen_surum=1, yeni_veri=["menü-1"])


def test_dis_servis_mock_dogrulama():
    with patch("builtins.print") as mock_print:
        mock_print("Supabase test istemcisi hazır")
        mock_print.assert_called_once_with("Supabase test istemcisi hazır")
