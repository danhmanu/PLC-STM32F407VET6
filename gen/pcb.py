"""Tao PCB 2 lop 100x80mm tu netlist: dat linh kien, vien board, lo bat vit, net class.

Chay: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/pcb.py
"""
import os
import re
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "kicad")
PCB = os.path.join(OUTDIR, "PLC_STM32_Modbus.kicad_pcb")
NETFILE = os.path.join(HERE, "plc.net")
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

OX, OY = 50.0, 50.0          # vi tri goc board tren trang
W, H = 100.0, 80.0
MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# ------------------------------------------------------------------ netlist
def read_netlist():
    t = kisch.parse(open(NETFILE, encoding="utf8").read())
    comps = {}
    for c in kisch.find(t, "components")[1:]:
        ref = kisch.find(c, "ref")[1]
        sp = kisch.find(c, "sheetpath")
        comps[ref] = dict(value=kisch.find(c, "value")[1], fp=kisch.find(c, "footprint")[1],
                          path=kisch.find(sp, "tstamps")[1] + kisch.find(c, "tstamps")[1])
    nets = {}
    for n in kisch.find(t, "nets")[1:]:
        name = kisch.find(n, "name")[1]
        for x in kisch.findall(n, "node"):
            nets[(kisch.find(x, "ref")[1], kisch.find(x, "pin")[1])] = name
    return comps, nets


# ------------------------------------------------------------------ board
class Board:
    def __init__(self):
        self.b = pcbnew.NewBoard(PCB)
        self.b.SetCopperLayerCount(2)
        self.fps = {}
        self.netinfo = {}
        self.placed_refs = set()
        self.vias = []

    def net(self, name):
        if name not in self.netinfo:
            ni = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(ni)
            self.netinfo[name] = ni
        return self.netinfo[name]

    def add(self, ref, comp, nets):
        lib, name = comp["fp"].split(":", 1)
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(comp["value"])
        fp.SetPath(pcbnew.KIID_PATH(comp["path"]))
        self.b.Add(fp)
        for pad in fp.Pads():
            n = nets.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(self.net(n))
        rt = fp.Reference()
        rt.SetTextSize(pcbnew.VECTOR2I(MM(0.7), MM(0.7)))
        rt.SetTextThickness(MM(0.12))
        self.fps[ref] = fp
        return fp

    def add_hole(self, ref, x, y):
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, "MountingHole.pretty"), "MountingHole_3.2mm_M3")
        fp.SetFPID(pcbnew.LIB_ID("MountingHole", "MountingHole_3.2mm_M3"))
        fp.SetReference(ref)
        fp.Reference().SetVisible(False)
        fp.SetPosition(P(x, y))
        self.b.Add(fp)
        self.fps[ref] = fp

    def outline(self):
        pts = [(0, 0), (W, 0), (W, H), (0, H)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(self.b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(x1, y1))
            s.SetEnd(P(x2, y2))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(MM(0.1))
            self.b.Add(s)

    # -- placement helpers
    def bbox(self, ref):
        fp = self.fps[ref]
        layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
        cy = fp.GetCourtyard(layer)
        if cy.OutlineCount() == 0:
            bb = fp.GetBoundingBox(False)
        else:
            bb = cy.BBox()
        return (pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY,
                pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)

    def put(self, ref, x, y, rot=0, bottom=False):
        fp = self.fps[ref]
        if bottom and not fp.IsFlipped():
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))

    def put_bbox(self, ref, rot, left=None, right=None, top=None, bottom=None, bside=False):
        """Dat theo canh courtyard."""
        self.put(ref, 0, 0, rot, bside)
        x0, y0, x1, y1 = self.bbox(ref)
        dx = (left - x0) if left is not None else (right - x1) if right is not None else 0
        dy = (top - y0) if top is not None else (bottom - y1) if bottom is not None else 0
        self.put(ref, dx, dy, rot, bside)

    def pack(self, refs, x0, y0, x1, y1, bottom=False, gap=0.35, prefer_narrow=False, sort=False):
        """Xep hang (shelf packing) trong vung chu nhat. Tra ve danh sach ref khong vua."""
        cx, cy, row_h = x0, y0, 0.0
        failed = []
        if sort:
            def hkey(r):
                self.put(r, 0, 0, 0, bottom)
                a = self.bbox(r)
                return -min(a[2] - a[0], a[3] - a[1])
            refs = sorted(refs, key=hkey)
        for ref in refs:
            best = None
            for rot in (0, 90):
                self.put(ref, 0, 0, rot, bottom)
                bx0, by0, bx1, by1 = self.bbox(ref)
                w, h = bx1 - bx0, by1 - by0
                key = (w if prefer_narrow else h, w)
                if best is None or key < best[0]:
                    best = (key, rot, w, h, bx0, by0)
            _, rot, w, h, bx0, by0 = best
            if cx + w > x1:
                cx, cy, row_h = x0, cy + row_h + gap, 0.0
            if cy + h > y1:
                failed.append(ref)
                self.put(ref, -30, -30, 0, bottom)   # tam dat ngoai board
                continue
            self.put(ref, cx - bx0, cy - by0, rot, bottom)
            cx += w + gap
            row_h = max(row_h, h)
        return failed

    def free(self, ref):
        """True neu courtyard cua ref khong chong lan linh kien cung mat."""
        a = self.bbox(ref)
        side = self.fps[ref].IsFlipped()
        for r, fp in self.fps.items():
            if r == ref or r not in self.placed_refs:
                continue
            tht = len(fp.Pads()) and fp.Pads()[0].GetAttribute() == pcbnew.PAD_ATTRIB_PTH
            if fp.IsFlipped() != side and not tht:
                continue
            b = self.bbox(r)
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                return False
        for (vx, vy, r) in self.vias:
            m = r + 0.25
            if a[0] - m < vx < a[2] + m and a[1] - m < vy < a[3] + m:
                return False
        return 0 <= a[0] and 0 <= a[1] and a[2] <= W and a[3] <= H

    def under(self, ic, ref, pin, inset=2.3):
        """Dat tu (mat duoi) ngay duoi chan 'pin' cua IC, song song canh IC."""
        fp = self.fps[ic]
        c = fp.GetPosition()
        pad = [p for p in fp.Pads() if p.GetNumber() == str(pin)][0].GetPosition()
        dx, dy = pcbnew.ToMM(pad.x - c.x), pcbnew.ToMM(pad.y - c.y)
        cx, cy = pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY
        horiz_side = abs(dy) > abs(dx)          # chan nam canh tren/duoi
        nx, ny = (0, 1 if dy > 0 else -1) if horiz_side else (1 if dx > 0 else -1, 0)
        rot = 0 if horiz_side else 90
        for k in range(0, 8):
            for along in (0, 1.7, -1.7, 3.4, -3.4, 5.1, -5.1):
                d = inset - 1.75 * k
                x = cx + dx - nx * d + (along if horiz_side else 0)
                y = cy + dy - ny * d + (0 if horiz_side else along)
                self.put(ref, x, y, rot, bottom=True)
                if self.free(ref):
                    self.placed_refs.add(ref)
                    return True
        return False

    def overlaps(self):
        items = [(r, self.bbox(r), self.fps[r].IsFlipped()) for r in self.fps]
        bad = []
        for i in range(len(items)):
            r1, a, s1 = items[i]
            for j in range(i + 1, len(items)):
                r2, b, s2 = items[j]
                tht = any(self.fps[r].Pads()[0].GetAttribute() == pcbnew.PAD_ATTRIB_PTH for r in (r1, r2)
                          if len(self.fps[r].Pads()))
                if s1 != s2 and not tht:
                    continue
                if a[0] < b[2] - 0.01 and b[0] < a[2] - 0.01 and a[1] < b[3] - 0.01 and b[1] < a[3] - 0.01:
                    bad.append((r1, r2))
        out = []
        for r, (x0, y0, x1, y1), _ in items:
            if r.startswith("J4") or r.startswith("J3"):
                continue   # dau noi mep board duoc phep nho ra
            if x0 < -0.01 or y0 < -0.01 or x1 > W + 0.01 or y1 > H + 0.01:
                out.append(r)
        return bad, out



# ------------------------------------------------------------------ power fan-out (QFP)
def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5


def _segseg(a, b, c, d):
    return min(_seg_dist(a, c, d), _seg_dist(b, c, d), _seg_dist(c, a, b), _seg_dist(d, a, b))


FAN_NETS = {"+3V3", "GND", "+3.3VA"}
FAN_NETS_LOCAL = ("VCAP1", "VCAP2", "VREF_3V0", "ETH_TOCAP", "ETH_1V2")


def fanout(B, ref, depth, via_d=0.6, drill=0.3, clr=0.199):
    """Moi chan nguon cua QFP: day ngan vao duoi than IC + via xuong mat duoi (khoa lai)."""
    fp = B.fps[ref]
    c = fp.GetPosition()
    cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
    pads = []
    for pad in fp.Pads():
        pp = pad.GetPosition()
        px, py = pcbnew.ToMM(pp.x) - cx, pcbnew.ToMM(pp.y) - cy
        pads.append((pad, px, py, pad.GetNetname()))
    obst_segs = []      # (a, b, halfwidth, net)
    obst_vias = []      # (x, y, r, net)
    for ofp in B.b.GetFootprints():          # pad cua linh kien khac gan IC (mat tren)
        if ofp.GetReference() == ref:
            continue
        for op in ofp.Pads():
            if not op.IsOnLayer(pcbnew.F_Cu):
                continue
            q = op.GetPosition()
            qx, qy = pcbnew.ToMM(q.x) - cx, pcbnew.ToMM(q.y) - cy
            if abs(qx) > 14 or abs(qy) > 14:
                continue
            sz = op.GetSize(pcbnew.F_Cu)
            hx, hy = pcbnew.ToMM(sz.x) / 2, pcbnew.ToMM(sz.y) / 2
            if hx > hy:
                obst_segs.append(((qx - hx + hy, qy), (qx + hx - hy, qy), hy, op.GetNetname()))
            else:
                obst_segs.append(((qx, qy - hy + hx), (qx, qy + hy - hx), hx, op.GetNetname()))
    for pad, px, py, net in pads:   # pad ~ doan thang theo chieu dai (1.6 x 0.3)
        if abs(px) > abs(py):
            obst_segs.append(((px - 0.65, py), (px + 0.65, py), 0.15, net))
        else:
            obst_segs.append(((px, py - 0.65), (px, py + 0.65), 0.15, net))

    def ok_seg(a, b, hw, net):
        for (c1, c2, h2, n) in obst_segs:
            if n != net and _segseg(a, b, c1, c2) < hw + h2 + clr:
                return False
        for (vx, vy, r, n) in obst_vias:
            if n != net and _seg_dist((vx, vy), a, b) < hw + r + clr:
                return False
        return True

    def ok_via(x, y, net):
        r = via_d / 2
        for (vx, vy, rr, n) in obst_vias:
            if ((vx - x) ** 2 + (vy - y) ** 2) ** 0.5 < r + rr + (clr if n != net else 0.15):
                return False
        for (c1, c2, h2, n) in obst_segs:
            if n != net and _seg_dist((x, y), c1, c2) < r + h2 + clr:
                return False
        return True

    made = 0
    # chan sat goc xu ly truoc, va uu tien dich vao giua canh
    pads.sort(key=lambda t: -min(abs(t[1]), abs(t[2])))
    for pad, px, py, net in pads:
        short = net.split("/")[-1]
        if not (net in FAN_NETS or short in FAN_NETS_LOCAL):
            continue
        horiz = abs(px) > abs(py)                 # chan o canh trai/phai
        sgn = 1 if (px if horiz else py) > 0 else -1
        along0 = py if horiz else px
        dist = abs(px if horiz else py)
        w = 0.3 if net in FAN_NETS else 0.2

        def P_(d, a):
            return (sgn * d, a) if horiz else (a, sgn * d)

        done_pad = False
        for dep in (depth, depth - 1.1, depth - 2.2):
            tc = -1 if along0 > 0 else 1          # huong vao giua canh
            for off in (0, 0.5 * tc, 1.0 * tc, -0.5 * tc, 1.5 * tc, -1.0 * tc, 2.0 * tc, 2.5 * tc, -1.5 * tc):
                al = along0 + off
                if abs(al) > dep - 0.4:
                    continue
                d1 = dist - 1.25
                start, knee, vpt = P_(dist - 0.7, along0), P_(d1, along0), P_(dep, al)
                segs = [(start, knee), (knee, vpt)] if off else [(start, vpt)]
                if not ok_via(*vpt, net):
                    continue
                if not all(ok_seg(a, b, w / 2, net) for a, b in segs):
                    continue
                for a, b in segs:
                    t = pcbnew.PCB_TRACK(B.b)
                    t.SetStart(pcbnew.VECTOR2I(MM(cx + a[0]), MM(cy + a[1])))
                    t.SetEnd(pcbnew.VECTOR2I(MM(cx + b[0]), MM(cy + b[1])))
                    t.SetWidth(MM(w))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(pad.GetNet())
                    t.SetLocked(True)
                    B.b.Add(t)
                    obst_segs.append((a, b, w / 2, net))
                v = pcbnew.PCB_VIA(B.b)
                v.SetPosition(pcbnew.VECTOR2I(MM(cx + vpt[0]), MM(cy + vpt[1])))
                v.SetWidth(MM(via_d))
                v.SetDrill(MM(drill))
                v.SetNet(pad.GetNet())
                v.SetLocked(True)
                B.b.Add(v)
                obst_vias.append((vpt[0], vpt[1], via_d / 2, net))
                B.vias.append((cx - OX + vpt[0], cy - OY + vpt[1], via_d / 2))
                made += 1
                done_pad = True
                break
            if done_pad:
                break
        if not done_pad:                       # du phong: di ra ngoai hang chan roi xuong via
            for dout in (1.65, 2.2):
                start, vpt = P_(dist + 0.7, along0), P_(dist + dout, along0)
                if ok_via(*vpt, net) and ok_seg(start, vpt, w / 2, net):
                    t = pcbnew.PCB_TRACK(B.b)
                    t.SetStart(pcbnew.VECTOR2I(MM(cx + start[0]), MM(cy + start[1])))
                    t.SetEnd(pcbnew.VECTOR2I(MM(cx + vpt[0]), MM(cy + vpt[1])))
                    t.SetWidth(MM(w))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(pad.GetNet())
                    t.SetLocked(True)
                    B.b.Add(t)
                    obst_segs.append((start, vpt, w / 2, net))
                    v = pcbnew.PCB_VIA(B.b)
                    v.SetPosition(pcbnew.VECTOR2I(MM(cx + vpt[0]), MM(cy + vpt[1])))
                    v.SetWidth(MM(via_d))
                    v.SetDrill(MM(drill))
                    v.SetNet(pad.GetNet())
                    v.SetLocked(True)
                    B.b.Add(v)
                    obst_vias.append((vpt[0], vpt[1], via_d / 2, net))
                    B.vias.append((cx - OX + vpt[0], cy - OY + vpt[1], via_d / 2))
                    made += 1
                    done_pad = True
                    break
        if not done_pad:
            print("  fanout skip", ref, pad.GetNumber(), net)
    return made


def edge_keepout(B, w=0.45):
    for (x0, y0, x1, y1) in [(0, 0, W, w), (0, H - w, W, H), (0, 0, w, H), (W - w, 0, W, H)]:
        z = pcbnew.ZONE(B.b)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask(2))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            ol.Append(MM(OX + x), MM(OY + y))
        B.b.Add(z)


# ------------------------------------------------------------------ layout
def layout(B, comps):
    refs = set(comps)

    def R(prefix, lo, hi):
        return [r for r in sorted(refs, key=lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s))))
                if re.match(prefix + r"\d+$", r) and lo <= int(re.sub(r"\D", "", r)) <= hi]

    placed = set()

    def done(lst):
        placed.update(lst)
        B.placed_refs.update(lst)
        return lst

    # mounting holes
    for i, (x, y) in enumerate([(3.5, 3.5), (96.5, 3.5), (3.5, 76.5), (96.5, 76.5)]):
        B.add_hole(f"H{i + 1}", x, y)

    # ---- terminal blocks (wire entry = +y cua footprint)
    B.put("J501", 45.5, 4.2, 180)
    B.put("J502", 86.5, 4.2, 180)
    B.put("J701", 9.5, 80 - 4.2, 0)
    B.put("J703", 49.5, 80 - 4.2, 0)
    B.put("J402", 73.5, 80 - 4.2, 0)
    B.put("J101", 86.2, 80 - 4.2, 0)
    done(["J501", "J502", "J701", "J703", "J402", "J101"])

    # ---- 16 output channels
    for n in range(1, 17):
        cx = 10.5 + 5.25 * (n - 1)
        k = n - 1
        B.put(f"D{502 + 2 * k}", cx - 0.9, 10.6, 90)            # LED
        B.put(f"R{504 + 4 * k}", cx + 0.9, 10.6, 90)            # R_led
        B.put(f"D{501 + 2 * k}", cx - 1.0, 15.1, 90)            # flyback
        B.put(f"R{502 + 4 * k}", cx + 1.5, 15.1, 90)            # R_c
        B.put(f"Q{500 + n}", cx - 0.85, 20.0, 90)                # MOSFET
        B.put(f"R{503 + 4 * k}", cx + 1.85, 20.0, 90)           # R_g
        done([f"D{502 + 2 * k}", f"R{504 + 4 * k}", f"D{501 + 2 * k}", f"R{502 + 4 * k}", f"Q{500 + n}",
              f"R{503 + 4 * k}"])
    opto_x = [10.5 + 5.25 * (4 * g + 1.5) for g in range(4)]
    for g in range(4):
        B.put(f"U{501 + g}", opto_x[g], 27.6, 90)
    done([f"U{501 + g}" for g in range(4)])
    gaps = [(7.2, 12.8), (23.9, 33.8), (44.9, 54.8), (65.9, 75.8), (86.9, 92.9)]
    B.put_bbox("D533", 90, left=gaps[0][0], top=23.3)
    done(["D533"])
    for g in range(4):
        x0, x1 = gaps[g + 1]
        rin = [f"R{501 + 4 * (4 * g + i)}" for i in range(4)]
        extra = ["C501"] if g == 0 else ["C502"] if g == 1 else []
        f = B.pack(rin + extra, x0, 23.3, x1, 32.2, prefer_narrow=True)
        assert not f, f
        done(rin + extra)

    # ---- edge connectors
    B.put_bbox("J401", 90, right=100.6, top=33.0)               # RJ45 mo ra phai
    B.put_bbox("J301", 270, left=-0.6, top=34.0)                # USB-C mo ra trai
    done(["J401", "J301"])

    # ---- MCU & W5500
    B.put("U200", 35.0, 43.6, 0)
    B.put("U400", 61.0, 43.0, 180)          # phia PHY huong ve RJ45
    done(["U200", "U400"])
    done(["H1", "H2", "H3", "H4"])
    B.put_bbox("J702", 90, right=47.0, top=53.2)
    done(["J702"])

    fails = []
    # thach anh MCU sat chan PH0/PH1 (canh trai)
    B.put_bbox("Y201", 90, right=B.bbox("U200")[0] - 0.3, top=40.0)
    done(["Y201"])
    yb = B.bbox("Y201")
    fails += B.pack(["C201", "C202"], yb[0] - 1.8, yb[3] + 0.3, yb[2], yb[3] + 5.0, prefer_narrow=True)
    done(["C201", "C202"])

    # USB / CH340 / auto-boot  (trai)
    usb = R("U", 301, 302) + R("Q", 301, 303) + R("R", 301, 308)
    rest = B.pack(usb, 9.8, 32.6, B.bbox("Y201")[0] - 0.4, 52.4)
    fails += B.pack(rest, 0.3, 45.6, 9.6, 52.4)
    done(usb)
    usb_bot = ["J201"] + R("C", 301, 304) + R("F", 301, 301)
    fails += B.pack(usb_bot, B.bbox("J301")[2] + 0.6, 33.5, 23.5, 52.0, bottom=True, sort=True)
    done(usb_bot)

    # nut nhan + LED trang thai: giua MCU va W5500, phia tren (chua kenh SPI o duoi)
    ui = ["SW201", "SW202", "D201", "R203", "D202", "R204"]
    fails += B.pack(ui, B.bbox("U200")[2] + 0.3, 32.6, B.bbox("U400")[0] - 0.2, 42.6, sort=True, gap=0.25)
    done(ui)
    # duoi MCU (ben phai header J702)
    below = ["JP301", "U201", "R201", "R202", "D103", "D107", "FB102"]
    fails += B.pack(below, 1.0, 53.3, B.bbox("J702")[0] - 0.5, 59.8)
    done(below)

    # W5500 group (giua U400 va RJ45)
    rj_left = B.bbox("J401")[0] - 0.3
    eth_top = ["Y401", "C403", "C404", "R401", "R402", "R403", "R404", "R405", "R406", "R407",
               "C411", "C413", "R408", "R409"]
    fails += B.pack(eth_top, B.bbox("U400")[2] + 0.3, 33.2, rj_left, 53.0)
    done(eth_top)

    # analog: header + top protection parts
    ana_top = [x for k in range(10) for x in (f"F{701 + k}", f"D{701 + k}", f"R{701 + 4 * k}")] + ["F711"]
    fails += B.pack(ana_top, 0.5, 60.6, 47.0, 71.3)
    done(ana_top)
    ana_bot = [f"R{702 + 4 * k + j}" for k in range(10) for j in range(3)] + R("C", 701, 710)
    ana_bot = [x for k in range(10) for x in (f"R{702 + 4 * k}", f"R{703 + 4 * k}", f"R{704 + 4 * k}", f"C{701 + k}")]
    fails += B.pack(ana_bot, 1.0, B.bbox("J702")[3] + 0.4, 47.0, 71.0, bottom=True)
    done(ana_bot)

    # RS485
    rs = ["U401", "D401", "D402", "JP401", "R410", "R411", "R412", "R413"]
    fails += B.pack(rs, 47.6, 53.6, 58.6, 71.3, sort=True)
    done(rs)

    # power
    pw_top = ["L101", "F101", "D101", "D102", "C101", "C102", "FB101", "C103", "C105", "U101", "D104",
              "C108", "D105", "D106", "U102", "L102", "F711"]
    pw_top = [r for r in pw_top if r in refs and r not in placed]
    fails += B.pack(pw_top, 59.0, 53.6, 99.6, 71.3, sort=True)
    done(pw_top)
    pw_bot = [r for r in ["C104", "C106", "C107", "C112", "C114", "R101", "R102", "C110", "C111", "C113", "C109"] if r in refs]
    fails += B.pack(pw_bot, 64.0, 54.0, 99.0, 71.0, bottom=True)
    done(pw_bot)

    # fan-out nguon cho QFP (sau khi da dat linh kien mat tren), roi moi dat tu mat duoi
    print("fanout U200:", fanout(B, "U200", depth=5.7))
    print("fanout U400:", fanout(B, "U400", depth=2.4))
    # tu loc duoi MCU (mat duoi), moi tu sat chan nguon cua no
    for cap, pin in [("C203", 11), ("C204", 19), ("C205", 28), ("C206", 50), ("C207", 75), ("C208", 100),
                     ("C210", 22), ("C211", 22), ("C214", 21), ("C215", 21), ("C212", 49), ("C213", 73),
                     ("C209", 28), ("C216", 14)]:
        if not B.under("U200", cap, pin, inset=0.0):
            fails.append(cap)
        done([cap])
    # tu loc duoi W5500
    for cap, pin in [("C405", 4), ("C406", 8), ("C407", 11), ("C408", 15), ("C409", 17), ("C414", 21),
                     ("C415", 28), ("C410", 28), ("C412", 2), ("C402", 22), ("C401", 20)]:
        if not B.under("U400", cap, pin, inset=0.0):
            fails.append(cap)
        done([cap])

    left = sorted(refs - placed)
    return fails, left


def netclasses(B):
    ns = B.b.GetDesignSettings().m_NetSettings
    dflt = ns.GetDefaultNetclass()
    dflt.SetTrackWidth(MM(0.2))
    dflt.SetClearance(MM(0.2))
    dflt.SetViaDiameter(MM(0.6))
    dflt.SetViaDrill(MM(0.3))

    def mk(name, w, clr, pats):
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(MM(w))
        nc.SetClearance(MM(clr))
        nc.SetViaDiameter(MM(0.8))
        nc.SetViaDrill(MM(0.4))
        ns.SetNetclass(name, nc)
        for p in pats:
            ns.SetNetclassPatternAssignment(p, name)

    mk("Power", 0.8, 0.2, ["*/VIN_*", "*/GND_IN", "+24V", "*/BUCK_SW", "+5V", "*/+5V_BUCK", "*/V24_*",
                            "*/COM_OUT", "*/Y?", "*/Y??", "VBUS", "*/VBUS_C"])
    mk("Supply", 0.3, 0.2, ["+3V3", "+3.3VA", "GND"])
    ns.RecomputeEffectiveNetclasses()


def main():
    comps, nets = read_netlist()
    B = Board()
    B.outline()
    for ref, c in comps.items():
        B.add(ref, c, nets)
    fails, left = layout(B, comps)
    netclasses(B)
    ds = B.b.GetDesignSettings()
    ds.m_CopperEdgeClearance = MM(0.3)
    ds.m_HoleClearance = MM(0.18)
    edge_keepout(B)
    bad, out = B.overlaps()
    print("pack failed:", fails)
    print("not placed:", left)
    print("overlaps:", len(bad), bad[:40])
    print("outside board:", out)
    # title on silkscreen
    t = pcbnew.PCB_TEXT(B.b)
    t.SetText("PLC STM32F407 MODBUS TCP - 16DO/10AI  v1.0")
    t.SetPosition(P(50, 18.0))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(1.2), MM(1.2)))
    B.b.Add(t)
    pcbnew.SaveBoard(PCB, B.b)
    import shutil
    shutil.copy(PCB, os.path.join(HERE, "placed.kicad_pcb"))
    print("saved", PCB)


if __name__ == "__main__":
    main()
