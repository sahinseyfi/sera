import time
import board
import adafruit_dht

# DHT11 sensör: BCM16 (GPIO16) -> fiziksel pin 36
dht = adafruit_dht.DHT11(board.D16)

while True:
    try:
        t = dht.temperature
        h = dht.humidity
        print(f"Sıcaklık: {t}°C  Nem: {h}%")
    except RuntimeError as e:
        print(f"Okuma hatası: {e}")
    time.sleep(1)
