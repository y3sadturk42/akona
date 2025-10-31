# Üretim Verimliliği Takip Uygulaması

Bu proje, üç vardiya ile çalışan üretim tesislerinde günlük üretim verimliliğini takip etmek için hazırlanmış basit bir web uygulamasıdır. Şu an için Yağmurlama Bölümü'ndeki L1, L2 ve L3 makineleri desteklenir; diğer bölümler için altyapı hazırdır.

## Özellikler

- Kullanıcı adı/şifre ile giriş kontrolü (varsayılan kullanıcı: `admin` / `admin123`).
- 7 bölüm için referans kayıtları ve Yağmurlama Bölümü'ne bağlı L1-L3 makineleri.
- Tanımlı çap/hız tablosuna göre teorik üretim ve verimlilik hesabı.
- Her kayıt için vardiya, tarih, makine, çap, üretim miktarı ve not alanları.
- Seçili tarih için vardiya bazında kayıtları listeleme.

## Kurulum

1. Bağımlılıkları kurun:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Veritabanını oluşturun (isteğe bağlıdır; uygulama ilk çalıştırmada da otomatik oluşturur):

   ```bash
   flask --app app init-db
   ```

3. Uygulamayı başlatın:

   ```bash
   flask --app app run --debug
   ```

   Alternatif olarak doğrudan Python ile de çalıştırabilirsiniz:

   ```bash
   python main.py
   ```

4. Tarayıcınızdan `http://127.0.0.1:5000/` adresine gidin ve giriş yapın.

## Notlar

- Varsayılan kullanıcı bilgilerini ilk girişten sonra `flask shell` ile veritabanına bağlanarak güncellemeniz önerilir.
- Üretim miktarı alanı metre cinsinden kabul edilir. Teorik üretim hesabında her vardiya için 420 dakikalık aktif çalışma süresi dikkate alınır.
- Üçüncü vardiya gece 23:30'da başladığı için, başlangıç tarihine göre kaydedilmelidir.
