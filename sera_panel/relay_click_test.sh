#!/usr/bin/env bash
set -euo pipefail

PINS=(18 23 24 25 20 21)
NAMES=("R1 isitici+fan" "R2 12cm havalandirma fan" "R3 pompa" "R4 3.kat fani" "R5 3.kat orta isik" "R6 3.kat arka isik")

if gpioset --help 2>&1 | grep -q -- '--chip\|-c'; then
  CHIP_ARGS=(-c gpiochip0)
else
  CHIP_ARGS=(gpiochip0)
fi

echo "Servisleri durduruyorum (GPIO çakışmasın)..."
for s in $(systemctl list-units --type=service --all | awk 'tolower($0) ~ /(sera|panel|flask|gunicorn)/ {print $1}'); do
  sudo systemctl stop "$s" || true
done

echo
echo "Röleleri sırayla 6 sn ON (0) sonra 2 sn OFF (1) yapacağım."
echo "CHIP_ARGS: ${CHIP_ARGS[*]}"
echo

hold_set() {
  local pin="$1" val="$2" sec="$3"
  sudo gpioset "${CHIP_ARGS[@]}" "${pin}=${val}" &
  local pid=$!
  sleep "$sec"
  sudo kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

for i in "${!PINS[@]}"; do
  p="${PINS[$i]}"
  n="${NAMES[$i]}"
  echo ">>> $n | GPIO$p  ON (0) 6sn"
  hold_set "$p" 0 6
  echo ">>> $n | GPIO$p OFF (1) 2sn"
  hold_set "$p" 1 2
  echo
done

echo "BİTTİ: hepsi OFF."
