import smbus
import time

# I2C bus
bus = smbus.SMBus(1)

# BH1750 adresi (genelde 0x23)
address = 0x23

# Sürekli yüksek çözünürlük modu
POWER_ON = 0x01
RESET = 0x07
CONT_H_RES_MODE = 0x10

bus.write_byte(address, POWER_ON)
bus.write_byte(address, RESET)

time.sleep(0.2)

while True:
    data = bus.read_i2c_block_data(address, CONT_H_RES_MODE, 2)
    lux = (data[0] << 8 | data[1]) / 1.2
    print(f"Işık: {lux:.2f} lux")
    time.sleep(2)
