#!/usr/bin/env python3
"""Board B, CORE: an 8-pin STM32G041J6, accelerometer, haptics, avalanche-noise entropy source.

All parts are on the top side, which faces the FACE board.  The bottom side faces the battery and is
kept flat: gold landing dots for the BASE board's spring pins, a Tag-Connect footprint for bring-up,
and labelled gold test pads.

The MCU has six I/O pins, each bonded to several GPIOs (KiCad symbol STM32G041J6Mx):
  pin 1  PB7...      NOISE_ADC   ADC1_IN11
  pin 4  PA2/NRST    UART        USART2_TX, single-wire half-duplex to the USB bridge on the base.
                                 NRST_MODE must be set to GPIO in the option bytes (once, over SWD).
  pin 5  PA9         SCL         I2C1
  pin 6  PA10        SDA         I2C1   (face driver 0x50, LIS3DH 0x18, DRV2605L 0x5A, MAX17048 0x36)
  pin 7  PA13        SWDIO       for 2 s after reset, then NOISE_EN (boost + amplifier on)
  pin 8  PA14/PB5    SWCLK       for 2 s after reset, then ACC_INT1 (wake), through 1k so a probe wins
The face's SDB is pulled up (driver shut down in software), the haptic driver's EN is tied high (it
idles in its STANDBY state, which the datasheet rates at the same 4 uA as shutdown) and its IN/TRIG is
grounded.  Battery state comes from the fuel gauge on the base, over I2C.

Run with KiCad's Python:  /usr/bin/python3 gen_core.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as K  # noqa: E402
from kicadgen import HW, Part, PcbBuilder, write_schematic  # noqa: E402

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
SOT3 = "Package_TO_SOT_SMD:SOT-23"
SOT5 = "Package_TO_SOT_SMD:SOT-23-5"

RES = {"100R": "R100_0402", "1k": "R1k_0402", "4.7k": "R4k7_0402", "10k": "R10k_0402",
       "100k": "R100k_0402", "1M": "R1M_0402"}
CAP = {"10pF": "C10p_0402", "100nF": "C100n_0402", "1uF": "C1u_0402", "4.7uF": "C4u7_0402",
       "10uF": "C10u_0603"}


def R(ref, val, a, b):
    return Part(ref, ("Device", "R"), val.replace("R", "Ω") if val.endswith("R") else val, R0402,
                {"1": a, "2": b}, part=RES[val], group="R")


def C(ref, val, a, b):
    return Part(ref, ("Device", "C"), val, C0603 if val == "10uF" else C0402, {"1": a, "2": b},
                part=CAP[val], group="C")


def TP(ref, net):
    return Part(ref, ("Connector", "TestPoint"), net, "Tumble:GoldDot_D1.5", {"1": net}, group="TP")


def parts():
    P = [
        Part("U1", ("MCU_ST_STM32G0", "STM32G041J6Mx"), "STM32G041J6M6", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
             {"1": "NOISE_ADC", "2": "3V3", "3": "GND", "4": "UART", "5": "SCL", "6": "SDA",
              "7": "SWDIO", "8": "SWCLK"}, part="STM32G041", group="U"),
        # LIS3DH (LGA-16): SA0 low = I2C address 0x18; CS high = I2C; pin 10 (RES) to GND; INT1 wakes the MCU
        Part("U2", ("Sensor_Motion", "LIS3DH"), "LIS3DH", "Tumble:LGA-16_3x3mm_P0.5mm_FINE",
             {"1": "3V3", "4": "SCL", "5": "GND", "6": "SDA", "7": "ACC_SA0", "8": "3V3", "10": "GND",
              "11": "ACC_INT1", "12": "GND", "14": "3V3"}, part="LIS3DH", group="U"),
        Part("U3", ("Driver", "DRV2605LDGS"), "DRV2605L", "Tumble:MSOP-10_3x3mm_P0.5mm_OSH",
             {"1": "HAPT_REG", "2": "SCL", "3": "SDA", "4": "GND", "5": "3V3", "6": "VBAT",
              "7": "LRA_P", "8": "GND", "9": "LRA_N", "10": "VBAT"}, part="DRV2605L", group="U"),
        Part("U4", ("Regulator_Switching", "TPS61040DBV"), "TPS61040", SOT5,
             {"1": "BST_SW", "2": "GND", "3": "BST_FB", "4": "SWDIO", "5": "VBAT"},
             part="TPS61040", group="U"),
        Part("L1", ("Device", "L"), "10uH", "Inductor_SMD:L_1210_3225Metric",
             {"1": "VBAT", "2": "BST_SW"}, part="L10u", group="L"),
        Part("D1", ("Device", "D_Schottky"), "1N5819HW", "Diode_SMD:D_SOD-123",
             {"1": "VBOOST", "2": "BST_SW"}, part="SCHOTTKY", group="D"),
        # avalanche junction: Q1 base-emitter reverse biased, collector open
        Part("Q1", ("Transistor_BJT", "MMBT3904"), "MMBT3904", SOT3,
             {"1": "GND", "2": "AVAL"}, part="MMBT3904", group="Q"),
        # Q2: common-emitter amplifier with collector-to-base feedback, powered from NOISE_EN (SWDIO)
        Part("Q2", ("Transistor_BJT", "MMBT3904"), "MMBT3904", SOT3,
             {"1": "AMP_B", "2": "GND", "3": "AMP_C"}, part="MMBT3904", group="Q"),
        Part("M1", ("Connector_Generic", "Conn_01x02"), "LRA", "Tumble:LRA_Pads",
             {"1": "LRA_P", "2": "LRA_N"}, part="LRA", group="M"),
        Part("J1", ("Connector", "Conn_ARM_SWD_TagConnect_TC2030-NL"), "SWD",
             "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical",
             {"1": "3V3", "2": "SWDIO", "4": "SWCLK", "5": "GND"}, group="J"),
        # boost: Vout = 1.233 V x (1 + 1M / 100k) = 13.6 V
        R("R1", "1M", "VBOOST", "BST_FB"), R("R2", "100k", "BST_FB", "GND"),
        C("C1", "10pF", "VBOOST", "BST_FB"), C("C2", "4.7uF", "VBAT", "GND"),
        C("C3", "1uF", "VBOOST", "GND"),
        R("R3", "10k", "VBOOST", "VNOISE"), C("C4", "1uF", "VNOISE", "GND"),
        R("R4", "100k", "VNOISE", "AVAL"), C("C5", "100nF", "AVAL", "AMP_B"),
        R("R5", "1M", "AMP_C", "AMP_B"), R("R6", "10k", "SWDIO", "AMP_C"),
        R("R7", "100R", "AMP_C", "NOISE_ADC"), R("R8", "100k", "SWDIO", "GND"),
        # MCU
        C("C6", "100nF", "3V3", "GND"), C("C8", "1uF", "3V3", "GND"), C("C9", "10uF", "3V3", "GND"),
        R("R9", "1k", "ACC_INT1", "SWCLK"), R("R13", "10k", "ACC_SA0", "GND"),   # address 0x18
        R("R10", "4.7k", "3V3", "SDA"), R("R11", "4.7k", "3V3", "SCL"), R("R12", "10k", "3V3", "LED_SDB"),
        # accelerometer, haptics
        C("C12", "1uF", "3V3", "GND"), C("C13", "100nF", "3V3", "GND"),
        C("C14", "1uF", "HAPT_REG", "GND"), C("C15", "1uF", "VBAT", "GND"),
    ]
    tps = ["NOISE_ADC", "UART", "LED_INTB", "SWDIO", "SWCLK", "3V3", "GND"]
    P += [TP(f"TP{i + 1}", n) for i, n in enumerate(tps)]
    P += K.pins(K.LINK_AB, "P") + K.lands(K.LINK_BC, "X") + K.holes()
    return P


# (x, y, rot) on the top side, seen from above, in placement order.  autoplace() keeps each part
# here if its courtyard is clear, otherwise moves it to the nearest clear spot.
#   MCU west of centre, square to the board; decoupling on the west side by its supply pins.
#   Accelerometer east of centre, away from the LRA and the standoffs.
#   Haptics in the south-east: LRA body glued in the circle drawn on the silkscreen, driver beside its pads.
#   Entropy chain in the south-west, flowing west -> east: boost, filter, junction, amplifier, ADC.
LRA_C, LRA_R = (11.5, 5.0), 4.1          # body: 8 mm coin
PLACE = {
    "U1": (-4.0, -4.0, 0), "C6": (-9.8, -4.0, 90), "C8": (-11.0, -4.0, 90), "C9": (-4.0, -8.6, 0),
    "R9": (1.6, 0.6, 90), "R10": (2.0, -7.4, 90), "R11": (3.2, -7.4, 90), "R12": (4.4, -7.4, 90), "R13": (11.2, -1.4, 0),
    "U2": (7.5, -4.0, 0), "C12": (10.0, -8.6, 90), "C13": (11.2, -8.6, 90),
    "M1": (11.5, 11.6, 0), "U3": (11.5, 15.4, 0), "C14": (7.6, 19.2, 90), "C15": (17.0, 18.0, 90),
    "C2": (-15.6, 9.0, 90), "U4": (-12.4, 9.0, 0), "R8": (-9.6, 7.0, 0),
    "C1": (-9.4, 9.4, 90), "R2": (-8.2, 9.4, 90), "R1": (-9.0, 11.6, 0),
    "L1": (-14.4, 13.4, 90), "D1": (-11.0, 14.4, 0), "C3": (-8.4, 14.4, 90),
    "R3": (-7.0, 14.4, 90), "C4": (-5.6, 14.4, 90), "R4": (-4.0, 15.8, 0),
    "Q1": (-1.6, 16.0, 0), "C5": (0.4, 14.0, 90), "Q2": (2.6, 14.0, 0),
    "R5": (2.6, 11.4, 0), "R6": (4.6, 12.0, 90), "R7": (4.6, 15.4, 90),
}
BACK = {"J1": (0.0, -13.0, 0)}
TP_ROW = [(x, 19.0) for x in (-7.2, -4.8, -2.4, 0.0, 2.4, 4.8, 7.2)]


def build(first=()):
    proj = "core"
    out = os.path.join(HW, proj)
    P = parts()
    nl = write_schematic(
        proj, "TinyDie Tumble - B CORE", P, out, paper="A2",
        notes=["Board B, CORE: STM32G041J6 (SO-8) + LIS3DH + DRV2605L/LRA + avalanche-noise entropy source",
               "P1-P10 spring pins up to the FACE; X1-X10 gold dots for the BASE's spring pins; TP* gold test pads",
               "MCU pins 7/8 are SWD for 2 s after reset, then NOISE_EN / ACC_INT1.  Set NRST_MODE = GPIO (pin 4 = UART).",
               "Entropy: TPS61040 boosts VBAT to ~13.6 V only while NOISE_EN is high; Q1 E-B junction in avalanche, Q2 amplifies"],
        flags=["GND", "VBAT", "3V3"])
    pb = PcbBuilder(proj, out, nl, origin=(100.0, 100.0))
    K.outline(pb)
    K.keyline(pb, "FB")
    K.place_common(pb, land_refs="X", pin_refs="P")
    for ref, (x, y, r) in BACK.items():
        pb.place(ref, x, y, r, back=True)
    for i, (x, y) in enumerate(TP_ROW):
        pb.place(f"TP{i + 1}", x, y, back=True)
    K.board_label(pb, "B · CORE  2/3", "F")
    K.gold_text(pb, "ENTROPY", -7.6, 5.4, side="F", size=0.8)
    fixed = [r for r in pb.fps if r[0] in "PXH" or r in BACK or r.startswith("TP")]
    lra = ("F", LRA_C[0] - LRA_R, LRA_C[1] - LRA_R, LRA_C[0] + LRA_R, LRA_C[1] + LRA_R)
    K.autoplace(pb, PLACE, fixed=fixed, reserve=[lra])
    pb.silk_circle(LRA_C[0], LRA_C[1], LRA_R, w=0.15)
    pb.text("LRA", LRA_C[0], LRA_C[1], size=1.0)
    # gold fence around the entropy block, open on the east side where its three signals leave
    ent = ["U4", "L1", "D1", "C1", "C2", "C3", "C4", "C5", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "Q1", "Q2"]
    bx = [K.courtyard(pb, r) for r in ent]
    x1, y1 = min(b[0] for b in bx) - 0.6, min(b[1] for b in bx) - 0.6
    x2, y2 = max(b[2] for b in bx) + 0.6, max(b[3] for b in bx) + 0.6
    gate = (y1 + 1.0, y1 + 5.0)
    for a, b in [((x1, y1), (x2, y1)), ((x1, y1), (x1, y2)), ((x1, y2), (x2, y2)),
                 ((x2, y1), (x2, gate[0])), ((x2, gate[1]), (x2, y2))]:
        pb.silk_line(a, b, w=0.2)                                 # ink, not copper: no mask openings

    from router import Router
    ox, oy = pb.ox, pb.oy
    failed = []
    jx, jy = BACK["J1"][:2]                       # Tag-Connect keep-out: no vias between its pads
    pb.via_keepouts = [(jx - 1.62, jy - 0.985, jx + 1.62, jy + 0.985)]
    stub_ends, stubbed = K.escape_stubs(pb, ["U1", "U2", "U3"], gnd_vias=True)
    # boost input cap: its ground pad gets its own via, outward from the cap
    (ax, ay), (bx, by) = pb.pad_xy("C2", "1"), pb.pad_xy("C2", "2")
    gx, gy = (bx, by) if pb.netlist["C2"]["pads"]["2"] == "GND" else (ax, ay)
    ox_, oy_ = (ax, ay) if (gx, gy) == (bx, by) else (bx, by)
    d = ((gx - ox_) ** 2 + (gy - oy_) ** 2) ** 0.5
    vg = (gx + (gx - ox_) / d * 0.95, gy + (gy - oy_) / d * 0.95)
    pb.track((gx, gy), vg, 0.3, "GND", "F")
    pb.via(*vg, "GND")      # fine-pitch parts: stubs to route to
    rt = K.make_router(pb, Router, maxw=0.25, clearance=0.16, layer_cost={"F": 0.0, "B": 0.3})

    nets = [("LRA_P", 0.25), ("LRA_N", 0.25), ("HAPT_REG", 0.2), ("SDA", 0.2), ("SCL", 0.2),
            ("3V3", 0.25), ("VBAT", 0.25),
            ("VBOOST", 0.25), ("BST_SW", 0.25), ("BST_FB", 0.2), ("VNOISE", 0.2), ("AVAL", 0.2),
            ("AMP_B", 0.2), ("AMP_C", 0.2), ("NOISE_ADC", 0.2), ("SWDIO", 0.2), ("SWCLK", 0.2),
            ("ACC_INT1", 0.2), ("ACC_SA0", 0.2), ("UART", 0.2), ("LED_SDB", 0.2), ("LED_INTB", 0.2)]
    nets = [n for n in nets if n[0] in first] + [n for n in nets if n[0] not in first]
    if os.environ.get("CORE_ONLY"):
        nets = [n for n in nets if n[0] in os.environ["CORE_ONLY"].split(",")]
    for net, w in nets:
        pads = [pd for fp in pb.fps.values() for pd in fp.Pads() if pd.GetNetname() == "/" + net
                and (fp.GetReference(), pd.GetNumber()) not in stubbed]
        if os.environ.get("CORE_DEBUG"):
            for pd in pads:
                cells, _ = rt.pad_cells(pd)
                nf = sum(1 for c in cells if rt.free(c[0], c[1:], "/" + net))
                print(f"    {net} pad {pd.GetParentFootprint().GetReference()}.{pd.GetNumber()} cells {len(cells)} free {nf}")
            for e in stub_ends.get("/" + net, []):
                c = rt.ij(*e)
                print(f"    {net} stub end {e} free F {rt.free('F', c, '/' + net)} blockers {rt.tblock['F'].get(c)}")
        ok, tr, vs = rt.route_net("/" + net, pads, w, extra=stub_ends.get("/" + net))
        print(f"  route {net:10s} {'ok' if ok else 'FAILED'} {len(tr):3d} segs {len(vs)} vias")
        if not ok:
            failed.append(net)
            continue
        for L, a, b, ww, n in tr:
            pb.track((a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy), ww, net, L)
        for (x, y), n in vs:
            pb.via(x - ox, y - oy, net)

    print("  ground (vias, links, failed):", K.ground(pb, K.make_router(pb, Router, maxw=0.25, clearance=0.16), skip=stubbed))
    print(f"  stitching vias: {K.stitch(pb, K.make_router(pb, Router, maxw=0.3), step=3.0)}")
    h = K.HALF - K.KEYLINE - 0.45
    for L in ("F", "B"):
        pb.zone("GND", L, [(-h, -h), (h, -h), (h, h), (-h, h)], clearance=0.2, min_w=0.2)
    # marks
    labels = ["NOISE", "UART", "INTB", "SWDIO", "SWCLK", "3V3", "GND"]
    for k, ((x, y), t) in enumerate(zip(TP_ROW, labels)):
        pb.text(t, x, y + (-1.6 if k % 2 == 0 else 1.6), layer="B.SilkS", size=0.6)
    pb.text("SWD", 0.0, -14.6, layer="B.SilkS", size=0.8)
    K.noise_trace(pb, -15.0, 15.0, -18.6, side="B")                       # 32 samples of blake2s("hexa3")
    pb.text('blake2s("hexa3")', 9.0, -16.0, layer="B.SilkS", size=0.8)
    out_pcb = pb.finish(clearance=0.16, track=0.2)
    if failed:
        print("UNROUTED:", failed)
    return out_pcb, failed


if __name__ == "__main__":
    first = []
    for attempt in range(1, 6):
        pcb, failed = build(first)
        print(f"attempt {attempt}: {len(failed)} unrouted {failed}")
        if not failed:
            break
        first = failed + [f for f in first if f not in failed]
    print(pcb)
    sys.exit(1 if failed else 0)
