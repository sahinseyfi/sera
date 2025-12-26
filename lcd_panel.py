import time
import smbus2
import board
import busio
import adafruit_dht
from RPLCD.i2c import CharLCD
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# ---------- LCD ----------
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4, charmap='A00')
lcd.clear()

def put(row, text):
    # 20 karaktere sabitle (taşma/kayma olmasın)
    text = (text[:20]).ljust(20)
    lcd.cursor_pos = (row, 0)
    lcd.write_string(text)

# ---------- BH1750 ----------
BH_ADDR = 0x23
CONT_H_RES = 0x10
bus = smbus2.SMBus(1)

def read_lux():
    data = bus.read_i2c_block_data(BH_ADDR, CONT_H_RES, 2)
    return int(((data[0] << 8) | data[1]) / 1.2)

# ---------- DHT22 ----------
dht = adafruit_dht.DHT22(board.D17)
last_t = None
last_h = None

# ---------- ADS1115 (Toprak) ----------
DRY = 17750
WET = 5600  # sulamadan sonra gördüğün en düşük stabil değer

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c, address=0x48)
ads.gain = 1
soil = AnalogIn(ads, 0)

def soil_percent():
    raw = soil.value
    pct = (DRY - raw) / (DRY - WET) * 100
    return int(clamp(pct))

# ---------- LOOP ----------
while True:
    # DHT
    try:
        t = dht.temperature
        h = dht.humidity
        if t is not None and h is not None:
            last_t, last_h = t, h
    except:
        pass

    # Lux
    try:
        lux = read_lux()
    except:
        lux = None

    # Soil
    try:
        sp = soil_percent()
    except:
        sp = None

    # Satırlar
    if last_t is None or last_h is None:
        line0 = "T: --.-C  N: --.-%"
    else:
        line0 = f"T:{last_t:4.1f}C  N:{last_h:4.1f}%"

    line1 = f"Isik: {lux:5d} lux" if lux is not None else "Isik:  ----- lux"
    line2 = f"Toprak: {sp:3d} %" if sp is not None else "Toprak:  -- %"
    line3 = "Sistem: AKTIF"

    put(0, line0)
    put(1, line1)
    put(2, line2)
    put(3, line3)

    time.sleep(2)
