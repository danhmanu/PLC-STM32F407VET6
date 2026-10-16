"""Gop duong day moi tu file .ses (Freerouting chay voi duong cu da khoa) vao PCB hien tai.

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/merge_ses.py kicad/PLC_STM32_Modbus.kicad_pcb file.ses
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def key(t):
    if t.GetClass() == "PCB_VIA":
        return ("v", t.GetPosition().x, t.GetPosition().y)
    a, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
    return ("t", t.GetLayer()) + tuple(sorted([a, e]))


def main():
    pcb, ses = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(pcb)
    tmp = pcbnew.LoadBoard(os.path.join(HERE, "placed.kicad_pcb"))
    pcbnew.ImportSpecctraSES(tmp, ses)
    have = {key(t) for t in b.GetTracks()}
    n = 0
    for t in tmp.GetTracks():
        if key(t) in have:
            continue
        c = t.Duplicate()
        c.SetParent(b)
        c.SetNet(b.FindNet(t.GetNetname()))
        c.SetLocked(False)
        b.Add(c)
        n += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(pcb, b)
    print("merged", n)


if __name__ == "__main__":
    main()
