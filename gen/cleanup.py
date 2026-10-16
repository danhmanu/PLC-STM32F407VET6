"""Sau DRC: xoa doan day gay chap (shorting_items) va thu hep day vi pham khoang cach.

Chay: kicad-cli pcb drc --format json -o kicad/drc.json kicad/PLC_STM32_Modbus.kicad_pcb
      "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/cleanup.py
"""
import json
import os
import re

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "kicad", "PLC_STM32_Modbus.kicad_pcb")
DRC = os.path.join(HERE, "..", "kicad", "drc.json")
MM = pcbnew.FromMM


def find_track(b, item):
    """Tim track theo net + do dai + vi tri trong mo ta DRC."""
    m = re.match(r"Track \[(.*?)\] on (\S+), length ([\d.]+) mm", item["description"])
    if not m:
        return None
    net, layer, length = m.group(1), m.group(2), float(m.group(3))
    px, py = MM(item["pos"]["x"]), MM(item["pos"]["y"])
    best = None
    for t in b.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() != net or b.GetLayerName(t.GetLayer()) != layer:
            continue
        if abs(pcbnew.ToMM(t.GetLength()) - length) > 0.002:
            continue
        d = min(abs(t.GetStart().x - px) + abs(t.GetStart().y - py), abs(t.GetEnd().x - px) + abs(t.GetEnd().y - py),
                abs(t.GetPosition().x - px) + abs(t.GetPosition().y - py))
        if best is None or d < best[0]:
            best = (d, t)
    return best[1] if best else None


def main():
    d = json.load(open(DRC, encoding="utf8"))
    b = pcbnew.LoadBoard(PCB)
    removed, narrowed = 0, 0
    gone = set()
    for v in d["violations"]:
        if v["type"] == "shorting_items":
            tracks = [find_track(b, it) for it in v["items"]]
            tracks = [t for t in tracks if t is not None]
            if tracks:
                t = min(tracks, key=lambda x: x.GetLength())   # bo doan ngan hon
                if t.m_Uuid.AsString() not in gone:
                    gone.add(t.m_Uuid.AsString())
                    b.RemoveNative(t)
                    removed += 1
        elif v["type"] == "track_dangling":
            for it in v["items"]:
                t = find_track(b, it)
                if t is not None and t.m_Uuid.AsString() not in gone:
                    gone.add(t.m_Uuid.AsString())
                    b.RemoveNative(t)
                    removed += 1
        elif v["type"] == "clearance":
            m = re.search(r"clearance ([\d.]+) mm; actual ([\d.]+) mm", v["description"])
            need = float(m.group(1)) - float(m.group(2)) if m else 0
            for it in v["items"]:
                t = find_track(b, it)
                if t is not None and t.GetWidth() > MM(0.3):
                    t.SetWidth(t.GetWidth() - MM(2 * need + 0.02))
                    narrowed += 1
                    break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print("removed", removed, "narrowed", narrowed)


if __name__ == "__main__":
    main()
