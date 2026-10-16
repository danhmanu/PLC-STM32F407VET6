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
OX, OY, W, H = 50.0, 50.0, 120.0, 90.0
ISO_Y, ISO_W = 29.0, 2.4
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


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def obstacles(b):
    """Danh sach vat can dong (mm): ('s', ax, ay, bx, by, halfw, net) va ('c', x, y, r, net)."""
    T = pcbnew.ToMM
    obs = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            obs.append(("c", T(t.GetPosition().x), T(t.GetPosition().y), T(t.GetWidth(pcbnew.F_Cu)) / 2, t.GetNetname()))
        else:
            obs.append(("s", T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y),
                        T(t.GetWidth()) / 2, t.GetNetname()))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            x0, y0, x1, y1 = T(bb.GetX()), T(bb.GetY()), T(bb.GetRight()), T(bb.GetBottom())
            hw = min(x1 - x0, y1 - y0) / 2
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if x1 - x0 > y1 - y0:
                obs.append(("s", x0 + hw, cy, x1 - hw, cy, hw, pad.GetNetname()))
            else:
                obs.append(("s", cx, y0 + hw, cx, y1 - hw, hw, pad.GetNetname()))
            if pad.GetDrillSize().x > 0:
                obs.append(("c", cx, cy, T(pad.GetDrillSize().x) / 2 + 0.1, "#hole"))
    return obs


def free_spot(obs, x, y, r, net, clr=0.32):
    for o in obs:
        if o[0] == "c":
            if ((o[1] - x) ** 2 + (o[2] - y) ** 2) ** 0.5 < o[3] + r + (clr if o[4] != net else 0.05):
                return False
        else:
            if o[6] == net:
                continue
            if _seg_dist(x, y, o[1], o[2], o[3], o[4]) < o[5] + r + clr:
                return False
    return True


def stitch(b, netname, rect, pitch=3.0, via_d=0.6, drill=0.3):
    """Via khau noi vung dong 2 mat tren luoi deu, tranh moi dong khac net."""
    net = b.FindNet(netname)
    obs = obstacles(b)
    x0, y0, x1, y1 = rect
    added = []
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            X, Y = OX + x, OY + y
            # tranh courtyard linh kien (ca 2 mat) de khong khoan duoi linh kien
            inside = False
            for fp in b.GetFootprints():
                for lay in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                    cy = fp.GetCourtyard(lay)
                    if cy.OutlineCount() and cy.Contains(pcbnew.VECTOR2I(MM(X), MM(Y))):
                        inside = True
                        break
                if inside:
                    break
            if not inside and free_spot(obs, X, Y, via_d / 2, netname):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(MM(X), MM(Y)))
                v.SetWidth(MM(via_d))
                v.SetDrill(MM(drill))
                v.SetNet(net)
                b.Add(v)
                obs.append(("c", X, Y, via_d / 2, netname))
                added.append(v)
            x += pitch
        y += pitch
    return added


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
    for jref in ("J703", "J701", "J101", "J501", "J502"):
        for p in b.FindFootprintByReference(jref).Pads():
            if p.GetNetname() in ("GND", "/16 ngo ra transistor/COM_OUT"):
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    # xoa doan day treo (mot dau khong noi)
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    for _ in range(3):
        dang = [t for t in b.GetTracks() if (t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False))
                or (t.GetClass() == "PCB_VIA" and len(conn.GetConnectedItems(t)) == 0)]
        for t in dang:
            b.RemoveNative(t)
        b.BuildConnectivity()
        conn = b.GetConnectivity()
        if not dang:
            break
    gnd = b.FindNet("GND")
    com = b.FindNet("/16 ngo ra transistor/COM_OUT")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        # phia logic: GND ; phia tai: COM_OUT (tach boi ranh cach ly)
        gnd_zone(b, layer, gnd, rect=(0.3, ISO_Y + ISO_W / 2, W - 0.3, H - 0.3))
        gnd_zone(b, layer, com, rect=(0.3, 0.3, W - 0.3, ISO_Y - ISO_W / 2), name="COM_OUT_" + b.GetLayerName(layer))
    p3 = os.environ.get("P3V3_ZONE")        # vd "53,37,75,62": vung dong +3V3 mat duoi (tuy chon)
    if p3:
        gnd_zone(b, pcbnew.B_Cu, b.FindNet("+3V3"), rect=tuple(float(v) for v in p3.split(",")), prio=1,
                 name="P3V3_B.Cu")
    vias = stitch(b, "GND", (1.5, ISO_Y + ISO_W / 2 + 1.0, W - 1.5, H - 1.5))
    vias += stitch(b, "/16 ngo ra transistor/COM_OUT", (1.5, 1.5, W - 1.5, ISO_Y - ISO_W / 2 - 1.0))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    # bo via khau khong noi duoc ca 2 mat
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    removed = 0
    for v in vias:
        if len(conn.GetConnectedItems(v)) < 2:
            b.RemoveNative(v)
            removed += 1
    print("stitch vias:", len(vias) - removed)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    print("unrouted:", b.GetConnectivity().GetUnconnectedCount(True))
    pcbnew.SaveBoard(PCB, b)
    print("saved")


if __name__ == "__main__":
    main()
