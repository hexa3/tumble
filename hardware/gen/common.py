"""Geometry and marks shared by the three Tumble boards, so they stack and look like one object.

Coordinates are millimetres from the board centre, x right, y down, seen from the top of the stack.
"""
import math

from kicadgen import Part

HALF = 25.0            # 50 x 50 mm: room below the LED field for the matrix driver
RADIUS = 5.0           # corner radius
HOLE = 21.0            # M2 mounting holes on a 42 mm square
KEYLINE = 0.8          # copper keyline inset from the edge
ROUTE_EDGE = 1.35      # routed copper stays this far inside the edge (inside the keyline)
GAP_MM = 4.5           # board-to-board gap = standoff length; spring pins work at 4.3-5.0 mm

HOLES = [(-HOLE, -HOLE), (HOLE, -HOLE), (-HOLE, HOLE), (HOLE, HOLE)]

# Spring-pin positions, identical on every board: six on the west edge, four on the east.  Pins sit
# on the lower board's top side and press on gold dots on the upper board's bottom side.
PX = 21.0
LINK_XY = [(-PX, y) for y in (-15.0, -9.0, -3.0, 3.0, 9.0, 15.0)] + [(PX, y) for y in (-15.0, -5.0, 5.0, 15.0)]
# core -> face.  West order follows the LED driver's west-side pins (top to bottom), so its escape
# lines nest without crossing; the east four are ground.
LINK_AB = ["LED_SDB", "LED_INTB", "SCL", "SDA", "3V3", "VBAT", "GND", "GND", "GND", "GND"]
# base -> core: power, the I2C bus (fuel gauge on the base), the two SWD lines (to the caseback dots)
# and the single-wire UART to the USB bridge
LINK_BC = ["VBAT", "GND", "SDA", "SCL", "SWDIO", "SWCLK", "3V3", "GND", "VBAT", "UART"]

M2 = "MountingHole:MountingHole_2.2mm_M2"
POGO = "Tumble:Pogo_MillMax_0900-2"
LAND = "Tumble:PogoLand_D2.2"


def holes():
    return [Part(f"H{i + 1}", ("Mechanical", "MountingHole"), "M2", M2, {}, group="H") for i in range(4)]


def pins(nets, prefix="P"):
    return [Part(f"{prefix}{i + 1}", ("Connector", "TestPoint"), n, POGO, {"1": n}, part="POGO", group=prefix)
            for i, n in enumerate(nets)]


def lands(nets, prefix="X"):
    return [Part(f"{prefix}{i + 1}", ("Connector", "TestPoint"), n, LAND, {"1": n}, group=prefix)
            for i, n in enumerate(nets)]


def _rounded(pb, inset, layer, width):
    """Rounded square, `inset` mm inside the board edge, drawn on `layer`."""
    pcbnew = pb.pcbnew
    h, r = HALF - inset, max(RADIUS - inset, 0.2)
    k = r * (1 - math.sqrt(0.5))

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(pb.board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pb.V(*a)); s.SetEnd(pb.V(*b))
        s.SetLayer(layer); s.SetWidth(pcbnew.FromMM(width)); pb.board.Add(s)

    def arc(a, m, b):
        s = pcbnew.PCB_SHAPE(pb.board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(pb.V(*a), pb.V(*m), pb.V(*b))
        s.SetLayer(layer); s.SetWidth(pcbnew.FromMM(width)); pb.board.Add(s)

    seg((-h + r, -h), (h - r, -h)); seg((h, -h + r), (h, h - r))
    seg((h - r, h), (-h + r, h)); seg((-h, h - r), (-h, -h + r))
    arc((h - r, -h), (h - k, -h + k), (h, -h + r)); arc((h, h - r), (h - k, h - k), (h - r, h))
    arc((-h + r, h), (-h + k, h - k), (-h, h - r)); arc((-h, -h + r), (-h + k, -h + k), (-h + r, -h))


def outline(pb):
    _rounded(pb, 0.0, pb.pcbnew.Edge_Cuts, 0.1)


def keyline(pb, sides="FB", width=0.3):
    """The thin copper frame every visible side carries (bare copper under clear mask)."""
    for s in sides:
        _rounded(pb, KEYLINE, pb.pcbnew.F_Cu if s == "F" else pb.pcbnew.B_Cu, width)


def art(pb, side, x1, y1, x2, y2, pad=0.35):
    """Register an artwork area so routers keep copper out of it (see make_router)."""
    if not hasattr(pb, "art"):
        pb.art = []
    pb.art.append((side, x1 - pad, y1 - pad, x2 + pad, y2 + pad))


def gold_text(pb, s, x, y, side="F", size=1.2, rot=0):
    """Centred lettering in ENIG gold: copper text with the mask opened over it.  Registers its area."""
    cu, mask = ("F.Cu", "F.Mask") if side == "F" else ("B.Cu", "B.Mask")
    t = pb.text(s, x, y, layer=cu, size=size, rot=rot, bold=True)
    pb.text(s, x, y, layer=mask, size=size, rot=rot, bold=True)
    b = t.GetBoundingBox()
    P = pb.pcbnew.ToMM
    art(pb, side, P(b.GetLeft()) - pb.ox, P(b.GetTop()) - pb.oy, P(b.GetRight()) - pb.ox, P(b.GetBottom()) - pb.oy)


LABEL_XY = (-11.0, 20.3)


def board_label(pb, s, side, at=None):
    """'A · FACE  1/3' etc.: same place, size and finish on every visible side (`at` moves it on a
    hidden side where that spot is taken)."""
    x, y = at or LABEL_XY
    gold_text(pb, s, x, y, side=side, size=0.9)


def place_common(pb, land_refs=None, pin_refs=None):
    for i, (x, y) in enumerate(HOLES):
        pb.place(f"H{i + 1}", x, y)
    for i, (x, y) in enumerate(LINK_XY):
        if land_refs:
            pb.place(f"{land_refs}{i + 1}", x, y, back=True)
        if pin_refs:
            pb.place(f"{pin_refs}{i + 1}", x, y)


def make_router(pb, Router, maxw=0.2, clearance=0.17, grid=0.1, via_cost=6.0, layer_cost=None,
                hole_keepout=2.6, shift=(0.0, 0.0), edge=ROUTE_EDGE):
    """Grid router primed with everything already on the board.

    shift moves the routing grid, so that fine-pitch pads can be put on grid points."""
    rt = Router(pb.ox - HALF + shift[0], pb.oy - HALF + shift[1], 2 * HALF, 2 * HALF, grid=grid, clearance=clearance,
                edge_clear=edge - 0.2, max_width=maxw, corner_r=RADIUS,
                layer_cost=layer_cost or {"F": 0.0, "B": 0.0}, via_cost=via_cost)
    for x, y in HOLES:      # room for the standoff and the screw head (track centre stays outside)
        rt.keepout_c.append((pb.ox + x, pb.oy + y, hole_keepout + maxw / 2))
    for x1, y1, x2, y2 in getattr(pb, "via_keepouts", []):   # e.g. between a Tag-Connect's pads
        rt.via_keepout.append((pb.ox + x1, pb.oy + y1, pb.ox + x2, pb.oy + y2))
    for side, x1, y1, x2, y2 in getattr(pb, "art", []):   # artwork: no copper, no vias
        rt.keepout.append((side, pb.ox + x1, pb.oy + y1, pb.ox + x2, pb.oy + y2))
    for fp in pb.fps.values():
        for pad in fp.Pads():
            rt.add_pad(pad)
    for L, a, b, w, n in pb.tracks:
        rt.add_track(L, a, b, w, n)
    for p, n in pb.vias:
        rt.add_via(p, n)
    return rt


def courtyard(pb, ref):
    """Courtyard bbox (board-centred coords) on whichever side the part sits."""
    pcbnew = pb.pcbnew
    fp = pb.fps[ref]
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    b = fp.GetCourtyard(layer).BBox()
    if b.GetWidth() == 0:
        b = fp.GetBoundingBox(False)
    return (pcbnew.ToMM(b.GetLeft()) - pb.ox, pcbnew.ToMM(b.GetTop()) - pb.oy,
            pcbnew.ToMM(b.GetRight()) - pb.ox, pcbnew.ToMM(b.GetBottom()) - pb.oy)


def overlap(a, b, margin=0.0):
    """Do rectangles a and b (x1, y1, x2, y2) overlap, with `margin` of clearance?"""
    return a[0] < b[2] + margin and b[0] < a[2] + margin and a[1] < b[3] + margin and b[1] < a[3] + margin


def autoplace(pb, wanted, back=(), fixed=(), reserve=(), margin=0.1, limit=8.0):
    """Place each part at its wanted (x, y, rot), or the nearest spot where its courtyard is clear.

    wanted: {ref: (x, y, rot)} in placement order.  fixed: refs already placed that others must avoid.
    reserve: extra (side, x1, y1, x2, y2) areas to keep empty.  Parts on different sides don't clash,
    except through-hole parts, which block both."""
    side = {}
    rects = []                                   # (side, x1, y1, x2, y2)

    def sides_of(ref):
        fp = pb.fps[ref]
        th = any(p.GetAttribute() in (pb.pcbnew.PAD_ATTRIB_PTH, pb.pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())
        return "FB" if th else ("B" if fp.IsFlipped() else "F")

    for ref in fixed:
        rects.append((sides_of(ref),) + courtyard(pb, ref))
    for x, y in HOLES:
        rects.append(("FB", x - 2.6, y - 2.6, x + 2.6, y + 2.6))
    rects += list(reserve)
    rects += [(sd,) + tuple(r) for sd, *r in getattr(pb, "art", [])]
    lim = HALF - 0.6

    def clash(sd, r):
        if r[0] < -lim or r[1] < -lim or r[2] > lim or r[3] > lim:
            return True
        return any(set(sd) & set(q[0]) and overlap(r, q[1:], margin) for q in rects)

    moved = []
    for ref, (px, py, pr) in wanted.items():
        done = False
        rad = 0.0
        while rad <= limit and not done:
            n = max(1, int(2 * math.pi * rad / 0.2))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = round(px + rad * math.cos(a), 2), round(py + rad * math.sin(a), 2)
                pb.place(ref, x, y, pr, back=ref in back)
                sd = sides_of(ref)
                r = courtyard(pb, ref)
                if not clash(sd, r):
                    rects.append((sd,) + r)
                    done = True
                    if rad > 0:
                        moved.append(f"{ref}+{rad:.1f}")
                    break
            rad = round(rad + 0.2, 2)
        if not done:
            pb.place(ref, px, py, pr, back=ref in back)
            r = courtyard(pb, ref)
            hits = [q for q in rects if set(q[0]) & set(sides_of(ref)) and overlap(r, q[1:], margin)]
            raise SystemExit(f"autoplace: no room for {ref} near ({px}, {py}); at its spot it hits {hits}")
    print("  autoplace moved:", " ".join(moved) or "nothing")


def gold_rect(pb, x1, y1, x2, y2, side="B"):
    """Filled copper rectangle with the mask opened over it: reads as solid gold."""
    pcbnew = pb.pcbnew
    for layer in ((pcbnew.B_Cu, pcbnew.B_Mask) if side == "B" else (pcbnew.F_Cu, pcbnew.F_Mask)):
        s = pcbnew.PCB_SHAPE(pb.board, pcbnew.SHAPE_T_RECT)
        s.SetStart(pb.V(x1, y1))
        s.SetEnd(pb.V(x2, y2))
        s.SetLayer(layer)
        s.SetFilled(True)
        s.SetWidth(0)
        pb.board.Add(s)


def gold_line(pb, a, b, side="F", width=0.25):
    pcbnew = pb.pcbnew
    for layer in ((pcbnew.B_Cu, pcbnew.B_Mask) if side == "B" else (pcbnew.F_Cu, pcbnew.F_Mask)):
        s = pcbnew.PCB_SHAPE(pb.board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pb.V(*a))
        s.SetEnd(pb.V(*b))
        s.SetLayer(layer)
        s.SetWidth(pcbnew.FromMM(width))
        pb.board.Add(s)


def stitch(pb, rt, step=3.0, net="GND"):
    """GND vias on a loose grid wherever both layers are free: ties the two pours together."""
    n = 0
    k = int(2 * HALF / step)
    for i in range(k + 1):
        for j in range(k + 1):
            gx, gy = -HALF + 1.5 + i * step, -HALF + 1.5 + j * step
            q = (pb.ox + gx, pb.oy + gy)
            c = rt.ij(*q)
            if rt.via_ok(q, "/__STITCH__") and rt.free("F", c, "/__STITCH__") and rt.free("B", c, "/__STITCH__"):
                pb.via(gx, gy, net)
                rt.add_via(q, "/" + net)
                n += 1
    return n


def ground(pb, rt, side="F", skip=()):
    """Tie every SMD ground pad on `side` to the pours: a via beside it if there's room, otherwise an
    A* link to the nearest ground copper already on the board.  Returns (vias, links, failures)."""
    pcbnew = pb.pcbnew
    lid = pcbnew.F_Cu if side == "F" else pcbnew.B_Cu
    ox, oy = pb.ox, pb.oy
    n_via = n_link = 0
    lonely = []
    for fp in pb.fps.values():
        for pd in fp.Pads():
            if pd.GetNetname() != "/GND" or not pd.IsOnLayer(lid) or pd.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if fp.GetReference()[0] in "PXT" and fp.GetReference() != "TP":   # spring pins/lands: pour-connected
                continue
            if (fp.GetReference(), pd.GetNumber()) in skip:
                continue
            px, py = pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)
            done = False
            for r in (0.75, 0.9, 1.05, 1.2, 1.4, 1.6, 1.9, 2.2, 2.6, 3.0, 3.5):
                for k in range(24):
                    q = (round(px + r * math.cos(k * math.pi / 12), 2), round(py + r * math.sin(k * math.pi / 12), 2))
                    if rt.via_ok(q, "/GND") and all(
                            rt.free(side, rt.ij(px + (q[0] - px) * t / 6, py + (q[1] - py) * t / 6), "/GND")
                            for t in range(1, 7)):
                        pb.track((px - ox, py - oy), (q[0] - ox, q[1] - oy), 0.25, "GND", side)
                        pb.via(q[0] - ox, q[1] - oy, "GND")
                        rt.add_track(side, (px, py), q, 0.25, "/GND")
                        rt.add_via(q, "/GND")
                        done = True
                        n_via += 1
                        break
                if done:
                    break
            if not done:
                lonely.append(pd)
    fails = []
    for pd in lonely:
        cop = [("track", L, a, b, w) for L, a, b, w, n in pb.tracks if n == "/GND"] + \
              [("via", p) for p, n in pb.vias if n == "/GND"]
        ok, tr, vs = rt.route_net("/GND", [pd], 0.2, seeds=rt.copper_cells(cop))
        if not ok:
            fails.append(f"{pd.GetParentFootprint().GetReference()}.{pd.GetNumber()}")
            continue
        n_link += 1
        for L, a, b, w, n in tr:
            pb.track((a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy), w, "GND", L)
        for p, n in vs:
            pb.via(p[0] - ox, p[1] - oy, "GND")
    return n_via, n_link, fails


def escape_stubs(pb, refs, length=0.7, width=0.2, spread=0.8, gnd_vias=False):
    """Short outward stubs from every signal pad of fine-pitch parts, so the grid router can reach
    them: returns ({net: [stub end, absolute mm]}, {(ref, pad number)} now served by a stub).
    Pins closer than `spread` fan out to that pitch, so no stub end sits in a neighbour's clearance.
    Ground pads are left to ground()."""
    pcbnew = pb.pcbnew
    ends, done = {}, set()
    for ref in refs:
        fp = pb.fps[ref]
        cx, cy = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
        side = "B" if fp.IsFlipped() else "F"
        info, sides = [], {}
        for pd in fp.Pads():
            px, py = pcbnew.ToMM(pd.GetPosition().x), pcbnew.ToMM(pd.GetPosition().y)
            dx, dy = px - cx, py - cy
            pbb = pd.GetBoundingBox()
            pw, ph = pbb.GetWidth(), pbb.GetHeight()
            horiz = pw > ph * 1.2 or (abs(pw - ph) <= ph * 0.2 and abs(dx) >= abs(dy))   # long axis = escape axis
            key = ("x", 1 if dx > 0 else -1) if horiz else ("y", 1 if dy > 0 else -1)
            lat = py if key[0] == "x" else px
            sides.setdefault(key, []).append(lat)
            info.append((pd, px, py, key, lat))
        for pd, px, py, key, lat in info:
            net = pd.GetNetname()
            if not net or net.startswith("unconnected") or (net == "/GND" and not gnd_vias):
                continue
            if net == "/GND" and pd.GetBoundingBox().GetWidth() > pcbnew.FromMM(1.6) and \
                    pd.GetBoundingBox().GetHeight() > pcbnew.FromMM(1.6):
                continue                                        # exposed pads: not escaped
            lats = sorted(set(round(v, 3) for v in sides[key]))
            pitch = min((b - a for a, b in zip(lats, lats[1:]) if b - a > 0.01), default=spread)
            mid = (lats[0] + lats[-1]) / 2
            new_lat = mid + (lat - mid) * (spread / pitch if pitch < spread else 1.0)
            bb = pd.GetBoundingBox()
            half = (pcbnew.ToMM(bb.GetWidth()) if key[0] == "x" else pcbnew.ToMM(bb.GetHeight())) / 2
            fan = abs(new_lat - lat)
            if key[0] == "x":
                p1 = (px + key[1] * (half + 0.25), py)
                e = (p1[0] + key[1] * (length + fan), new_lat)
            else:
                p1 = (px, py + key[1] * (half + 0.25))
                e = (new_lat, p1[1] + key[1] * (length + fan))
            for a_, b_ in (((px, py), p1), (p1, e)):
                pb.track((a_[0] - pb.ox, a_[1] - pb.oy), (b_[0] - pb.ox, b_[1] - pb.oy), width, net[1:], side)
            if net == "/GND":                                  # ground: the stub ends in a via
                pb.via(e[0] - pb.ox, e[1] - pb.oy, "GND")
            else:
                ends.setdefault(net, []).append(e)
            done.add((ref, pd.GetNumber()))
    return ends, done


# ---------------------------------------------------------------- maker's marks
# Silkscreen and ENIG lettering only: both are on every board already, so none of this costs anything.
# Bottom-side drawings take mirror=True so they read left to right from below.

def hex_badge(pb, x, y, r=3.0, side="B", text="hexa3"):
    """A flat-topped hexagon with `text` in it, in ink.  Registers its area so vias stay out."""
    layer = side + ".SilkS"
    pts = [(x + r * math.cos(math.radians(60 * k)), y + r * math.sin(math.radians(60 * k))) for k in range(6)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        pb.silk_line(a, b, w=0.2, layer=layer)
    pb.text(text, x, y, layer=layer, size=1.0, bold=True)
    art(pb, side, x - r, y - r, x + r, y + r)


_PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
         4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
         6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


def tumbling_dice(pb, x, y, side="B", size=3.4, step=5.4, mirror=True):
    """Faces 1..6 in a row, each turned a bit further than the last, bouncing along a baseline."""
    layer = side + ".SilkS"
    h, p = size / 2, size * 0.27
    for k in range(6):
        cx = x + (k - 2.5) * step * (-1 if mirror else 1)
        cy = y - (0.9 if k % 2 else 0.0)                              # every other one in the air
        a = math.radians(18 * k * (-1 if mirror else 1))

        def rot(u, v):
            return cx + u * math.cos(a) - v * math.sin(a), cy + u * math.sin(a) + v * math.cos(a)
        c = [rot(-h, -h), rot(h, -h), rot(h, h), rot(-h, h)]
        for s, t in zip(c, c[1:] + c[:1]):
            pb.silk_line(s, t, w=0.18, layer=layer)
        for u, v in _PIPS[k + 1]:
            pb.silk_circle(*rot(u * p, v * p), 0.28, w=0.1, layer=layer, fill=True)


def noise_trace(pb, x1, x2, y, amp=1.1, seed=b"hexa3", side="B", mirror=True):
    """An avalanche-noise oscilloscope trace whose samples are blake2s(seed), in ink."""
    import hashlib
    layer = side + ".SilkS"
    d = hashlib.blake2s(seed).digest()
    n = len(d)
    xs = [x1 + (x2 - x1) * i / (n - 1) for i in range(n)]
    if mirror:
        xs = xs[::-1]
    pts = [(xs[i], y - amp * (d[i] - 127.5) / 127.5) for i in range(n)]
    for a, b in zip(pts, pts[1:]):
        pb.silk_line(a, b, w=0.15, layer=layer)
    pb.silk_line((x1, y), (x2, y), w=0.1, layer=layer)                # the zero line
    return d
