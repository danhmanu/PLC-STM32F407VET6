"""Dat module W5500 Lite (J401) o mep phai board, RJ45 huong ra ngoai; dat C401/C402/R401/R402 (mat duoi)
ngay duoi chan 3V3/INT/RST cua module; xoa day/via khac net cham vao pad moi.

  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/place_module.py kicad/PLC_STM32_Modbus.kicad_pcb [gen/placed.kicad_pcb]
"""
import math
import sys

import pcbnew

T, MM = pcbnew.ToMM, pcbnew.FromMM
OX, OY, W, H = 50.0, 50.0, 120.0, 90.0


def crt(fp):
    lay = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    bb = fp.GetCourtyard(lay).BBox()
    return T(bb.GetX()), T(bb.GetY()), T(bb.GetRight()), T(bb.GetBottom())


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pad_xy(fp, num):
    p = [q for q in fp.Pads() if q.GetNumber() == str(num)][0].GetPosition()
    return T(p.x), T(p.y)


def clear_copper(b, fp):
    """Xoa day/via khac net cham pad cua fp (pad xuyen lo: ca 2 lop)."""
    n = 0
    for pad in fp.Pads():
        pb = pad.GetBoundingBox()
        box = (T(pb.GetX()) - 0.4, T(pb.GetY()) - 0.4, T(pb.GetRight()) + 0.4, T(pb.GetBottom()) + 0.4)
        for t in list(b.GetTracks()):
            if t.GetNetname() == pad.GetNetname():
                continue
            if t.GetClass() == "PCB_TRACK" and not (pad.IsOnLayer(t.GetLayer())):
                continue
            tb = t.GetBoundingBox()
            if hit(box, (T(tb.GetX()), T(tb.GetY()), T(tb.GetRight()), T(tb.GetBottom()))):
                b.RemoveNative(t)
                n += 1
    return n


def place(path):
    b = pcbnew.LoadBoard(path)
    j = b.FindFootprintByReference("J401")
    if j.IsFlipped():
        j.Flip(j.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    # huong RJ45 (truc -y cua footprint) phai chi sang +x (mep phai board)
    best_rot, best_dx = None, None
    for rot in (0, 90, 180, 270):
        j.SetOrientationDegrees(rot)
        c = crt(j)
        pcx = sum(pad_xy(j, q)[0] for q in range(1, 13)) / 12
        dx = (c[0] + c[2]) / 2 - pcx          # courtyard lech ve phia RJ45 (nho ra 2.5mm)
        if best_dx is None or dx > best_dx:
            best_rot, best_dx = rot, dx
    j.SetOrientationDegrees(best_rot)
    others = []
    for fp in b.GetFootprints():
        if fp.GetReference() in ("J401", "C401", "C402", "R401", "R402"):
            continue
        tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())
        if fp.IsFlipped() and not tht:
            continue
        others.append(crt(fp))
    best = None
    for k in range(0, 400):
        y = 30 + k * 0.05                              # mep tren courtyard (toa do board)
        j.SetPosition(pcbnew.VECTOR2I(MM(OX + 100), MM(OY + y)))
        c = crt(j)
        j.SetPosition(pcbnew.VECTOR2I(j.GetPosition().x + MM(OX + W + 0.25 - c[2]),
                                      j.GetPosition().y + MM(OY + y - c[1])))
        c = crt(j)
        if any(hit(c, o) for o in others):
            continue
        d = abs(c[1] - (OY + 38.0))
        if best is None or d < best[0]:
            best = (d, j.GetPosition())
    if best is None:
        raise SystemExit("khong tim duoc cho cho module")
    j.SetPosition(best[1])
    print(path, "J401 rot", best_rot, "courtyard", [round(v - o, 2) for v, o in zip(crt(j), (OX, OY, OX, OY))])
    n = clear_copper(b, j)
    # tu/tro mat duoi, ben trong khung module, sat chan tuong ung
    cx = sum(pad_xy(j, q)[0] for q in range(1, 13)) / 12
    cy = sum(pad_xy(j, q)[1] for q in range(1, 13)) / 12
    for ref, pin, off in (("C401", 8, 3.2), ("C402", 9, 3.2), ("R401", 6, 3.2), ("R402", 11, 3.2)):
        fp = b.FindFootprintByReference(ref)
        if not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        px, py = pad_xy(j, pin)
        vx, vy = cx - px, cy - py                     # huong vao trong module
        if abs(vx) > abs(vy):
            vx, vy, rot = (1 if vx > 0 else -1), 0, 0
        else:
            vx, vy, rot = 0, (1 if vy > 0 else -1), 90
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pcbnew.VECTOR2I(MM(px + vx * off), MM(py + vy * off)))
        n += clear_copper(b, fp)
    for _ in range(8):
        b.BuildConnectivity()
        conn = b.GetConnectivity()
        dead = [t for t in b.GetTracks() if (t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False))
                or (t.GetClass() == "PCB_VIA" and len(conn.GetConnectedItems(t)) == 0)]
        for t in dead:
            b.RemoveNative(t)
        n += len(dead)
        if not dead:
            break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    print("  removed copper items:", n)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        place(f)
