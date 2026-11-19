"""2-layer grid router (A*, 8 directions, turn + via penalties).

Started life as TinyDie v1's router.  Additions for the cube:
  * an origin offset (boards are drawn around (ox, oy) in KiCad space),
  * rectangular boards with square corners,
  * seeding a net's search tree with copper that is already there
    (the structured buses), so A* only fills in the missing links,
  * per-layer cost and keep-out rectangles.
KiCad DRC is still the final judge.
"""
import heapq
import math

import pcbnew

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
LAYERS = ("F", "B")


class Router:
    def __init__(self, x0, y0, w, h, grid=0.2, clearance=0.2, edge_clear=0.5,
                 max_width=0.4, via_d=0.6, corner_r=3.0, layer_cost=None, via_cost=12.0):
        self.x0, self.y0, self.w, self.h, self.g = x0, y0, w, h, grid
        self.nx, self.ny = int(round(w / grid)) + 1, int(round(h / grid)) + 1
        self.clr = clearance
        self.edge = edge_clear
        self.cr = corner_r
        m = max(0.6 * grid, 0.03)        # quantisation margin: a cell centre is <= g/2 off
        self.t_infl = max_width / 2 + clearance + m
        self.v_infl = via_d / 2 + clearance + m
        self.via_d = via_d
        # cell -> set of nets whose copper is too close
        self.tblock = {L: {} for L in LAYERS}
        self.vblock = {}
        self.layer_cost = layer_cost or {"F": 0.0, "B": 0.6}
        self.via_cost = via_cost
        self.keepout = []   # (layer or None, x1, y1, x2, y2)
        self.keepout_c = [] # (cx, cy, r): nothing within r of the centre, either layer
        self.via_keepout = []  # (x1, y1, x2, y2): no via centre inside
        self.hblock = set() # cells where a new drill would sit too close to an existing one

    # ------------------------------------------------------------ geometry
    def xy(self, i, j):
        return self.x0 + i * self.g, self.y0 + j * self.g

    def ij(self, x, y):
        return int(round((x - self.x0) / self.g)), int(round((y - self.y0) / self.g))

    def inside_board(self, x, y, m):
        x1, y1, x2, y2 = self.x0 + m, self.y0 + m, self.x0 + self.w - m, self.y0 + self.h - m
        if not (x1 <= x <= x2 and y1 <= y <= y2):
            return False
        if self.cr <= 0:
            return True
        r = self.cr - m
        for cx, cy in [(self.x0 + self.cr, self.y0 + self.cr),
                       (self.x0 + self.w - self.cr, self.y0 + self.cr),
                       (self.x0 + self.cr, self.y0 + self.h - self.cr),
                       (self.x0 + self.w - self.cr, self.y0 + self.h - self.cr)]:
            if (abs(x - cx) <= self.cr and abs(y - cy) <= self.cr and
                    ((x < cx) == (cx < self.x0 + self.w / 2)) and
                    ((y < cy) == (cy < self.y0 + self.h / 2)) and
                    math.hypot(x - cx, y - cy) > r):
                return False
        return True

    @staticmethod
    def _dist_rect(px, py, cx, cy, hx, hy):
        dx = max(abs(px - cx) - hx, 0.0)
        dy = max(abs(py - cy) - hy, 0.0)
        return math.hypot(dx, dy)

    @staticmethod
    def _dist_seg(px, py, a, b):
        ax, ay = a
        bx, by = b
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
        return math.hypot(px - (ax + t * vx), py - (ay + t * vy))

    def _mark(self, layers, bbox, dist, net):
        """bbox=(x1,y1,x2,y2) of copper; dist(px,py) = distance to copper edge."""
        x1, y1, x2, y2 = bbox
        m = max(self.t_infl, self.v_infl)
        i1, j1 = self.ij(x1 - m, y1 - m)
        i2, j2 = self.ij(x2 + m, y2 + m)
        for i in range(max(i1, 0), min(i2, self.nx - 1) + 1):
            for j in range(max(j1, 0), min(j2, self.ny - 1) + 1):
                d = dist(*self.xy(i, j))
                if d < self.t_infl:
                    for L in layers:
                        self.tblock[L].setdefault((i, j), set()).add(net)
                if d < self.v_infl:
                    self.vblock.setdefault((i, j), set()).add(net)

    # ------------------------------------------------------------ obstacles
    def pad_info(self, pad):
        layers = [L for L, lid in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu))
                  if pad.IsOnLayer(lid)]
        bb = pad.GetBoundingBox()
        x1, y1 = pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY())
        x2, y2 = x1 + pcbnew.ToMM(bb.GetWidth()), y1 + pcbnew.ToMM(bb.GetHeight())
        cx, cy = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        try:
            circ = pad.GetShape(pcbnew.F_Cu) == pcbnew.PAD_SHAPE_CIRCLE
        except TypeError:
            circ = pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE
        return layers, (x1, y1, x2, y2), (cx, cy), circ

    def add_pad(self, pad):
        layers, bb, (cx, cy), circ = self.pad_info(pad)
        if circ:
            r = (bb[2] - bb[0]) / 2
            dist = lambda px, py: max(math.hypot(px - cx, py - cy) - r, 0.0)  # noqa: E731
        else:
            hx, hy = (bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2
            mx, my = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            dist = lambda px, py: self._dist_rect(px, py, mx, my, hx, hy)  # noqa: E731
        self._mark(layers, bb, dist, pad.GetNetname() or f"pad{id(pad)}")

    def add_track(self, layer, a, b, w, net):
        bb = (min(a[0], b[0]) - w / 2, min(a[1], b[1]) - w / 2,
              max(a[0], b[0]) + w / 2, max(a[1], b[1]) + w / 2)
        self._mark([layer], bb, lambda px, py: max(self._dist_seg(px, py, a, b) - w / 2, 0.0), net)

    def add_via(self, p, net, drill=0.3):
        lim = drill / 2 + 0.3 / 2 + 0.25          # hole-to-hole, any net
        ci, cj = self.ij(*p)
        k = int(lim / self.g) + 1
        for i in range(ci - k, ci + k + 1):
            for j in range(cj - k, cj + k + 1):
                x, y = self.xy(i, j)
                if math.hypot(x - p[0], y - p[1]) < lim:
                    self.hblock.add((i, j))
        r = self.via_d / 2
        bb = (p[0] - r, p[1] - r, p[0] + r, p[1] + r)
        self._mark(LAYERS, bb, lambda px, py: max(math.hypot(px - p[0], py - p[1]) - r, 0.0), net)

    # ------------------------------------------------------------ queries
    def free(self, L, c, net):
        i, j = c
        if not (0 <= i < self.nx and 0 <= j < self.ny):
            return False
        x, y = self.xy(i, j)
        if not self.inside_board(x, y, self.edge + 0.2):
            return False
        for kl, a, b, c2, d in self.keepout:
            if (kl is None or kl == L) and a <= x <= c2 and b <= y <= d:
                return False
        for cx, cy, r in self.keepout_c:
            if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                return False
        s = self.tblock[L].get(c)
        return not s or s <= {net}

    def via_ok(self, p, net, cell=None):
        c = cell or self.ij(*p)
        x, y = self.xy(*c)
        if not self.inside_board(x, y, self.edge + self.via_d / 2):
            return False
        for kl, a, b, c2, d in self.keepout:
            if a <= x <= c2 and b <= y <= d:
                return False
        for cx, cy, r in self.keepout_c:
            if (x - cx) ** 2 + (y - cy) ** 2 < (r + self.via_d / 2) ** 2:
                return False
        for a, b, c2, d in self.via_keepout:
            if a <= x <= c2 and b <= y <= d:
                return False
        if c in self.hblock:
            return False
        s = self.vblock.get(c)
        return not s or s <= {net}

    def pad_cells(self, pad):
        layers, bb, (cx, cy), circ = self.pad_info(pad)
        i1, j1 = self.ij(bb[0], bb[1])
        i2, j2 = self.ij(bb[2], bb[3])
        out = set()
        for i in range(i1, i2 + 1):
            for j in range(j1, j2 + 1):
                x, y = self.xy(i, j)
                inside = (math.hypot(x - cx, y - cy) <= (bb[2] - bb[0]) / 2 - 0.1 if circ
                          else bb[0] + 0.1 <= x <= bb[2] - 0.1 and bb[1] + 0.1 <= y <= bb[3] - 0.1)
                if inside:
                    for L in layers:
                        out.add((L, i, j))
        return out, (cx, cy)

    # ------------------------------------------------------------ search
    def _astar(self, net, sources, targets, tcenter):
        tx, ty = self.ij(*tcenter)

        def h(i, j):
            dx, dy = abs(i - tx), abs(j - ty)
            return (max(dx, dy) - min(dx, dy)) + 1.4142 * min(dx, dy)

        openq, best, came = [], {}, {}
        for (L, i, j) in sources:
            st = (L, i, j, -1)
            best[st] = 0.0
            heapq.heappush(openq, (h(i, j), 0.0, st))
        while openq:
            f, g, st = heapq.heappop(openq)
            if g > best.get(st, 1e18):
                continue
            L, i, j, d = st
            if (L, i, j) in targets:
                path = [(L, i, j)]
                while st in came:
                    st = came[st]
                    path.append(st[:3])
                return path[::-1]
            # moves
            for nd, (di, dj) in enumerate(DIRS):
                c = (i + di, j + dj)
                if not self.free(L, c, net) and (L, *c) not in targets:
                    continue
                step = 1.4142 if di and dj else 1.0
                turn = 0.0 if d < 0 else min((nd - d) % 8, (d - nd) % 8) * 0.6
                layer_pen = self.layer_cost[L]
                ng = g + step * (1 + layer_pen) + turn
                ns = (L, c[0], c[1], nd)
                if ng < best.get(ns, 1e18):
                    best[ns] = ng
                    came[ns] = st
                    heapq.heappush(openq, (ng + h(*c), ng, ns))
            # via
            if self.via_ok(None, net, (i, j)):
                oL = "B" if L == "F" else "F"
                if self.free(oL, (i, j), net) or (oL, i, j) in targets:
                    ns = (oL, i, j, d)
                    ng = g + self.via_cost
                    if ng < best.get(ns, 1e18):
                        best[ns] = ng
                        came[ns] = st
                        heapq.heappush(openq, (ng + h(i, j), ng, ns))
        return None

    def copper_cells(self, items):
        """Cells covered by existing same-net copper: [('track', L, a, b, w) | ('via', p)]."""
        out = set()
        for it in items:
            if it[0] == "via":
                i, j = self.ij(*it[1])
                out |= {("F", i, j), ("B", i, j)}
            else:
                _, L, a, b, w = it
                n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (self.g / 2)))
                for k in range(n + 1):
                    x = a[0] + (b[0] - a[0]) * k / n
                    y = a[1] + (b[1] - a[1]) * k / n
                    out.add((L, *self.ij(x, y)))
        return out

    def route_net(self, net, pads, width, seeds=None, extra=None):
        """Connect pads (pcbnew PADs) as a tree. Returns ok, tracks, vias.

        `seeds` are cells of copper already on the board for this net; when
        given, the tree starts from them and every pad is joined to it."""
        cells = [self.pad_cells(p) for p in pads]
        for pt in extra or []:            # extra targets: copper ends that aren't pads
            c = self.ij(*pt)
            cells.append(({("F", c[0], c[1])}, pt))
            pads = list(pads) + [None]
        connected = [0]
        if seeds:
            tree = set(seeds)
            cells = [(set(), (0, 0))] + cells
            pads = [None] + list(pads)
        else:
            tree = set(cells[0][0])
        if not tree:                      # first pad has no usable cell: report, don't crash
            return False, [], []
        paths = []
        remaining = list(range(1, len(pads)))
        while remaining:
            # nearest remaining pad to the tree
            def dist_to_tree(k):
                cx, cy = cells[k][1]
                return min(math.hypot(cx - self.xy(i, j)[0], cy - self.xy(i, j)[1])
                           for _, i, j in tree)
            remaining.sort(key=dist_to_tree)
            k = remaining.pop(0)
            tgt, tc = cells[k]
            if tree & tgt:
                tree |= tgt
                continue
            path = self._astar(net, tree, tgt, tc)
            if not path:
                return False, [], []
            paths.append((path, k))
            tree |= set(path) | tgt
            # a via cell exists on both layers
            for a, b in zip(path, path[1:]):
                if a[0] != b[0]:
                    tree.add(("F", a[1], a[2]))
                    tree.add(("B", a[1], a[2]))
            connected.append(k)

        tracks, vias = [], []
        keep = {p[0][1:] for p, _ in paths} | {p[-1][1:] for p, _ in paths}
        pad_center = {}
        for k in range(len(cells)):
            for c in cells[k][0]:
                pad_center[c] = cells[k][1]
        for path, k in paths:
            # split into same-layer runs
            runs, cur = [], [path[0]]
            for a, b in zip(path, path[1:]):
                if a[0] != b[0]:
                    runs.append(cur)
                    vias.append((self.xy(a[1], a[2]), net))
                    cur = [b]
                else:
                    cur.append(b)
            runs.append(cur)
            for run in runs:
                L = run[0][0]
                pts = [run[0]]
                for idx in range(1, len(run) - 1):
                    p0, p1, p2 = pts[-1], run[idx], run[idx + 1]
                    d1 = (p1[1] - p0[1], p1[2] - p0[2])
                    d2 = (p2[1] - p1[1], p2[2] - p1[2])
                    collinear = d1[0] * d2[1] - d1[1] * d2[0] == 0
                    if not collinear or p1[1:] in keep:
                        pts.append(p1)
                if len(run) > 1:
                    pts.append(run[-1])
                xy = [self.xy(p[1], p[2]) for p in pts]
                # stubs into exact pad centres
                if run[0] in pad_center and run is runs[0]:
                    xy.insert(0, pad_center[run[0]])
                if run[-1] in pad_center and run is runs[-1]:
                    xy.append(pad_center[run[-1]])
                for a, b in zip(xy, xy[1:]):
                    if a != b:
                        tracks.append((L, a, b, width, net))
        for L, a, b, w, n in tracks:
            self.add_track(L, a, b, w, n)
        for p, n in vias:
            self.add_via(p, n)
        return True, tracks, vias
