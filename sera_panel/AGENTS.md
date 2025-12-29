# Agent Rehberi — AKILLI SERA (Momo & Nova Station)

Bu repo fiziksel donanımı kontrol edebildiği için bazı komutlar “gerçek dünyada” etki yaratır. Bu rehberin amacı: güvenli kalmak, doğru dosyayı doğru yerden değiştirmek ve donanım testlerini kontrollü yapmak.

## Ben kimim?
Ben **Sahin**. “**AKILLI SERA – Momo & Nova Station**” adlı projeyi geliştiriyorum. Raspberry Pi 4 (4GB) kullanıyorum; sistem **Raspberry Pi OS + Python + Flask + GPIO** odaklı.

## Proje özeti
4 katlı portatif serada (Gardener 16040) sıcaklık, nem, ışık ve toprak nemini izleyip; ışık, fan, ısıtıcı ve ileride sulamayı otomatik kontrol etmek istiyorum. Yerel ağdan web arayüz (Flask) ve ayrıca 20×4 I2C LCD ile durumu görüyorum.

## Mevcut donanım (özet)
- **Kontrol:** Raspberry Pi 4 (4GB)
- **Aydınlatma:** 4× 12V 5730 LED bar (6500K), alüminyum profiller, 12V 8.5A adaptör, DC barrel jaklar
- **Sensörler:** DHT22, DS18B20 (su geçirmez), 3× kapasitif nem sensörü (analog), BH1750 (I2C), ADS1115 (I2C ADC)
- **Aktüatörler:** 12V 120mm fan, 12V PTC ısıtıcı plaka, 2 kanallı 5V röle kartı, durum LED’leri (kırmızı/yeşil/sarı)
- **Arayüz:** 20×4 I2C LCD
- **Prototipleme:** breadboard, T-Cobbler, jumper kablolar, dirençler (4.7K, 330R)

## Kısa sözlük (terimler)
- **GPIO (BCM numarası):** Raspberry Pi üzerindeki kontrol pinleri. Koddaki “GPIO18” gibi sayılar genelde **BCM** numarasıdır (fiziksel pin sırası değildir).
- **Röle active-low / active-high:** `active_low=true` ise genelde **0 = ON**, **1 = OFF**; `active_low=false` ise tam tersi olabilir.
- **I2C:** BH1750/ADS1115/LCD gibi cihazların konuştuğu 2 kablolu hat. I2C cihazlarının **adresleri** olur (örn. `0x23`, `0x48`, `0x27`).
- **1-Wire:** DS18B20 sıcaklık sensörünün kullandığı hat (genelde `/sys/bus/w1/devices/28-*` olarak görünür).
- **SAFE MODE:** Panelde “güvenli kilit” modu; aktüatör komutlarını engeller. (Acil durdurma yine çalışır.)
- **SIMULATION_MODE:** `SIMULATION_MODE=1` iken donanım olmadan simülasyon (geliştirme/test için güvenli).
- **DISABLE_BACKGROUND_LOOPS:** `DISABLE_BACKGROUND_LOOPS=1` iken sensör/otomasyon thread’leri çalışmaz (testlerde kullanılır).

## Kritik güvenlik kuralları (ZORUNLU)
- Varsayılan hedef: **tüm röleler OFF** (pompa kilitli, ısıtıcı kapalı).
- Pompa ve ısıtıcı: sadece **süre limitli** çalıştır (test için kısa: pompa 3–5 sn, ısıtıcı 5–10 sn).
- Isıtıcı açıkken fan mantığı: mümkünse **fan ON olmadan ısıtıcı ON yapma**.
- GPIO/röle davranışını değiştirmeden önce daima mevcut durumu oku (örn. `gpioinfo`, `gpioget`, `raspi-gpio get`).
- Sistem güvenliği: root/sudo kullanımında dikkat; gereksiz servis/boot değişikliği yapma.

## Dosya haritası (bu klasörde ve repoda)
- Ana uygulama: `app.py` (repo kökü)
- Bu klasördeki `app.py`: sadece **launcher** (kök `app.py`’yi import eder ve 5000 portunda çalıştırır)
- Kanal/GPIO eşlemesi (asıl kaynak): `config/channels.json`
- Sensör/LCD ayarları: `config/sensors.json`
- Röle test scriptleri: `sera_panel/relay_polarity_test.sh`, `sera_panel/relay_click_test.sh`
- Not: `sera_panel/config.json` ve `sera_panel/config/channels.json` eski/deneysel kalmış olabilir; güncel mapping için önce `config/` klasörüne bak.

## Güvenli çalışma akışı (adım adım)
1) **Donanım yokken veya emin değilsen:** `SIMULATION_MODE=1` ile çalıştır, UI/API akışını doğrula.
2) **Donanım varken:** SAFE MODE açıkken başla; önce sadece izleme ve sensör okuma doğrula.
3) **Röle yönü (active-low/active-high) belirsizse:** yükleri (özellikle pompa/ısıtıcı) güvene alıp `bash sera_panel/relay_polarity_test.sh` ile “klik” hangi değerde geliyor kontrol et.
4) **Kısa röle tıklama testi gerekiyorsa:** yine yükleri güvene alıp `bash sera_panel/relay_click_test.sh` ile sırayla test et (pompa/ısıtıcı süreleri kısa tutulmalı).
5) **Değişiklik sonrası:** `config/channels.json` değiştiyse tüm kanalların OFF olmasını garanti et ve UI’dan tekrar doğrula.

## Agent çalışma prensipleri
- Kodları genelde anlamayabilirim: her şeyi **adım adım**, uygulanabilir şekilde yaz.
- Dosya düzenleme gerekiyorsa, “şunu bul değiştir” demeden terminal komutlarıyla otomatik yap.
- Riskli komutlar (`sudo`, `gpioset`, `systemctl stop`) çalıştırmadan önce **ne yapacağını ve etkisini** net söyle.
- Her değişiklikten sonra çalıştırılabilir doğrulama komutları öner (örn. `pytest`, `curl`, script testleri).
- Commit/push istenirse önce `git status` kontrol et; **sadece ilgili dosyaları** stage et ve alakasız değişiklikler varsa kullanıcıya sor.
- Toplu silme/yeniden yazma (örn. `reports/` altı) gibi işlemleri **açık talep olmadan** yapma; gerekirse onay iste.

## UX ve ürün prensipleri (hata tekrarı olmasın)
- **Bilgi önceliği:** Her sayfada "en önemli 3 durum" görünür olmalı; detaylar ikincil katmanda kalmalı.
- **Riskli aksiyonlar:** Pompa/ısıtıcı gibi kritik komutlarda ikili onay + geri sayım görseli zorunlu.
- **Otomasyon gerekçesi:** Her otomasyon kararında "neden bu karar verildi" metni/etiketi sun.
- **Bildirim + audit:** Kritik eşiklerde bildirim (email/telegram) ve "kim-ne zaman-ne yaptı" audit kaydı olmadan özellik kapanmış sayılır.
- **İlk kurulum akışı:** Yeni kullanıcı için 5 dk içinde ilk okuma hedefi; ayarlar basit/gelismis mod ile ayrılmalı.
- **Veri yönetimi:** Ayar yedekleme/geri yükleme ve veri saklama/temizleme politikası belirtilmeden raporlama genişletme.
- **Terminoloji standardı:** Lux/lx, °C, %, kWh, dakika/saniye gibi birimler tek formatta.
- **Legacy ayrımı:** `sera_panel` sadece geriye dönük destek; yeni UX/özellikler ana panelde.

## Yol haritası uyumu
- Faz 0: Menü etiket temizliği, terminoloji düzeltmeleri, basit/gelismis görünüm.
- Faz 1: Durum özeti kutusu, kritik aksiyon onayı, "son komutlar + neden" paneli, mobil iyileştirme, mikro yardım.
- Faz 2: Bildirim kanalları, audit log, otomatik SAFE MODE, ayar yedek/geri yükleme.
- Faz 3: Otomasyon karar açıklamaları, senaryo profilleri, günlük toplam limit raporu, bağımlılıkların görünürleştirilmesi.
- Faz 4: Hedef-sapma trendleri, haftalık öneriler (sadece gözlem), veri kalitesi dashboardu.

## Hedef modüller (yol haritası)
- Sensör okuma servisleri (DHT22, DS18B20, BH1750, ADS1115)
- Flask API:
  - `/api/status` (sensör durumları)
  - `/api/actuator/<name>` (güvenli aktüatör kontrol; süre limitli)
- LCD: özet ekran + alarm durumları
- Otomasyon: ışık/fan/ısıtıcı/pompa güvenli eşikler + bağımlılıklar

## Yapılmaması gerekenler
- Yeni donanım önermek (zorunlu olmadıkça).
- Pompa/ısıtıcıyı onaysız uzun süre çalıştırmak.
- Ağ güvenliği zayıf ayarlar (rastgele port açma, şifreleri düz metin yazma).

## Kalite ve kabul kriterleri
- Kritik akışlar için SIMULATION_MODE testleri olmadan PR yapılmaz.
- UI smoke testleri: `/dashboard`, `/control`, `/settings`, `/reports` temel yüklenme kontrolü.
- SAFE MODE ve `emergency_stop` regresyon kontrolü yapılır.
- Başarı kriterleri: yeni kullanıcı 5 dk içinde ilk okuma görür; kritik alarm 60 sn içinde bildirilir; günlük rapor "ne oldu + ne yapmalıyım" tek sayfada cevaplar.
