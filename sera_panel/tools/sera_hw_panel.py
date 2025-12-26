#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AKILLI SERA – Donanım Test Paneli
- DHT22 GPIO17: 10 deneme (2 sn arayla) okur, sonucu yazdırır.
- Röleler: Enter ile sırayla test
    Enter => ON
    Enter => OFF ve sonraki
  Komutlar:
    q + Enter => çıkış (hepsi OFF)
    s + Enter => bu röleyi atla (OFF kalır)
GÜVENLİK:
- Başta tüm röleleri OFF'a çeker.
- Çıkışta (CTRL+C dahil) tüm röleleri OFF'a çeker.
"""

import sys, time, argparse, atexit

RELAYS = [
    ("relay1_heater_fan", 18),
    ("relay2_vent_fan", 23),
    ("relay3_pump", 24),
    ("relay4_lvl3_fan", 25),
    ("relay5_lvl3_mid_light", 20),
    ("relay6_lvl3_back_light", 21),
]

DHT_PIN = 17  # GPIO17 (BCM)

def try_read_dht():
    print("\n=== DHT22 OKUMA (GPIO17) ===")
    try:
        import board
        import adafruit_dht
    except Exception as e:
        print("DHT için kütüphane yok gibi:", e)
        print("Kurulum:")
        print("  python3 -m pip install adafruit-circuitpython-dht")
        print("  sudo apt-get update && sudo apt-get install -y libgpiod2")
        return

    dht = None
    try:
        dht = adafruit_dht.DHT22(getattr(board, "D17"))
        for i in range(1, 11):
            try:
                t = dht.temperature
                h = dht.humidity
                if t is not None and h is not None:
                    print(f"OK: T={t:.1f}°C  H={h:.1f}%  (deneme {i}/10)")
                    return
                else:
                    print(f"retry: None değer geldi (deneme {i}/10)")
            except Exception as e:
                print(f"retry: {e} (deneme {i}/10)")
            time.sleep(2)
        print("DHT okunamadı (10 deneme bitti). Kablo/pull-up/kitaplık kontrol et.")
    finally:
        try:
            if dht:
                dht.exit()
        except Exception:
            pass

def supports_rpigpio():
    try:
        import RPi.GPIO as GPIO  # noqa
        return True
    except Exception:
        return False

class GPIOBackend:
    def __init__(self):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.GPIO.setwarnings(False)
        self.GPIO.setmode(self.GPIO.BCM)

    def setup_out(self, pin, initial):
        self.GPIO.setup(pin, self.GPIO.OUT, initial=initial)

    def write(self, pin, val):
        self.GPIO.output(pin, val)

    def cleanup(self):
        try:
            self.GPIO.cleanup()
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser(description="Sera donanım test paneli (DHT22 + röleler).")
    ap.add_argument("--active-low", action="store_true",
                    help="Röle kartın active-low ise ver (ON=0, OFF=1). Varsayılan active-high.")
    ap.add_argument("--delay", type=float, default=0.2, help="OFF sonrası küçük bekleme (sn).")
    ap.add_argument("--no-dht", action="store_true", help="DHT okumasını atla.")
    args = ap.parse_args()

    if not args.no_dht:
        try_read_dht()

    print("\n=== RÖLE TEST PANELİ (Enter ile) ===")
    if not supports_rpigpio():
        print("HATA: RPi.GPIO yok. Kurulum:")
        print("  python3 -m pip install RPi.GPIO")
        return 2

    gpio = GPIOBackend()

    OFF = 1 if args.active_low else 0
    ON  = 0 if args.active_low else 1

    pins = [p for _, p in RELAYS]

    def all_off():
        for p in pins:
            try:
                gpio.write(p, OFF)
            except Exception:
                pass

    # Setup + SAFE OFF
    for p in pins:
        gpio.setup_out(p, initial=OFF)

    atexit.register(all_off)
    atexit.register(gpio.cleanup)

    print(f"Mod: {'ACTIVE-LOW' if args.active_low else 'ACTIVE-HIGH'} (OFF={OFF}, ON={ON})")
    print("Komutlar: Enter=devam | q=çıkış | s=atla")
    print("⚠️ UYARI: Isıtıcı/pompa ON durumunda fiziksel risk. Kısa tut.\n")

    try:
        for name, pin in RELAYS:
            print(f"\n--- Sıradaki: {name} (GPIO{pin}) ---")
            print("Enter=ON | s=atla | q=çıkış")
            cmd = input("> ").strip().lower()
            if cmd == "q":
                print("Çıkış. Hepsi OFF...")
                all_off()
                return 0
            if cmd == "s":
                print("Atlandı (OFF).")
                gpio.write(pin, OFF)
                continue

            gpio.write(pin, ON)
            print(f"{name} => ON")
            print("Enter=OFF ve sonraki | q=çıkış (önce OFF)")
            cmd2 = input("> ").strip().lower()

            gpio.write(pin, OFF)
            time.sleep(args.delay)
            print(f"{name} => OFF")

            if cmd2 == "q":
                print("Çıkış. Hepsi OFF...")
                all_off()
                return 0

        print("\nBitti. Hepsi OFF.")
        all_off()
        return 0

    except KeyboardInterrupt:
        print("\nCTRL+C. Hepsi OFF...")
        all_off()
        return 130
    except Exception as e:
        print(f"\nHATA: {e}")
        print("Hepsi OFF...")
        all_off()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
