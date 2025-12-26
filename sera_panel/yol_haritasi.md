# AKILLI SERA – Yol Haritası

Bu yol haritası `hedef.md` içeriğini teslim edilebilir, adım adım bir plana böler.

## Başlangıç (Sprint 0) – Dokümantasyon ve netleştirme

- [x] Hedef dokümanını kaydet (hedef.md)
- [x] Yol haritası oluştur (yol_haritasi.md)
- [x] Mevcut durum envanteri çıkar (sensörler, aktüatörler, aktif endpoint’ler)
- [ ] Kritik güvenlik limitlerini doğrula (pompa/ısıtıcı max süre, cooldown)

## Mevcut durum (güncel)

- Sensörler: DHT22, DS18B20, BH1750 (I2C), ADS1115 (CH0–CH3)
- Aktüatörler: R1_LIGHT_K1A, R2_LIGHT_K1B, R3_PUMP, R4_HEATER, R5_FAN, R6_POT_FAN
- UI: Dashboard (anlık, grafik, enerji, sensör sağlık, olay), Kontrol, Ayarlar, Pin Mapping, Test Panel
- API: /api/status, /api/actuator/<name>, /api/emergency_stop, /api/settings, /api/config, /api/pins, /api/history, /api/events
- Güvenlik: SAFE MODE varsayılan açık, pompa limit/cooldown, ısıtıcı max+cutoff, stale fail-safe, admin token/yerel ağ kısıtı
- Otomasyon: lux tamamlama, ısıtıcı, nem fan, periyodik fan, sulama

## Aşama 1 – MVP (İzleme)

Çıkış kriteri: Tek ekranda anlık sensör + aktüatör durumu okunabilir.

- [x] /api/status çıktısını netleştir (veri gecikmesi, son değişiklik zamanı)
- [x] Dashboard “Şu an” kartları + uyarılar bandı
- [x] Sensör hata gösterimi (okunamadı/timeout)
- [x] Basit sensör loglama (SQLite veya dosya)

## Aşama 2 – Güvenli Manuel Kontrol

Çıkış kriteri: SAFE MODE + güvenli manuel kontrol tam ve sınırlı.

- [x] SAFE MODE kilidi + UI’da görünür durum
- [x] Pompa süre limit + cooldown + kilit
- [x] Isıtıcı max süre + üst limit kesme
- [x] Acil durdur (tüm aktüatör OFF)

## Aşama 3 – Otomasyon

Çıkış kriteri: Temel 3 otomasyon (ışık, ısı, nem) kararlı çalışır.

- [x] Lux tamamlama (BH1750)
- [x] Isıtıcı kontrol (DHT22/DS18B20)
- [x] Nem bazlı fan kontrolü
- [x] Sulama (toprak nemi + güvenlik)
- [x] Periyodik havalandırma + gece modu
- [x] Alarm/Fail-safe kuralları

## Aşama 4 – Grafikler & Kalibrasyon

Çıkış kriteri: 24s/7g grafik + kalibrasyon ekranı.

- [x] /api/history endpoint’i
- [x] Grafikleri dashboard’a ekle
- [x] Nem sensörü kalibrasyon akışı
- [x] CSV dışa aktarım

## Aşama 5 – Enerji & Sağlık

Çıkış kriteri: Enerji tahmini + sensör sağlık paneli.

- [x] Cihaz kataloğu (W/voltaj/adet)
- [x] Günlük/haftalık enerji tahmini
- [x] Sensör sağlık paneli (offline süre, hata oranı)

## Aşama 6 – Olay Günlüğü & Bildirim

Çıkış kriteri: Olay günlüğü + alarm bildirimleri.

- [x] Audit log (manuel/otomasyon/güvenlik)
- [ ] Bildirim kanalı (Telegram/e-posta/yerel)
- [ ] Bildirim sessize alma

## Başladığım ilk adım

Bugün başlamak için en güvenli ve düşük riskli iş:

- [x] Mevcut durum envanteri (sensörler, aktüatörler, endpoint’ler)
- [x] /api/status veri gecikmesi göstergesi

Onay verirsen bu adımı hemen uygulamaya alacağım.

## Yakın dönem ayrıntı planı (Aşama 1 odak)

### 1.1 Durum verisi ve tazelik

- [x] /api/status içine `data_age_sec` (sensör verisi yaşı) alanı ekle
- [x] Stale uyarı eşiği (örn. 10+ sn) ve uyarı mesajı
- [x] Aktüatör için son değişiklik zamanı gösterimi

### 1.2 Dashboard okunabilirlik

- [x] “Şu an” kartlarında değer + birim standardı
- [x] Uyarılar bandı (SAFE MODE, sensör hatası, stale)
- [x] Son güncelleme zamanı + renkli gecikme göstergesi

### 1.3 Sensör loglama (MVP)

- [x] `sensor_log` tablosu (ts, dht, ds, lux, soil1..)
- [x] 5–10 sn aralıkla loglama (arka plan döngüsünde)
- [x] Hata durumunda loglama yerine uyarı üret

## Aşama 2 ayrıntı planı (Güvenli manuel kontrol)

### 2.1 SAFE MODE kilidi

- [x] UI butonlarını kilitle (SAFE MODE açıkken)
- [x] SAFE MODE toggle için admin token doğrulama
- [x] Admin işlemleri için token/yerel ağ kısıtı (actuator/emergency/test)
- [x] Admin token girişi (UI + tarayıcıda saklama)
- [x] “SAFE MODE açık” uyarısını üst banda taşı

### 2.2 Pompa ve ısıtıcı güvenliği

- [x] Pompa: süre limit + cooldown görünür göstergesi
- [x] Isıtıcı: max süre + üst limit kesme alarmı
- [x] Fail-safe: sensör offline olursa pompa/ısıtıcı otomatik OFF

### 2.3 Acil durdurma

- [x] E-STOP butonu (tek tık)
- [x] Uygulama içi log: ne zaman, neden (event_log)
- [ ] Kimlik bilgisi (kim tetikledi) ekle

## Aşama 3 ayrıntı planı (Otomasyon)

### 3.1 Lux tamamlama

- [ ] Çoklu zaman penceresi desteği (1+ pencere)
- [x] Minimum açık kalma ve maksimum blok süresi
- [x] Lux üst limit kontrolü (çok aydınlıkta açma)

### 3.2 Sıcaklık kontrolü

- [x] DHT22/DS18B20 sensör seçimi
- [x] Histerezisli T_low/T_high
- [x] Gece modu (farklı hedefler)

### 3.3 Nem bazlı fan

- [x] RH_high/RH_low + cooldown
- [x] Gece sessiz modu (daha seyrek)

### 3.4 Sulama

- [ ] Pot eşlemesi (A0..A3 → POT_1..)
- [x] Kuru/ıslak kalibrasyon değerleri
- [x] Max günlük çalışma süresi

## Aşama 4 ayrıntı planı (Grafik & Kalibrasyon)

 - [x] /api/history (from/to/metric)
- [x] 24s/7g grafikler (seçilebilir)
- [x] Kalibrasyon ekranı (kuru/ıslak)
 - [x] CSV export

## Aşama 5 ayrıntı planı (Enerji & Sağlık)

- [x] Cihaz kataloğu (W, adet, voltaj)
- [x] Günlük/haftalık Wh/kWh tahmini
- [x] Sensör sağlık paneli (offline süre, hata oranı)

## Aşama 6 ayrıntı planı (Olay günlüğü & Bildirim)

- [x] Olay günlüğü: manuel/otomasyon/güvenlik ayrımı
- [ ] Bildirim kanalı seçimi (Telegram/e-posta/yerel)
- [ ] Sessize alma ve tekrar aralığı

### 6.1 Bildirim altyapısı

- [ ] Bildirim konfigürasyonu (kanal seçimi + kritik seviye)
- [ ] Uyarı için rate limit/cooldown
- [ ] Test bildirimi (tek tık)

### 6.2 Sessize alma

- [ ] Mute süreleri (15 dk / 1 sa / 1 gün)
- [ ] Kritik uyarılar için mute bypass

## Kabul kriterleri (MVP)

- [x] Dashboard tek sayfada tüm sensör + aktüatör durumunu gösterir
- [x] SAFE MODE açıkken hiçbir manuel kontrol çalışmaz
- [x] Sensör verisi 10+ sn gecikirse uyarı görünür
- [x] Pompa ve ısıtıcı süre limitleri zorunlu çalışır

## Test ve doğrulama (minimum)

- [ ] /api/status verisi doğru alanları içeriyor
- [ ] SAFE MODE açıkken /api/actuator 403 dönüyor
- [ ] Pompa süre limit dışı istekler reddediliyor
- [ ] Sensör okunamadığında uyarı logu üretiliyor

## Bağımlılıklar / Notlar

- I2C/1-Wire açık olmalı
- DHT22 için GPIO yetkisi ve kütüphane düzgün kurulmalı
- ADS1115 adresi ve kanal eşleşmesi netleşmeli

## Önceliklendirilmiş backlog (P0/P1/P2)

### P0 (kritik, olmazsa olmaz)

- [x] /api/status veri tazeliği ve uyarı bandı
- [x] SAFE MODE kilidi + görünür uyarı
- [x] Pompa ve ısıtıcı süre limitleri (UI + API)
- [x] Acil durdur (E-STOP)
- [x] Sensör offline fail-safe (pompa/ısıtıcı OFF)

### P1 (çok önemli)

- [x] Lux tamamlama otomasyonu (zaman pencereli)
- [x] Sıcaklık otomasyonu (histerezis)
- [x] Nem bazlı fan otomasyonu
- [x] Sensör loglama + /api/history taslağı
- [x] Kalibrasyon ekranı (kuru/ıslak)

### P2 (iyi olur)

- [x] Enerji tahmini paneli
- [x] Sensör sağlık paneli
- [x] Olay günlüğü
- [ ] Bildirimler
- [x] CSV export
- [ ] Raporlama

## Sprint planı (öneri)

### Sprint 1 (1-2 hafta)

- [x] P0 maddeleri: veri tazeliği, SAFE MODE kilidi, E-STOP
- [x] Dashboard okunabilirlik iyileştirmeleri

### Sprint 2 (1-2 hafta)

- [x] P0: pompa/ısıtıcı süre limitleri + fail-safe
- [x] P1: lux tamamlama otomasyonu

### Sprint 3 (1-2 hafta)

- [x] P1: sıcaklık + nem otomasyonu
- [x] Sensör loglama + /api/history taslağı

### Sprint 4 (1-2 hafta)

- [x] Kalibrasyon ekranı + CSV export
- [x] Enerji tahmini başlangıcı

### Sprint 5 (1-2 hafta)

- [ ] Bildirim kanalı (Telegram/e-posta/yerel)
- [ ] Çoklu zaman penceresi (lux otomasyonu)
- [ ] Saksı/pot eşlemesi (A0..A3 → POT_1..)
- [ ] Kimlik bilgisi (kim tetikledi) loglama

## Definition of Done (DoD)

- [ ] Güvenlik kuralları ihlal edilemiyor (SAFE MODE kilitli)
- [ ] Kritik aktüatörler süre limitli ve cooldown’lı
- [ ] UI’da açık/kapalı durumlar ve uyarılar net
- [ ] /api/status ve loglar tutarlı
- [ ] Basit test senaryoları çalışıyor

## Riskler ve önlemler

- [ ] Sensör okuması hatalı/boş → fail-safe OFF + uyarı
- [ ] Röle stuck → zaman aşımı + uyarı + otomatik kesme
- [ ] DHT22 hatalı → retry sınırı + uyarı
- [ ] Pompa kuru çalışma → süre limit + kilit

## Operasyonel kontrol listesi

- [ ] I2C/1-Wire aktif mi kontrol et
- [ ] Servis ayarlarını doğrula (systemd)
- [ ] SAFE MODE varsayılan açık
- [ ] Röle polaritesi test edildi

## Gözden geçirme noktaları

- [ ] Her aşama sonunda saha testi ve log inceleme
- [ ] Gerçek donanımda 24 saat gözlem
- [ ] Sensör stabilitesi raporu

## API haritalama (MVP → V2)

- [x] /api/status: sensör + aktüatör + uyarı + veri tazeliği
- [x] /api/actuator/<name>: manuel kontrol (SAFE MODE kilitli)
- [x] /api/emergency_stop: tüm aktüatör OFF
- [x] /api/settings: safe_mode + limitler + otomasyon ayarları
- [x] /api/history: grafik verisi (Aşama 4)
- [x] /api/events: olay günlüğü (Aşama 6)
- [ ] /api/rules: otomasyon kural CRUD (Aşama 3)
- [ ] /api/calibration: nem sensörü kalibrasyon (Aşama 4)

## Konfigürasyon yönetimi

- [x] `config/channels.json`: röle/pin eşlemesi + active_low + güç/adet/voltaj
- [ ] `config.json`: otomasyon ve limit ayarları
- [x] Ortam değişkenleri: `SIMULATION_MODE`, `ADMIN_TOKEN`, `BH1750_ADDR`
- [x] Konfig değişince tüm aktüatörler OFF (güvenli yeniden yükleme)

## Veri saklama politikası (öneri)

- [ ] Sensor log: 30–90 gün tutulur, eski kayıtlar temizlenir
- [ ] Actuator log: 90 gün tutulur
- [ ] CSV export: istek üzerine üretilir

## Geri alma / Recovery planı

- [ ] Konfig yedeği: her kayıtta timestamp’li backup
- [ ] Servis restart sonrası SAFE MODE açık
- [ ] Hatalı deploy → son çalışan sürüme dön

## Test matrisi (minimum)

- [ ] Sensör okuma: DHT22/DS18B20/BH1750/ADS1115
- [ ] API: /api/status, /api/actuator, /api/emergency_stop
- [ ] Güvenlik: SAFE MODE açıkken kontrol kilitli
- [ ] Fail-safe: sensör stale → pompa/ısıtıcı OFF

## UI/UX görevleri (okunabilirlik)

- [x] Kontrast kontrolü (metin/arkaplan)
- [ ] Mobil görünüm (kartlar tek sütun)
- [x] Uyarı bandı görünürlüğü

## Donanım kontrol listesi (saha)

- [ ] Röle polaritesi doğrulandı (active-low/high)
- [ ] Pompa testleri kısa süreli (5–10 sn)
- [ ] Isıtıcı testleri fan ON ile
- [ ] I2C cihaz adresleri doğrulandı

## İşletim / bakım

- [ ] Günlük: log ve uyarıları kontrol et
- [ ] Haftalık: sensör stabilitesi, kablo kontrolü
- [ ] Aylık: kalibrasyon tekrar kontrolü

## Kilometre taşları ve teslim çıktıları

### M1 – İzleme MVP (Aşama 1)

- Dashboard tek sayfa, sensör + aktüatör görünür
- /api/status veri tazeliği ve uyarı bandı
- Sensör hata gösterimi

### M2 – Güvenli manuel kontrol (Aşama 2)

- SAFE MODE kilidi + E-STOP
- Pompa/ısıtıcı limitleri ve cooldown görünür
- Fail-safe: stale sensör → riskli aktüatör OFF

### M3 – Temel otomasyon (Aşama 3)

- Lux tamamlama (BH1750)
- Isıtıcı kontrol (histerezis)
- Nem bazlı fan

### M4 – Grafik & kalibrasyon (Aşama 4)

- /api/history + 24s/7g grafik
- Nem sensörü kalibrasyonu
- CSV export

### M5 – Enerji & sağlık (Aşama 5)

- Cihaz kataloğu (W/adet)
- Enerji tahmini (günlük/haftalık)
- Sensör sağlık paneli

### M6 – Olay günlüğü & bildirim (Aşama 6)

- Audit log
- Bildirimler + sessize alma

## Takvim önerisi (esnek)

- Hafta 1–2: M1
- Hafta 3–4: M2
- Hafta 5–6: M3
- Hafta 7–8: M4
- Hafta 9–10: M5
- Hafta 11–12: M6

## Ölçülebilir metrikler

- Sensör veri gecikmesi (ortalama / p95)
- Otomasyon tetik başarı oranı
- Hata oranı (sensör offline, CRC, i2c)
- Pompa/ısıtıcı günlük çalışma süresi

## Açık sorular

- DHT22 için donanım stabilizasyonu (kablo, pull-up) netleşti mi?
- ADS1115 kanallarının saksı eşleşmesi kesin mi?
- BH1750 adresi 0x23 mü 0x5c mi?

## Karar kayıtları (özet)

- Öncelik kuralı: Güvenlik > Manuel > Otomasyon
- SAFE MODE varsayılan açık
- Pompa ve ısıtıcı süre limitli çalışır

## Versiyonlama (dokümantasyon)

- Her büyük değişiklikte hedef.md ve yol_haritasi.md güncellenir
- Uygulama sürümü için basit etiketleme (v0.x) önerilir

## Rol ve sorumluluklar

- [ ] Sahin: saha testleri, donanım doğrulama
- [ ] Yazılım: güvenlik kuralları ve panel geliştirme
- [ ] Dokümantasyon: hedef + yol haritası güncel tutulur

## Basit karar şablonu (RFC mini)

- [ ] Karar: ...
- [ ] Gerekçe: ...
- [ ] Etki: ...
- [ ] Geri dönüş: ...

## Deployment notları

- [ ] systemd servis yolları doğrulanmış olmalı
- [ ] `ADMIN_TOKEN` gerekliyse tanımlı olmalı
- [ ] `SIMULATION_MODE` üretimde 0 olmalı

## Kullanıcı senaryoları (MVP)

- [ ] Senaryo 1: Kullanıcı dashboard açar, anlık değerleri görür
- [ ] Senaryo 2: SAFE MODE kapalıyken manuel fan açar
- [ ] Senaryo 3: Pompa 5 sn çalıştırılır ve cooldown aktif olur
- [ ] Senaryo 4: Sensör offline → pompa/ısıtıcı kapanır + uyarı

## KPI hedefleri (ilk sürüm)

- [ ] Sensör okuma başarı oranı %95+
- [ ] Kritik hatalara tepki süresi < 5 sn
- [ ] Dashboard yüklenme < 2 sn (LAN)

## Ölçüm yöntemleri

- [ ] Sensör başarı oranı: 24 saatte okunan / beklenen ölçüm sayısı
- [ ] Tepki süresi: alarm tetik → aktüatör OFF süre farkı
- [ ] Dashboard yüklenme: tarayıcı network time-to-first-render

## Kabul checklist (yayına hazır)

- [ ] SAFE MODE varsayılan açık
- [ ] Pompa ve ısıtıcı limitleri doğrulandı
- [ ] Sensörler en az 24 saat stabil
- [ ] Fail-safe tetik testleri geçti

## Olası ölçekleme (çok kat/saksı)

- [ ] Pot sayısı artışına göre ADS1115 genişleme planı
- [ ] Kanal isimlendirme standardı korundu
- [ ] UI kartları dinamik listeleme

## Güvenlik ve erişim

- [ ] LAN dışına açık port yok
- [x] Admin işlemleri token veya yerel ağ kısıtıyla korunur
- [ ] Zayıf şifre/PIN yok

## Sürüm notları şablonu

- [ ] Sürüm: v0.x
- [ ] Tarih: YYYY-MM-DD
- [ ] Yeni: ...
- [ ] Düzeltme: ...
- [ ] Not: ...

## İletişim / destek

- [ ] Kurulum dokümanı güncel
- [ ] Sık sorulanlar (FAQ) taslağı

## Eğitim / kullanım rehberi

- [ ] SAFE MODE kullanımı
- [ ] Pompa/ısıtıcı güvenlik kuralları
- [ ] Otomasyonların devreye alınması

## Kapsam dışı (şimdilik)

- [ ] Bulut bağlantısı / uzak erişim
- [ ] Yeni donanım ekleme
- [ ] Kamera ve görüntü işleme
- [ ] ML tabanlı otomasyon

## Gözlemleme / telemetri

- [ ] Servis sağlık endpoint’i (/health)
- [ ] Sensör okuma sayacı ve hata sayacı
- [ ] Otomasyon tetik sayacı

## Yedekleme ve geri yükleme

- [ ] Konfig dosyaları için otomatik yedek
- [ ] SQLite veritabanı günlük yedek
- [ ] Geri yükleme adımları dokümanı

## Definition of Ready (DoR)

- [ ] Gereksinim net, hedef kabul kriteri yazılı
- [ ] Güvenlik etkisi değerlendirildi
- [ ] Test yaklaşımı belirlendi

## Release checklist (kısa)

- [ ] Servis restart sonrası durum kontrol edildi
- [ ] Kritik API’ler test edildi
- [ ] SAFE MODE varsayılan açık

## Yapılandırma varsayılanları (öneri)

- [ ] SAFE MODE: açık
- [ ] Pompa max süre: 5–10 sn
- [ ] Pompa cooldown: 60 sn
- [ ] Isıtıcı max süre: 5 dk
- [ ] Lux eşiği (LUX_OK): 300–400
- [ ] Nem fan eşiği: 80% → aç, 70% → kapat

## Log formatı (öneri)

- [ ] ts, source, level, message
- [ ] source: sensor/actuator/automation/safety
- [ ] example: 2025-12-21T10:00:00Z,safety,warning,Sensor stale → heater OFF

## Hazır otomasyon presetleri (öneri)

- [ ] Sıcaklık: 18–20°C (gece 17–19°C)
- [ ] Nem fan: 80% üstü 3 dk, 70% altı kapat
- [ ] Işık: 08:00–22:00, LUX_OK 350, hedef 300 dk
- [ ] Sulama: 5 sn darbe, cooldown 60 sn

## A/B testleri (opsiyonel)

- [ ] Farklı LUX_OK değerlerini haftalık kıyasla
- [ ] Nem eşiği değişimlerinin küf etkisi

## Haftalık rapor şablonu (kısa)

- [ ] Hafta: YYYY-WW
- [ ] Özet: ana gelişmeler
- [ ] Sorunlar: bloklayan konular
- [ ] Sensör sağlık: okuma oranı, hata sayısı
- [ ] Otomasyon: tetik sayıları
- [ ] Sonraki hafta: plan

## Örnek test senaryoları (MVP)

- [ ] SAFE MODE açık → /api/actuator 403
- [ ] Pompa 20 sn isteği → reddedilir (limit üstü)
- [ ] Sensör stale simülasyonu → pompa/ısıtıcı OFF
- [ ] Lux düşük + pencere içi → ışık ON

## Metrik toplama tablosu (taslak)

- [ ] metric: sensor_success_rate, window: 24h
- [ ] metric: actuator_on_minutes, window: daily
- [ ] metric: automation_trigger_count, window: daily
- [ ] metric: alerts_count, window: weekly

## İlerleme takibi (basit)

- [ ] Her hafta sonunda yol_haritasi.md güncellensin
- [ ] Tamamlanan maddeler işaretlensin

## Metrik toplama teknik planı (öneri)

### Veri kaynakları

- [ ] sensor_loop: okuma sayısı, hata sayısı, son okuma zamanı
- [ ] actuator_manager: toplam ON süreleri, tetik sayısı
- [ ] automation_engine: tetik sayısı, pas geçme nedeni
- [ ] alerts: uyarı sayısı ve tipleri

### Toplama noktaları

- [ ] Sensör okuma sonrası sayaçları güncelle
- [ ] Aktüatör state değişiminde süre sayaçlarını güncelle
- [ ] Otomasyon tick sonunda tetik/skip kaydet

### Depolama (SQLite öneri)

- [ ] metrics_daily(date, key, value)
- [ ] metrics_hourly(ts_hour, key, value) (opsiyonel)
- [ ] alerts_log(ts, level, source, message)

### Retention

- [ ] Hourly: 7–14 gün
- [ ] Daily: 90 gün

### API ve UI

- [ ] /api/metrics?window=24h|7d|30d
- [ ] Dashboard: küçük KPI kutuları
- [ ] Sistem sayfası: detaylı metrik görünümü

### Performans / güvenlik

- [ ] Metrik yazımı 1–5 dk aralıklı batch
- [ ] Sensör döngüsüne ek yük bindirme

## Doküman referansları

- [ ] hedef.md → kapsam ve güvenlik ilkeleri
- [ ] yol_haritasi_ozet.md → tek sayfa özet
- [ ] README.md → kurulum ve çalıştırma
