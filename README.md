# Aziziye Aşevi

Aziziye Aşevi; yemek üretimi, stok, fatura, rapor ve kullanıcı işlemlerini
Streamlit tabanlı tek bir panelde yöneten uygulamadır.

## Gereksinimler

- Python 3.10 veya üzeri
- Supabase projesi (kalıcı veri ve kullanıcı işlemleri için)
- SMTP hesabı (e-posta raporları için, isteğe bağlı)

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Uygulamayı başlatmak için:

```powershell
streamlit run app.py
```

## Streamlit secrets

`.streamlit/secrets.toml` dosyasını yerelde oluşturun veya dağıtım
platformunun Secrets bölümünü kullanın:

```toml
FERNET_KEY = "..."
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "..."

MAIL_SENDER = "rapor@example.com"
MAIL_PASSWORD = "..."
MAIL_RECIPIENT = "yonetici@example.com"
MAIL_SERVER = "smtp.example.com"
MAIL_PORT = 587
```

`FERNET_KEY`, Fernet formatında geçerli bir anahtar olmalıdır. Anahtar
üretmek için:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

E-posta ayarları yalnızca manuel rapor gönderme düğmesi kullanıldığında
gereklidir. Uygulama artık her Streamlit yenilemesinde otomatik e-posta
göndermez.

## Proje yapısı

```text
app.py                  # Streamlit giriş noktası
src/                    # Uygulama modülleri
  besin_hesaplama.py    # Kalori hesaplama
  cekirdek.py           # Ortak veri ve iş kuralları
  dashboard_ui.py       # Dashboard yardımcıları
  ...
tests/                  # Regresyon ve davranış testleri
.streamlit/config.toml # Pure Dark tema ve Streamlit ayarları
```

Uygulamanın tema politikası Pure Dark’tır. Hava durumu verisi 15 dakika
önbelleğe alınır; ürün kalori eşleşmeleri yalnızca tam kelime sınırlarıyla
yapılır.

## Testler

```powershell
pytest -q
```

Uygulama başlatma kontrolü için:

```powershell
python -m py_compile app.py src\*.py
```

## Lisans

Bu proje [Apache License 2.0](LICENSE) ile lisanslanmıştır.

Copyright 2026 Sefa Ünal Topcu (Aziziye Aşevi adına)
