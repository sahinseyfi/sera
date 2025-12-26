from flask import Flask, render_template, jsonify, request
import random
import os
from datetime import datetime

# --- KONFİGÜRASYON ---
# Raspberry Pi pin ayarları (İleride kullanacağız)
PIN_AYARLARI = {
    'DHT_PIN': 4,
    'RELA_ISIK': 17,
    'RELA_FAN': 27,
    'RELA_POMPA': 22
}

# Dosya yollarını sabitleme
proje_ana_dizini = os.path.dirname(os.path.abspath(__file__))
sablon_dizini = os.path.join(proje_ana_dizini, 'templates')

app = Flask(__name__, template_folder=sablon_dizini)

# --- SERA YÖNETİCİSİ SINIFI ---
class SeraYoneticisi:
    def __init__(self):
        # Geçmiş veriler (Grafik için)
        self.veriler = {
            'zaman': [],
            'sicaklik': [],
            'nem': [],
            'toprak': [],
            'isik': []
        }
        # Anlık durum (Varsayılan değerler)
        self.durum = {
            'sicaklik': 24.0,
            'nem': 55,
            'toprak_nemi': 60,
            'isik_seviyesi': 500,
            'isik_durumu': False,
            'fan_durumu': False,
            'pompa_durumu': False
        }
        self.loglar = []

    def log_ekle(self, mesaj):
        zaman = datetime.now().strftime('%H:%M')
        self.loglar.append({'zaman': zaman, 'mesaj': mesaj})
        # Son 10 logu tut
        if len(self.loglar) > 10:
            self.loglar.pop(0)

    def sensorleri_oku(self):
        # BURASI SİMÜLASYON ALANI
        # Sensörler bağlandığında burayı gerçek okumalarla değiştireceğiz.
        
        # 1. Sıcaklık hafif dalgalanır
        self.durum['sicaklik'] = round(self.durum['sicaklik'] + random.uniform(-0.2, 0.2), 1)
        
        # 2. Fan açıksa nem düşer
        if self.durum['fan_durumu']:
            self.durum['nem'] = max(30, self.durum['nem'] - 0.5)
        else:
            self.durum['nem'] = min(90, self.durum['nem'] + 0.2)
            
        # 3. Pompa açıksa toprak nemi artar
        if self.durum['pompa_durumu']:
            self.durum['toprak_nemi'] = min(100, self.durum['toprak_nemi'] + 2.0)
        else:
            self.durum['toprak_nemi'] = max(0, self.durum['toprak_nemi'] - 0.1)

        # Değerleri temizle (Virgülden kurtar)
        self.durum['nem'] = int(self.durum['nem'])
        self.durum['toprak_nemi'] = int(self.durum['toprak_nemi'])
        
        # Grafikler için verileri kaydet
        simdi = datetime.now().strftime('%H:%M:%S')
        self.veriler['zaman'].append(simdi)
        self.veriler['sicaklik'].append(self.durum['sicaklik'])
        self.veriler['nem'].append(self.durum['nem'])
        self.veriler['toprak'].append(self.durum['toprak_nemi'])
        
        # Listeyi temiz tut (Son 30 veri)
        if len(self.veriler['zaman']) > 30:
            for k in self.veriler:
                self.veriler[k].pop(0)

# Sistemi başlat
sera = SeraYoneticisi()

@app.route('/')
def index():
    return render_template('index.html', durum=sera.durum)

@app.route('/api/guncelle')
def api_guncelle():
    # Sayfa her sorduğunda sensörleri oku
    sera.sensorleri_oku()
    # Verileri paketle ve gönder
    return jsonify({
        'durum': sera.durum,
        'grafik': sera.veriler,
        'loglar': list(reversed(sera.loglar))
    })

@app.route('/api/kontrol', methods=['POST'])
def api_kontrol():
    veri = request.json
    cihaz = veri.get('cihaz')
    eylem = veri.get('eylem') # 'ac' veya 'kapat'
    
    durum_bool = True if eylem == 'ac' else False
    
    # Komuta göre işlem yap
    if cihaz == 'isik':
        sera.durum['isik_durumu'] = durum_bool
    elif cihaz == 'fan':
        sera.durum['fan_durumu'] = durum_bool
    elif cihaz == 'pompa':
        sera.durum['pompa_durumu'] = durum_bool
        if durum_bool:
            sera.log_ekle("Sulama Başlatıldı 💧")
        else:
            sera.log_ekle("Sulama Bitti 🛑")
            
    return jsonify({'basarili': True})

if __name__ == '__main__':
    print("Momo & Nova Station v3.0 Online! 🚀")
    print("Erişim: http://192.168.1.13:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
