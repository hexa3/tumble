#!/usr/bin/env python3
"""Board A, FACE: 121 LEDs in an 11 x 11 woven grid, driven by one IS31FL3733B.

The IS31FL3733B is a true 12 x 16 matrix driver: CS lines source current into anodes, SW lines sink
it from cathodes, and every LED sits at one (SW, CS) crossing.  So the board is a woven grid:

    rows    (anodes,   CS)  top copper: one straight trace above each LED row, visible on the face
    columns (cathodes, SW)  bottom copper: one straight line under each LED column

Every matrix line is placed by this script, not by the router:
  * columns run straight down and funnel into the driver's north side (SW1-SW9) and the top of its
    east side (SW10, SW11);
  * rows leave the field to the east as a 0.4 mm bus; its 45-degree corner also spreads it to
    0.54 mm, and each line drops to the bottom side through one of two staggered via columns and
    fans into the driver's east side (CS1-CS8, with PVCC between CS4 and CS5) or, from below, its
    south side (CS9-CS11);
  * the driver's west side escapes to the six west spring-pin dots, nested so nothing crosses.
The grid router only joins power, ground and the passives.

pixel_map() is the single source for this board and for the firmware's register table
(firmware/tools/gen_pixelmap.py checks it against this board's netlist).

Run with KiCad's Python:  /usr/bin/python3 gen_face.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as K  # noqa: E402
from kicadgen import HW, Part, PcbBuilder, write_schematic  # noqa: E402

N = 11
PITCH = 2.4
PADX = 0.485            # LED pad centres are +-0.485 mm from the LED centre (pad 1 = K west, 2 = A east)
DY = 0.85               # row trace this far above the LED, column via this far below
W = 0.2                 # matrix track width

LED_FP = "LED_SMD:LED_0402_1005Metric"
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
QFN = "Package_DFN_QFN:QFN-48-1EP_6x6mm_P0.4mm_EP4.2x4.2mm"

# driver placement (bottom side) and the derived geometry
UX, UY = -1.2, 18.7               # on the router's 0.1 mm grid, so pins line up with it
Y0 = 13.4               # first funnel horizontal, just below the last column via
FUN = 0.4               # funnel / bus pitch
XE0 = 13.1              # innermost row-bus line, just east of the field
C0 = 25.6               # x + y of the innermost bus diagonal
SPREAD = 0.54           # bus pitch after the corner = via-to-via vertical spacing
YV0 = UY - 1.2          # first via row
XA, XB = UX + 6.6, UX + 7.4
VIA_D, VIA_DRILL = 0.55, 0.28   # OSH Park: drill >= 0.254, annular ring >= 0.127


def xy(i, j):
    return (j - 5) * PITCH, (i - 5) * PITCH


def sw_of(j):           # column -> SW line (cathodes)
    return j + 1


def cs_of(i):           # row -> CS line (anodes); row 10 is the innermost bus line = CS1
    return N - i


def register_index(sw, cs):
    """PWM register (page 1) of the LED at (SWy, CSx): (y - 1) * 16 + (x - 1)  (datasheet Fig. 9)."""
    return (sw - 1) * 16 + (cs - 1)


def pixel_map():
    """[(row, col, sw, cs)] for all 121 LEDs, row-major."""
    return [(i, j, sw_of(j), cs_of(i)) for i in range(N) for j in range(N)]


def parts():
    P = []
    for i, j, sw, cs in pixel_map():
        P.append(Part(f"D{i * N + j + 1}", ("Device", "LED"), "YEL", LED_FP,
                      {"1": f"SW{sw}", "2": f"CS{cs}"}, part="LED", group="D"))
    pins = {"5": "GND", "12": "GND", "20": "VBAT", "29": "VBAT", "34": "GND", "35": "ISET",
            "37": "VBAT", "38": "VBAT", "39": "3V3", "41": "SDA", "42": "SCL", "43": "GND", "44": "GND",
            "45": "LED_INTB", "46": "LED_SDB", "47": "GND", "48": "GND", "49": "GND"}
    for n, p in enumerate([2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14], 1):
        pins[str(p)] = f"SW{n}"
    for n, p in enumerate([16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27], 1):
        pins[str(p)] = f"CS{n}"
    P.append(Part("U1", ("Driver_LED", "IS31FL3733-QF"), "IS31FL3733B", QFN, pins,
                  part="IS31FL3733B", group="U"))

    def R(ref, val, a, b, key):
        return Part(ref, ("Device", "R"), val, R0402, {"1": a, "2": b}, part=key, group="R")

    def C(ref, val, a, b, key, fp=C0402):
        return Part(ref, ("Device", "C"), val, fp, {"1": a, "2": b}, part=key, group="C")

    P += [
        R("R1", "20k", "ISET", "GND", "R20k_0402"),        # I_OUT = 840 / R_ISET * GCC / 256 = 42 mA at GCC 255
        R("R2", "100k", "LED_SDB", "GND", "R100k_0402"),   # driver held in shutdown until the MCU enables it
        C("C1", "1uF", "VBAT", "GND", "C1u_0402"), C("C2", "100nF", "VBAT", "GND", "C100n_0402"),
        C("C3", "10uF", "VBAT", "GND", "C10u_0603", C0603), C("C4", "10uF", "VBAT", "GND", "C10u_0603", C0603),
        C("C5", "1uF", "VBAT", "GND", "C1u_0402"),
        C("C7", "1uF", "3V3", "GND", "C1u_0402"),
    ]
    P += K.lands(K.LINK_AB) + K.holes()
    return P


def build(first=()):
    proj = "face"
    out = os.path.join(HW, proj)
    P = parts()
    nl = write_schematic(
        proj, "TinyDie Tumble - A FACE", P, out, paper="A1",
        notes=["Board A, FACE: 11 x 11 LED grid on one IS31FL3733B (I2C 0x50).  Rows = CS (anodes), columns = SW (cathodes).",
               "X1-X10 are gold dots that the core board's spring pins press on.  SDA/SCL/INTB pull-ups are on the core."],
        flags=["GND", "VBAT", "3V3"])
    pb = PcbBuilder(proj, out, nl, origin=(100.0, 100.0))
    K.outline(pb)
    K.keyline(pb, "F")
    K.place_common(pb, land_refs="X")

    def path(pts, net, layer, w=W):
        pb.path(pts, w, net, layer)

    # ------------------------------------------------ the woven grid
    rows = {}                                        # row -> [x of each anode stub]
    for i, j, sw, cs in pixel_map():
        x, y = xy(i, j)
        pb.place(f"D{i * N + j + 1}", x, y, 0)
        path([(x + PADX, y), (x + PADX, y - DY)], f"CS{cs}", "F")          # anode up to the row trace
        path([(x - PADX, y), (x - PADX, y + DY)], f"SW{sw}", "F")          # cathode down to its via
        pb.via(x - PADX, y + DY, f"SW{sw}")
        rows.setdefault(i, []).append(x + PADX)
    for j in range(N):                                                    # column lines
        x = xy(0, j)[0] - PADX
        path([(x, xy(0, j)[1] + DY), (x, xy(N - 1, j)[1] + DY)], f"SW{sw_of(j)}", "B")

    # ------------------------------------------------ driver
    for rot in (0, 90, 180, 270):
        pb.place("U1", UX, UY, rot, back=True)
        x6, y6 = pb.pad_xy("U1", "6")
        x21, y21 = pb.pad_xy("U1", "21")
        if y6 < UY - 2.5 and x21 > UX + 2.5:
            break
    else:
        raise SystemExit("no rotation puts pin 6 north and pin 21 east")

    def pad(n):
        return pb.pad_xy("U1", str(n))

    # side-1 and west-side grounds, AGND: short stubs inward to the exposed pad
    for n in (5, 12, 34, 43, 44, 47, 48):
        px, py = pad(n)
        dx, dy = px - UX, py - UY
        step = (-0.8 if dx > 0 else 0.8, 0) if abs(dx) > abs(dy) else (0, -0.8 if dy > 0 else 0.8)
        path([(px, py), (px + step[0], py + step[1])], "GND", "B", 0.2)

    # ------------------------------------------------ columns -> SW (funnel)
    last_via = xy(N - 1, 0)[1] + DY
    col_pin = {j: 2 + j + (1 if j >= 3 else 0) for j in range(9)}          # SW1-3 pins 2-4, SW4-9 pins 6-11
    west = sorted([j for j in range(9) if xy(0, j)[0] - PADX < pad(col_pin[j])[0]],
                  key=lambda j: pad(col_pin[j])[0] - (xy(0, j)[0] - PADX))
    east = sorted([j for j in range(9) if j not in west],
                  key=lambda j: (xy(0, j)[0] - PADX) - pad(col_pin[j])[0])
    for group in (west, east):
        for rank, j in enumerate(group):                                  # longest travel lowest
            x = xy(0, j)[0] - PADX
            px, py = pad(col_pin[j])
            yh = Y0 + FUN * rank
            path([(x, last_via), (x, yh), (px, yh), (px, py)], f"SW{sw_of(j)}", "B")
    for j, n in ((9, 13), (10, 14)):                                      # SW10, SW11: east side, top
        x = xy(0, j)[0] - PADX
        px, py = pad(n)
        path([(x, last_via), (x, py), (px, py)], f"SW{sw_of(j)}", "B")

    # ------------------------------------------------ rows -> CS (east bus, spread, vias, fan)
    LEAD = UX + 3.375 + 0.45                                              # fan lines straighten here
    cs_pin = {1: 16, 2: 17, 3: 18, 4: 19, 5: 21, 6: 22, 7: 23, 8: 24, 9: 25, 10: 26, 11: 27}
    slot = {cs: (cs - 1 if cs <= 4 else cs) for cs in range(1, 12)}       # via slot; slot 4 is PVCC
    yv = [YV0 + SPREAD * p for p in range(12)]
    xv = [XA if p % 2 == 0 else XB for p in range(12)]
    for k in range(N):                                                    # k = 0 innermost
        i = N - 1 - k
        cs = cs_of(i)
        p = slot[cs]
        xe = XE0 + FUN * k
        ck = C0 + 0.6 * k
        ty = xy(i, 0)[1] - DY
        rows[i].append(xe)
        path([(xe, ty), (xe, ck - xe), (ck - yv[p], yv[p]), (xv[p], yv[p])], f"CS{cs}", "F")
        pb.via(xv[p], yv[p], f"CS{cs}", d=VIA_D, drill=VIA_DRILL)
        px, py = pad(cs_pin[cs])
        if cs <= 8:                                                       # east side: straight lead-in
            path([(xv[p], yv[p]), (XA - 0.45, yv[p]), (LEAD, py), (px, py)], f"CS{cs}", "B")
        else:                                                             # south side, from below
            path([(xv[p], yv[p]), (px, yv[p]), (px, py)], f"CS{cs}", "B")
    for i, xs in rows.items():
        y = xy(i, 0)[1] - DY
        path([(min(xs), y), (max(xs), y)], f"CS{cs_of(i)}", "F")
    # PVCC (pin 20) takes via slot 4; PVCC (pin 29) gets a via just below it.  Both join on top copper.
    px, py = pad(20)
    path([(xv[4], yv[4]), (XA - 0.45, yv[4]), (LEAD, py), (px, py)], "VBAT", "B", 0.2)
    pb.via(xv[4], yv[4], "VBAT", d=VIA_D, drill=VIA_DRILL)
    x29, y29 = pad(29)
    v29 = (x29, y29 + 1.15)
    path([(x29, y29), v29], "VBAT", "B", 0.2)
    pb.via(*v29, "VBAT")

    # ------------------------------------------------ west side -> spring-pin dots, nested
    lands = dict(zip(K.LINK_AB, K.LINK_XY))
    turns = [("LED_SDB", 46, -13.4), ("LED_INTB", 45, -14.0), ("SCL", 42, -14.6), ("SDA", 41, -15.2),
             ("3V3", 39, -15.8), ("VBAT", 38, -16.4)]
    for net, n, xt in turns:
        px, py = pad(n)
        lx, ly = lands[net]
        path([(px, py), (xt, py), (xt, ly), (lx, ly)], net, "B", W)
    a37, a38 = pad(37), pad(38)
    path([a37, (a37[0] - 0.65, a37[1]), (a38[0] - 0.65, a38[1])], "VBAT", "B", 0.2)
    # VBAT up to the top side and across to the two PVCC vias
    vt = (-6.2, pad(38)[1] + 0.75)                                        # below the VBAT line, clear of 3V3
    path([(vt[0], pad(38)[1]), vt], "VBAT", "B", 0.25)
    pb.via(*vt, "VBAT")
    yb = 20.45
    path([vt, (v29[0], vt[1]), v29], "VBAT", "F", 0.3)
    path([(v29[0], vt[1]), (v29[0], yb), (XA - 0.8, yb), (xv[4], yv[4])], "VBAT", "F", 0.3)

    # ------------------------------------------------ passives, ground, labels
    # R_ISET straight under its pin; PVCC(29) decoupling beside its via; the rest in two rows below
    # the west escape lines, clear of everything else on this side.
    r1 = (pad(35)[0], pad(35)[1] + 1.95)
    for rot in (90, 270):                                                 # pad 1 (ISET) towards the pin
        pb.place("R1", r1[0], r1[1], rot, back=True)
        if pb.pad_xy("R1", "1")[1] < pb.pad_xy("R1", "2")[1]:
            break
    path([pad(35), pb.pad_xy("R1", "1")], "ISET", "B")
    def upright(ref, x, y):                                               # vertical, pad 1 on top
        for rot in (90, 270):
            pb.place(ref, x, y, rot, back=True)
            if pb.pad_xy(ref, "1")[1] < pb.pad_xy(ref, "2")[1]:
                return pb.pad_xy(ref, "1")
    # VBAT decoupling stands under the VBAT escape line, each cap stubbed straight up to it
    yl = pad(38)[1]
    for ref, x, cy in (("C2", -7.2, 21.95), ("C1", -8.4, 21.95), ("C3", -9.9, 22.3), ("C4", -11.6, 22.3)):
        p1 = upright(ref, x, cy)
        path([(x, yl), p1], "VBAT", "B", 0.25)
    p1 = upright("C5", v29[0] - 1.3, v29[1] + 0.6)                       # PVCC(29) decoupling
    path([v29, (p1[0], v29[1]), p1], "VBAT", "B", 0.25)
    place = {"R2": (-9.0, 16.1, 90), "C7": (-18.0, 10.7, 0)}
    for ref, (x, y, r) in place.items():
        pb.place(ref, x, y, r, back=True)
    K.board_label(pb, "A · FACE  1/3", "B", at=(12.6, 23.3))

    from router import Router
    ox, oy = pb.ox, pb.oy
    failed = []
    rt = K.make_router(pb, Router, maxw=0.25, clearance=0.16, layer_cost={"F": 0.3, "B": 0.0},
                       edge=0.9)                      # no keyline on this hidden side
    # the top side is the face: only the deliberate wiring above goes there.  Router copper may use
    # it only in a small window over the driver, where the driver's own ground ring needs a hop.
    win = (UX - 5.0, UY - 3.4, UX + 3.2, K.HALF - 0.6)
    H = K.HALF
    for r in [(-H, -H, H, win[1]), (-H, win[1], win[0], H), (win[2], win[1], H, H)]:
        rt.keepout.append(("F", ox + r[0], oy + r[1], ox + r[2], oy + r[3]))
    nets = [("LED_SDB", 0.2), ("ISET", 0.2), ("3V3", 0.25), ("GND", 0.25), ("VBAT", 0.25)]
    nets = [n for n in nets if n[0] in first] + [n for n in nets if n[0] not in first]
    for net, w in nets:
        cop = [("track", L, a, b, ww) for L, a, b, ww, n in pb.tracks if n == "/" + net] + \
              [("via", p) for p, n in pb.vias if n == "/" + net]
        ends = [a for _, L, a, b, ww in [c for c in cop if c[0] == "track"]] + \
               [b for _, L, a, b, ww in [c for c in cop if c[0] == "track"]]

        def wired(pd):          # a pad that deterministic copper already reaches
            bb = pd.GetBoundingBox()
            x1, y1 = pb.pcbnew.ToMM(bb.GetLeft()), pb.pcbnew.ToMM(bb.GetTop())
            x2, y2 = pb.pcbnew.ToMM(bb.GetRight()), pb.pcbnew.ToMM(bb.GetBottom())
            return any(x1 - 1e-3 <= e[0] <= x2 + 1e-3 and y1 - 1e-3 <= e[1] <= y2 + 1e-3 for e in ends)

        pads = [pd for fp in pb.fps.values() for pd in fp.Pads()
                if pd.GetNetname() == "/" + net and not wired(pd) and rt.pad_cells(pd)[0]]
        seeds = rt.copper_cells(cop) if cop else None
        ok, tr, vs = rt.route_net("/" + net, pads, w, seeds=seeds)
        print(f"  route {net:9s} {'ok' if ok else 'FAILED'} {len(tr):3d} segs {len(vs)} vias")
        if not ok:
            failed.append(net)
            continue
        for L, a, b, ww, n in tr:
            pb.track((a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy), ww, net, L)
        for (x, y), n in vs:
            pb.via(x - ox, y - oy, net)
    h = K.HALF - 0.6
    pb.zone("GND", "B", [(-h, -h), (h, -h), (h, h), (-h, h)], clearance=0.2, min_w=0.2)
    pb.text("TinyDie Tumble", 12.6, 21.8, layer="B.SilkS", size=0.9)
    out_pcb = pb.finish(clearance=0.16, track=0.2)
    if failed:
        print("UNROUTED:", failed)
    return out_pcb, failed


if __name__ == "__main__":
    first = []
    for attempt in range(1, 4):
        pcb, failed = build(first)
        print(f"attempt {attempt}: {len(failed)} unrouted {failed}")
        if not failed:
            break
        first = failed + [f for f in first if f not in failed]
    print(pcb)
    sys.exit(1 if failed else 0)
