import time
import csv
from datetime import datetime
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# === KALİBRASYON ===
DRY = 17750
WET = 5600

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

# I2C & ADS
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c, address=0x48)
ads.gain = 1

ch0 = AnalogIn(ads, 0)

def avg(chan, n=10, dt=0.05):
    s = 0
    for _ in range(n):
        s += chan.value
        time.sleep(dt)
    return s / n

filename = "moisture_log.csv"

# Dosya yoksa başlık yaz
try:
    with open(filename, "x", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "raw", "percent"])
except FileExistsError:
    pass

print("Dakikalık kayıt başladı (CTRL+C ile durdur)")

while True:
    raw = avg(ch0)
    pct = clamp((DRY - raw) / (DRY - WET) * 100)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts, f"{raw:.0f}", f"{pct:.1f}"])

    print(f"{ts} | raw={raw:.0f} | {pct:.1f}%")

    time.sleep(60)  # 1 dakika


