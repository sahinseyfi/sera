# Repository Guidelines — AKILLI SERA (Momo & Nova Station)

Bu repo Raspberry Pi üzerinde çalışan bir sera kontrol panelidir. Kod, fiziksel donanımı (röle/pompa/ısıtıcı/fan) kontrol edebildiği için öncelik her zaman **güvenlik**tir.

## Hızlı Başlangıç (geliştirme)
- Sanal ortam: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  - Not: Repoda `venv/` veya `sera-venv/` görülebilir; **tek bir venv** seçip onu kullanmak en temizi.
- Panel (donanım yokken): `SIMULATION_MODE=1 python3 app.py`
- Panel (gerçek donanım): `python3 app.py` (LAN: `http://<pi-ip>:5000`)
- Alternatif launcher: `python3 sera_panel/app.py` (aynı uygulamayı `0.0.0.0:5000` ile başlatır)
- Otomatik test: `SIMULATION_MODE=1 DISABLE_BACKGROUND_LOOPS=1 pytest -q`

## Proje Yapısı (nerede ne var?)
- `app.py`: Ana Flask uygulaması (API + otomasyon + GPIO katmanı)
- `templates/`, `static/`: Arayüz dosyaları
- `config/`: Çalışma zamanı ayarları
  - `config/channels.json`: Kanal ↔ GPIO eşlemesi (active-low/active-high)
  - `config/sensors.json`: Sensör/LCD ayarları (I2C adresleri dahil)
  - `config/reporting.json`: Raporlama/bitki profil eşikleri
  - `config/updates.json`: Panelde görünen “Güncellemeler” listesi
- `data/`: Üretilen veriler (SQLite + CSV loglar); git’e dahil edilmez
- `sera_panel/`: Launcher + eski dosyalar + röle test scriptleri (`relay_*.sh`)
- `sera_projesi/`: Eski/alternatif giriş noktası
- Kök `*_test.py` dosyaları: Donanım denemeleri (tekil scriptler)
- `tests/`: `pytest` ile çalışan temel otomatik testler (SIMULATION_MODE ile)

## Güvenlik (donanım)
- Varsayılan hedef: tüm aktüatörler OFF; pompa/ısıtıcı sadece süre-limitli.
- Röle/pompa/ısıtıcıyla ilgili değişikliklerde önce `SIMULATION_MODE=1` ile doğrula.
- Donanım testleri için `sera_panel/AGENTS.md` içindeki checklist ve kuralları takip et.

## Konfigürasyon & Secrets
- Mapping/sensör ayarlarını `config/*.json` içinde tut; koda sabitleme yapma.
- `ADMIN_TOKEN` gibi değerleri env var olarak kullan; repoya secret ekleme.
- Donanım davranışı değişiyorsa (GPIO/I2C/pin): kod/README içinde net belirt.

## Güncelleme Notu (UI)
- GitHub’a push ettiğinde kullanıcıya görünür bir not eklemek için `config/updates.json`’a yeni bir kayıt gir.
- Kayıtlar teknik detay değil, “ne değişti + kullanıcıya faydası” odaklı olmalı.

## Commit & PR
- Commit mesajları: kısa, emir kipinde (örn. “Add relay polarity check”).
- PR açıklaması: ne değişti + nasıl doğruladın (komutlar) + donanım varsayımları.
