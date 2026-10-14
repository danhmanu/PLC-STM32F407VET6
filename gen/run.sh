#!/bin/sh
# Regenerate schematic + ERC
cd "$(dirname "$0")/.." || exit 1
rm -f kicad/*.kicad_sch
"/c/Program Files/KiCad/10.0/bin/python.exe" gen/design.py || exit 1
cd kicad && "/c/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc --severity-all -o erc.rpt PLC_STM32_Modbus.kicad_sch
grep -o "^\[[a-z_]*\]" erc.rpt | sort | uniq -c
cd kicad 2>/dev/null; "/c/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch export pdf -o PLC_STM32_Modbus.pdf PLC_STM32_Modbus.kicad_sch >/dev/null
