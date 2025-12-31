# Repository Guidelines — AKILLI SERA (Momo & Nova Station)

Bu repo Raspberry Pi üzerinde çalışan bir sera kontrol panelidir. Kod, fiziksel donanımı (röle/pompa/ısıtıcı/fan) kontrol edebildiği için öncelik her zaman **güvenlik**tir.

## Amaç (bu dosya ne işe yarar?)
- Codex/agent’in bu repoda **tutarlı**, **güvenli** ve **izlenebilir** şekilde ilerlemesini sağlar.
- Pratik referanslar: `docs/RUNBOOK.md`, `docs/CHECKLISTS.md`, `AGENT_ASSUMPTIONS.md`, `scripts/doctor.py`.
- İletişim: Kullanıcıyla yazışırken Türkçe yanıtla.

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
  - Serav1 backend/refactor (çoklu zone, node komut/ACK): yüksek risk; SAFE MODE/ACK/TTL yollarını bozma, simülasyonla doğrula.

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

## Sonraki Adımlar Takibi
- Sonraki adım önerileri `docs/NEXT_STEPS.md` dosyasında tutulur.
- Her çalışmada bu dosyayı kontrol et; tamamlananları `[x]` ile işaretle, yeni önerileri ekle.
- Yanıtlarda uzun öneri listesi yerine bu dosyaya kısa referans ver.

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

## Serav1 Sprint Planı (yaşayan liste)
- Bu bölüm Serav1 teslimine giden sprintleri içerir; her sprintte `durum` alanını güncelle ve kapsam genişlediğinde ilgili sprinti **genişletip** bu dosyada kaydet (kısa not + tarih).
- Durum etiketleri: `planned`, `in_progress`, `blocked`, `done`.
- Tamamlanan sprintler silinmez; tarihli not ile kapatılır.

### Sprint 00 — Envanter ve Risk Haritası (durum: done)
- Kapsam: tek-zon bağımlılıkları envanteri (`app.py`, `templates/`, `static/`), güvenlik/risk noktaları listesi, Serav1 kapsamının netleştirilmesi.
- Çıktılar: envanter listesi + risk matrisi (doküman), Serav1 için kesin kapsam onayı.
- Doğrulama: yeni dokümanlara kısa çapraz referans, değişiklik yoksa test koşulmaz.
- Not (2025-12-30): Envanter tamamlandı, çıktı `Serav1/sprint-00-inventory.md`.

### Sprint 01 — Katalog ve Migrasyon Altyapısı (durum: done)
- Kapsam: `config/catalog.json` şeması, `scripts/migrate_catalog.py`, `scripts/doctor.py` güncellemesi, eski config uyumluluğu.
- Çıktılar: katalog şeması + dry-run migrasyon raporu + geriye uyum notu.
- Doğrulama: `make doctor`, `python3 scripts/migrate_catalog.py --dry-run`, `make test` (SIMULATION_MODE=1).
- Not (2025-12-30): `config/schema/catalog.schema.json`, `scripts/migrate_catalog.py` ve `scripts/doctor.py` katalog doğrulaması eklendi.

### Sprint 02 — Telemetri Depolama ve Node Protokolü (durum: done)
- Kapsam: telemetri tablosu (metric/key-value), `/api/telemetry` + `/api/node_commands`, ACK/TTL/backoff, node auth.
- Çıktılar: yeni DB şeması + API uçları + event log kayıtları + unit testler.
- Doğrulama: `pytest -q tests` (SIMULATION_MODE=1).
- Not (2025-12-30): Telemetry tablosu ve node API uçları eklendi; test komutu pytest eksik olduğu için çalıştırılamadı.

### Sprint 03 — Zone-First Model ve API Uyumluluğu (durum: done)
- Kapsam: iç model (zones/sensors/actuators), `/api/status` çift şema, eski alanların `deprecated` işaretlenmesi.
- Çıktılar: uyumlu API yanıtları + mapping katmanı + deprecation notları.
- Doğrulama: `make test`, örnek JSON snapshot kıyaslaması.
- Not (2025-12-30): `/api/status` zone-first alanları eklendi (zones/sensors/actuators/nodes + catalog meta), deprecation alanı eklendi; testler pytest eksik olduğu için çalıştırılamadı.

### Sprint 04 — Otomasyon ve Güvenlik Refaktörü (durum: done)
- Kapsam: zone bazlı otomasyonlar (heater/pump/fan/lux), SAFE MODE/ACK/TTL, bağımlılıklar ve cooldown.
- Çıktılar: yeni otomasyon akışı + güvenlik testleri + fail-safe davranışları.
- Doğrulama: `pytest -q tests` (SIMULATION_MODE=1), SAFE MODE senaryoları.
- Not (2025-12-30): Otomasyon ON aksiyonları güvenlik politikasına bağlandı (max_on_s/cooldown_s + fan dependency), per-aktüatör cooldown takibi + max_daily_s günlük limitleri + role bazlı pump/heater güvenlik kontrolleri + pump günlük kullanımını actuator_log ile takip eden cache + node_commands POST kuyruklama ve default `since` penceresi + SAFE MODE/E-STOP blokajı + `/api/actuator` PWM komutlarının ESP32 kuyruğuna yönlenmesi + `emergency_stop` ile ESP32 off kuyruklama + node health (`last_seen`/stale) snapshot + ESP32 ACK ile remote actuator state takibi + remote sensor snapshot + `sensor_health` içine remote sensor’lar + catalog sensor `backend` şema alanı + node_commands rate limit + README API/env güncellemesi + `/api/nodes` ve queue_size snapshot + SAFE MODE'da node kuyruk temizleme + updates.json kaydı eklendi.
- Not (2025-12-31): Node rate limit test izolasyonu için test fixture eklendi, SAFE MODE açıkken node_commands GET testinde safe_mode kapatma eklendi; `make test` başarıyla koştu.
- Not (2025-12-31): `datetime.utcnow()` kullanımları timezone-aware hale getirildi; testlerdeki DeprecationWarning temizlendi.

### Sprint 05 — Yeni UI: Overview/Zones/Control (durum: in_progress)
- Kapsam: zone-first sayfalar, `USE_NEW_UI` bayrağı, kritik aksiyon onay akışları.
- Çıktılar: yeni template/JS, eski UI ile birlikte çalışma, erişilebilirlik kontrolleri.
- Doğrulama: SIMULATION_MODE ile manuel smoke + hızlı performans kontrolü.
- Not (2025-12-31): `USE_NEW_UI` bayrağı eklendi; Overview/Zones sayfaları ve Serav1 tabanlı navigasyon iskeleti hazırlandı, Control sayfası yeni şablona taşındı.
- Not (2025-12-31): Control sayfası zone-first kart yapısına geçirildi; ESP32 PWM slider eklendi ve pompa/ısıtıcı için ek onay akışı devreye alındı.
- Not (2025-12-31): Control kartlarına otomasyon durumu (override/blok) özeti eklendi.
- Not (2025-12-31): Control kartlarına override iptal aksiyonu eklendi (otomasyon yeniden devreye alınabilir).
- Not (2025-12-31): Zones kartlarına aktif aktüatör ve son aksiyon özeti eklendi.
- Not (2025-12-31): ESP32 aktüatör kartlarında node sağlık durumu (status + yaş) gösteriliyor.
- Not (2025-12-31): Control banner’a node uyarıları eklendi (missing/unknown).
- Not (2025-12-31): Overview otomasyon özeti (lux/fan/ısıtıcı/pompa) eklendi.
- Not (2025-12-31): Overview node sağlık rozetleri (OK/missing/error/unknown) eklendi.
- Not (2025-12-31): Overview node rozetleri tıklanınca liste filtrelenir.
- Not (2025-12-31): Overview node listesine Tümü filtresi eklendi.
- Not (2025-12-31): Overview node listesinde son IP bilgisi gösteriliyor.
- Not (2025-12-31): Overview node listesinde firmware bilgisi gösteriliyor.
- Not (2025-12-31): Overview node listesinde son snapshot zamanı gösteriliyor.
- Not (2025-12-31): Overview node listesinde kamera desteği (kamera) gösteriliyor.
- Not (2025-12-31): Overview node rozetlerine kamera filtresi eklendi.
- Not (2025-12-31): Zones kartlarına mini trend (son 6 saat) eklendi.
- Not (2025-12-31): `/api/trends` için `max_points` parametresi ve sunucu tarafı downsample eklendi; zone mini trend istekleri bu sınırı kullanıyor.
- Not (2025-12-31): Control sayfası zone başlıklarına sensör özeti (sıcaklık/nem/lux/toprak) ve sensör durum rozeti eklendi.
- Not (2025-12-31): History/Loglar sayfası Serav1 görünümüne taşındı.
- Not (2025-12-31): History/Loglar sayfasına trend grafiği eklendi.
- Not (2025-12-31): History/Loglar sayfasına olay günlüğü eklendi.
- Not (2025-12-31): History trendleri zone seçimiyle telemetri verisinden okunuyor ve CSV export destekleniyor.
- Not (2025-12-31): History olay günlüğüne kategori/seviye filtreleri eklendi.
- Not (2025-12-31): Ayarlar sayfası Serav1 base layout ile çalışıyor; tooltip stili Serav1 temaya taşındı.
- Not (2025-12-31): Ayarlar sayfasına özet kartı eklendi (SAFE MODE/otomasyon/bildirim/retention/pompa kullanım).
- Not (2025-12-31): Overview sayfasına son 24 saat özet kartı eklendi.
- Not (2025-12-31): Overview özet kartında veri kaynağı (telemetri/log) gösteriliyor.
- Not (2025-12-31): Overview özet kartına 6s/24s/7g aralık seçici eklendi.
- Not (2025-12-31): History olay günlüğüne zaman aralığı filtresi eklendi.
- Not (2025-12-31): Overview özet kartına zone seçici eklendi.
- Not (2025-12-31): Overview özet kartına CSV indirme eklendi.
- Not (2025-12-31): History grafiğine min/max/son rozetleri eklendi.
- Not (2025-12-31): Ayarlar sayfası bölüm başlıkları Serav1 diliyle sadeleştirildi.
- Not (2025-12-31): Günlük/Haftalık rapor sayfaları Serav1 base layout ile çalışıyor.
- Not (2025-12-31): Donanım/LCD/Notlar sayfaları Serav1 base layout ile çalışıyor.
- Not (2025-12-31): Serav1 navigasyona Diger menusu eklendi (raporlar/yardim/guncellemeler/donanim/LCD/notlar).
- Not (2025-12-31): Yardım/SSS metinleri Serav1 sayfa adlarıyla uyumlu hale getirildi.
- Not (2025-12-31): Serav1 icin Diger sayfasi eklendi (ek sayfalara hizli erisim).
- Not (2025-12-31): Diger sayfasi metinleri Turkce hale getirildi.
- Not (2025-12-31): Serav1/current-state-reference dokumani Serav1 beta UI ozetini iceriyor.
- Not (2025-12-31): Serav1 mobil tabbar sadelestirildi; Ayarlar Diger sayfasina alindi.
- Not (2025-12-31): History sayfasina rapor kisa yollari eklendi.
- Not (2025-12-31): Mobilde Diger sekmesi alt sayfalarda da aktif vurgulanir.
- Not (2025-12-31): Zones sayfasi aciklamasi History'deki trend/olaylar ile netlestirildi.
- Not (2025-12-31): Serav1 nav kararlari panel-redesign-spec ve decision-log icine islendi.
- Not (2025-12-31): Yardim/SSS metinleri History/Donanim adlariyla uyumlu hale getirildi.
- Not (2025-12-31): README'de USE_NEW_UI aciklamasi Serav1 sayfalarini kapsayacak sekilde guncellendi.
- Not (2025-12-31): Raporlarda History kisa yolu eklendi.
- Not (2025-12-31): Diger menusundeki Notlar etiketi Turkcelestirildi.
- Not (2025-12-31): Serav1 menu etiketleri Turkcelestirildi (Genel Bakis/Zoneler/Kontrol/Gecmis/Ayarlar/Diger/Yardim).
- Not (2025-12-31): Overview/Zoneler metinleri Turkcelestirildi (Katalog/Veri Yasi/Zon odakli).
- Not (2025-12-31): Zon secimleri icin erisilebilirlik etiketleri eklendi.
- Not (2025-12-31): Sayfa basliklarindaki Serav1 etiketi kaldirildi.
- Not (2025-12-31): Gecmis sayfasinda log ifadesi kayit olarak sadelestirildi.
- Not (2025-12-31): Olay gunlugu etiketleri Turkcelestirildi.
- Not (2025-12-31): Serav1 dokumanlari Turkce terminolojiye guncellendi (Genel Bakis/Zoneler/Geçmiş/Kayit).
- Not (2025-12-31): Zon kartlarinda varsayilan baslik metni Turkcelestirildi.
- Not (2025-12-31): Serav1 panel-redesign-spec basliklari Turkcelestirildi.
- Not (2025-12-31): Yardım ve Güncellemeler sayfaları Serav1 base layout ile çalışıyor.
- Not (2025-12-31): Node durum rozetlerindeki Missing/Error/Unknown etiketleri Turkcelestirildi.
- Not (2025-12-31): Geçmiş tablosundaki Soil sütunları Toprak olarak adlandırıldı.
- Not (2025-12-31): Node filtre rozetleri klavye ile secilebilir hale getirildi.
- Not (2025-12-31): Genel Bakış özetindeki Log etiketi Kayıt olarak guncellendi.
- Not (2025-12-31): Yardım metinlerinde log ifadeleri kayıt terminolojisine uyarlandı.
- Not (2025-12-31): Özet ve Geçmiş aralık butonlarinda aria-pressed durumu eklendi.
- Not (2025-12-31): Kayıt temizleme onay metni log yerine kayıt terminolojisine uyarlandi.
- Not (2025-12-31): Node listesinde fw/snap etiketleri Turkcelestirildi.
- Not (2025-12-31): Override ifadeleri arayuzde Mudahale olarak guncellendi.
- Not (2025-12-31): Yardım sayfasındaki override ifadesi Mudahale olarak guncellendi.
- Not (2025-12-31): Katalog kaynagi etiketi Eski/Katalog olarak guncellendi.
- Not (2025-12-31): Veri gecikmesi ifadesi Veri yasi olarak guncellendi.
- Not (2025-12-31): Geçmiş tablosundaki Ts basligi Zaman olarak guncellendi.
- Not (2025-12-31): Ayarlar ozetinde Retention etiketi Veri Saklama olarak guncellendi.
- Not (2025-12-31): Veri Saklama alanlarinda log ifadeleri kayit olarak guncellendi.

### Sprint 06 — Settings: Sensors/Automation/LCD/Devices (durum: planned)
- Kapsam: sensör editörü, LDR/BH1750 kalibrasyon akışı, LCD template editor, cihaz/kanal mapping UI.
- Çıktılar: yeni ayar sayfaları + güvenli kayıt akışları (pin değişiminde OFF + SAFE MODE).
- Doğrulama: `make doctor`, SIMULATION_MODE ile form akış testi.

### Sprint 07 — History/Trends/Reports (durum: planned)
- Kapsam: yeni telemetri okuma, downsampling, CSV export, rapor güncellemeleri.
- Çıktılar: performanslı trend API + güncel raporlar + eski log uyumluluğu.
- Doğrulama: örnek veri ile grafik ve CSV doğrulama.

### Sprint 08 — Bildirimler ve Hava Durumu (durum: planned)
- Kapsam: location/weather ayarları, cache, Telegram/Email bildirimleri, quiet hours.
- Çıktılar: bildirim konfig ekranı + test send uçları + offline davranışları.
- Doğrulama: SIMULATION_MODE ile test send + env var doğrulama.

### Sprint 09 — Entegrasyonlar ve Kameralar (durum: planned)
- Kapsam: HA adapter, ESP32-CAM snapshot proxy, retention politikası.
- Çıktılar: entegrasyon durum ekranı + kamera uçları + veri saklama sınırları.
- Doğrulama: SIMULATION_MODE, sahte snapshot ile smoke test.

### Sprint 10 — Sertleştirme ve Yayın (durum: planned)
- Kapsam: performans optimizasyonu, diagnostics sayfası, deprecation kaldırma, rollback planı.
- Çıktılar: final dokümantasyon + versiyon notları + geçiş checklist’i.
- Doğrulama: `make doctor`, `make test`, SIMULATION_MODE end-to-end smoke.

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
