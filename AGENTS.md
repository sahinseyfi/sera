# Repository Guidelines — AKILLI SERA (Momo & Nova Station)

Bu repo Raspberry Pi üzerinde çalışan bir sera kontrol panelidir. Kod, fiziksel donanımı (röle/pompa/ısıtıcı/fan) kontrol edebildiği için öncelik her zaman **güvenlik**tir.

## Amaç (bu dosya ne işe yarar?)
- Codex/agent’in bu repoda **tutarlı**, **güvenli** ve **izlenebilir** şekilde ilerlemesini sağlar.
- Pratik referanslar: `docs/RUNBOOK.md`, `docs/CHECKLISTS.md`, `AGENT_ASSUMPTIONS.md`, `scripts/doctor.py`.

## Altın Kurallar (ZORUNLU)
- Varsayılan hedef: **tüm aktüatörler OFF**; belirsizlikte “güvenli tarafta kal”.
- Donanım riski olan işlerde varsayılan rota: **`SIMULATION_MODE=1` ile doğrula**, sonra kontrollü donanım testi.
- Pompa/ısıtıcı gibi kritik aktüatörler: sadece **süre-limitli** ve kısa testlerle.
- Riskli komutlar (`sudo`, `systemctl`, GPIO/I2C araçları): önce **etki + geri dönüş** planı yaz; açık istek yoksa çalıştırma.
- Donanım test scriptleri (`sera_panel/relay_*.sh`, kökteki `*_test.py`) **otomatik çalıştırılmaz**; ancak kullanıcı açıkça isterse ve güvenlik koşulları sağlanırsa.
- Belirsizlik varsa (özellikle donanım davranışı): donanım etkileyen adımları **erteleyip** varsayımı `AGENT_ASSUMPTIONS.md`’ye **`pending`** olarak ekle; yazılım tarafında güvenli/geri alınabilir işlerle ilerle.

## Risk Seviyesi (agent karar verme rehberi)
- Düşük risk: UI metinleri, rapor kartları, statik sayfalar, dokümantasyon.
  - Minimum: `make test` (gerekliyse) + hızlı smoke önerisi.
- Orta risk: API şeması/JSON payload değişiklikleri, otomasyon mantığı, loglama/veri dönüşümü.
  - Minimum: `make doctor` (config dokunulduysa) + `make test` + geriye uyum notu.
- Yüksek risk: GPIO/mapping, aktüatör kontrolü, güvenlik limitleri, systemd/servis akışı.
  - Minimum: `make doctor` + `make test` + rollback planı + donanımda SAFE MODE ile kontrollü doğrulama adımları.

## Hızlı Başlangıç (geliştirme)
- Sanal ortam: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  - Not: Repoda `venv/` veya `sera-venv/` görülebilir; **tek bir venv** seçip onu kullanmak en temizi.
  - Not (PEP 668): Sistem Python’ına `pip install` çalışmayabilir; her zaman venv (veya `make install`) kullan.
- Tek komut akışı (önerilen):
  - Kurulum: `make install`
  - Konfig kontrol: `make doctor`
  - Test: `make test`
  - Simülasyon çalıştır: `make run-sim`
- Panel (gerçek donanım): `python3 app.py` (LAN: `http://<pi-ip>:5000`)
- Alternatif launcher: `python3 sera_panel/app.py` (kök `app.py`’yi import eder; `0.0.0.0:5000`)

## Proje Yapısı (nerede ne var?)
- `app.py`: Ana Flask uygulaması (API + otomasyon + GPIO katmanı)
- `templates/`, `static/`: Arayüz dosyaları
- `config/`: Çalışma zamanı ayarları (**tek kaynak**)
  - `config/channels.json`: Kanal ↔ GPIO eşlemesi (active-low/active-high)
  - `config/sensors.json`: Sensör/LCD ayarları (I2C adresleri dahil)
  - `config/reporting.json`: Raporlama/bitki profil eşikleri
  - `config/panel.json`: Panel ayarları (limitler + otomasyon + uyarı eşikleri)
  - `config/notifications.json`: Bildirim ayarları (token içermez; token env var ile)
  - `config/retention.json`: Veri saklama/temizlik ayarları
  - `config/updates.json`: Panelde görünen “Güncellemeler” listesi
  - `config/schema/`: JSON Schema doğrulamaları
- `scripts/doctor.py`: Config + şema doğrulama (CI öncesi hızlı kontrol)
- `tests/`: `pytest` ile çalışan otomatik testler (SIMULATION_MODE ile)
  - Not: Repo kökündeki `*_test.py` dosyaları çoğunlukla **donanım deneme scriptleri**; `pytest.ini` bunları test olarak toplamaz.
- `data/`: Üretilen veriler (SQLite + CSV loglar); git’e dahil edilmez
- `sera_panel/`: Legacy/launcher + röle test scriptleri (`relay_*.sh`) + donanım checklist’i (`sera_panel/AGENTS.md`)
- `Serav1/`: Yeni panel / multi-zone plan dokümanları
- `docs/`: Çalışma rehberi ve checklist’ler (`docs/RUNBOOK.md`, `docs/CHECKLISTS.md`)
- `systemd/`: Servis örnekleri (`systemd/sera-panel.service`, `systemd/sera-panel.env.example`)

## Doğrulama Protokolü (hızlı)
- Config değiştiyse: `make doctor` (gerekirse `python3 scripts/doctor.py --strict`)
- Yeni/değişen config alanı eklediysen: ilgili `config/schema/*.schema.json` ve gerekirse `scripts/doctor.py` güncellenir.
- Kod değiştiyse: `make test`
- Test çalıştırırken `pytest` yerine `make test` veya `pytest -q tests` kullan (repo kökünde donanım deneme scriptleri var).
- Yeni test ekleyeceksen: `tests/test_*.py` altına ekle ve simülasyon ortam değişkenleriyle koşacak şekilde yaz.
- Kullanıcıya görünen değişiklikse: `config/updates.json` içine “ne değişti + faydası” notu ekle.

## Konfig Kuralları (config/*.json)
- Değişiklikten sonra `make doctor` zorunlu (şema + temel tutarlılık kontrolleri).
- `config/channels.json`:
  - `name`, `gpio_pin`, `active_low` zorunlu; `name` ve `gpio_pin` benzersiz olmalı.
  - Röle polaritesi belirsizse `sera_panel/AGENTS.md` + `sera_panel/relay_polarity_test.sh` akışını takip et (yükleri güvene al).
  - Mapping/polarity değişikliklerinde donanımda SAFE MODE ile başla; ilk aksiyon “tüm kanalları OFF doğrula” olmalı.
- `config/sensors.json`:
  - I2C adresleri `"0x.."` formatında string olmalı (BH1750/ADS1115/LCD).
  - LCD satır sayısı ile `lcd_lines` uyumlu olmalı (`lcd_rows` kadar satır).
- `config/panel.json`:
  - `limits`, `automation`, `alerts` alanları object olmalı; sadece bu dosya üzerinden kalıcılık beklenir.
  - Yeni alan eklersen: `config/schema/panel.schema.json` ve `scripts/doctor.py` güncelle.
- `config/notifications.json`:
  - Token/chat_id içermez; sadece davranış ayarlarıdır (tokenlar env var).
  - Simülasyonda varsayılan: bildirim gönderme kapalı (`allow_simulation=false`).
- `config/retention.json`:
  - `*_days` alanları `0` ise silme yapılmaz; `archive_enabled` açıkken `archive_dir` repo altında olmalı.
- `config/updates.json`:
  - `date` ISO formatında olmalı (`YYYY-MM-DD`); `details` sadece string listesi olmalı.

## Güvenlik İnvaryantları (kırma)
- SAFE MODE varsayılanı: başlangıçta **açık** olmalı (manual kontrol kilitli).
- SAFE MODE açıkken: manuel aktüatör komutları engellenmeli; sadece `emergency_stop` ile “hemen OFF” her zaman çalışmalı.
- `emergency_stop`: her zaman tüm kanalları OFF’a çekebilmeli.
- Pompa/ısıtıcı: süre limitleri + cooldown’lar devre dışı bırakılamamalı (yüksek risk).
- Pin/mapping kaydı değişince: sistem güvenlik için tüm kanalları OFF’a çekmeli (ve UI bunu açıkça belirtmeli).
- Yeni background loop/thread ekleniyorsa: `DISABLE_BACKGROUND_LOOPS=1` ile devre dışı kalmalı; testlerde çalışmamalı.
- Bu davranışları değiştiriyorsan: `tests/` altında test ekle/güncelle ve `make test` ile doğrula.

## Diff Hijyeni (gözden geçirmeyi kolaylaştır)
- İlgisiz reformat/refactor yapma (özellikle JSON’larda “sadece format” değişikliği üretme).
- Config değişikliklerinde mümkünse **minimal satır farkı** hedefle; `make doctor` ile doğrula.

## Kullanıcıya Görünen Güncellemeler (updates)
- UI davranışı değiştiyse, yeni sayfa/akış eklendiyse veya “kullanıcı ne kazandı?” netse `config/updates.json` kaydı ekle.
- Kayıt dili: teknik detay değil; kısa fayda + 2–4 madde “ne değişti”.

## Codex/Agent Çalışma Akışı (standart)
1) Hedefi netleştir + donanım riskini sınıflandır (UI/rapor düşük; GPIO/aktüatör yüksek).
2) Planı kısa adımlara böl ve her adımda doğrulama komutu yaz.
3) Yeni bir varsayım gerekiyorsa `AGENT_ASSUMPTIONS.md` içine **`pending`** olarak ekle; donanım etkileyen varsayımlarda kullanıcı onayı olmadan ilerleme.
4) Minimal ve izlenebilir diff yap; config değişikliklerinde `scripts/doctor.py` ile doğrula.
5) İş bitince: nasıl doğruladığını (komutlar) tek satırda özetle.

## Yanıt/Plan Formatı (kullanıcı dostu)
- Riskli işlerde cevap formatı: **Amaç → Risk → Plan → Doğrulama → Rollback**.
- Rollback örnekleri: `config/` değişikliği geri alma, SAFE MODE ile başlama, `emergency_stop` kontrolü, servis revert adımı.
- Varsayım gerekiyorsa: soruya boğmadan `AGENT_ASSUMPTIONS.md`’ye **`pending`** ekle; donanım etkileyen varsayımlarda kullanıcı onayı olmadan davranış değiştirme.

## Varsayımlar (Assumptions Ledger)
- Kaynak: `AGENT_ASSUMPTIONS.md`
- Durumlar: `pending` (onay bekliyor) → `confirmed` → `deprecated` (silme yok; iz bırak).
- Varsayım gerekiyorsa “neden gerekli + nasıl doğrulanır” alanlarını doldur.

## Serav1 Doküman Akışı (yeniden tasarım)
- Uygulama/UX büyük değişikliklerinde önce `Serav1/` altındaki spec’leri oku (özellikle `Serav1/panel-redesign-spec.md` ve `Serav1/current-state-reference.md`).
- Yeni karar alındığında veya karar değiştiğinde `Serav1/decision-log.md` güncellenir (kısa ve stabil tut).

## Konfigürasyon & Secrets
- Mapping/sensör ayarlarını `config/*.json` içinde tut; koda sabitleme yapma.
- `ADMIN_TOKEN` gibi değerleri env var olarak kullan; repoya secret ekleme (`.env.example` sadece örnektir).
- Donanım davranışı değişiyorsa (GPIO/I2C/pin): ilgili dokümanda net belirt (`docs/` veya README).
- Repo içinde token/anahtar saklama: **yapma**. Yanlışlıkla eklenmiş secret görürsen ilgili dosyayı kaldır/ignore et ve kullanıcıya tokenları döndürmesi/yenilemesi gerektiğini söyle.

## Talimat Bakımı (kendi kendini güncel tutma)
- Agent talimatları kalıcı olarak otomatik değiştirmez; ihtiyaç görünce küçük bir patch önerir.
- Yeni klasör/komut/env var eklendiğinde, tekrarlayan hata/yanlış anlaşılma olduğunda veya güvenlik davranışı değiştiğinde bu dosyaya ve ilgili dokümana güncelleme öner.
- Güncelleme önerisi formatı: (1) problem (2) önerilen metin (3) nasıl doğruladım (4) risk/geri dönüş.

## Commit & PR
- Commit mesajları: kısa, emir kipinde (örn. “Add relay polarity check”).
- PR açıklaması: ne değişti + nasıl doğruladın (komutlar) + donanım varsayımları.
