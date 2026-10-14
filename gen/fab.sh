#!/bin/sh
# Xuat file san xuat PCB: Gerber, khoan, vi tri linh kien (2 mat), BOM, PDF, anh 3D
cd "$(dirname "$0")/../kicad" || exit 1
CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
PCB=PLC_STM32_Modbus.kicad_pcb
rm -rf fab && mkdir -p fab/gerber
"$CLI" pcb export gerbers --layers "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
    --subtract-soldermask --no-x2 -o fab/gerber/ "$PCB" >/dev/null
"$CLI" pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
    -o fab/gerber/ "$PCB" >/dev/null
"$CLI" pcb export pos --side front --format csv --units mm -o fab/pos_top.csv "$PCB" >/dev/null
"$CLI" pcb export pos --side back --format csv --units mm -o fab/pos_bottom.csv "$PCB" >/dev/null
"$CLI" sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --labels 'Ref,Value,Footprint,Qty' \
    --group-by 'Value,Footprint' -o BOM.csv PLC_STM32_Modbus.kicad_sch >/dev/null
"$CLI" pcb export pdf --layers "F.Cu,F.SilkS,Edge.Cuts" --mode-single -o fab/PCB_top.pdf "$PCB" >/dev/null
"$CLI" pcb export pdf --layers "B.Cu,B.SilkS,Edge.Cuts" --mode-single --mirror -o fab/PCB_bottom.pdf "$PCB" >/dev/null
"$CLI" pcb render --side top -w 1600 -h 1280 -o fab/render_top.png "$PCB" >/dev/null 2>&1
"$CLI" pcb render --side bottom -w 1600 -h 1280 -o fab/render_bottom.png "$PCB" >/dev/null 2>&1
(cd fab/gerber && "/c/Program Files/KiCad/10.0/bin/python.exe" -c "
import zipfile,os
z=zipfile.ZipFile('../PLC_STM32_Modbus_gerber.zip','w',zipfile.ZIP_DEFLATED)
[z.write(f) for f in sorted(os.listdir('.'))]
z.close()")
ls -R fab | head -40
