# Sera Panel Roadmap

Amac
- Sera panelini guvenlik odakli, anlasilir ve profesyonel bir urune donusturmek.
- Panelin 3 temel soruya net cevap vermesini saglamak: Simdi ne oluyor? Neyi degistirebilirim? Degistirirsem ne olur?

Kapsam
- Ana panel (koku app.py + templates/static) birincil odak.
- sera_panel (legacy) sadece geriye donuk destek; yeni gelisim ana panelde.

Mevcut durum ozeti (inceleme)
- Dashboard: sensor durumlari, otomasyon ozeti, grafikler, uyarilar, enerji tahmini, saglik kartlari.
- Kontrol: guvenli manuel komut + acil durdurma.
- Ayarlar: SAFE MODE, limitler, lux/isitici/pompa/fan otomasyonu, toprak kalibrasyonu.
- Raporlar: gunluk/haftalik ozet, karsilastirmalar, grafikler.
- Guvenlik: SAFE MODE varsayilan, sure-limitleri, admin token destegi.

Bosluklar ve iyilestirme alanlari
- Bilgi yogunlugu yuksek; yeni kullanici icin onceliklendirme eksik.
- Manual kontrol akisi riskli yerlerde (sulama/isitma) daha belirgin onay ve geri sayim ihtiyaci.
- Otomasyon mantigi gorunur ama “neden bu karar verildi?” acikligi daha iyi olabilir.
- Bildirimler (email/telegram) ve kritik olay kaydi (audit) kullaniciya proaktif bilgi vermiyor.
- Kurulum/ilk calistirma akisi yok; ayarlar karmasik gorunebilir.
- Veri yonetimi: yedek/geri yukleme, uzun vadeli saklama ve cihaz sagligi raporlari sinirli.

Yol haritasi

Faz 0 - Temizlik ve netlik (kisa vade)
- Legacy sera_panel ile ana panelin rolunu netlestir; dokumanda “tek panel” vurgusu.
- Nav menude “MVP-1/MVP-2” gibi gelistirme etiketlerini temizle.
- Terminoloji standardi: lux/lx, C, %, kWh gibi birimlerde tutarlilik.
- Ayarlar sayfasinda basit/gelismis gorunum anahtari (acemi modu genislet).

Faz 1 - Kullanici deneyimi ve profesyonel gorunum
- Ana sayfada “Durum ozeti” kutusu: SAFE MODE, son veri, alarm sayisi, otomasyon durumu.
- Kritik aksiyonlar icin ikili onay + geri sayim (pompa/isitici).
- Kontrol sayfasinda “son komutlar + nedenleri” paneli.
- Mobil uyum: kart yukseklikleri, buton boylari, oncelikli metrikler.
- Yardim/SSS icin baglamsal mikro yardim (her kartta 1-2 cumle).

Faz 2 - Guvenlik ve isletim
- Bildirim kanallari (email/telegram) ve kritik esiklerde alarm gonderimi.
- Audit log: kim, ne zaman, neyi degistirdi (token dahil).
- Otomatik guvenli mod: sensor veri bayatligi belirli sureyi asarsa SAFE MODE’a gec.
- Ayar yedekleme/geri yukleme (JSON export/import).

Faz 3 - Otomasyonun olgunlastirilmasi
- Otomasyon karar aciklamalari: “su an acik cunku ...” etiketi.
- Senaryo setleri: Yaz/kis profili, gece modu, hasat oncesi.
- Pompa icin “gunluk toplam su/isi limitleri” raporu.
- Fan/isitici bagimliliklari: isitici acikken fan otomatik (zaten var, daha gorunur).

Faz 4 - Raporlama ve icgoruler
- Raporlarda hedef-sapma trendleri ve “en kritik 3 konu” listesi.
- Haftalik raporda iyilestirme onerileri (sadece gozlem, otomasyon onerisi degil).
- Veri kalitesi dashboardu: sensor offline sureleri, spike sayilari, kapsama.

Kalite ve test
- SIMULATION_MODE ile kritik akislara otomatik test ekle.
- UI smoke testleri: /dashboard, /control, /settings, /reports.
- Guvenlik regresyonu: SAFE MODE ve emergency_stop davranislari icin testler.

Basari kriterleri
- Yeni kullanici 5 dakikada kurulumu tamamlari ve ilk okumalari gorur.
- Kritk bir alarm olusunca 60 sn icinde bildirim alinir.
- Gunluk rapor, “ne oldu ve ne yapmaliyim” sorusunu tek sayfada yanitlar.
