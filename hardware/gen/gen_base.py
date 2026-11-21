#!/usr/bin/env python3
"""Board C, BASE: USB-C, ESD, Li-Po charger, 3.3 V LDO, USB-UART bridge, fuel gauge, battery bay.

Top side (faces the CORE): USB-C on the south edge, power parts and the MCP2221A bridge in the
margins, the Li-Po cell in the reserved bay, spring pins up to the CORE at the east/west edges.
The bridge is powered only while USB is plugged in (P-FET switched by VBUS), and talks to the MCU
over one wire: its TX through 1k, its RX direct (single-wire half-duplex UART).
Bottom side is the caseback: no components.  Six gold pads laid out as the "6" face -- SWDIO, SWCLK,
3V3, GND for an ST-Link pogo jig, plus VBAT and VBUS -- gold lettering, and a gold outline of TinyDie
Mk I's SOIC-8 footprint.

Run with KiCad's Python:  /usr/bin/python3 gen_base.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as K  # noqa: E402
from kicadgen import HW, Part, PcbBuilder, write_schematic  # noqa: E402

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
SOT5 = "Package_TO_SOT_SMD:SOT-23-5"
USBC_FP = "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"
USB_EDGE = 3.675            # the footprint's "PCB Edge" line
BAY = (-17.0, -15.0, 17.0, 10.0)  # battery bay: 34 x 25 mm, cell <= 3.5 mm thick (4.5 mm gap)

RES = {"1k": "R1k_0402", "5.1k": "R5k1_0402", "10k": "R10k_0402", "20k": "R20k_0402", "100k": "R100k_0402"}
CAP = {"1uF": "C1u_0402", "4.7uF": "C4u7_0402", "10uF": "C10u_0603", "100nF": "C100n_0402",
       "470nF": "C470n_0402"}


def R(ref, val, a, b):
    return Part(ref, ("Device", "R"), val, R0402, {"1": a, "2": b}, part=RES[val], group="R")


def C(ref, val, a, b):
    return Part(ref, ("Device", "C"), val, C0603 if val == "10uF" else C0402, {"1": a, "2": b},
                part=CAP[val], group="C")


def parts():
    usb = {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "A4": "VBUS", "B4": "VBUS",
           "A9": "VBUS", "B9": "VBUS", "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP",
           "A7": "USB_DM", "B7": "USB_DM", "SH": "GND"}
    P = [
        Part("J1", ("Connector", "USB_C_Receptacle_USB2.0_16P"), "USB-C", USBC_FP, usb, part="USBC", group="J"),
        Part("U1", ("Power_Protection", "USBLC6-2SC6"), "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
             {"1": "USB_DP", "2": "GND", "3": "USB_DM", "4": "USB_DM", "5": "VBUS", "6": "USB_DP"},
             part="USBLC6", group="U"),
        Part("U2", ("Battery_Management", "MCP73831-2-OT"), "MCP73831-2", SOT5,
             {"1": "CHG_STAT", "2": "GND", "3": "VBAT", "4": "VBUS", "5": "PROG"}, part="MCP73831", group="U"),
        # RT9080-33 has the AP2112K pinout: 1 VIN, 2 GND, 3 EN, 5 VOUT
        Part("U3", ("Regulator_Linear", "AP2112K-3.3"), "RT9080-33GJ5", SOT5,
             {"1": "VBAT", "2": "GND", "3": "VBAT", "5": "3V3"}, part="RT9080", group="U"),
        Part("BT1", ("Connector_Generic", "Conn_01x02"), "Li-Po 1S", "Tumble:BatteryPads_2x2.2x2.8",
             {"1": "VBAT", "2": "GND"}, part="LIPO", group="BT"),
        R("R1", "5.1k", "CC1", "GND"), R("R2", "5.1k", "CC2", "GND"),
        R("R3", "10k", "PROG", "GND"),                 # MCP73831: I = 1000 V / R_PROG = 100 mA
        C("C1", "4.7uF", "VBUS", "GND"), C("C2", "4.7uF", "VBAT", "GND"),
        C("C3", "1uF", "VBAT", "GND"), C("C4", "1uF", "3V3", "GND"), C("C5", "10uF", "3V3", "GND"),
        C("C6", "100nF", "VBUS", "GND"),
        # charge LED: MCP73831 STAT sinks while charging
        Part("D2", ("Device", "LED"), "RED", "LED_SMD:LED_0603_1608Metric", {"1": "CHG_STAT", "2": "LED_A"},
             part="LED_RED_0603", group="D"),
        R("R7", "1k", "VBUS", "LED_A"),
        # USB-UART bridge, powered from 3V3 only while VBUS is present (VUSB tied to VDD at 3.3 V)
        Part("U4", ("Interface_USB", "MCP2221AxSL"), "MCP2221A", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
             {"1": "3V3_USB", "4": "BR_RST", "5": "UART", "6": "BR_TX", "11": "3V3_USB", "12": "USB_DM",
              "13": "USB_DP", "14": "GND"}, part="MCP2221A", group="U"),
        R("R6", "1k", "BR_TX", "UART"), R("R8", "10k", "3V3_USB", "BR_RST"),
        C("C7", "100nF", "3V3_USB", "GND"), C("C8", "470nF", "3V3_USB", "GND"),
        Part("Q1", ("Transistor_FET", "AO3401A"), "AO3401A", "Package_TO_SOT_SMD:SOT-23",
             {"1": "BR_PG", "2": "3V3", "3": "3V3_USB"}, part="AO3401A", group="Q"),
        Part("Q2", ("Transistor_FET", "2N7002"), "2N7002", "Package_TO_SOT_SMD:SOT-23",
             {"1": "BR_G", "2": "GND", "3": "BR_PG"}, part="2N7002", group="Q"),
        R("R9", "100k", "3V3", "BR_PG"), R("R10", "10k", "VBUS", "BR_G"), R("R11", "100k", "BR_G", "GND"),
        # fuel gauge: senses the cell on VDD; CELL is not connected on the MAX17048
        Part("U5", ("Tumble", "MAX17048"), "MAX17048", "Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.6mm",
             {"1": "GND", "3": "VBAT", "4": "GND", "6": "GND", "7": "SCL", "8": "SDA", "9": "GND"},
             part="MAX17048", group="U"),
        C("C9", "100nF", "VBAT", "GND"),
    ]
    dots = ["SWDIO", "SWCLK", "3V3", "GND", "VBAT", "VBUS"]
    P += [Part(f"TP{i + 1}", ("Connector", "TestPoint"), n, "Tumble:GoldDot_D3.0", {"1": n}, group="TP")
          for i, n in enumerate(dots)]
    P += K.pins(K.LINK_BC, "P") + K.holes()
    return P


PLACE = {
    # south margin, either side of the USB-C: protection, charging, charge LED, bridge
    "U1": (-8.4, 16.0, 0), "C6": (-8.4, 12.8, 0), "R1": (-5.0, 12.4, 90), "R2": (5.0, 12.4, 90),
    "U2": (9.0, 16.0, 0), "C1": (6.8, 14.6, 90), "R3": (9.0, 12.6, 0),
    "D2": (7.4, 21.6, 0), "R7": (9.6, 21.6, 0),
    "U4": (-14.6, 17.2, 0), "R6": (-8.6, 19.8, 0), "R8": (-8.6, 21.4, 0), "C7": (-11.2, 12.0, 90),
    "C8": (-12.4, 12.0, 90), "Q1": (16.4, 12.6, 0), "Q2": (14.6, 18.8, 0), "R9": (13.8, 12.2, 90),
    "R10": (13.0, 21.4, 0), "R11": (16.4, 21.4, 0),
    # north margin: battery pads, regulator, fuel gauge
    "BT1": (0.0, -18.6, 0), "U3": (8.0, -18.6, 0), "C3": (5.2, -18.6, 90), "C4": (10.8, -18.6, 90),
    "C5": (12.8, -18.6, 90), "U5": (-7.0, -18.6, 0), "C9": (-9.6, -18.6, 90),
}
DOTS = [(-8.0, -8.0), (8.0, -8.0), (-8.0, 0.0), (8.0, 0.0), (-8.0, 8.0), (8.0, 8.0)]   # the "6" face


def build(first=()):
    proj = "base"
    out = os.path.join(HW, proj)
    P = parts()
    nl = write_schematic(
        proj, "TinyDie Tumble - C BASE", P, out, paper="A3",
        notes=["Board C, BASE: USB-C -> USBLC6 -> MCP73831 (100 mA) -> Li-Po; RT9080 3.3 V LDO; MCP2221A bridge; MAX17048 gauge",
               "P1-P10 spring pins up to the CORE.  TP1-TP6 gold caseback pads, arranged as the six face (SWD jig).",
               "CC1/CC2 5.1k: USB 2.0 sink, 5 V only.  No power path: the system runs from the cell while charging."],
        flags=["GND", "VBUS", "3V3_USB"])
    pb = PcbBuilder(proj, out, nl, origin=(100.0, 100.0))
    K.outline(pb)
    K.keyline(pb, "FB")
    K.place_common(pb, pin_refs="P")
    pb.place("J1", 0.0, K.HALF - USB_EDGE, 0)
    for i, (x, y) in enumerate(DOTS):
        pb.place(f"TP{i + 1}", x, y, back=True)
    pb.place("C2", 0.0, -16.0, 0)                                      # battery decoupling, see below
    fixed = [r for r in pb.fps if r[0] in "PH" or r == "J1" or r.startswith("TP") or r == "C2"]
    K.autoplace(pb, PLACE, fixed=fixed, reserve=[("F",) + BAY])
    # battery decoupling: straight under the battery pads, wired to them directly
    for n in ("1", "2"):
        net = pb.netlist["C2"]["pads"][n]
        tgt = "1" if net == "VBAT" else "2"
        pb.track(pb.pad_xy("C2", n), pb.pad_xy("BT1", tgt), 0.3, net, "F")
    # fuel gauge: its ground pins tie inward to the exposed pad, which leaves through one stub to a via
    ex, ey = pb.pad_xy("U5", "9")
    for n in ("1", "4", "6"):
        px, py = pb.pad_xy("U5", n)
        pb.track((px, py), (ex + (0.25 if px > ex else -0.25), py), 0.25, "GND", "F")
    pb.track((ex, ey), (ex, ey - 1.75), 0.3, "GND", "F")          # away from the caseback title
    pb.via(ex, ey - 1.75, "GND")
    # the battery bay, drawn on the top silkscreen
    x1, y1, x2, y2 = BAY
    for a, b in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        pb.silk_line(a, b, w=0.15)
    pb.text("Li-Po 1S  <= 34 x 25 x 3.5 mm", 0.0, (y1 + y2) / 2, size=1.0)

    # ---------------------------------------------------- caseback art (bottom, read from below)
    K.gold_text(pb, "TINYDIE TUMBLE", 0.0, -17.6, side="B", size=1.8)
    K.gold_text(pb, "REV A · 2026", 0.0, -14.7, side="B", size=0.9)
    K.gold_text(pb, "OPPOSITE FACES SUM TO SEVEN", -17.5, 0.0, side="B", size=0.9, rot=90)
    K.gold_text(pb, "CREATED BY SHEHERYAR", 17.5, -2.0, side="B", size=0.9, rot=90)
    K.hex_badge(pb, 0.0, 0.0, side="B")                                    # the "6" face has no centre pip
    K.board_label(pb, "C · BASE  3/3", "B")
    for (x, y), t in zip(DOTS, ["SWDIO", "SWCLK", "3V3", "GND", "VBAT", "VBUS"]):
        pb.text(t, x, y + 2.6, layer="B.SilkS", size=0.7)
    # Mk I: the ATtiny412's SOIC-8 land pattern in gold, with its name
    mx, my = 15.0, 12.5
    for k in range(4):
        for sgn in (-1, 1):
            cx, cy = mx + sgn * 2.7, my - 1.905 + k * 1.27
            K.gold_rect(pb, cx - 0.775, cy - 0.3, cx + 0.775, cy + 0.3, side="B")
    K.art(pb, "B", mx - 3.5, my - 2.3, mx + 3.5, my + 2.3)
    K.gold_text(pb, "MK I", mx, my + 4.0, side="B", size=0.8)
    pb.text("ATtiny412", mx, my - 4.0, layer="B.SilkS", size=0.6)

    from router import Router
    ox, oy = pb.ox, pb.oy
    failed = []
    sig = [("USB_DP", 0.2), ("USB_DM", 0.2), ("CC1", 0.2), ("CC2", 0.2), ("PROG", 0.2),
           ("CHG_STAT", 0.2), ("LED_A", 0.2), ("UART", 0.2), ("BR_TX", 0.2), ("BR_RST", 0.2),
           ("BR_PG", 0.2), ("BR_G", 0.2), ("SDA", 0.2), ("SCL", 0.2), ("SWDIO", 0.2), ("SWCLK", 0.2)]
    pwr = [("3V3_USB", 0.3), ("VBUS", 0.3), ("VBAT", 0.3), ("3V3", 0.3)]
    sig = [n for n in sig if n[0] in first] + [n for n in sig if n[0] not in first]
    stub_ends, stubbed = K.escape_stubs(pb, ["U5"])                  # 0.5 mm DFN: stubs to route to
    for group, maxw in ((sig, 0.2), (pwr, 0.3)):
        # USB-C pads sit on x = 0.25 + n * 0.5: shift the 0.1 mm grid by 0.05 so they land on it
        rt = K.make_router(pb, Router, maxw=maxw, clearance=0.16, layer_cost={"F": 0.0, "B": 0.6},
                           shift=(-0.05, 0.0))
        for net, w in group:
            pads = [pd for fp in pb.fps.values() for pd in fp.Pads() if pd.GetNetname() == "/" + net
                    and (fp.GetReference(), pd.GetNumber()) not in stubbed]
            ok, tr, vs = rt.route_net("/" + net, pads, w, extra=stub_ends.get("/" + net))
            print(f"  route {net:9s} {'ok' if ok else 'FAILED'} {len(tr):3d} segs {len(vs)} vias")
            if not ok:
                failed.append(net)
                continue
            for L, a, b, ww, n in tr:
                pb.track((a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy), ww, net, L)
            for (x, y), n in vs:
                pb.via(x - ox, y - oy, net)

    print("  ground (vias, links, failed):", K.ground(pb, K.make_router(pb, Router, maxw=0.25)))
    print(f"  stitching vias: {K.stitch(pb, K.make_router(pb, Router, maxw=0.3), step=4.5)}")
    h = K.HALF - K.KEYLINE - 0.45
    for L in ("F", "B"):
        pb.zone("GND", L, [(-h, -h), (h, -h), (h, h), (-h, h)], clearance=0.25, min_w=0.2)

    out_pcb = pb.finish(clearance=0.16, track=0.2)
    if failed:
        print("UNROUTED:", failed)
    return out_pcb, failed


if __name__ == "__main__":
    first = []
    for attempt in range(1, 5):
        pcb, failed = build(first)
        print(f"attempt {attempt}: {len(failed)} unrouted {failed}")
        if not failed:
            break
        first = failed + [f for f in first if f not in failed]
    print(pcb)
    sys.exit(1 if failed else 0)
