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
