"""PLC STM32F407VET6 + W5500 (Modbus TCP) + 16 DO transistor + 10 AI (0-10V / 4-20mA).

Chạy:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" design.py
Sinh project KiCad vào thư mục ../kicad
"""
import os
import kisch
from kisch import Sheet

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad")
FP_DIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

# ------------------------------------------------------------------ footprints
R0603 = "Resistor_SMD:R_0603_1608Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1206 = "Capacitor_SMD:C_1206_3216Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
SOD123 = "Diode_SMD:D_SOD-123"
DSMA = "Diode_SMD:D_SMA"
DSMB = "Diode_SMD:D_SMB"
DSMC = "Diode_SMD:D_SMC"
JMP2 = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
BTN = "Button_Switch_SMD:SW_SPST_PTS810"
TB = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1-{n}-3.81_1x{n:02d}_P3.81mm_Horizontal"
PTC1206 = "Fuse:Fuse_1206_3216Metric"
PTC0805 = "Fuse:Fuse_0805_2012Metric"
SOD123F = "Diode_SMD:D_SOD-123F"
FB0805 = "Inductor_SMD:L_0805_2012Metric"

_missing_fp = set()


def fp_ok(fp):
    if not fp:
        return fp
    lib, name = fp.split(":", 1)
    if os.path.exists(os.path.join(FP_DIR, lib + ".pretty", name + ".kicad_mod")):
        return fp
    _missing_fp.add(fp)
    return fp


def tb(n):
    return TB.format(n=n)


class Refs:
    def __init__(self):
        self.c = {}

    def __call__(self, prefix, base):
        k = (prefix, base)
        self.c[k] = self.c.get(k, 0) + 1
        return f"{prefix}{base + self.c[k]}"


ref = Refs()


# convenience placers -------------------------------------------------------
def R(sh, base, val, x, y, n1, n2, rot=0, fp=R0603, **kw):
    return sh.place("Device:R", ref("R", base), val, x, y, rot, {1: n1, 2: n2}, footprint=fp_ok(fp), **kw)


def C(sh, base, val, x, y, n1, n2, rot=0, fp=C0603, **kw):
    return sh.place("Device:C", ref("C", base), val, x, y, rot, {1: n1, 2: n2}, footprint=fp_ok(fp), **kw)


def CP(sh, base, val, x, y, npos, nneg, fp="Capacitor_SMD:CP_Elec_8x10", **kw):
    return sh.place("Device:C_Polarized", ref("C", base), val, x, y, 0, {1: npos, 2: nneg}, footprint=fp_ok(fp), **kw)


def LED(sh, base, val, x, y, na, nk, rot=0, fp=LED0603):
    return sh.place("Device:LED", ref("D", base), val, x, y, rot, {2: na, 1: nk}, footprint=fp_ok(fp))


def PWRFLAG(sh, x, y, net):
    sh.place("power:PWR_FLAG", ref("#FLG", 0), "PWR_FLAG", x, y, 0, {1: net}, stub=0)


def decap_row(sh, base, x, y, net, vals, gnd="GND", dx=10.16, fp=C0603):
    for i, v in enumerate(vals):
        C(sh, base, v, x + i * dx, y, net, gnd, fp=(C0805 if v in ("4.7uF", "10uF", "22uF", "2.2uF") else fp))


# =================================================================== POWER
def sheet_power():
    sh = Sheet("Nguon 24VDC", "power.kicad_sch", "Nguon: loc 24VDC, buck 5V, LDO 3.3V, ref 3.0V")
    sh.text(20, 22, "NGUON VAO 24VDC: cau chi -> chong nguoc -> TVS -> loc common-mode -> loc LC -> +24V", 2.0)
    # input terminal
    sh.place("Connector:Screw_Terminal_01x02", ref("J", 100), "24VDC IN", 30, 60, 0,
             {1: "VIN_RAW", 2: "GND_IN"}, footprint=fp_ok(tb(2)), mirror="y")
    sh.place("Device:Fuse", ref("F", 100), "PTC MF-MSMF050-2 0.5A/60V", 50, 50, 90, {1: "VIN_RAW", 2: "VIN_F"},
             footprint=fp_ok("Fuse:Fuse_1812_4532Metric"))
    sh.place("Device:D_Schottky", ref("D", 100), "SS110 (100V/1A)", 70, 50, 180, {2: "VIN_F", 1: "VIN_P"},
             footprint=fp_ok(DSMA))
    sh.place("Device:D_TVS", ref("D", 100), "SMBJ33CA", 85, 62, 90, {2: "VIN_P", 1: "GND_IN"},
             footprint=fp_ok(DSMB))
    sh.place("Filter:Choke_CommonMode_FerriteCore_1234", ref("L", 100), "CMC TDK ACM7060-701-2PL", 105, 60, 0,
             {1: "VIN_P", 2: "VIN_CM", 3: "GND_IN", 4: "GND"},
             footprint=fp_ok("Inductor_SMD:L_CommonModeChoke_TDK_ACM7060"))
    CP(sh, 100, "47uF/50V", 125, 62, "VIN_CM", "GND", fp="Capacitor_SMD:CP_Elec_6.3x7.7")
    C(sh, 100, "1uF/50V", 135, 62, "VIN_CM", "GND", fp=C1206)
    sh.place("Device:FerriteBead", ref("FB", 100), "BLM31PG601SN1 3A", 150, 50, 90, {1: "VIN_CM", 2: "+24V"},
             footprint=fp_ok("Inductor_SMD:L_1206_3216Metric"))
    C(sh, 100, "10uF/50V", 165, 62, "+24V", "GND", fp="Capacitor_SMD:C_1210_3225Metric")
    C(sh, 100, "100nF/50V", 175, 62, "+24V", "GND", fp=C0805)
    R(sh, 100, "4.7k", 190, 58, "+24V", "PWR_LED_A", fp=R1206)
    LED(sh, 100, "PWR (green)", 190, 72, "PWR_LED_A", "GND", rot=90)
    PWRFLAG(sh, 205, 50, "+24V")
    PWRFLAG(sh, 215, 50, "GND")

    # buck 24 -> 5V
    sh.text(20, 105, "BUCK 24V -> 5V (LMR16006Y, 60V, 0.6A, 2.1MHz)", 2.0)
    C(sh, 100, "2.2uF/50V", 40, 135, "+24V", "GND", fp=C1206)
    C(sh, 100, "100nF/50V", 50, 135, "+24V", "GND", fp=C0805)
    sh.place("Regulator_Switching:LMR16006YQ5", ref("U", 100), "LMR16006YQ5", 85, 135, 0,
             {5: "+24V", 4: "+24V", 2: "GND", 1: "BUCK_CB", 6: "BUCK_SW", 3: "+5V_BUCK"})
    C(sh, 100, "100nF", 115, 122, "BUCK_CB", "BUCK_SW")
    sh.place("Diode:SS16", ref("D", 100), "SS16", 125, 145, 270, {1: "BUCK_SW", 2: "GND"})
    sh.place("Device:L", ref("L", 100), "10uH 1A", 140, 130, 90, {1: "BUCK_SW", 2: "+5V_BUCK"},
             footprint=fp_ok("Inductor_SMD:L_Bourns-SRN4018"))
    C(sh, 100, "22uF", 155, 140, "+5V_BUCK", "GND", fp=C1206)
    C(sh, 100, "22uF", 165, 140, "+5V_BUCK", "GND", fp=C1206)
    # OR-ing with USB VBUS
    sh.place("Diode:SS14", ref("D", 100), "SS14", 185, 130, 180, {2: "+5V_BUCK", 1: "+5V"})
    sh.place("Diode:SS14", ref("D", 100), "SS14", 185, 150, 180, {2: "VBUS", 1: "+5V"})
    sh.text(170, 160, "Cap nguon tu USB khi chua co 24V (de nap code)", 1.5)
    PWRFLAG(sh, 200, 125, "+5V")

    # LDO 3.3V
    sh.text(20, 185, "LDO 5V -> 3.3V, loc rieng 3.3VA cho ADC", 2.0)
    C(sh, 100, "10uF", 40, 215, "+5V", "GND", fp=C0805)
    sh.place("Regulator_Linear:AMS1117-3.3", ref("U", 100), "AMS1117-3.3", 65, 210, 0,
             {3: "+5V", 2: "+3V3", 1: "GND"})
    C(sh, 100, "22uF", 90, 215, "+3V3", "GND", fp=C1206)
    C(sh, 100, "100nF", 100, 215, "+3V3", "GND")
    sh.place("Device:FerriteBead", ref("FB", 100), "600R@100MHz", 120, 205, 90, {1: "+3V3", 2: "+3.3VA"},
             footprint=fp_ok(FB0805))
    C(sh, 100, "10uF", 140, 215, "+3.3VA", "GND", fp=C0805)
    C(sh, 100, "100nF", 150, 215, "+3.3VA", "GND")
    PWRFLAG(sh, 165, 205, "+3.3VA")
    R(sh, 100, "1k", 180, 210, "+3V3", "LED33_A")
    LED(sh, 100, "3V3 (green)", 180, 224, "LED33_A", "GND", rot=90)
    return sh


# =================================================================== MCU
def sheet_mcu():
    sh = Sheet("MCU STM32F407VET6", "mcu.kicad_sch", "Vi dieu khien STM32F407VET6")
    X, Y = 200, 150
    # DO1..DO16 = PE1, PE0, PB9, PB8, PB7, PB6, PB5, PB4, PD7..PD0 (canh tren LQFP, huong ve khoi ngo ra)
    DO_PINS = [98, 97, 96, 95, 93, 92, 91, 90, 88, 87, 86, 85, 84, 83, 82, 81]
    AI_PINS = [23, 24, 25, 26, 15, 16, 17, 18, 33, 34]                      # PA0-3, PC0-5
    conns = {6: "+3V3", 11: "+3V3", 19: "+3V3", 28: "+3V3", 50: "+3V3", 75: "+3V3", 100: "+3V3",
             10: "GND", 20: "GND", 22: "+3.3VA", 21: "VREF_3V0", 49: "VCAP1", 73: "VCAP2",
             12: "OSC_IN", 13: "OSC_OUT", 14: "NRST", 94: "BOOT0", 37: "BOOT1",
             51: "ETH_CS", 52: "ETH_SCK", 53: "ETH_MISO", 54: "ETH_MOSI", 55: "ETH_RST", 56: "ETH_INT",
             68: "UART1_TX", 69: "UART1_RX", 72: "SWDIO", 76: "SWCLK", 89: "SWO",
             59: "LED_RUN", 60: "LED_ERR"}
    for i, p in enumerate(DO_PINS):
        conns[p] = f"DO{i + 1}"
    for i, p in enumerate(AI_PINS):
        conns[p] = f"AI{i + 1}_ADC"
    stacked_vss = {27, 74, 99}
    for p in range(1, 101):
        if p not in conns and p not in stacked_vss:
            conns[p] = "NC"
    sh.place("MCU_ST_STM32F4:STM32F407VETx", "U200", "STM32F407VET6", X, Y, 0, conns, stub=5.08)

    # HSE 8 MHz: sat chan PH0/PH1 (canh trai MCU)
    sh.text(120, 92, "HSE 8MHz", 1.5)
    sh.place("Device:Crystal_GND24", ref("Y", 200), "8MHz 20pF", 152.4, 104.14, 90,
             {1: "OSC_IN", 3: "OSC_OUT", 2: "GND"}, footprint=fp_ok("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"))
    C(sh, 200, "20pF", 137.16, 99.06, "OSC_IN", "GND")
    C(sh, 200, "20pF", 137.16, 114.3, "OSC_OUT", "GND")

    # tu loc nguon (chi noi power symbol) - goc duoi trai
    sh.text(25, 232, "Tu loc nguon: 1 tu 100nF sat moi chan VDD; 1uF+100nF cho VDDA", 1.5)
    decap_row(sh, 200, 30, 248, "+3V3", ["100nF"] * 6 + ["4.7uF"])
    decap_row(sh, 200, 110, 248, "+3.3VA", ["1uF", "100nF"])
    # VCAP sat chan VCAP_1/VCAP_2
    C(sh, 200, "2.2uF", 160.02, 205.74, "VCAP1", "GND", fp=C0805)
    C(sh, 200, "2.2uF", 149.86, 205.74, "VCAP2", "GND", fp=C0805)

    # VREF 3.0V sat chan VREF+
    sh.text(100, 62, "VREF+ = 3.000V", 1.5)
    sh.place("Reference_Voltage:REF3030", ref("U", 200), "REF3030", 119.38, 78.74, 0,
             {1: "+3.3VA", 2: "VREF_3V0", 3: "GND"})
    C(sh, 200, "1uF", 139.7, 83.82, "VREF_3V0", "GND")
    C(sh, 200, "100nF", 149.86, 83.82, "VREF_3V0", "GND")

    # reset / boot (NRST, BOOT0 la net global -> nhan)
    sh.text(30, 30, "RESET / BOOT", 1.5)
    C(sh, 200, "100nF", 35.56, 50.8, "NRST", "GND")
    sh.place("Switch:SW_Push", ref("SW", 200), "RESET", 55.88, 48.26, 0, {1: "NRST", 2: "GND"}, footprint=fp_ok(BTN))
    R(sh, 200, "10k", 81.28, 50.8, "BOOT0", "GND")
    sh.place("Switch:SW_Push", ref("SW", 200), "BOOT", 101.6, 48.26, 0, {1: "+3V3", 2: "BOOT0"}, footprint=fp_ok(BTN))
    # BOOT1 (PB2, canh phai)
    R(sh, 200, "10k", 243.84, 142.24, "BOOT1", "GND")

    # SWD (canh phai, quay ve phia MCU)
    sh.text(250, 100, "SWD debug (ST-Link)", 1.5)
    sh.place("Connector:Conn_ARM_JTAG_SWD_10", ref("J", 200), "SWD", 264.16, 124.46, 0,
             {1: "+3V3", 2: "SWDIO", 3: "GND", 4: "SWCLK", 6: "SWO", 7: "NC", 8: "NC", 9: "GND", 10: "NRST"},
             footprint=fp_ok("Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD"), mirror="y")

    # LED trang thai (PD12/PD13, canh trai)
    sh.text(120, 172, "LED trang thai", 1.5)
    R(sh, 200, "1k", 160.02, 182.88, "LED_RUN", "RUN_A", rot=270)
    LED(sh, 200, "RUN (green)", 147.32, 182.88, "RUN_A", "GND", rot=0)
    R(sh, 200, "1k", 160.02, 190.5, "LED_ERR", "ERR_A", rot=270)
    LED(sh, 200, "ERR (red)", 147.32, 190.5, "ERR_A", "GND", rot=0)

    sh.text(290, 160, "GAN CHAN:", 1.8)
    notes = ["DO1..DO16 -> PE1,PE0,PB9,PB8,PB7,PB6,PB5,PB4,PD7..PD0",
             "PA0-PA3, PC0-PC5 -> AI1..AI10 (ADC1 12-bit)",
             "SPI2 PB12(CS) PB13 PB14 PB15 -> W5500, PD8 RST, PD9 INT",
             "USART1 PA9/PA10 -> CH340C (bootloader UART)",
             "PA13/PA14/PB3 -> SWD, PD12/PD13 -> LED"]
    for i, n in enumerate(notes):
        sh.text(290, 167 + i * 6, n, 1.5)
    return sh


# =================================================================== USB
def sheet_usb():
    sh = Sheet("USB nap code", "usb.kicad_sch", "USB-C -> CH340C -> USART1 + mach tu dong vao bootloader")
    sh.place("Connector:USB_C_Receptacle_USB2.0_16P", ref("J", 300), "USB-C", 50, 90, 0,
             {"A4": "VBUS_C", "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM",
              "B7": "USB_DM", "A8": "NC", "B8": "NC", "A1": "GND", "SH": "USB_SHIELD"},
             footprint=fp_ok("Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"))
    R(sh, 300, "5.1k", 90, 80, "CC1", "GND")
    R(sh, 300, "5.1k", 100, 80, "CC2", "GND")
    R(sh, 300, "1M", 40, 130, "USB_SHIELD", "GND")
    C(sh, 300, "4.7nF/250V", 52, 130, "USB_SHIELD", "GND", fp=C1206)
    sh.place("Device:Polyfuse", ref("F", 300), "500mA", 95, 55, 90, {1: "VBUS_C", 2: "VBUS"},
             footprint=fp_ok(PTC1206))
    PWRFLAG(sh, 110, 50, "VBUS")
    C(sh, 300, "1uF", 120, 60, "VBUS", "GND")
    sh.place("Power_Protection:USBLC6-2SC6", ref("U", 300), "USBLC6-2SC6", 125, 100, 0,
             {1: "USB_DP", 6: "USB_DP", 3: "USB_DM", 4: "USB_DM", 5: "VBUS", 2: "GND"})

    sh.place("Interface_USB:CH340C", ref("U", 300), "CH340C", 185, 95, 0,
             {16: "+3V3", 4: "+3V3", 1: "GND", 5: "USB_DP", 6: "USB_DM", 2: "UART1_RX", 3: "UART1_TX",
              13: "CH_DTR", 14: "CH_RTS", 9: "NC", 10: "NC", 11: "NC", 12: "NC", 15: "NC", 7: "NC", 8: "NC"},
             footprint=fp_ok("Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"))
    C(sh, 300, "100nF", 160, 130, "+3V3", "GND")
    C(sh, 300, "10uF", 170, 130, "+3V3", "GND", fp=C0805)

    sh.text(230, 40, "MACH TU DONG NAP (DTR/RTS) - giong ESP32", 1.8)
    sh.text(230, 46, "RTS=1,DTR=0 -> NRST=0 ; RTS=0,DTR=1 -> BOOT0=1 ; ca hai =1 hoac =0 -> khong tac dong", 1.3)
    R(sh, 300, "10k", 250, 75, "CH_DTR", "Q1_B", rot=90)
    sh.place("Transistor_BJT:MMBT3904", ref("Q", 300), "MMBT3904", 265, 75, 0,
             {1: "Q1_B", 2: "CH_RTS", 3: "NRST"})
    R(sh, 300, "10k", 250, 105, "CH_RTS", "Q2_B", rot=90)
    sh.place("Transistor_BJT:MMBT3904", ref("Q", 300), "MMBT3904", 265, 105, 0,
             {1: "Q2_B", 2: "CH_DTR", 3: "BOOT_N"})
    R(sh, 300, "10k", 285, 95, "+3V3", "BOOT_N")
    R(sh, 300, "10k", 300, 120, "BOOT_N", "Q3_B", rot=90)
    sh.place("Transistor_BJT:MMBT3906", ref("Q", 300), "MMBT3906", 315, 120, 0,
             {1: "Q3_B", 2: "+3V3", 3: "BOOT_AUTO"}, mirror="x")
    sh.place("Jumper:Jumper_2_Open", ref("JP", 300), "AUTO-BOOT", 340, 140, 0, {1: "BOOT_AUTO", 2: "BOOT_J"},
             footprint=fp_ok(JMP2))
    R(sh, 300, "1k", 365, 140, "BOOT_J", "BOOT0", rot=90)
    return sh


# =================================================================== COMM
def sheet_comm():
    sh = Sheet("Ethernet", "comm.kicad_sch", "W5500 Ethernet - Modbus TCP")
    X, Y = 140, 130
    c = {28: "+3V3", 4: "+3V3", 8: "+3V3", 11: "+3V3", 15: "+3V3", 17: "+3V3", 21: "+3V3",
         3: "GND", 9: "GND", 14: "GND", 16: "GND", 19: "GND", 48: "GND", 29: "GND", 23: "GND",
         10: "ETH_EXRES", 18: "NC", 20: "ETH_TOCAP", 22: "ETH_1V2",
         7: "NC", 12: "NC", 13: "NC", 46: "NC", 47: "NC", 38: "NC", 39: "NC", 40: "NC", 41: "NC", 42: "NC",
         43: "NC", 44: "NC", 45: "NC", 24: "NC", 26: "NC",
         25: "ETH_LINK_LED", 27: "ETH_ACT_LED", 30: "ETH_XI", 31: "ETH_XO",
         32: "ETH_CS", 33: "ETH_SCK", 34: "ETH_MISO", 35: "ETH_MOSI", 36: "ETH_INT", 37: "ETH_RST",
         1: "ETH_TXN", 2: "ETH_TXP", 5: "ETH_RXN", 6: "ETH_RXP"}
    sh.place("Interface_Ethernet:W5500", "U400", "W5500", X, Y, 0, c, stub=5.08)
    # support parts
    R(sh, 400, "12.4k 1%", 170.18, 157.48, "ETH_EXRES", "GND")
    C(sh, 400, "4.7uF", 180.34, 162.56, "ETH_TOCAP", "GND", fp=C0805)
    C(sh, 400, "10nF", 190.5, 167.64, "ETH_1V2", "GND")
    sh.place("Device:Crystal", ref("Y", 400), "25MHz 18pF", 109.22, 133.35, 90, {1: "ETH_XI", 2: "ETH_XO"},
             footprint=fp_ok("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"))
    C(sh, 400, "18pF", 99.06, 144.78, "ETH_XI", "GND")
    C(sh, 400, "18pF", 88.9, 144.78, "ETH_XO", "GND")
    R(sh, 400, "10k", 95.25, 104.14, "+3V3", "ETH_INT")
    R(sh, 400, "10k", 102.87, 104.14, "+3V3", "ETH_RST")
    sh.text(40, 245, "Tu loc W5500 (dat sat chan AVDD/VDD)", 1.5)
    decap_row(sh, 400, 40, 260, "+3V3", ["100nF"] * 5 + ["10uF"])

    # magnetics termination
    sh.text(170, 78, "Phoi hop tro khang PHY (theo WIZnet ref. schematic - kiem tra lai)", 1.3)
    R(sh, 400, "49.9 1%", 177.8, 92.71, "+3V3", "ETH_TXP")
    R(sh, 400, "49.9 1%", 185.42, 92.71, "+3V3", "ETH_TXN")
    R(sh, 400, "49.9 1%", 193.04, 128.27, "ETH_RXP", "ETH_RXMID")
    R(sh, 400, "49.9 1%", 200.66, 128.27, "ETH_RXN", "ETH_RXMID")
    C(sh, 400, "6.8nF", 208.28, 138.43, "ETH_RXMID", "GND")
    C(sh, 400, "10nF", 195.58, 90.17, "+3V3", "GND")
    sh.place("Connector:RJ45_Hanrun_HR911105A_Horizontal", ref("J", 400), "HR911105A", 248.92, 111.76, 0,
             {1: "ETH_TXP", 2: "ETH_TXN", 3: "ETH_RXP", 6: "ETH_RXN", 4: "+3V3", 5: "ETH_RCT", 7: "NC",
              8: "GND", "SH": "GND", 9: "ETH_LEDG_A", 10: "ETH_LINK_LED", 12: "ETH_LEDY_A", 11: "ETH_ACT_LED"})
    C(sh, 400, "10nF", 218.44, 135.89, "ETH_RCT", "GND")
    C(sh, 400, "100nF", 210.82, 90.17, "+3V3", "GND")
    R(sh, 400, "330", 284.48, 120.65, "+3V3", "ETH_LEDG_A")
    R(sh, 400, "330", 292.1, 102.87, "+3V3", "ETH_LEDY_A")

    # them 1 tu 100nF cho chan VDD (pin 28) cua W5500 (giu ref C415 nhu tren PCB)
    C(sh, 400, "100nF", 160.02, 182.88, "+3V3", "GND")
    return sh


# =================================================================== OUTPUTS
def out_channel(sh, n, X, Y):
    """1 kenh ngo ra: opto PC817 -> N-MOSFET 60V, sink (NPN-type), diode dap, LED bao."""
    X, Y = kisch.snap(X), kisch.snap(Y)
    yn, vo, com = f"Y{n}", "V24_OUT", "COM_OUT"
    rin = R(sh, 500, "470", X + 7.62, Y, f"DO{n}", None, rot=90)
    a_pin, k_pin, c_pin, e_pin = 1, 2, 4, 3          # PC817: 1=A 2=K 3=E 4=C
    op = sh.place("Isolator:PC817", ref("U", 500), "PC817 (SMD)", X + 22.86, Y + 2.54, 0,
                  {k_pin: "GND"}, footprint=fp_ok("Package_DIP:SMDIP-4_W9.53mm"))
    sh.path(rin.p(2), op.p(a_pin))
    rc = R(sh, 500, "10k", X + 30.48, Y - 7.62, vo, None)
    sh.path(op.p(c_pin), rc.p(2))
    q = sh.place("Transistor_FET:DMN6075S", ref("Q", 500), "DMN6075S", X + 43.18, Y + 5.08, 0, {2: com})
    rg = R(sh, 500, "10k", X + 35.56, Y + 8.89, None, com)
    sh.path(op.p(e_pin), rg.p(1))
    sh.path(rg.p(1), q.p(1))
    d = sh.place("Diode:SS16", ref("D", 500), "SS16FL", X + 45.72, Y - 3.81, 270, {1: vo}, footprint=fp_ok(SOD123F))
    rl = R(sh, 500, "10k", X + 58.42, Y - 11.43, vo, None)
    led = sh.place("Device:LED", ref("D", 500), f"Q{n}", X + 58.42, Y - 3.81, 90, {}, footprint=fp_ok(LED0603))
    sh.path(rl.p(2), led.p(2))
    sh.path(q.p(3), led.p(1))
    end = sh.path(led.p(1), (X + 66.04, Y))
    sh.label_at(yn, *end, (1, 0))
    _ = d
    sh.text(X - 2, Y - 18, f"DO{n} -> Y{n}", 1.5)


def sheet_outputs():
    sh = Sheet("16 ngo ra transistor", "outputs.kicad_sch", "16 ngo ra transistor (sink), cach ly quang", paper="A2")
    sh.text(20, 20, "16 NGO RA TRANSISTOR SINK (NPN-type): MCU -> PC817 -> MOSFET 60V/2.5A. "
                    "Tai noi giua V+ (24V) va Yn. Cap nguon ngoai vao V+/COM (cach ly voi mach logic).", 2.0)
    for ch in range(16):
        col, row = ch % 4, ch // 4
        X, Y = 30 + col * 95, 55 + row * 55
        out_channel(sh, ch + 1, X, Y)
    # field supply / terminals
    bx, by = 440, 60
    sh.text(bx - 10, by - 15, "CAU DAU NGO RA", 2.0)
    for k in range(2):
        base = k * 8
        # chan 10..3 = Y1..Y8 (tu trai qua phai khi xoay 180 tren PCB), chan 2 = V+, chan 1 = COM
        cn = {10 - i: f"Y{base + i + 1}" for i in range(8)}
        cn[2] = "V24_OUT"
        cn[1] = "COM_OUT"
        sh.place("Connector:Screw_Terminal_01x10", ref("J", 500), f"OUT {base + 1}-{base + 8}", bx + 60 * k, by + 20,
                 0, cn, footprint=fp_ok(tb(10)))
    sh.text(bx - 10, by + 60, "Loc / bao ve nguon ngo ra", 1.8)
    sh.place("Device:D_TVS", ref("D", 500), "SMBJ33A", bx, by + 85, 90, {2: "V24_OUT", 1: "COM_OUT"}, footprint=fp_ok(DSMB))
    C(sh, 500, "10uF/50V", bx + 15, by + 85, "V24_OUT", "COM_OUT", fp=C1206)
    C(sh, 500, "100nF/50V", bx + 25, by + 85, "V24_OUT", "COM_OUT", fp=C0805)
    return sh


# =================================================================== ANALOG
def ai_channel(sh, n, X, Y):
    """Chi 4-20mA: PTC -> TVS 5V -> shunt 120R 0.1% (20mA -> 2.40V) -> loc 4.7k/100nF -> ADC."""
    X, Y = kisch.snap(X), kisch.snap(Y)
    k = n - 1
    t = f"AI{n}_T"
    ptc = sh.place("Device:Polyfuse", f"F{701 + k}", "50mA", X + 7.62, Y, 90, {1: t}, footprint=fp_ok(PTC0805))
    tvs = sh.place("Device:D_TVS", f"D{701 + k}", "SMF5.0CA", X + 15.24, Y + 3.81, 90, {1: "GND"},
                   footprint=fp_ok(SOD123F))
    rsh = sh.place("Device:R", f"R{701 + 4 * k}", "120 0.1% 25ppm", X + 22.86, Y + 3.81, 0, {2: "GND"},
                   footprint=fp_ok(R1206))
    rf = sh.place("Device:R", f"R{704 + 4 * k}", "4.7k", X + 30.48, Y, 90, {}, footprint=fp_ok(R0603))
    cf = sh.place("Device:C", f"C{701 + k}", "100nF", X + 38.1, Y + 3.81, 0, {2: "GND"}, footprint=fp_ok(C0603))
    sh.path(ptc.p(2), tvs.p(2))
    sh.path(tvs.p(2), rsh.p(1))
    sh.path(rsh.p(1), rf.p(1))
    sh.label_at(f"AI{n}_IN", *rsh.p(1), (0, -1))
    sh.path(rf.p(2), cf.p(1))
    end = sh.path(cf.p(1), (X + 45.72, Y))
    sh.label_at(f"AI{n}_ADC", *end, (1, 0))
    sh.text(X, Y - 8, f"AI{n}: 4-20mA", 1.5)


def sheet_analog():
    sh = Sheet("10 ngo vao analog", "analog.kicad_sch", "10 ngo vao analog 4-20mA")
    sh.text(20, 20, "10 NGO VAO 4-20mA: shunt 120R 0.1% -> Vadc = I x 120R ; 4mA -> 0.48V ; 20mA -> 2.40V ; "
                    "24mA -> 2.88V (VREF = 3.000V)", 1.8)
    for ch in range(10):
        col, row = ch % 2, ch // 2
        ai_channel(sh, ch + 1, 30 + col * 95, 45 + row * 42)
    sh.place("Connector:Screw_Terminal_01x10", "J701", "AI 1-10 (4-20mA)", 250, 60, 0,
             {i + 1: f"AI{i + 1}_T" for i in range(10)}, footprint=fp_ok(tb(10)), mirror="y")
    sh.text(225, 105, "Nguon cap cho cam bien 2 day (24V loop) + chan chung GND", 1.5)
    sh.place("Device:Polyfuse", "F711", "200mA", 250, 125, 90, {1: "+24V", 2: "V24_LOOP"},
             footprint=fp_ok(PTC1206))
    sh.place("Connector:Screw_Terminal_01x06", "J703", "AI PWR/COM", 250, 150, 0,
             {1: "V24_LOOP", 2: "V24_LOOP", 3: "V24_LOOP", 4: "GND", 5: "GND", 6: "GND"},
             footprint=fp_ok(tb(6)), mirror="y")
    return sh


def main():
    os.makedirs(OUT, exist_ok=True)
    root = Sheet("Root", "PLC_STM32_Modbus.kicad_sch", "PLC STM32F407 Modbus TCP - 16DO / 10AI")
    root.text(30, 25, "PLC STM32F407VET6 + W5500 : Modbus TCP (LAN), nap code qua USB-C (CH340C)", 2.5)
    sheets = [sheet_power(), sheet_mcu(), sheet_usb(), sheet_comm(), sheet_outputs(), sheet_analog()]
    gl, singles = kisch.write_project(OUT, root, sheets)
    pro = os.path.join(OUT, "PLC_STM32_Modbus.kicad_pro")
    if not os.path.exists(pro):
        open(pro, "w").write('{"meta": {"filename": "PLC_STM32_Modbus.kicad_pro", "version": 3}}\n')
    print("global nets:", len(gl))
    print("single-label nets (check!):", singles)
    print("missing footprints:", sorted(_missing_fp))


if __name__ == "__main__":
    main()
