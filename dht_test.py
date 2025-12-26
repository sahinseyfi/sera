import time
import adafruit_dht
import board

dht = adafruit_dht.DHT22(board.D17)

while True:
    try:
        temperature = dht.temperature
        humidity = dht.humidity
        print(f"Sıcaklık: {temperature:.1f} °C   Nem: {humidity:.1f} %")
    except RuntimeError as error:
        print("DHT okuma hatası:", error)
    time.sleep(2)
