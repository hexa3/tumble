#!/usr/bin/env bash
# Rebuild the three boards from scratch and collect everything worth keeping in release/:
#
#   release/<board>/     KiCad project (pcb, sch, pro, dru, lib tables), netlist.json, drc.rpt
#   release/lib/         Tumble footprints + symbols (the projects point at ../lib)
#   release/fab/         gerber zips, BOMs, pos files, JLCPCB bom/cpl, hand-solder list
#   release/renders/     3D renders, top / bottom / iso
#   release/all/         every board's pcb/sch/pro + BOMs (full and JLC) + bom-total, flat in one folder;
#                        kicanvas.org/?github=<repo>/tree/main/hardware/release/all shows all three boards
#
# Needs KiCad 10: pcbnew only imports in the system python, not conda's.
# The base board alone takes ~10 minutes to route.
set -euo pipefail

HW="$(cd "$(dirname "$0")" && pwd)"
PY=/usr/bin/python3
BOARDS=(face core base)
OUT="$HW/release"

cd "$HW/gen"
$PY fplib.py
for b in "${BOARDS[@]}"; do
    echo "== $b"
    $PY -u "gen_$b.py"
done

for b in "${BOARDS[@]}"; do
    if ! kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations \
            -o "$HW/$b/drc.rpt" "$HW/$b/$b.kicad_pcb" > /dev/null; then
        echo "DRC failed on $b, see $HW/$b/drc.rpt"
        exit 1
    fi
    echo "  drc $b clean"
done

$PY fab.py

rm -rf "$OUT"
mkdir -p "$OUT/fab" "$OUT/renders"
cp -r "$HW/lib" "$OUT/lib"
for b in "${BOARDS[@]}"; do
    mkdir -p "$OUT/$b" "$OUT/all"
    cp "$HW/$b"/{"$b".kicad_pcb,"$b".kicad_sch,"$b".kicad_pro,"$b".kicad_dru,fp-lib-table,sym-lib-table,netlist.json,drc.rpt} "$OUT/$b/"
    cp "$HW/$b"/{"$b".kicad_pcb,"$b".kicad_sch,"$b".kicad_pro} "$HW/fab/$b-bom.csv" "$OUT/all/"
    cp "$HW/fab/jlc/$b-bom.csv" "$OUT/all/$b-jlc-bom.csv"
    cp "$HW/fab/$b-gerbers.zip" "$HW/fab/$b-bom.csv" "$HW/fab/$b-pos.csv" "$OUT/fab/"
    pcb="$HW/$b/$b.kicad_pcb"
    kicad-cli pcb render --quality high --side top    -w 1600 -h 1600 -o "$OUT/renders/$b-top.png"    "$pcb" > /dev/null
    kicad-cli pcb render --quality high --side bottom -w 1600 -h 1600 -o "$OUT/renders/$b-bottom.png" "$pcb" > /dev/null
    kicad-cli pcb render --quality high --rotate '-45,0,45' --perspective -w 1600 -h 1200 \
        -o "$OUT/renders/$b-iso.png" "$pcb" > /dev/null
done
cp "$HW/fab/bom-total.csv" "$OUT/fab/"
cp "$HW/fab/bom-total.csv" "$OUT/all/"
cp -r "$HW/fab/jlc" "$OUT/fab/jlc"
echo "release -> $OUT"
