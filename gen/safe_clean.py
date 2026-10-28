"""Xoa an toan day/via treo theo bao cao DRC: xoa tung phan tu, neu so ket noi ho tang thi hoan tac.

  kicad-cli pcb drc --format json -o kicad/drc.json kicad/PLC_STM32_Modbus.kicad_pcb
  "C:\Program Files\KiCad\10.0\bin\python.exe" gen/safe_clean.py
"""
import json
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "kicad", "PLC_STM32_Modbus.kicad_pcb")
DRC = os.path.join(HERE, "..", "kicad", "drc.json")
T = pcbnew.ToMM


def main():
    d = json.load(open(DRC, encoding="utf8"))
    targets = [(v["type"], v["items"][0]["pos"]["x"], v["items"][0]["pos"]["y"]) for v in d["violations"]
               if v["type"] in ("track_dangling", "via_dangling")]
    b = pcbnew.LoadBoard(PCB)

    def unc():
        b.BuildConnectivity()
        return b.GetConnectivity().GetUnconnectedCount(True)

    base = unc()
    removed = 0
    for typ, x, y in targets:
        cand = None
        for t in b.GetTracks():
            pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd(), t.GetPosition()]
            if (typ == "via_dangling") != (t.GetClass() == "PCB_VIA"):
                continue
            if any(abs(T(q.x) - x) < 0.01 and abs(T(q.y) - y) < 0.01 for q in pts):
                cand = t
                break
        if cand is None:
            continue
        clone = cand.Duplicate()
        b.RemoveNative(cand)
        if unc() > base:
            b.Add(clone)
        else:
            removed += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print("removed", removed, "unconnected", unc())


if __name__ == "__main__":
    main()
