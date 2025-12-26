import time
import smbus2 as smbus
import adafruit_dht
import board

# -------- BH1750 --------
bus = smbus.SMBus(1)
BH1750_ADDR = 0x23
POWER_ON = 0x01
RESET = 0x07
CONT_H_RES_MODE = 0x10

bus.write_byte(BH1750_ADDR, POWER_ON)
bus.write_byte(BH1750_ADDR, RESET)
time.sleep(0.2)

def read_lux():
    data = bus.read_i2c_block_data(BH1750_ADDR, CONT_H_RES_MODE, 2)
    return ((data[0] << 8) | data[1]) / 1.2

# -------- DHT22 --------
dht = adafruit_dht.DHT22(board.D17)

while True:
    # BH1750
    try:
        lux = read_lux()
    except Exception as e:
        lux = None
        print("BH1750 hata:", e)

    # DHT22
    try:
        t = dht.temperature
        h = dht.humidity
    except RuntimeError as e:
        # DHT arada hata verebilir
        t, h = None, None
        print("DHT hata:", e)

    # Print
    lux_str = f"{lux:.1f}" if lux is not None else "--"
    t_str = f"{t:.1f}" if t is not None else "--"
    h_str = f"{h:.1f}" if h is not None else "--"

    print(f"Sıcaklık: {t_str} °C | Nem: {h_str} % | Işık: {lux_str} lux")
    time.sleep(2)
