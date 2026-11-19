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
