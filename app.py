import base64
import datetime
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import time
from html import escape as html_escape
import difflib
import zoneinfo
import requests
from cryptography.fernet import Fernet
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# Sayfa Yapılandırması: Streamlit'te İLK komut olmak zorundadır
# (kenar çubuğu, önbellek vb. komutlardan önce çağrılmalıdır).
st.set_page_config(
    page_title="Aziziye - Aşevi Takip Sistemi",
    page_icon="🍲",
    layout="wide",
)

APP_VERSION = "v2.0.0"
LAST_UPDATE = "Kasım 2026"


def bellek_kullanimi_al():
    """Python sürecinin sunucuda kullandığı anlık RAM miktarını (MB) hesaplar."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 1)
    except Exception:
        return 0.0

def baglanti_tanilama_goster():
    """?tani=1 adresinde çalışır. Gizli değerleri GÖSTERMEZ; yalnızca ayarların görünüp
    görünmediğini ve Supabase bağlantısının veri döndürüp döndürmediğini denetler."""
    st.markdown("## 🔧 Bağlantı Tanılama")
    st.caption(
        "Bu sayfa şifre/anahtar değerlerini göstermez. Sorun çözülünce secrets içindeki `TANI_MODU` satırını silin."
    )
    try:
        ust_anahtarlar = list(st.secrets.keys())
    except Exception as e:
        st.error(
            f"Secrets okunamadı ({type(e).__name__}). Secrets metnindeki biçimi kontrol edin: "
            'her satır `ADI = "değer"` şeklinde ve DÜZ çift tırnaklı olmalı (“ ” gibi kıvrık tırnak olmaz).'
        )
        return
    bolumler = {}
    for k in ust_anahtarlar:
        try:
            if hasattr(st.secrets[k], "keys"):
                bolumler[k] = list(st.secrets[k].keys())
        except Exception:
            pass

    st.markdown("### 1) Secrets ayarları")
    for ad in ("SUPABASE_URL", "SUPABASE_KEY", "FERNET_KEY", "MASTER_RECOVERY_KEY"):
        if ad in ust_anahtarlar and ad not in bolumler:
            deger = str(st.secrets.get(ad, ""))
            if deger.strip() == "":
                st.warning(f"**{ad}**: tanımlı ama BOŞ.")
            elif deger != deger.strip():
                st.warning(f"**{ad}**: değerin başında/sonunda boşluk veya satır sonu var; silin.")
            elif any(c in deger for c in "“”‘’"):
                st.warning(f"**{ad}**: değerde kıvrık tırnak karakteri var; düz tırnak kullanın.")
            else:
                st.success(f"**{ad}**: görünüyor.")
        else:
            yerler = [b for b, alt in bolumler.items() if ad in alt]
            if yerler:
                st.error(
                    f"**{ad}**: bir `[{yerler[0]}]` bölümünün İÇİNDE kalmış, bu yüzden uygulama göremiyor. "
                    f"Secrets metninde bu satırı, ilk `[bölüm]` başlığından ÖNCEKİ en üst kısma taşıyın."
                )
            else:
                st.error(f"**{ad}**: bulunamadı (ad büyük/küçük harfe duyarlıdır, tam olarak bu yazılmalı).")
    if bolumler:
        st.info("Secrets içinde bölüm başlıkları var: " + ", ".join(f"[{b}]" for b in bolumler))
    st.caption("Secrets'ta görünen en üst düzey ad sayısı: " + str(len([k for k in ust_anahtarlar if k not in bolumler])))

    st.markdown("### 2) Supabase bağlantısı")
    url = str(st.secrets.get("SUPABASE_URL", "") or "")
    anahtar = str(st.secrets.get("SUPABASE_KEY", "") or "")
    if not url or not anahtar:
        st.error("SUPABASE_URL veya SUPABASE_KEY görünmüyor; uygulama yerel (geçici) modda çalışır ve hiçbir veri kaydedilmez.")
        return
    if not url.startswith("https://") or "/rest/" in url or url.endswith("/"):
        st.warning("SUPABASE_URL biçimi şöyle olmalı: `https://PROJEKODU.supabase.co` (sonunda `/` ve `/rest/v1` OLMADAN).")
    rol = "bilinmiyor"
    if anahtar.startswith("sb_publishable"):
        rol = "anon"
    elif anahtar.startswith("sb_secret"):
        rol = "service_role"
    else:
        try:
            parca = anahtar.split(".")[1]
            parca += "=" * (-len(parca) % 4)
            rol = str(json.loads(base64.urlsafe_b64decode(parca)).get("role", "bilinmiyor"))
        except Exception:
            rol = "bilinmiyor"
    if rol == "anon":
        st.warning("Kullanılan anahtar **anon / publishable** türünde. RLS açıksa bu anahtar tablodan veri OKUYAMAZ ve YAZAMAZ. `service_role` (secret) anahtarına geçin.")
    elif rol == "service_role":
        st.success("Kullanılan anahtar **service_role / secret** türünde (doğru).")
    else:
        st.info("Anahtarın türü belirlenemedi. Anahtarı Supabase > Project Settings > API bölümünden yeniden kopyalayın.")

    basliklar = {"apikey": anahtar}
    if not anahtar.startswith("sb_"):
        basliklar["Authorization"] = f"Bearer {anahtar}"
    try:
        r = requests.get(
            f"{url}/rest/v1/asevi_veritabani", headers=basliklar,
            params={"select": "id", "limit": "50"}, timeout=10,
        )
    except Exception as e:
        st.error(f"Supabase'e ulaşılamadı ({type(e).__name__}). SUPABASE_URL yanlış olabilir.")
        return
    try:
        govde = r.json()
    except Exception:
        govde = None
    if r.status_code == 200:
        satirlar = govde if isinstance(govde, list) else []
        if satirlar:
            st.success(f"Bağlantı ve okuma ÇALIŞIYOR. Tabloda görünen kayıt sayısı: {len(satirlar)} ({', '.join(str(x.get('id')) for x in satirlar[:8])}...)")
        elif rol == "anon":
            st.error("Okuma HTTP 200 döndü ama 0 satır görünüyor. Anon anahtar + RLS birleşiminde Supabase hata vermez, satırları sessizce GİZLER. Asıl sorun budur: `service_role` anahtarına geçin.")
        else:
            st.warning("Bağlantı çalışıyor ama tablo boş görünüyor. Uygulama ilk açılışta kayıtları kendisi oluşturur; ilk kayıttan sonra tablo dolar. Dolmuyorsa yazma yetkisini kontrol edin.")
    elif r.status_code in (401, 403):
        st.error(f"HTTP {r.status_code}: anahtar geçersiz veya yetkisiz. Anahtarı yeniden kopyalayın (başında/sonunda boşluk olmasın).")
    elif r.status_code == 404:
        st.error("HTTP 404: `asevi_veritabani` tablosu bulunamadı veya SUPABASE_URL yanlış. Tabloyu kontrol edin (id: text, veri: jsonb).")
    else:
        mesaj = govde.get("message") if isinstance(govde, dict) else ""
        st.error(f"HTTP {r.status_code}: {mesaj}")


def _tani_acik_mi():
    """Tanılama sayfası varsayılan olarak KAPALIDIR. Açmak için hem adreste ?tani=1 hem de
    secrets içinde TANI_MODU = "1" bulunmalıdır. İşiniz bitince TANI_MODU satırını silin."""
    if str(st.query_params.get("tani", "")) != "1":
        return False
    try:
        return str(st.secrets.get("TANI_MODU", "")).strip().lower() in ("1", "true", "evet")
    except Exception:
        return False


if _tani_acik_mi():
    baglanti_tanilama_goster()
    st.stop()

# Şifreleme Anahtarı ve Motoru
# FERNET_KEY tanımlı değilse uygulama BİLEREK durdurulur: her açılışta rastgele
# anahtar üretmek, kaydedilen T.C./telefon/adres verilerini okunamaz hâle getirir.
try:
    gizli_anahtar = str(st.secrets["FERNET_KEY"]).encode("utf-8")
    fernet_motoru = Fernet(gizli_anahtar)
except Exception:
    st.error(
        "🔐 **FERNET_KEY tanımlı değil veya geçersiz.** Güvenlik ve veri kaybını önlemek için "
        "uygulama durduruldu. Aşağıdaki komutla bir anahtar üretip `secrets` ayarlarınıza "
        "`FERNET_KEY = \"...\"` olarak ekleyin ve anahtarı güvenli bir yerde YEDEKLEYİN:"
    )
    st.code(
        'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
        language="bash",
    )
    st.stop()

class SifrelemeHatasi(RuntimeError):
    """Fernet şifreleme başarısız olduğunda fırlatılır. Düz metin kaydını engeller."""

def metni_sifrele(duz_metin):
    if not duz_metin:
        return ""
    # Zaten şifreli (Fernet) gelen değer tekrar şifrelenmez; aksi hâlde anahtar
    # uyuşmazlığında veri katman katman şifrelenip geri dönülmez hâle gelir.
    if str(duz_metin).startswith("gAAAAA"):
        return str(duz_metin)
    try:
        return fernet_motoru.encrypt(str(duz_metin).encode("utf-8")).decode("utf-8")
    except Exception as e:
        # DÜZ METİN DÖNDÜRMEK YASAK: T.C./telefon/adres gibi hassas alanlar
        # sessizce açık metin olarak veritabanına yazılırdı. Bunun yerine
        # hatayı yukarı fırlatıp çağıran katmanda kaydı iptal ettiriyoruz.
        raise SifrelemeHatasi(
            f"Şifreleme başarısız oldu ({type(e).__name__}); veri kaydedilmedi."
        ) from e


def metni_coz(sifreli_metin):
    if not sifreli_metin:
        return ""
    try:
        if not str(sifreli_metin).startswith("gAAAAA"):
            return str(sifreli_metin)
        return fernet_motoru.decrypt(str(sifreli_metin).encode("utf-8")).decode(
            "utf-8"
        )
    except Exception:
        return str(sifreli_metin)


def sifre_hashle(sifre):
    """ESKİ yöntem (tuzsuz SHA-256). Yalnızca eski kayıtları doğrulamak için tutulur."""
    if not sifre:
        return ""
    return hashlib.sha256(str(sifre).encode("utf-8")).hexdigest()


# Eski sürümlerde kodda açıkça yazılı olan varsayılan şifrelerin SHA-256 hash'leri.
# Bu hash'lerle kayıtlı hesaplar ilk girişte şifre değiştirmeye zorlanır.
ESKI_VARSAYILAN_HASHLER = {
    "8110e127a1ea6d6e6b10122673400c15d112802259aeb48783b7ae3c795937c4",
    "f6595d11049c9b69670c7ce640632b5131e93032aad76a5796bfc4506c6afd65",
    "eeed6b32b495d07ee61434679ddd7640024cb7b0a7d53561bf847b11b2405a56",
}

_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024


def sifre_hashle_yeni(sifre):
    """Her şifre için rastgele tuzlu, yavaş (scrypt) hash üretir: s1$tuz$hash"""
    tuz = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        str(sifre).encode("utf-8"), salt=tuz, n=_SCRYPT_N, r=_SCRYPT_R,
        p=_SCRYPT_P, dklen=32, maxmem=_SCRYPT_MAXMEM,
    )
    return f"s1${tuz.hex()}${dk.hex()}"


def sifre_dogrula(girilen, kayitli):
    """Hem yeni (scrypt) hem eski (SHA-256) kayıtları sabit zamanlı karşılaştırır."""
    girilen = str(girilen or "")
    kayitli = str(kayitli or "")
    if kayitli == "":
        return girilen == ""
    if kayitli.startswith("s1$"):
        try:
            _, tuz_hex, hash_hex = kayitli.split("$")
            dk = hashlib.scrypt(
                girilen.encode("utf-8"), salt=bytes.fromhex(tuz_hex), n=_SCRYPT_N,
                r=_SCRYPT_R, p=_SCRYPT_P, dklen=32, maxmem=_SCRYPT_MAXMEM,
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False
    return hmac.compare_digest(sifre_hashle(girilen), kayitli)


def sifre_yukseltilmeli_mi(kayitli):
    """Kayıtlı hash eski biçimdeyse (SHA-256) True döner."""
    return bool(kayitli) and not str(kayitli).startswith("s1$")


def sifre_politika_hatasi(sifre):
    """Şifre kurallara uymuyorsa hata metni, uyuyorsa None döner."""
    sifre = str(sifre or "")
    if len(sifre) < 10:
        return "Şifre en az 10 karakter olmalıdır."
    if not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", sifre) or not re.search(r"\d", sifre):
        return "Şifre en az bir harf ve en az bir rakam içermelidir."
    return None


def simdi_tr_str(format_str="%Y-%m-%d %H:%M"):
    """Gerçek Türkiye saatini (Europe/Istanbul) döndürür."""
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).strftime(format_str)
    except Exception:
        return datetime.datetime.now().strftime(format_str)

# =========================================================================
# SUPABASE BULUT VERİTABANI BAĞLANTI FONKSİYONLARI
# =========================================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# Kayıt kimliği -> session_state anahtarı. Bu veriler için "çakışma denetimi" yapılır:
# başka bir oturum veriyi değiştirdiyse, eski kopyayla üzerine yazmak engellenir.
KAYIT_ESLEME = {
    "girisler": "girisler",
    "kullanim_loglari": "kullanim_loglari",
    "silinen_urun_loglari": "silinen_urun_loglari",
    "ihtiyac_sahipleri": "ihtiyac_sahipleri",
    "dagitim_loglari": "dagitim_loglari",
    "personeller": "personeller",
    "personel_izinleri": "personel_izinleri",
    "resmi_tatiller": "resmi_tatiller",
    "yemek_uretim_arsivi": "yemek_uretim_arsivi",
    "depolar_listesi": "depolar",
    "demirbaslar_listesi": "demirbaslar",
    "kritik_seviyeler": "kritik_seviyeler",
    "kullanici_yetkileri": "kullanicilar",
    "dashboard_widgets": "dashboard_widgets",
}
# Yedeğe giren veriler (kullanıcı/şifre bilgileri, oturum ve deneme kayıtları yedeğe girmez)
YEDEK_ANAHTARLARI = [k for k in KAYIT_ESLEME if k != "kullanici_yetkileri"]

        
# Güvenlik açısından kritik anahtarlar: bu anahtarların okumaları cache'i
# ATLAMALI. Aksi hâlde 60 sn'lik @st.cache_data penceresinde birbirini izleyen
# "oku → değiştir → yaz" döngüleri eski sayacın üzerine yazar; hem kullanıcı
# bazlı kilit (MAKS_HATALI_GIRIS) hem IP kilidi fiilen devre dışı kalır.
ONBELLEKSIZ_ANAHTARLAR = {"giris_denemeleri", "aktif_oturumlar"}

def _supa_basliklar(ekstra=None):
    h = {"apikey": SUPABASE_KEY}
    if not str(SUPABASE_KEY).startswith("sb_"):  # sb_secret_/sb_publishable_ anahtarları JWT değildir
        h["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if ekstra:
        h.update(ekstra)
    return h


def supabase_anahtar_rolu():
    """Kullanılan Supabase anahtarının rolü: 'anon', 'service_role' veya 'bilinmiyor'."""
    anahtar = str(SUPABASE_KEY or "")
    if anahtar.startswith("sb_publishable"):
        return "anon"
    if anahtar.startswith("sb_secret"):
        return "service_role"
    try:
        parca = anahtar.split(".")[1]
        parca += "=" * (-len(parca) % 4)
        return str(json.loads(base64.urlsafe_b64decode(parca)).get("role", "bilinmiyor"))
    except Exception:
        return "bilinmiyor"


def _veri_hash(veri):
    return hashlib.sha256(
        json.dumps(veri, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()

# =========================================================================
# HIZLANDIRILMIŞ VERİTABANI BAĞLANTI VE ÖNBELLEKLEME
# =========================================================================
@st.cache_resource
def get_http_session():
    """Tüm Supabase istekleri için ortak ve hızlı HTTP bağlantı havuzu oluşturur."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    return session


def _supabase_ham_oku(kayit_id):
    """('ok', veri) | ('yok', None) | ('hata', mesaj). Oturum durumunu DEĞİŞTİRMEZ."""
    try:
        session = get_http_session()
        r = session.get(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar(),
            params={"id": f"eq.{kayit_id}", "select": "veri"},
            timeout=10,
        )
    except Exception as e:
        return "hata", f"Bağlantı hatası: {type(e).__name__}"
    if r.status_code != 200:
        return "hata", f"HTTP {r.status_code}"
    try:
        data = r.json()
    except Exception:
        return "hata", "Geçersiz yanıt"
    if data and data[0].get("veri") is not None:
        return "ok", data[0]["veri"]
    return "yok", None


@st.cache_data(ttl=60, show_spinner=False)
def _supabase_ham_oku_cached(kayit_id):
    """Veritabanı okumalarını 60 saniye boyunca bellek seviyesinde hızlı tutar.
    Güvenlik açısından kritik anahtarlar bu cache'i KULLANMAZ; bkz. ONBELLEKSIZ_ANAHTARLAR."""
    return _supabase_ham_oku(kayit_id)

def _taban_hashler():
    if "_db_hash" not in st.session_state:
        st.session_state["_db_hash"] = {}
    return st.session_state["_db_hash"]


def _veritabani_hatasi_dur(mesaj):
    st.error(
        f"⚠️ **Veritabanı hatası:** {mesaj}. Verilerinizin bozulmaması için işlem durduruldu. "
        "Bağlantıyı/ayarları kontrol edip sayfayı yenileyin."
    )
    st.stop()


def supabase_veri_oku(kayit_id, varsayilan_deger, kritik=True):
    """Veriyi okur. Bulunamazsa varsayılanı döndürür. Hata olursa (kritik=True ise)
    boş veri DÖNDÜRMEK yerine işlemi durdurur; aksi hâlde sonraki kayıt veritabanını
    boşla ezebilirdi."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return varsayilan_deger
    # Güvenlik açısından kritik anahtarlar cache'i ATLAR (bkz. ONBELLEKSIZ_ANAHTARLAR).
    if kayit_id in ONBELLEKSIZ_ANAHTARLAR:
        durum, veri = _supabase_ham_oku(kayit_id)
    else:
        durum, veri = _supabase_ham_oku_cached(kayit_id)
    if durum == "hata":
        if kritik:
            _veritabani_hatasi_dur(f"'{kayit_id}' okunamadı ({veri})")
        return varsayilan_deger
    if kayit_id in KAYIT_ESLEME:
        _taban_hashler()[kayit_id] = _veri_hash(veri) if durum == "ok" else "__yok__"
    return veri if durum == "ok" else varsayilan_deger


def _cakisma_ve_dur():
    for sk in set(KAYIT_ESLEME.values()):
        st.session_state.pop(sk, None)
    st.session_state.pop("_db_hash", None)
    st.error(
        "⚠️ **Kayıt YAPILMADI – veri çakışması.** Siz çalışırken başka bir kullanıcı/oturum "
        "bu veriyi değiştirdi. Onun değişikliğinin silinmemesi için işleminiz iptal edildi. "
        "Aşağıdaki düğmeyle güncel verileri yükleyip işlemi tekrar yapın."
    )
    if st.button("🔄 Verileri Yenile", key="cakisma_yenile_btn"):
        st.rerun()
    st.stop()


def supabase_veri_kaydet(kayit_id, veri_objesi, zorla=False):
    """Veriyi kaydeder. Çakışma varsa ve kayıt başarısız olursa işlemi durdurur
    (hata artık sessizce yutulmaz)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    if kayit_id in KAYIT_ESLEME and not zorla:
        durum, mevcut = _supabase_ham_oku(kayit_id)
        if durum == "hata":
            _veritabani_hatasi_dur(f"'{kayit_id}' doğrulanamadı ({mevcut})")
        guncel = _veri_hash(mevcut) if durum == "ok" else "__yok__"
        taban = _taban_hashler().get(kayit_id)
        if taban is not None and taban != guncel:
            _cakisma_ve_dur()
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/asevi_veritabani",
            headers=_supa_basliklar({
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }),
            json={"id": kayit_id, "veri": veri_objesi},
            timeout=10,
        )
    except Exception as e:
        _veritabani_hatasi_dur(f"'{kayit_id}' kaydedilemedi (Bağlantı hatası: {type(e).__name__})")
    if r.status_code not in (200, 201):
        _veritabani_hatasi_dur(f"'{kayit_id}' kaydedilemedi (HTTP {r.status_code})")
    if kayit_id in KAYIT_ESLEME:
        try:
            _taban_hashler()[kayit_id] = _veri_hash(r.json()[0]["veri"])
        except Exception:
            _taban_hashler().pop(kayit_id, None)
    

# =========================================================================
# YEDEKLEME / GERİ YÜKLEME
# =========================================================================
def yedek_paketi_olustur():
    """Veritabanındaki ham veriyi (şifreli alanlar şifreli kalır) paketler. Hata olursa None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    veri = {}
    for anahtar in YEDEK_ANAHTARLARI:
        durum, icerik = _supabase_ham_oku(anahtar)
        if durum == "hata":
            return None
        if durum == "ok":
            veri[anahtar] = icerik
    return {
        "_meta": {
            "zaman": simdi_tr_str("%Y-%m-%d %H:%M:%S"),
            "surum": 1,
            "olusturan": st.session_state.get("aktif_kullanici", ""),
        },
        "veri": veri,
    }


def otomatik_yedek_al(neden):
    """Silme gibi geri dönüşsüz işlemlerden önce tek seviyelik otomatik yedek alır."""
    paket = yedek_paketi_olustur()
    if paket is None:
        return False
    paket["_meta"]["neden"] = str(neden)[:200]
    supabase_veri_kaydet("otomatik_yedek", paket)
    return True


def yedek_geri_yukle(paket):
    """Yedek paketini veritabanına yazar. (basarili, mesaj) döndürür."""
    if not isinstance(paket, dict) or not isinstance(paket.get("veri"), dict):
        return False, "Geçersiz yedek dosyası."
    yazilacak = {k: v for k, v in paket["veri"].items() if k in YEDEK_ANAHTARLARI}
    if not yazilacak:
        return False, "Yedek dosyasında geri yüklenecek bölüm bulunamadı."
    for k, v in yazilacak.items():
        beklenen = dict if k == "kritik_seviyeler" else list
        if not isinstance(v, beklenen):
            return False, f"'{k}' bölümü hatalı biçimde, geri yükleme iptal edildi."
    otomatik_yedek_al("Geri yükleme öncesi otomatik yedek")
    for k, v in yazilacak.items():
        supabase_veri_kaydet(k, v, zorla=True)
    for sk in set(KAYIT_ESLEME.values()):
        st.session_state.pop(sk, None)
    st.session_state.pop("_db_hash", None)
    return True, f"{len(yazilacak)} bölüm geri yüklendi."


# =========================================================================
# OTURUM GÜVENLİĞİ
# =========================================================================
OTURUM_SURESI_SN = 8 * 60 * 60  # 8 saat
MAKS_HATALI_GIRIS = 3           # kullanıcı + IP başına
KILIT_SURESI_SN = 30            # ilk kilit süresi (her kilitte ikiye katlanır, en çok 15 dk)
IP_MAKS_HATALI_GIRIS = 10       # yalnızca IP başına (kullanıcı adı denemelerine karşı)
IP_KILIT_SURESI_SN = 60
COOKIE_ADI = "aziziye_oturum"
OTURUM_DOGRULAMA_ARALIGI_SN = 60  # açık oturum bu aralıkla veritabanından yeniden doğrulanır


def bosta_kalma_suresi_sn():
    """Etkinlik olmadığında oturumun kapanacağı süre. Varsayılan 30 dk;
    secrets içinde BOSTA_KALMA_DAKIKA ile 5-480 dk arasında değiştirilebilir."""
    try:
        dk = int(str(st.secrets.get("BOSTA_KALMA_DAKIKA", 30)))
    except Exception:
        dk = 30
    return max(5, min(dk, 480)) * 60

# Çerez desteği: `streamlit-cookies-controller` paketi kuruluysa token adres çubuğu yerine
# çerezde tutulur. Kurulu değilse eski yönteme (adreste token) güvenli şekilde geri düşer.
try:
    from streamlit_cookies_controller import CookieController
except Exception:
    CookieController = None

cerez_kontrol = None
if CookieController is not None:
    try:
        cerez_kontrol = CookieController(key="aziziye_cerez")
    except TypeError:
        try:
            cerez_kontrol = CookieController()
        except Exception:
            cerez_kontrol = None
    except Exception:
        cerez_kontrol = None


def cerez_oku():
    if cerez_kontrol is None:
        return ""
    try:
        return str(cerez_kontrol.get(COOKIE_ADI) or "")
    except Exception:
        return ""


def cerez_yaz(token):
    if cerez_kontrol is None:
        return
    try:
        cerez_kontrol.set(COOKIE_ADI, token, max_age=OTURUM_SURESI_SN, same_site="strict")
    except TypeError:
        try:
            cerez_kontrol.set(COOKIE_ADI, token)
        except Exception:
            pass
    except Exception:
        pass


def cerez_sil():
    if cerez_kontrol is None:
        return
    try:
        cerez_kontrol.remove(COOKIE_ADI)
    except Exception:
        pass


def istemci_ip_bilgisi():
    """(kilit için kullanılan IP, tam X-Forwarded-For). Kilitte EN SAĞDAKİ adres kullanılır:
    istemci tarafından sahte eklenen adresler soldadır, en sağdakini ise sunucuya en yakın
    güvenilir vekil ekler. Böylece sahte başlıkla kilit atlatılamaz."""
    try:
        basliklar = st.context.headers
        xff = str(basliklar.get("X-Forwarded-For", "") or "")
        if xff:
            ip = xff.split(",")[-1].strip()
        else:
            ip = str(basliklar.get("X-Real-Ip", "") or "").strip()
        return (ip or "bilinmiyor"), xff[:200]
    except Exception:
        return "bilinmiyor", ""


def giris_logla(kullanici, durum):
    """Giriş/çıkış/yönetim olaylarını (kim, ne zaman, hangi IP) kaydeder. Şifre KAYDEDİLMEZ."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    d, mevcut = _supabase_ham_oku("giris_loglari")
    if d == "hata":
        return
    kayitlar = mevcut if d == "ok" and isinstance(mevcut, list) else []
    ip, xff = istemci_ip_bilgisi()
    kayitlar.append({
        "zaman": simdi_tr_str("%Y-%m-%d %H:%M:%S"),
        "kullanici": str(kullanici)[:50],
        "durum": str(durum)[:80],
        "ip": ip,
        "xff": xff,
    })
    supabase_veri_kaydet("giris_loglari", kayitlar[-1000:])


def _token_hashle(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def oturum_olustur(kullanici_adi):
    """Rastgele token üretir; veritabanında yalnızca hash'ini saklar."""
    token = secrets.token_urlsafe(32)
    simdi = time.time()
    bitis = simdi + OTURUM_SURESI_SN
    oturumlar = supabase_veri_oku("aktif_oturumlar", {})
    if not isinstance(oturumlar, dict):
        oturumlar = {}
    oturumlar = {h: o for h, o in oturumlar.items() if o.get("bitis", 0) > simdi}
    oturumlar[_token_hashle(token)] = {"kullanici": kullanici_adi, "bitis": bitis}
    supabase_veri_kaydet("aktif_oturumlar", oturumlar)
    return token, bitis


def oturum_dogrula(token):
    if not token:
        return None
    oturumlar = supabase_veri_oku("aktif_oturumlar", {}, kritik=False)
    if not isinstance(oturumlar, dict):
        return None
    kayit = oturumlar.get(_token_hashle(token))
    if kayit and kayit.get("bitis", 0) > time.time():
        return kayit
    return None


def oturum_sil(token):
    if not token:
        return
    oturumlar = supabase_veri_oku("aktif_oturumlar", {})
    if not isinstance(oturumlar, dict):
        return
    h = _token_hashle(token)
    if h in oturumlar:
        del oturumlar[h]
        supabase_veri_kaydet("aktif_oturumlar", oturumlar)


def kullanici_oturumlarini_kapat(kullanici, haric_token=None):
    """Bir kullanıcının tüm açık oturumlarını (isteğe bağlı biri hariç) sonlandırır."""
    oturumlar = supabase_veri_oku("aktif_oturumlar", {})
    if not isinstance(oturumlar, dict):
        return
    haric = _token_hashle(haric_token) if haric_token else None
    yeni = {h: o for h, o in oturumlar.items() if o.get("kullanici") != kullanici or h == haric}
    if len(yeni) != len(oturumlar):
        supabase_veri_kaydet("aktif_oturumlar", yeni)


def oturumu_baslat(kullanici_adi):
    token, bitis = oturum_olustur(kullanici_adi)
    st.session_state.oturum_aktif = True
    st.session_state.aktif_kullanici = kullanici_adi
    st.session_state.oturum_token = token
    st.session_state.oturum_bitis = bitis
    st.session_state["son_etkinlik"] = time.time()
    st.session_state["_oturum_son_dogrulama"] = time.time()
    if kullanici_adi != "misafir":
        st.session_state.pop("ilk_kurulum_sifreleri", None)
    if cerez_kontrol is not None:
        cerez_yaz(token)
        time.sleep(1.0)  # tarayıcı bileşeninin çerezi yazabilmesi için kısa bekleme
    else:
        st.query_params["token"] = token


def oturumu_kapat():
    """Oturumu sunucuda iptal eder, çerezi ve oturum durumunu temizler."""
    kullanici = st.session_state.get("aktif_kullanici", "misafir")
    token = st.session_state.get("oturum_token", "")
    giris_logla(kullanici, "çıkış")
    oturum_sil(token)
    if cerez_kontrol is not None:
        cerez_sil()
        time.sleep(0.6)
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    st.session_state.oturum_bitis = 0
    st.query_params.clear()


def oturumu_zorla_kapat(mesaj, log_durumu):
    """Sunucu/süre/boşta kalma nedeniyle oturumu kapatır; giriş ekranında mesaj gösterilir."""
    kullanici = st.session_state.get("aktif_kullanici", "misafir")
    token = st.session_state.get("oturum_token", "")
    giris_logla(kullanici, log_durumu)
    oturum_sil(token)
    if cerez_kontrol is not None:
        cerez_sil()
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    st.session_state.oturum_bitis = 0
    st.session_state["oturum_mesaji"] = mesaj
    if "token" in st.query_params:
        del st.query_params["token"]


def sifre_degistir(kullanici, yeni_sifre, haric_token=None, zorunlu=False):
    """Şifreyi yeni (scrypt) biçimde kaydeder ve kullanıcının diğer oturumlarını kapatır."""
    k = st.session_state.kullanicilar[kullanici]
    k["sifre"] = sifre_hashle_yeni(yeni_sifre)
    if zorunlu:
        k["sifre_degistirilmeli"] = True
    else:
        k.pop("sifre_degistirilmeli", None)
    kullanıcıları_kaydet(st.session_state.kullanicilar)
    kullanici_oturumlarini_kapat(kullanici, haric_token)
    giris_logla(kullanici, "şifre değiştirildi")


def giris_kilit_kalan(anahtar):
    kayitlar = supabase_veri_oku("giris_denemeleri", {}, kritik=False)
    if not isinstance(kayitlar, dict):
        return 0
    return max(0, int(kayitlar.get(anahtar, {}).get("kilit_bitis", 0) - time.time()))


def hatali_giris_kaydet(anahtar, maks=MAKS_HATALI_GIRIS, taban_sn=KILIT_SURESI_SN):
    """(kalan_hak, kilitlendi_mi) döndürür. Her ardışık kilitte süre ikiye katlanır (en çok 15 dk)."""
    simdi = time.time()
    kayitlar = supabase_veri_oku("giris_denemeleri", {})
    if not isinstance(kayitlar, dict):
        kayitlar = {}
    kayitlar = {
        k: v for k, v in kayitlar.items()
        if v.get("kilit_bitis", 0) > simdi or simdi - v.get("son", 0) < 3600
    }
    kayit = kayitlar.get(anahtar, {"sayi": 0, "kilit_sayisi": 0, "kilit_bitis": 0, "son": 0})
    if simdi - kayit.get("son", 0) > 3600:
        kayit["sayi"] = 0
        kayit["kilit_sayisi"] = 0
    kayit["sayi"] = kayit.get("sayi", 0) + 1
    kayit["son"] = simdi
    kilitlendi = kayit["sayi"] >= maks
    if kilitlendi:
        kayit["kilit_sayisi"] = kayit.get("kilit_sayisi", 0) + 1
        sure = min(taban_sn * (2 ** (kayit["kilit_sayisi"] - 1)), 900)
        kayit["kilit_bitis"] = simdi + sure
        kayit["sayi"] = 0
    kayitlar[anahtar] = kayit
    supabase_veri_kaydet("giris_denemeleri", kayitlar)
    return max(maks - kayit["sayi"], 0), kilitlendi


def giris_denemesini_sifirla(anahtar=None):
    """anahtar verilirse yalnızca onu, verilmezse tüm kilitleri temizler."""
    if anahtar is None:
        supabase_veri_kaydet("giris_denemeleri", {})
        return
    kayitlar = supabase_veri_oku("giris_denemeleri", {})
    if isinstance(kayitlar, dict) and anahtar in kayitlar:
        del kayitlar[anahtar]
        supabase_veri_kaydet("giris_denemeleri", kayitlar)


# =========================================================
# SEFA AŞEVİ - PURE DARK LIQUID GLASS TEMA
# =========================================================

# Kodun alt kısımlarındaki KeyError ve NameError hatalarını engelleyen değişkenler:
if "tema" not in st.session_state:
    st.session_state.tema = "Dark"

border_color = "rgba(16, 185, 129, 0.35)"
bg_color = "#040711"
card_bg = "rgba(10, 15, 29, 0.75)"
sidebar_bg = "rgba(6, 10, 20, 0.85)"
text_color = "#f4f4f5"
subtext_color = "#94a3b8"
input_bg = "rgba(15, 23, 42, 0.85)"
popover_bg = "#0b1329"

# STİL ENJEKSİYONU
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Ana Arka Plan ve Tipografi */
    .stApp {
        background-color: #040711 !important;
        background-image: radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.12) 0%, transparent 45%),
                          radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.12) 0%, transparent 45%) !important;
        background-attachment: fixed !important;
        color: #f4f4f5 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Sol Menü (Sidebar) Cam Görünümü */
    section[data-testid="stSidebar"] {
        background: rgba(6, 10, 20, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(16, 185, 129, 0.35) !important;
    }

    /* Sol Menü Butonları */
    section[data-testid="stSidebar"] div.stButton > button {
        background: transparent !important;
        color: #94a3b8 !important;
        border: 1px solid transparent !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        padding: 10px 16px !important;
        transition: all 0.25s ease !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #f4f4f5 !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35) !important;
        transform: translateX(4px) !important;
    }

    /* Metrik Kartları ve Formlar (Neon Cam Efekti) */
    div[data-testid="stMetric"], 
    div[data-testid="stForm"], 
    div[data-testid="stExpander"] {
        background: rgba(10, 15, 29, 0.75) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        border-radius: 18px !important;
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35) !important;
    }

    /* Girdi Kutuları ve İnputlar (Koyu Mavi Zemin) */
    input, 
    div[data-baseweb="input"] > div, 
    div[data-baseweb="select"] > div {
        background-color: rgba(15, 23, 42, 0.85) !important;
        color: #f4f4f5 !important;
        border-radius: 12px !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
    }

    /* Birincil Yeşil Butonlar */
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4) !important;
    }

    /* İkincil Butonlar */
    button[data-testid="baseButton-secondary"], div.stButton > button {
        background: rgba(10, 15, 29, 0.75) !important;
        color: #f4f4f5 !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        border-radius: 12px !important;
    }

    /* HTML Özel Tablo */
    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 15px 0;
        background: rgba(10, 15, 29, 0.75);
        backdrop-filter: blur(16px);
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(16, 185, 129, 0.35);
        box-shadow: 0 0 25px -3px rgba(16, 185, 129, 0.35);
    }
    .custom-table th {
        background: rgba(6, 10, 20, 0.85);
        color: #f4f4f5 !important;
        padding: 14px 18px;
        font-size: 13px !important;
        font-weight: 700;
        border-bottom: 1px solid rgba(16, 185, 129, 0.35);
    }
    .custom-table td {
        padding: 14px 18px;
        color: #94a3b8 !important;
        font-size: 13px !important;
        border-bottom: 1px solid rgba(16, 185, 129, 0.35);
    }
</style>
""", unsafe_allow_html=True)

def yeni_id_uret(onek, liste, genislik=3, anahtar="id"):
    """Mevcut en büyük numaranın bir fazlasını üretir (kayıt silinse bile kimlik tekrarlanmaz)."""
    en_buyuk = 0
    for oge in liste:
        m = re.search(r"(\d+)$", str(oge.get(anahtar, "")))
        if m:
            en_buyuk = max(en_buyuk, int(m.group(1)))
    return f"{onek}{en_buyuk + 1:0{genislik}d}"


def idleri_benzersiz_yap(liste, onek, genislik=3, anahtar="id"):
    """Eski sürümlerde (kayıt sayısına göre üretildiği için) tekrarlanmış kimlikleri düzeltir."""
    sayac = 0
    for oge in liste:
        m = re.search(r"(\d+)$", str(oge.get(anahtar, "")))
        if m:
            sayac = max(sayac, int(m.group(1)))
    gorulen = set()
    for oge in liste:
        kid = oge.get(anahtar)
        if not kid or kid in gorulen:
            sayac += 1
            kid = f"{onek}{sayac:0{genislik}d}"
            oge[anahtar] = kid
        gorulen.add(kid)
    return liste


def silme_onay_kutusu(anahtar):
    return st.checkbox(
        "⚠️ Bu işlemin geri alınamayacağını anlıyorum, silmeyi onaylıyorum.", key=anahtar
    )


KALORI_TABLOSU = {
    "PİRİNÇ": 130,
    "BALDO PİRİNÇ": 130,
    "KURU FASULYE": 340,
    "NOHUT": 360,
    "KIRMIZI MERCİMEK": 350,
    "YEŞİL MERCİMEK": 350,
    "BULGUR": 340,
    "PİLAVLIK BULGUR": 340,
    "MAKARNA": 350,
    "BURGU MAKARNA": 350,
    "İNCE UZUN MAKARNA": 350,
    "ERİŞTE MAKARNA": 360,
    "ARPA ŞEHRİYE": 350,
    "UN": 364,
    "PATATES": 77,
    "SOĞAN": 40,
    "DOMATES": 18,
    "SALATALIK": 15,
    "BİBER": 40,
    "ÇARLİ": 40,
    "KAPYA BİBER": 31,
    "ISPANAK": 23,
    "PATLICAN": 25,
    "KABAK": 17,
    "HAVUÇ": 41,
    "LAHANA": 25,
    "KIRMIZI LAHANA": 31,
    "MAYDANOZ": 36,
    "ET": 250,
    "KUŞBAŞI ET": 250,
    "TAVUK": 165,
    "SIRTSIZ GÖĞÜS": 165,
    "YUMURTA": 155,
    "YOĞURT": 61,
    "TAM YAĞLI YOĞURT": 61,
    "SÜT": 42,
    "YAĞLI SÜT": 42,
    "TEREYAĞI": 717,
    "AYÇİÇEK YAĞI": 884,
    "TENEKE AYÇİÇEK YAĞI": 884,
    "SALÇA": 82,
    "DOMATES SALÇASI": 82,
    "ŞEKER": 387,
    "TOZ ŞEKER": 387,
    "TUZ": 0,
    "İRMİK": 360,
    "BEZELYE": 81,
    "BEZELYE KONSERVESİ": 81,
}


def urun_kalori_hesapla(urun_adi, miktar, birim):
    urun_upper = urun_adi.upper()
    birim_kalori = 100
    for k, v in KALORI_TABLOSU.items():
        if k in urun_upper:
            birim_kalori = v
            break
    carp = 1000 if birim in ["Kg", "Lt"] else 100
    return (miktar * carp * birim_kalori) / 100.0


varsayilan_personeller = [
    {
        "tc": "11111111111",
        "ad_soyad": "MUHAMMED İLKER ÇELİK",
        "gorev": "Şoför",
        "baslama": "2026-10-12",
        "aktif": True,
        "izinler": [],
    },
]

varsayilan_resmi_tatiller = [
    {"tarih": "2026-01-01", "aciklama": "Yılbaşı"},
    {
        "tarih": "2026-04-23",
        "aciklama": "Ulusal Egemenlik ve Çocuk Bayramı",
    },
    {"tarih": "2026-05-01", "aciklama": "Emek ve Dayanışma Günü"},
    {
        "tarih": "2026-05-19",
        "aciklama": "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
    },
    {"tarih": "2026-07-15", "aciklama": "Demokrasi ve Millî Birlik Günü"},
    {"tarih": "2026-08-30", "aciklama": "Zafer Bayramı"},
    {"tarih": "2026-10-29", "aciklama": "Cumhuriyet Bayramı"},
]

varsayilan_depolar = [
    "Soğuk Hava Deposu +5/+6",
    "Soğuk Hava Deposu -18",
    "Sebze Deposu",
    "Kuru Gıda Deposu"
]

varsayilan_demirbaslar = [
    {
        "id": "DEM-001",
        "ad": "Endüstriyel Çorba Kazanı",
        "kategori": "Mutfak Ekipmanı",
        "adet": 2,
        "durum": "Sağlam",
        "zimmet": "Aşçıbaşı",
        "tarih": "2026-01-15"
    }
]

misafir_yasaklar_varsayilan = [
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu",
    "Yeni Mal Alımı / Fatura Ekle",
    "Ürün Sil / Düzenle",
    "Fire / Zayiat Girişi",
    "Toplu Stok Düşümü & Sarfiyat",
    "Ürün Birim Fiyatları & Ay Analizi",
    "Günlük Yemek Üretimi & Maliyet Raporu",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
    "Kapsamlı Envanter ve Hareket Raporu",
    "Depo Yönetimi",
    "Demirbaş Yönetimi",
]
misafir_maskeler_varsayilan = [
    "1. Sayfa: Toplam Fire",
    "1. Sayfa: Stok Değeri",
    "2. Sayfa: Güncel Stok Durumu - Kalan Miktar",
    "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi",
    "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu",
]

def varsayilan_misafir_kaydi():
    return {
        "sifre": "",
        "tip": "misafir",
        "yasakli_menuler": list(misafir_yasaklar_varsayilan),
        "maskeli_alanlar": list(misafir_maskeler_varsayilan),
        "salt_okunur": True,
        "buton_metni": "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)",
        "buton_aktif": True,
    }


def varsayilan_kullanicilar_olustur():
    """İlk kurulumda kullanıcıları oluşturur. Kodda sabit şifre YOKTUR:
    şifre `secrets` içinde (ADMIN_INITIAL_PASSWORD vb.) verilmişse o kullanılır,
    verilmemişse rastgele üretilir, giriş ekranında BİR KEZ gösterilir ve ilk girişte
    değiştirilmesi zorunlu tutulur."""
    kayit = {}
    uretilenler = {}
    for ad, tip, salt_okunur, secret_adi in (
        ("admin", "admin", False, "ADMIN_INITIAL_PASSWORD"),
        ("asci", "personel", False, "ASCI_INITIAL_PASSWORD"),
        ("yonetim", "personel", True, "YONETIM_INITIAL_PASSWORD"),
    ):
        try:
            sifre = str(st.secrets.get(secret_adi, "") or "")
        except Exception:
            sifre = ""
        rastgele = not sifre
        if rastgele:
            sifre = secrets.token_urlsafe(9)
            uretilenler[ad] = sifre
        kayit[ad] = {
            "sifre": sifre_hashle_yeni(sifre),
            "tip": tip,
            "yasakli_menuler": [],
            "maskeli_alanlar": [],
            "salt_okunur": salt_okunur,
        }
        if rastgele:
            kayit[ad]["sifre_degistirilmeli"] = True
    kayit["misafir"] = varsayilan_misafir_kaydi()
    if uretilenler:
        st.session_state["ilk_kurulum_sifreleri"] = uretilenler
    return kayit


varsayilan_widgets = [
    {
        "id": "w1",
        "baslik": "Kategori Bazlı Stok Dağılımı (Sütun Grafik)",
        "tur": "Sütun Grafik",
        "aktif": True,
    },
    {
        "id": "w2",
        "baslik": "Aylık Fire ve Zayiat Trendi (Çizgi Grafik)",
        "tur": "Çizgi Grafik",
        "aktif": True,
    },
]


def widgetlari_yukle():
    return supabase_veri_oku("dashboard_widgets", varsayilan_widgets)


def widgetlari_kaydet(veri):
    supabase_veri_kaydet("dashboard_widgets", veri)


def depoları_yukle():
    return supabase_veri_oku("depolar_listesi", varsayilan_depolar)


def depoları_kaydet(veri):
    supabase_veri_kaydet("depolar_listesi", veri)


def demirbasları_yukle():
    return supabase_veri_oku("demirbaslar_listesi", varsayilan_demirbaslar)


def demirbasları_kaydet(veri):
    supabase_veri_kaydet("demirbaslar_listesi", veri)


def kritik_seviyeleri_yukle():
    return supabase_veri_oku("kritik_seviyeler", {})


def kritik_seviyeleri_kaydet(veri):
    supabase_veri_kaydet("kritik_seviyeler", veri)


def kullanıcıları_yukle():
    data = supabase_veri_oku("kullanici_yetkileri", None)
    ilk_kurulum = (not isinstance(data, dict)) or (not data)
    if ilk_kurulum:
        data = varsayilan_kullanicilar_olustur()
    for k, v in data.items():
        if "yasakli_menuler" not in v:
            v["yasakli_menuler"] = []
        if "maskeli_alanlar" not in v:
            v["maskeli_alanlar"] = []
        if "salt_okunur" not in v:
            v["salt_okunur"] = (k in ["yonetim", "misafir"])
        elif k in ["yonetim", "misafir"]:
            v["salt_okunur"] = True

        if k == "misafir":
            if not v["yasakli_menuler"]:
                v["yasakli_menuler"] = misafir_yasaklar_varsayilan
            if not v["maskeli_alanlar"]:
                v["maskeli_alanlar"] = misafir_maskeler_varsayilan

        # Düz metin gelen şifre (eski sürümlerden kalma) yeni biçimde hash'lenir.
        sifre_deger = v.get("sifre", "")
        if (
            sifre_deger
            and k != "misafir"
            and not str(sifre_deger).startswith("s1$")
            and len(str(sifre_deger)) != 64
        ):
            v["sifre"] = sifre_hashle_yeni(sifre_deger)

    if "misafir" not in data:
        data["misafir"] = varsayilan_misafir_kaydi()
    else:
        if "buton_metni" not in data["misafir"]:
            data["misafir"]["buton_metni"] = "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)"
        if "buton_aktif" not in data["misafir"]:
            data["misafir"]["buton_aktif"] = True
        if not data["misafir"]["yasakli_menuler"]:
            data["misafir"]["yasakli_menuler"] = misafir_yasaklar_varsayilan
        if not data["misafir"]["maskeli_alanlar"]:
            data["misafir"]["maskeli_alanlar"] = misafir_maskeler_varsayilan

    if ilk_kurulum:
        kullanıcıları_kaydet(data)
    return data


def kullanıcıları_kaydet(veri):
    supabase_veri_kaydet("kullanici_yetkileri", veri)


def verileri_yukle():
    return supabase_veri_oku("girisler", [])


def verileri_kaydet(veri):
    supabase_veri_kaydet("girisler", veri)


def loglari_yukle():
    return supabase_veri_oku("kullanim_loglari", [])


def loglari_kaydet(veri):
    supabase_veri_kaydet("kullanim_loglari", veri)


def silinen_urun_loglarini_yukle():
    return supabase_veri_oku("silinen_urun_loglari", [])


def silinen_urun_loglarini_kaydet(veri):
    supabase_veri_kaydet("silinen_urun_loglari", veri)


def ihtiyac_sahiplerini_yukle():
    ham_veri = supabase_veri_oku("ihtiyac_sahipleri", [])
    cozulmus_liste = []
    for k in ham_veri:
        k_kopya = k.copy()
        h_tc = k.get("tc_hane", "")
        h_tel = k.get("telefon", "")
        h_adr = k.get("adres", "")
        
        k_kopya["tc_hane"] = metni_coz(h_tc) if h_tc else ""
        k_kopya["telefon"] = metni_coz(h_tel) if h_tel else ""
        k_kopya["adres"] = metni_coz(h_adr) if h_adr else ""
        if "aktif" not in k_kopya:
            k_kopya["aktif"] = True
        cozulmus_liste.append(k_kopya)
    return cozulmus_liste


def ihtiyac_sahiplerini_kaydet(veri_listesi):
    try:
        sifrelenmis_liste = []
        for k in veri_listesi:
            k_kopya = k.copy()
            k_kopya["tc_hane"] = metni_sifrele(k.get("tc_hane", ""))
            k_kopya["telefon"] = metni_sifrele(k.get("telefon", ""))
            k_kopya["adres"] = metni_sifrele(k.get("adres", ""))
            sifrelenmis_liste.append(k_kopya)
    except SifrelemeHatasi as e:
        st.error(
            f"⚠️ **Kayıt YAPILMADI — hassas veri korunamadı.** {e} "
            "Fernet anahtarını ve sunucu durumunu kontrol edip tekrar deneyin. "
            "Hassas alanlar şifrelenmeden veritabanına yazılmaz."
        )
        st.stop()
    supabase_veri_kaydet("ihtiyac_sahipleri", sifrelenmis_liste)


def dagitim_loglarini_yukle():
    return supabase_veri_oku("dagitim_loglari", [])


def dagitim_loglarini_kaydet(veri):
    supabase_veri_kaydet("dagitim_loglari", veri)


def personelleri_yukle():
    ham_veri = supabase_veri_oku("personeller", varsayilan_personeller)
    cozulmus_p = []
    for p in ham_veri:
        p_kopya = p.copy()
        h_tc = p.get("tc", "")
        p_kopya["tc"] = metni_coz(h_tc) if h_tc else ""
        cozulmus_p.append(p_kopya)
    return cozulmus_p


def personelleri_kaydet(veri_listesi):
    try:
        sifrelenmis_p = []
        for p in veri_listesi:
            p_kopya = p.copy()
            p_kopya["tc"] = metni_sifrele(p.get("tc", ""))
            sifrelenmis_p.append(p_kopya)
    except SifrelemeHatasi as e:
        st.error(
            f"⚠️ **Kayıt YAPILMADI — hassas veri korunamadı.** {e} "
            "Fernet anahtarını kontrol edip tekrar deneyin."
        )
        st.stop()
    supabase_veri_kaydet("personeller", sifrelenmis_p)


def personel_izinlerini_yukle():
    veri = supabase_veri_oku("personel_izinleri", [])
    return veri if isinstance(veri, list) else []


def personel_izinlerini_kaydet(veri_listesi):
    supabase_veri_kaydet("personel_izinleri", veri_listesi)


# Eski modelde izinler her personelin içinde (personeller[].izinler) tutuluyordu.
_ESKI_IZIN_TURU_ESLEME = {
    "Yıllık İzin": "Yıllık İzin",
    "Sağlık Raporu": "Hastalık / Rapor",
    "Saatlik İzin": "Mazeret İzni",
}


def eski_izinleri_tasi():
    """Eski biçimdeki (personeller[].izinler) kayıtları yeni listeye (personel_izinleri) aktarır.
    Tekrar çalıştırılırsa aynı kaydı ikinci kez eklemez; aktarılan eski kayıtlar silinmez, boşaltılır."""
    mevcut = st.session_state.personel_izinleri
    anahtarlar = {
        (i.get("personel_ad"), i.get("izin_turu"), i.get("baslangic"), i.get("bitis"), i.get("aciklama"))
        for i in mevcut if i.get("kaynak") == "eski_kayit"
    }
    degisti = False
    for p in st.session_state.personeller:
        eskiler = p.get("izinler") or []
        if not eskiler:
            continue
        ad = p.get("ad_soyad", p.get("ad", p.get("isim", "-")))
        for iz in eskiler:
            eski_tur = iz.get("tur", "Yıllık İzin")
            tur = _ESKI_IZIN_TURU_ESLEME.get(eski_tur, "Resmi Görev / Diğer")
            bas = str(iz.get("baslangic", ""))
            bit = str(iz.get("bitis", bas))
            try:
                gun = (datetime.date.fromisoformat(bit) - datetime.date.fromisoformat(bas)).days + 1
            except Exception:
                gun = 0
            kayit_saat = None
            if eski_tur == "Saatlik İzin":
                # Yeni modelde saatlik izin yok: gün sayısı 0 tutulur, süre açıklamada saklanır.
                kayit_saat = iz.get("saat", 0)
                gun = 0
                aciklama = f"Saatlik izin: {kayit_saat} saat ({iz.get('detay', '-')})"
            else:
                aciklama = str(iz.get("detay") or "Eski sistemden aktarıldı")
            anahtar = (ad, tur, bas, bit, aciklama)
            if anahtar in anahtarlar:
                continue
            yeni = {
                "id": yeni_id_uret("IZN-", mevcut),
                "personel_ad": ad,
                "izin_turu": tur,
                "baslangic": bas,
                "bitis": bit,
                "gun_sayisi": max(gun, 0),
                "aciklama": aciklama,
                "ekleme_tarihi": simdi_tr_str("%Y-%m-%d %H:%M"),
                "kaynak": "eski_kayit",
            }
            if kayit_saat is not None:
                yeni["saat"] = kayit_saat
            mevcut.append(yeni)
            anahtarlar.add(anahtar)
        p["izinler"] = []
        degisti = True
    if degisti:
        personel_izinlerini_kaydet(mevcut)   # önce yeni liste, sonra eski kayıtların boşaltılması
        personelleri_kaydet(st.session_state.personeller)


def resmi_tatilleri_yukle():
    return supabase_veri_oku("resmi_tatiller", varsayilan_resmi_tatiller)


def yemek_uretim_arsivini_yukle():
    return supabase_veri_oku("yemek_uretim_arsivi", [])


def yemek_uretim_arsivini_kaydet(veri):
    supabase_veri_kaydet("yemek_uretim_arsivi", veri)


if "girisler" not in st.session_state:
    st.session_state.girisler = idleri_benzersiz_yap(verileri_yukle(), "FAT-")
if "kullanim_loglari" not in st.session_state:
    st.session_state.kullanim_loglari = loglari_yukle()
if "silinen_urun_loglari" not in st.session_state:
    st.session_state.silinen_urun_loglari = silinen_urun_loglarini_yukle()
if "ihtiyac_sahipleri" not in st.session_state:
    st.session_state.ihtiyac_sahipleri = idleri_benzersiz_yap(ihtiyac_sahiplerini_yukle(), "IHT-")
if "dagitim_loglari" not in st.session_state:
    st.session_state.dagitim_loglari = idleri_benzersiz_yap(dagitim_loglarini_yukle(), "DAG-")
if "personeller" not in st.session_state:
    st.session_state.personeller = idleri_benzersiz_yap(personelleri_yukle(), "PER-")
if "personel_izinleri" not in st.session_state:
    st.session_state.personel_izinleri = idleri_benzersiz_yap(personel_izinlerini_yukle(), "IZN-")
    eski_izinleri_tasi()
if "resmi_tatiller" not in st.session_state:
    st.session_state.resmi_tatiller = resmi_tatilleri_yukle()
if "yemek_uretim_arsivi" not in st.session_state:
    st.session_state.yemek_uretim_arsivi = yemek_uretim_arsivini_yukle()
if "depolar" not in st.session_state:
    st.session_state.depolar = depoları_yukle()
if "demirbaslar" not in st.session_state:
    st.session_state.demirbaslar = idleri_benzersiz_yap(demirbasları_yukle(), "DEM-")
if "kritik_seviyeler" not in st.session_state:
    st.session_state.kritik_seviyeler = kritik_seviyeleri_yukle()
if "kalori_sepeti" not in st.session_state:
    st.session_state.kalori_sepeti = []
if "personel_silme_mesaji" not in st.session_state:
    st.session_state.personel_silme_mesaji = ""
if "dagitim_silme_mesaji" not in st.session_state:
    st.session_state.dagitim_silme_mesaji = ""
if "kullanicilar" not in st.session_state:
    st.session_state.kullanicilar = kullanıcıları_yukle()
if "dashboard_widgets" not in st.session_state:
    st.session_state.dashboard_widgets = widgetlari_yukle()

if "hatali_giris_sayisi" not in st.session_state:
    st.session_state.hatali_giris_sayisi = 0
if "kilitlenme_bitis_zamani" not in st.session_state:
    st.session_state.kilitlenme_bitis_zamani = 0

query_params = st.query_params

# Eski, güvensiz parametreleri URL'den temizle
for _eski in ("auth", "user"):
    if _eski in query_params:
        del query_params[_eski]

if "oturum_aktif" not in st.session_state:
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
# Eski sürümden kalan oturumlarda eksik anahtarları tamamla
for _anahtar, _deger in (("oturum_token", ""), ("oturum_bitis", 0)):
    if _anahtar not in st.session_state:
        st.session_state[_anahtar] = _deger

# Giriş yapılmamışsa: çerezdeki (çerez desteği yoksa adresteki) token ile oturumu geri yüklemeyi dene
if not st.session_state.oturum_aktif:
    if cerez_kontrol is not None:
        aday_token = cerez_oku()
        if "token" in query_params:
            del query_params["token"]
    else:
        aday_token = str(query_params.get("token", ""))
    if aday_token:
        kayit = oturum_dogrula(aday_token)
        if kayit and kayit.get("kullanici") in st.session_state.kullanicilar:
            st.session_state.oturum_aktif = True
            st.session_state.aktif_kullanici = kayit["kullanici"]
            st.session_state.oturum_token = aday_token
            st.session_state.oturum_bitis = kayit["bitis"]
            st.session_state["son_etkinlik"] = time.time()
            st.session_state["_oturum_son_dogrulama"] = time.time()
        elif cerez_kontrol is None:
            if "token" in query_params:
                del query_params["token"]
        elif not st.session_state.get("_cerez_temizlendi"):
            cerez_sil()  # geçersiz/eski çerezi bir kez temizle
            st.session_state["_cerez_temizlendi"] = True

# Her çalışmada: token'sız (eski), süresi dolmuş veya kullanıcısı silinmiş oturumu kapat
if st.session_state.oturum_aktif and (
    not st.session_state.oturum_token
    or st.session_state.aktif_kullanici not in st.session_state.kullanicilar
    or time.time() > st.session_state.oturum_bitis
):
    oturum_sil(st.session_state.oturum_token)
    st.session_state.oturum_aktif = False
    st.session_state.aktif_kullanici = "misafir"
    st.session_state.oturum_token = ""
    if "token" in st.query_params:
        del st.query_params["token"]

# Boşta kalma: Streamlit yalnızca kullanıcı işlem yapınca çalıştığı için, her çalışma bir etkinliktir.
if st.session_state.oturum_aktif:
    _simdi = time.time()
    if _simdi - st.session_state.get("son_etkinlik", _simdi) > bosta_kalma_suresi_sn():
        oturumu_zorla_kapat(
            "Uzun süre işlem yapılmadığı için oturumunuz güvenlik nedeniyle kapatıldı. Lütfen yeniden giriş yapın.",
            "boşta kalma nedeniyle oturum kapandı",
        )
    else:
        st.session_state["son_etkinlik"] = _simdi

# Açık oturumu belirli aralıkla veritabanından yeniden doğrula ve kullanıcı yetkilerini tazele:
# silinen/şifresi değişen/yetkisi kısıtlanan kullanıcı 8 saat beklemeden en geç 1 dk içinde etkilenir.
# Geçici veritabanı hatasında oturum AÇIK bırakılır (ağ kesintisi herkesi dışarı atmasın).
if st.session_state.oturum_aktif and SUPABASE_URL and SUPABASE_KEY:
    _simdi = time.time()
    if _simdi - st.session_state.get("_oturum_son_dogrulama", 0) > OTURUM_DOGRULAMA_ARALIGI_SN:
        st.session_state["_oturum_son_dogrulama"] = _simdi
        _d, _oturumlar = _supabase_ham_oku("aktif_oturumlar")
        if _d in ("ok", "yok"):
            _kayit = (_oturumlar or {}).get(_token_hashle(st.session_state.oturum_token)) if isinstance(_oturumlar, dict) else None
            if not _kayit or _kayit.get("bitis", 0) <= _simdi:
                oturumu_zorla_kapat(
                    "Oturumunuz sonlandırıldı (başka bir yerden kapatıldı, şifreniz değişti veya süre doldu). Lütfen yeniden giriş yapın.",
                    "oturum sunucuda geçersiz, kapatıldı",
                )
        if st.session_state.oturum_aktif:
            _kd, _ = _supabase_ham_oku("kullanici_yetkileri")
            if _kd == "ok":
                st.session_state.kullanicilar = kullanıcıları_yukle()
                if st.session_state.aktif_kullanici not in st.session_state.kullanicilar:
                    oturumu_zorla_kapat("Hesabınız bulunamadı. Lütfen yöneticiyle iletişime geçin.", "hesap silinmiş, oturum kapandı")

gecerli_menuler = [
    "Kurumsal Dashboard & Özet",
    "Güncel Stok Durumu",
    "Yeni Mal Alımı / Fatura Ekle",
    "Ürün Sil / Düzenle",
    "Fire / Zayiat Girişi",
    "Toplu Stok Düşümü & Sarfiyat",
    "Ürün Birim Fiyatları & Ay Analizi",
    "Günlük Yemek Üretimi & Maliyet Raporu",
    "Kalori Hesaplama Aracı",
    "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
    "Personel & Çalışma Süresi Takibi",
    "Kullanım Takibi",
    "Kapsamlı Envanter ve Hareket Raporu",
    "Depo Yönetimi",
    "Demirbaş Yönetimi",
    "Kullanıcı Ayarları",
]

if "aktif_menu" not in st.session_state:
    if "menu" in query_params and query_params["menu"] in gecerli_menuler:
        st.session_state.aktif_menu = query_params["menu"]
    else:
        st.session_state.aktif_menu = "Kurumsal Dashboard & Özet"

if "silme_mesaji" not in st.session_state:
    st.session_state.silme_mesaji = ""
if "kisi_silme_mesaji" not in st.session_state:
    st.session_state.kisi_silme_mesaji = ""


def net_calisma_gunu_hesapla(
    baslangic_tarihi, bitis_tarihi, izin_listesi, tatil_listesi
):
    if baslangic_tarihi > bitis_tarihi:
        return 0, 0, 0, 0
    tatil_tarihleri = {
        datetime.datetime.strptime(t["tarih"], "%Y-%m-%d").date()
        for t in tatil_listesi
    }
    tam_gun_izin_tarihleri = set()
    saglik_raporu_gun_sayisi = 0
    saatlik_izin_toplam_saat = 0.0

    for izin in izin_listesi:
        tur = izin.get("tur", "Yıllık İzin")
        i_bas = datetime.datetime.strptime(izin["baslangic"], "%Y-%m-%d").date()
        i_bit = datetime.datetime.strptime(izin["bitis"], "%Y-%m-%d").date()
        if tur == "Saatlik İzin":
            saatlik_izin_toplam_saat += float(izin.get("saat", 2.0))
        elif tur == "Sağlık Raporu":
            curr = i_bas
            while curr <= i_bit:
                if curr.weekday() < 5 and curr not in tatil_tarihleri:
                    saglik_raporu_gun_sayisi += 1
                curr += datetime.timedelta(days=1)
        else:
            curr = i_bas
            while curr <= i_bit:
                tam_gun_izin_tarihleri.add(curr)
                curr += datetime.timedelta(days=1)

    net_gun = 0
    toplam_izin_gunu = len(tam_gun_izin_tarihleri)
    curr = baslangic_tarihi
    while curr <= bitis_tarihi:
        hafta_sonu = curr.weekday() >= 5
        resmi_tatil = curr in tatil_tarihleri
        izinli = curr in tam_gun_izin_tarihleri
        if not hafta_sonu and not resmi_tatil and not izinli:
            net_gun += 1
        curr += datetime.timedelta(days=1)
    return net_gun, toplam_izin_gunu, saglik_raporu_gun_sayisi, saatlik_izin_toplam_saat


def bugunun_turkce_tarihi():
    simdi = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")).date() if hasattr(datetime, "datetime") else datetime.date.today()
    aylar = {
        1: "Ocak",
        2: "Şubat",
        3: "Mart",
        4: "Nisan",
        5: "Mayıs",
        6: "Haziran",
        7: "Temmuz",
        8: "Ağustos",
        9: "Eylül",
        10: "Ekim",
        11: "Kasım",
        12: "Aralık",
    }
    gunler = {
        0: "Pazartesi",
        1: "Salı",
        2: "Çarşamba",
        3: "Perşembe",
        4: "Cuma",
        5: "Cumartesi",
        6: "Pazar",
    }
    return f"{simdi.day} {aylar.get(simdi.month, '')} {simdi.year}, {gunler.get(simdi.weekday(), '')}"


# =========================================================================
# GİRİŞ KONTROLÜ / AÇILIŞ GİRİŞ EKRANI
# =========================================================================
if not st.session_state.oturum_aktif:
    st.markdown(
        "<div style='text-align: center; margin-top: 40px;'></div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.3, 1])
    with c2:
        st.markdown(
            f"""
                <div style="text-align: center; margin-bottom: 28px; background: {card_bg}; border: 1px solid {border_color}; padding: 32px; border-radius: 20px; box-shadow: 0 16px 40px rgba(0,0,0,0.08);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🍲</div>
                    <h2 style="font-weight: 700; letter-spacing: -0.03em; margin: 0; color: {text_color};">AZİZİYE AŞEVİ</h2>
                    <p style="opacity: 0.6; font-size: 13.5px; margin-top: 6px; color: {subtext_color};">Yönetim & Takip Sistemi</p>
                </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("oturum_mesaji"):
            st.warning(st.session_state.pop("oturum_mesaji"))

        if st.session_state.get("ilk_kurulum_sifreleri"):
            _satirlar = "\n".join(
                f"- **{ad}** → `{sf}`" for ad, sf in st.session_state["ilk_kurulum_sifreleri"].items()
            )
            st.warning(
                "🔑 **İlk kurulum şifreleri** (yalnızca burada, bir kez gösterilir; şimdi not edin). "
                "İlk girişte yeni şifre belirlemeniz istenecek:\n\n" + _satirlar
            )

        simdikiekran_zaman = time.time()
        kilitli_mi = st.session_state.kilitlenme_bitis_zamani > simdikiekran_zaman

        if kilitli_mi:
            kalan_sure = int(st.session_state.kilitlenme_bitis_zamani - simdikiekran_zaman)
            st.error(f"⚠️ Çok fazla hatalı giriş yaptınız! Güvenlik nedeniyle girişler {kalan_sure} saniye süreyle kilitlendi.")
        else:
            with st.form("merkezi_giris_formu"):
                st.markdown("**Kullanıcı Adı**")
                k_adi_inp = st.text_input(
                    "Kullanıcı Adı",
                    placeholder="Kullanıcı adı giriniz...",
                    label_visibility="collapsed",
                ).strip().lower()
                st.markdown("**Şifre**")
                sifre_inp = st.text_input(
                    "Şifre",
                    type="password",
                    placeholder="Şifre giriniz...",
                    label_visibility="collapsed",
                )

                giris_tikla = st.form_submit_button(
                    "Giriş Yap", use_container_width=True
                )

                if giris_tikla:
                    kullanici_db = st.session_state.kullanicilar
                    istemci_ip, _xff = istemci_ip_bilgisi()
                    kullanici_var = k_adi_inp in kullanici_db
                    log_adi = k_adi_inp if kullanici_var else "(bilinmeyen kullanıcı)"
                    u_anahtar = f"u|{k_adi_inp if kullanici_var else '_bilinmeyen'}|{istemci_ip}"
                    ip_anahtar = f"ip|{istemci_ip}"
                    kalan_kilit = max(giris_kilit_kalan(u_anahtar), giris_kilit_kalan(ip_anahtar))

                    if kalan_kilit > 0:
                        giris_logla(log_adi, "kilitliyken deneme")
                        st.error(f"⚠️ Çok fazla hatalı deneme. Lütfen {kalan_kilit} saniye sonra tekrar deneyin.")
                    else:
                        kayitli_hash = str(kullanici_db.get(k_adi_inp, {}).get("sifre", ""))
                        if kullanici_var:
                            gecerli = (kayitli_hash != "" or k_adi_inp == "misafir") and sifre_dogrula(sifre_inp, kayitli_hash)
                        else:
                            sifre_dogrula(sifre_inp, sifre_hashle_yeni("sahte"))
                            gecerli = False

                        if gecerli:
                            if sifre_yukseltilmeli_mi(kayitli_hash):
                                if kayitli_hash in ESKI_VARSAYILAN_HASHLER:
                                    kullanici_db[k_adi_inp]["sifre_degistirilmeli"] = True
                                kullanici_db[k_adi_inp]["sifre"] = sifre_hashle_yeni(sifre_inp)
                                kullanıcıları_kaydet(kullanici_db)
                            st.session_state.hatali_giris_sayisi = 0
                            giris_denemesini_sifirla(u_anahtar)
                            giris_logla(k_adi_inp, "başarılı giriş")
                            oturumu_baslat(k_adi_inp)
                            st.rerun()
                        else:
                            kalan_hak, kilit_u = hatali_giris_kaydet(u_anahtar, MAKS_HATALI_GIRIS, KILIT_SURESI_SN)
                            if istemci_ip and istemci_ip != "bilinmiyor":
                                _, kilit_ip = hatali_giris_kaydet(ip_anahtar, IP_MAKS_HATALI_GIRIS, IP_KILIT_SURESI_SN)
                            else:
                                kilit_ip = False
                            giris_logla(log_adi, "hatalı giriş")
                            st.session_state.hatali_giris_sayisi += 1
                            if kilit_u or kilit_ip:
                                st.session_state.kilitlenme_bitis_zamani = time.time() + KILIT_SURESI_SN
                                st.session_state.hatali_giris_sayisi = 0
                                st.rerun()
                            else:
                                st.error(f"Hatalı kullanıcı adı veya şifre! Kalan deneme hakkı: {max(kalan_hak, 0)}")
            
        st.markdown(
            f"<div style='text-align: center; margin: 16px 0; opacity: 0.4; font-size: 13px; color: {subtext_color};'>veya</div>",
            unsafe_allow_html=True,
        )

        misafir_ayar = st.session_state.kullanicilar.get("misafir", {})
        misafir_buton_metni = misafir_ayar.get("buton_metni", "👁️ Misafir Girişi İçin Tıklayın (Gözlemci)")
        misafir_buton_aktif = misafir_ayar.get("buton_aktif", True)

        if misafir_buton_aktif:
            if st.button(
                misafir_buton_metni,
                use_container_width=True,
                type="secondary",
            ):
                giris_logla("misafir", "misafir girişi")
                oturumu_baslat("misafir")
                st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        with st.expander("🔑 Admin Şifre Kurtarma (Master Key)"):
            tanimli_master = str(st.secrets.get("MASTER_RECOVERY_KEY", "") or "")
            if not tanimli_master:
                st.info(
                    "Şifre kurtarma devre dışı. Etkinleştirmek için `secrets` ayarlarına "
                    "güçlü bir `MASTER_RECOVERY_KEY` ekleyin. Eklediğiniz hâlde bu mesajı görüyorsanız "
                    "secrets'a `TANI_MODU = \"1\"` ekleyip adres sonuna `?tani=1` yazarak Bağlantı Tanılama sayfasına bakın."
                )
            else:
                with st.form("master_key_sifre_sifirla"):
                    st.markdown("Şifrenizi unuttuysanız kurtarma anahtarı ile admin için geçici bir şifre üretebilirsiniz.")
                    master_key_inp = st.text_input("Kurtarma Anahtarı (Master Recovery Key)", type="password")
                    sifirla_btn = st.form_submit_button("Admin Şifresini Sıfırla")

                    if sifirla_btn:
                        m_ip, _ = istemci_ip_bilgisi()
                        m_anahtar = f"master|{m_ip}"
                        m_kalan = giris_kilit_kalan(m_anahtar)
                        if m_kalan > 0:
                            st.error(f"⚠️ Çok fazla hatalı deneme. {m_kalan} saniye sonra tekrar deneyin.")
                        elif hmac.compare_digest(master_key_inp.encode("utf-8"), tanimli_master.encode("utf-8")):
                            if "admin" in st.session_state.kullanicilar:
                                gecici_sifre = secrets.token_urlsafe(10)
                                st.session_state.kullanicilar["admin"]["sifre"] = sifre_hashle_yeni(gecici_sifre)
                                st.session_state.kullanicilar["admin"]["sifre_degistirilmeli"] = True
                                kullanıcıları_kaydet(st.session_state.kullanicilar)
                                kullanici_oturumlarini_kapat("admin")
                                giris_denemesini_sifirla()
                                giris_logla("admin", "şifre master key ile sıfırlandı")
                                st.success("Admin için geçici şifre üretildi. Şimdi not edin; girişte değiştirmeniz istenecek:")
                                st.code(gecici_sifre)
                            else:
                                st.error("Admin kullanıcısı veritabanında bulunamadı.")
                        else:
                            hatali_giris_kaydet(m_anahtar, 5, 120)
                            giris_logla("(master key)", "hatalı kurtarma anahtarı")
                            st.error("Hatalı Kurtarma Anahtarı!")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button(
            "✉️ İletişim / Destek", use_container_width=True, type="secondary"
        ):
            st.info("📩 İletişim için **sefaunaltopcu@gmail.com** mail adresi ile iletişime geçebilirsiniz.")

    st.stop()

# =========================================================================
# ZORUNLU ŞİFRE DEĞİŞİMİ (ilk kurulum / eski varsayılan şifre / sıfırlanmış şifre)
# =========================================================================
_aktif_kb = st.session_state.kullanicilar.get(st.session_state.aktif_kullanici, {})
if st.session_state.aktif_kullanici != "misafir" and (
    _aktif_kb.get("sifre_degistirilmeli") or _aktif_kb.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
):
    _z1, _z2, _z3 = st.columns([1, 1.6, 1])
    with _z2:
        st.markdown("### 🔐 Şifrenizi değiştirmeniz gerekiyor")
        st.info(
            "Güvenlik nedeniyle devam etmeden önce yeni bir şifre belirlemelisiniz "
            "(en az 10 karakter, en az bir harf ve bir rakam)."
        )
        with st.form("zorunlu_sifre_formu"):
            z_yeni1 = st.text_input("Yeni Şifre", type="password")
            z_yeni2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
            z_kaydet = st.form_submit_button("Şifreyi Kaydet", use_container_width=True)
            if z_kaydet:
                z_hata = sifre_politika_hatasi(z_yeni1)
                if z_hata:
                    st.error(z_hata)
                elif z_yeni1 != z_yeni2:
                    st.error("Şifreler aynı değil.")
                elif sifre_dogrula(z_yeni1, _aktif_kb.get("sifre", "")):
                    st.error("Yeni şifre eskisiyle aynı olamaz.")
                else:
                    sifre_degistir(
                        st.session_state.aktif_kullanici, z_yeni1,
                        haric_token=st.session_state.oturum_token,
                    )
                    st.success("Şifreniz güncellendi.")
                    st.rerun()
        if st.button("Oturumu Kapat", key="zorunlu_cikis_btn"):
            oturumu_kapat()
            st.rerun()
    st.stop()

# =========================================================================
# ANA UYGULAMA İÇERİĞİ
# =========================================================================
st.markdown("### 🍲 AZİZİYE - AŞEVİ TAKİP EKRANI ")
st.markdown(f"**Hoş geldiniz** &nbsp;|&nbsp; 📅 {bugunun_turkce_tarihi()}")
st.markdown("---")

kullanici_adi_goruntule = (
    st.session_state.aktif_kullanici.upper()
    if st.session_state.oturum_aktif
    else "MİSAFİR"
)
kullanici_adi_goruntule = html_escape(kullanici_adi_goruntule)

st.sidebar.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 12px; padding: 12px 8px 18px 8px; border-bottom: 1px solid {border_color}; margin-bottom: 12px;">
        <div style="background: rgba(99, 102, 241, 0.1); color: {text_color}; width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; border: 1px solid {border_color}; backdrop-filter: blur(12px);">
            🍲
        </div>
        <div>
            <div style="font-weight: 700; font-size: 15px; color: {text_color}; letter-spacing: -0.02em;">AZİZİYE AŞEVİ</div>
            <div style="font-size: 11px; color: {subtext_color}; font-weight: 500;">Yönetim & Takip Sistemi</div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f"""
    <div style="background: transparent; padding: 6px 8px; display: flex; align-items: center; justify-content: space-between; margin-top: 12px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <div style="background: rgba(99, 102, 241, 0.12); color: {text_color}; width: 32px; height: 32px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 13px; border: 1px solid {border_color};">
                {kullanici_adi_goruntule[:1]}
            </div>
            <div>
                <div style="font-weight: 600; font-size: 13.5px; color: {text_color};">{kullanici_adi_goruntule}</div>
                <div style="font-size: 11px; color: {subtext_color};">Aktif Oturum</div>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

sidebar_arama = st.sidebar.text_input(
    "🔍 Hızlı Arama",
    placeholder="Öğe veya log ara...",
    label_visibility="collapsed",
).strip().lower()

otomatik_yonlendirilen_menu = None
if sidebar_arama:
    urun_veya_fatura_bulundu = any(
        sidebar_arama in g.get("urun", "").lower()
        or sidebar_arama in g.get("fatura_no", "").lower()
        for g in st.session_state.girisler
    )
    if urun_veya_fatura_bulundu:
        otomatik_yonlendirilen_menu = "Güncel Stok Durumu"

    personel_bulundu = any(
        sidebar_arama in p.get("ad_soyad", "").lower()
        or sidebar_arama in p.get("tc", "")
        for p in st.session_state.personeller
    )
    if personel_bulundu:
        otomatik_yonlendirilen_menu = "Personel & Çalışma Süresi Takibi"

    ihtiyac_sahibi_bulundu = any(
        sidebar_arama in i.get("ad_soyad", "").lower()
        or sidebar_arama in i.get("tc_hane", "")
        for i in st.session_state.ihtiyac_sahipleri
    )
    if ihtiyac_sahibi_bulundu:
        otomatik_yonlendirilen_menu = "İhtiyaç Sahibi & Yemek Dağıtım Takibi"

    if otomatik_yonlendirilen_menu:
        st.session_state.aktif_menu = otomatik_yonlendirilen_menu
        st.query_params["menu"] = otomatik_yonlendirilen_menu

st.sidebar.markdown(
    f'<p style="font-size: 11px; font-weight: 700; margin-top: 12px; margin-bottom: 8px; padding-left: 4px; opacity: 0.6; text-transform: uppercase; letter-spacing: 0.05em; color: {subtext_color};">ÇALIŞMA ALANI NAVİGASYONU</p>',
    unsafe_allow_html=True,
)

yonetici_modu = (
    st.session_state.oturum_aktif
    and st.session_state.aktif_kullanici == "admin"
)
misafir_modu = (
    not st.session_state.oturum_aktif
    or st.session_state.aktif_kullanici == "misafir"
)

aktif_k_bilgi = st.session_state.kullanicilar.get(
    st.session_state.aktif_kullanici, {}
)
kullanici_salt_okunur_mu = aktif_k_bilgi.get("salt_okunur", False) or st.session_state.aktif_kullanici in ["yonetim", "misafir"]

yonetim_modu = (
    st.session_state.oturum_aktif
    and kullanici_salt_okunur_mu
)
salt_okunur_modu = misafir_modu or yonetim_modu

yasakli_menuler_listesi = aktif_k_bilgi.get("yasakli_menuler", [])
aktif_k_maskeleri = aktif_k_bilgi.get("maskeli_alanlar", [])

toplam_aktif_stok_sayisi = len(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
aktif_personel_sayisi = sum(
    1 for p in st.session_state.personeller if p.get("aktif", True)
)

menu_gruplari = {
    "🏠 Genel Bakış": [("Kurumsal Dashboard & Özet", "")],
    "📦 Depo & Stok Yönetimi": [
        ("Güncel Stok Durumu", str(toplam_aktif_stok_sayisi)),
        ("Yeni Mal Alımı / Fatura Ekle", ""),
        ("Ürün Sil / Düzenle", ""),
        ("Fire / Zayiat Girişi", ""),
        ("Toplu Stok Düşümü & Sarfiyat", ""),
        ("Ürün Birim Fiyatları & Ay Analizi", ""),
        ("Depo Yönetimi", str(len(st.session_state.depolar))),
        ("Demirbaş Yönetimi", str(len(st.session_state.demirbaslar))),
    ],
    "🍲 Üretim & Mutfak": [
        ("Günlük Yemek Üretimi & Maliyet Raporu", ""),
        ("Kalori Hesaplama Aracı", ""),
    ],
    "👥 Sosyal & İnsan Kaynakları": [
        (
            "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
            str(len(st.session_state.ihtiyac_sahipleri)),
        ),
        ("Personel & Çalışma Süresi Takibi", str(aktif_personel_sayisi)),
    ],
    "📈 Raporlar & Arşiv": [
        ("Kullanım Takibi", ""),
        ("Kapsamlı Envanter ve Hareket Raporu", ""),
    ],
}

if yonetici_modu:
    menu_gruplari["⚙️ Sistem Ayarları"] = [(
        "Kullanıcı Ayarları",
        str(len(st.session_state.kullanicilar)),
    )]

filtrelenmis_gruplar = {}
for grup_adi, alt_menuler in menu_gruplari.items():
    uygun_menuler = []
    for m, badge in alt_menuler:
        if misafir_modu and m in [
            "Güncel Stok Durumu",
            "Ürün Sil / Düzenle",
            "Fire / Zayiat Girişi",
            "Toplu Stok Düşümü & Sarfiyat",
            "İhtiyaç Sahibi & Yemek Dağıtım Takibi",
            "Personel & Çalışma Süresi Takibi",
            "Kullanım Takibi",
            "Kapsamlı Envanter ve Hareket Raporu",
            "Depo Yönetimi",
            "Demirbaş Yönetimi",
        ]:
            continue
        if not yonetici_modu and m in yasakli_menuler_listesi:
            continue
        if (
            not sidebar_arama
            or sidebar_arama in m.lower()
            or sidebar_arama in grup_adi.lower()
            or otomatik_yonlendirilen_menu == m
        ):
            uygun_menuler.append((m, badge))
    if uygun_menuler:
        filtrelenmis_gruplar[grup_adi] = uygun_menuler

for grup_adi, alt_menuler in filtrelenmis_gruplar.items():
    grup_aktif_mu = any(st.session_state.aktif_menu == m for m, _ in alt_menuler)
    with st.sidebar.expander(
        grup_adi, expanded=grup_aktif_mu or bool(sidebar_arama)
    ):
        for m, badge in alt_menuler:
            if m == "Yeni Mal Alımı / Fatura Ekle" and salt_okunur_modu:
                continue

            btn_label = f"{m}  [{badge}]" if badge and badge != "0" else m
            btn_type = (
                "primary" if st.session_state.aktif_menu == m else "secondary"
            )
            if st.button(
                btn_label, use_container_width=True, type=btn_type, key=f"menu_btn_{m}"
            ):
                st.session_state.aktif_menu = m
                st.query_params["menu"] = m
                st.rerun()

st.sidebar.markdown("<div style='margin-top: 150px;'></div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button(
    "Oturumu Kapat", use_container_width=True, type="secondary"
):
    oturumu_kapat()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<p style="font-size: 11px; text-align: center; opacity: 0.5; color: {subtext_color};">sefautopcu</p>',
    unsafe_allow_html=True,
)
st.sidebar.caption(f"🚀 {APP_VERSION} · Son güncelleme: {LAST_UPDATE}")
if yonetici_modu:  # sunucu bellek bilgisi yalnızca admin'e gösterilir
    ram_kullanimi = bellek_kullanimi_al()
    if ram_kullanimi > 0:
        st.sidebar.caption(f"💾 **RAM Kullanımı:** {ram_kullanimi} MB")
        if st.sidebar.button("🧹 Önbellek Temizle", key="sb_ram_clean_btn", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()


def tablo_to_excel_bytes(veri_listesi, baslik_str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rapor"
    ws.views.sheetView[0].showGridLines = True
    header_fill = PatternFill(
        start_color="6366f1", end_color="6366f1", fill_type="solid"
    )
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="000000")
    regular_font = Font(name="Calibri", size=11)
    thin_border = Border(
        left=Side(style="thin", color="e2e8f0"),
        right=Side(style="thin", color="e2e8f0"),
        top=Side(style="thin", color="e2e8f0"),
        bottom=Side(style="thin", color="e2e8f0"),
    )

    ws.cell(row=1, column=1, value=baslik_str).font = title_font
    ws.cell(
        row=2,
        column=1,
        value=f"Rapor Tarihi ve Saati: {simdi_tr_str('%Y-%m-%d %H:%M:%S')}",
    ).font = Font(name="Calibri", size=11, italic=True, color="6b7280")

    if not veri_listesi:
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        return excel_buffer.getvalue()

    headers = list(veri_listesi[0].keys())
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 5
    for item in veri_listesi:
        for col_idx, h in enumerate(headers, 1):
            val = item.get(h, "")
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            if c.data_type == "f":
                c.data_type = "s"
            c.font = regular_font
            c.border = thin_border
        row_idx += 1

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    return excel_buffer.getvalue()


def tablo_to_html_pdf_bytes(baslik, veri_listesi):
    tr_zaman = simdi_tr_str("%Y-%m-%d %H:%M:%S")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{html_escape(str(baslik))}</title>
        <style>
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; margin: 30px; color: {text_color}; background: {bg_color}; }}
            h2 {{ color: {text_color}; margin-bottom: 5px; }}
            p {{ color: {subtext_color}; font-size: 14px; margin-top: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: {card_bg}; }}
            th {{ background-color: #6366f1; color: white; padding: 12px; text-align: left; font-size: 13px; }}
            td {{ border: 1px solid {border_color}; padding: 10px 12px; font-size: 13px; color: {subtext_color}; }}
            tr:nth-child(even) {{ background-color: {sidebar_bg}; }}
        </style>
    </head>
    <body>
        <h2>{html_escape(str(baslik))}</h2>
        <p>Rapor Tarihi ve Saati: {tr_zaman}</p>
        <hr style="border: 0; border-top: 1px solid {border_color};"/>
    """
    if veri_listesi:
        headers = list(veri_listesi[0].keys())
        html += "<table><tr>"
        for h in headers:
            html += f"<th>{html_escape(str(h))}</th>"
        html += "</tr>"
        for item in veri_listesi:
            html += "<tr>"
            for h in headers:
                html += f"<td>{html_escape(str(item.get(h, '')))}</td>"
            html += "</tr>"
        html += "</table>"
    else:
        html += "<p>Kayıt bulunamadı.</p>"
    html += "</body></html>"
    return html.encode("utf-8")


def ortak_indirme_alani(excel_veri, pdf_veri, dosya_adi_koku, unique_key):
    col_sec, col_btn = st.columns([2, 1])
    with col_sec:
        format_secimi = st.selectbox(
            "İndirilecek Formatı Seçin",
            ["Excel (.xlsx)", "PDF / HTML (.html)"],
            key=f"sel_{unique_key}",
        )
    with col_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if "Excel" in format_secimi:
            st.download_button(
                label="📥 Raporu İndir",
                data=excel_veri,
                file_name=f"{dosya_adi_koku}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                key=f"btn_{unique_key}",
            )
        else:
            st.download_button(
                label="📥 Raporu İndir",
                data=pdf_veri,
                file_name=f"{dosya_adi_koku}.html",
                mime="text/html",
                key=f"btn_{unique_key}",
            )


def ozel_html_tablo_goster(veri_listesi):
    if not veri_listesi:
        st.info("Gösterilecek veri bulunmuyor.")
        return
    
    headers = list(veri_listesi[0].keys())
    html = "<table class='custom-table'><thead><tr>"
    for h in headers:
        html += f"<th>{html_escape(str(h))}</th>"
    html += "</tr></thead><tbody>"
    
    for row in veri_listesi:
        html += "<tr>"
        for h in headers:
            html += f"<td>{html_escape(str(row.get(h, '')))}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


if yonetici_modu and SUPABASE_URL and supabase_anahtar_rolu() == "anon":
    st.warning(
        "🛡️ **Güvenlik uyarısı:** Supabase için herkese açık (anon) anahtar kullanıyorsunuz. "
        "Veritabanını RLS ile kilitleyip `secrets` içinde `service_role` anahtarını kullanın "
        "(adımlar için `supabase_guvenlik.sql` dosyasına bakın)."
    )

menu = st.session_state.aktif_menu

if not yonetici_modu and menu in yasakli_menuler_listesi:
    st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    st.stop()
    
if menu == "Kurumsal Dashboard & Özet" or menu == "Genel Bakış":
    import base64
    from collections import defaultdict
        # Üstteki varsayılan Streamlit boşluğunu kaldır
    st.markdown("<style>div.block-container { padding-top: 1,5rem !important; } hr { margin-top: 0rem !important; margin-bottom: 0rem !important; }</style>", unsafe_allow_html=True)   

    # --- ARKA PLAN RESMİ YÖNETİMİ ---
    varsayilan_arka_plan = "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?q=80&w=1920&auto=format&fit=crop"
    
    if "dashboard_arka_plan" not in st.session_state:
        st.session_state.dashboard_arka_plan = varsayilan_arka_plan
    
    arka_plan_url = st.session_state.dashboard_arka_plan

    # --- VERİ HAZIRLIĞI ---
    gecmis_uretimler = st.session_state.get("yemek_uretim_arsivi", [])
    urun_cesidi_sayisi = len(set(g.get("urun", "").strip().upper() for g in st.session_state.get("girisler", []) if g.get("urun")))
    toplam_stok_degeri = sum(float(g.get("kalan", 0)) * float(g.get("fiyat", 0)) for g in st.session_state.get("girisler", []))
    toplam_fire_kg = sum(float(l.get("miktar", 0)) for l in st.session_state.get("kullanim_loglari", []) if l.get("tur") == "Fire/Zayiat")
    toplam_fire_tl = sum(float(l.get("tutar", 0)) for l in st.session_state.get("kullanim_loglari", []) if l.get("tur") == "Fire/Zayiat")
    aktif_personel_sayisi = sum(1 for p in st.session_state.get("personeller", []) if p.get("aktif", True))

    # --- MASKELEME KONTROLÜ ---
    fire_maskeli = "1. Sayfa: Toplam Fire" in aktif_k_maskeleri
    stok_maskeli = "1. Sayfa: Stok Değeri" in aktif_k_maskeleri
    urun_maskeli = "1. Sayfa: Ürün Çeşidi" in aktif_k_maskeleri
    personel_maskeli = "1. Sayfa: Aktif Personel" in aktif_k_maskeleri
    grafik_maskeli = "1. Sayfa: Grafik Alanı" in aktif_k_maskeleri

    fire_degeri_gosterim = "🔒 Gizli" if fire_maskeli else f"{toplam_fire_kg:.1f} Kg"
    fire_alt_gosterim = "" if fire_maskeli else f"({toplam_fire_tl:,.2f} ₺)"
    stok_degeri_gosterim = "🔒 Gizli" if stok_maskeli else f"{toplam_stok_degeri:,.0f} ₺"
    urun_cesidi_gosterim = "🔒 Gizli" if urun_maskeli else f"{urun_cesidi_sayisi} Çeşit"
    personel_gosterim = "🔒 Gizli" if personel_maskeli else f"{aktif_personel_sayisi} Kişi"

    # --- GRAFİK VERİLERİ HESAPLAMA ---
    gida_toplam = sum(float(g.get("kalan", 0)) * float(g.get("fiyat", 0)) for g in st.session_state.get("girisler", []) if g.get("kategori") == "KURU GIDA")
    sebze_toplam = sum(float(g.get("kalan", 0)) * float(g.get("fiyat", 0)) for g in st.session_state.get("girisler", []) if g.get("kategori") == "SEBZE")
    yag_toplam = sum(float(g.get("kalan", 0)) * float(g.get("fiyat", 0)) for g in st.session_state.get("girisler", []) if g.get("kategori") == "YAĞ")
    genel_toplam = toplam_stok_degeri if toplam_stok_degeri > 0 else 1
    yuzde_gida = int((gida_toplam / genel_toplam) * 100)
    yuzde_sebze = int((sebze_toplam / genel_toplam) * 100)
    yuzde_yag = int((yag_toplam / genel_toplam) * 100)

    depo_doluluk = {}
    for depo in st.session_state.get("depolar", []):
        depo_toplam = sum(float(g.get("kalan", 0)) * float(g.get("fiyat", 0)) for g in st.session_state.get("girisler", []) if g.get("depo") == depo)
        depo_doluluk[depo] = int((depo_toplam / genel_toplam) * 100)
    sirali_depolar = sorted(depo_doluluk.items(), key=lambda x: x[1], reverse=True)[:3]
    renkler = ["#10b981", "#38bdf8", "#f59e0b"]
    
    depo_html_satirlari = ""
    for i, (d_adi, d_yuzde) in enumerate(sirali_depolar):
        renk = renkler[i % len(renkler)]
        depo_html_satirlari += f"""
            <div class="progress-row">
                <div class="progress-title"><span>{html_escape(d_adi)}</span><span class="text-white">{d_yuzde}%</span></div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {d_yuzde}%; background: {renk};"></div></div>
            </div>
        """

    # --- DİNAMİK KRİTİK SEVİYE VE OPERASYONEL SAĞLIK HESABI ---
    kritik_urun_sayisi = 0
    for u in set(g.get("urun", "").strip().upper() for g in st.session_state.get("girisler", []) if g.get("urun")):
        toplam_kalan = sum(float(g.get("kalan", 0)) for g in st.session_state.get("girisler", []) if g.get("urun", "").strip().upper() == u)
        ozel_sinir = st.session_state.get("kritik_seviyeler", {}).get(u, 10.0)
        if toplam_kalan <= float(ozel_sinir):
            kritik_urun_sayisi += 1

    guvenli_urun_sayisi = urun_cesidi_sayisi - kritik_urun_sayisi if urun_cesidi_sayisi > kritik_urun_sayisi else 0
        # --- SKT / STT UYARILARI (Operasyonel Sağlık için) ---
    skt_kirmizi = 0
    skt_turuncu = 0
    bugun_tarih = datetime.date.today()
    
    for u in set(g.get("urun", "").strip().upper() for g in st.session_state.get("girisler", []) if g.get("urun")):
        skt_listesi = [g.get("skt") for g in st.session_state.get("girisler", []) if g.get("urun", "").strip().upper() == u and g.get("skt")]
        en_yakin_skt = min(skt_listesi) if skt_listesi else None
        if en_yakin_skt:
            try:
                skt_date = datetime.datetime.strptime(en_yakin_skt, "%Y-%m-%d").date()
                kalan_gun = (skt_date - bugun_tarih).days
                if kalan_gun < 0:
                    skt_kirmizi += 1
                elif kalan_gun <= 7:
                    skt_turuncu += 1
            except Exception:
                pass
    yuzde_kritik = int((kritik_urun_sayisi / urun_cesidi_sayisi) * 100) if urun_cesidi_sayisi > 0 else 0
    yuzde_guvenli = 100 - yuzde_kritik

    aylik_dagitim = defaultdict(int)
    for d in st.session_state.get("dagitim_loglari", []):
        if len(d.get("tarih", "")) >= 7: aylik_dagitim[d["tarih"][:7]] += int(d.get("porsiyon", 1))
    
    son_5_ay = sorted(aylik_dagitim.keys())[-5:]
    while len(son_5_ay) < 5: son_5_ay.insert(0, f"2026-{len(son_5_ay)+1:02d}")
    
    aylar_tr = {"01":"Oca", "02":"Şub", "03":"Mar", "04":"Nis", "05":"May", "06":"Haz", "07":"Tem", "08":"Ağu", "09":"Eyl", "10":"Eki", "11":"Kas", "12":"Ara"}
    maks_dag = max([aylik_dagitim.get(ay, 0) for ay in son_5_ay] + [1])
    
    aylik_barlar_html = ""
    for ay in son_5_ay:
        deger = aylik_dagitim.get(ay, 0)
        yuzde = max(10, int((deger / maks_dag) * 100))
        aylik_barlar_html += f"""
            <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%;">
                <div style="font-size: 12px; color: #10b981; font-weight: bold; margin-bottom: 5px;">{deger}</div>
                <div style="width: 80%; background: linear-gradient(180deg, #10b981 0%, #059669 100%); border-radius: 6px 6px 0 0; height: {yuzde}%;"></div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">{aylar_tr.get(ay[-2:], ay)}</div>
            </div>
        """

    # --- TÜM TASARIM TEK BİR HTML İÇİNDE ---
        st.markdown("""
    <style>
        .table-panel { 
            background: rgba(10, 15, 29, 0.85); 
            border: 1px solid rgba(16, 185, 129, 0.35); 
            border-radius: 18px; 
            padding: 25px; 
            transition: all 0.3s ease; 
            display: flex; 
            flex-direction: column; 
            min-height: 320px; 
            height: 100%; 
        }
        .table-panel:hover { 
            transform: translateY(-5px); 
            border-color: rgba(16, 185, 129, 0.8); 
            box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); 
        }
    </style>
    """, unsafe_allow_html=True)
    # --- TÜM TASARIM TEK BİR HTML İÇİNDE ---
    # --- ERZURUM AZİZİYE 7 GÜNLÜK HAVA DURUMU VERİSİ ---
    hava_durumu_html = ""
    try:
        hava_url = "https://api.open-meteo.com/v1/forecast?latitude=39.95&longitude=41.10&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Europe/Istanbul&forecast_days=7"
        hava_cevap = requests.get(hava_url, timeout=10)
        hava_veri = hava_cevap.json()
        
        if "daily" in hava_veri:
            gunler = hava_veri["daily"]["time"]
            max_temp = hava_veri["daily"]["temperature_2m_max"]
            min_temp = hava_veri["daily"]["temperature_2m_min"]
            yagis = hava_veri["daily"]["precipitation_sum"]
            
            aylar_tr_kisa = {"01":"Oca", "02":"Şub", "03":"Mar", "04":"Nis", "05":"May", "06":"Haz", "07":"Tem", "08":"Ağu", "09":"Eyl", "10":"Eki", "11":"Kas", "12":"Ara"}
            
            for i in range(len(gunler)):
                tarih_obj = datetime.datetime.strptime(gunler[i], "%Y-%m-%d")
                gun_adi = f"{tarih_obj.day} {aylar_tr_kisa.get(f'{tarih_obj.month:02d}', '')}"
                
                ort_temp = (max_temp[i] + min_temp[i]) / 2
                if ort_temp > 15: renk = "#10b981" 
                elif ort_temp > 5: renk = "#38bdf8" 
                elif ort_temp > -5: renk = "#f59e0b" 
                else: renk = "#ef4444" 
                
                yagis_ikon = "☀️" if yagis[i] == 0 else ("🌧️" if yagis[i] < 10 else "🌧️🌧️")
                
                m_temp = f"{max_temp[i]:.0f}"
                n_temp = f"{min_temp[i]:.0f}"
                renk_alt = renk + "88"
                
                hava_durumu_html += f"""
                    <div style="flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; height: 100%;">
                        <div style="font-size: 20px; margin-bottom: 5px;">{yagis_ikon}</div>
                        <div style="font-size: 14px; color: #f4f4f5; font-weight: bold;">{m_temp}°</div>
                        <div style="font-size: 12px; color: #94a3b8;">{n_temp}°</div>
                        <div style="width: 80%; background: linear-gradient(180deg, {renk} 0%, {renk_alt} 100%); border-radius: 6px 6px 0 0; height: 60%; margin-top: 8px;"></div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">{gun_adi}</div>
                    </div>
                """
    except Exception:
        hava_durumu_html = "<div style='color: #94a3b8; text-align: center; width: 100%;'>Hava durumu verisi alınamadı.</div>"
    hero_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }}
        body {{ background: transparent; margin: 0; padding: 0; }}
        
        .main-hero-container {{
            background-image: linear-gradient(rgba(4, 7, 17, 0.75), rgba(4, 7, 17, 0.95)), url('{arka_plan_url}'); 
            background-size: cover; background-position: center; 
            border-radius: 24px; padding: 35px; margin-bottom: 25px; 
            border: 1px solid rgba(16, 185, 129, 0.4); box-shadow: 0 15px 40px -10px rgba(0,0,0,0.6); 
        }}
        .hero-badge {{ background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #10b981; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; margin-bottom: 15px; }}
        .hero-title {{ font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 8px; letter-spacing: -0.03em; }}
        .hero-subtitle {{ color: #cbd5e1; font-size: 14px; margin-bottom: 30px; }}

        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px; }}
        .metric-card {{ background: rgba(10, 15, 29, 0.75); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 18px; box-shadow: 0 0 25px -5px rgba(16, 185, 129, 0.25); transition: all 0.3s ease; backdrop-filter: blur(10px); }}
        .metric-card:hover {{ transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }}
        .metric-val {{ font-size: 1.4rem; font-weight: 800; color: #f4f4f5; margin: 6px 0; }}
        .metric-label {{ font-size: 12px; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
        .metric-sub {{ font-size: 11px; color: #10b981; font-weight: 600; }}
        .metric-sub-red {{ font-size: 11px; color: #ef4444; font-weight: 600; }}

        .panel-title {{ font-size: 1.1rem; font-weight: 700; color: #f4f4f5; }}
        .panel-total {{ font-size: 1.6rem; font-weight: 800; color: #fff; line-height: 1.2; margin-top: 5px; }}
        .panel-sub {{ font-size: 12px; color: #94a3b8; margin-top: 4px; margin-bottom: 20px; }}
        
        .table-panel {{ background: rgba(10, 15, 29, 0.85); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 25px; transition: all 0.3s ease; display: flex; flex-direction: column; min-height: 340px; height: 100%; }}
        .table-panel:hover {{ transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }}
        
        .progress-row {{ margin-bottom: 15px; }}
        .progress-title {{ display: flex; justify-content: space-between; font-size: 13px; color: #cbd5e1; font-weight: 500; margin-bottom: 8px; }}
        .text-white {{ color: #fff; font-weight: 700; }}
        .progress-bar-bg {{ height: 6px; background: rgba(15, 23, 42, 0.9); border-radius: 4px; overflow: hidden; }}
        .progress-bar-fill {{ height: 100%; border-radius: 4px; }}
        
        .chart-container {{ display: flex; gap: 15px; align-items: flex-end; height: 120px; padding-bottom: 20px; }}
    </style>
    </head>
    <body>
        <div class="main-hero-container">
            <div class="hero-badge">📍 AZİZİYE AŞEVİ · KURUMSAL PANEL</div>
            <div class="hero-title">Genel Bakış & Operasyonel Özet</div>
            <div class="hero-subtitle">Canlı Stok ve Maliyet Takip Sistemi</div>

            <div class="metrics-grid">
                <div class="metric-card"><div class="metric-label">Günlük Sıcak Yemek</div><div class="metric-val">Aktif</div><div class="metric-sub">↑ Anlık Simülasyon</div></div>
                <div class="metric-card"><div class="metric-label">Ürün Çeşidi</div><div class="metric-val">{urun_cesidi_gosterim}</div><div class="metric-sub">↑ Güncel Stok Durumu</div></div>
                <div class="metric-card"><div class="metric-label">Toplam Fire / Zayiat</div><div class="metric-val">{fire_degeri_gosterim}</div><div class="metric-sub-red">{fire_alt_gosterim}</div></div>
                <div class="metric-card"><div class="metric-label">Stok Değeri</div><div class="metric-val">{stok_degeri_gosterim}</div><div class="metric-sub">↑ Güncel Depo Toplamı</div></div>
            </div>
            <div class="metrics-grid" style="margin-bottom: 30px;">
                <div class="metric-card"><div class="metric-label">Aktif Çalışan Personel</div><div class="metric-val">{personel_gosterim}</div><div class="metric-sub">↑ Personel Takip Tablosu</div></div>
                <div class="metric-card"><div class="metric-label">Depo Durumu</div><div class="metric-val">Senkronize</div><div class="metric-sub">↑ Supabase Realtime RLS</div></div>
                <div class="metric-card"><div class="metric-label">Son Birim Fiyat Mantığı</div><div class="metric-val">FIFO Mantığı</div><div class="metric-sub">↑ Reçete Hassasiyeti</div></div>
                <div class="metric-card"><div class="metric-label">Son İşlem Desteği</div><div class="metric-val">Aktif (Undo)</div><div class="metric-sub">↑ Tek Tıkla Geri Al</div></div>
            </div>

            <!-- 3'LÜ TABLO -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div class="table-panel">
                    <div class="panel-title">Kategori Doluluk</div>
                    <div class="panel-total">Stok Dağılımı</div>
                    <div class="panel-sub">Maliyet bazlı oranlar</div>
                    <div class="progress-row"><div class="progress-title"><span>1. Kuru Gıda</span><span class="text-white">{yuzde_gida}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_gida}%; background: #10b981;"></div></div></div>
                    <div class="progress-row"><div class="progress-title"><span>2. Sebze</span><span class="text-white">{yuzde_sebze}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_sebze}%; background: #38bdf8;"></div></div></div>
                    <div class="progress-row"><div class="progress-title"><span>3. Yağ</span><span class="text-white">{yuzde_yag}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_yag}%; background: #a855f7;"></div></div></div>
                </div>

                <div class="table-panel">
                    <div class="panel-title">Depo Doluluk</div>
                    <div class="panel-total">Ağırlıklı</div>
                    <div class="panel-sub">Fiziksel depo dolulukları</div>
                    {depo_html_satirlari}
                </div>

                <div class="table-panel">
                    <div class="panel-title">Operasyonel Sağlık</div>
                    <div class="panel-total">{urun_cesidi_sayisi}</div>
                    <div class="panel-sub">Kayıtlı çeşit üzerinden durum</div>
                    
                    <div class="progress-row">
                        <div class="progress-title"><span>Kritik Seviyede</span><span class="text-white">{kritik_urun_sayisi} Ürün</span></div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_kritik}%; background: #ef4444;"></div></div>
                    </div>
                    <div class="progress-row">
                        <div class="progress-title"><span>Güvenli Stokta</span><span class="text-white">{guvenli_urun_sayisi} Ürün</span></div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {yuzde_guvenli}%; background: #10b981;"></div></div>
                    </div>
                    <div class="progress-row">
                        <div class="progress-title"><span>🔴 SKT Süresi Geçen</span><span class="text-white">{skt_kirmizi} Ürün</span></div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_kirmizi*10, 100)}%; background: #ef4444;"></div></div>
                    </div>
                    <div class="progress-row">
                        <div class="progress-title"><span>🟠 SKT'si Yaklaşan</span><span class="text-white">{skt_turuncu} Ürün</span></div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {min(skt_turuncu*10, 100)}%; background: #f59e0b;"></div></div>
                    </div>
                </div>
            </div>

            <!-- CANLI HAVA DURUMU GRAFİĞİ -->
            <div class="table-panel">
                <div class="panel-title" style="margin-bottom: 15px;">🌤️ Erzurum / Aziziye - 7 Günlük Hava Durumu</div>
                <div class="chart-container" style="height: 140px;">
                    {hava_durumu_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(hero_html, height=1200, scrolling=False)

    # --- 3. BÖLÜM: EN ALT (YEMEK SEÇİMİ + CANLI MALİYET ÖZET PANELİ) ---
    st.markdown("---")
    menu_secenekleri = {}
    if gecmis_uretimler:
        for item in gecmis_uretimler:
            if not item: continue
            top_mal = float(item.get("toplam_maliyet", 0)) or sum(float(m.get("tutar", 0)) for m in item.get("malzemeler", []))
            kisi = int(item.get("kisi_sayisi", 1) or 1)
            item["kisi_basi"] = top_mal / kisi if kisi > 0 else 0.0
            item["kalem_sayisi"] = len(item.get("malzemeler", []))
            menu_secenekleri[f"{item.get('tarih', '-')} | {item.get('yemek_adi', '-')} ({kisi} Kişi)"] = item

    if not menu_secenekleri:
        menu_secenekleri = {"Henüz Kayıt Yok": {"tarih": "-", "yemek_adi": "Kayıt Yok", "kisi_basi": 0.0, "kalem_sayisi": 0}}

    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        secilen_key = st.selectbox("📋 Geçmişte Çıkan Yemeği / Menüyü Seçin", options=list(menu_secenekleri.keys()))
    with col_sel2:
        kisi_sayisi = st.slider("Yararlanılan Kişi Sayısı (Simülasyon)", 10, 1000, 230, step=10)

    secilen_veri = menu_secenekleri[secilen_key]
    toplam_tl = secilen_veri.get("kisi_basi", 0.0) * kisi_sayisi

    st.markdown(f"""
    <style>
        .cost-panel {{ background: rgba(10, 15, 29, 0.85); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 20px; padding: 25px; box-shadow: 0 0 35px -5px rgba(16, 185, 129, 0.35); margin-bottom: 25px; }}
        .cost-header {{ font-size: 1.2rem; font-weight: 700; color: #f4f4f5; }}
        .cost-meta {{ font-size: 12px; color: #94a3b8; margin: 4px 0 18px 0; text-transform: uppercase; }}
        .inner-box {{ background: rgba(6, 10, 20, 0.7); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 16px; padding: 20px; }}
        .cost-row {{ display: flex; gap: 16px; margin-bottom: 16px; }}
        .cost-card {{ flex: 1; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 14px; padding: 15px; }}
        .cost-num-green {{ font-size: 1.6rem; font-weight: 800; color: #10b981; margin-top: 4px; }}
        .cost-num-blue {{ font-size: 1.6rem; font-weight: 800; color: #38bdf8; margin-top: 4px; }}
    </style>
    <div class="cost-panel">
        <div class="cost-header">📊 Canlı Maliyet Özet Paneli</div>
        <div class="cost-meta">Tarih: {html_escape(str(secilen_veri.get('tarih', '-')))} | {secilen_veri.get('kalem_sayisi', 0)} Kalem Malzeme | Simülasyon: {kisi_sayisi} Kişi</div>
        <div class="inner-box">
            <div style="font-size: 1.25rem; font-weight: 800; color: #ffffff; margin-bottom: 16px;">{html_escape(str(secilen_veri.get('yemek_adi', '-')))}</div>
            <div class="cost-row">
                <div class="cost-card"><div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Menü Toplam Maliyeti</div><div class="cost-num-green">{toplam_tl:,.2f} ₺</div></div>
                <div class="cost-card"><div style="font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase;">Kişi Başı Maliyet ({kisi_sayisi} Kişi)</div><div class="cost-num-blue">{secilen_veri.get('kisi_basi', 0.0):,.2f} ₺</div></div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.12); border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 8px; font-size: 12px; color: #cbd5e1;">🔄 <b>Son İşlem Geri Alma Desteği:</b> Hatalı girilen günlük üretim kaydı tek tıkla depoya iade edilebilir.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # --- 4. BÖLÜM: SİSTEM ÖZELLİKLERİ (HOVER EFEKTLİ) ---
    st.markdown("### 🌟 Sistem Özellikleri ve Modüller")
    st.markdown("<br>", unsafe_allow_html=True)
    
    ozellikler_html = """
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }
        body { background: transparent; margin: 0; padding: 0; }
        .feature-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
        .metric-card { background: rgba(10, 15, 29, 0.75); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 18px; padding: 24px; height: 160px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.3s ease; backdrop-filter: blur(10px); }
        .metric-card:hover { transform: translateY(-5px); border-color: rgba(16, 185, 129, 0.8); box-shadow: 0 0 35px -2px rgba(16, 185, 129, 0.45); }
        .feature-icon { font-size: 32px; }
        .feature-title { font-size: 16px; font-weight: 700; color: #f4f4f5; margin-bottom: 4px; }
        .feature-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
    </style>
    </head>
    <body>
        <div class="feature-grid">
            <div class="metric-card">
                <div class="feature-icon">📦</div>
                <div><div class="feature-title">Stok Yönetimi</div><div class="feature-desc">FIFO mantığı ile anlık depo takibi, kritik seviye uyarıları.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">🍲</div>
                <div><div class="feature-title">Yemek Üretimi</div><div class="feature-desc">Reçete bazlı otomatik maliyet hesaplama ve stok düşümü.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">👥</div>
                <div><div class="feature-title">İhtiyaç Sahipleri</div><div class="feature-desc">Şifreli veri saklama ile güvenli kayıt ve porsiyon dağıtımı.</div></div>
            </div>
            <div class="metric-card">
                <div class="feature-icon">🔒</div>
                <div><div class="feature-title">Gelişmiş Güvenlik</div><div class="feature-desc">scrypt hash, Fernet şifreleme, oturum yönetimi ve maskeleme.</div></div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(ozellikler_html, height=190, scrolling=False)


    # --- 5. BÖLÜM: EN ALTA TAŞINAN ARKA PLAN DEĞİŞTİRME ---
    if yonetici_modu:
        st.markdown("---")
        with st.expander("🎨 Dashboard Arka Plan Resmini Değiştir (Admin)"):
            yeni_resim = st.file_uploader("Yeni arka plan resmi yükleyin (JPG, PNG)", type=["jpg", "jpeg", "png"], key="dashboard_bg_uploader")
            if yeni_resim is not None:
                b64 = base64.b64encode(yeni_resim.getvalue()).decode()
                st.session_state.dashboard_arka_plan = f"data:{yeni_resim.type};base64,{b64}"
                st.success("✅ Arka plan resmi güncellendi!")
            if st.button("🔄 Varsayılan Resme Dön", key="dashboard_bg_reset"):
                st.session_state.dashboard_arka_plan = varsayilan_arka_plan
                st.rerun()
            
# 1. GÜNCEL STOK DURUMU
elif menu == "Güncel Stok Durumu":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_baslik, col_indir_alan = st.columns([2, 2])
        with col_baslik:
            st.header("📦 Güncel Depo Envanteri ve Kritik Stoklar")

        benzersiz_urunler_Excel = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )
        
        bugun = datetime.date.today()

        excel_liste = []
        for u in benzersiz_urunler_Excel:
            toplam_kalan_ex = sum(
                g.get("kalan", 0) for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u
            )
            kategori_ex = next(
                (g.get("kategori", "GENEL") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "GENEL",
            )
            birim_ex = next(
                (g.get("birim", "Kg") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Kg",
            )
            depo_ex = next(
                (g.get("depo", "Merkez Depo") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Merkez Depo",
            )
            islem_yapan_ex = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                "admin",
            )
            en_son_tarih_ex = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                default="-",
            )
            # En yakın SKT'yi bul
            skt_listesi = [g.get("skt") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u and g.get("skt")]
            en_yakin_skt = min(skt_listesi) if skt_listesi else "Belirtilmemiş"
            
            gosterilen_kalan_excel = "🔒 Gizli" if "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri else toplam_kalan_ex
            
            excel_liste.append({
                "Ürün Adı": u,
                "Kategori": kategori_ex,
                "Birim": birim_ex,
                "Kalan Miktar": gosterilen_kalan_excel,
                "En Yakın SKT / STT": en_yakin_skt,
                "Depo Yeri": depo_ex,
                "Eklenme/Güncelleme Tarihi": en_son_tarih_ex,
                "Son İşlemi Yapan": islem_yapan_ex,
            })

        excel_data = tablo_to_excel_bytes(
            excel_liste, "Aziziye Aşevi - Güncel Stok Raporu"
        )
        pdf_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Güncel Stok Raporu", excel_liste
        )

        with col_indir_alan:
            ortak_indirme_alani(
                excel_data, pdf_data, "asevi_guncel_stok_raporu", "stok_sayfasi"
            )

        depolar = ["Tümü"] + st.session_state.depolar
        secilen_depo = st.selectbox("Depo Konumuna Göre Filtrele", depolar)

        benzersiz_urunler = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )
        stok_tablosu = []
        kritik_urunler_tablosu = []
        
        for u in benzersiz_urunler:
            toplam_kalan = sum(
                g.get("kalan", 0) for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u
            )
            kategori = next(
                (g.get("kategori", "GENEL") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "GENEL",
            )
            birim = next(
                (g.get("birim", "Kg") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Kg",
            )
            depo = next(
                (g.get("depo", "Merkez Depo") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u),
                "Merkez Depo",
            )
            islem_yapan = next(
                (
                    g.get("islem_yapan", "admin")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                "admin",
            )
            en_son_tarih = max(
                (
                    g.get("tarih", "-")
                    for g in st.session_state.girisler
                    if g.get("urun", "").strip().upper() == u
                ),
                default="-",
            )
            
            # En yakın SKT'yi bul (Ekranda Göstermek İçin)
            skt_listesi = [g.get("skt") for g in st.session_state.girisler if g.get("urun", "").strip().upper() == u and g.get("skt")]
            en_yakin_skt = min(skt_listesi) if skt_listesi else "Belirtilmemiş"
            
            # SKT Rengi Belirleme
            skt_gosterim = en_yakin_skt
            if en_yakin_skt != "Belirtilmemiş":
                try:
                    skt_date = datetime.datetime.strptime(en_yakin_skt, "%Y-%m-%d").date()
                    kalan_gun = (skt_date - bugun).days
                    if kalan_gun < 0:
                        skt_gosterim = f"🔴 {en_yakin_skt} (Süresi Geçti)"
                    elif kalan_gun <= 7:
                        skt_gosterim = f"🟠 {en_yakin_skt} ({kalan_gun} Gün Kaldı)"
                    else:
                        skt_gosterim = f"🟢 {en_yakin_skt}"
                except:
                    pass

            final_kalan_gosterim = "🔒 Gizli" if "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" in aktif_k_maskeleri else toplam_kalan

            if secilen_depo == "Tümü" or depo == secilen_depo:
                stok_tablosu.append({
                    "Ürün Adı": u,
                    "Kategori": kategori,
                    "Birim": birim,
                    "Kalan Miktar": final_kalan_gosterim,
                    "SKT / STT": skt_gosterim,
                    "Depo Yeri": depo,
                    "Eklenme Tarihi": en_son_tarih,
                    "İşlemi Yapan": islem_yapan,
                })

            ozel_kritik_sinir = st.session_state.kritik_seviyeler.get(u, 10.0)
            if toplam_kalan <= float(ozel_kritik_sinir) and "2. Sayfa: Güncel Stok Durumu - Kalan Miktar" not in aktif_k_maskeleri:
                kritik_urunler_tablosu.append({
                    "Ürün Adı": u,
                    "Kalan Miktar": f"{toplam_kalan} {birim}",
                    "Kritik Eşik Sınırı": f"{ozel_kritik_sinir} {birim}",
                    "Depo Yeri": depo
                })

        st.markdown("### Envanter Listesi")
        ozel_html_tablo_goster(stok_tablosu)

        st.markdown("---")
        st.markdown("### ⚠️ Kritik Seviyenin Altındaki veya Tükenen Ürünler Tablosu")
        if kritik_urunler_tablosu:
            ozel_html_tablo_goster(kritik_urunler_tablosu)
        else:
            st.success("Tebrikler! Kritik seviyenin altında ürün bulunmuyor.")

        st.markdown("---")
        
        # YENİ EKLENEN: TOPLU SKT GÜNCELLEME FORMU
        st.markdown("### 📅 Son Tüketim Tarihi (SKT / STT) Güncelle")
        st.info("Sisteme daha önceden eklenmiş ve SKT tarihi girilmemiş ürünler için buradan toplu tarih güncellemesi yapabilirsiniz. Girilen tarih, seçilen ürünün en eski (en son kullanılacak) partisine atanır.")
        
        if not benzersiz_urunler:
            st.info("Sistemde kayıtlı ürün bulunmuyor.")
        else:
            with st.form("skt_guncelle_formu"):
                skt_sec_urun = st.selectbox("SKT Güncellenecek Ürünü Seçin", benzersiz_urunler, index=None, placeholder="Ürün Seçiniz...", key="skt_upd_urun")
                skt_yeni_tarih = st.date_input("Yeni SKT / STT Tarihi", value=None)
                skt_guncelle_btn = st.form_submit_button("SKT Tarihini Güncelle", type="primary")
                
                if skt_guncelle_btn:
                    if not skt_sec_urun:
                        st.error("⚠️ Lütfen SKT güncellenecek ürünü seçin!")
                    elif skt_yeni_tarih is None:
                        st.error("⚠️ Lütfen yeni SKT / STT tarihini seçin!")
                    else:
                        guncellendi = False
                        # İlgili ürünün stokta kalanı > 0 olan en eski partisini bul (FIFO)
                        ilgili_partiler = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == skt_sec_urun and g.get("kalan", 0) > 0]
                        if ilgili_partiler:
                            en_eski_parti = min(ilgili_partiler, key=lambda x: str(x.get("tarih", "")))
                            en_eski_parti["skt"] = str(skt_yeni_tarih)
                            guncellendi = True
                            
                        if guncellendi:
                            verileri_kaydet(st.session_state.girisler)
                            st.success(f"🎉 Başarılı! {skt_sec_urun} ürününün SKT tarihi {skt_yeni_tarih} olarak güncellendi.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ Seçilen ürünün stokta kalan partisi bulunmuyor, tarih atanamadı.")

        with st.expander("⚙️ Ürün Bazlı Kritik Eşik Sınırı Belirle"):
            with st.form("kritik_ayar_form"):
                secilen_k_urun = st.selectbox("Kritik Eşiği Değiştirilecek Ürün", benzersiz_urunler if benzersiz_urunler else ["Yok"])
                mevcut_esin = st.session_state.kritik_seviyeler.get(secilen_k_urun, 10.0)
                yeni_esin_deger = st.number_input("Kritik Miktar Sınırı", min_value=0.0, value=float(mevcut_esin), step=1.0)
                kritik_kaydet_btn = st.form_submit_button("Kritik Eşiği Güncelle", type="primary")

                if kritik_kaydet_btn and secilen_k_urun != "Yok":
                    st.session_state.kritik_seviyeler[secilen_k_urun] = yeni_esin_deger
                    kritik_seviyeleri_kaydet(st.session_state.kritik_seviyeler)
                    st.success("🎉 Başarılı! Kritik sınır güncellendi.")
                    st.balloons()
                    st.rerun()

# 2. YENİ MAL ALIMI / FATURA EKLE
elif menu == "Yeni Mal Alımı / Fatura Ekle":
    if salt_okunur_modu:
        st.warning(
            "⚠️ Bu sayfaya yalnızca gözlem amaçlı erişebilirsiniz. Salt okunur (Yönetim/Misafir) modda işlem yapamazsınız."
        )
    else:
        st.header("📝 Yeni Fatura ve Mal Alımı Girişi")
        st.markdown("Her yeni mal alımı ayrı bir kayıt olarak depoya eklenir; böylece aynı ürün eklendiğinde stoğunuz artar ve geçmiş alım fiyatlarınız/tarihçeniz korunur.")
        
        # Son Eklenen İşlemi Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_eklenen_fatura_id"):
            son_id = st.session_state["son_eklenen_fatura_id"]
            son_fatura = next((g for g in st.session_state.girisler if g.get("id") == son_id), None)
            if son_fatura:
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Eklenen Kayıt:** {son_fatura.get('urun')} ({son_fatura.get('miktar')} {son_fatura.get('birim')} - Fatura No: {son_fatura.get('fatura_no')})")
                with c_undo2:
                    if st.button("↩️ Son Mal Alımını Geri Al", type="secondary", key="btn_undo_fatura_son"):
                        otomatik_yedek_al("Fatura ekleme geri alma: " + str(son_id))
                        st.session_state.girisler = [g for g in st.session_state.girisler if g.get("id") != son_id]
                        verileri_kaydet(st.session_state.girisler)
                        st.session_state.pop("son_eklenen_fatura_id", None)
                        st.success(f"🎉 {son_id} numaralı mal alım kaydı başarıyla geri alındı ve silindi!")
                        time.sleep(1)
                        st.rerun()

        with st.form("fatura_formu"):
            fatura_tarihi_secim = st.date_input("📅 Fatura / Alım Tarihi", value=datetime.date.today())
            fatura_saati_secim = st.time_input("⏰ Alım Saati", value=datetime.datetime.now().time())
            tarih_giris = f"{fatura_tarihi_secim.strftime('%Y-%m-%d')} {fatura_saati_secim.strftime('%H:%M')}"

            fatura_no_input = st.text_input(
                "Fatura No / Belge No (Örn: FAT-2026-105)"
            ).strip().upper()
            
            mevcut_urun_listesi = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
            
            yeni_urun_secimi = st.checkbox("➕ Listede Olmayan Yepyeni Bir Ürün Ekle")
            
            if yeni_urun_secimi or not mevcut_urun_listesi:
                urun = st.text_input(
                    "Yeni Ürün Adı (Örn: KIRMIZI MERCİMEK - Büyük Harfle)"
                ).strip().upper()
            else:
                urun = st.selectbox(
                    "Mevcut Ürünlerden Seçin",
                    mevcut_urun_listesi,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="fatura_urun_selectbox"
                )

            kategori = st.selectbox(
                "Kategori",
                [
                    "SEBZE",
                    "MEYVE",
                    "KURU GIDA",
                    "BAHARAT",
                    "SÜT/SÜT ÜRÜNLERİ",
                    "KASAP / ŞARKÜTERİ",
                    "YAĞ",
                ],
            )
            birim = st.selectbox("Birim", ["Kg", "Adet", "Lt"])
            depo = st.selectbox("Depo Yeri", st.session_state.depolar if st.session_state.depolar else ["Merkez Depo"])
            
            # YENİ EKLENEN: ZORUNLU SKT / STT TARİHİ
            skt_tarihi = st.date_input("📅 Son Tüketim Tarihi (SKT / STT) - Zorunlu", value=None)

            miktar = st.number_input("Toplam Miktar", min_value=0.1, step=1.0)
            fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.01, step=0.1)

            submitted = st.form_submit_button("Depoya Yeni Ürün / Fatura Ekle")
            if submitted:
                if not urun:
                    st.error("⚠️ Lütfen listeden bir ürün seçin veya yeni bir ürün adı girin!")
                elif skt_tarihi is None:
                    st.error("⚠️ Lütfen ürünün Son Tüketim Tarihini (SKT/STT) seçin! Bu alan zorunludur.")
                else:
                    urun_temiz = urun.strip().upper()
                    
                    if yeni_urun_secimi and mevcut_urun_listesi:
                        benzerler = difflib.get_close_matches(urun_temiz, mevcut_urun_listesi, n=1, cutoff=0.7)
                        if benzerler:
                            st.warning(f"⚠️ Dikkat! Yazdığınız ürün mevcut '{benzerler[0]}' adına çok benziyor.")

                    islem_yapan_kisi = st.session_state.aktif_kullanici
                    fatura_no_degeri = (
                        fatura_no_input if fatura_no_input else "BELİRTİLMEMİŞ"
                    )
                    yeni_kayit_id = yeni_id_uret("FAT-", st.session_state.girisler)
                    
                    yeni_kayit_obj = {
                        "id": yeni_kayit_id,
                        "tarih": tarih_giris,
                        "fatura_no": fatura_no_degeri,
                        "urun": urun_temiz,
                        "kategori": kategori,
                        "birim": birim,
                        "miktar": miktar,
                        "kalan": miktar,
                        "fiyat": fiyat,
                        "depo": depo,
                        "skt": str(skt_tarihi), # YENİ EKLENEN VERİ
                        "islem_yapan": islem_yapan_kisi,
                    }
                    
                    st.session_state.girisler.append(yeni_kayit_obj)
                    st.session_state["son_eklenen_fatura_id"] = yeni_kayit_id
                    verileri_kaydet(st.session_state.girisler)
                    
                    st.markdown(
                    """
                    <div style="background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981; padding: 14px 18px; border-radius: 14px; margin: 16px 0; font-weight: 600; font-size: 15px;">
                    🎉 Başarılı! Yeni mal alımı faturası ve ürün SKT/STT tarihi ile birlikte depoya eklendi.
                    </div>
                    """,
                    unsafe_allow_html=True
                    )
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        # ... (Fatura Arşivi kısmı aynen kalacak, dilersen bu kısmı da SKT sütunu ile güncelleyebiliriz ama şu anlık dokunmuyoruz) ...
            
# DEPO YÖNETİMİ
elif menu == "Depo Yönetimi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🏢 Depo ve Kategori Yönetimi")
        st.markdown("Sisteme yeni depolar ve ürün kategorileri ekleyebilir, mevcut kayıtları yönetebilirsiniz.")

        # Varsayılan Kategoriler ve Session State Kontrolü
        varsayilan_kategoriler = ["SEBZE", "MEYVE", "KURU GIDA", "BAHARAT", "SÜT/SÜT ÜRÜNLERİ", "KASAP / ŞARKÜTERİ", "YAĞ"]
        if "kategoriler" not in st.session_state:
            st.session_state.kategoriler = supabase_veri_oku("kategoriler_listesi", varsayilan_kategoriler, kritik=False)
            if not isinstance(st.session_state.kategoriler, list) or not st.session_state.kategoriler:
                st.session_state.kategoriler = list(varsayilan_kategoriler)

        # Son Depo veya Kategori İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_depo_kat_islem"):
            son_islem = st.session_state["son_depo_kat_islem"]
            tur = son_islem.get("tur")
            ad = son_islem.get("ad")
            
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "depo_ekle":
                    st.info(f"💡 **Son İşlem:** '{ad}' deposu eklendi.")
                elif tur == "depo_sil":
                    st.info(f"💡 **Son İşlem:** '{ad}' deposu ve ilgili kayıtlar silindi.")
                elif tur == "kat_ekle":
                    st.info(f"💡 **Son İşlem:** '{ad}' kategorisi eklendi.")
                elif tur == "kat_sil":
                    st.info(f"💡 **Son İşlem:** '{ad}' kategorisi silindi.")
            
            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_depo_kat_son"):
                    otomatik_yedek_al("Depo/Kategori işlemi geri alma: " + str(ad))
                    
                    if tur == "depo_ekle":
                        if ad in st.session_state.depolar:
                            st.session_state.depolar.remove(ad)
                            depoları_kaydet(st.session_state.depolar)
                    elif tur == "depo_sil":
                        if ad not in st.session_state.depolar:
                            st.session_state.depolar.append(ad)
                            depoları_kaydet(st.session_state.depolar)
                        # Silinen bağlı alım kayıtlarını geri yükle
                        silinen_girisler = son_islem.get("silinen_girisler", [])
                        if silinen_girisler:
                            st.session_state.girisler.extend(silinen_girisler)
                            verileri_kaydet(st.session_state.girisler)
                    elif tur == "kat_ekle":
                        if ad in st.session_state.kategoriler:
                            st.session_state.kategoriler.remove(ad)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)
                    elif tur == "kat_sil":
                        if ad not in st.session_state.kategoriler:
                            st.session_state.kategoriler.append(ad)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)

                    st.session_state.pop("son_depo_kat_islem", None)
                    st.success(f"🎉 '{ad}' üzerine yapılan son işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        depo_tab1, depo_tab2 = st.tabs(["🏢 Depo Yönetimi", "🏷️ Kategori Yönetimi"])

        # TAB 1: DEPO YÖNETİMİ
        with depo_tab1:
            col_depo_ekle, col_depo_sil = st.columns(2)
            with col_depo_ekle:
                with st.form("yeni_depo_ekle_form"):
                    st.markdown("**➕ Yeni Depo Ekle**")
                    yeni_depo_adi = st.text_input("Depo Adı (Örn: Soğuk Hava Deposu -20)").strip()
                    depo_ekle_btn = st.form_submit_button("Depoyu Kaydet", type="primary")

                    if depo_ekle_btn and yeni_depo_adi:
                        if yeni_depo_adi in st.session_state.depolar:
                            st.error("⚠️ Bu depo zaten mevcut!")
                        else:
                            st.session_state.depolar.append(yeni_depo_adi)
                            depoları_kaydet(st.session_state.depolar)
                            
                            st.session_state["son_depo_kat_islem"] = {
                                "tur": "depo_ekle",
                                "ad": yeni_depo_adi
                            }
                            
                            st.success(f"🎉 Başarılı! '{yeni_depo_adi}' deposu eklendi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

            with col_depo_sil:
                if not yonetici_modu:
                    st.info("🗑️ Depo silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("depo_sil_form"):
                        st.markdown("**🗑️ Depo Sil**")
                        if st.session_state.depolar:
                            secilen_sil_depo = st.selectbox("Silinecek Depoyu Seçin", st.session_state.depolar)
                            onay_depo_sil_btn = silme_onay_kutusu("onay_depo_sil")
                            depo_sil_btn = st.form_submit_button("Seçilen Depoyu ve Bağlı Ürünleri Sil", type="primary")

                            if depo_sil_btn:
                                if not onay_depo_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                elif len(st.session_state.depolar) <= 1:
                                    st.error("⚠️ Sistemde en az 1 depo kalmalıdır, tamamen silemezsiniz!")
                                else:
                                    otomatik_yedek_al("Depo silme: " + str(secilen_sil_depo))
                                    
                                    # Silinecek depoya bağlı alım kayıtlarını sakla (Geri Al için)
                                    silinecek_girisler = [g for g in st.session_state.girisler if g.get("depo") == secilen_sil_depo]
                                    
                                    st.session_state.depolar.remove(secilen_sil_depo)
                                    depoları_kaydet(st.session_state.depolar)
                                
                                    st.session_state.girisler = [g for g in st.session_state.girisler if g.get("depo") != secilen_sil_depo]
                                    verileri_kaydet(st.session_state.girisler)

                                    st.session_state["son_depo_kat_islem"] = {
                                        "tur": "depo_sil",
                                        "ad": secilen_sil_depo,
                                        "silinen_girisler": silinecek_girisler
                                    }

                                    st.success(f"🎉 Başarılı! '{secilen_sil_depo}' deposu ve bağlı ürünler silindi.")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.info("Silinecek depo bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Aktif Depolar Listesi")
            depo_tablosu = [{"Depo Adı": d} for d in st.session_state.depolar]
            ozel_html_tablo_goster(depo_tablosu)

        # TAB 2: KATEGORİ YÖNETİMİ
        with depo_tab2:
            col_kat_ekle, col_kat_sil = st.columns(2)
            with col_kat_ekle:
                with st.form("yeni_kat_ekle_form"):
                    st.markdown("**➕ Yeni Ürün Kategorisi Ekle**")
                    yeni_kat_adi = st.text_input("Kategori Adı (Örn: TEK KULLANIMLIK / AMBALAJ)").strip().upper()
                    kat_ekle_btn = st.form_submit_button("Kategoriyi Kaydet", type="primary")

                    if kat_ekle_btn and yeni_kat_adi:
                        if yeni_kat_adi in st.session_state.kategoriler:
                            st.error("⚠️ Bu kategori zaten mevcut!")
                        else:
                            st.session_state.kategoriler.append(yeni_kat_adi)
                            supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)
                            
                            st.session_state["son_depo_kat_islem"] = {
                                "tur": "kat_ekle",
                                "ad": yeni_kat_adi
                            }
                            
                            st.success(f"🎉 Başarılı! '{yeni_kat_adi}' kategorisi eklendi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

            with col_kat_sil:
                if not yonetici_modu:
                    st.info("🗑️ Kategori silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("kat_sil_form"):
                        st.markdown("**🗑️ Ürün Kategorisi Sil**")
                        if st.session_state.kategoriler:
                            secilen_sil_kat = st.selectbox("Silinecek Kategoriyi Seçin", st.session_state.kategoriler)
                            onay_kat_sil_btn = silme_onay_kutusu("onay_kat_sil")
                            kat_sil_btn = st.form_submit_button("Seçilen Kategoriyi Sil", type="primary")

                            if kat_sil_btn:
                                if not onay_kat_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                elif len(st.session_state.kategoriler) <= 1:
                                    st.error("⚠️ Sistemde en az 1 kategori kalmalıdır!")
                                else:
                                    st.session_state.kategoriler.remove(secilen_sil_kat)
                                    supabase_veri_kaydet("kategoriler_listesi", st.session_state.kategoriler)

                                    st.session_state["son_depo_kat_islem"] = {
                                        "tur": "kat_sil",
                                        "ad": secilen_sil_kat
                                    }

                                    st.success(f"🎉 Başarılı! '{secilen_sil_kat}' kategorisi silindi.")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.info("Silinecek kategori bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Ürün Kategorileri Listesi")
            kat_tablosu = [{"Kategori Adı": k} for k in st.session_state.kategoriler]
            ozel_html_tablo_goster(kat_tablosu)

# DEMİRBAŞ YÖNETİMİ
elif menu == "Demirbaş Yönetimi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🛠️ Aşevi Demirbaş ve Ekipman Yönetimi")
        st.markdown("Aşevinde bulunan demirbaşları, mutfak ekipmanlarını ve malzemeleri buradan ekleyebilir, durumlarını (Sağlam, Bakımda vb.) takip edebilirsiniz.")

        # Son Demirbaş İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_demirbas_islem"):
            son_islem = st.session_state["son_demirbas_islem"]
            tur = son_islem.get("tur")
            d_obj = son_islem.get("obje")
            
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "ekle":
                    st.info(f"💡 **Son İşlem:** '{d_obj.get('ad')}' demirbaşı eklendi (ID: {d_obj.get('id')}).")
                elif tur == "sil":
                    st.info(f"💡 **Son İşlem:** '{d_obj.get('ad')}' demirbaş kaydı silindi (ID: {d_obj.get('id')}).")
            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_dem_son"):
                    otomatik_yedek_al("Demirbaş işlemi geri alma: " + str(d_obj.get("id")))
                    
                    if tur == "ekle":
                        st.session_state.demirbaslar = [d for d in st.session_state.demirbaslar if d.get("id") != d_obj.get("id")]
                    elif tur == "sil":
                        if not any(d.get("id") == d_obj.get("id") for d in st.session_state.demirbaslar):
                            st.session_state.demirbaslar.append(d_obj)
                    
                    demirbasları_kaydet(st.session_state.demirbaslar)
                    st.session_state.pop("son_demirbas_islem", None)
                    st.success(f"🎉 '{d_obj.get('ad')}' kaydı üzerine yapılan işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        col_b_dem, col_indir_dem = st.columns([2, 2])
        with col_b_dem:
            st.subheader("📋 Kayıtlı Demirbaş Listesi")

        demirbas_tablo = []
        excel_demirbas_listesi = []
        for d in st.session_state.demirbaslar:
            demirbas_tablo.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })
            excel_demirbas_listesi.append({
                "Demirbaş ID": d.get("id", "-"),
                "Demirbaş Adı": d.get("ad", "-"),
                "Kategori": d.get("kategori", "-"),
                "Adet": d.get("adet", 1),
                "Durumu": d.get("durum", "Sağlam"),
                "Zimmetli Sorumlu": d.get("zimmet", "-"),
                "Kayıt Tarihi": d.get("tarih", "-")
            })

        excel_dem_data = tablo_to_excel_bytes(excel_demirbas_listesi, "Aziziye Aşevi - Demirbaş Listesi")
        pdf_dem_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Demirbaş Listesi", excel_demirbas_listesi)

        with col_indir_dem:
            ortak_indirme_alani(excel_dem_data, pdf_dem_data, "demirbas_listesi_raporu", "demirbas_sayfasi")

        if salt_okunur_modu:
            st.warning("👀 Salt okunur modundasınız. Yeni demirbaş ekleyemez veya düzenleyemezsiniz.")
        else:
            col_dem_ekle, col_dem_sil = st.columns(2)
            with col_dem_ekle:
                with st.form("demirbas_ekle_form"):
                    st.markdown("**➕ Yeni Demirbaş Ekle**")
                    d_ad = st.text_input("Demirbaş Adı (Örn: Sanayi Tipi Fırın)").strip()
                    d_kat = st.selectbox("Kategori", ["Mutfak Ekipmanı", "Elektronik", "Mobilya", "Taşıt / Lojistik", "Diğer"])
                    d_adet = st.number_input("Adet", min_value=1, value=1, step=1)
                    d_durum = st.selectbox("Durumu", ["Sağlam", "Bakımda", "Hurda / Kullanılamaz"])
                    d_zimmet = st.text_input("Zimmetli Sorumlu / Yer (Örn: Aşçıbaşı)").strip()
                    d_tarih = st.date_input("Kayıt Tarihi", value=datetime.date.today())

                    dem_ekle_btn = st.form_submit_button("Demirbaş Kaydet", type="primary")
                    if dem_ekle_btn and d_ad:
                        yeni_d_id = yeni_id_uret("DEM-", st.session_state.demirbaslar)
                        yeni_dem_obj = {
                            "id": yeni_d_id,
                            "ad": d_ad,
                            "kategori": d_kat,
                            "adet": int(d_adet),
                            "durum": d_durum,
                            "zimmet": d_zimmet if d_zimmet else "Belirtilmemiş",
                            "tarih": str(d_tarih)
                        }
                        st.session_state.demirbaslar.append(yeni_dem_obj)
                        demirbasları_kaydet(st.session_state.demirbaslar)
                        
                        st.session_state["son_demirbas_islem"] = {
                            "tur": "ekle",
                            "obje": yeni_dem_obj
                        }
                        
                        st.success(f"🎉 Başarılı! '{d_ad}' demirbaş listesine eklendi.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

            with col_dem_sil:
                if not yonetici_modu:
                    st.info("🗑️ Demirbaş silme yetkisi yalnızca Admin'e aittir.")
                else:
                    with st.form("demirbas_sil_form"):
                        st.markdown("**🗑️ Demirbaş Sil**")
                        if st.session_state.demirbaslar:
                            dem_secenekleri = [f"{d['id']} - {d['ad']} ({d['kategori']})" for d in st.session_state.demirbaslar]
                            secilen_sil_dem = st.selectbox(
                                "Silinecek Demirbaşı Seçin",
                                dem_secenekleri,
                                index=None,
                                placeholder="Demirbaş Seçiniz...",
                                key="dem_sil_selectbox"
                            )
                            onay_dem_sil_btn = silme_onay_kutusu("onay_demirbas_sil")
                            dem_sil_btn = st.form_submit_button("Seçilen Demirbaş Kaydını Sil", type="primary")

                            if dem_sil_btn:
                                if not secilen_sil_dem:
                                    st.error("⚠️ Lütfen silmek istediğiniz demirbaşı seçin!")
                                elif not onay_dem_sil_btn:
                                    st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                else:
                                    otomatik_yedek_al("Demirbaş silme: " + str(secilen_sil_dem))
                                    sil_id = secilen_sil_dem.split(" - ")[0]
                                    silinen_obj = next((d for d in st.session_state.demirbaslar if d["id"] == sil_id), None)
                                    
                                    if silinen_obj:
                                        st.session_state.demirbaslar = [d for d in st.session_state.demirbaslar if d["id"] != sil_id]
                                        demirbasları_kaydet(st.session_state.demirbaslar)
                                        
                                        st.session_state["son_demirbas_islem"] = {
                                            "tur": "sil",
                                            "obje": silinen_obj
                                        }

                                        st.success("🎉 Başarılı! Demirbaş kaydı silindi.")
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun()
                        else:
                            st.info("Silinecek demirbaş bulunmuyor.")

        st.markdown("---")
        st.subheader("📋 Kayıtlı Demirbaş Tablosu")
        if demirbas_tablo:
            ozel_html_tablo_goster(demirbas_tablo)
        else:
            st.info("Kayıtlı demirbaş bulunmuyor.")
            
# 3. ÜRÜN SİL / DÜZENLE
elif menu == "Ürün Sil / Düzenle":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Sistemden Ürün veya Kayıt Silme")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda silme işlemi gerçekleştiremezsiniz.")
        elif not yonetici_modu:
            st.warning("⚠️ Bu ekrana erişmek için **Admin** hesabıyla giriş yapmalısınız.")
        else:
            if st.session_state.silme_mesaji:
                st.success(st.session_state.silme_mesaji)
                st.session_state.silme_mesaji = ""

            # Son Silme İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_silinen_kayit"):
                son_silinen = st.session_state["son_silinen_kayit"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Silinen Kayıt:** {son_silinen.get('urun')} (ID: {son_silinen.get('id')} - Kalan: {son_silinen.get('kalan')} {son_silinen.get('birim')})")
                with c_undo2:
                    if st.button("↩️ Silme İşlemini Geri Al", type="secondary", key="btn_undo_silme_son"):
                        # Silinen kaydı depoya geri ekle
                        st.session_state.girisler.append(son_silinen)
                        verileri_kaydet(st.session_state.girisler)

                        # Silinen ürün loglarından ilgili kaydı temizle
                        silinen_id = son_silinen.get("id")
                        st.session_state.silinen_urun_loglari = [
                            l for l in st.session_state.silinen_urun_loglari if l.get("kayit_id") != silinen_id
                        ]
                        silinen_urun_loglarini_kaydet(st.session_state.silinen_urun_loglari)

                        st.session_state.pop("son_silinen_kayit", None)
                        st.success(f"🎉 Kayıt ID {silinen_id} ({son_silinen.get('urun')}) depoya ve sisteme geri yüklendi!")
                        time.sleep(1)
                        st.rerun()

            if not st.session_state.girisler:
                st.info("Sistemde silinecek kayıt bulunmuyor.")
            else:
                with st.form("urun_silme_formu"):
                    secenekler = [
                        f"{g['id']} - {g['urun']} (Eklenme: {g.get('tarih', '-')}, Kalan: {g['kalan']} {g['birim']}, Fiyat: {g.get('fiyat', 0)} TL)"
                        for g in st.session_state.girisler
                    ]
                    secilen_kayit_str = st.selectbox(
                        "Silmek İstediğiniz Kaydı / Faturayı Seçin",
                        secenekler,
                        index=None,
                        placeholder="Silinecek kaydı seçiniz...",
                        key="urun_silme_select_box"
                    )
                    silme_nedeni_input = st.text_input(
                        "Silme Nedeni / Gerekçesi", "Örn: Yanlış giriş"
                    )
                    onay_sil_onay_btn = silme_onay_kutusu("onay_urun_sil")
                    sil_onay_btn = st.form_submit_button(
                        "Seçilen Kaydı Kalıcı Olarak Sil", type="primary"
                    )

                    if sil_onay_btn:
                        if not secilen_kayit_str:
                            st.error("⚠️ Lütfen silmek istediğiniz kaydı listeden seçin!")
                        elif not onay_sil_onay_btn:
                            st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                        else:
                            secilen_id = secilen_kayit_str.split(" - ")[0]
                            ilgili_oge = next(
                                (g for g in st.session_state.girisler if g["id"] == secilen_id),
                                None,
                            )
                            if ilgili_oge:
                                otomatik_yedek_al("Kayıt silme: " + str(ilgili_oge.get("id")))
                                silinen_urun_adi = ilgili_oge["urun"]
                                
                                # Son silinen kaydı sakla (Geri Al için)
                                st.session_state["son_silinen_kayit"] = ilgili_oge.copy()

                                st.session_state.silinen_urun_loglari.append({
                                    "tarih": simdi_tr_str("%Y-%m-%d %H:%M"),
                                    "urun": silinen_urun_adi,
                                    "kayit_id": ilgili_oge["id"],
                                    "fatura_no": ilgili_oge.get("fatura_no", "-"),
                                    "neden": (
                                        silme_nedeni_input
                                        if silme_nedeni_input
                                        else "Belirtilmedi"
                                    ),
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                })
                                silinen_urun_loglarini_kaydet(
                                    st.session_state.silinen_urun_loglari
                                )
                                st.session_state.girisler = [
                                    g
                                    for g in st.session_state.girisler
                                    if g["id"] != secilen_id
                                ]
                                verileri_kaydet(st.session_state.girisler)
                                st.session_state.silme_mesaji = (
                                    f"🎉 Başarılı! {silinen_urun_adi} kayıt ID {secilen_id} sistemden silindi."
                                )
                                st.balloons()
                                time.sleep(1)
                                st.rerun()

        st.markdown("---")
        
        col_b_silinen, col_indir_silinen = st.columns([2, 2])
        with col_b_silinen:
            st.subheader("📋 Silinen Ürünler Arşivi")

        if st.session_state.silinen_urun_loglari:
            silinen_tablo_verisi = [
                {
                    "Silinme Tarihi": sl["tarih"],
                    "Kayıt ID": sl.get("kayit_id", "-"),
                    "Ürün Adı": sl["urun"],
                    "Silme Nedeni": sl["neden"],
                    "İşlemi Yapan": sl.get("islem_yapan", "admin"),
                }
                for sl in st.session_state.silinen_urun_loglari
            ]
            
            excel_silinen_data = tablo_to_excel_bytes(silinen_tablo_verisi, "Aziziye Aşevi - Silinen Ürünler Arşivi")
            pdf_silinen_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Silinen Ürünler Arşivi", silinen_tablo_verisi)
            with col_indir_silinen:
                ortak_indirme_alani(excel_silinen_data, pdf_silinen_data, "silinen_urunler_arsivi", "silinen_arsiv_sayfasi")

            ozel_html_tablo_goster(silinen_tablo_verisi)
        else:
            st.info("Silinmiş ürün kaydı bulunmuyor.")

# 4. FİRE / ZAYİAT GİRİŞİ
elif menu == "Fire / Zayiat Girişi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🗑️ Fire / Zayiat Bildirimi")
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda fire düşemezsiniz.")
        else:
            # Son Fire İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_fire_kaydi"):
                son_fire = st.session_state["son_fire_kaydi"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Fire Kaydı:** {son_fire.get('urun')} ({son_fire.get('miktar')} Miktar - Zarar: {son_fire.get('tutar', 0):,.2f} ₺ - Tarih: {son_fire.get('tarih')})")
                with c_undo2:
                    if st.button("↩️ Son Fire İşlemini Geri Al", type="secondary", key="btn_undo_fire_son"):
                        otomatik_yedek_al("Fire girişi geri alma: " + str(son_fire.get("urun")))
                        
                        # Düşülen miktarları orijinal stok girişlerine iade et
                        for item in son_fire.get("dusulen_kayitlar", []):
                            for g in st.session_state.girisler:
                                if g.get("id") == item["id"]:
                                    g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                        # Kullanım loglarından sil
                        log_target = son_fire.get("log_objesi")
                        if log_target and log_target in st.session_state.kullanim_loglari:
                            st.session_state.kullanim_loglari.remove(log_target)

                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)
                        
                        st.session_state.pop("son_fire_kaydi", None)
                        st.success(f"🎉 {son_fire.get('urun')} için girilen fire bildirimi geri alındı ve stok iade edildi!")
                        time.sleep(1)
                        st.rerun()

            benzersiz_urunler = sorted(
                list(set(str(g.get("urun", "")).strip().upper() for g in st.session_state.girisler if g.get("urun")))
            )
            
            if not benzersiz_urunler:
                st.info("Sistemde kayıtlı ürün bulunmuyor.")
            else:
                col_f_t1, col_f_t2 = st.columns(2)
                with col_f_t1:
                    fire_tarihi_secim = st.date_input("📅 Fire / Zayiat Tarihi", value=datetime.date.today(), key="fire_tarih_inp")
                with col_f_t2:
                    fire_saati_secim = st.time_input("⏰ Fire Saati", value=datetime.datetime.now().time(), key="fire_saat_inp")
                fire_tarih_str = f"{fire_tarihi_secim.strftime('%Y-%m-%d')} {fire_saati_secim.strftime('%H:%M')}"

                secilen_gercek_urun = st.selectbox(
                    "Fire Düşülecek Ürünü Seçin",
                    benzersiz_urunler,
                    index=None,
                    placeholder="Ürün Seçiniz...",
                    key="fire_urun_secim_box"
                )
                
                if secilen_gercek_urun:
                    ilgili_girisler = [
                        g
                        for g in st.session_state.girisler
                        if str(g.get("urun", "")).strip().upper() == str(secilen_gercek_urun).strip().upper()
                    ]
                    toplam_stok = sum(float(g.get("kalan", 0)) for g in ilgili_girisler)
                    aktif_ilgili_girisler = [g for g in ilgili_girisler if float(g.get("kalan", 0)) > 0]

                    en_son_fiyat = 0.0
                    if ilgili_girisler:
                        en_son_kayit = max(
                            ilgili_girisler, key=lambda x: str(x.get("tarih", ""))
                        )
                        en_son_fiyat = float(en_son_kayit.get("fiyat", 0.0))

                    st.info(
                        f"Güncel Toplam Stok ({secilen_gercek_urun}): {toplam_stok} | Baz Alınan Birim Fiyat: {en_son_fiyat:,.2f} ₺"
                    )
                    
                    fire_miktari = st.number_input(
                        "Fire Miktarı",
                        min_value=0.1,
                        value=1.0,
                        step=0.1,
                        key="fire_miktar_inp"
                    )
                    fire_aciklama = st.text_input(
                        "Fire Açıklaması / Nedeni",
                        placeholder="Örn: Bozuldu, döküldü, son kullanma tarihi geçti...",
                        key="fire_aciklama_inp"
                    ).strip()

                    if st.button("Fireyi Düş ve Kaydet", type="primary", key="fire_kaydet_button"):
                        if fire_miktari <= 0:
                            st.error("⚠️ Lütfen 0'dan büyük bir fire miktarı girin!")
                        elif fire_miktari > toplam_stok:
                            st.error(f"⚠️ Hata: Girilen fire miktarı ({fire_miktari}), güncel toplam stoktan ({toplam_stok}) büyük olamaz!")
                        else:
                            kalan_dusulecek = fire_miktari
                            dusulen_kayitlar = []

                            for g in aktif_ilgili_girisler:
                                if kalan_dusulecek <= 0:
                                    break
                                if float(g["kalan"]) >= kalan_dusulecek:
                                    dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek})
                                    g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                    kalan_dusulecek = 0
                                else:
                                    dusulen = float(g["kalan"])
                                    dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen})
                                    g["kalan"] = 0.0
                                    kalan_dusulecek -= dusulen

                            toplam_zarar = fire_miktari * en_son_fiyat

                            yeni_log = {
                                "tarih": fire_tarih_str,
                                "urun": secilen_gercek_urun,
                                "tur": "Fire/Zayiat",
                                "miktar": fire_miktari,
                                "tutar": toplam_zarar,
                                "aciklama": (fire_aciklama if fire_aciklama else "Belirtilmedi"),
                                "islem_yapan": st.session_state.aktif_kullanici,
                            }

                            st.session_state.kullanim_loglari.append(yeni_log)
                            
                            # Son fire kaydını session_state içinde sakla
                            st.session_state["son_fire_kaydi"] = {
                                "urun": secilen_gercek_urun,
                                "miktar": fire_miktari,
                                "tutar": toplam_zarar,
                                "tarih": fire_tarih_str,
                                "dusulen_kayitlar": dusulen_kayitlar,
                                "log_objesi": yeni_log
                            }

                            verileri_kaydet(st.session_state.girisler)
                            loglari_kaydet(st.session_state.kullanim_loglari)

                            st.success(
                                f"🎉 Başarılı! {secilen_gercek_urun} için fire düşüldü ({fire_tarih_str}). Toplam zarar: {toplam_zarar:,.2f} ₺"
                            )
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

        st.markdown("---")
        
        col_b_fire, col_indir_fire = st.columns([2, 2])
        with col_b_fire:
            st.subheader("📋 Kayıtlı Fire ve Zayiatlar Listesi")
        
        if "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi" in aktif_k_maskeleri:
            st.info("🔒 Kayıtlı Fire ve Zayiatlar Listesi tablosu bu kullanıcı için tamamen maskelenmiştir (gizlenmiştir).")
        else:
            fire_loglari = [
                l
                for l in st.session_state.kullanim_loglari
                if l.get("tur") == "Fire/Zayiat"
            ]
            if fire_loglari:
                fire_tablo_verisi = []
                for f_log in reversed(fire_loglari):
                    fire_tablo_verisi.append({
                        "Tarih / Saat": f_log.get("tarih", "-"),
                        "Ürün Adı": f_log.get("urun", "-"),
                        "Fire Miktarı": f"{f_log.get('miktar', 0)}",
                        "Toplam Tutar": f"{f_log.get('tutar', 0):,.2f} ₺",
                        "İşlemi Yapan": f_log.get("islem_yapan", "admin"),
                        "Açıklama": f_log.get("aciklama", "—"),
                    })
                
                excel_fire_data = tablo_to_excel_bytes(fire_tablo_verisi, "Aziziye Aşevi - Fire ve Zayiat Raporu")
                pdf_fire_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Fire ve Zayiat Raporu", fire_tablo_verisi)
                with col_indir_fire:
                    ortak_indirme_alani(excel_fire_data, pdf_fire_data, "fire_ve_zayiat_listesi", "fire_arsiv_sayfasi")

                ozel_html_tablo_goster(fire_tablo_verisi)
            else:
                st.info("Sistemde kayıtlı fire / zayiat bulunmuyor.")

# TOPLU STOK DÜŞÜMÜ & SARFİYAT
elif menu == "Toplu Stok Düşümü & Sarfiyat":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("🔄 Toplu Stok Düşümü ve Kullanılan Ürünler")
        st.markdown("Geçmiş yemek tarifleri seçmek zorunda kalmadan, kullanılan malzemeleri ve miktarlarını seçerek doğrudan stoktan düşürebilir ve kullanılan ürünler listesine ekleyebilirsiniz.")
        
        if salt_okunur_modu:
            st.warning("👀 Salt okunur (Yönetim/Misafir) modundasınız. Bu ekranda toplu stok düşümü yapamazsınız.")
        else:
            # Son Sarfiyat İşlemini Geri Al Butonu ve Bildirimi
            if st.session_state.get("son_toplu_sarfiyat_kaydi"):
                son_sarf = st.session_state["son_toplu_sarfiyat_kaydi"]
                c_undo1, c_undo2 = st.columns([3, 1])
                with c_undo1:
                    st.info(f"💡 **Son Sarfiyat Kaydı:** {son_sarf.get('urun')} ({son_sarf.get('miktar')} Miktar - Tutar: {son_sarf.get('tutar', 0):,.2f} ₺ - Tarih: {son_sarf.get('tarih')})")
                with c_undo2:
                    if st.button("↩️ Son Sarfiyat İşlemini Geri Al", type="secondary", key="btn_undo_toplu_sarf_son"):
                        otomatik_yedek_al("Toplu sarfiyat geri alma: " + str(son_sarf.get("urun")))
                        
                        # Düşülen miktarları orijinal stok girişlerine iade et
                        for item in son_sarf.get("dusulen_kayitlar", []):
                            for g in st.session_state.girisler:
                                if g.get("id") == item["id"]:
                                    g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                        # Kullanım loglarından sil
                        log_target = son_sarf.get("log_objesi")
                        if log_target and log_target in st.session_state.kullanim_loglari:
                            st.session_state.kullanim_loglari.remove(log_target)

                        verileri_kaydet(st.session_state.girisler)
                        loglari_kaydet(st.session_state.kullanim_loglari)
                        
                        st.session_state.pop("son_toplu_sarfiyat_kaydi", None)
                        st.success(f"🎉 {son_sarf.get('urun')} için yapılan stok düşümü geri alındı ve stok iade edildi!")
                        time.sleep(1)
                        st.rerun()

            col_form1, col_form2 = st.columns(2)
            
            with col_form1:
                st.subheader("Malzeme Çıkış Formu")
                benzersiz_urunler_toplu = sorted(list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun"))))
                
                if benzersiz_urunler_toplu:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        toplu_tarih_secim = st.date_input("📅 Sarfiyat Tarihi", value=datetime.date.today(), key="toplu_tarih_inp")
                    with col_t2:
                        toplu_saat_secim = st.time_input("⏰ Sarfiyat Saati", value=datetime.datetime.now().time(), key="toplu_saat_inp")
                    toplu_tarih_str = f"{toplu_tarih_secim.strftime('%Y-%m-%d')} {toplu_saat_secim.strftime('%H:%M')}"

                    selected_item = st.selectbox(
                        "Malzeme Seçin",
                        benzersiz_urunler_toplu,
                        index=None,
                        placeholder="Malzeme Seçiniz...",
                        key="toplu_malzeme_selectbox"
                    )
                    
                    if selected_item:
                        ilgili_girisler_toplu = [g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == selected_item.strip().upper()]
                        current_stock = sum(float(g.get("kalan", 0)) for g in ilgili_girisler_toplu)
                        aktif_ilgili_toplu = [g for g in ilgili_girisler_toplu if float(g.get("kalan", 0)) > 0]
                        
                        unit = ilgili_girisler_toplu[0].get("birim", "Kg") if ilgili_girisler_toplu else "Kg"
                        
                        st.info(f"Mevcut Toplam Stok ({selected_item}): {current_stock} {unit}")
                        
                        used_amount = st.number_input(f"Kullanılan Miktar ({unit})", min_value=0.1, value=1.0, step=0.5)
                        description = st.text_input("Açıklama / Not (Örn: Kazan yemeği, günlük dağıtım vb.)", "Günlük Aşevi Üretimi")
                        
                        if st.button("Stoktan Düş ve Kullanılanlara Ekle", type="primary"):
                            if used_amount <= 0:
                                st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                            elif used_amount > current_stock:
                                st.error(f"⚠️ Hata: Kullanılan miktar ({used_amount}), mevcut toplam stoktan ({current_stock}) büyük olamaz!")
                            else:
                                kalan_dusulecek = used_amount
                                harcanan_tutar = 0.0
                                dusulen_kayitlar = []
                                
                                for g in aktif_ilgili_toplu:
                                    if kalan_dusulecek <= 0:
                                        break
                                    if float(g["kalan"]) >= kalan_dusulecek:
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek})
                                        g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                        harcanan_tutar += kalan_dusulecek * float(g["fiyat"])
                                        kalan_dusulecek = 0
                                    else:
                                        dusulen = float(g["kalan"])
                                        dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen})
                                        g["kalan"] = 0.0
                                        harcanan_tutar += dusulen * float(g["fiyat"])
                                        kalan_dusulecek -= dusulen
                                
                                yeni_log = {
                                    "tarih": toplu_tarih_str,
                                    "urun": selected_item,
                                    "tur": f"Toplu Sarfiyat ({description})",
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                }

                                st.session_state.kullanim_loglari.append(yeni_log)
                                
                                # Son sarfiyat kaydını session_state içinde sakla
                                st.session_state["son_toplu_sarfiyat_kaydi"] = {
                                    "urun": selected_item,
                                    "miktar": used_amount,
                                    "tutar": harcanan_tutar,
                                    "tarih": toplu_tarih_str,
                                    "dusulen_kayitlar": dusulen_kayitlar,
                                    "log_objesi": yeni_log
                                }

                                verileri_kaydet(st.session_state.girisler)
                                loglari_kaydet(st.session_state.kullanim_loglari)
                                
                                st.success(f"🎉 Başarılı! {toplu_tarih_str} tarihli {used_amount} {unit} {selected_item} stoktan düşüldü ve loglara eklendi!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                else:
                    st.info("Depoda kayıtlı ürün bulunmuyor.")

            with col_form2:
                st.subheader("Geçmişte Kullanılan Ürünler (Sarfiyat Logu)")
                toplu_sarfiyat_loglari = [l for l in st.session_state.kullanim_loglari if "Toplu Sarfiyat" in l.get("tur", "")]
                if toplu_sarfiyat_loglari:
                    tablo_sarf = []
                    for s_log in reversed(toplu_sarfiyat_loglari):
                        tablo_sarf.append({
                            "Tarih / Saat": s_log.get("tarih", "-"),
                            "Malzeme": s_log.get("urun", "-"),
                            "Miktar": f"{s_log.get('miktar', 0)}",
                            "Tutar": f"{s_log.get('tutar', 0):,.2f} ₺",
                            "Açıklama": s_log.get("tur", "-"),
                            "İşlemi Yapan": s_log.get("islem_yapan", "-"),
                        })
                    ozel_html_tablo_goster(tablo_sarf)
                else:
                    st.info("Henüz toplu stok düşümü yapılmadı.")
                    
# 5. GÜNLÜK YEMEK ÜRETİMİ & MALİYET RAPORU
elif menu == "Günlük Yemek Üretimi & Maliyet Raporu":
    col_baslik_r, col_indir_alan = st.columns([2, 2])
    with col_baslik_r:
        st.header("🍲 Günlük Yemek Üretimi, Kullanımı ve Tarih Aralığı Takibi")

    # Son Yemek Üretim İşlemini Geri Al Butonu ve Bildirimi
    if st.session_state.get("son_yemek_uretim_kaydi"):
        son_uretim = st.session_state["son_yemek_uretim_kaydi"]
        c_undo1, c_undo2 = st.columns([3, 1])
        with c_undo1:
            st.info(
                f"💡 **Son Yemek Üretimi:** '{son_uretim.get('yemek_adi')}' ({son_uretim.get('kisi_sayisi')} Kişilik) - "
                f"Toplam Maliyet: {son_uretim.get('toplam_maliyet', 0):,.2f} ₺ - Tarih: {son_uretim.get('tarih')}"
            )
        with c_undo2:
            if st.button("↩️ Son Üretimi Geri Al", type="secondary", key="btn_undo_uretim_son"):
                otomatik_yedek_al("Yemek üretimi geri alma: " + str(son_uretim.get("yemek_adi")))
                
                # 1. Stoktan düşülen miktarları depoya iade et
                for item in son_uretim.get("dusulen_kayitlar", []):
                    for g in st.session_state.girisler:
                        if g.get("id") == item["id"]:
                            g["kalan"] = float(g.get("kalan", 0)) + float(item["miktar"])

                # 2. Yemek üretim arşivinden kaydı sil
                arsiv_target = son_uretim.get("arsiv_objesi")
                if arsiv_target and arsiv_target in st.session_state.yemek_uretim_arsivi:
                    st.session_state.yemek_uretim_arsivi.remove(arsiv_target)

                # 3. Kullanım loglarından ilgili kayıtları sil
                eklenen_loglar = son_uretim.get("eklenen_loglar", [])
                for log_item in eklenen_loglar:
                    if log_item in st.session_state.kullanim_loglari:
                        st.session_state.kullanim_loglari.remove(log_item)

                # 4. Değişiklikleri veritabanına kaydet
                verileri_kaydet(st.session_state.girisler)
                loglari_kaydet(st.session_state.kullanim_loglari)
                yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)

                st.session_state.pop("son_yemek_uretim_kaydi", None)
                st.success(f"🎉 '{son_uretim.get('yemek_adi')}' üretimi geri alındı, malzemeler stoğa iade edildi ve arşiv temizlendi!")
                time.sleep(1)
                st.rerun()

    col_tarih_mod, col_tarih_sec = st.columns([1.2, 1.8])
    with col_tarih_mod:
        zaman_modu = st.radio(
            "Arşiv Görünüm Modu", ["Tek Tarih", "Tarih Aralığı", "Tüm Zamanlar"], horizontal=True
        )
    with col_tarih_sec:
        if zaman_modu == "Tek Tarih":
            secilen_tarih_filtresi = st.date_input(
                "📅 Sorgulanacak Tarihi Seçin", value=datetime.date.today()
            )
            secilen_tarih_str = secilen_tarih_filtresi.strftime("%Y-%m-%d")
        elif zaman_modu == "Tarih Aralığı":
            c_bas, c_bit = st.columns(2)
            with c_bas:
                bas_tarih_filt = st.date_input("Başlangıç Tarihi", value=datetime.date.today() - datetime.timedelta(days=7))
            with c_bit:
                bit_tarih_filt = st.date_input("Bitiş Tarihi", value=datetime.date.today())
        else:
            secilen_tarih_str = "TÜMÜ"

    if not misafir_modu:
        st.markdown("---")
        st.subheader("🍲 Yeni Yemek Üretim Planı ve Malzeme Düşümü")
        yemek_adi = st.text_input("Çıkan Yemek / Menü Adı", "Ispanak Yemeği")
        kisi_sayisi = st.number_input(
            "Yararlanan Kişi Sayısı", min_value=1, value=200
        )
        uretim_tarihi_input = st.date_input(
            "📅 Yemeğin Yapıldığı Tarih (Geçmiş / Bugün)",
            value=datetime.date.today(),
        )
        uretim_tarih_str = uretim_tarihi_input.strftime("%Y-%m-%d")

        benzersiz_urunler = sorted(
            list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
        )

        if "sepet" not in st.session_state:
            st.session_state.sepet = []

        if not salt_okunur_modu:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                secilen_urun = st.selectbox(
                    "Malzeme Seç",
                    benzersiz_urunler if benzersiz_urunler else [],
                    index=None,
                    placeholder="Malzeme Seçiniz...",
                    key="yemek_urun"
                )
            with col2:
                stok_max = 0.0
                if secilen_urun:
                    ilgili_girisler = [
                        g
                        for g in st.session_state.girisler
                        if g.get("urun", "").strip().upper() == secilen_urun.strip().upper()
                    ]
                    stok_max = sum(g.get("kalan", 0) for g in ilgili_girisler)
                
                kullanilacak_miktar = st.number_input(
                    f"Miktar (Toplam Stok: {stok_max})",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                    key="yemek_miktar",
                )
            with col3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Sepete Ekle", use_container_width=True):
                    if not secilen_urun:
                        st.error("⚠️ Lütfen sepete eklemek için bir malzeme seçin!")
                    elif kullanilacak_miktar <= 0:
                        st.error("⚠️ Lütfen 0'dan büyük bir miktar girin!")
                    else:
                        st.session_state.sepet.append(
                            {"urun": secilen_urun, "miktar": kullanilacak_miktar}
                        )
                        st.success("Eklendi!")
                        st.rerun()

        st.markdown("---")
        st.subheader("Seçilen Malzemeler")

        if st.session_state.sepet:
            if not salt_okunur_modu:
                if st.button("🔄 Tümünü Sıfırla"):
                    st.session_state.sepet = []
                    st.rerun()

            toplam_maliyet = 0.0
            excel_sepet_liste = []

            silinecek_index = None
            for idx, item in enumerate(st.session_state.sepet):
                urun = item["urun"]
                istenen = item["miktar"]

                ilgili_girisler = [
                    g for g in st.session_state.girisler if g.get("urun", "").strip().upper() == urun.strip().upper()
                ]
                ortalama_fiyat = 0.0
                if ilgili_girisler:
                    toplam_fiyat_degeri = sum(
                        g.get("fiyat", 0) * g.get("miktar", 0) for g in ilgili_girisler
                    )
                    toplam_miktar_degeri = sum(g.get("miktar", 0) for g in ilgili_girisler)
                    ortalama_fiyat = (
                        toplam_fiyat_degeri / toplam_miktar_degeri
                        if toplam_miktar_degeri > 0
                        else 0.0
                    )

                item_maliyeti = istenen * ortalama_fiyat
                toplam_maliyet += item_maliyeti

                c_item_ad, c_item_mik, c_item_mal, c_item_sil = st.columns(
                    [3, 2, 2, 1]
                )
                with c_item_ad:
                    st.markdown(f"• **{urun}**")
                with c_item_mik:
                    st.markdown(f"Miktar: {istenen}")
                with c_item_mal:
                    st.markdown(f"Maliyet: **{item_maliyeti:,.2f} ₺**")
                with c_item_sil:
                    if not salt_okunur_modu:
                        if st.button("❌", key=f"sil_item_{idx}"):
                            silinecek_index = idx

                excel_sepet_liste.append({
                    "Malzeme": urun,
                    "Maliyet (TL)": round(item_maliyeti, 2),
                })

            if silinecek_index is not None:
                st.session_state.sepet.pop(silinecek_index)
                st.rerun()

            if not salt_okunur_modu:
                if st.button(
                    "🍲 Üretimi Tamamla ve Stoktan / Kullanıma Düş", type="primary"
                ):
                    tarih_simdi = simdi_tr_str("%Y-%m-%d %H:%M")

                    arsiv_malzemeler = []
                    dusulen_kayitlar = []
                    eklenen_loglar = []

                    for item in st.session_state.sepet:
                        urun = item["urun"]
                        istenen = item["miktar"]
                        kalan_dusulecek = istenen
                        item_tutar = 0.0
                        ilgili_g = [
                            g
                            for g in st.session_state.girisler
                            if g.get("urun", "").strip().upper() == urun.strip().upper() and g.get("kalan", 0) > 0
                        ]
                        for g in ilgili_g:
                            if kalan_dusulecek <= 0:
                                break
                            if float(g["kalan"]) >= kalan_dusulecek:
                                dusulen_kayitlar.append({"id": g["id"], "miktar": kalan_dusulecek})
                                g["kalan"] = float(g["kalan"]) - kalan_dusulecek
                                item_tutar += kalan_dusulecek * float(g["fiyat"])
                                kalan_dusulecek = 0
                            else:
                                dusulen = float(g["kalan"])
                                dusulen_kayitlar.append({"id": g["id"], "miktar": dusulen})
                                g["kalan"] = 0.0
                                item_tutar += dusulen * float(g["fiyat"])
                                kalan_dusulecek -= dusulen

                        arsiv_malzemeler.append(
                            {"urun": urun, "miktar": istenen, "tutar": item_tutar}
                        )

                        log_obj = {
                            "tarih": f"{uretim_tarih_str} 12:00",
                            "urun": urun,
                            "tur": f"Günlük Kullanım ({yemek_adi})",
                            "miktar": istenen,
                            "tutar": item_tutar,
                            "islem_yapan": st.session_state.aktif_kullanici,
                        }
                        st.session_state.kullanim_loglari.append(log_obj)
                        eklenen_loglar.append(log_obj)

                    arsiv_obj = {
                        "tarih": uretim_tarih_str,
                        "zaman": tarih_simdi,
                        "yemek_adi": yemek_adi,
                        "kisi_sayisi": kisi_sayisi,
                        "malzemeler": arsiv_malzemeler,
                        "toplam_maliyet": toplam_maliyet,
                        "islem_yapan": st.session_state.aktif_kullanici,
                    }
                    st.session_state.yemek_uretim_arsivi.append(arsiv_obj)

                    # Son yemek üretim kaydını sakla (Geri Al için)
                    st.session_state["son_yemek_uretim_kaydi"] = {
                        "yemek_adi": yemek_adi,
                        "kisi_sayisi": kisi_sayisi,
                        "toplam_maliyet": toplam_maliyet,
                        "tarih": uretim_tarih_str,
                        "dusulen_kayitlar": dusulen_kayitlar,
                        "arsiv_objesi": arsiv_obj,
                        "eklenen_loglar": eklenen_loglar
                    }

                    yemek_uretim_arsivini_kaydet(st.session_state.yemek_uretim_arsivi)
                    verileri_kaydet(st.session_state.girisler)
                    loglari_kaydet(st.session_state.kullanim_loglari)
                    st.session_state.sepet = []
                    st.success(
                        f"🎉 Başarılı! {uretim_tarih_str} tarihli üretim arşive kaydedildi."
                    )
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

            st.markdown("---")
            kisi_basi_maliyet = (
                toplam_maliyet / kisi_sayisi if kisi_sayisi > 0 else 0.0
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Toplam Maliyet", f"{toplam_maliyet:,.2f} ₺")
            with m2:
                st.metric("Kişi Başı Maliyet", f"{kisi_basi_maliyet:,.2f} ₺")

            pdf_data = tablo_to_html_pdf_bytes(
                f"Yemek Maliyet Raporu - {yemek_adi}", excel_sepet_liste
            )
            excel_sepet_data = tablo_to_excel_bytes(
                excel_sepet_liste, f"Yemek Maliyet Raporu - {yemek_adi}"
            )
            with col_indir_alan:
                ortak_indirme_alani(
                    excel_sepet_data,
                    pdf_data,
                    "yemek_maliyet_raporu",
                    "yemek_sayfasi",
                )
        else:
            st.info("Henüz sepete malzeme eklenmedi.")

    st.markdown("---")
    
    col_b_arsiv, col_indir_arsiv = st.columns([2, 2])
    with col_b_arsiv:
        if zaman_modu == "Tüm Zamanlar":
            st.subheader("📚 Tüm Zamanların Yemek Üretim ve Maliyet Arşivi")
            secilen_gun_uretimleri = st.session_state.yemek_uretim_arsivi
        elif zaman_modu == "Tek Tarih":
            st.subheader(
                f"📅 Seçilen Tarihteki ({secilen_tarih_str}) Yemek Üretim ve Maliyet Arşivi"
            )
            secilen_gun_uretimleri = [
                u
                for u in st.session_state.yemek_uretim_arsivi
                if u.get("tarih") == secilen_tarih_str
            ]
        else:
            st.subheader(f"📅 Tarih Aralığı Arşivi ({bas_tarih_filt} ile {bit_tarih_filt} arası)")
            secilen_gun_uretimleri = []
            for u in st.session_state.yemek_uretim_arsivi:
                t_str = u.get("tarih", "")
                try:
                    t_dt = datetime.datetime.strptime(t_str, "%Y-%m-%d").date()
                    if bas_tarih_filt <= t_dt <= bit_tarih_filt:
                        secilen_gun_uretimleri.append(u)
                except:
                    pass

    if "3. Sayfa: Yemek Üretim ve Maliyet Arşivi" in aktif_k_maskeleri:
        st.info("🔒 Yemek Üretim ve Maliyet Arşivi bu kullanıcı için maskelenmiştir (gizlenmiştir).")
    else:
        if secilen_gun_uretimleri:
            arsiv_tablo_verisi = []
            excel_arsiv_listesi = []
            for u_kayit in secilen_gun_uretimleri:
                # Toplam Maliyet ve Kişi Başı Maliyet Hesabı
                toplam_maliyet_degeri = float(u_kayit.get("toplam_maliyet", 0))
                if toplam_maliyet_degeri == 0 and u_kayit.get("malzemeler"):
                    toplam_maliyet_degeri = sum(float(m.get("tutar", 0)) for m in u_kayit.get("malzemeler", []))
                
                kisi_sayisi_degeri = int(u_kayit.get("kisi_sayisi", 1) or 1)
                kisi_basi_maliyet = toplam_maliyet_degeri / kisi_sayisi_degeri if kisi_sayisi_degeri > 0 else 0.0

                if misafir_modu:
                    arsiv_tablo_verisi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                    })
                    excel_arsiv_listesi.append({
                        "Tarih": u_kayit.get("tarih", "-"),
                        "Çıkan Yemek Adı": u_kayit.get("yemek_adi", "-"),
                        "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                    })
                else:
                    for m in u_kayit.get("malzemeler", []):
                        arsiv_tablo_verisi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Kullanılan Malzeme": m.get("urun", "-"),
                            "Malzeme Maliyeti": f"{m.get('tutar', 0):,.2f} ₺",
                            "Menü Toplam Maliyeti": f"{toplam_maliyet_degeri:,.2f} ₺",
                            "Kişi Başı Maliyet": f"{kisi_basi_maliyet:,.2f} ₺",
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })
                        excel_arsiv_listesi.append({
                            "Tarih": u_kayit.get("tarih", "-"),
                            "Yemek Adı": u_kayit.get("yemek_adi", "-"),
                            "Kişi Sayısı": u_kayit.get("kisi_sayisi", "-"),
                            "Kullanılan Malzeme": m.get("urun", "-"),
                            "Malzeme Maliyeti (TL)": round(m.get("tutar", 0), 2),
                            "Menü Toplam Maliyeti (TL)": round(toplam_maliyet_degeri, 2),
                            "Kişi Başı Maliyet (TL)": round(kisi_basi_maliyet, 2),
                            "İşlemi Yapan": u_kayit.get("islem_yapan", "-"),
                        })

            rapor_adi_etiketi = "yemek_uretim_raporu_arsiv"
            baslik_etiketi = "Aziziye Aşevi - Yemek Üretim Raporu Arşivi"

            excel_arsiv_data = tablo_to_excel_bytes(
                excel_arsiv_listesi, baslik_etiketi
            )
            pdf_arsiv_data = tablo_to_html_pdf_bytes(baslik_etiketi, excel_arsiv_listesi)

            with col_indir_arsiv:
                ortak_indirme_alani(
                    excel_arsiv_data,
                    pdf_arsiv_data,
                    rapor_adi_etiketi,
                    "arsiv_tarih_araligi",
                )

            ozel_html_tablo_goster(arsiv_tablo_verisi)
        else:
            st.info("Seçilen tarih aralığında kayıtlı yemek üretim ve maliyet arşivi bulunmuyor.")

# 6. KALORİ HESAPLAMA ARACI
elif menu == "Kalori Hesaplama Aracı":
    col_b_kal, col_indir_kal = st.columns([2, 2])
    with col_b_kal:
        st.header("🔥 Kalori Hesaplama Aracı")

    benzersiz_urunler_kalori = sorted(
        list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
    )
    col_k_sec1, col_k_sec2, col_k_sec3 = st.columns([2, 1, 1])
    with col_k_sec1:
        secilen_kalori_urun = st.selectbox(
            "Malzeme Seçin", benzersiz_urunler_kalori if benzersiz_urunler_kalori else ["Yok"], key="kalori_urun_sec"
        )
    with col_k_sec2:
        kalori_miktar_input = st.number_input(
            "Miktar", min_value=0.1, value=1.0, step=0.5, key="kalori_mik"
        )
    with col_k_sec3:
        kalori_birim_input = st.selectbox(
            "Birim", ["Kg", "Adet", "Lt"], key="kalori_brm"
        )

    if st.button("➕ Listeye Ekle"):
        st.session_state.kalori_sepeti.append({
            "urun": secilen_kalori_urun,
            "miktar": kalori_miktar_input,
            "birim": kalori_birim_input,
        })
        st.success("🎉 Başarılı! Eklendi.")
        st.balloons()

    if st.session_state.kalori_sepeti:
        toplam_kalori = sum(
            urun_kalori_hesapla(i["urun"], i["miktar"], i["birim"])
            for i in st.session_state.kalori_sepeti
        )
        st.metric("Toplam Tarif Kalorisi", f"{toplam_kalori:,.0f} kcal")

# 7. İHTİYAÇ SAHİBİ & YEMEK DAĞITIM TAKİBİ
elif menu == "İhtiyaç Sahibi & Yemek Dağıtım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 İhtiyaç Sahibi ve Yemek Dağıtım Takibi")
        st.markdown(
            "Aşevimizden yemek yardımı alan kişilerin kayıtlarını oluşturun, aktif/pasif durumlarını yönetin ve yemek dağıtımlarını takip edin."
        )

        # 1) Son Silinen İhtiyaç Sahibini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_silinen_ihtiyac_sahibi"):
            son_kisi = st.session_state["son_silinen_ihtiyac_sahibi"]
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                st.info(
                    f"💡 **Son Silinen İhtiyaç Sahibi:** {son_kisi.get('ad_soyad')} (Kayıt No: {son_kisi.get('id')} - T.C./Hane: {son_kisi.get('tc_hane', '-')})"
                )
            with c_undo2:
                if st.button("↩️ Silinen Kişiyi Geri Al", type="secondary", key="btn_undo_kisi_sil_son"):
                    otomatik_yedek_al("Silinen ihtiyaç sahibini geri alma: " + str(son_kisi.get("ad_soyad")))
                    
                    # Kişiyi tekrar listeye iade et
                    if not any(k["id"] == son_kisi["id"] for k in st.session_state.ihtiyac_sahipleri):
                        st.session_state.ihtiyac_sahipleri.append(son_kisi)
                    
                    ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                    st.session_state.pop("son_silinen_ihtiyac_sahibi", None)
                    st.success(f"🎉 '{son_kisi.get('ad_soyad')}' ihtiyaç sahibi listesine başarıyla geri yüklendi!")
                    time.sleep(1)
                    st.rerun()

        # 2) Son Toplu Yemek Dağıtımını Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_toplu_dagitim_kaydi"):
            son_dagitim = st.session_state["son_toplu_dagitim_kaydi"]
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                st.info(
                    f"💡 **Son Toplu Dağıtım:** '{son_dagitim.get('menu')}' ({son_dagitim.get('sayi')} Haneye Dağıtıldı - Tarih: {son_dagitim.get('tarih')})"
                )
            with c_undo2:
                if st.button("↩️ Son Dağıtımı Geri Al", type="secondary", key="btn_undo_dagitim_son"):
                    otomatik_yedek_al("Toplu yemek dağıtımı geri alma: " + str(son_dagitim.get("menu")))
                    
                    silinecek_id_listesi = son_dagitim.get("eklenen_id_listesi", [])
                    st.session_state.dagitim_loglari = [
                        d for d in st.session_state.dagitim_loglari if d.get("id") not in silinecek_id_listesi
                    ]
                    
                    dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                    st.session_state.pop("son_toplu_dagitim_kaydi", None)
                    st.success(f"🎉 '{son_dagitim.get('menu')}' için yapılan toplu dağıtım kaydı geri alındı ve silindi!")
                    time.sleep(1)
                    st.rerun()

        tab1, tab2, tab3 = st.tabs([
            "📋 İhtiyaç Sahibi Listesi, Aktif/Pasif ve Ekle",
            "🍲 Toplu Yemek Dağıtımı",
            "📊 Dağıtım Sayacı & Raporları",
        ])

        with tab1:
            col_b_kisi, col_indir_kisi = st.columns([2, 2])
            with col_b_kisi:
                st.subheader("📋 İhtiyaç Sahibi Listesi ve Yönetimi")

            if st.session_state.kisi_silme_mesaji:
                st.success(st.session_state.kisi_silme_mesaji)
                st.session_state.kisi_silme_mesaji = ""

            kisi_liste_gosterim = []
            for k in st.session_state.ihtiyac_sahipleri:
                tc_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "")
                ad_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adı Soyadı" in aktif_k_maskeleri else k.get("ad_soyad", "")
                tel_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Telefon" in aktif_k_maskeleri else k.get("telefon", "")
                adres_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Adres" in aktif_k_maskeleri else k.get("adres", "")
                birey_maskele = "🔒 Gizli" if "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı" in aktif_k_maskeleri else k.get("birey_sayisi", "")
                durum_str = "🟢 Aktif" if k.get("aktif", True) else "🔴 Pasif"

                kisi_liste_gosterim.append({
                    "Kayıt No": k["id"],
                    "Durumu": durum_str,
                    "T.C. Kimlik No / Hane No": tc_maskele,
                    "Adı Soyadı": ad_maskele,
                    "Telefon": tel_maskele,
                    "Adres": adres_maskele,
                    "Birey Sayısı": birey_maskele,
                    "Eklenme Zamanı": k.get("eklenme_tarihi", "-"),
                    "İşlemi Yapan": k.get("islem_yapan", "admin"),
                })

            excel_kisi_data = tablo_to_excel_bytes(
                kisi_liste_gosterim, "Aziziye Aşevi - İhtiyaç Sahipleri Listesi"
            )
            pdf_kisi_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - İhtiyaç Sahipleri Listesi", kisi_liste_gosterim
            )

            with col_indir_kisi:
                ortak_indirme_alani(
                    excel_kisi_data,
                    pdf_kisi_data,
                    "ihtiyac_sahipleri_listesi",
                    "ihtiyac_kisi_sayfasi",
                )

            if not salt_okunur_modu:
                with st.expander("🔄 Vatandaşın Aktif / Pasif Durumunu Değiştir"):
                    with st.form("aktif_pasif_form"):
                        kisi_sec_list = [f"{k['id']} - {k['ad_soyad']} (Mevcut: {'Aktif' if k.get('aktif', True) else 'Pasif'})" for k in st.session_state.ihtiyac_sahipleri]
                        secilen_kisi_durum_str = st.selectbox(
                            "Vatandaş Seçin",
                            kisi_sec_list if kisi_sec_list else [],
                            index=None,
                            placeholder="Vatandaş Seçiniz...",
                            key="kisi_durum_selectbox"
                        )
                        yeni_durum_secim = st.radio("Yeni Durum", ["Aktif Yap", "Pasif Yap"], horizontal=True)
                        durum_degis_btn = st.form_submit_button("Durumu Güncelle", type="primary")

                        if durum_degis_btn:
                            if not secilen_kisi_durum_str:
                                st.error("⚠️ Lütfen durumu güncellenecek vatandaşı seçin!")
                            else:
                                h_id = secilen_kisi_durum_str.split(" - ")[0]
                                for k in st.session_state.ihtiyac_sahipleri:
                                    if k["id"] == h_id:
                                        k["aktif"] = (yeni_durum_secim == "Aktif Yap")
                                ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                                st.success("🎉 Başarılı! Vatandaşın aktif/pasif durumu güncellendi.")
                                st.rerun()

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda yalnızca kayıtlı ihtiyaç sahiplerini gözlemleyebilirsiniz.")
            else:
                col_form_ekle, col_form_sil = st.columns(2)
                with col_form_ekle:
                    with st.form("ihtiyac_sahibi_formu"):
                        st.markdown("**➕ Yeni İhtiyaç Sahibi / Hane Ekle**")
                        yeni_hane = st.text_input("Hane No").strip()
                        yeni_ad = (
                            st.text_input("Adı Soyadı / Hane Unvanı").strip().upper()
                        )
                        yeni_tel = st.text_input("Telefon Numarası")
                        yeni_adres = st.text_input("Açık Adres")
                        yeni_birey = st.number_input(
                            "Aile / Hane Birey Sayısı", min_value=1, value=1
                        )

                        kaydet_btn = st.form_submit_button("İhtiyaç Sahibini Kaydet")
                        if kaydet_btn and yeni_ad:
                            islem_tarihi_str = simdi_tr_str("%Y-%m-%d %H:%M")
                            islem_yapan_kisi = st.session_state.aktif_kullanici
                            st.session_state.ihtiyac_sahipleri.append({
                                "id": yeni_id_uret("IHT-", st.session_state.ihtiyac_sahipleri),
                                "tc_hane": yeni_tc_hane,
                                "ad_soyad": yeni_ad,
                                "telefon": yeni_tel,
                                "adres": yeni_adres,
                                "birey_sayisi": yeni_birey,
                                "aktif": True,
                                "eklenme_tarihi": islem_tarihi_str,
                                "islem_yapan": islem_yapan_kisi,
                            })
                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                            st.success(f"🎉 Başarılı! {yeni_ad} kaydedildi.")
                            st.balloons()
                            st.rerun()

                with col_form_sil:
                    if not yonetici_modu:
                        st.info("🗑️ İhtiyaç sahibi silme yetkisi yalnızca Admin'e aittir.")
                    else:
                        with st.form("ihtiyac_sahibi_sil_formu"):
                            st.markdown("**🗑️ Kayıtlı İhtiyaç Sahibini Sil**")
                            if st.session_state.ihtiyac_sahipleri:
                                kisi_secenekleri_sil = [
                                    f"{k['id']} - {k['ad_soyad']} (T.C./Hane: {k.get('tc_hane', '-')})"
                                    for k in st.session_state.ihtiyac_sahipleri
                                ]
                                secilen_silinecek = st.selectbox(
                                    "Silinecek Kişiyi / Haneyi Seçin",
                                    kisi_secenekleri_sil,
                                    index=None,
                                    placeholder="Kişi Seçiniz...",
                                    key="ihtiyac_sil_selectbox"
                                )
                                onay_sil_btn = silme_onay_kutusu("onay_ihtiyac_sil")
                                sil_btn = st.form_submit_button(
                                    "Seçilen Kişiyi Sistemden Sil", type="primary"
                                )

                                if sil_btn:
                                    if not secilen_silinecek:
                                        st.error("⚠️ Lütfen silinecek kişi/haneyi seçin!")
                                    elif not onay_sil_btn:
                                        st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                    else:
                                        otomatik_yedek_al("İhtiyaç sahibi silme: " + str(secilen_silinecek))
                                        silinecek_id = secilen_silinecek.split(" - ")[0]
                                        silinen_kisi_obj = next(
                                            (
                                                k
                                                for k in st.session_state.ihtiyac_sahipleri
                                                if k["id"] == silinecek_id
                                            ),
                                            None,
                                        )
                                        if silinen_kisi_obj:
                                            # Geri al butonu için sakla
                                            st.session_state["son_silinen_ihtiyac_sahibi"] = silinen_kisi_obj.copy()

                                            silinen_isim = silinen_kisi_obj["ad_soyad"]
                                            st.session_state.ihtiyac_sahipleri = [
                                                k
                                                for k in st.session_state.ihtiyac_sahipleri
                                                if k["id"] != silinecek_id
                                            ]
                                            ihtiyac_sahiplerini_kaydet(st.session_state.ihtiyac_sahipleri)
                                            st.session_state.kisi_silme_mesaji = (
                                                f"🎉 Başarılı! {silinen_isim} silindi."
                                            )
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()
                            else:
                                st.info("Silinecek kayıt bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı İhtiyaç Sahipleri Tablosu")
            if kisi_liste_gosterim:
                ozel_html_tablo_goster(kisi_liste_gosterim)
            else:
                st.info("Sistemde kayıtlı ihtiyaç sahibi bulunmuyor.")

        with tab2:
            col_b_dag, col_indir_dag = st.columns([2, 2])
            with col_b_dag:
                st.subheader("🍲 Toplu Yemek Dağıtımı Girişi ve Yönetimi")

            if st.session_state.dagitim_silme_mesaji:
                st.success(st.session_state.dagitim_silme_mesaji)
                st.session_state.dagitim_silme_mesaji = ""

            aktif_ihtiyac_sahipleri = [k for k in st.session_state.ihtiyac_sahipleri if k.get("aktif", True)]

            if yonetim_modu:
                st.info("👀 Yönetim modundasınız. Bu ekranda yeni dağıtım kaydı oluşturamazsınız.")
            elif not aktif_ihtiyac_sahipleri:
                st.warning("Aktif durumda kayıtlı ihtiyaç sahibi bulunmuyor.")
            else:
                st.markdown("##### ⚡ Toplu Dağıtım Paneli (Aktif Vatandaşlar)")
                with st.form("toplu_dagitim_formu"):
                    menu_adi_toplu = st.text_input(
                        "Dağıtılacak Ortak Menü / Yemek Adı", "Ispanak Yemeği ve Pilav"
                    )
                    st.markdown("---")
                    st.markdown("**Aktif İhtiyaç Sahibi Listesi ve Porsiyon Belirleme**")
                    
                    secim_verileri = []
                    for idx, k in enumerate(aktif_ihtiyac_sahipleri):
                        c1, c2, c3 = st.columns([0.5, 2.5, 1])
                        with c1:
                            secili_mi = st.checkbox("Seç", value=True, key=f"toplu_sec_{idx}", label_visibility="collapsed")
                        with c2:
                            st.markdown(f"**{html_escape(str(k['ad_soyad']))}** <span style='font-size:12px; opacity:0.6;'>(Hane/T.C: {html_escape(str(k.get('tc_hane', '-')))})</span>", unsafe_allow_html=True)
                        with c3:
                            varsayilan_porsiyon = int(k.get("birey_sayisi", 1))
                            pors_val = st.number_input("Porsiyon", min_value=1, value=varsayilan_porsiyon, key=f"toplu_pors_{idx}", label_visibility="collapsed")
                        
                        secim_verileri.append({
                            "kisi": k["ad_soyad"],
                            "secili": secili_mi,
                            "porsiyon": pors_val
                        })

                    st.markdown("---")
                    toplu_kaydet_btn = st.form_submit_button("🚀 Seçilen Tüm Hanelere Toplu Dağıtımı Onayla ve Kaydet", type="primary")

                    if toplu_kaydet_btn:
                        d_tarih_saat = simdi_tr_str("%Y-%m-%d %H:%M")
                        eklenen_sayisi = 0
                        eklenen_id_listesi = []

                        for sv in secim_verileri:
                            if sv["secili"]:
                                yeni_dag_id = yeni_id_uret("DAG-", st.session_state.dagitim_loglari)
                                st.session_state.dagitim_loglari.append({
                                    "id": yeni_dag_id,
                                    "tarih": d_tarih_saat,
                                    "kisi": sv["kisi"],
                                    "menu": menu_adi_toplu,
                                    "porsiyon": sv["porsiyon"],
                                    "islem_yapan": st.session_state.aktif_kullanici,
                                })
                                eklenen_id_listesi.append(yeni_dag_id)
                                eklenen_sayisi += 1
                        
                        st.session_state["son_toplu_dagitim_kaydi"] = {
                            "tarih": d_tarih_saat,
                            "menu": menu_adi_toplu,
                            "sayi": eklenen_sayisi,
                            "eklenen_id_listesi": eklenen_id_listesi
                        }

                        dagitim_loglarini_kaydet(st.session_state.dagitim_loglari)
                        st.success(f"🎉 Başarılı! Seçilen {eklenen_sayisi} haneye yemek dağıtımı işlendi.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

            st.markdown("---")
            st.subheader("📋 Kayıtlı Yemek Dağıtımları Tablosu")
            
            dagitim_gosterim_listesi = []
            for idx, d in enumerate(st.session_state.dagitim_loglari):
                tarih_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Tarih/Saat" in aktif_k_maskeleri else d.get("tarih", "-")
                kisi_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Kişi/Hane" in aktif_k_maskeleri else d.get("kisi", "-")
                menu_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Menü" in aktif_k_maskeleri else d.get("menu", "-")
                porsiyon_maskele_d = "🔒 Gizli" if "4. Sayfa: Yemek Dağıtımları - Porsiyon" in aktif_k_maskeleri else d.get("porsiyon", 1)

                dagitim_gosterim_listesi.append({
                    "Kayıt No": d.get("id", f"DAG-{idx+1:03d}"),
                    "Tarih / Saat": tarih_maskele_d,
                    "Kişi / Hane": kisi_maskele_d,
                    "Menü": menu_maskele_d,
                    "Porsiyon": porsiyon_maskele_d,
                    "İşlemi Yapan": d.get("islem_yapan", "admin"),
                })

            excel_dag_data = tablo_to_excel_bytes(
                dagitim_gosterim_listesi, "Aziziye Aşevi - Yemek Dağıtım Listesi"
            )
            pdf_dag_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Yemek Dağıtım Listesi", dagitim_gosterim_listesi
            )

            with col_indir_dag:
                ortak_indirme_alani(
                    excel_dag_data,
                    pdf_dag_data,
                    "yemek_dagitim_listesi",
                    "dagitim_sayfasi",
                )

            if dagitim_gosterim_listesi:
                ozel_html_tablo_goster(dagitim_gosterim_listesi)
            else:
                st.info("Kayıtlı yemek dağıtımı bulunmuyor.")

        with tab3:
            col_b_sayac, col_indir_sayac = st.columns([2, 2])
            with col_b_sayac:
                st.subheader("📊 Kişi Bazlı Günlük, Haftalık ve Aylık Sayaç Raporu")

            simdi_dt = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Istanbul")) if hasattr(datetime, "datetime") else datetime.datetime.now()
            bugun_str = simdi_dt.strftime("%Y-%m-%d")
            yedi_gun_once = (simdi_dt - datetime.timedelta(days=7)).date()
            bu_yil_ay = simdi_dt.strftime("%Y-%m")

            sayac_tablosu = []
            excel_sayac_liste = []

            for k in st.session_state.ihtiyac_sahipleri:
                kisi_adi = k["ad_soyad"]
                k_loglari = [
                    d
                    for d in st.session_state.dagitim_loglari
                    if d.get("kisi") == kisi_adi
                ]

                gunluk_sefer = 0
                gunluk_porsiyon = 0
                haftalik_sefer = 0
                haftalik_porsiyon = 0
                aylik_sefer = 0
                aylik_porsiyon = 0

                for d in k_loglari:
                    tarih_saat_str = d.get("tarih", "")
                    pors = int(d.get("porsiyon", 1))
                    if not tarih_saat_str:
                        continue
                    try:
                        d_tarih = datetime.datetime.strptime(
                            tarih_saat_str.split()[0], "%Y-%m-%d"
                        ).date()
                    except:
                        continue

                    if tarih_saat_str.startswith(bugun_str):
                        gunluk_sefer += 1
                        gunluk_porsiyon += pors

                    if yedi_gun_once <= d_tarih <= simdi_dt.date():
                        haftalik_sefer += 1
                        haftalik_porsiyon += pors

                    if tarih_saat_str.startswith(bu_yil_ay):
                        aylik_sefer += 1
                        aylik_porsiyon += pors

                tc_hane_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - T.C./Hane No" in aktif_k_maskeleri else k.get("tc_hane", "-")
                kisi_ad_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - İhtiyaç Sahibi" in aktif_k_maskeleri else kisi_adi
                gunluk_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Günlük Alım" in aktif_k_maskeleri else f"{gunluk_sefer} Kez / {gunluk_porsiyon} Pors."
                haftalik_maskele = "🔒 Gizli" if "4. Sayfa: Haftalık Alım" in aktif_k_maskeleri else f"{haftalik_sefer} Kez / {haftalik_porsiyon} Pors."
                aylik_maskele = "🔒 Gizli" if "4. Sayfa: Sayaç Raporu - Aylık Alım" in aktif_k_maskeleri else f"{aylik_sefer} Kez / {aylik_porsiyon} Pors."

                sayac_tablosu.append({
                    "T.C. / Hane No": tc_hane_maskele,
                    "İhtiyaç Sahibi": kisi_ad_maskele,
                    "Günlük Alım (Kez / Porsiyon)": gunluk_maskele,
                    "Haftalık Alım (Kez / Porsiyon)": haftalik_maskele,
                    "Aylık Alım (Kez / Porsiyon)": aylik_maskele,
                })

                excel_sayac_liste.append({
                    "T.C. / Hane No": tc_hane_maskele,
                    "İhtiyaç Sahibi": kisi_ad_maskele,
                    "Günlük Kez": gunluk_sefer,
                    "Günlük Porsiyon": gunluk_porsiyon,
                    "Haftalık Kez": haftalik_sefer,
                    "Haftalık Porsiyon": haftalik_porsiyon,
                    "Aylık Kez": aylik_sefer,
                    "Aylık Porsiyon": aylik_porsiyon,
                })

            excel_sayac_data = tablo_to_excel_bytes(
                excel_sayac_liste,
                "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
            )
            pdf_sayac_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Kişi Bazlı Yemek Dağıtım Sayaç Raporu",
                excel_sayac_liste,
            )

            with col_indir_sayac:
                ortak_indirme_alani(
                    excel_sayac_data,
                    pdf_sayac_data,
                    "kisi_bazli_yemek_sayac_raporu",
                    "sayac_sayfasi",
                )

            if sayac_tablosu:
                ozel_html_tablo_goster(sayac_tablosu)
            else:
                st.info("Listelenecek ihtiyaç sahibi veya dağıtım verisi bulunmuyor.")

# 8. PERSONEL VE ÇALIŞMA SÜRESİ TAKİBİ
elif menu in ["Personel ve Çalışma Süresi Takibi", "Personel & Çalışma Süresi Takibi"]:
    import calendar
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        st.header("👥 Personel ve Çalışma Süresi Takibi")
        st.markdown(
            "Aşevi personelinin kayıtlarını tutun, izin/rapor günlerini girin ve net çalışma günlerini takip edin."
        )

        # Session State Güvenlik Kontrolleri ve Otomatik ID Ataması
        if "personeller" not in st.session_state or st.session_state.personeller is None:
            st.session_state.personeller = []
        
        # ID'si eksik olan eski kayıtlar varsa anında benzersiz PER- ID'si atanır
        st.session_state.personeller = idleri_benzersiz_yap(st.session_state.personeller, "PER-")

        if "personel_izinleri" not in st.session_state or st.session_state.personel_izinleri is None:
            st.session_state.personel_izinleri = []

        # Son Personel / İzin İşlemini Geri Al Butonu ve Bildirimi
        if st.session_state.get("son_personel_islem"):
            son_p_islem = st.session_state["son_personel_islem"]
            tur = son_p_islem.get("tur")
            p_obj = son_p_islem.get("obje", {})
            
            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if tur == "personel_ekle":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli eklendi.")
                elif tur == "personel_sil":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('ad_soyad', p_obj.get('ad', '-'))}' personeli silindi.")
                elif tur == "izin_ekle":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' için {p_obj.get('gun_sayisi', 0)} günlük {p_obj.get('izin_turu', '-')} eklendi.")
                elif tur == "izin_sil":
                    st.info(f"💡 **Son İşlem:** '{p_obj.get('personel_ad', '-')}' kişisine ait izin kaydı silindi.")

            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_personel_son"):
                    otomatik_yedek_al("Personel işlemi geri alma: " + str(tur))
                    
                    if tur == "personel_ekle":
                        st.session_state.personeller = [p for p in st.session_state.personeller if str(p.get("id")) != str(p_obj.get("id"))]
                    elif tur == "personel_sil":
                        if not any(str(p.get("id")) == str(p_obj.get("id")) for p in st.session_state.personeller):
                            st.session_state.personeller.append(p_obj)
                    elif tur == "izin_ekle":
                        st.session_state.personel_izinleri = [iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) != str(p_obj.get("id"))]
                    elif tur == "izin_sil":
                        if not any(str(iz.get("id")) == str(p_obj.get("id")) for iz in st.session_state.personel_izinleri):
                            st.session_state.personel_izinleri.append(p_obj)

                    if "personelleri_kaydet" in globals():
                        personelleri_kaydet(st.session_state.personeller)
                    else:
                        supabase_veri_kaydet("personeller", st.session_state.personeller)

                    if "personel_izinlerini_kaydet" in globals():
                        personel_izinlerini_kaydet(st.session_state.personel_izinleri)
                    else:
                        supabase_veri_kaydet("personel_izinleri", st.session_state.personel_izinleri)

                    st.session_state.pop("son_personel_islem", None)
                    st.success("🎉 Yapılan son işlem başarıyla geri alındı!")
                    time.sleep(1)
                    st.rerun()

        tab_p1, tab_p2, tab_p3 = st.tabs([
            "📋 Personel Listesi ve Ekle/Sil",
            "📅 İzin & Rapor Girişi ve Takibi",
            "📊 Net Çalışma Günü Raporu"
        ])

        # TAB 1: PERSONEL LİSTESİ VE EKLE / SİL
        with tab_p1:
            col_b_pers, col_indir_pers = st.columns([2, 2])
            with col_b_pers:
                st.subheader("📋 Personel Kayıtları ve Yönetimi")

            personel_gosterim = []
            for p in st.session_state.personeller:
                ad_soyad_val = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
                tc_p = "🔒 Gizli" if "5. Sayfa: Personel - T.C. No" in aktif_k_maskeleri else (p.get("tc_no") or p.get("tc") or "-")
                ad_p = "🔒 Gizli" if "5. Sayfa: Personel - Adı Soyadı" in aktif_k_maskeleri else ad_soyad_val
                tel_p = "🔒 Gizli" if "5. Sayfa: Personel - Telefon" in aktif_k_maskeleri else (p.get("telefon") or "-")
                gorev_p = p.get("gorev") or p.get("gorevi") or "-"
                tarih_p = p.get("baslama_tarihi") or p.get("baslama") or p.get("ise_baslama_tarihi") or p.get("tarih") or "-"

                personel_gosterim.append({
                    "Personel ID": p.get("id", "-"),
                    "T.C. Kimlik No": tc_p,
                    "Adı Soyadı": ad_p,
                    "Görevi / Unvanı": gorev_p,
                    "Telefon": tel_p,
                    "İşe Başlama Tarihi": tarih_p,
                })

            excel_p_data = tablo_to_excel_bytes(personel_gosterim, "Aziziye Aşevi - Personel Listesi")
            pdf_p_data = tablo_to_html_pdf_bytes("Aziziye Aşevi - Personel Listesi", personel_gosterim)
            with col_indir_pers:
                ortak_indirme_alani(excel_p_data, pdf_p_data, "personel_listesi_raporu", "personel_sayfasi")

            if not salt_okunur_modu:
                col_p_ekle, col_p_sil = st.columns(2)
                with col_p_ekle:
                    with st.form("yeni_personel_form"):
                        st.markdown("**➕ Yeni Personel Ekle**")
                        p_tc = st.text_input("T.C. Kimlik No").strip()
                        p_ad = st.text_input("Adı Soyadı").strip().upper()
                        p_gorev = st.text_input("Görevi / Unvanı (Örn: Aşçıbaşı, Şoför)").strip()
                        p_tel = st.text_input("Telefon Numarası")
                        p_tarih = st.date_input("İşe Başlama Tarihi", value=datetime.date.today())

                        p_ekle_btn = st.form_submit_button("Personeli Kaydet", type="primary")
                        if p_ekle_btn and p_ad:
                            yeni_p_id = yeni_id_uret("PER-", st.session_state.personeller)
                            yeni_p_obj = {
                                "id": yeni_p_id,
                                "tc_no": p_tc,
                                "tc": p_tc,
                                "ad_soyad": p_ad,
                                "gorev": p_gorev if p_gorev else "Personel",
                                "telefon": p_tel,
                                "baslama_tarihi": str(p_tarih),
                                "baslama": str(p_tarih),
                                "ise_baslama_tarihi": str(p_tarih),
                                "eklenme_zamanı": simdi_tr_str("%Y-%m-%d %H:%M")
                            }
                            st.session_state.personeller.append(yeni_p_obj)
                            
                            if "personelleri_kaydet" in globals():
                                personelleri_kaydet(st.session_state.personeller)
                            else:
                                supabase_veri_kaydet("personeller", st.session_state.personeller)

                            st.session_state["son_personel_islem"] = {
                                "tur": "personel_ekle",
                                "obje": yeni_p_obj
                            }

                            st.success(f"🎉 Başarılı! {p_ad} personel olarak kaydedildi.")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()

                with col_p_sil:
                    if not yonetici_modu:
                        st.info("🗑️ Personel silme yetkisi yalnızca Admin'e aittir.")
                    else:
                        with st.form("personel_sil_form"):
                            st.markdown("**🗑️ Kayıtlı Personeli Sil**")
                            if st.session_state.personeller:
                                p_secenekler_sil = [
                                    f"{p.get('id', '-') } - {p.get('ad_soyad') or p.get('ad') or p.get('isim') or '-'} ({p.get('gorev') or p.get('gorevi') or '-'})"
                                    for p in st.session_state.personeller
                                ]
                                secilen_sil_p = st.selectbox(
                                    "Silinecek Personeli Seçin",
                                    p_secenekler_sil,
                                    index=None,
                                    placeholder="Personel Seçiniz...",
                                    key="personel_sil_selectbox"
                                )
                                onay_p_sil_btn = silme_onay_kutusu("onay_personel_sil")
                                p_sil_btn = st.form_submit_button("Seçilen Personeli Sil", type="primary")

                                if p_sil_btn:
                                    if not secilen_sil_p:
                                        st.error("⚠️ Lütfen silinecek personeli seçin!")
                                    elif not onay_p_sil_btn:
                                        st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                    else:
                                        otomatik_yedek_al("Personel silme: " + str(secilen_sil_p))
                                        sil_p_id = secilen_sil_p.split(" - ")[0]
                                        silinen_p_obj = next(
                                            (p for p in st.session_state.personeller if str(p.get("id", "")) == str(sil_p_id) or f"{p.get('id', '-')} - {p.get('ad_soyad') or p.get('ad') or '-'}" in secilen_sil_p), 
                                            None
                                        )
                                        
                                        if silinen_p_obj:
                                            st.session_state.personeller = [
                                                p for p in st.session_state.personeller 
                                                if p != silinen_p_obj and str(p.get("id", "")) != str(sil_p_id)
                                            ]
                                            
                                            if "personelleri_kaydet" in globals():
                                                personelleri_kaydet(st.session_state.personeller)
                                            else:
                                                supabase_veri_kaydet("personeller", st.session_state.personeller)
                                            
                                            st.session_state["son_personel_islem"] = {
                                                "tur": "personel_sil",
                                                "obje": silinen_p_obj
                                            }

                                            st.success("🎉 Başarılı! Personel kaydı silindi.")
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()
                            else:
                                st.info("Silinecek personel bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı Personel Tablosu")
            if personel_gosterim:
                ozel_html_tablo_goster(personel_gosterim)
            else:
                st.info("Kayıtlı personel bulunmuyor.")

        # TAB 2: İZİN & RAPOR GİRİŞİ VE TAKİBİ
        with tab_p2:
            st.subheader("📅 Personel İzin ve Rapor Girişi")
            
            if not st.session_state.personeller:
                st.warning("İzin girmek için öncelikle personel eklemelisiniz.")
            else:
                if not salt_okunur_modu:
                    col_iz_ekle, col_iz_sil = st.columns(2)
                    with col_iz_ekle:
                        with st.form("yeni_izin_form"):
                            st.markdown("**➕ İzin / Rapor Kaydı Ekle**")
                            p_isimler = [p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-" for p in st.session_state.personeller]
                            secilen_p_ad = st.selectbox(
                                "Personel Seçin",
                                p_isimler,
                                index=None,
                                placeholder="Personel Seçiniz...",
                                key="izin_personel_select"
                            )
                            izin_turu = st.selectbox(
                                "İzin / Mazeret Türü",
                                ["Yıllık İzin", "Mazeret İzni", "Hastalık / Rapor", "Ücretsiz İzin", "Resmi Görev / Diğer"],
                                index=None,
                                placeholder="İzin Türü Seçiniz...",
                                key="izin_turu_select"
                            )
                            c_iz_bas, c_iz_bit = st.columns(2)
                            with c_iz_bas:
                                iz_bas_tarih = st.date_input("İzin Başlangıç Tarihi", value=datetime.date.today())
                            with c_iz_bit:
                                iz_bit_tarih = st.date_input("İzin Bitiş Tarihi", value=datetime.date.today())
                            
                            iz_aciklama = st.text_input("Açıklama / Not", "Yıllık İzin Kullanımı").strip()
                            iz_ekle_btn = st.form_submit_button("İznı Kaydet", type="primary")

                            if iz_ekle_btn:
                                if not secilen_p_ad:
                                    st.error("⚠️ Lütfen bir personel seçin!")
                                elif not izin_turu:
                                    st.error("⚠️ Lütfen izin türünü seçin!")
                                elif iz_bit_tarih < iz_bas_tarih:
                                    st.error("⚠️ Bitiş tarihi başlangıç tarihinden önce olamaz!")
                                else:
                                    gun_sayisi = (iz_bit_tarih - iz_bas_tarih).days + 1
                                    yeni_iz_id = yeni_id_uret("IZN-", st.session_state.personel_izinleri)
                                    yeni_iz_obj = {
                                        "id": yeni_iz_id,
                                        "personel_ad": secilen_p_ad,
                                        "izin_turu": izin_turu,
                                        "baslangic": str(iz_bas_tarih),
                                        "bitis": str(iz_bit_tarih),
                                        "gun_sayisi": gun_sayisi,
                                        "aciklama": iz_aciklama,
                                        "ekleme_tarihi": simdi_tr_str("%Y-%m-%d %H:%M")
                                    }
                                    st.session_state.personel_izinleri.append(yeni_iz_obj)
                                    
                                    if "personel_izinlerini_kaydet" in globals():
                                        personel_izinlerini_kaydet(st.session_state.personel_izinleri)
                                    else:
                                        supabase_veri_kaydet("personel_izinleri", st.session_state.personel_izinleri)

                                    st.session_state["son_personel_islem"] = {
                                        "tur": "izin_ekle",
                                        "obje": yeni_iz_obj
                                    }

                                    st.success(f"🎉 Başarılı! {secilen_p_ad} için {gun_sayisi} günlük {izin_turu} kaydedildi.")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()

                    with col_iz_sil:
                        if not yonetici_modu:
                            st.info("🗑️ İzin silme yetkisi yalnızca Admin'e aittir.")
                        else:
                            with st.form("izin_sil_form"):
                                st.markdown("**🗑️ İzin Kaydı Sil**")
                                if st.session_state.personel_izinleri:
                                    iz_secenekler = [
                                        f"{iz.get('id', '-') } - {iz.get('personel_ad', '-') } ({iz.get('izin_turu', '-') }: {iz.get('baslangic', '-') } / {iz.get('bitis', '-') })"
                                        for iz in st.session_state.personel_izinleri
                                    ]
                                    secilen_sil_iz = st.selectbox(
                                        "Silinecek İzin Kaydını Seçin",
                                        iz_secenekler,
                                        index=None,
                                        placeholder="İzin Kaydı Seçiniz...",
                                        key="izin_sil_select"
                                    )
                                    onay_iz_sil_btn = silme_onay_kutusu("onay_izin_sil")
                                    iz_sil_btn = st.form_submit_button("İzin Kaydını Sil", type="primary")

                                    if iz_sil_btn:
                                        if not secilen_sil_iz:
                                            st.error("⚠️ Lütfen silinecek izin kaydını seçin!")
                                        elif not onay_iz_sil_btn:
                                            st.error("⚠️ Silmek için onay kutusunu işaretleyin.")
                                        else:
                                            sil_iz_id = secilen_sil_iz.split(" - ")[0]
                                            silinen_iz_obj = next((iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) == str(sil_iz_id)), None)
                                            
                                            if silinen_iz_obj:
                                                st.session_state.personel_izinleri = [iz for iz in st.session_state.personel_izinleri if str(iz.get("id")) != str(sil_iz_id)]
                                                
                                                if "personel_izinlerini_kaydet" in globals():
                                                    personel_izinlerini_kaydet(st.session_state.personel_izinleri)
                                                else:
                                                    supabase_veri_kaydet("personel_izinleri", st.session_state.personel_izinleri)

                                                st.session_state["son_personel_islem"] = {
                                                    "tur": "izin_sil",
                                                    "obje": silinen_iz_obj
                                                }

                                                st.success("🎉 Başarılı! İzin kaydı silindi.")
                                                st.balloons()
                                                time.sleep(1)
                                                st.rerun()
                                else:
                                    st.info("Silinecek izin kaydı bulunmuyor.")

            st.markdown("---")
            st.subheader("📋 Kayıtlı İzin ve Raporlar Tablosu")
            if st.session_state.personel_izinleri:
                iz_tablo = []
                for iz in reversed(st.session_state.personel_izinleri):
                    iz_tablo.append({
                        "Kayıt ID": iz.get("id", "-"),
                        "Personel Adı": iz.get("personel_ad", "-"),
                        "İzin Türü": iz.get("izin_turu", "-"),
                        "Başlangıç": iz.get("baslangic", "-"),
                        "Bitiş": iz.get("bitis", "-"),
                        "Gün Sayısı": iz.get("gun_sayisi", 0),
                        "Açıklama": iz.get("aciklama", "-"),
                    })
                ozel_html_tablo_goster(iz_tablo)
            else:
                st.info("Kayıtlı izin veya rapor bulunmuyor.")

        # TAB 3: NET ÇALIŞMA GÜNÜ RAPORU
        with tab_p3:
            st.subheader("📊 Personel Net Çalışma Günü Raporu")
            
            sorgu_ay = st.date_input("Sorgulanacak Ay ve Yıl Seçin", value=datetime.date.today(), key="sorgu_ay_picker")
            sorgu_yil_ay_str = sorgu_ay.strftime("%Y-%m")
            
            toplam_ay_gunu = calendar.monthrange(sorgu_ay.year, sorgu_ay.month)[1]
            
            net_calisma_raporu = []
            for p in st.session_state.personeller:
                p_ad = p.get("ad_soyad") or p.get("ad") or p.get("isim") or "-"
                
                kullandigi_izin_gunu = 0
                for iz in st.session_state.personel_izinleri:
                    if iz.get("personel_ad") == p_ad:
                        bas_t = iz.get("baslangic", "")
                        if bas_t.startswith(sorgu_yil_ay_str):
                            kullandigi_izin_gunu += int(iz.get("gun_sayisi", 0))

                net_gun = toplam_ay_gunu - kullandigi_izin_gunu
                if net_gun < 0:
                    net_gun = 0

                net_calisma_raporu.append({
                    "Personel Adı": p_ad,
                    "Görevi": p.get("gorev") or p.get("gorevi") or "-",
                    "Dönem": sorgu_yil_ay_str,
                    "Toplam Ay Günü": toplam_ay_gunu,
                    "Kullanılan İzin / Rapor (Gün)": kullandigi_izin_gunu,
                    "Net Çalışma Günü": net_gun
                })

            if net_calisma_raporu:
                excel_p_calisma = tablo_to_excel_bytes(net_calisma_raporu, f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})")
                pdf_p_calisma = tablo_to_html_pdf_bytes(f"Aziziye Aşevi - Personel Net Çalışma Raporu ({sorgu_yil_ay_str})", net_calisma_raporu)
                
                ortak_indirme_alani(excel_p_calisma, pdf_p_calisma, f"personel_net_calisma_{sorgu_yil_ay_str}", "personel_calisma_raporu_sayfasi")
                ozel_html_tablo_goster(net_calisma_raporu)
            else:
                st.info("Raporlanacak personel bulunmuyor.")
                
# 9. KULLANIM TAKİBİ
elif menu == "Kullanım Takibi":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_kullanim, col_indir_kullanim = st.columns([2, 2])
        with col_b_kullanim:
            st.header("📈 Tüm Sistem Kullanım Logları ve Hareket Arşivi")

        if st.session_state.kullanim_loglari:
            log_tablosu = []
            for log in reversed(st.session_state.kullanim_loglari):
                log_tablosu.append({
                    "Tarih / Saat": log.get("tarih", "-"),
                    "İşlem Türü / Açıklama": log.get("tur", "-"),
                    "Ürün / Malzeme": log.get("urun", "-"),
                    "Miktar": f"{log.get('miktar', 0)}",
                    "Tutar": f"{log.get('tutar', 0):,.2f} ₺",
                    "İşlemi Yapan": log.get("islem_yapan", "admin"),
                })

            excel_log_data = tablo_to_excel_bytes(
                log_tablosu, "Aziziye Aşevi - Sistem Kullanım Logları"
            )
            pdf_log_data = tablo_to_html_pdf_bytes(
                "Aziziye Aşevi - Sistem Kullanım Logları", log_tablosu
            )

            with col_indir_kullanim:
                ortak_indirme_alani(
                    excel_log_data,
                    pdf_log_data,
                    "sistem_kullanim_loglari_arsivi",
                    "kullanim_sayfasi",
                )

            ozel_html_tablo_goster(log_tablosu)
        else:
            st.info("Henüz sistemde kayıtlı kullanım logu bulunmuyor.")

# 10. KAPSAMLI ENVANTER VE HAREKET RAPORU
elif menu == "Kapsamlı Envanter ve Hareket Raporu":
    if misafir_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz bulunmamaktadır.")
    else:
        col_b_env, col_indir_env = st.columns([2, 2])
        with col_b_env:
            st.header("📋 Kapsamlı Envanter ve Hareket Raporu")

        kapsamli_liste = []
        for g in st.session_state.girisler:
            kapsamli_liste.append({
                "Kayıt ID": g.get("id", "-"),
                "Tarih": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Ürün Adı": g.get("urun", "-"),
                "Kategori": g.get("kategori", "-"),
                "Depo": g.get("depo", "-"),
                "Alınan Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                "Kalan Miktar": f"{g.get('kalan', 0)} {g.get('birim', 'Kg')}",
                "Birim Fiyat": f"{g.get('fiyat', 0):,.2f} ₺",
                "Toplam Değer": f"{(g.get('kalan', 0) * g.get('fiyat', 0)):,.2f} ₺",
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })

        excel_kapsamli_data = tablo_to_excel_bytes(
            kapsamli_liste, "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu"
        )
        pdf_kapsamli_data = tablo_to_html_pdf_bytes(
            "Aziziye Aşevi - Kapsamlı Envanter ve Hareket Raporu", kapsamli_liste
        )

        with col_indir_env:
            ortak_indirme_alani(
                excel_kapsamli_data,
                pdf_kapsamli_data,
                "kapsamli_envanter_ve_hareket_raporu",
                "kapsamli_envanter_sayfasi",
            )

        if kapsamli_liste:
            ozel_html_tablo_goster(kapsamli_liste)
        else:
            st.info("Kapsamlı rapor için kayıt bulunmuyor.")

# 11. ÜRÜN BİRİM FİYATLARI & AY ANALİZİ
elif menu == "Ürün Birim Fiyatları & Ay Analizi":
    col_b_fiy, col_indir_fiy = st.columns([2, 2])
    with col_b_fiy:
        st.header("💰 Ürün Birim Fiyatları ve Ay Bazlı Maliyet Analizi")

    benzersiz_urunler_fiyat = sorted(
        list(set(g.get("urun", "").strip().upper() for g in st.session_state.girisler if g.get("urun")))
    )

    if benzersiz_urunler_fiyat:
        secilen_fiyat_urun = st.selectbox(
            "Analiz Edilecek Ürünü Seçin", benzersiz_urunler_fiyat
        )
        urun_kayitlari = [
            g
            for g in st.session_state.girisler
            if g.get("urun", "").strip().upper() == secilen_fiyat_urun.strip().upper()
        ]

        fiyat_analiz_tablosu = []
        excel_fiyat_analiz = []
        for g in urun_kayitlari:
            fiyat_degeri = g.get("fiyat", 0)
            gosterilen_fiyat = "🔒 Gizli" if "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu" in aktif_k_maskeleri else f"{fiyat_degeri:,.2f} ₺"
            fiyat_analiz_tablosu.append({
                "Alım Tarihi": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Depo": g.get("depo", "-"),
                "Miktar": f"{g.get('miktar', 0)} {g.get('birim', 'Kg')}",
                "Birim Fiyat": gosterilen_fiyat,
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })
            excel_fiyat_analiz.append({
                "Alım Tarihi": g.get("tarih", "-"),
                "Fatura No": g.get("fatura_no", "-"),
                "Depo": g.get("depo", "-"),
                "Miktar": g.get("miktar", 0),
                "Birim Fiyat (TL)": fiyat_degeri,
                "İşlemi Yapan": g.get("islem_yapan", "admin"),
            })

        excel_fiy_data = tablo_to_excel_bytes(
            excel_fiyat_analiz, f"Aziziye Aşevi - {secilen_fiyat_urun} Fiyat Analizi"
        )
        pdf_fiy_data = tablo_to_html_pdf_bytes(
            f"Aziziye Aşevi - {secilen_fiyat_urun} Fiyat Analizi", excel_fiyat_analiz
        )

        with col_indir_fiy:
            ortak_indirme_alani(
                excel_fiy_data,
                pdf_fiy_data,
                f"urun_fiyat_analizi_{secilen_fiyat_urun.lower()}",
                "fiyat_analiz_sayfasi",
            )

        ozel_html_tablo_goster(fiyat_analiz_tablosu)
    else:
        st.info("Analiz edilecek ürün kaydı bulunmuyor.")

# 12. KULLANICI YÖNETİMİ, GÜVENLİK DURUMU, GİRİŞ KAYITLARI VE YEDEKLEME
elif menu == "Kullanıcı Ayarları":
    if not yonetici_modu:
        st.warning("⚠️ Bu sayfaya erişim yetkiniz yalnızca **Admin** kullanıcısına aittir.")
    else:
        st.header("⚙️ Kullanıcı Yönetimi, Güvenlik ve Yedekleme")
        kullanici_db = st.session_state.kullanicilar

        # Tip güvenliği: maskeler ve yasaklı menüler düz liste olmalıdır
        for _kk, _kv in kullanici_db.items():
            if not isinstance(_kv.get("maskeli_alanlar"), list):
                _kv["maskeli_alanlar"] = []
            if not isinstance(_kv.get("yasakli_menuler"), list):
                _kv["yasakli_menuler"] = []

        # ------------------------------------------------------------------
        # SON İŞLEMİ GERİ AL (UNDO) MEKANİZMASI
        # ------------------------------------------------------------------
        if st.session_state.get("son_kullanici_islem"):
            son_islem = st.session_state["son_kullanici_islem"]
            islem_turu = son_islem.get("tur")
            k_adi_hedef = son_islem.get("kullanici_adi")

            c_undo1, c_undo2 = st.columns([3, 1])
            with c_undo1:
                if islem_turu == "sil":
                    st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısı silindi.")
                elif islem_turu == "ekle":
                    st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısı eklendi.")
                elif islem_turu == "guncelle":
                    st.info(f"💡 **Son İşlem:** '{k_adi_hedef}' kullanıcısının ayarları/yetkileri değiştirildi.")

            with c_undo2:
                if st.button("↩️ Son İşlemi Geri Al", type="secondary", key="btn_undo_kullanici_islem"):
                    otomatik_yedek_al("Kullanıcı işlemi geri alma: " + str(islem_turu))
                    
                    if islem_turu == "sil":
                        # Silinen kullanıcıyı ve detaylarını geri yükle
                        eski_obj = son_islem.get("eski_obje")
                        if eski_obj:
                            kullanici_db[k_adi_hedef] = eski_obj
                    elif islem_turu == "ekle":
                        # Yeni eklenen kullanıcıyı sil
                        if k_adi_hedef in kullanici_db:
                            del kullanici_db[k_adi_hedef]
                    elif islem_turu == "guncelle":
                        # Eski yetki/maske ayarlarına geri dön; ANCAK mevcut şifre korunur
                        # (güncelleme şifre değiştirmişse, geri alma eski/ele geçirilmiş şifreyi geri getirmesin).
                        eski_obj = son_islem.get("eski_obje")
                        if eski_obj:
                            eski_obj = dict(eski_obj)
                            if k_adi_hedef in kullanici_db:
                                eski_obj["sifre"] = kullanici_db[k_adi_hedef].get("sifre", eski_obj.get("sifre", ""))
                                if kullanici_db[k_adi_hedef].get("sifre_degistirilmeli"):
                                    eski_obj["sifre_degistirilmeli"] = True
                                else:
                                    eski_obj.pop("sifre_degistirilmeli", None)
                            kullanici_db[k_adi_hedef] = eski_obj

                    kullanıcıları_kaydet(kullanici_db)
                    giris_logla("admin", f"kullanıcı işlemi geri alındı: {islem_turu} ({k_adi_hedef})")
                    st.session_state.pop("son_kullanici_islem", None)
                    st.toast(f"🎉 '{k_adi_hedef}' üzerindeki son işlem geri alındı!", icon="✅")
                    time.sleep(1)
                    st.rerun()

        # ------------------------------------------------------------------
        # GÜVENLİK DURUMU - LOGO VE HOVER (ÜZERİNE GELİNCE GÖSTERİM) ROZETLERİ
        # ------------------------------------------------------------------
        st.subheader("🛡️ Güvenlik Durumu")
        
        # 1. Supabase Durum Hesaplaması
        if not SUPABASE_URL or not SUPABASE_KEY:
            sb_badge = ("❌", "Supabase Bağlantısı Yok", "Supabase bağlı değil: veriler kalıcı olarak saklanmıyor ve yedek/giriş kaydı çalışmıyor.", "background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #f87171;")
        else:
            _rol = supabase_anahtar_rolu()
            if _rol == "anon":
                sb_badge = ("⚠️", "Supabase (Anon)", "Supabase'de herkese açık (anon) anahtar kullanılıyor. RLS'yi açın ve `service_role` anahtarına geçin (`supabase_guvenlik.sql`).", "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")
            elif _rol == "service_role":
                sb_badge = ("🔑", "Supabase (service_role)", "Supabase anahtarı: service_role (doğru). RLS'nin açık olduğundan emin olun.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
            else:
                sb_badge = ("ℹ️", "Supabase (Belirsiz)", "Supabase anahtarının rolü belirlenemedi; panelden RLS'nin açık olduğunu kontrol edin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

        # 2. Çerez Oturumu Hesaplaması
        if cerez_kontrol is not None:
            ck_badge = ("🍪", "Çerez Oturumu", "Oturum anahtarı çerezde tutuluyor (adres çubuğunda görünmez).", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
        else:
            ck_badge = ("🔗", "Adres Çubuğu Oturumu", "Oturum anahtarı hâlâ adres çubuğunda. Çerez desteği için `requirements.txt` dosyasına `streamlit-cookies-controller` ekleyin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

        # 3. Master Recovery Key Hesaplaması
        if str(st.secrets.get("MASTER_RECOVERY_KEY", "") or ""):
            mr_badge = ("🛡️", "Kurtarma Anahtarı", "MASTER_RECOVERY_KEY tanımlı.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")
        else:
            mr_badge = ("⚠️", "Kurtarma Anahtarı Yok", "MASTER_RECOVERY_KEY tanımlı değil: şifre kurtarma devre dışı. Ekledim diyorsanız secrets'a TANI_MODU = \"1\" ekleyip adrese ?tani=1 yazarak kontrol edin.", "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")

        # 4. Boşta Kalma Süresi
        bosta_dk = bosta_kalma_suresi_sn() // 60
        it_badge = ("⏱️", f"Boşta Kalma: {bosta_dk} dk", f"Boşta kalma süresi: {bosta_dk} dk (işlem yapılmazsa oturum kapanır). Değiştirmek için secrets'a BOSTA_KALMA_DAKIKA = \"20\" gibi bir satır ekleyin.", "background: rgba(59, 130, 246, 0.15); border: 1px solid #3b82f6; color: #60a5fa;")

        # 5. Şifre Durumu Hesaplaması
        _zayif = [
            k for k, v in kullanici_db.items()
            if v.get("sifre_degistirilmeli") or v.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
        ]
        if _zayif:
            pw_badge = ("🚨", f"Şifre Yenileme ({len(_zayif)})", "Şifresini değiştirmesi beklenen hesaplar: " + ", ".join(_zayif), "background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; color: #fbbf24;")
        else:
            pw_badge = ("✅", "Şifre Durumu Güvenli", "Eski varsayılan şifreyle kalan hesap yok.", "background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #10b981;")

        # HTML Rozet Paneli Gösterimi
        st.markdown(
            f"""
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; margin-top: 5px;">
                <div title="{html_escape(sb_badge[2])}" style="{sb_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                    <span>{sb_badge[0]}</span> <span>{sb_badge[1]}</span>
                </div>
                <div title="{html_escape(ck_badge[2])}" style="{ck_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                    <span>{ck_badge[0]}</span> <span>{ck_badge[1]}</span>
                </div>
                <div title="{html_escape(mr_badge[2])}" style="{mr_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                    <span>{mr_badge[0]}</span> <span>{mr_badge[1]}</span>
                </div>
                <div title="{html_escape(it_badge[2])}" style="{it_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                    <span>{it_badge[0]}</span> <span>{it_badge[1]}</span>
                </div>
                <div title="{html_escape(pw_badge[2])}" style="{pw_badge[3]} padding: 8px 14px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: help; display: flex; align-items: center; gap: 6px; backdrop-filter: blur(8px);">
                    <span>{pw_badge[0]}</span> <span>{pw_badge[1]}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        sekme_k, sekme_s, sekme_l, sekme_y = st.tabs([
            "👤 Kullanıcılar", "🔑 Şifrem", "📜 Giriş Kayıtları", "💾 Yedekleme",
        ])

        # ------------------------------------------------ Kullanıcılar
        with sekme_k:
            st.subheader("📋 Aktif Kullanıcılar ve Yetki Matrisi")
            if len(kullanici_db) > 0:
                tablo_satirlari = []
                for k_adi, k_obj in kullanici_db.items():
                    tablo_satirlari.append({
                        "Kullanıcı Adı": k_adi,
                        "Rol": "Admin" if k_adi == "admin" else k_obj.get("rol", "Personel"),
                        "Salt Okunur": "Evet" if k_obj.get("salt_okunur", False) else "Hayır",
                        "Maskelenen Alan Sayısı": len(k_obj.get("maskeli_alanlar", [])),
                        "Yasaklı Menüler": ", ".join(k_obj.get("yasakli_menuler", [])) or "Yok",
                        "Şifre Durumu": "Değişmesi gerekiyor" if (
                            k_obj.get("sifre_degistirilmeli") or k_obj.get("sifre", "") in ESKI_VARSAYILAN_HASHLER
                        ) else "Tamam",
                    })
                st.dataframe(pd.DataFrame(tablo_satirlari), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🛠️ Kullanıcı Düzenle, Yetki Ver ve Alan Maskele")

            MASKE_SECENEKLERI = {
                "Kurumsal Dashboard": [
                    ("Ürün Çeşidi", "1. Sayfa: Ürün Çeşidi"),
                    ("Toplam Fire", "1. Sayfa: Toplam Fire"),
                    ("Stok Değeri", "1. Sayfa: Stok Değeri"),
                    ("Aktif Personel", "1. Sayfa: Aktif Personel"),
                    ("Grafik Alanı", "1. Sayfa: Grafik Alanı"),
                ],
                "Güncel Stok / Fire / Fiyat": [
                    ("Stok - Kalan Miktar", "2. Sayfa: Güncel Stok Durumu - Kalan Miktar"),
                    ("Kayıtlı Fire ve Zayiat Listesi", "2. Sayfa: Kayıtlı Fire ve Zayiatlar Listesi"),
                    ("Birim Fiyat Sütunu", "2. Sayfa: Ürün Birim Fiyatları - Fiyat Sütunu"),
                ],
                "Günlük Yemek Üretimi": [
                    ("Üretim ve Maliyet Arşivi", "3. Sayfa: Yemek Üretim ve Maliyet Arşivi"),
                ],
                "İhtiyaç Sahipleri Listesi": [
                    ("T.C./Hane No", "4. Sayfa: İhtiyaç Sahipleri - T.C./Hane No"),
                    ("Adı Soyadı", "4. Sayfa: İhtiyaç Sahipleri - Adı Soyadı"),
                    ("Telefon", "4. Sayfa: İhtiyaç Sahipleri - Telefon"),
                    ("Adres", "4. Sayfa: İhtiyaç Sahipleri - Adres"),
                    ("Birey Sayısı", "4. Sayfa: İhtiyaç Sahipleri - Birey Sayısı"),
                ],
                "Yemek Dağıtımları": [
                    ("Tarih/Saat", "4. Sayfa: Yemek Dağıtımları - Tarih/Saat"),
                    ("Kişi/Hane", "4. Sayfa: Yemek Dağıtımları - Kişi/Hane"),
                    ("Menü", "4. Sayfa: Yemek Dağıtımları - Menü"),
                    ("Porsiyon", "4. Sayfa: Yemek Dağıtımları - Porsiyon"),
                ],
                "Dağıtım Sayaç Raporu": [
                    ("T.C./Hane No", "4. Sayfa: Sayaç Raporu - T.C./Hane No"),
                    ("İhtiyaç Sahibi", "4. Sayfa: Sayaç Raporu - İhtiyaç Sahibi"),
                    ("Günlük Alım", "4. Sayfa: Sayaç Raporu - Günlük Alım"),
                    ("Haftalık Alım", "4. Sayfa: Haftalık Alım"),
                    ("Aylık Alım", "4. Sayfa: Sayaç Raporu - Aylık Alım"),
                ],
            }
            _bilinen_maskeler = {a for liste in MASKE_SECENEKLERI.values() for _, a in liste}

            yonetilebilir_kullanicilar = [k for k in kullanici_db.keys() if k != "admin"]
            if yonetilebilir_kullanicilar:
                secilen_k_adi = st.selectbox(
                    "İşlem Yapılacak Kullanıcıyı Seçin",
                    yonetilebilir_kullanicilar,
                    index=None,
                    placeholder="Kullanıcı Seçiniz...",
                    key="secilen_k_ozel_mask"
                )
                if secilen_k_adi:
                    k_obj = kullanici_db[secilen_k_adi]

                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        mevcut_rol = k_obj.get("rol", "Personel")
                        rol_secenekleri = ["Personel", "Yönetim", "Misafir"]
                        rol_index = rol_secenekleri.index(mevcut_rol) if mevcut_rol in rol_secenekleri else 0
                        yeni_rol = st.selectbox("Kullanıcı Rolü", rol_secenekleri, index=rol_index, key=f"rol_ozel_{secilen_k_adi}")
                        yeni_salt_okunur = st.checkbox("Salt Okunur (veri değiştiremez)", value=k_obj.get("salt_okunur", False), key=f"ro_ozel_{secilen_k_adi}")
                    with col_d2:
                        yeni_sifre_k = st.text_input("Yeni şifre belirle (boş bırakılırsa değişmez)", type="password", key=f"ysifre_{secilen_k_adi}")
                        sifre_zorunlu_k = st.checkbox("Bir sonraki girişte şifre değiştirmek zorunda olsun", value=True, key=f"szor_{secilen_k_adi}")
                    kullaniciyi_sil = st.checkbox(
                        "⚠️ Bu kullanıcıyı KALICI olarak sil (işaretlemezseniz silinmez)", value=False, key=f"sil_ozel_{secilen_k_adi}"
                    )

                    st.markdown("##### 🔒 Gizlenecek (maskelenecek) alanlar")
                    mevcut_maskeler = k_obj.get("maskeli_alanlar", [])
                    secilen_maskeler = []
                    for g_idx, (grup_adi, secenekler) in enumerate(MASKE_SECENEKLERI.items()):
                        st.markdown(f"**📂 {grup_adi}**")
                        m_cols = st.columns(3)
                        for o_idx, (etiket, anahtar) in enumerate(secenekler):
                            with m_cols[o_idx % 3]:
                                if st.checkbox(etiket, value=(anahtar in mevcut_maskeler), key=f"mask_{secilen_k_adi}_{g_idx}_{o_idx}"):
                                    secilen_maskeler.append(anahtar)
                    yeni_maskeler = [m for m in mevcut_maskeler if m not in _bilinen_maskeler] + secilen_maskeler

                    st.markdown("##### 🚫 Sayfa / Menü Erişim Kısıtlamaları")
                    tum_menu_ogeleri = [m for m in gecerli_menuler if m != "Kullanıcı Ayarları"]
                    mevcut_yasaklar = k_obj.get("yasakli_menuler", [])
                    yeni_yasaklar = [m for m in mevcut_yasaklar if m not in tum_menu_ogeleri]
                    y_cols = st.columns(2)
                    for idx, m_item in enumerate(tum_menu_ogeleri):
                        with y_cols[idx % 2]:
                            if st.checkbox(m_item, value=(m_item in mevcut_yasaklar), key=f"ozel_yasak_{secilen_k_adi}_{idx}"):
                                yeni_yasaklar.append(m_item)

                    if st.button("Değişiklikleri Kaydet / Uygula", type="primary", key=f"btn_ozel_kaydet_{secilen_k_adi}"):
                        if kullaniciyi_sil:
                            otomatik_yedek_al("Kullanıcı silme: " + str(secilen_k_adi))
                            
                            # Geri al butonu için mevcut halini kaydet
                            st.session_state["son_kullanici_islem"] = {
                                "tur": "sil",
                                "kullanici_adi": secilen_k_adi,
                                "eski_obje": dict(kullanici_db[secilen_k_adi])
                            }

                            del kullanici_db[secilen_k_adi]
                            kullanıcıları_kaydet(kullanici_db)
                            kullanici_oturumlarini_kapat(secilen_k_adi)
                            giris_logla("admin", f"kullanıcı silindi: {secilen_k_adi}")
                            st.toast(f"🗑️ '{secilen_k_adi}' kullanıcısı silindi!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        else:
                            sifre_hata = sifre_politika_hatasi(yeni_sifre_k) if yeni_sifre_k else None
                            if sifre_hata:
                                st.error(sifre_hata)
                            else:
                                otomatik_yedek_al("Kullanıcı güncelleme: " + str(secilen_k_adi))
                                
                                # Geri al butonu için güncelleme öncesi halini kaydet
                                st.session_state["son_kullanici_islem"] = {
                                    "tur": "guncelle",
                                    "kullanici_adi": secilen_k_adi,
                                    "eski_obje": dict(kullanici_db[secilen_k_adi])
                                }

                                k_obj["rol"] = yeni_rol
                                k_obj["salt_okunur"] = yeni_salt_okunur
                                k_obj["maskeli_alanlar"] = yeni_maskeler
                                k_obj["yasakli_menuler"] = yeni_yasaklar
                                if yeni_sifre_k:
                                    sifre_degistir(secilen_k_adi, yeni_sifre_k, zorunlu=sifre_zorunlu_k)
                                else:
                                    kullanıcıları_kaydet(kullanici_db)
                                giris_logla("admin", f"kullanıcı ayarları güncellendi: {secilen_k_adi}")
                                st.toast(f"✅ '{secilen_k_adi}' ayarları kaydedildi!", icon="🎉")
                                time.sleep(1)
                                st.rerun()
            else:
                st.info("Düzenlenebilecek ek kullanıcı bulunmuyor.")

            st.markdown("---")
            st.subheader("➕ Yeni Sistem Kullanıcısı Ekle")
            yeni_k_adi = st.text_input("Kullanıcı Adı (3-30 karakter: harf, rakam, . _ -)", key="yeni_k_adi_input_ozel").strip().lower()
            yeni_sifre = st.text_input("Şifre (en az 10 karakter, harf ve rakam)", type="password", key="yeni_sifre_input_ozel")
            y_col1, y_col2, y_col3 = st.columns(3)
            with y_col1:
                yeni_k_rol = st.selectbox("Kullanıcı Rolü", ["Personel", "Yönetim", "Misafir"], key="yeni_rol_select_ozel")
            with y_col2:
                yeni_k_salt = st.checkbox("Salt Okunur Kullanıcı", value=False, key="yeni_salt_chk_ozel")
            with y_col3:
                yeni_k_zorunlu = st.checkbox("İlk girişte şifre değiştirsin", value=True, key="yeni_zorunlu_chk_ozel")

            if st.button("Yeni Kullanıcıyı Sisteme Ekle", type="secondary", key="btn_ozel_yeni_ekle"):
                if not re.fullmatch(r"[a-z0-9_.\-]{3,30}", yeni_k_adi or ""):
                    st.error("Kullanıcı adı 3-30 karakter olmalı; yalnızca küçük harf, rakam, nokta, alt çizgi ve tire içerebilir.")
                elif yeni_k_adi in kullanici_db:
                    st.error("Bu kullanıcı adı zaten sistemde mevcut!")
                elif sifre_politika_hatasi(yeni_sifre):
                    st.error(sifre_politika_hatasi(yeni_sifre))
                else:
                    yeni_user_data = {
                        "sifre": sifre_hashle_yeni(yeni_sifre),
                        "rol": yeni_k_rol,
                        "salt_okunur": yeni_k_salt,
                        "maskeli_alanlar": [],
                        "yasakli_menuler": [],
                        "sifre_degistirilmeli": yeni_k_zorunlu,
                    }
                    kullanici_db[yeni_k_adi] = yeni_user_data
                    
                    st.session_state["son_kullanici_islem"] = {
                        "tur": "ekle",
                        "kullanici_adi": yeni_k_adi
                    }

                    kullanıcıları_kaydet(kullanici_db)
                    giris_logla("admin", f"kullanıcı eklendi: {yeni_k_adi}")
                    st.toast(f"🎉 Yeni kullanıcı '{yeni_k_adi}' eklendi!", icon="✨")
                    time.sleep(1)
                    st.rerun()

        # ------------------------------------------------ Kendi şifrem
        with sekme_s:
            st.subheader("🔑 Kendi Şifrenizi Değiştirin")
            with st.form("admin_sifre_degistir_formu"):
                eski_s = st.text_input("Mevcut Şifre", type="password")
                yeni_s1 = st.text_input("Yeni Şifre", type="password")
                yeni_s2 = st.text_input("Yeni Şifre (Tekrar)", type="password")
                if st.form_submit_button("Şifremi Değiştir", type="primary"):
                    _ben = st.session_state.aktif_kullanici
                    if not sifre_dogrula(eski_s, kullanici_db.get(_ben, {}).get("sifre", "")):
                        st.error("Mevcut şifre hatalı.")
                    elif sifre_politika_hatasi(yeni_s1):
                        st.error(sifre_politika_hatasi(yeni_s1))
                    elif yeni_s1 != yeni_s2:
                        st.error("Yeni şifreler aynı değil.")
                    elif yeni_s1 == eski_s:
                        st.error("Yeni şifre eskisiyle aynı olamaz.")
                    else:
                        sifre_degistir(_ben, yeni_s1, haric_token=st.session_state.oturum_token)
                        st.success("Şifreniz değiştirildi. Diğer cihazlardaki oturumlarınız kapatıldı.")

        # ------------------------------------------------ Giriş kayıtları
        with sekme_l:
            st.subheader("📜 Giriş ve Güvenlik Kayıtları (son 200)")
            if not SUPABASE_URL or not SUPABASE_KEY:
                st.info("Kayıtlar için Supabase bağlantısı gerekir.")
            else:
                giris_kayitlari = supabase_veri_oku("giris_loglari", [], kritik=False)
                if not isinstance(giris_kayitlari, list):
                    giris_kayitlari = []
                log_satirlari = [
                    {
                        "Zaman": g.get("zaman", "-"),
                        "Kullanıcı": g.get("kullanici", "-"),
                        "Olay": g.get("durum", "-"),
                        "IP": g.get("ip", "-"),
                        "X-Forwarded-For": g.get("xff", ""),
                    }
                    for g in reversed(giris_kayitlari[-200:])
                ]
                if log_satirlari:
                    ortak_indirme_alani(
                        tablo_to_excel_bytes(log_satirlari, "Aziziye Aşevi - Giriş Kayıtları"),
                        tablo_to_html_pdf_bytes("Aziziye Aşevi - Giriş Kayıtları", log_satirlari),
                        "giris_kayitlari", "giris_kayit_sayfasi",
                    )
                    ozel_html_tablo_goster(log_satirlari)
                else:
                    st.info("Henüz giriş kaydı yok.")

                st.markdown("---")
                st.markdown("**🔓 Kilitleri Temizle** – Hatalı girişlerden kalan tüm geçici kilitleri kaldırır.")
                if st.button("Tüm Giriş Kilitlerini Temizle", key="kilit_temizle_btn"):
                    giris_denemesini_sifirla()
                    giris_logla("admin", "giriş kilitleri temizlendi")
                    st.success("Kilitler temizlendi.")

        # ------------------------------------------------ Yedekleme
        with sekme_y:
            st.subheader("💾 Yedekleme ve Geri Yükleme")
            if st.session_state.get("yedek_mesaj"):
                st.success(st.session_state.pop("yedek_mesaj"))
            if not SUPABASE_URL or not SUPABASE_KEY:
                st.info("Yedekleme için Supabase bağlantısı gerekir.")
            else:
                st.caption(
                    "Yedek dosyası kayıtlı kişilere ait bilgiler (ad-soyad, personel, stok vb.) içerir; "
                    "T.C./telefon/adres alanları şifreli kalır. Kullanıcı şifreleri yedeğe GİRMEZ. "
                    "Dosyayı güvenli bir yerde saklayın."
                )
                if st.button("📦 Tüm Veriyi Yedekle", key="yedek_hazirla_btn"):
                    paket = yedek_paketi_olustur()
                    if paket is None:
                        st.error("Yedek alınamadı: veritabanına ulaşılamadı.")
                    else:
                        st.session_state["yedek_bytes"] = json.dumps(paket, ensure_ascii=False, indent=1).encode("utf-8")
                        st.session_state["yedek_adi"] = f"asevi_yedek_{simdi_tr_str('%Y%m%d_%H%M')}.json"
                        giris_logla("admin", "yedek alındı")
                if st.session_state.get("yedek_bytes"):
                    st.download_button(
                        "⬇️ Yedek Dosyasını İndir",
                        data=st.session_state["yedek_bytes"],
                        file_name=st.session_state.get("yedek_adi", "asevi_yedek.json"),
                        mime="application/json",
                        key="yedek_indir_btn",
                    )

                st.markdown("---")
                st.markdown("**♻️ Yedekten Geri Yükle** – Mevcut veriler yedekteki verilerle DEĞİŞTİRİLİR. İşlemden önce otomatik bir yedek alınır.")
                yuklenen_yedek = st.file_uploader("Yedek dosyası (.json)", type=["json"], key="yedek_yukle_dosya")
                geri_yukle_onay = st.checkbox("⚠️ Mevcut verilerin yedekle değiştirileceğini anlıyorum, onaylıyorum.", key="yedek_onay_chk")
                if st.button("Yedeği Geri Yükle", type="primary", key="yedek_geri_yukle_btn"):
                    if yuklenen_yedek is None:
                        st.error("Önce bir yedek dosyası seçin.")
                    elif not geri_yukle_onay:
                        st.error("Geri yüklemek için onay kutusunu işaretleyin.")
                    elif yuklenen_yedek.size > 25 * 1024 * 1024:
                        st.error("Dosya çok büyük (en fazla 25 MB).")
                    else:
                        try:
                            paket = json.loads(yuklenen_yedek.getvalue().decode("utf-8"))
                        except Exception:
                            paket = None
                        basarili, mesaj = yedek_geri_yukle(paket)
                        if basarili:
                            giris_logla("admin", "yedekten geri yüklendi")
                            st.session_state["yedek_mesaj"] = mesaj
                            st.rerun()
                        else:
                            st.error(mesaj)

                st.markdown("---")
                st.markdown("**⏪ Son Otomatik Yedek** – Silme ve geri yükleme işlemlerinden hemen önce otomatik alınır (yalnızca en son yedek tutulur).")
                oto_durum, oto_paket = _supabase_ham_oku("otomatik_yedek")
                if oto_durum == "ok" and isinstance(oto_paket, dict):
                    _meta = oto_paket.get("_meta", {})
                    st.info(f"Zaman: {_meta.get('zaman', '-')} | Neden: {_meta.get('neden', '-')}")
                    oto_onay = st.checkbox("⚠️ Otomatik yedeğe dönmeyi onaylıyorum.", key="oto_yedek_onay_chk")
                    if st.button("Son Otomatik Yedeğe Dön", key="oto_yedek_geri_btn"):
                        if not oto_onay:
                            st.error("Onay kutusunu işaretleyin.")
                        else:
                            basarili, mesaj = yedek_geri_yukle(oto_paket)
                            if basarili:
                                giris_logla("admin", "otomatik yedeğe dönüldü")
                                st.session_state["yedek_mesaj"] = mesaj
                                st.rerun()
                            else:
                                st.error(mesaj)
                elif oto_durum == "hata":
                    st.error("Otomatik yedek bilgisi okunamadı.")
                else:
                    st.caption("Henüz otomatik yedek alınmadı.")
