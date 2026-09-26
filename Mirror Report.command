#!/bin/bash
# Opens your latest Mirror report in the browser. No questions after the first run. Nothing is sent anywhere.
cd "$(dirname "$0")" || exit 1
TEST=0
if [ "$1" = "--test" ]; then TEST=1; fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Mirror needs Python 3.8 or newer, and I could not find it."
  echo "Install it from https://www.python.org/downloads/ and double-click this file again."
  [ $TEST -eq 0 ] && read -r -p "Press Enter to close." _
  exit 1
fi
if [ $TEST -eq 1 ]; then
  python3 mirror.py report --yes
  exit $?
fi
python3 mirror.py report --open
echo
read -r -p "Press Enter to close this window." _
