#!/usr/bin/env python3
"""Export manufacturing files for the three boards (PCBs from OSH Park, parts from DigiKey).

  fab/<board>-gerbers.zip   Gerbers + Excellon drill (OSH Park also accepts the .kicad_pcb directly)
  fab/<board>-bom.csv       Qty, References, Value, Manufacturer, MPN, DigiKey PN, checked, Description
  fab/<board>-pos.csv       part positions (stencil / hand placement reference)
  fab/bom-total.csv         one line per orderable part across all three boards, priced
  fab/jlc/<board>-bom.csv   JLCPCB assembly BOM (Comment, Designator, Footprint, LCSC Part #)
  fab/jlc/<board>-cpl.csv   JLCPCB placement file (Designator, Mid X, Mid Y, Layer, Rotation)
  fab/jlc/hand-solder.csv   parts JLCPCB does not place
"""
import csv
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parts_db import HAND, JLC, JLC_ROT, LCSC, PARTS, checked, cheapest, entry, unit_price  # noqa: E402

GEN = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(GEN)
FAB = os.path.join(HW, "fab")
BOARDS = ["face", "core", "base"]
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask"


def cli(*args):
    r = subprocess.run(["kicad-cli", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)


def jlc_rot(footprint, rot):
    for prefix, add in JLC_ROT:
        if footprint.split(":")[-1].startswith(prefix):
            return (rot + add) % 360
    return rot % 360


def jlc_files(board, nl, groups, pos):
    """JLCPCB BOM + CPL for one board; returns the rows it leaves for hand soldering."""
    placed, hand = set(), []
    with open(os.path.join(FAB, "jlc", f"{board}-bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for key, refs in sorted(groups.items()):
            refs = sorted(refs, key=lambda r: (r[0], int("".join(c for c in r if c.isdigit()) or 0)))
            if key in JLC:
                w.writerow([JLC[key][1], ",".join(refs), nl[refs[0]]["footprint"].split(":")[-1], JLC[key][0]])
                placed.update(refs)
            else:
                hand.append([board, " ".join(refs), entry(key)[1], HAND.get(key, "no JLCPCB part chosen")])
    with open(pos) as fi, open(os.path.join(FAB, "jlc", f"{board}-cpl.csv"), "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in csv.DictReader(fi):
            if r["Ref"] in placed:
                rot = jlc_rot(nl[r["Ref"]]["footprint"], float(r["Rot"]))
                w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}mm', f'{float(r["PosY"]):.4f}mm',
                            "Top" if r["Side"] == "top" else "Bottom", f"{rot:g}"])
    return hand


def main():
    os.makedirs(FAB, exist_ok=True)
    total = {}
    hand = []
    os.makedirs(os.path.join(FAB, "jlc"), exist_ok=True)
    for b in BOARDS:
        pcb = os.path.join(HW, b, f"{b}.kicad_pcb")
        gd = os.path.join(FAB, b, "gerbers")
        shutil.rmtree(gd, ignore_errors=True)
        os.makedirs(gd)
        cli("pcb", "export", "gerbers", "-o", gd + "/", "-l", LAYERS, pcb)
        cli("pcb", "export", "drill", "-o", gd + "/", pcb)
        shutil.make_archive(os.path.join(FAB, f"{b}-gerbers"), "zip", gd)
        pos = os.path.join(FAB, b, "pos.csv")
        cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "-o", pos, pcb)
        nl = json.load(open(os.path.join(HW, b, "netlist.json")))
        groups = {}
        for ref, d in nl.items():
            if d.get("part") and not d.get("dnp"):
                groups.setdefault(d["part"], []).append(ref)
        with open(os.path.join(FAB, f"{b}-bom.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Qty", "References", "Value", "Manufacturer", "MPN", "DigiKey PN", "Checked", "Description"])
            for key, refs in sorted(groups.items()):
                man, mpn, dk, desc, _, _ = entry(key)
                w.writerow([len(refs), " ".join(sorted(refs)), nl[refs[0]]["value"], man, mpn, dk, checked(key), desc])
                total[key] = total.get(key, 0) + len(refs)
        shutil.copy(pos, os.path.join(FAB, f"{b}-pos.csv"))
        hand += jlc_files(b, nl, groups, pos)
        print(f"  {b:5s} gerbers + {len(groups)} BOM lines / {sum(len(v) for v in groups.values())} parts")
    with open(os.path.join(FAB, "jlc", "hand-solder.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Board", "References", "Part", "Why"])
        w.writerows(hand)
    cost = cheap = 0.0
    with open(os.path.join(FAB, "bom-total.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Qty", "Manufacturer", "MPN", "DigiKey PN", "DigiKey unit $", "LCSC #", "LCSC alt MPN",
                    "LCSC unit $", "Buy from", "Line $", "Checked", "Note"])
        for key, n in sorted(total.items(), key=lambda kv: -kv[1] * cheapest(kv[0], kv[1])[1]):
            man, mpn, dk, desc, _, stock = entry(key)
            u = unit_price(key, n)
            src, cu = cheapest(key, n)
            lc = LCSC.get(key, ("", "", "", ""))
            cost += u * n
            cheap += cu * n
            w.writerow([n, man, mpn, dk, f"{u:.4f}", lc[0], lc[1], lc[2], src, f"{cu * n:.2f}", checked(key),
                        lc[3] or stock])
    print(f"  parts for one unit: DigiKey only ${cost:.2f}; cheapest of DigiKey/LCSC ${cheap:.2f} (LCSC prices are estimates)")


if __name__ == "__main__":
    main()
