#!/usr/bin/env python3
"""Write the project footprint library (Tumble.pretty).

Footprints the stock KiCad library doesn't have:
  Pogo_MillMax_0900-2    Mill-Max 0900-2-15-20-75-14-11-0 SMT spring pin, 1.83 mm pad (datasheet)
  PogoLand_D2.2          gold landing dot a spring pin presses on (other board)
  BatteryPads_2x2.2x2.8  solder pads for the Li-Po leads
  LRA_Pads               solder pads for the haptic actuator's two leads
  GoldDot_D1.5           bare ENIG test pad
  GoldDot_D3.0           die-pip-sized ENIG test pad for the caseback
"""
import os
import re
import uuid

from sexp import Q, dump

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib", "Tumble.pretty")
KFP = "/usr/share/kicad/footprints"
KSYM = "/usr/share/kicad/symbols"


def u(tag):
    return Q(str(uuid.uuid5(uuid.NAMESPACE_URL, "tumble-fp/" + tag)))


def text(kind, val, x, y, layer, size=0.8, hide=False):
    t = ["property", Q(kind), Q(val), ["at", x, y, 0], ["layer", Q(layer)],
         ["uuid", u(kind + val + layer)],
         ["effects", ["font", ["size", size, size], ["thickness", round(size * 0.15, 3)]]]]
    if hide:
        t.insert(5, ["hide", "yes"])
    return t


def line(a, b, layer, w=0.1):
    return ["fp_line", ["start", a[0], a[1]], ["end", b[0], b[1]],
            ["stroke", ["width", w], ["type", "solid"]], ["layer", Q(layer)], ["uuid", u(f"{a}{b}{layer}")]]


def rect(x1, y1, x2, y2, layer, w=0.05):
    return ["fp_rect", ["start", x1, y1], ["end", x2, y2],
            ["stroke", ["width", w], ["type", "solid"]], ["fill", "no"], ["layer", Q(layer)],
            ["uuid", u(f"r{x1}{y1}{x2}{y2}{layer}")]]


def circle(cx, cy, r, layer, w=0.1, fill=False):
    return ["fp_circle", ["center", cx, cy], ["end", cx + r, cy],
            ["stroke", ["width", w], ["type", "solid"]], ["fill", "yes" if fill else "no"],
            ["layer", Q(layer)], ["uuid", u(f"c{cx}{cy}{r}{layer}")]]


def smd(num, x, y, w, h, shape="rect", layers=("F.Cu", "F.Mask", "F.Paste"), rr=None):
    p = ["pad", Q(num), "smd", shape, ["at", x, y], ["size", w, h],
         ["layers"] + [Q(L) for L in layers]]
    if rr:
        p.append(["roundrect_rratio", rr])
    p.append(["uuid", u(f"p{num}{x}{y}")])
    return p


def footprint(name, descr, items, attr="smd", model=None, extra=None):
    fp = ["footprint", Q(name), ["version", 20241229], ["generator", Q("tinydie-tumble")],
          ["generator_version", Q("1.0")], ["layer", Q("F.Cu")],
          text("Reference", "REF**", 0, -2.0, "F.SilkS", hide=True),
          text("Value", name, 0, 2.0, "F.Fab", hide=True),
          ["descr", Q(descr)],
          ["attr"] + attr.split()]
    fp += extra or []
    fp += items
    if model:
        fp.append(["model", Q(model), ["offset", ["xyz", 0, 0, 0]], ["scale", ["xyz", 1, 1, 1]],
                   ["rotate", ["xyz", 0, 0, 0]]])
    fp.append(["embedded_fonts", "no"])
    with open(os.path.join(LIB, name + ".kicad_mod"), "w") as f:
        f.write(dump(fp) + "\n")


def main():
    os.makedirs(LIB, exist_ok=True)
    footprint("Pogo_MillMax_0900-2", "SMT spring pin, 5 mm class: 2.2 mm pad fits Mill-Max 0900-2 (1.83 mm) and 2 mm-flange LCSC pins",
              [smd("1", 0, 0, 2.2, 2.2, shape="circle"),
               circle(0, 0, 0.915, "F.Fab", 0.1), circle(0, 0, 0.535, "F.Fab", 0.1),
               circle(0, 0, 1.25, "F.CrtYd", 0.05)])
    footprint("PogoLand_D2.2", "Landing pad for a spring pin on the neighbouring board",
              [smd("1", 0, 0, 2.2, 2.2, shape="circle", layers=("F.Cu", "F.Mask")),
               circle(0, 0, 1.3, "F.CrtYd", 0.05)], attr="smd exclude_from_pos_files")
    footprint("BatteryPads_2x2.2x2.8", "Solder pads for the LiPo leads: 1 = BAT+, 2 = BAT-",
              [smd("1", -1.6, 0, 2.2, 2.8, layers=("F.Cu", "F.Mask")),
               smd("2", 1.6, 0, 2.2, 2.8, layers=("F.Cu", "F.Mask")),
               rect(-2.95, -1.65, 2.95, 1.65, "F.CrtYd")], attr="smd")
    footprint("LRA_Pads", "Solder pads for the LRA leads (actuator body is glued beside them)",
              [smd("1", -1.0, 0, 1.4, 1.8, layers=("F.Cu", "F.Mask")),
               smd("2", 1.0, 0, 1.4, 1.8, layers=("F.Cu", "F.Mask")),
               rect(-1.95, -1.15, 1.95, 1.15, "F.CrtYd")], attr="smd")
    footprint("GoldDot_D1.5", "Bare ENIG test pad",
              [smd("1", 0, 0, 1.5, 1.5, shape="circle", layers=("F.Cu", "F.Mask")),
               circle(0, 0, 0.9, "F.CrtYd", 0.05)], attr="smd exclude_from_pos_files exclude_from_bom")
    footprint("GoldDot_D3.0", "Bare ENIG test pad, die-pip size (caseback)",
              [smd("1", 0, 0, 3.0, 3.0, shape="circle", layers=("F.Cu", "F.Mask")),
               circle(0, 0, 1.7, "F.CrtYd", 0.05)], attr="smd exclude_from_pos_files exclude_from_bom")
    # LIS3DH LGA-16 with 0.34 mm pads (gaps 0.16 mm), as used on the TinyDie Cube
    name = "LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y"
    src = open(f"{KFP}/Package_LGA.pretty/{name}.kicad_mod").read()
    out = src.replace(f'(footprint "{name}"', '(footprint "LGA-16_3x3mm_P0.5mm_FINE"', 1)
    out, n1 = re.subn(r"\(size 0\.55 0\.35\)", "(size 0.55 0.34)", out)
    out, n2 = re.subn(r"\(size 0\.35 0\.55\)", "(size 0.34 0.55)", out)
    assert n1 + n2 == 16, (n1, n2)
    open(os.path.join(LIB, "LGA-16_3x3mm_P0.5mm_FINE.kicad_mod"), "w").write(out)
    # MSOP-10 with 0.30 mm pads: the stock 0.35 mm pads leave 0.150 mm gaps, under OSH Park's 6 mil
    src = open(f"{KFP}/Package_SO.pretty/MSOP-10_3x3mm_P0.5mm.kicad_mod").read()
    out = src.replace('(footprint "MSOP-10_3x3mm_P0.5mm"', '(footprint "MSOP-10_3x3mm_P0.5mm_OSH"', 1)
    out, n = re.subn(r"\(size 1\.5 0\.35\)", "(size 1.5 0.3)", out)
    assert n == 10, n
    open(os.path.join(LIB, "MSOP-10_3x3mm_P0.5mm_OSH.kicad_mod"), "w").write(out)
    print("footprints ->", LIB)


if __name__ == "__main__":
    main()
