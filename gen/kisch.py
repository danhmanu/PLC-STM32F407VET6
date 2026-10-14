"""Tiny KiCad schematic writer: S-expression I/O, symbol library loader, sheet builder.

Mọi kết nối được tạo bằng "dây ngắn + nhãn" (label / global label / power symbol),
nên netlist đúng tuyệt đối và ERC kiểm tra được.
"""
import math
import os
import re
import uuid as _uuid

KICAD_SYM_DIR = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
PROJECT = "PLC_STM32_Modbus"
GRID = 1.27


# ----------------------------------------------------------------- S-expr
class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif t[0] == '"':
            cur.append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            cur.append(Sym(t))
    return cur[0]


def fmt_num(v):
    if isinstance(v, float):
        s = ("%.4f" % v).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def dump(node, ind=0):
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return str(node)
        if isinstance(node, (int, float)):
            return fmt_num(node)
        return '"' + str(node).replace("\\", "\\\\").replace('"', '\\"') + '"'
    simple = all(not isinstance(x, list) for x in node)
    if simple:
        return "(" + " ".join(dump(x) for x in node) + ")"
    parts = []
    head = []
    for x in node:
        if isinstance(x, list):
            break
        head.append(dump(x))
    out = "\t" * ind + "(" + " ".join(head)
    for x in node[len(head):]:
        if isinstance(x, list):
            out += "\n" + ("\t" * (ind + 1) + dump(x) if all(not isinstance(y, list) for y in x)
                           else dump(x, ind + 1))
        else:
            out += " " + dump(x)
    out += "\n" + "\t" * ind + ")"
    return out


def S(*a):
    return [Sym(a[0])] + list(a[1:])


def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def uid():
    return str(_uuid.uuid4())


# ----------------------------------------------------------------- library
_libcache = {}


def _load_lib(lib):
    if lib not in _libcache:
        path = os.path.join(KICAD_SYM_DIR, lib + ".kicad_sym")
        tree = parse(open(path, encoding="utf8").read())
        _libcache[lib] = {x[1]: x for x in findall(tree, "symbol")}
    return _libcache[lib]


def _rename_units(node, old, new):
    for x in node:
        if isinstance(x, list) and x and x[0] == "symbol" and isinstance(x[1], str):
            if x[1].startswith(old + "_"):
                x[1] = new + x[1][len(old):]


class LibSymbol:
    def __init__(self, lib, name):
        import copy
        syms = _load_lib(lib)
        node = copy.deepcopy(syms[name])
        ext = find(node, "extends")
        if ext is not None:
            parent = LibSymbol(lib, ext[1]).node  # flattened parent
            parent = copy.deepcopy(parent)
            # replace parent properties by child properties
            child_props = {p[1]: p for p in findall(node, "property")}
            newnode = [Sym("symbol"), name]
            for x in parent[2:]:
                if isinstance(x, list) and x[0] == "property" and x[1] in child_props:
                    newnode.append(child_props.pop(x[1]))
                else:
                    newnode.append(x)
            for p in child_props.values():
                newnode.append(p)
            _rename_units(newnode, ext[1], name)
            node = newnode
        node[1] = name
        self.node = node
        self.lib_id = lib + ":" + name
        self.pins = {}   # number -> list of dict (may have duplicates over units)
        self.power = find(node, "power") is not None
        for sub in findall(node, "symbol"):
            m = re.match(r".*_(\d+)_(\d+)$", sub[1])
            unit = int(m.group(1)) if m else 0
            for p in findall(sub, "pin"):
                at = find(p, "at")
                num = find(p, "number")[1]
                nm = find(p, "name")[1]
                self.pins.setdefault(num, []).append(dict(
                    unit=unit, x=float(at[1]), y=float(at[2]), ang=float(at[3]),
                    name=nm, etype=str(p[1])))
        self.units = max([d["unit"] for v in self.pins.values() for d in v] + [1])

    def embedded(self):
        import copy
        n = copy.deepcopy(self.node)
        n[1] = self.lib_id
        return n

    def prop(self, name):
        for p in findall(self.node, "property"):
            if p[1] == name:
                return p
        return None


_symcache = {}


def libsym(lib_id):
    if lib_id not in _symcache:
        lib, name = lib_id.split(":", 1)
        _symcache[lib_id] = LibSymbol(lib, name)
    return _symcache[lib_id]


# ----------------------------------------------------------------- geometry
def xform(x, y, rot, mirror=None):
    """lib coords (y up) -> sheet offset (y down)."""
    if mirror == "y":
        x = -x
    elif mirror == "x":
        y = -y
    r = math.radians(rot)
    xr = x * math.cos(r) - y * math.sin(r)
    yr = x * math.sin(r) + y * math.cos(r)
    return xr, -yr


def snap(v):
    return round(round(v / GRID) * GRID, 4)


# ----------------------------------------------------------------- sheet
POWER_NETS = {
    "GND": "power:GND", "GNDA": "power:GNDA", "+3V3": "power:+3V3", "+5V": "power:+5V",
    "+24V": "power:+24V", "+3.3VA": "power:+3.3VA", "VBUS": "power:VBUS",
}


class Placed:
    def __init__(self, ref):
        self.ref = ref
        self.pins = {}

    def p(self, num):
        return self.pins[str(num)]


_pwr_counter = [0]


class Sheet:
    def __init__(self, name, filename, title, paper="A3"):
        self.name = name
        self.filename = filename
        self.title = title
        self.paper = paper
        self.uuid = uid()
        self.items = []          # top-level nodes (wires, labels, symbols...)
        self.symbols = []        # (node, ref) for later instance path patch
        self.libs = {}
        self.nets_used = []      # (net, x, y, ang) label requests
        self.pwr_count = 0
        self.texts = []
        self.pin_points = []
        self.wire_ends = []

    # -- helpers
    def _use(self, ls):
        self.libs[ls.lib_id] = ls

    def path(self, *pts, label=None):
        """Wire through points; tuples (x,y). Optional label at last point (outward dir of last seg)."""
        pts = [(round(a, 4), round(b, 4)) for a, b in pts]
        for (a, b), (c, d) in zip(pts, pts[1:]):
            if (a, b) != (c, d):
                self.wire(a, b, c, d)
        return pts[-1]

    def label_at(self, net, x, y, outward):
        self.net_at(net, round(x, 4), round(y, 4), outward)

    def wire(self, x1, y1, x2, y2):
        self.wire_ends += [(round(x1, 4), round(y1, 4)), (round(x2, 4), round(y2, 4))]
        self.items.append(S("wire", S("pts", S("xy", x1, y1), S("xy", x2, y2)),
                            S("stroke", S("width", 0), S("type", Sym("solid"))), S("uuid", uid())))

    def text(self, x, y, s, size=2.0):
        self.items.append(S("text", s, S("exclude_from_sim", Sym("no")), S("at", x, y, 0),
                            S("effects", S("font", S("size", size, size)), S("justify", Sym("left"), Sym("bottom"))),
                            S("uuid", uid())))

    def no_connect(self, x, y):
        self.items.append(S("no_connect", S("at", x, y), S("uuid", uid())))

    def place(self, lib_id, ref, value, x, y, rot=0, conns=None, unit=1, footprint=None,
              mirror=None, stub=2.54, fields=None, hide_value=False):
        """Place a symbol. conns: {pin_number: net}. net None/'NC' -> no-connect flag.
        Pins not listed in conns are left untouched (ERC will report them)."""
        ls = libsym(lib_id)
        self._use(ls)
        x, y = snap(x), snap(y)
        node = S("symbol", S("lib_id", ls.lib_id), S("at", x, y, rot))
        if mirror:
            node.append(S("mirror", Sym(mirror)))
        node += [S("unit", unit), S("exclude_from_sim", Sym("no")), S("in_bom", Sym("no" if ls.power else "yes")),
                 S("on_board", Sym("no" if ls.power else "yes")), S("dnp", Sym("no")), S("uuid", uid())]
        pts = [(d["x"], d["y"]) for v in ls.pins.values() for d in v]
        small = (not ls.power) and len(ls.pins) <= 4 and all(abs(a) <= 7.62 and abs(b) <= 7.62 for a, b in pts)
        tp = [xform(a, b, rot, mirror) for a, b in pts]
        horiz = len(tp) > 1 and abs(tp[0][0] - tp[-1][0]) > abs(tp[0][1] - tp[-1][1])
        if len(ls.pins) == 3:     # transistors: text to the right
            horiz = False
        props = {"Reference": ref, "Value": value}
        if footprint is not None:
            props["Footprint"] = footprint
        if fields:
            props.update(fields)
        for p in findall(ls.node, "property"):
            if isinstance(p[1], Sym) or str(p[1]).startswith("ki_"):
                continue   # private / internal library fields are not copied to instances
            pname = p[1]
            pval = props.pop(pname, p[2])
            at = find(p, "at")
            dx, dy = xform(float(at[1]), float(at[2]), rot, mirror)
            just = None
            fang = 90 if rot in (90, 270) else 0     # KiCad shows field angle + symbol rotation
            if small and pname in ("Reference", "Value"):
                k = 0 if pname == "Reference" else 1
                txt = str(pval)
                if horiz:                 # displayed horizontal: ref above, value below
                    dx, dy = 0, (-2.4 if k == 0 else 2.4)
                else:                     # displayed vertical: text to the right (centered)
                    dx, dy = (4.6 if len(ls.pins) == 3 else 1.6) + 0.36 * len(txt), (-1.0 if k == 0 else 1.0)
            eff = find(p, "effects")
            hide = find(p, "hide") is not None or (eff is not None and find(eff, "hide") is not None)
            if pname == "Value" and hide_value:
                hide = True
            pn = S("property", pname, pval, S("at", round(x + dx, 4), round(y + dy, 4), fang))
            if hide:
                pn.append(S("hide", Sym("yes")))
            fsz = 1.0 if small else 1.27
            eff_n = S("effects", S("font", S("size", fsz, fsz)))
            if just:
                eff_n.append(S("justify", Sym(just)))
            pn.append(eff_n)
            node.append(pn)
        for pname, pval in props.items():
            node.append(S("property", pname, pval, S("at", x, y, 0), S("hide", Sym("yes")),
                          S("effects", S("font", S("size", 1.27, 1.27)))))
        for num, lst in ls.pins.items():
            if any(d["unit"] in (0, unit) for d in lst):
                node.append(S("pin", num, S("uuid", uid())))
        inst = S("instances", S("project", PROJECT, S("path", "__PATH__", S("reference", ref), S("unit", unit))))
        node.append(inst)
        self.items.append(node)
        self.symbols.append(node)
        handle = Placed(ref)
        for num, lst in ls.pins.items():
            for d in lst:
                if d["unit"] in (0, unit):
                    dx, dy = xform(d["x"], d["y"], rot, mirror)
                    pt = (round(x + dx, 4), round(y + dy, 4))
                    handle.pins.setdefault(num, pt)
                    self.pin_points.append(pt)
        # connections
        done = set()
        for num, net in (conns or {}).items():
            cands = [d for d in ls.pins[str(num)] if d["unit"] in (0, unit)]
            if not cands:
                raise KeyError(f"{ref}: pin {num} not in unit {unit}")
            d = cands[0]
            dx, dy = xform(d["x"], d["y"], rot, mirror)
            px, py = round(x + dx, 4), round(y + dy, 4)
            # pin direction (towards body) in sheet coords
            bx, by = xform(math.cos(math.radians(d["ang"])), math.sin(math.radians(d["ang"])), rot, mirror)
            ox, oy = -round(bx), -round(by)   # outward
            if net is None:
                continue
            if (px, py) in done:
                continue
            done.add((px, py))
            if net == "NC":
                self.no_connect(px, py)
                continue
            ex, ey = round(px + ox * stub, 4), round(py + oy * stub, 4)
            if stub:
                self.wire(px, py, ex, ey)
            self.net_at(net, ex, ey, (ox, oy))
        return handle

    def net_at(self, net, x, y, outward):
        ox, oy = outward
        if net in POWER_NETS:
            ls = libsym(POWER_NETS[net])
            self._use(ls)
            ground = net.startswith("GND")
            # GND body points down (0,1); +V body points up (0,-1). rotate to outward.
            base = (0, 1) if ground else (0, -1)
            rot = {((0, 1), (0, 1)): 0, ((0, 1), (1, 0)): 90, ((0, 1), (0, -1)): 180, ((0, 1), (-1, 0)): 270,
                   ((0, -1), (0, -1)): 0, ((0, -1), (-1, 0)): 90, ((0, -1), (0, 1)): 180, ((0, -1), (1, 0)): 270}[(base, (ox, oy))]
            self.pwr_count += 1
            _pwr_counter[0] += 1
            ref = "#PWR%04d" % _pwr_counter[0]
            node = S("symbol", S("lib_id", ls.lib_id), S("at", x, y, rot), S("unit", 1),
                     S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
                     S("dnp", Sym("no")), S("uuid", uid()))
            node.append(S("property", "Reference", ref, S("at", x, y, 0), S("hide", Sym("yes")),
                          S("effects", S("font", S("size", 1.27, 1.27)))))
            vx, vy = x + ox * 3.2, y + oy * 3.2
            node.append(S("property", "Value", net, S("at", round(vx, 3), round(vy, 3), 0),
                          S("effects", S("font", S("size", 1.0, 1.0)))))
            for pname in ("Footprint", "Datasheet", "Description"):
                node.append(S("property", pname, "", S("at", x, y, 0), S("hide", Sym("yes")),
                              S("effects", S("font", S("size", 1.27, 1.27)))))
            node.append(S("pin", "1", S("uuid", uid())))
            node.append(S("instances", S("project", PROJECT, S("path", "__PATH__", S("reference", ref), S("unit", 1)))))
            self.items.append(node)
            self.symbols.append(node)
            return
        ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[(ox, oy)]
        self.nets_used.append((net, x, y, ang))

    def add_junctions(self):
        from collections import Counter
        c = Counter(self.wire_ends)
        pins = Counter(self.pin_points)
        for pt, n in c.items():
            if n + pins.get(pt, 0) >= 3:
                self.items.append(S("junction", S("at", pt[0], pt[1]), S("diameter", 0),
                                    S("color", 0, 0, 0, 0), S("uuid", uid())))

    def finalize_labels(self, global_nets):
        self.add_junctions()
        for net, x, y, ang in self.nets_used:
            just = Sym("left") if ang in (0, 90) else Sym("right")
            if net in global_nets:
                self.items.append(S("global_label", net, S("shape", Sym("passive")), S("at", x, y, ang),
                                    S("fields_autoplaced", Sym("yes")),
                                    S("effects", S("font", S("size", 1.0, 1.0)), S("justify", just)),
                                    S("uuid", uid()),
                                    S("property", "Intersheetrefs", "${INTERSHEET_REFS}", S("at", x, y, 0),
                                      S("hide", Sym("yes")),
                                      S("effects", S("font", S("size", 1.27, 1.27)), S("justify", just)))))
            else:
                self.items.append(S("label", net, S("at", x, y, ang), S("fields_autoplaced", Sym("yes")),
                                    S("effects", S("font", S("size", 1.0, 1.0)), S("justify", just, Sym("bottom"))),
                                    S("uuid", uid())))

    def to_tree(self, root_uuid, page, extra=None):
        path = "/" + root_uuid if self is extra.get("root") else f"/{root_uuid}/{extra['sheet_uuid'][self.name]}"
        for n in self.symbols:
            inst = find(n, "instances")
            find(find(inst, "project"), "path")[1] = path
        tree = S("kicad_sch", S("version", 20250610), S("generator", "eeschema"), S("generator_version", "10.0"),
                 S("uuid", self.uuid), S("paper", self.paper),
                 S("title_block", S("title", self.title), S("date", "2026-10-14"), S("rev", "1.0"),
                   S("company", "PLC STM32F407 + W5500 Modbus TCP"), S("comment", 1, f"Sheet: {self.name}")))
        tree.append([Sym("lib_symbols")] + [ls.embedded() for ls in self.libs.values()])
        tree += self.items
        if extra.get("tail"):
            tree += extra["tail"]
        tree.append(S("embedded_fonts", Sym("no")))
        return tree


def write_project(outdir, root, sheets):
    """root: Sheet for root; sheets: list of child Sheets. Uses global labels across sheets."""
    from collections import defaultdict
    where = defaultdict(set)
    for sh in [root] + sheets:
        for net, *_ in sh.nets_used:
            where[net].add(sh.name)
    global_nets = {n for n, s in where.items() if len(s) > 1}
    # single-use nets warning
    singles = []
    for sh in [root] + sheets:
        cnt = defaultdict(int)
        for net, *_ in sh.nets_used:
            cnt[net] += 1
        for n, c in cnt.items():
            if c == 1 and n not in global_nets:
                singles.append((sh.name, n))
    for sh in [root] + sheets:
        sh.finalize_labels(global_nets)
    root_uuid = root.uuid
    sheet_uuid = {}
    tail = []
    x, y = 30.0, 40.0
    for i, sh in enumerate(sheets):
        su = uid()
        sheet_uuid[sh.name] = su
        root.items.append(S("sheet", S("at", x, y), S("size", 60, 25),
                            S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")), S("on_board", Sym("yes")),
                            S("dnp", Sym("no")),
                            S("stroke", S("width", 0.1524), S("type", Sym("solid"))),
                            S("fill", S("color", 0, 0, 0, 0.0)), S("uuid", su),
                            S("property", "Sheetname", sh.name, S("at", x, y - 0.8, 0),
                              S("effects", S("font", S("size", 1.524, 1.524)), S("justify", Sym("left"), Sym("bottom")))),
                            S("property", "Sheetfile", sh.filename, S("at", x, y + 25.6, 0),
                              S("effects", S("font", S("size", 1.27, 1.27)), S("justify", Sym("left"), Sym("top")))),
                            S("instances", S("project", PROJECT, S("path", "/" + root_uuid, S("page", str(i + 2)))))))
        x += 75
        if x > 300:
            x = 30.0
            y += 45
    tail = [S("sheet_instances", S("path", "/", S("page", "1")))]
    extra = {"root": root, "sheet_uuid": sheet_uuid}
    out = os.path.join(outdir, root.filename)
    open(out, "w", encoding="utf8", newline="\n").write(dump(root.to_tree(root_uuid, 1, dict(extra, tail=tail))) + "\n")
    for sh in sheets:
        open(os.path.join(outdir, sh.filename), "w", encoding="utf8", newline="\n").write(
            dump(sh.to_tree(root_uuid, 0, extra)) + "\n")
    return global_nets, singles
