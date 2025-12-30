# AKILLI SERA — Panel UX / IA Planı (Mobil Öncelikli)

Bu doküman; mevcut panelin **kullanıcı dostu** ve **mobil uyumlu** olması için sayfa bazında “ne nerede olmalı?” planını tutar.
Amaç: geliştirme sırasında rastgele UI eklemek yerine tutarlı bir bilgi mimarisi (IA) ve ortak etkileşim desenleriyle ilerlemek.

## Tasarım Hedefleri
- **Mobil‑öncelik**: En kritik işler (izleme, acil durdurma, güvenli manuel kontrol) telefonda rahat yapılabilmeli.
- **Güvenlik‑öncelik**: “Yanlışlıkla dokunma” ve “yanlış modda çalışma” riskini minimize et.
- **Tek ekranda tek hedef**: Her sayfanın “birincil” amacı ve 1 adet ana aksiyonu net olsun.
- **Tutarlılık**: Başlık, durum banner’ı, aksiyon butonlarının yeri ve metin dili her sayfada benzer.
- **Anlaşılabilirlik**: Durumlar sadece renk ile değil metin ile de anlaşılmalı.

## Kullanıcı Rolleri (zihinsel model)
- **İzleyici**: SAFE MODE açık; sadece izler, rapor okur, loglara bakar.
- **Operatör**: SAFE MODE kapalı; kontrollü manuel komut verir (pompa süreli vb.).
- **Admin**: Config/ayar/pin mapping yazma yetkisi (ADMIN_TOKEN veya LAN).

## Global Bileşenler (tüm sayfalar)
### 1) Üst Bar (navbar)
Sağ üstte her zaman görünür:
- **SAFE MODE rozeti** (aktif/pasif)
- **Bağlantı durumu** (OK / Kesildi)
- **Veri gecikmesi** (sn)

Mobilde:
- Menü hamburger ile açılır.
- “Kontrol” ve “Ayarlar” linkleri menünün en üstünde olmalı.

### 2) Durum Banner’ı (sayfa içi)
Her sayfada (header altı):
- SAFE MODE açık/kapalı açıklaması
- Admin/Yetki hatası varsa “ne yapmalıyım?” yönlendirmesi
- Sensör stale/lock varsa sebep (örn. “Pompa kilitli: toprak sensörü hatası”)

### 3) Aksiyon Konumu Kuralı
- Desktop: sayfa header’ında sağ üst “aksiyon grubu”.
- Mobil: aynı aksiyonlar sayfanın üstünde kalabilir ama **kritik butonlar** (Kaydet, Acil Durdur) için opsiyonel **sticky** aksiyon barı planlanır.

### 4) Güvenlik Onay Desenleri
Yüksek risk aksiyonlar (acil durdurma, log silme, retention temizliği, mapping kaydı) için:
- “YES yaz” veya net bir onay
- Aksiyon sonrası “ne oldu?” mesajı
- Mümkünse geri dönüş (rollback) yönlendirmesi

## Navigasyon / Bilgi Mimarisi
### Ana Sekmeler (sık kullanım)
1. **Dashboard** (varsayılan giriş)
2. **Kontrol**
3. **Ayarlar**
4. **Loglar**

### İleri / Yönetim (seyrek kullanım)
- Donanım (mapping + sensör config)
- LCD
- Raporlar
- Güncellemeler
- Yardım/SSS
- Notlar (roadmap)

## Sayfa Bazında Plan

### 1) Dashboard — İzleme
**Amaç**: “Sistem şu an sağlıklı mı?” sorusuna 5 saniyede cevap.

**Üstte (hero)**:
- Otomasyon durumu rozeti (Açık/Kapalı + kısa özet)
- (Opsiyonel) “Kontrol” ve “Ayarlar” kısayol butonları (mobilde tek satır)

**Bölümler (sıra)**:
1. **Kritik durum banner’ı**: stale, lock, alarm özetleri
2. **Otomasyon Durumu kartı**: hedef/override/blok/min‑off ve son sebep
3. **Sensör kartları** (DHT/DS/Lux/Soil): her kartta
   - okuma değeri + durum rozeti (OK/SIM/HATA/YOK)
   - (varsa) kısa ortalamalar
4. **Grafik**:
   - metrik seçimi + aralık (24h/7d) + CSV
   - mobilde chart yüksekliği azalt
5. **Aktüatör Durumu**:
   - sadece durum (Açık/Kapalı), cooldown bilgisi
6. **Uyarılar**:
   - son 10–20 uyarı; severity renk + metin
7. **Enerji Tahmini**:
   - mobilde “özet + detay açılır” (collapsible) önerilir
8. **Sensör Sağlığı**
9. **Olay Günlüğü** (son 20–50)

**Butonlar**
- (Opsiyonel) “Yenile” (genelde otomatik)
- “CSV” (grafik için)
- “Kontrol” kısayolu (mobilde önemli)

**Empty/Fail**
- API erişilemiyorsa: bağlantı banner’ı + “yeniden dene”

---

### 2) Kontrol — Güvenli Manuel Kontrol
**Amaç**: Yanlışlıkla çalıştırmadan, doğru röleyi kısa/limitli çalıştırmak.

**Üstte (hero)**:
- “Yenile”
- **Acil Durdur** (tek bir kırmızı CTA; onaylı)
- SAFE MODE açıkken: “Kontrol kilitli” banner + “Ayarlar’a git” linki

**Aktüatör kartı standardı**
- Başlık: açıklama + kanal adı (küçük)
- Durum: Açık/Kapalı + süre sayacı (varsa)
- Uyarı satırı: pump cooldown, heater lock vb.
- Aksiyonlar:
  - **Aç** / **Kapat**
  - Pompa için: “Süreli çalıştır” (sn input + buton)
  - Isıtıcı için: süreli açma + max notu

**Mobil**
- Kartlar tek sütun
- Aksiyon butonları tam genişlik (touch target)
- Acil Durdur için yanlış dokunmayı azaltacak onay deseni

---

### 3) Ayarlar — SAFE MODE, Limitler, Otomasyon, Bildirimler, Retention
**Amaç**: Sistem davranışını güvenli ve kalıcı biçimde yönetmek.

**Üstte**
- Admin token alanı (ilk ekran)
- Tek “Kaydet” (primary)

**Bölüm yapısı**
1. SAFE MODE (tek toggle)
2. Limitler (pompa/heater/enerji)
3. Uyarı eşikleri
4. Işık otomasyonu (genel)
5. Isıtıcı otomasyonu
6. Pompa otomasyonu + toprak kalibrasyon
7. Fan otomasyonu (nem + gece + periyodik)
8. Bildirimler (Telegram) + test mesajı
9. Veri saklama/temizlik (0 gün = kapalı) + “şimdi çalıştır” (onaylı)

**Mobil**
- Bölümler arası hızlı gezinme için “Bölüme git” dropdown/TOC önerilir.
- Kaydet butonu uzun sayfada kaybolmamalı (sticky opsiyonu).

---

### 4) Donanım — Mapping + Sensör config (ileri seviye)
**Amaç**: Kanal tanımları ve sensör parametrelerini yönetmek (admin).

**Üstte**
- Yenile / Ekle / Kaydet
- Kaydet sonrası “tüm kanallar OFF” uyarısı her zaman görünür

**Mobil**
- Tablo yerine kart listesi (her kanal bir kart: ad, gpio, role, active_low, enabled)
- “Detay” açılır (W/volt/notes)

**Güvenlik**
- Kaydet onayı: “YES yaz” (yüksek risk)
- Kaydet sonrası otomatik OFF davranışı + ekranda net mesaj

---

### 5) Loglar — Sensör kayıtları
**Amaç**: “Ne oldu?” sorusuna geçmiş veriden cevap.

**Üstte**
- Zaman aralığı + limit + aralık (downsample)
- Yenile / CSV indir
- Log temizle (admin, “YES yaz”)

**Mobil**
- Filtreler tek sütun (stack)
- Tablo yatay kaydırma yerine “satır kartı” opsiyonu (ileride)

---

### 6) LCD — Önizleme ve şablon
**Amaç**: LCD’de ne görüneceğini güvenli biçimde ayarlamak.

**Üstte**
- Yenile / Kaydet

**Orta**
- Ayarlar (enabled/mode/addr/cols/rows)
- Satırlar (4 input) + token kısayolları + önizleme

**Mobil**
- Token butonları çoksa “kategori/arama” opsiyonu (ileride)

---

### 7) Raporlar — Günlük / Haftalık
**Amaç**: Yorumlanmış özet + trend.

**Üstte**
- Acemi modu toggle (varsayılan açık)
- CSV
- Günlük ↔ Haftalık geçiş butonu

**Mobil**
- Uzun metinler collapsible
- Chartlar tek sütun

---

### 8) Güncellemeler
**Amaç**: Kullanıcı dilinde “ne değişti?”.
- Liste kartları; en son en üstte.

---

### 9) Yardım / SSS
**Amaç**: “Bu ne demek?” sorularını azaltmak.
- Accordion iyi; her sayfadan anchor link ile ulaşılmalı.

---

### 10) Notlar
**Amaç**: Ürün backlog’u kullanıcı dilinde görünür tutmak (seyrek).

## Uygulama Önceliklendirmesi (öneri)
1) Mobilde aksiyonların erişilebilirliği (Kontrol + Ayarlar)  
2) Yüksek risk butonlara onay (Acil Durdur / retention / mapping)  
3) Donanım & Loglar için mobil görünüm sadeleştirme  
4) Dashboard yoğunluk azaltma (collapsible “detay” kartları)  

