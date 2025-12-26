#!/usr/bin/env bash
set -euo pipefail

PINS=(18 23 24 25 20 21)

# gpioset sürümüne göre chip seçimini belirle
if gpioset --help 2>&1 | grep -q -- '--chip\|-c'; then
  CHIP_ARGS=(-c gpiochip0)
else
  CHIP_ARGS=(gpiochip0)
fi

echo "Her GPIO için: 0 ver (2sn), 1 ver (2sn). Klik hangi değerdeyse ON odur."
echo "CHIP_ARGS: ${CHIP_ARGS[*]}"
echo

hold_set() {
  local pin="$1" val="$2" sec="$3"
  # gpioset bazı sürümlerde -t destekler, bazılarında desteklemez: arkaplanda tutup süre dolunca öldürüyoruz
  sudo gpioset "${CHIP_ARGS[@]}" "${pin}=${val}" &
  local pid=$!
  sleep "$sec"
  sudo kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

for p in "${PINS[@]}"; do
  echo "GPIO$p => set 0 (2sn)  $(date +%T)"
  hold_set "$p" 0 2
  echo "GPIO$p => set 1 (2sn)  $(date +%T)"
  hold_set "$p" 1 2
  echo
done

echo "BİTTİ."
