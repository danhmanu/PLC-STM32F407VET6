"""Bo tu di day cho so do nguyen ly (luoi 1.27mm).

Quy tac an toan de khong tao ket noi nham trong KiCad:
- Khong di qua than linh kien va doan chan (pin line).
- Khong cham dau chan / dau day / goc day / nhan cua net khac.
- Chi duoc cat vuong goc qua doan thang cua net khac (khong re tai o cat).
- Moi diem noi la diem dau-mut chung (T duoc tach doan + junction).
"""
import heapq
import math

G = 1.27
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def gc(v):
    return int(round(v / G))


def on_grid(x, y):
    return abs(x / G - round(x / G)) < 1e-3 and abs(y / G - round(y / G)) < 1e-3


class Grid:
    def __init__(self, w_mm, h_mm, margin=8.0):
        self.x0, self.y0 = gc(margin), gc(margin)
        self.x1, self.y1 = gc(w_mm - margin), gc(h_mm - margin)
        self.blocked = set()
        # occ[cell] = {net: set of 'H','V','N'}
        self.occ = {}

    def inb(self, c):
        return self.x0 <= c[0] <= self.x1 and self.y0 <= c[1] <= self.y1

    def block_box(self, x0, y0, x1, y1):
        for gx in range(gc(min(x0, x1)), gc(max(x0, x1)) + 1):
            for gy in range(gc(min(y0, y1)), gc(max(y0, y1)) + 1):
                self.blocked.add((gx, gy))

    def mark(self, cell, net, kind):
        self.occ.setdefault(cell, {}).setdefault(net, set()).add(kind)

    def add_segment(self, a, b, net, end_nodes=True):
        """a, b: grid cells on same row/col."""
        (ax, ay), (bx, by) = a, b
        if ax == bx:
            rng = range(min(ay, by), max(ay, by) + 1)
            cells = [(ax, y) for y in rng]
            axis = "V"
        else:
            rng = range(min(ax, bx), max(ax, bx) + 1)
            cells = [(x, ay) for x in rng]
            axis = "H"
        for c in cells:
            self.mark(c, net, axis)
        if end_nodes:
            self.mark(a, net, "N")
            self.mark(b, net, "N")


def route_net(grid, net, terms, max_len_cells=70, max_expand=60000):
    """terms: list of (cell, outward_dir or None). Returns list of paths (list of cells) or None."""
    tree = set()
    tree_pin = {}            # cell -> required entry dir (for pin terminals)
    first = terms[0]
    tree.add(first[0])
    if first[1]:
        tree_pin[first[0]] = first[1]
    remaining = list(terms[1:])
    paths = []
    added = []               # (cell, net, kind) to rollback
    while remaining:
        # chon terminal gan cay nhat
        remaining.sort(key=lambda t: min(abs(t[0][0] - c[0]) + abs(t[0][1] - c[1]) for c in tree))
        tgt = remaining.pop(0)
        path = _astar(grid, net, tgt, tree, tree_pin, max_len_cells, max_expand)
        if path is None:
            for cell, n, kind in added:
                s = grid.occ.get(cell, {}).get(n)
                if s:
                    s.discard(kind)
            return None
        # ghi nhan vao luoi
        for i, c in enumerate(path):
            kinds = set()
            if i > 0:
                kinds.add("V" if path[i - 1][0] == c[0] else "H")
            if i < len(path) - 1:
                kinds.add("V" if path[i + 1][0] == c[0] else "H")
            if i == 0 or i == len(path) - 1 or len(kinds) > 1:
                kinds.add("N")
            for k in kinds:
                if k not in grid.occ.get(c, {}).get(net, set()):
                    grid.mark(c, net, k)
                    added.append((c, net, k))
            tree.add(c)
        if tgt[1]:
            tree_pin[tgt[0]] = tgt[1]
        paths.append(path)
    return paths


def _astar(grid, net, tgt, tree, tree_pin, max_len, max_expand):
    start, sdir = tgt
    # trang thai: (cell, dir_index, forced_straight)
    openh = []
    cnt = 0
    g0 = {}

    def push(cost, cell, d, forced, parent, length):
        nonlocal cnt
        cnt += 1
        h = min(abs(cell[0] - c[0]) + abs(cell[1] - c[1]) for c in _near(tree, cell))
        heapq.heappush(openh, (cost + h, cnt, cost, cell, d, forced, parent, length))

    # buoc dau: bat buoc theo huong ra cua chan
    if sdir:
        dirs0 = [DIRS.index(sdir)]
    else:
        dirs0 = range(4)
    root = (start, None, False, None, 0)
    seen = {}
    for di in dirs0:
        dx, dy = DIRS[di]
        nc = (start[0] + dx, start[1] + dy)
        ok, forced = _enter(grid, net, nc, di, tree, tree_pin)
        if ok is None:
            continue
        if ok == "goal":
            return [start, nc]
        push(1, nc, di, forced, root, 1)
    expand = 0
    while openh:
        f, _, cost, cell, d, forced, parent, length = heapq.heappop(openh)
        key = (cell, d)
        if key in seen and seen[key] <= cost:
            continue
        seen[key] = cost
        expand += 1
        if expand > max_expand or length > max_len:
            continue
        node = (cell, d, forced, parent, length)
        for di in range(4):
            if forced and di != d:
                continue
            if di == (d ^ 1):           # khong quay dau
                continue
            dx, dy = DIRS[di]
            nc = (cell[0] + dx, cell[1] + dy)
            res, nforced = _enter(grid, net, nc, di, tree, tree_pin)
            if res is None:
                continue
            step = 1 + (2.5 if di != d else 0) + (3 if nforced else 0)
            if res == "goal":
                # dung lai duong di
                path = [nc, cell]
                p = parent
                while p is not None:
                    path.append(p[0])
                    p = p[3]
                path.reverse()
                return path
            push(cost + step, nc, di, nforced, node, length + 1)
    return None


def _near(tree, cell, k=40):
    if len(tree) <= k:
        return tree
    return sorted(tree, key=lambda c: abs(c[0] - cell[0]) + abs(c[1] - cell[1]))[:k]


def _enter(grid, net, nc, di, tree, tree_pin):
    """Co duoc buoc vao o nc theo huong di? -> ('goal'|'ok', forced_straight) hoac (None, None)."""
    if not grid.inb(nc):
        return None, None
    axis = "H" if di < 2 else "V"
    occ = grid.occ.get(nc, {})
    if nc in tree:
        req = tree_pin.get(nc)
        if req is not None and DIRS[di] != (-req[0], -req[1]):
            return None, None
        # khong noi tai o dang co net khac cat qua
        if any(n != net for n in occ):
            return None, None
        return "goal", False
    if nc in grid.blocked:
        return None, None
    forced = False
    for n, kinds in occ.items():
        if n == net:
            continue            # o cua chinh net (ngoai cay hien tai) - hiem gap
        if "N" in kinds or axis in kinds:
            return None, None
        forced = True           # cat vuong goc
    return "ok", forced


def path_segments(path):
    """Gop cac o thanh doan thang (diem dau/cuoi tai goc)."""
    segs = []
    a = path[0]
    for i in range(1, len(path) - 1):
        p, c, n = path[i - 1], path[i], path[i + 1]
        if (p[0] == c[0]) != (c[0] == n[0]):
            segs.append((a, c))
            a = c
    segs.append((a, path[-1]))
    return segs
