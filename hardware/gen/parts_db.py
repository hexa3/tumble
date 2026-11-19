"""Purchasable parts for the three TinyDie Tumble boards: one entry per orderable part.

Each schematic symbol gets Manufacturer / MPN / DigiKey_PN fields from here (kicadgen.part_fields).

Prices are DigiKey cut-tape unit prices in USD.  `checked` says how far each entry was verified:
  "page"    price and stock read from the DigiKey product page on 2026-11-10
  "cube"    read from DigiKey on 2026-11-10 during the earlier cube project
  "verify"  MPN chosen from the datasheet / series naming; DigiKey PN, price or stock NOT confirmed
Anything marked "verify" must be looked up before ordering.
"""

PRICED_ON = "2026-11-10"

# key: (manufacturer, mpn, digikey_pn, description, breaks, stock note, checked)
PARTS = {
    # ---------------------------------------------------------------- face
    "LED": ("Kingbright", "APHHS1005SYCK", "754-1105-1-ND",
            "LED yellow 590 nm, 0402, Vf 2.0 V, 150 mcd @ 20 mA",
            [(1, 0.28), (10, 0.194), (100, 0.1366), (500, 0.11036)], "105,966 in stock", "page"),
    "IS31FL3733B": ("Lumissil Microsystems", "IS31FL3733B-QFLS4-TR", "",
                    "12 x 16 matrix LED driver, 8-bit PWM per LED, I2C, QFN-48 6x6 P0.4",
                    [(1, 2.59)], "12,133 in stock (eTQFP version IS31FL3733B-TQLS4-TR: 2,997, $2.81)", "page"),
    "IS31FL3731": ("Lumissil Microsystems", "IS31FL3731-QFLS2-TR", "",
                   "144-LED charlieplex matrix driver, 8-bit PWM per LED, I2C, QFN-28 4x4",
                   [(1, 1.52)], "price seen on DigiKey; stock not shown. SSOP-28 version (-SALS2-TR) had 538",
                   "verify"),
    # ---------------------------------------------------------------- core
    "STM32G041": ("STMicroelectronics", "STM32G041J6M6", "497-STM32G041J6M6-ND",
                  "MCU Cortex-M0+ 64 MHz, 32 KB flash, 8 KB RAM, hardware RNG + AES, SO-8",
                  [(1, 1.98)], "419 in stock", "page"),
    "MCP2221A": ("Microchip Technology", "MCP2221A-I/SL", "MCP2221A-I/SL-ND",
                 "USB 2.0 to UART/I2C bridge, crystal-less, SOIC-14", [(1, 2.53)], "1,614 in stock", "page"),
    "MAX17048": ("Analog Devices / Maxim", "MAX17048G+T10", "",
                 "1-cell Li+ fuel gauge (ModelGauge), I2C, TDFN-8 2x2", [(1, 4.61)],
                 "21,841 in stock; land pattern: check ADI package drawing for the TDFN-8 2x2", "page"),
    "LED_RED_0603": ("Lite-On", "LTST-C191KRKT", "160-1447-1-ND", "red LED 0603 (charge indicator)",
                     [(1, 0.15), (10, 0.104)], "1,334,425 in stock", "cube"),
    "R1k_0402": ("YAGEO", "RC0402FR-071KL", "311-1.00KLRCT-ND", "1 k 1 % 0402", None, "", "verify"),
    "C470n_0402": ("Samsung Electro-Mechanics", "CL05A474KO5NNNC", "", "470 nF 16 V X5R 0402",
                   [(1, 0.10), (10, 0.03)], "", "verify"),
    "STM32L412": ("STMicroelectronics", "STM32L412KBT6", "",
                  "MCU Cortex-M4F, 128 K flash, 40 K RAM, crystal-less USB FS, TRNG, LQFP-32",
                  [(1, 4.90)], "2,170 in stock", "page"),
    "LIS3DH": ("STMicroelectronics", "LIS3DHTR", "497-10613-1-ND",
               "3-axis accelerometer, I2C, click + motion interrupts, LGA-16 3x3",
               [(1, 1.94)], "DigiKey 0 in stock on 2026-11-10; LCSC C15134 in stock", "cube"),
    "ADXL343": ("Analog Devices", "ADXL343BCCZ-RL7", "",
                "3-axis accelerometer, I2C, tap + activity interrupts, LGA-14 3x5",
                [(1, 4.02)], "16,920 in stock. Pin- and register-compatible with ADXL345 ($8.01)", "page"),
    "DRV2605L": ("Texas Instruments", "DRV2605LDGSR", "",
                 "haptic driver for LRA/ERM, I2C, VSSOP-10",
                 [(1, 2.28)], "stock not shown for -DGSR; -DGST showed 281", "verify"),
    "LRA": ("Vybronics", "VG0832022D", "1670-VG0832022D-ND",
            "linear resonant actuator, 8 mm coin, 235 Hz, 1.8 Vac",
            [(1, 3.47)], "15,639 in stock. Thickness and lead style not confirmed", "page"),
    "TPS61040": ("Texas Instruments", "TPS61040DBVR", "",
                 "boost converter, 400 mA switch, up to 28 V out, SOT-23-5",
                 [(1, 1.29)], "stock not shown", "verify"),
    "MMBT3904": ("onsemi", "MMBT3904LT1G", "",
                 "NPN 40 V 200 mA, SOT-23", [(1, 0.15)], "price is an estimate", "verify"),
    "L10u": ("Murata", "LQH32PH100MN0L", "",
             "inductor 10 uH, 1210 (3.2x2.5 mm), Isat >= 0.5 A", [(1, 0.45)],
             "candidate only: confirm saturation current >= 0.5 A (boost switch limit 400 mA) and land pattern",
             "verify"),
    "SW": ("Omron", "B3U-1000P", "SW1020CT-ND",
           "tactile switch, top actuated, 3.0x2.5 mm SMD", [(1, 0.85)], "price is an estimate", "verify"),
    "POGO": ("Mill-Max", "0900-2-15-20-75-14-11-0", "ED9002-ND",
             "SMT spring pin, 5.00 mm max / 4.30 mm recommended working height, 60 gf mid-stroke (verify stroke vs 4.5 mm gap)",
             [(1, 0.715)], "49,077 in stock", "cube"),
    # ---------------------------------------------------------------- base
    "USBC": ("GCT", "USB4105-GF-A", "2073-USB4105-GF-ACT-ND",
             "USB-C receptacle, USB 2.0, 16 pin, SMD horizontal",
             [(1, 0.80), (10, 0.676)], "263,569 in stock", "cube"),
    "USBLC6": ("STMicroelectronics", "USBLC6-2SC6", "497-5235-1-ND",
               "USB ESD protection, SOT-23-6", [(1, 0.54), (10, 0.329)], "27,230 in stock", "cube"),
    "MCP73831": ("Microchip Technology", "MCP73831T-2ACI/OT", "MCP73831T-2ACI/OTCT-ND",
                 "Li-Po charger, 4.20 V, SOT-23-5", [(1, 0.76)], "28,916 in stock", "cube"),
    "RT9080": ("Richtek", "RT9080-33GJ5", "1028-1509-1-ND",
               "3.3 V 600 mA LDO, 2 uA Iq, SOT-23-5", [(1, 0.28), (10, 0.193)], "74,219 in stock", "cube"),
    "AO3401A": ("Alpha & Omega Semiconductor", "AO3401A", "785-1001-1-ND",
                "P-MOSFET -30 V -4 A, SOT-23", [(1, 0.52), (10, 0.322)], "303,699 in stock", "cube"),
    "2N7002": ("onsemi", "2N7002LT1G", "2N7002LT1GOSCT-ND",
               "N-MOSFET 60 V 115 mA, SOT-23", [(1, 0.26), (10, 0.158)], "732,197 in stock", "cube"),
    "SCHOTTKY": ("Diodes Incorporated", "1N5819HW-7-F", "1N5819HW-FDICT-ND",
                 "Schottky 40 V 1 A, SOD-123", [(1, 0.31), (10, 0.19)], "306,077 in stock", "cube"),
    "LIPO": ("TBD", "TBD (1S Li-Po with protection, <= 34 x 25 x 3.5 mm)", "",
             "1S Li-Po, 150-250 mAh, protection PCB, leads soldered to BT1",
             [(1, 7.00)], "NOT SELECTED: the 4.3 mm board gap needs a cell 3.5 mm thick or less", "verify"),
    # ---------------------------------------------------------------- passives
    "C10u_0603": ("Taiyo Yuden", "LMK107BBJ106MALT", "587-3258-1-ND", "10 uF 10 V X5R 0603",
                  [(1, 0.15), (10, 0.083)], "1,209,517 in stock", "cube"),
    "C100n_0402": ("Samsung Electro-Mechanics", "CL05B104KO5NNNC", "1276-1001-1-ND", "100 nF 16 V X7R 0402",
                   [(1, 0.10), (10, 0.021)], "10,000 in stock", "cube"),
    "C1u_0402": ("Samsung Electro-Mechanics", "CL05A105KA5NQNC", "1276-1445-1-ND", "1 uF 25 V X5R 0402",
                 [(1, 0.19), (10, 0.109)], "1,961,997 in stock", "cube"),
    "C4u7_0402": ("TDK", "C1005X5R1A475K050BC", "445-13820-1-ND", "4.7 uF 10 V X5R 0402",
                  [(1, 0.25), (10, 0.142)], "739,251 in stock", "cube"),
    "C10n_0402": ("Samsung Electro-Mechanics", "CL05B103KB5NNNC", "", "10 nF 50 V X7R 0402",
                  [(1, 0.10), (10, 0.02)], "", "verify"),
    "C10p_0402": ("Samsung Electro-Mechanics", "CL05C100JB5NNNC", "", "10 pF 50 V C0G 0402",
                  [(1, 0.10), (10, 0.02)], "", "verify"),
    # Yageo RC0402FR-07 thick film 1 %; DigiKey PNs follow 311-<value>LRCT-ND (pattern, spot-checked on 10k/100k)
    "R100_0402": ("YAGEO", "RC0402FR-07100RL", "311-100LRCT-ND", "100 R 1 % 0402", None, "", "cube"),
    "R4k7_0402": ("YAGEO", "RC0402FR-074K7L", "311-4.70KLRCT-ND", "4.7 k 1 % 0402", None, "", "cube"),
    "R5k1_0402": ("YAGEO", "RC0402FR-075K1L", "311-5.10KLRCT-ND", "5.1 k 1 % 0402", None, "", "verify"),
    "R10k_0402": ("YAGEO", "RC0402FR-0710KL", "311-10.0KLRCT-ND", "10 k 1 % 0402", None, "", "cube"),
    "R20k_0402": ("YAGEO", "RC0402FR-0720KL", "311-20.0KLRCT-ND", "20 k 1 % 0402", None, "", "cube"),
    "R100k_0402": ("YAGEO", "RC0402FR-07100KL", "311-100KLRCT-ND", "100 k 1 % 0402", None, "", "cube"),
    "R220k_0402": ("YAGEO", "RC0402FR-07220KL", "311-220KLRCT-ND", "220 k 1 % 0402", None, "", "verify"),
    "R1M_0402": ("YAGEO", "RC0402FR-071ML", "311-1.00MLRCT-ND", "1 M 1 % 0402", None, "", "verify"),
}

RES_BREAKS = [(1, 0.10), (10, 0.023), (100, 0.0108)]

# Symbols that are copper on the PCB, not something you buy.
NO_PART = ("N/A", "N/A (PCB copper feature, not a part)")


def entry(key):
    """(manufacturer, mpn, digikey_pn, description, breaks, stock) with defaults resolved."""
    man, mpn, dk, desc, br, stock, _ = PARTS[key]
    return man, mpn, dk, desc, br or RES_BREAKS, stock


def checked(key):
    return PARTS[key][6]


def unit_price(key, qty):
    br = entry(key)[4]
    return [p for q, p in br if q <= max(qty, 1)][-1]


# LCSC (JLCPCB's parts arm) alternatives, user's choice on 2026-11-11 to buy whichever is cheapest.
# Entries marked "live" were read from JLCPCB's parts API on 2026-11-11 (qty-1 price); "est" are guesses.
# key: (LCSC part #, LCSC MPN if different, qty-1 unit price $, note)
LCSC = {
    "LED": ("C25503856", "XINGLIGHT XL-1005UYC", 0.0132, "live 2026-11-11, 175,965 in stock"),
    "IS31FL3733B": ("C506251", "ISSI IS31FL3733-QFLS4-TR (B version out of stock)", 1.4516, "live 2026-11-11"),
    "STM32G041": ("C724068", "", 2.022, "live 2026-11-11; only 3 in stock"),
    "LIS3DH": ("C15134", "", 1.8063, "live 2026-11-11"),
    "DRV2605L": ("C527464", "", 1.2309, "live 2026-11-11"),
    "MAX17048": ("C2682616", "", 1.9599, "live 2026-11-11"),
    "TPS61040": ("C7722", "", 0.8598, "live 2026-11-11"),
    "MMBT3904": ("C20526", "JSCJ MMBT3904", 0.0104, "live 2026-11-11, basic"),
    "AO3401A": ("C15127", "", 0.0821, "live 2026-11-11, basic"),
    "2N7002": ("C8545", "JSCJ 2N7002", 0.0155, "live 2026-11-11, basic"),
    "SCHOTTKY": ("C8598", "JSCJ B5819W SL", 0.0265, "live 2026-11-11, basic"),
    "USBLC6": ("C7519", "", 0.1572, "live 2026-11-11"),
    "MCP73831": ("C424093", "", 0.7978, "live 2026-11-11"),
    "RT9080": ("C841192", "", 0.1208, "live 2026-11-11"),
    "USBC": ("C3020560", "", 1.02, "live 2026-11-11"),
    "L10u": ("C907910", "", 0.2058, "live 2026-11-11"),
    "LED_RED_0603": ("C2286", "KENTO KT-0603R", 0.0077, "live 2026-11-11, basic"),
}
for _k in [k for k in PARTS if k.startswith(("R", "C")) and "_04" in k or k.endswith("_0603") and k[0] in "RC"]:
    LCSC.setdefault(_k, ("", "generic, JLC basic part", 0.005, "est"))


def cheapest(key, qty):
    """(source, unit price) of the cheaper of DigiKey and LCSC for this part."""
    dk = unit_price(key, qty)
    if key in LCSC and LCSC[key][2] < dk:
        return "LCSC", LCSC[key][2]
    return "DigiKey", dk
