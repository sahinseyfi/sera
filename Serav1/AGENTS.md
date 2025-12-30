# Serav1 Agent Rehberi — Multi‑Zone Panel (Redesign)

Bu klasör; yeni panel tasarımı (multi-zone) için spec ve plan dokümanlarını içerir.
Amaç: büyük değişiklikleri kontrollü ilerletmek, kararları kaybetmemek ve güvenliği korumak.

## Kaynak Dokümanlar (önce oku)
- Ürün/UX spec: `Serav1/panel-redesign-spec.md`
- Mevcut durum referansı: `Serav1/current-state-reference.md`
- Karar kaydı (tek kaynak): `Serav1/decision-log.md`
- Donanım planı/envanter: `Serav1/hardware-plan.md`, `Serav1/hardware-inventory.md`
- İleri özellikler: `Serav1/future-features.md`

## Çalışma Prensipleri
- Büyük kararlarda (zone modeli, backend ayrımı, HA/ESP32 entegrasyonu) önce `Serav1/decision-log.md` güncelle; sonra kod.
- Varsayımlar için tek defter: `AGENT_ASSUMPTIONS.md` (donanım etkileyen varsayımlarda onaysız ilerleme yok).
- Mevcut paneli kırmadan ilerle: tercih edilen yaklaşım **additive** değişiklikler + net geçiş planı.
- Yeni config alanı eklediğinde: `config/schema/*.schema.json` + `scripts/doctor.py` güncelle; `make doctor` ile doğrula.
- Her PR/patch sonunda minimum doğrulama: `make doctor` + `make test`.

## Plan Formatı (Serav1 işleri)
- **Amaç → Kapsam dışı → Kararlar → Plan → Geçiş planı → Doğrulama** sırasını kullan.
- “Geçiş planı”: mevcut panel kullanıcılarını kırmadan nasıl devreye alacağız? (flag, config, paralel sayfa, gradual rollout).

## Doküman Tutarlılığı
- Her dosyada mevcut dili koru (EN yazılmış spec’e TR paragraf ekleme; TR dokümana EN paragraf ekleme).
- Büyük reformat yerine küçük, hedefli diff’ler yap (inceleme kolaylığı için).

## Güvenlik
- Donanım etkileyen değişikliklerde varsayılan rota `SIMULATION_MODE=1` doğrulamasıdır.
- GPIO/aktüatör komutları çalıştırma: önce etki + geri dönüş planı yaz; açık istek yoksa çalıştırma.
