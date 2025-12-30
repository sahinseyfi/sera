# Agent Varsayımları (Assumptions Ledger)

Bu dosya, Codex/agent'in çalışırken dayandığı varsayımları şeffaf şekilde tutar.
Amaç: yanlış varsayımları erken yakalamak ve donanım güvenliğini korumak.

## Kullanım
- Yeni bir varsayım gerekiyorsa, aşağıdaki tabloya **`pending`** olarak ekle (ID artır).
- Donanım davranışını etkileyebilecek varsayımlarda kullanıcı onayı gelmeden ilerleme.
- Onaylanan varsayımlar **`confirmed`**, geçersizleşenler **`deprecated`** olur (silme yok; iz bırak).

## Varsayımlar

| ID | Durum | Varsayım | Kanıt/Kaynak | Doğrulama (nasıl kontrol edilir?) | Not |
|---|---|---|---|---|---|
| A001 | confirmed | `gpio_pin` değerleri aksi belirtilmedikçe **BCM** numarasıdır. | `sera_panel/AGENTS.md` | Raspberry Pi üzerinde pin doğrulaması gerekiyorsa `raspi-gpio get <bcm>` ile kontrol. |  |
| A002 | confirmed | Kanal/sensör ayarlarının tek güncel kaynağı `config/*.json` dosyalarıdır. | `AGENTS.md`, `sera_panel/AGENTS.md` | `scripts/doctor.py` + uygulama davranışı ile doğrula. |  |
| A003 | confirmed | Varsayılan hedef: aktüatörler OFF ve SAFE MODE başlangıçta açıktır. | `README.md`, `tests/test_api.py` | `SIMULATION_MODE=1` ile `/api/status` kontrolü. |  |
| A004 | confirmed | Bildirim ayarları `config/notifications.json` içindedir; Telegram token/chat id **env var** ile verilir (config içine yazılmaz). | `app.py`, `.env.example` | `/api/status` → `notifications.runtime.telegram_configured` ve `notifications.config` kontrolü. |  |
| A005 | confirmed | Varsayılan veri saklama politikası silme yapmaz: `*_days=0` ve arşiv kapalıdır. | `config/retention.json`, `app.py` | `/api/status` → `retention.config` kontrolü; `make doctor`. |  |
| A006 | confirmed | Panel ayarlarının kalıcılık kaynağı `config/panel.json` dosyasıdır (`limits`, `automation`, `alerts`). | `app.py` | Ayarlar sayfasından değiştir → `config/panel.json` güncelleniyor mu kontrol et. |  |
