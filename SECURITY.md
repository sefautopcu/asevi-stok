# Güvenlik yapılandırması ve geçiş notları

## Önemli durum

`security_utils.py` güvenli yardımcıları sağlar; mevcut `app.py` henüz bu yardımcıları
kullanmıyor. Bu nedenle bu dosyanın eklenmesi tek başına uygulamadaki güvenlik
bulgularını kapatmaz. Yayındaki uygulama, `app.py` entegrasyonu ve Supabase tarafı
tamamlanıp doğrulanana kadar güvenli kabul edilmemelidir.

## Öncelikli acil işlemler

1. Kodda yayımlanmış varsayılan admin parolasını ve `MASTER_RECOVERY_KEY` değerini
   geçersiz kılın. Yeni, benzersiz ve güçlü değerleri yalnızca dağıtımın Streamlit
   Secrets ayarına ekleyin. Eski erişim bilgileri açığa çıkmış kabul edilmelidir.
2. Supabase `service_role` anahtarını yenileyin; uygulamanın ihtiyaç duyduğu sırları
   yalnızca Streamlit Secrets'ta tutun. Bu anahtarı istemciye veya kaynak depoya
   koymayın. `service_role` RLS'yi bypass ettiği için, uygulama sunucusunda kalması
   gerekir; RLS tek başına sızıntıya karşı koruma sağlamaz.
3. `FERNET_KEY` için kalıcı, yedeklenmiş bir Fernet anahtarı ayarlayın. Anahtar
   değişimi mevcut şifreli kayıtların çözülmesini engelleyebilir; eski anahtar
   güvenli biçimde saklanmadan değiştirmeyin. Bu anahtar yoksa uygulama fail-closed
   çalışmalıdır.

## Streamlit Secrets

Aşağıdakiler dağıtım ortamında tanımlanmalıdır; örnek değerler bilerek verilmemiştir:

```toml
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "<server-side key>"
MASTER_RECOVERY_KEY = "<long random secret>"
FERNET_KEY = "<persistent Fernet key>"
```

Gerçek değerleri depoya veya issue/PR açıklamalarına eklemeyin. Fernet anahtarı
üretmek için güvenilir ortamda `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`
komutunu kullanın.

## Supabase RLS kontrol listesi

- `public.asevi_veritabani` tablosunda Row Level Security'yi etkinleştirin.
- Uygulama anon/authenticated istemcilerine doğrudan erişim vermeyin; mevcut
  uygulama özel kullanıcı/parola doğrulamasıyla çalıştığından anon anahtarıyla
  güvenli kullanıcı bazlı politika kurmak için ayrıca kimlik doğrulama tasarımı gerekir.
- `service_role` anahtarını yalnızca sunucu tarafında saklayın. RLS'yi etkinleştirmek
  `service_role` erişimini sınırlandırmaz; bu rol RLS'yi atlar.
- Politikaları ve erişimi ayrıcalıksız bir rolde test edin. Üretim verisine uygulamadan
  önce yedek alın.

## Yedekleme ve silme işlemleri

Supabase projesinde otomatik yedekleme/PITR planını etkinleştirin ve saklama süresini
kurum politikasına göre belirleyin. Düzenli geri yükleme testi yapın. Depo silme ve
bağlı stok kayıtlarını kaldırma işlemleri için uygulamada ayrıca hedef adıyla ikinci
bir onay adımı ve mümkünse soft-delete/geri alma yolu eklenmelidir.

## Kalan uygulama çalışması

- `app.py` varsayılan kimlik bilgilerini ve fabrika parolasına sıfırlama akışını
  kaldırmalı; kurtarma işleminde sabit parola atamak yerine yeni parola istemelidir.
- Giriş doğrulaması `verify_password` / `hash_password` kullanmalı ve eski SHA-256
  kayıtlarını başarılı girişte bcrypt'e yükseltmelidir.
- Kullanıcı içeriği `unsafe_allow_html=True` ile basılan her yerde bağlama uygun
  kaçışla korunmalı; tercihen tablo gösterimi `st.dataframe` ile yapılmalıdır.
- Oturum kimlik bilgileri URL query parametresinden kaldırılmalıdır. Streamlit'in
  `session_state`'i sunucu oturumuyla sınırlıdır; kalıcı/HttpOnly/Secure/SameSite
  cookie ayarı uygulamanın dağıtım mimarisine uygun, test edilmiş bir oturum katmanı
  gerektirir.
- IP tabanlı denetim ve rate-limit ancak güvenilir proxy başlıkları doğru
  yapılandırıldığında yapılmalıdır. İstemciden doğrudan gelen `X-Forwarded-For`
  değerine güvenmeyin; parola denemesi kilidini yalnızca kullanıcı adına bağlamayın.
- Giriş başarı/başarısızlık olaylarında kimlik, UTC zaman, sonuç, başarısız deneme
  sayısı ve proxy tarafından doğrulanmış IP kaydı tutun; sırları/parolaları loglamayın.

## Doğrulama

`security_utils.py` fonksiyonlarını uygulamaya bağlamadan önce test edin: geçersiz
şifre, bcrypt başarı/başarısızlık, SHA-256 geçiş hash'i, HTML özel karakterleri,
eksik/bozuk `FERNET_KEY`. Ayrıca RLS izin/ret senaryolarını staging projesinde
ayrıcalıksız API anahtarıyla kontrol edin.
