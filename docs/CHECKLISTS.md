# AKILLI SERA — Değişiklik Checklist’leri

Bu checklist’ler, Codex/agent’in planlamasını ve senin hızlı gözden geçirmeni kolaylaştırır.
Donanım etkileyen değişikliklerde “minimum doğrulama” maddeleri zorunludur.

## UI Değişikliği (yalnız arayüz)
- [ ] Kritik aksiyonlar (pompa/ısıtıcı) için ikili onay/uyarılar bozulmadı.
- [ ] Dashboard/Kontrol/Ayarlar sayfaları açılıyor (smoke).
- [ ] Simülasyonda hızlı kontrol: `make run-sim` (veya `SIMULATION_MODE=1 python3 app.py`)

## API / Backend Değişikliği
- [ ] Simülasyon testleri: `make test` (veya `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`)
- [ ] Geriye dönük uyum: mevcut endpoint/JSON alanları kırılmadı (veya notu düşüldü).
- [ ] Hata durumları güvenli: riskli aksiyonlarda default **engelle**.

## Konfig Değişikliği (`config/*.json`)
- [ ] `make doctor` temiz (veya `python3 scripts/doctor.py`).
- [ ] `config/channels.json` değiştiyse: mapping yazma sonrası tüm kanallar OFF davranışı korunuyor.
- [ ] Kullanıcıya görünür değişiklikse `config/updates.json` notu eklendi.

## GPIO / Röle / Donanım Davranışı Değişikliği (yüksek risk)
- [ ] Önce simülasyon: `make test` (veya `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`)
- [ ] SAFE MODE varsayılanı korunuyor; acil durdurma çalışıyor.
- [ ] Pompa/ısıtıcı süre limitleri korunuyor (uzun süre ON yok).
- [ ] Röle polaritesi değiştiyse: yükler güvene alındı ve kısa doğrulama yapıldı.
- [ ] Donanım komutları için geri dönüş planı hazır (servis stop/rollback, mapping geri alma).

## Raporlama/Profil Değişikliği
- [ ] Eşikler/özetler mantıklı; birim ve terminoloji tutarlı.
- [ ] `tests/test_reporting.py` geçiyor.
