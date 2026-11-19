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
PITCH = 2.54
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
