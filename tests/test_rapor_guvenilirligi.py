import ast
import datetime
import html
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.cekirdek import rapor_mail_durumunu_guncelle, rapor_verilerini_oku


_RAPOR_ANAHTARLARI = (
    "girisler",
    "kullanim_loglari",
    "silinen_urun_loglari",
    "yemek_uretim_arsivi",
    "personel_izinleri",
)


def _sonuclardan_oku(sonuclar):
    return rapor_verilerini_oku(lambda anahtar: sonuclar[anahtar])


def test_fire_secimi_urunle_birlikte_fatura_ve_kalan_miktari_gosterir(fire_helpers):
    etiket = fire_helpers["fire_partisi_etiketi"]({
        "id": "FAT-002",
        "urun": "mercimek",
        "fatura_no": "FAT-2026-002",
        "kalan": 4,
        "birim": "Kg",
        "tarih": "2026-11-17",
    })

    assert "MERCIMEK" in etiket
    assert "FAT-2026-002" in etiket
    assert "Kalan: 4 Kg" in etiket


def test_fire_detayi_secilen_fatura_partisinin_fiyatini_ve_kimligini_kullanir(fire_helpers):
    ikinci_fatura = {
        "id": "FAT-002",
        "urun": "MERCİMEK",
        "fatura_no": "FAT-2026-002",
        "miktar": 5,
        "kalan": 2,
        "birim_fiyat": 7,
        "fiyat": 35,
    }

    detay = fire_helpers["fire_partisi_detayi"](ikinci_fatura, 1.5)

    assert detay == {
        "giris_id": "FAT-002",
        "fatura_no": "FAT-2026-002",
        "miktar": 1.5,
        "birim_fiyat": 7,
        "tutar": 10.5,
    }
    assert ikinci_fatura["kalan"] == 2


def test_fire_miktari_secilen_fatura_stogunu_asamaz(fire_helpers):
    with pytest.raises(ValueError, match="seçilen fatura"):
        fire_helpers["fire_partisi_detayi"](
            {"id": "FAT-001", "fatura_no": "FAT-1", "miktar": 5, "kalan": 1},
            1.1,
        )


def test_fire_detayi_eski_kayitta_toplam_fiyattan_birim_fiyat_hesaplar(fire_helpers):
    detay = fire_helpers["fire_partisi_detayi"](
        {
            "id": "FAT-OLD",
            "fatura_no": "ESKİ-FATURA",
            "miktar": 4,
            "kalan": 3,
            "fiyat": 12,
        },
        2,
    )

    assert detay["birim_fiyat"] == 3
    assert detay["tutar"] == 6


def test_rapor_okumalari_yok_durumunu_bos_liste_kabul_eder():
    sonuclar = {
        anahtar: ("yok", None)
        for anahtar in _RAPOR_ANAHTARLARI
    }

    assert _sonuclardan_oku(sonuclar) == {
        anahtar: []
        for anahtar in _RAPOR_ANAHTARLARI
    }


def test_rapor_okuma_hatasi_bos_rapor_olarak_gizlenmez():
    sonuclar = {
        anahtar: ("ok", [])
        for anahtar in _RAPOR_ANAHTARLARI
    }
    sonuclar["girisler"] = ("hata", "HTTP 503")

    with pytest.raises(RuntimeError, match="girisler.*HTTP 503"):
        _sonuclardan_oku(sonuclar)


def test_rapor_listesi_olmayan_veriyi_reddeder():
    sonuclar = {
        anahtar: ("ok", [])
        for anahtar in _RAPOR_ANAHTARLARI
    }
    sonuclar["girisler"] = ("ok", {"beklenmeyen": "dict"})

    with pytest.raises(ValueError, match="liste biçiminde değil"):
        _sonuclardan_oku(sonuclar)


def test_rapor_kayitlari_nesne_biciminde_degilse_reddeder():
    sonuclar = {
        anahtar: ("ok", [])
        for anahtar in _RAPOR_ANAHTARLARI
    }
    sonuclar["girisler"] = ("ok", ["hatalı-kayıt"])

    with pytest.raises(ValueError, match="kayıtları nesne biçiminde değil"):
        _sonuclardan_oku(sonuclar)


def test_rapor_sahiplenme_gonderim_sirasinda_ve_basari_sonrasinda_tekildir():
    durum, sahiplenildi = rapor_mail_durumunu_guncelle(
        {}, "gunluk", "2026-11-16", 100, "sahiplen", "claim-a"
    )
    assert sahiplenildi is True

    durum, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 101, "sahiplen", "claim-b"
    )
    assert sahiplenildi is False

    durum, tamamlandi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 102, "tamamlandi", "claim-a"
    )
    assert tamamlandi is True

    _, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 103, "sahiplen", "claim-c"
    )
    assert sahiplenildi is False


def test_basarisiz_rapor_bekleme_suresi_dolunca_yeniden_denenebilir():
    durum, _ = rapor_mail_durumunu_guncelle(
        {}, "gunluk", "2026-11-16", 100, "sahiplen", "claim-a"
    )
    durum, basarisiz = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 110, "basarisiz", "claim-a"
    )
    assert basarisiz is True

    durum, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 1009, "sahiplen", "claim-b"
    )
    assert sahiplenildi is False

    _, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 1010, "sahiplen", "claim-b"
    )
    assert sahiplenildi is True


def test_suresi_dolan_gonderim_kilidi_kesilen_islemi_kurtarir():
    durum, _ = rapor_mail_durumunu_guncelle(
        {}, "gunluk", "2026-11-16", 100, "sahiplen", "claim-a"
    )

    _, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", "2026-11-16", 700, "sahiplen", "claim-b"
    )
    assert sahiplenildi is True


def test_eski_basari_kayitlari_tekrar_mail_gondermez():
    _, sahiplenildi = rapor_mail_durumunu_guncelle(
        {"gunluk": "2026-11-16"}, "gunluk", "2026-11-16",
        100, "sahiplen", "claim-a"
    )

    assert sahiplenildi is False


@pytest.mark.parametrize(
    "rapor_durumu",
    [
        {"durum": "gonderiliyor", "kilit_sonu": "0"},
        {"durum": "basarisiz", "yeniden_deneme": "0"},
    ],
)
def test_bozuk_zaman_durumlari_yeni_gonderim_kilidi_acmaz(rapor_durumu):
    donem = "2026-11-16"
    rapor_durumu["donem"] = donem
    durum = {
        "gunluk": donem,
        "_rapor_durum": {"gunluk": rapor_durumu},
    }

    _, sahiplenildi = rapor_mail_durumunu_guncelle(
        durum, "gunluk", donem, 100, "sahiplen", "claim-next"
    )

    assert sahiplenildi is False


def _uygulama_fonksiyonlarini_yukle(adlar, namespace):
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"))
    fonksiyonlar = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in adlar
    ]
    module = ast.fix_missing_locations(
        ast.Module(body=fonksiyonlar, type_ignores=[])
    )
    exec(compile(module, str(app_path), "exec"), namespace)
    return namespace


@pytest.fixture(scope="module")
def fire_helpers():
    return _uygulama_fonksiyonlarini_yukle(
        {"fire_partisi_detayi", "fire_partisi_etiketi"},
        {},
    )


def test_manuel_rapor_okuma_hatasinda_mail_gondermez():
    hata = RuntimeError("girisler okunamadı: HTTP 503")
    st = SimpleNamespace(error=Mock())
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"manuel_rapor_maili_gonder"},
        {
            "datetime": datetime,
            "rapor_verilerini_oku": Mock(side_effect=hata),
            "_supabase_ham_oku": Mock(),
            "log": Mock(),
            "st": st,
            "_smtp_gonder_senkron": Mock(),
        },
    )

    assert namespace["manuel_rapor_maili_gonder"]() is False
    namespace["_smtp_gonder_senkron"].assert_not_called()
    st.error.assert_called_once()


def test_manuel_rapor_html_inde_kullanici_metni_escape_edilir():
    bugun = datetime.date.today()
    veri = {
        "girisler": [{
            "tarih": str(bugun - datetime.timedelta(days=1)),
            "urun": "<img src=x onerror=alert(1)>",
            "miktar": "1<script>",
            "birim": "kg",
            "fatura_no": "<svg onload=alert(1)>",
        }],
        "kullanim_loglari": [{
            "tarih": str(bugun - datetime.timedelta(days=1)),
            "urun": "MERCİMEK",
            "fatura_no": "FIRE-<svg onload=alert(1)>",
            "tur": "Fire/Zayiat",
            "miktar": 1,
            "tutar": 3,
            "aciklama": "Fire",
        }],
        "silinen_urun_loglari": [],
        "yemek_uretim_arsivi": [],
        "personel_izinleri": [],
    }
    smtp = Mock(return_value=(True, ""))
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"_rapor_html_metni", "manuel_rapor_maili_gonder"},
        {
            "datetime": datetime,
            "html_escape": html.escape,
            "rapor_verilerini_oku": rapor_verilerini_oku,
            "_supabase_ham_oku": lambda anahtar: ("ok", veri[anahtar]),
            "log": Mock(),
            "st": SimpleNamespace(spinner=lambda _: nullcontext()),
            "_smtp_gonder_senkron": smtp,
        },
    )

    assert namespace["manuel_rapor_maili_gonder"]() is True
    gonderilen_html = smtp.call_args.args[1]
    assert "&lt;img src=x onerror=alert(1)&gt;" in gonderilen_html
    assert "&lt;script&gt;" in gonderilen_html
    assert "FIRE-&lt;svg onload=alert(1)&gt;" in gonderilen_html
    assert "<img src=x onerror=alert(1)>" not in gonderilen_html


def test_otomatik_rapor_html_inde_kullanici_metni_escape_edilir():
    veri = {
        "girisler": [{
            "tarih": "2026-11-16",
            "urun": "<img src=x onerror=alert(1)>",
            "miktar": "1<script>",
            "birim": "kg",
            "fatura_no": "<svg onload=alert(1)>",
        }],
        "kullanim_loglari": [{
            "tarih": "2026-11-16",
            "urun": "MERCİMEK",
            "fatura_no": "FIRE-<svg onload=alert(1)>",
            "tur": "Fire/Zayiat",
            "miktar": 1,
            "tutar": 3,
            "aciklama": "Fire",
        }],
        "silinen_urun_loglari": [],
        "yemek_uretim_arsivi": [],
        "personel_izinleri": [],
    }
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"_rapor_html_metni", "_rapor_icerigi_olustur"},
        {
            "html_escape": html.escape,
            "rapor_verilerini_oku": rapor_verilerini_oku,
            "_supabase_ham_oku": lambda anahtar: ("ok", veri[anahtar]),
        },
    )

    gonderilen_html = namespace["_rapor_icerigi_olustur"](
        "Günlük", "16.11.2026", "2026-11-16", "2026-11-16"
    )
    assert "&lt;img src=x onerror=alert(1)&gt;" in gonderilen_html
    assert "&lt;svg onload=alert(1)&gt;" in gonderilen_html
    assert "FIRE-&lt;svg onload=alert(1)&gt;" in gonderilen_html
    assert "<img src=x onerror=alert(1)>" not in gonderilen_html


def test_otomatik_rapor_okuma_hatasinda_smtp_atlanip_tekrar_planlanir():
    sabit_tarih = datetime.datetime(2026, 11, 17, 10, 0)

    class _SabitTarih:
        @classmethod
        def now(cls):
            return sabit_tarih

    sahiplen = Mock(return_value="claim-1")
    geri_al = Mock()
    smtp = Mock()
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"gunluk_rapor_maili_gonder"},
        {
            "datetime": SimpleNamespace(
                datetime=_SabitTarih,
                timedelta=datetime.timedelta,
            ),
            "holidays": SimpleNamespace(Turkey=lambda: set()),
            "_rapor_sahiplen": sahiplen,
            "_rapor_icerigi_olustur": Mock(
                side_effect=RuntimeError("girisler okunamadı: HTTP 503")
            ),
            "_rapor_geri_al": geri_al,
            "_smtp_gonder_senkron": smtp,
            "log": Mock(),
        },
    )

    assert namespace["gunluk_rapor_maili_gonder"]() is False
    sahiplen.assert_called_once_with("gunluk", "2026-11-17")
    geri_al.assert_called_once_with("gunluk", "2026-11-17", "claim-1")
    smtp.assert_not_called()


def test_geri_yukleme_once_guvenlik_yedegi_alir_ve_yuklenen_veriyi_temizler():
    islemler = []
    state = {"girisler": ["eski"], "_db_hash": {"girisler": "old"}}
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"yedek_geri_yukle"},
        {
            "SUPABASE_URL": "https://example.invalid",
            "SUPABASE_KEY": "test-key",
            "YEDEK_ANAHTARLARI": ("girisler", "kritik_seviyeler"),
            "KAYIT_ESLEME": {"girisler": "girisler"},
            "otomatik_yedek_al": lambda neden: islemler.append(("backup", neden)) or True,
            "supabase_veri_kaydet": lambda anahtar, veri, zorla=False:
                islemler.append(("write", anahtar, zorla)),
            "st": SimpleNamespace(session_state=state),
        },
    )

    basarili, mesaj = namespace["yedek_geri_yukle"](
        {"veri": {"girisler": ["yeni"], "kritik_seviyeler": {}}}
    )

    assert basarili is True
    assert "2 bölüm" in mesaj
    assert islemler[0][0] == "backup"
    assert [islem[1] for islem in islemler[1:]] == [
        "girisler", "kritik_seviyeler"
    ]
    assert all(islem[2] is True for islem in islemler[1:])
    assert "girisler" not in state
    assert "_db_hash" not in state


def test_geri_yukleme_guvenlik_yedegi_alinamazsa_yazma_yapmaz():
    yaz = Mock()
    namespace = _uygulama_fonksiyonlarini_yukle(
        {"yedek_geri_yukle"},
        {
            "SUPABASE_URL": "https://example.invalid",
            "SUPABASE_KEY": "test-key",
            "YEDEK_ANAHTARLARI": ("girisler",),
            "KAYIT_ESLEME": {"girisler": "girisler"},
            "otomatik_yedek_al": Mock(return_value=False),
            "supabase_veri_kaydet": yaz,
            "st": SimpleNamespace(session_state={}),
        },
    )

    basarili, mesaj = namespace["yedek_geri_yukle"](
        {"veri": {"girisler": ["yeni"]}}
    )

    assert basarili is False
    assert "otomatik yedek alınamadı" in mesaj
    yaz.assert_not_called()
