"""Supabase REST operations with injected session and header providers."""
import time


def supabase_veri_kaydet(
    kayit_id, veri_objesi, zorla, url, anahtar, kayit_esleme, ham_oku,
    taban_hashler, veri_hash, basliklar_fn, post_fn, hata_dur, cakisma_dur,
):
    """Write a record while enforcing the app's session baseline conflict check."""
    if not url or not anahtar:
        return
    if kayit_id in kayit_esleme and not zorla:
        durum, mevcut = ham_oku(kayit_id)
        if durum == "hata":
            hata_dur(f"'{kayit_id}' doğrulanamadı ({mevcut})")
        guncel = veri_hash(mevcut) if durum == "ok" else "__yok__"
        taban = taban_hashler().get(kayit_id)
        if taban is not None and taban != guncel:
            cakisma_dur()
    try:
        response = post_fn(
            f"{url}/rest/v1/asevi_veritabani",
            headers=basliklar_fn({
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }),
            json={"id": kayit_id, "veri": veri_objesi},
            timeout=10,
        )
    except Exception as exc:
        hata_dur(
            f"'{kayit_id}' kaydedilemedi (Bağlantı hatası: {type(exc).__name__})"
        )
        return
    if response.status_code not in (200, 201):
        hata_dur(f"'{kayit_id}' kaydedilemedi (HTTP {response.status_code})")
        return
    if kayit_id in kayit_esleme:
        try:
            taban_hashler()[kayit_id] = veri_hash(response.json()[0]["veri"])
        except Exception:
            taban_hashler().pop(kayit_id, None)


def supabase_veri_oku(
    kayit_id, varsayilan_deger, kritik, url, anahtar, onbelleksiz_anahtarlar,
    kayit_esleme, ham_oku, ham_oku_cached, taban_hashler, veri_hash, hata_dur,
):
    """Coordinate cache policy, fallback behavior, and per-session baseline hashes."""
    if not url or not anahtar:
        return varsayilan_deger
    if kayit_id in onbelleksiz_anahtarlar:
        durum, veri = ham_oku(kayit_id)
    else:
        durum, veri = ham_oku_cached(kayit_id)
    if durum == "hata":
        if kritik:
            hata_dur(f"'{kayit_id}' okunamadı ({veri})")
        return varsayilan_deger
    if kayit_id in kayit_esleme:
        taban_hashler()[kayit_id] = veri_hash(veri) if durum == "ok" else "__yok__"
    return veri if durum == "ok" else varsayilan_deger


def supabase_atomik_dict_guncelle(
    kayit_id, guncelleme_fn, okuma_versiyonlu, cas_yaz, max_retry=8, uyku=time.sleep
):
    """Retry an optimistic read-modify-write until CAS succeeds or retries are exhausted."""
    son_hata = ""
    for i in range(max_retry):
        durum, mevcut, versiyon = okuma_versiyonlu(kayit_id)
        if durum == "hata":
            return "hata", mevcut
        mevcut_dict = dict(mevcut) if isinstance(mevcut, dict) else {}
        yeni = guncelleme_fn(dict(mevcut_dict))
        basarili, sonuc = cas_yaz(kayit_id, versiyon, yeni)
        if basarili:
            return "ok", yeni
        son_hata = sonuc
        uyku(0.02 * (2 ** min(i, 4)))
    return "hata", f"Çakışma ({max_retry} deneme): {son_hata}"


def supabase_ham_oku(url, kayit_id, headers_fn, session_fn):
    """Return ('ok', data), ('yok', None), or ('hata', message)."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/asevi_veritabani",
            headers=headers_fn(),
            params={"id": f"eq.{kayit_id}", "select": "veri"},
            timeout=10,
        )
    except Exception as exc:
        return "hata", f"Bağlantı hatası: {type(exc).__name__}"
    if response.status_code != 200:
        return "hata", f"HTTP {response.status_code}"
    try:
        data = response.json()
    except Exception:
        return "hata", "Geçersiz yanıt"
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"]
    return "yok", None


def supabase_ham_oku_versiyonlu(url, kayit_id, headers_fn, session_fn):
    """Return versioned CAS data without using any cache."""
    try:
        response = session_fn().get(
            f"{url}/rest/v1/asevi_veritabani",
            headers=headers_fn(),
            params={"id": f"eq.{kayit_id}", "select": "veri,versiyon"},
            timeout=10,
        )
    except Exception as exc:
        return "hata", f"Bağlantı hatası: {type(exc).__name__}", None
    if response.status_code != 200:
        return "hata", f"HTTP {response.status_code}", None
    try:
        data = response.json()
    except Exception:
        return "hata", "Geçersiz yanıt", None
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"], int(data[0].get("versiyon") or 0)
    return "yok", None, None


def supabase_cas_yaz(url, kayit_id, beklenen_versiyon, yeni_veri, headers_fn, session_fn):
    """Insert or update a record only if its expected version still matches."""
    try:
        if beklenen_versiyon is None:
            response = session_fn().post(
                f"{url}/rest/v1/asevi_veritabani",
                headers=headers_fn({
                    "Content-Type": "application/json",
                    "Prefer": "resolution=ignore-duplicates,return=representation",
                }),
                json={"id": kayit_id, "veri": yeni_veri, "versiyon": 0},
                timeout=10,
            )
            if response.status_code in (200, 201) and response.json():
                return True, 0
            return False, "insert-çakışma"

        yeni_versiyon = beklenen_versiyon + 1
        response = session_fn().patch(
            f"{url}/rest/v1/asevi_veritabani",
            headers=headers_fn({
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }),
            params={"id": f"eq.{kayit_id}", "versiyon": f"eq.{beklenen_versiyon}"},
            json={"veri": yeni_veri, "versiyon": yeni_versiyon},
            timeout=10,
        )
        if response.status_code == 200:
            updated = response.json()
            if updated:
                return True, yeni_versiyon
            return False, "versiyon-çakışma"
        return False, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, f"Bağlantı hatası: {type(exc).__name__}"
