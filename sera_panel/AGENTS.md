# Agent Rehberi — AKILLI SERA (Momo & Nova Station)

## Ben kimim?
Ben **Sahin**. “**AKILLI SERA – Momo & Nova Station**” adlı projeyi geliştiriyorum. Raspberry Pi 4 (4GB) elimde ve sistem **Raspberry Pi OS + Python + Flask + GPIO** odaklı ilerliyor.

## Proje özeti
4 katlı portatif serada (Gardener 16040) sıcaklık, nem, ışık ve toprak nemini izleyip; ışık, fan, ısıtıcı ve ileride sulamayı otomatik kontrol etmek istiyorum. Yerel ağdan web arayüz (Flask) ve ayrıca 20x4 I2C LCD ile durumu göreceğim.

## Mevcut donanım (özet)
- **Kontrol:** Raspberry Pi 4 (4GB)
- **Aydınlatma:** 4× 12V 5730 LED bar (6500K), alüminyum profiller, 12V 8.5A adaptör, DC barrel jaklar
- **Sensörler:** DHT22, DS18B20 (su geçirmez), 3× kapasitif nem sensörü (analog), BH1750 (I2C), ADS1115 (I2C ADC)
- **Aktüatörler:** 12V 120mm fan, 12V PTC ısıtıcı plaka, 2 kanallı 5V röle kartı, durum LED’leri (kırmızı/yeşil/sarı)
- **Arayüz:** 20×4 I2C LCD
- **Prototipleme:** breadboard, T-Cobbler, jumper kablolar, dirençler (4.7K, 330R)

## Kritik güvenlik kuralları (ZORUNLU)
- Varsayılan durum: **tüm röleler OFF** (pompa kilitli, ısıtıcı kapalı).
- Pompa ve ısıtıcı: sadece **süre limitli** çalıştır (test maks. 5–10 sn).
- Isıtıcı açıkken fan mantığı: mümkünse **fan ON olmadan ısıtıcı ON yapma**.
- GPIO/role değiştirmeden önce daima **durumu oku** (gpioget/gpioinfo vb.).
- Sistem güvenliği: root/sudo kullanımında dikkat; gereksiz servis/boot değişikliği yapma.

## Agent çalışma prensipleri
- Ben kodları genelde anlamayabilirim: her şeyi **adım adım**, uygulanabilir şekilde yaz.
- Dosya düzenleme gerekiyorsa, “şunu bul değiştir” demeden **terminal komutlarıyla otomatik** yap.
- Her değişiklikten sonra:
  - `git diff` (varsa) göster
  - çalıştırılabilir test komutları öner (`python -m ...`, `pytest`, `curl ...`)
- Donanımla ilgili riskli işlemlerde önce güvenli kontrol:
  - Röle polaritesi (aktif-LOW/aktif-HIGH) doğrulaması
  - Çıkışları kısa süreli test
  - Loglama/uyarı mesajları

## Hedef modüller
- Sensör okuma servisleri (DHT22, DS18B20, BH1750, ADS1115)
- Flask API:
  - `/api/status` (sensör durumları)
  - `/api/relay/<name>` (güvenli role kontrol; süre limitli)
- LCD:
  - özet ekran (T/H/Lux/Nem) + alarm durumları
- Otomasyon:
  - ışık: günlük lux izleme + hedef aydınlatma eksikse belirli saat açma
  - fan: sıcaklık/nem eşiklerine göre
  - ısıtıcı: güvenli eşikler + fan bağımlılığı

## Yapılmaması gerekenler
- Yeni donanım önermek (zorunlu olmadıkça).
- Pompa/ısıtıcıyı onaysız uzun süre çalıştırmak.
- Ağ güvenliği zayıf ayarlar (rastgele port açma, şifreleri düz metin yazma).
