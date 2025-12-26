import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# I2C
i2c = busio.I2C(board.SCL, board.SDA)

# ADS1115 (adres: 0x48)
ads = ADS1115(i2c, address=0x48)
ads.gain = 1  # 0–4.096V aralığı (3.3V sistem için güvenli)

# A0 kanalı (EN GARANTİLİ KULLANIM)
ch0 = AnalogIn(ads, 0)

def avg(chan, n=10, dt=0.05):
    total = 0
    for _ in range(n):
        total += chan.value
        time.sleep(dt)
    return total / n

while True:
    raw = avg(ch0)
    print(f"A0 raw: {raw:.0f}")
    time.sleep(1)
