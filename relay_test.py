#!/usr/bin/env python3
import time
import sys

# Çoğu röle kartı "aktif-low" çalışır: GPIO LOW -> röle çeker
ACTIVE_LOW = True

RELAYS = [
    ("Röle 1 (ısıtıcı+fan)", 18),
    ("Röle 2 (12cm havalandırma fanı)", 23),
    # ("Röle 3 (pompa)", 24),  # SU YOK -> KAPALI / TESTE DAHİL DEĞİL
    ("Röle 4 (3.kat fanı)", 25),
    ("Röle 5 (3.kat orta ışık)", 20),
    ("Röle 6 (3.kat arka ışık)", 21),
]

ON_TIME_SEC = 2.0
OFF_TIME_SEC = 1.0

def main():
    driver = None
    try:
        # Önce gpiozero dene (daha modern; libgpiod altyapısıyla çalışır)
        from gpiozero import DigitalOutputDevice

        class Relay:
            def __init__(self, gpio):
                self.dev = DigitalOutputDevice(gpio, active_high=not ACTIVE_LOW, initial_value=False)
            def on(self): self.dev.on()
            def off(self): self.dev.off()
            def close(self): self.dev.close()

        driver = "gpiozero"

    except Exception:
        # gpiozero yoksa RPi.GPIO dene
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            class Relay:
                def __init__(self, gpio):
                    self.gpio = gpio
                    GPIO.setup(self.gpio, GPIO.OUT)
                    self.off()
                def on(self):
                    GPIO.output(self.gpio, GPIO.LOW if ACTIVE_LOW else GPIO.HIGH)
                def off(self):
                    GPIO.output(self.gpio, GPIO.HIGH if ACTIVE_LOW else GPIO.LOW)
                def close(self):
                    self.off()

            driver = "RPi.GPIO"
        except Exception as e:
            print("GPIO kütüphanesi bulunamadı.")
            print("Çözüm: sudo apt install -y python3-gpiozero  (önerilen)")
            print("Alternatif: sudo apt install -y python3-rpi.gpio")
            print("Hata:", e)
            sys.exit(1)

    print(f"\n=== Röle Testi (driver: {driver}) ===")
    print("Pompa TEST DIŞI (GPIO24).")
    print("Çıkmak için her adımda 'q' yazıp Enter.\n")
    print("Eğer röleler ters çalışıyorsa (ON dediğinde kapanıyorsa), dosyada ACTIVE_LOW değerini değiştir.\n")

    relays = []
    try:
        for name, gpio in RELAYS:
            relays.append((name, gpio, Relay(gpio)))

        for idx, (name, gpio, r) in enumerate(relays, start=1):
            inp = input(f"[{idx}/{len(relays)}] Hazırsa Enter (ya da q): ").strip().lower()
            if inp == "q":
                break

            print(f"-> ON  : {name}  (GPIO{gpio})")
            r.on()
            time.sleep(ON_TIME_SEC)

            print(f"-> OFF : {name}  (GPIO{gpio})")
            r.off()
            time.sleep(OFF_TIME_SEC)

        print("\nBitti. Tüm röleler OFF yapıldı.")

    except KeyboardInterrupt:
        print("\nCTRL+C alındı. Kapatıyorum....")

    finally:
        for _, _, r in relays:
            try:
                r.off()
                r.close()
            except Exception:
                pass

        # RPi.GPIO kullanıldıysa cleanup
        if driver == "RPi.GPIO":
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass

if __name__ == "__main__":
    main()
