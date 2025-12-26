# AKILLI SERA – Yol Haritası (Tek Sayfa Özet)

## Amaç

- Seranın anlık durumunu tek ekranda görmek (sensör + aktüatör)
- Güvenli manuel kontrol ve otomasyon
- Ölçeklenebilir yapı (çok kat / çok saksı)

## Güvenlik İlkeleri

- Varsayılan OFF, SAFE MODE açık
- Pompa/ısıtıcı süre limitli + cooldown
- Sensör hatasında fail-safe OFF
- Öncelik: Güvenlik > Manuel > Otomasyon

## Aşamalar ve Kilometre Taşları

- M1: İzleme MVP
  - Dashboard + /api/status
  - Veri tazeliği + uyarılar
- M2: Güvenli manuel kontrol
  - SAFE MODE kilidi, E-STOP
  - Pompa/ısıtıcı limitleri
- M3: Temel otomasyon
  - Lux tamamlama, ısıtıcı, nem fan
- M4: Grafik & kalibrasyon
  - /api/history, grafikler, kalibrasyon, CSV
- M5: Enerji & sağlık
  - Enerji tahmini, sensör sağlık paneli
- M6: Olay günlüğü & bildirim
  - Audit log, bildirim kanalı

## Önceliklendirme

- P0: SAFE MODE kilidi, veri tazeliği uyarısı, E-STOP, pompa/ısıtıcı limitleri, fail-safe
- P1: Lux/ısı/nem otomasyonları, sensör loglama, kalibrasyon
- P2: Enerji tahmini, sağlık paneli, bildirimler

## MVP Kabul Kriterleri

- Dashboard tek sayfada tüm sensör + aktüatör görünür
- SAFE MODE açıkken manuel kontrol çalışmaz
- Sensör verisi 10+ sn gecikirse uyarı görünür
- Pompa ve ısıtıcı limitleri zorunlu çalışır

## KPI (ilk sürüm)

- Sensör okuma başarı oranı %95+
- Kritik hatalara tepki < 5 sn
- Dashboard yüklenme < 2 sn (LAN)

## Release Checklist (kısa)

- SAFE MODE varsayılan açık
- Kritik API’ler test edildi
- Servis restart sonrası durum kontrol edildi
