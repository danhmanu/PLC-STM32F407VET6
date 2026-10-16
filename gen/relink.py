"""Cap nhat lien ket footprint <-> symbol (KIID path) theo netlist moi, giu nguyen duong day PCB.

Dung sau khi sinh lai so do (UUID symbol thay doi):
  kicad-cli sch export netlist --format kicadsexpr -o gen/plc.net kicad/PLC_STM32_Modbus.kicad_sch
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/relink.py kicad/PLC_STM32_Modbus.kicad_pcb [gen/placed.kicad_pcb]
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    t = kisch.parse(open(os.path.join(HERE, "plc.net"), encoding="utf8").read())
    paths = {}
    for c in kisch.find(t, "components")[1:]:
        sp = kisch.find(c, "sheetpath")
        paths[kisch.find(c, "ref")[1]] = kisch.find(sp, "tstamps")[1] + kisch.find(c, "tstamps")[1]
    for f in sys.argv[1:]:
        b = pcbnew.LoadBoard(f)
        n = 0
        for fp in b.GetFootprints():
            p = paths.get(fp.GetReference())
            if p:
                fp.SetPath(pcbnew.KIID_PATH(p))
                n += 1
        pcbnew.SaveBoard(f, b)
        print(f, "relinked", n)


if __name__ == "__main__":
    main()
