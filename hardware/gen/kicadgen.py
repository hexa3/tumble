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


def write_schematic(project, title, parts, out_dir, rev="1.0", notes=(), paper="A3",
                    cols=None, flags=("GND",), comment=""):
    """Flat schematic: every pin gets a short wire stub and a net label."""
    root = v4(f"{project}-root")
    lib_syms, body = {}, []

    def need(lib, name):
        key = f"{lib}:{name}"
        if key not in lib_syms:
            lib_syms[key] = lib_symbol(lib, name)
        return lib_syms[key]

    def inst(lib_id, ref, value, fp, x, y, rot, pins, tag, libsym, in_bom=True, fields=(),
             dnp=False, hide_value=False, on_board=None):
        on_board = in_bom if on_board is None else on_board
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, rot], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if in_bom else "no"],
                ["on_board", "yes" if on_board else "no"], ["dnp", "yes" if dnp else "no"],
                ["uuid", Q(v4(f"{project}/{tag}"))],
                _lib_prop(libsym, "Reference", ref, x, y, rot, hide=not on_board),
                _lib_prop(libsym, "Value", value, x, y, rot, hide=hide_value),
                _prop("Footprint", fp, x, y, hide=True),
                _prop("Datasheet", "", x, y, hide=True)]
        for k, v in fields:
            node.append(_prop(k, v, x, y, hide=True))
        for n in pins:
            node.append(["pin", Q(n), ["uuid", Q(v4(f"{project}/{tag}/pin{n}"))]])
        node.append(["instances", ["project", Q(project),
                     ["path", Q("/" + root), ["reference", Q(ref)], ["unit", 1]]]])
        return node

    # --- layout: groups in columns, parts stacked
    groups = {}
    for p in parts:
        groups.setdefault(p.group or p.ref.rstrip("0123456789"), []).append(p)
    x0, y0 = 30.48, 40.64
    col_x, y = x0, y0
    page_h = {"A4": 190, "A3": 270, "A2": 400, "A1": 560}[paper]
    max_x = {"A4": 280, "A3": 400, "A2": 580, "A1": 820}[paper]
    netlist = {}
    col_w = 0
    for gname, gparts in groups.items():
        for p in gparts:
            lsym, pins, bb = need(*p.sym)
            w = (bb[2] - bb[0]) + 30
            h = (bb[3] - bb[1]) + 12.7
            if y + h > page_h:
                col_x += max(col_w, 40)
                y = y0
                col_w = 0
            col_w = max(col_w, w)
            # place symbol so its bbox top-left lands at (col_x, y)
            sx = round((col_x - bb[0] + 12.7) / 2.54) * 2.54
            sy = round((y + bb[3] + 2.54) / 2.54) * 2.54
            fields = part_fields(p)
            in_bom = bool(p.part)
            body.append(inst(f"{p.sym[0]}:{p.sym[1]}", p.ref, p.value, p.footprint, sx, sy, 0,
                             list(pins), p.ref, lsym, fields=fields, dnp=p.dnp, in_bom=in_bom,
                             on_board=True))
            netlist[p.ref] = dict(footprint=p.footprint, value=p.value, uuid=v4(f"{project}/{p.ref}"),
                                  pads=p.pins, part=p.part, fields=dict(fields), dnp=p.dnp,
                                  in_bom=bool(p.part),
                                  nc_pins={n: pins[n][3] for n in pins if not p.pins.get(n)})
            for num, (px, py, pang, pname) in pins.items():
                net = p.pins.get(num)
                ex, ey = pin_xy(sx, sy, 0, px, py)
                if not net:
                    body.append(["no_connect", ["at", ex, ey],
                                 ["uuid", Q(v4(f"{project}/nc/{p.ref}/{num}"))]])
                    continue
                d = _outward(0, pang)
                tx, ty = round(ex + d[0] * 2.54, 2), round(ey + d[1] * 2.54, 2)
                body.append(["wire", ["pts", ["xy", ex, ey], ["xy", tx, ty]],
                             ["stroke", ["width", 0], ["type", "default"]],
                             ["uuid", Q(v4(f"{project}/w/{p.ref}/{num}"))]])
                ang, just = LBL[d]
                body.append(["label", Q(net), ["at", tx, ty, ang],
                             ["effects", ["font", ["size", 1.0, 1.0]], ["justify"] + just],
                             ["uuid", Q(v4(f"{project}/l/{p.ref}/{num}"))]])
            y += h
        y += 5.08
    # PWR_FLAGs so ERC knows the rails are driven (they come in through joints/pads)
    lsym, _, _ = need("power", "PWR_FLAG")
    fx = round(min(col_x + col_w + 20, max_x - 30) / 2.54) * 2.54
    for i, net in enumerate(flags):
        fy = y0 + i * 12.7
        body.append(inst("power:PWR_FLAG", f"#FLG{i + 1:02d}", "PWR_FLAG", "", fx, fy, 0, ["1"],
                         f"flag{i}", lsym, in_bom=False, hide_value=True))
        body.append(["wire", ["pts", ["xy", fx, fy], ["xy", fx, fy + 2.54]],
                     ["stroke", ["width", 0], ["type", "default"]], ["uuid", Q(v4(f"{project}/fw{i}"))]])
        body.append(["label", Q(net), ["at", fx, fy + 2.54, 270],
                     ["effects", ["font", ["size", 1.0, 1.0]], ["justify", "right", "bottom"]],
                     ["uuid", Q(v4(f"{project}/fl{i}"))]])
    for i, t in enumerate(notes):
        body.append(["text", Q(t), ["exclude_from_sim", "no"], ["at", x0, 20.32 + i * 5.08, 0],
                     ["effects", ["font", ["size", 1.8, 1.8]], ["justify", "left", "bottom"]],
                     ["uuid", Q(v4(f"{project}/note{i}"))]])
    sch = ["kicad_sch", ["version", "20250114"], ["generator", Q("eeschema")],
           ["generator_version", Q("10.0")], ["uuid", Q(root)], ["paper", Q(paper)],
           ["title_block", ["title", Q(title)], ["date", Q("2026-11-10")], ["rev", Q(rev)],
            ["company", Q("TinyDie Tumble")], ["comment", 1, Q(comment or title)]],
           ["lib_symbols"] + [s for s, _, _ in lib_syms.values()]]
    sch += body
    sch += [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{project}.kicad_sch"), "w") as f:
        f.write(dump(sch) + "\n")
    with open(os.path.join(out_dir, "netlist.json"), "w") as f:
        json.dump(netlist, f, indent=1)
    return netlist
