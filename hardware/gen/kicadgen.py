"""Shared KiCad writers for every TinyDie Tumble board.

A board is described once as a list of parts:

    Part(ref, (lib, symbol), value, footprint, pins={pin: net}, part="<parts_db key>")

Every symbol carries Manufacturer / MPN / DigiKey_PN fields from parts_db.  Symbols with no
`part` are PCB copper (joints, pads, test points) and say so in those fields.

`write_schematic` turns that into a flat, label-connected .kicad_sch (auto grid
layout) and `PcbBuilder` places the same parts with matching UUID paths so
KiCad's schematic<->PCB parity check passes.
"""
import copy
import json
import math
import os
import uuid
from dataclasses import dataclass, field

from parts_db import NO_PART, entry
from sexp import Q, dump, find, find1, parse

GEN = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(GEN)
SYMDIR = "/usr/share/kicad/symbols"
FPDIR = "/usr/share/kicad/footprints"
LOCAL_FP = os.path.join(HW, "lib", "Tumble.pretty")
LOCAL_SYM = os.path.join(HW, "lib", "Tumble.kicad_sym")


def v4(name):
    return str(uuid.UUID(bytes=uuid.uuid5(uuid.NAMESPACE_URL, name).bytes, version=4))


@dataclass
class Part:
    ref: str
    sym: tuple
    value: str
    footprint: str
    pins: dict
    part: str = ""           # parts_db key; "" = PCB feature, nothing to buy
    dnp: bool = False
    group: str = ""          # schematic grouping/ordering key
    extra: dict = field(default_factory=dict)


# ------------------------------------------------------------------ symbols
_libs = {}


def lib_symbol(lib, name):
    if lib not in _libs:
        path = LOCAL_SYM if lib == "Tumble" else f"{SYMDIR}/{lib}.kicad_sym"
        _libs[lib] = parse(open(path).read())
    syms = {s[1]: s for s in find(_libs[lib], "symbol")}
    sym = copy.deepcopy(syms[name])
    ext = find1(sym, "extends")
    if ext:
        base = copy.deepcopy(syms[ext[1]])
        props = {p[1]: p for p in find(sym, "property")}
        out = [base[0], Q(name)]
        for item in base[2:]:
            if isinstance(item, list) and item[0] == "property" and item[1] in props:
                out.append(props.pop(item[1]))
            elif isinstance(item, list) and item[0] == "symbol":
                item[1] = Q(item[1].replace(ext[1], name))
                out.append(item)
            else:
                out.append(item)
        sym = out
    pins = {}
    for sub in find(sym, "symbol"):
        for p in find(sub, "pin"):
            at = find1(p, "at")
            pins.setdefault(find1(p, "number")[1],
                            (float(at[1]), float(at[2]), float(at[3]), find1(p, "name")[1]))
    sym[1] = Q(f"{lib}:{name}")
    # bounding box of the body for layout
    xs, ys = [0.0], [0.0]
    for (px, py, _, _) in pins.values():
        xs.append(px)
        ys.append(py)
    bbox = (min(xs), min(ys), max(xs), max(ys))
    return sym, pins, bbox


def pin_xy(x, y, rot, px, py):
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return round(x + rx, 2), round(y - ry, 2)


def _prop(name, value, x, y, hide=False, size=1.27):
    p = ["property", Q(name), Q(value), ["at", x, y, 0],
         ["effects", ["font", ["size", size, size]]]]
    if hide:
        p[-1].append(["hide", "yes"])
    return p


def _lib_prop(libsym, name, value, x, y, rot, hide=False):
    lp = [p for p in find(libsym, "property") if p[1] == name][0]
    at = find1(lp, "at")
    fx, fy = pin_xy(x, y, rot, float(at[1]), float(at[2]))
    eff = copy.deepcopy(find1(lp, "effects"))
    eff = [e for e in eff if not (isinstance(e, list) and e[0] == "hide")]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", fx, fy, float(at[3]) if len(at) > 3 else 0], eff]


LBL = {(1, 0): (0, ["left", "bottom"]), (-1, 0): (180, ["right", "bottom"]),
       (0, -1): (90, ["left", "bottom"]), (0, 1): (270, ["right", "bottom"])}


def _outward(rot, ang):
    a = math.radians(ang + 180 + rot)
    return round(math.cos(a)), -round(math.sin(a))


def part_fields(p):
    """Manufacturer / MPN / DigiKey_PN symbol fields for a Part."""
    if not p.part:
        return [("Manufacturer", NO_PART[0]), ("MPN", NO_PART[1]), ("DigiKey_PN", NO_PART[0])]
    man, mpn, dk, desc, _, _ = entry(p.part)
    return [("Manufacturer", man), ("MPN", mpn), ("DigiKey_PN", dk or "TBD (verify)"), ("Description", desc)]
