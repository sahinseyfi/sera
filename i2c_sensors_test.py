import time
import board
import busio

print("I2C init...")
i2c = busio.I2C(board.SCL, board.SDA)

# BH1750
print("\nBH1750 test:")
try:
    import adafruit_bh1750
    light = adafruit_bh1750.BH1750(i2c)
    for _ in range(5):
        print(f"  Lux: {light.lux:.1f}")
        time.sleep(1)
except Exception as e:
    print("  BH1750 ERROR:", e)

# ADS1115
print("\nADS1115 test:")
try:
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    ads = ADS.ADS1115(i2c)
    ch0 = AnalogIn(ads, ADS.P0)
    ch1 = AnalogIn(ads, ADS.P1)
    ch2 = AnalogIn(ads, ADS.P2)

    for _ in range(5):
        print(f"  A0: {ch0.voltage:.3f} V | A1: {ch1.voltage:.3f} V | A2: {ch2.voltage:.3f} V")
        time.sleep(1)
except Exception as e:
    print("  ADS1115 ERROR:", e)

print("\nDONE.")
