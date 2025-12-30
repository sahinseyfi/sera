# Donanım Envanteri (Mevcut) — Fiyatlı Liste

Bu dosya; elindeki ekipmanları **model/özellik + adet + fiyat** ile kayıt altına almak için oluşturuldu.
Fiyatlar, senin paylaştığın birim fiyatlardır (kargo/indirim değişebilir).

## Özet
- Kalem sayısı: 43 (14 kalemde fiyat eksik)
- Toplam tutar (fiyatı bilinenler): 6.389,16 TL

## 0) Kontrol Bilgisayarı

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| Raspberry Pi (ana kontrolcü) | Raspberry Pi 4 Model B (4GB) | USB‑C, 5V/3A resmi adaptör + orijinal güç kablosu | 1 | — | — | Panel bilgisayarı (fiyat bilgisi yok) |

## 1) Sensörler ve Ölçüm Modülleri

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| ADS1115 16‑Bit 4 Kanal ADC | ADS1115 | I2C, 4 analog kanal, 16‑bit | 1 | 113,14 | 113,14 | Analog sensör okumaları (toprak nem vb.); ESP32 düğümlerine “node başına ADC” olarak eklenebilir |
| DHT22 Dijital Sıcaklık/Nem Sensörü Modülü | DHT22 | Dijital temp/nem, modül | 1 | 87,71 | 87,71 | Yedek/legacy sensör; hedef ölçüm SHT31 |
| DS18B20 (Su Geçirmez) Dijital Isı Sensörü | A0244 | 1‑Wire, waterproof prob | 1 | 44,74 | 44,74 | Yedek/alternatif sıcaklık ölçümü |
| BH1750 Lux Sensörü Modülü | A0860 (GY‑302) | I2C lux sensörü | 1 | 89,48 | 89,48 | Referans lux (LDR kalibrasyonu için) |
| Kapasitif Toprak Nem Sensörü (Higrometre) | — | Analog çıkış | 3 | 31,57 | 94,71 | Kat1 + Kat2 + 1 yedek |

## 2) Aydınlatma (LED)

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 12V LED Bar Alüminyum Çubuk | 5730/5630, 72 LED, 6500K | 100cm, 72 LED/m, 1000–1800 lm, 12V, 1,4–2A (≈17–24W) | 4 | 51,21 | 204,84 | KAT1: 2 bar (tek PWM kanal), KAT2: 2 bar (tek PWM kanal) |
| LED Profil (1m) | PJ1094 | Şeffaf kapaklı profil | 4 | 55,48 | 221,92 | LED bar montaj/profil |

## 3) Fanlar ve Isıtma

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 12V Fan 120×120×25mm | FAN0050 (XMER) | 12V, 0,45A, 2P | 1 | 140,62 | 140,62 | Egzoz veya kat fanı (ihtiyaca göre) |
| PTC Isıtıcı Plaka | A0947 | 12V, max 110°C, 35×21×5mm, PTC (self‑regulating) | 1 | 149,14 | 149,14 | Fide kutusu içi ısıtma; watt/akım değeri netleşince sigorta+kablo kesinleşir |
| Elektrikli Isıtıcı Fan | Kiwi KHT 8415 | 1000W/2000W, termostat, devrilme emniyeti | 1 | 617,40 | 617,40 | Sera genel ısıtma (AC) |
| Akıllı WiFi Priz | Cata CT‑4010 | Uzaktan kontrol | 1 | 345,00 | 345,00 | Isıtıcıyı Home Assistant üzerinden sürmek için |

## 4) Güç ve Bağlantı

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 12V Adaptör (Masa Tip) | 12V 8.5A | 12V, 8.5A | 1 | 341,40 | 341,40 | LED + fan besleme (toplam akıma göre yeterlilik kontrol) |
| DC Barrel Dişi Güç Jakı | 2.5 mm | Dişi jack | 1 | 10,90 | 10,90 | Güç giriş/çıkış işleri |
| DC Barrel Dişi Güç Jakı | 2.1 mm | Dişi jack | 1 | 7,79 | 7,79 | Güç giriş/çıkış işleri |

## 5) Kontrol, Prototipleme ve Kablolama

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 2 Kanal 5V Röle Kartı | — | 5V röle kartı | 1 | 54,26 | 54,26 | KAT1/KAT2 canopy fan on/off için kullanılabilir (active‑low kontrolünü doğrula) |
| Büyük Breadboard | A0036 | 830 pin | 1 | 46,87 | 46,87 | Masa testi / prototipleme |
| Raspberry Pi Breadboard T‑Cobbler + 40 Pin Kablo | — | 40 pin breakout | 1 | 127,29 | 127,29 | Breadboard’da düzenli GPIO bağlantısı |
| Jumper Kablo Seti | 140 parça | Karışık jumper | 1 | 61,10 | 61,10 | Prototip bağlantılar |
| Jumper Kablo (Dişi‑Dişi) | 40 adet / 20cm | 20 cm | 1 | 25,46 | 25,46 | Prototip bağlantılar |
| Jumper Kablo (Dişi‑Erkek) | 40 adet / 20cm | 20 cm | 1 | 26,99 | 26,99 | Prototip bağlantılar |
| Jumper Kablo (Erkek‑Erkek) | 40 adet / 20cm | 20 cm | 1 | 28,51 | 28,51 | Prototip bağlantılar |
| Isıyla Daralan Makaron Seti | GüncelÇarşı | 530 adet, 8 boy, 5 renk; alev geciktirici | 1 | 241,37 | 241,37 | Kablo izolasyonu ve düzen |

## 6) Ekran (LCD)

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 20×4 LCD (I2C) | Lehimli, Mavi Display | 20 sütun, 4 satır, I2C backpack | 1 | 220,06 | 220,06 | Panel dışı hızlı durum göstergesi |

## 7) Pasifler (Direnç/LED)

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| Direnç Paketi | 1/4W 4.7kΩ (10 adet) | 0.25W | 1 | 2,08 | 2,08 | LDR/LED vb. prototipleme |
| Direnç Paketi | 1/4W 330Ω (10 adet) | 0.25W | 1 | 2,08 | 2,08 | LED akım sınırlama |
| 5mm Kırmızı LED | LED00001 (10 adet) | 5mm | 1 | 8,10 | 8,10 | Gösterge |
| 5mm Yeşil LED | LED00002 (10 adet) | 5mm | 1 | 8,10 | 8,10 | Gösterge |
| 5mm Sarı LED | LED00003 (10 adet) | 5mm | 1 | 8,10 | 8,10 | Gösterge |

## 8) Sera Gövdesi (Mekanik)

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| 4 Katlı Portatif Bahçe Serası | Gardener 16040 (Ürün Kodu: 61483255) | 69×49×158 cm, PVC kılıf, metal boru iskelet | 1 | 3.060,00 | 3.060,00 | Ana sera gövdesi |

## 9) Eski Projeden Kalanlar (Fiyat Bilinmiyor)

Bu bölüm, elinde olup fiyatı paylaşılmamış parçaları “kayıt altına almak” için var.

| Ürün | Model/Kod | Teknik detay | Adet | Birim (TL) | Toplam (TL) | Not / Kullanım |
|---|---|---:|---:|---:|---:|---|
| Mini DC diyaframlı sıvı pompası + DC motor | — | Muhtemelen 12V, diyafram pompa kafası (giriş/çıkış portlu) + fırçalı DC motor | 1 | — | — | Kablo/lehimi kopuk görünüyor; akım/debi test edilecek |
| Yan keski / pense | — | Kablo kesme/soyma, tutma için el aleti | 1 | — | — | Montaj/servis |
| 4×4 Matris Buton Takımı (Keypad) | — | 16 tuşlu, S1…S16, satır‑sütun okuma | 1 | — | — | Prototip kontrol arayüzleri |
| DC motor sürücü modülü | L298N | 2 kanallı H‑bridge, PWM ile hız, klemensli | 2 | — | — | Motor prototip; sera finalinde zorunlu değil |
| Röle kartı (8 kanal) | Tongling JQC‑3FF‑S‑Z | 12V bobin, IN1…IN8 girişli modül | 1 | — | — | Çoklu yük anahtarlama; lojik seviye/sürücü ihtiyacı kontrol edilmeli |
| Röle kartı (4 kanal) | Songle SRD‑12VDC‑SL‑C | 12V bobin, 4 kanal modül | 1 | — | — | Yük anahtarlama; lojik seviye/sürücü ihtiyacı kontrol edilmeli |
| Röle kartı (2 kanal) | Tongling JQC‑3FF‑S‑Z | 12V bobin, 2 kanal modül | 1 | — | — | Yük anahtarlama; lojik seviye/sürücü ihtiyacı kontrol edilmeli |
| Röle modülü (1 kanal) | Songle SRD‑5VDC‑SL‑C | 5V bobin, tek kanal modül | 1 | — | — | Küçük testler için uygun |
| Lazer verici modülü | KY‑008 | 3 pin (S/+/-) lazer diyot modülü | 1 | — | — | Sera için şart değil; deney/hizalama |
| RC Servo motor | Futaba S3003 | Standart servo, PWM ile açı kontrol | 1 | — | — | Mekanik projeler/deney |
| Sıcaklık‑Nem sensörü modülü | DHT11 | 3 pin modül, düşük hassasiyet | 1 | — | — | Yedek; hedef sensör DHT22/SHT31 |
| Redüktörlü DC motor | — | Dişli kutulu motor, yüksek tork/düşük hız | 1 | — | — | Mekanik projeler/deney |
| Ayarlı trimpotlu modül | — | Üzerinde trimpot olan küçük modül (model belirsiz) | 1 | — | — | Model/fonksiyon foto ile netleşecek |

## Notlar / Açık Noktalar
- Fan hedefi: KAT1 kat fanı + KAT2 kat fanı + egzoz fan + (opsiyonel) FIDE kutu fanı. Envanterde şu an 1 adet 120mm fan var.
- Röle tarafında: 2 kanal 5V röle kartı + (eski proje) 1/2/4/8 kanal röle modülleri var. Final tasarımda çıkış sayısına ve yük tipine göre MOSFET/SSR/röle seçimi netleşecek.
- LDR’ler listede yok (Kat1/Kat2 için 2 adet). Eğer aldıysan model/fiyatını ekleyebilirim.
