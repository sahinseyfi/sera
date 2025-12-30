# AKILLI SERA — Runbook (Geliştirme + Operasyon)

Bu doküman, projeyi hızlı ve güvenli şekilde çalıştırmak/değiştirmek için pratik bir “rehber”dir.
Donanım kontrolü olduğu için varsayılan yaklaşım: **önce simülasyon**, sonra kontrollü donanım doğrulaması.

## Hızlı Komutlar
- Kurulum: `make install`
- Konfig kontrol: `make doctor`
- Test: `make test`
- Simülasyon çalıştır: `make run-sim`

Alternatif (make kullanmadan):
- Simülasyon çalıştır: `SIMULATION_MODE=1 python3 app.py`
- Test: `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`
- Konfig kontrol (önerilen): `python3 scripts/doctor.py`

> Not: `Makefile` hedefleri venv varsa onu kullanır.

## Modlar
- **Simülasyon (`SIMULATION_MODE=1`)**: Donanım olmadan güvenli geliştirme/test. Varsayılan tercih.
- **Gerçek donanım**: SAFE MODE açıkken başla; önce izleme ve sensör okumaları, sonra kontrollü aktüatör denemesi.

## Kritik Güvenlik İlkeleri (özet)
- Varsayılan hedef: **tüm aktüatörler OFF**.
- Pompa/ısıtıcı: **süre limitli** kullan.
- Riskli aksiyonlarda (GPIO/mapping, systemd, röle polaritesi) önce simülasyon doğrulaması yap.

## Konfig Dosyaları (tek kaynak: `config/`)
- `config/channels.json`: Kanal → GPIO mapping (`active_low` dahil).
- `config/sensors.json`: Sensör/LCD ayarları (I2C adresleri dahil).
- `config/panel.json`: Limitler + otomasyon + uyarı eşikleri (kalıcı panel ayarları).
- `config/reporting.json`: Raporlama eşikleri ve bitki profilleri.
- `config/notifications.json`: Bildirim ayarları.
- `config/retention.json`: Veri tutma/temizlik ayarları.
- `config/updates.json`: Panelde görünen güncelleme notları.

Değişikliklerden sonra: `python3 scripts/doctor.py`

## Sık İşler

### 1) Yeni kanal eklemek / GPIO değiştirmek
1. `config/channels.json` içine yeni kaydı ekle.
2. İsim/GPIO çakışması olmadığını doğrula: `python3 scripts/doctor.py`
3. Simülasyon testlerini çalıştır: `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`
4. Donanımda: SAFE MODE açıkken başla; ardından kısa ve kontrollü test yap.

### 2) Röle polaritesi (active-low / active-high) belirsizse
- Yükleri (özellikle pompa/ısıtıcı) güvene al.
- `bash sera_panel/relay_polarity_test.sh` ile rölenin “klik” ettiği değeri gözle.
- Sonucu `config/channels.json` içindeki `active_low` ile eşleştir.

### 3) I2C adres değişikliği (BH1750/ADS1115/LCD)
1. `config/sensors.json` içindeki `*_addr` alanını güncelle (`"0x.."` formatı).
2. `python3 scripts/doctor.py` ile formatı doğrula.
3. Donanımda gerekiyorsa `i2cdetect -y 1` ile adresi doğrula.

### 4) Telegram bildirimlerini açmak (opsiyonel)
1. Ortam değişkenlerini ver: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (örn. `/etc/sera-panel.env`).
2. Panel → Ayarlar → Bildirimler bölümünden etkinleştir/seviyeyi seç.
3. “Test Bildirimi Gönder” ile doğrula (SIMULATION_MODE’da varsayılan kapalıdır).

### 5) Retention (veri saklama/temizlik) ayarlamak
- 0 gün = silme kapalıdır (varsayılan).
- Silme geri alınamaz; gerekiyorsa arşivi aç ve önce yedek al.

## Değişiklik Sonrası Minimum Doğrulama
- `python3 scripts/doctor.py`
- `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`
- (İsteğe bağlı) `SIMULATION_MODE=1 python3 app.py` + `/api/status` kontrolü
