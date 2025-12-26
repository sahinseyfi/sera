# Ana hedef

Seranın anlık durumunu (sensörler + aktüatörler) tek ekranda görmek.

Güvenli biçimde manuel kontrol ve otomasyon çalıştırmak.

Sonradan büyütülebilir: çok kat / çok saksı / farklı senaryolar.

## 1) Tasarım ilkeleri (güvenlik odaklı)

- Varsayılan güvenli durum: Isıtıcı/Fan/Pompa/Işıklar OFF.
- SAFE MODE: Açıkken sadece izleme; kontrol butonları kilitli.
- Pompa süre limitli (ör. 5–15 sn) + “cooldown” (örn. 60 sn) + kilit.
- Isıtıcı süre limitli (örn. max 5 dk) + sıcaklık üst limitinde otomatik kesme.
- Fail-safe: Sensör hatası/timeout olursa tehlikeli aktüatörler OFF.
- Yetkilendirme: Panel tek cihazda olsa bile en azından PIN/şifre veya yerel ağ kısıtı.
- Çakışma/Öncelik kuralı (karar verildi)
  - Güvenlik > Manuel > Otomasyon
  - Güvenlik kuralları gerektiğinde tüm ilgili aktüatörleri keser.
  - Manuel kontrol, otomasyonun komutlarını geçersiz kılar.
  - Otomasyon en altta çalışır.

## 2) Sayfa yapısı (IA)

### 2.1 Dashboard (Ana ekran)

“Şu an” kartları:

- Ortam: sıcaklık/nem (DHT22)
- Toprak/su sıcaklığı (DS18B20)
- Işık (BH1750)
- Toprak nemi (her saksı/kat)
- Aktüatör durumu: Işıklar/Fan/Isıtıcı/Pompa (ON/OFF + son değişiklik zamanı)

Uyarılar bandı:

- “SAFE MODE açık”, “sensör okunamadı”, “eşik aşıldı” vb.
- Son güncelleme zamanı + veri gecikmesi (örn. 0–3 sn iyi, 10+ sn uyarı)

### 2.2 Kontrol (Manuel)

Her röle için net isimlendirme:

- Kat1 Işık A/B, Kat2 Işık…, Fan, Isıtıcı, Pompa, Saksı fanı…

Butonlar:

- ON / OFF
- Pompa için “X saniye çalıştır” (preset: 3s, 5s, 10s)
- “Acil Durdur” (tüm aktüatörleri OFF)

Güvenlik widget’ı:

- SAFE MODE toggle (admin)
- Pompa max süre, ısıtıcı max süre
- Cooldown durumu

### 2.3 Otomasyon Kuralları

Kural listesi (enable/disable)

Kural tanımı bileşenleri:

- Koşul (sensör) + eşik + histerezis
- Eylem (aktüatör) + süre
- Zaman penceresi (gündüz/gece)
- Güvenlik limitleri (max süre, cooldown, fail-safe)

Kural tipleri (panelden ayarlanabilir)

#### 1) Lux ile ışık tamamlama (BH1750)

Amaç: Gün içinde yeterli ışık alınmadıysa LED’lerle tanımlı saatlerde tamamlamak.

Mantık:

- “Yeterli lux” eşiği LUX_OK üstündeki süreyi topla (ok_minutes_today).
- Günlük hedef: target_ok_minutes.
- Zaman pencereleri içindeyken hedefe ulaşılmadıysa LED aç; hedefe ulaşınca kapat.

Panel ayarları:

- LUX_OK (lux), target_ok_minutes (dk), ölçüm aralığı (sn)
- Zaman pencereleri (1+)
- LED kanal seçimi (hangi röleler)
- Minimum açık kalma (dk), maksimum blok süresi (dk)
- Lux üst limit (ortam zaten çok aydınlıksa LED açma)
- Gün reset saati
- Manuel override davranışı

Fail-safe:

- SAFE MODE açıkken çalışmaz.
- BH1750 okuma hatasında pasif (LED açmaz).

#### 2) Sıcaklık kontrolü (Isıtıcı)

Amaç: Ortam sıcaklığını hedef aralıkta tutmak.

Sensör: DHT22 (ortam) ve/veya DS18B20 (toprak/su) seçilebilir.

Panel ayarları:

- T_low / T_high (histerezisli)
- Çalışma penceresi (örn. gece daha agresif)
- Isıtıcı max çalışma süresi (dk)
- Üst limit kesme (örn. T_high + güvenlik payı)

Fail-safe: sensör hatasında ısıtıcı OFF.

#### 3) Nem bazlı havalandırma (Fan)

Amaç: Yüksek nem/küf riskini azaltmak.

Sensör: DHT22 nem.

Panel ayarları:

- RH_high / RH_low (histerezis)
- Max fan süresi (dk)
- Minimum dinlenme/cooldown (dk)
- Gece modu (sessiz/az çalışma)

#### 4) Toprak nemine göre sulama (Pompa)

Amaç: Toprak nemi düşükse kısa darbelerle sulamak.

Sensör: ADS1115 kanalları (kapasitif nem sensörleri).

Panel ayarları:

- Pot seçimi (hangi sensör hangi saksı)
- Nem eşikleri (kuru/ıslak referansı veya kalibrasyon değerleri)
- Pompa darbe süresi (sn), max günlük çalışma (sn)
- Cooldown (sn/dk)
- Zaman penceresi (örn. sadece gündüz)

Fail-safe:

- SAFE MODE açıkken çalışmaz.
- Sensör okunmuyorsa pompa çalışmaz.

#### 5) Zaman bazlı ışık (fallback)

Amaç: Sensör/hesap devre dışı kaldığında minimum ışık rutini.

Panel ayarları:

- Açma-kapama saatleri
- Haftalık program (opsiyonel)
- LED kanal seçimi

#### 6) Periyodik havalandırma (küf önleme)

Amaç: Nem eşik aşmasa bile hava değişimi yapmak.

Panel ayarları:

- Her X dakikada bir Y dakika fan
- Gece farklı parametre

#### 7) Gece modu (enerji/ısı/ses yönetimi)

Amaç: Gece LED/fan/ısıtıcı davranışlarını farklılaştırmak.

Panel ayarları:

- Gece zaman aralığı
- Gece hedefleri (örn. farklı T/RH)

#### 8) Alarm & güvenlik kuralları (bildirim/ekran uyarısı)

Amaç: Anormal durumda kullanıcıyı uyarmak ve tehlikeli aktüatörleri kesmek.

Örnek tetikler:

- Aşırı sıcaklık / aşırı nem
- Sensör offline (X dakikadır veri yok)
- Röle stuck şüphesi (komut verildi ama durum değişmedi)

Panel ayarları:

- Eşikler ve gecikmeler
- “Acil durdur” davranışı (hangi röleler kesilsin)

Önerilen hazır kurallar (MVP):

- T < 18°C → Isıtıcı ON (max 5 dk), T > 20°C → OFF
- RH > 80% → Fan ON (max 3 dk), RH < 70% → OFF
- Işık < X lux ve saat 08:00–22:00 → Işık ON
- Toprak nemi < Y → Pompa 5 sn (cooldown 60 sn)

Lux tabanlı ışık otomasyonu (günlük ışık dozu)

Amaç: BH1750 lux ölçümüyle gün içinde bitkinin yeterli ışık alıp almadığını takip etmek; yetersizse LED’lerle tamamlamak.

Yöntem (pratik):

- “Yeterli ışık” eşiği LUX_OK üstündeki süreyi topla (ok_minutes_today).
- Günlük hedef: target_ok_minutes.
- Hedefe ulaşılamadıysa LED’leri sadece tanımlı zaman pencerelerinde aç.

Panelden ayarlanabilir ayarlar

- LUX_OK (lux eşiği)
- target_ok_minutes (dk)
- Ölçüm aralığı (sn) (lux örnekleme periyodu)
- Zaman pencereleri (örn. 08:00–11:00, 17:00–22:00) — birden fazla pencere
- LED kanal seçimi (hangi röleler bu otomasyona bağlı)
- Minimum açık kalma (dk) (çok sık aç/kapa önleme)
- Maksimum blok süresi (dk) (tek seferde üst limit)
- Lux üst limiti (ortam zaten çok aydınlıksa LED’i açma)
- Gün reset saati (günlük sayaçların sıfırlanacağı saat)
- Manuel override davranışı (manuel açıldıysa otomasyon ne yapsın)

Güvenlik / fail-safe

- SAFE MODE açıkken otomasyon çalışmaz (sadece izleme).
- Pencere dışındayken LED otomatik açılmaz.
- Hedefe ulaşıldığında LED otomatik kapanır.
- BH1750 okuma hatasında otomasyon pasif olur (LED açmaz).

### 2.4 Grafikler & Log

- 24 saat / 7 gün grafik (seçilebilir)
- Sensör bazında filtre
- Olay günlüğü:
  - Aktüatör değişiklikleri
  - Hatalar/uyarılar
  - Otomasyon tetiklemeleri
- Dışa aktarma: CSV

### 2.5 Kalibrasyon

Kapasitif nem sensörleri için:

- “Kuru kalibrasyon” (havada) / “Islak kalibrasyon” (su/çok ıslak toprak)
- Kanal eşlemesi (ADS1115 A0/A1/A2/A3 → hangi saksı)

Sensör sağlık testi:

- DHT22 okuma retry sayısı
- DS18B20 CRC hatası
- BH1750 okuma zamanı

### 2.6 Sistem & Bakım

Cihaz durumu:

- CPU sıcaklığı, disk doluluk, uptime
- Servisler: web, sensör döngüsü, otomasyon döngüsü

Konfig:

- Pin mapping
- Eşikler
- SAFE MODE

## 3) Veri modeli (mantıksal)

- sensor_readings: ts, dht_temp, dht_hum, ds18_temp, lux, soil1..soilN
- actuator_state: ts, relay_name, state, reason(manual/auto/safety), duration
- alerts: ts, level, message, cleared_ts
- rules: id, enabled, condition, action, schedule, hysteresis

## 4) API ihtiyaçları (tasarım)

- GET /api/status → anlık durum (sensörler + aktüatör + alarm)
- GET /api/history?from=&to=&metric= → grafik verisi
- POST /api/actuator/ → {state,on/off, seconds}
- POST /api/emergency_stop
- GET/POST /api/rules (listele, ekle, güncelle)
- POST /api/calibration (kuru/ıslak kaydet)

## 5) Teknik mimari (kod detayı yok)

3 döngü/servis düşün:

- Sensör okuma döngüsü (örn. 2–5 sn)
- Otomasyon değerlendirme döngüsü (örn. 2–5 sn)
- Web sunucu (Flask)

Veriyi basit başla: SQLite + dosya log (sonra büyüt)

LCD (20x4):

- Ekran 1: Ortam T/RH
- Ekran 2: Toprak T + Lux
- Ekran 3: Toprak nemleri (scroll)
- Ekran 4: Aktüatör durumları + uyarı

## 6) MVP’den sürüm planı (aşamalar)

### Aşama 1 (MVP – izleme)

- Dashboard + /api/status
- Sensörler stabil: DHT22, DS18B20, BH1750, ADS1115
- Basit log + hata gösterimi

### Aşama 2 (Güvenli manuel kontrol)

- SAFE MODE
- Pompa süre limit + cooldown
- Isıtıcı max süre + üst limit kesme
- Acil durdur

### Aşama 3 (Otomasyon)

- Kural tipleri: ışık (lux tamamlama), sıcaklık, nem fan, sulama, periyodik havalandırma, gece modu, alarm & güvenlik
- Histerezis + zaman penceresi
- Kural tetik kayıtları (asgarî düzey)

### Aşama 4 (Grafikler & Kalibrasyon)

- 24s/7g trend
- Nem sensörü kalibrasyonu
- CSV export

### Aşama 5 (Enerji & Sağlık)

- Enerji tahmini paneli (MVP sonrası ama erken eklenebilir)
- Panelden ayarlanabilir “Cihaz Kataloğu”
- Her aktüatör/kanal için: ad, bağlı röle, güç (W), adet (varsa), not (örn. LED bar sayısı)
- İsteğe bağlı: voltaj (12V/5V) sadece bilgi amaçlı
- Varsayılan güvenlik: gücü bilinmeyen cihazın W değeri 0 kabul edilir (enerji hesabını şişirmesin)
- Günlük/haftalık çalışma süresinden Wh/kWh tahmini çıkar
- Kanal bazında ve toplamda rapor (örn. Kat1 ışık A/B ayrı)
- Grafik: “bugün toplam Wh” ve “en çok tüketen kanal”
- Her aktüatör için “güç (W)” panelden girilir
- Günlük/haftalık çalışma süresinden Wh/kWh tahmini çıkar
- Sensör sağlık paneli
- Sensör başına: son okuma zamanı, hata oranı, retry sayısı, offline süresi
- Eşik: “X dakikadır veri yok” uyarısı

### Aşama 6 (V2 – Olay günlüğü & Bildirim)

- Olay günlüğü (audit log)
- Manuel/otomasyon/güvenlik kaynaklı tüm aktüatör değişiklikleri
- Kural tetiklemeleri ve hata olayları
- Bildirimler
- Alarm durumunda kullanıcıya bildirim (örn. Telegram/e-posta/yerel push)
- Bildirim sessize alma ve tekrar aralığı

## 7) İsimlendirme standardı

- Röleler: R1_LIGHT_K1A, R2_LIGHT_K1B, R3_PUMP, R4_HEATER, R5_FAN, R6_POT_FAN …
- Saksılar: POT_1 (kat1), POT_2 (kat2), POT_3 (kat3)

## 8) Risk notları (özellikle ısıtıcı/pompa)

- Isıtıcı: Yanıcı malzemeden uzak, fan yönüyle sıcak nokta oluşmasını engelle.
- Pompa: Kuru çalışmayı engelle (su seviyesi kontrolü yoksa süre limit + kullanıcı uyarısı).
- Röle/12V: Ortak GND düzeni ve kablo kesiti, klemens izolasyonu.
