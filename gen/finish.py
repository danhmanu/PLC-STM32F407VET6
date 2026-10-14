"""Nap ket qua Freerouting (.ses), do dong GND 2 mat, fill zone, luu board.

Chay: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/finish.py <file.ses>
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "kicad", "PLC_STM32_Modbus.kicad_pcb")
OX, OY, W, H = 50.0, 50.0, 100.0, 80.0
MM = pcbnew.FromMM


def gnd_zone(b, layer, net, rect=None, prio=0, name=None):
    z = pcbnew.ZONE(b)
    z.SetAssignedPriority(prio)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    x0, y0, x1, y1 = rect or (0.3, 0.3, W - 0.3, H - 0.3)
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        ol.Append(MM(OX + x), MM(OY + y))
    z.SetZoneName(name or ("GND_" + b.GetLayerName(layer)))
    b.Add(z)
    return z


def fixups(b):
    """Dong bo field voi so do, lo bat vit 'board only', co chu silk >= 0.8mm, rule clearance."""
    t = kisch.parse(open(os.path.join(HERE, "plc.net"), encoding="utf8").read())
    for c in kisch.find(t, "components")[1:]:
        fp = b.FindFootprintByReference(kisch.find(c, "ref")[1])
        if fp is None:
            continue
        for f in kisch.findall(kisch.find(c, "fields"), "field"):
            name = kisch.find(f, "name")[1]
            val = f[2] if len(f) > 2 and not isinstance(f[2], list) else ""
            if name in ("Footprint",):
                continue
            fp.SetField(name, val)
            fld = fp.GetField(name)
            if name not in ("Reference", "Value"):
                fld.SetVisible(False)
    for fp in b.GetFootprints():
        if fp.GetReference().startswith("H"):
            fp.SetBoardOnly(True)
            fp.SetExcludedFromBOM(True)
            fp.SetExcludedFromPosFiles(True)
        r = fp.Reference()
        r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        r.SetTextThickness(MM(0.13))
    ds = b.GetDesignSettings()
    ds.m_HoleClearance = MM(0.18)
    ns = ds.m_NetSettings
    ns.GetNetClassByName("Power").SetClearance(MM(0.2))


def main():
    ses = sys.argv[1]
    import shutil
    shutil.copy(os.path.join(HERE, "placed.kicad_pcb"), PCB)   # ban da dat linh kien, chua di day
    b = pcbnew.LoadBoard(PCB)
    ok = pcbnew.ImportSpecctraSES(b, ses)
    print("import ses:", ok, " tracks+vias:", len(b.GetTracks()))
    # cac file .ses bo sung (chi chua duong moi): nap vao ban tam roi chep sang
    for extra in sys.argv[2:]:
        tmp = pcbnew.LoadBoard(os.path.join(HERE, "placed.kicad_pcb"))
        pcbnew.ImportSpecctraSES(tmp, extra)
        n = 0

        def key(t):
            if t.GetClass() == "PCB_VIA":
                return ("v", t.GetPosition().x, t.GetPosition().y)
            a, e = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
            return ("t", t.GetLayer()) + tuple(sorted([a, e]))
        have = {key(t) for t in b.GetTracks()}
        for t in tmp.GetTracks():
            if key(t) in have:
                continue
            c = t.Duplicate()
            c.SetParent(b)
            c.SetNet(b.FindNet(t.GetNetname()))
            b.Add(c)
            n += 1
        print("merged", extra, n)
    fixups(b)
    # day cong suat vao chan SOT-23-6 cua LMR16006: thu hep con 0.5mm gan IC de du khoang cach
    u = b.FindFootprintByReference("U101")
    pads = [p.GetPosition() for p in u.Pads()]
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() > MM(0.5):
            for q in (t.GetStart(), t.GetEnd()):
                if any(abs(q.x - p.x) < MM(1.6) and abs(q.y - p.y) < MM(1.6) for p in pads):
                    t.SetWidth(MM(0.5))
                    break
    # pad GND cua cau dau RS485 noi dac vao vung dong
    for p in b.FindFootprintByReference("J402").Pads():
        if p.GetNetname() == "GND":
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    # xoa doan day treo (mot dau khong noi)
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    for _ in range(3):
        dang = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False)]
        for t in dang:
            b.RemoveNative(t)
        b.BuildConnectivity()
        conn = b.GetConnectivity()
        if not dang:
            break
    gnd = b.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        gnd_zone(b, layer, gnd)
    # vung dong +3V3 mat duoi duoi MCU + W5500 (noi cac doan +3V3 ngan)
    gnd_zone(b, pcbnew.B_Cu, b.FindNet("+3V3"), rect=(24.0, 33.0, 72.0, 53.5), prio=1, name="P3V3_B.Cu")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    print("unrouted:", b.GetConnectivity().GetUnconnectedCount(True))
    pcbnew.SaveBoard(PCB, b)
    print("saved")


if __name__ == "__main__":
    main()
