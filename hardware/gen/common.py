"""Geometry and marks shared by the three Tumble boards, so they stack and look like one object.

Coordinates are millimetres from the board centre, x right, y down, seen from the top of the stack.
"""
import math

from kicadgen import Part

HALF = 22.5            # 45 x 45 mm
RADIUS = 5.0           # corner radius
HOLE = 21.0            # M2 mounting holes on a 42 mm square
KEYLINE = 0.8          # copper keyilne inset from the edge
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


def gold_txt(pb, s, x, y, side="F", size=1.2, rot=0):
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
    gold_txt(pb, s, x, y, side=side, size=0.9)


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
