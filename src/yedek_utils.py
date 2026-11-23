"""Backup payload orchestration and validation, separated from Streamlit state."""


def yedek_paketi_olustur(
    supabase_url, supabase_key, anahtarlar, ham_oku, zaman_etiketi, olusturan
):
    """Collect raw backup records; abort the package if any section has a read error."""
    if not supabase_url or not supabase_key:
        return None
    veri = {}
    for anahtar in anahtarlar:
        durum, icerik = ham_oku(anahtar)
        if durum == "hata":
            return None
        if durum == "ok":
            veri[anahtar] = icerik
    return {
        "_meta": {
            "zaman": zaman_etiketi,
            "surum": 1,
            "olusturan": olusturan,
        },
        "veri": veri,
    }


def yedek_geri_yukle(
    paket, supabase_url, supabase_key, izinli_anahtarlar, otomatik_yedek_al,
    veri_kaydet, bellekteki_veriyi_temizle,
):
    """Validate and restore a backup, requiring a safety backup before any writes."""
    if not supabase_url or not supabase_key:
        return False, "Supabase yapılandırılmamış; geri yükleme yapılamadı."
    yazilacak, hata = yedek_verisini_dogrula(paket, izinli_anahtarlar, {"kritik_seviyeler"})
    if hata:
        return False, hata
    if not otomatik_yedek_al("Geri yükleme öncesi otomatik yedek"):
        return False, "Geri yükleme öncesi otomatik yedek alınamadı; güvenlik için iptal edildi."

    for key, value in yazilacak.items():
        veri_kaydet(key, value)
    bellekteki_veriyi_temizle()
    return True, f"{len(yazilacak)} bölüm geri yüklendi."


def yedek_verisini_dogrula(paket, izinli_anahtarlar, sozluk_anahtarlari=()):
    """Return (filtered data, error message); persistence and rollback stay in app.py."""
    if not isinstance(paket, dict) or not isinstance(paket.get("veri"), dict):
        return None, "Geçersiz yedek dosyası."

    yazilacak = {
        key: value for key, value in paket["veri"].items()
        if key in izinli_anahtarlar
    }
    if not yazilacak:
        return None, "Yedek dosyasında geri yüklenecek bölüm bulunamadı."

    for key, value in yazilacak.items():
        beklenen = dict if key in sozluk_anahtarlari else list
        if not isinstance(value, beklenen):
            return None, f"'{key}' bölümü hatalı biçimde, geri yükleme iptal edildi."
    return yazilacak, None
