"""Dong bo PCB da di day voi netlist moi (tuong tu 'Update PCB from Schematic' nhung giu duong day):
- xoa footprint khong con trong so do (tru lo bat vit H*)
- doi ten net (theo nhom chan), gan lai net cho pad / day / via / vung dong
- xoa day cua net khong con chan nao, xoa doan day treo
- cap nhat lien ket footprint <-> symbol, do lai vung dong

  kicad-cli sch export netlist --format kicadsexpr -o gen/plc.net kicad/PLC_STM32_Modbus.kicad_sch
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" gen/sync_pcb.py kicad/PLC_STM32_Modbus.kicad_pcb [gen/placed.kicad_pcb]
"""
import os
import sys
from collections import Counter, defaultdict

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kisch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def read_netlist():
    t = kisch.parse(open(os.path.join(HERE, "plc.net"), encoding="utf8").read())
    paths, node_net = {}, {}
    values = {}
    for c in kisch.find(t, "components")[1:]:
        sp = kisch.find(c, "sheetpath")
        paths[kisch.find(c, "ref")[1]] = kisch.find(sp, "tstamps")[1] + kisch.find(c, "tstamps")[1]
        values[kisch.find(c, "ref")[1]] = kisch.find(c, "value")[1]
        fpn = kisch.find(c, "footprint")
        values["#fp:" + kisch.find(c, "ref")[1]] = fpn[1] if fpn else ""
    paths["#values"] = values
    for n in kisch.find(t, "nets")[1:]:
        name = kisch.find(n, "name")[1]
        for x in kisch.findall(n, "node"):
            node_net[(kisch.find(x, "ref")[1], kisch.find(x, "pin")[1])] = name
    return paths, node_net


def sync(path, paths, node_net):
    b = pcbnew.LoadBoard(path)
    removed = []
    for fp in list(b.GetFootprints()):
        r = fp.GetReference()
        if (r not in paths or r == "#values") and not r.startswith("H"):
            removed.append(r)
            b.RemoveNative(fp)
    # doi footprint neu so do da doi (giu vi tri, huong, mat)
    FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
    swapped = []
    for fp in list(b.GetFootprints()):
        r = fp.GetReference()
        want = paths["#values"].get("#fp:" + r)
        have = "%s:%s" % (fp.GetFPID().GetLibNickname(), fp.GetFPID().GetLibItemName())
        if want and want != have:
            lib, name = want.split(":", 1)
            libdir = os.path.join(FPDIR, lib + ".pretty")
            if lib == "PLC":
                libdir = os.path.join(HERE, "..", "kicad", "PLC.pretty")
            nf = pcbnew.FootprintLoad(libdir, name)
            nf.SetFPID(pcbnew.LIB_ID(lib, name))
            nf.SetReference(r)
            nf.SetValue(fp.GetValue())
            nf.SetPosition(fp.GetPosition())
            if fp.IsFlipped():
                nf.Flip(nf.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            nf.SetOrientation(fp.GetOrientation())
            nf.Reference().SetTextSize(fp.Reference().GetTextSize())
            nf.Reference().SetTextThickness(fp.Reference().GetTextThickness())
            b.RemoveNative(fp)
            b.Add(nf)
            swapped.append((r, have, want))
    if swapped:
        print("  doi footprint:", swapped)
    # anh xa net cu -> net moi theo pad
    votes = defaultdict(Counter)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            new = node_net.get((fp.GetReference(), pad.GetNumber()))
            if new is not None and pad.GetNetname():
                votes[pad.GetNetname()][new] += 1
    rename = {old: c.most_common(1)[0][0] for old, c in votes.items()}

    def net(name):
        ni = b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, name)
            b.Add(ni)
        return ni

    for fp in b.GetFootprints():
        p = paths.get(fp.GetReference())
        if p:
            fp.SetPath(pcbnew.KIID_PATH(p))
            v = paths["#values"].get(fp.GetReference())
            if v and fp.GetValue() != v:
                fp.SetValue(v)
        for pad in fp.Pads():
            new = node_net.get((fp.GetReference(), pad.GetNumber()))
            if new is not None and new != pad.GetNetname():
                pad.SetNet(net(new))
    dropped = 0
    for t in list(b.GetTracks()):
        old = t.GetNetname()
        if old in rename:
            if rename[old] != old:
                t.SetNet(net(rename[old]))
        elif old:                      # net khong con chan nao (vd RS485_*)
            b.RemoveNative(t)
            dropped += 1
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.GetNetname() in rename:
            z.SetNet(net(rename[z.GetNetname()]))
    # xoa doan day treo
    for _ in range(6):
        b.BuildConnectivity()
        conn = b.GetConnectivity()
        dang = [t for t in b.GetTracks() if (t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False))]
        for t in dang:
            b.RemoveNative(t)
        dropped += len(dang)
        if not dang:
            break
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    renamed = sum(1 for o, n in rename.items() if o != n)
    print(path, "removed fp:", removed, "renamed nets:", renamed, "dropped tracks:", dropped)


def main():
    paths, node_net = read_netlist()
    for f in sys.argv[1:]:
        sync(f, paths, node_net)


if __name__ == "__main__":
    main()
