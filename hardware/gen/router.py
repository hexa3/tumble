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
