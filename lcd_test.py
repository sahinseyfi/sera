from RPLCD.i2c import CharLCD
from time import sleep

lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,   # 0x3f olabilir
    port=1,
    cols=20,
    rows=4,
    charmap='A00',
    auto_linebreaks=True
)

lcd.clear()
lcd.write_string("AKILLI SERA\n")
lcd.write_string("LCD Calisiyor\n")
lcd.write_string("BH1750 + DHT\n")
lcd.write_string("ADS1115 OK")

sleep(10)
lcd.clear()
