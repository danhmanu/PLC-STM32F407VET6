"""Tao thu vien rieng cua project: ky hieu + footprint module W5500 Lite (Ethernet co san RJ45).

Kich thuoc theo ban ve module: board 23 x 25mm, 2 hang chan 1x6 buoc 2.54mm, cach nhau 20.32mm.
Hang trai (tren -> duoi): GND, GND, MOSI, SCLK, CS, INT
Hang phai (tren -> duoi): GND, 3V3, 3V3, NC, RST, MISO      (nhin tu mat tren, RJ45 o phia tren)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
KI = os.path.join(HERE, "..", "kicad")

PINS = [  # (so chan, ten, kieu, cot, hang)
    (1, "GND", "power_in", 0, 0), (2, "GND", "passive", 0, 1), (3, "MOSI", "input", 0, 2),
    (4, "SCLK", "input", 0, 3), (5, "CS", "input", 0, 4), (6, "INT", "output", 0, 5),
    (7, "GND", "passive", 1, 0), (8, "3V3", "power_in", 1, 1), (9, "3V3", "passive", 1, 2),
    (10, "NC", "no_connect", 1, 3), (11, "RST", "input", 1, 4), (12, "MISO", "output", 1, 5),
]


def font(sz=1.27):
    return f"(effects (font (size {sz} {sz})))"


def symbol_lib():
    pins = []
    for num, name, typ, col, row in PINS:
        y = 6.35 - row * 2.54
        x, ang = (-12.7, 0) if col == 0 else (12.7, 180)
        hide = " (hide yes)" if typ == "no_connect" else ""
        pins.append(f'(pin {typ} line (at {x} {y} {ang}) (length 2.54){hide} (name "{name}" {font()}) '
                    f'(number "{num}" {font()}))')
    return f'''(kicad_symbol_lib (version 20241209) (generator "plc_gen") (generator_version "10.0")
  (symbol "W5500_Lite" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 0 12.7 0) {font()})
    (property "Value" "W5500_Lite" (at 0 10.16 0) {font()})
    (property "Footprint" "PLC:W5500_Lite_Module" (at 0 -12.7 0) (hide yes) {font()})
    (property "Datasheet" "https://docs.wiznet.io/Product/Chip/Ethernet/W5500" (at 0 -15.24 0) (hide yes) {font()})
    (property "Description" "Module W5500 Lite (W5500 + RJ45 co bien ap), SPI, 3.3V, 2 hang chan 1x6 cach 20.32mm" (at 0 0 0) (hide yes) {font()})
    (property "ki_keywords" "W5500 Ethernet module SPI Modbus TCP" (at 0 0 0) (hide yes) {font()})
    (symbol "W5500_Lite_0_1"
      (rectangle (start -10.16 8.89) (end 10.16 -8.89) (stroke (width 0.254) (type default)) (fill (type background)))
      (text "W5500 Lite" (at 0 0 0) {font(1.5)})
      (text "RJ45" (at 0 -6.35 0) {font(1.0)})
    )
    (symbol "W5500_Lite_1_1"
      {" ".join(pins)}
    )
  )
)
'''


def footprint():
    X0, X1 = -1.34, 21.66            # mep board module (23mm)
    Y0, Y1 = -6.5, 18.5              # mep tren (phia RJ45) va duoi (25mm)
    RJ = (2.11, -9.0, 18.21, 12.0)   # than RJ45 (rong 16.10mm), nho ra khoi mep tren ~2.5mm
    pads = []
    for num, name, typ, col, row in PINS:
        x, y = col * 20.32, row * 2.54
        shape = "rect" if num == 1 else "circle"
        pads.append(f'(pad "{num}" thru_hole {shape} (at {x:.2f} {y:.2f}) (size 1.7 1.7) (drill 1.0) '
                    f'(layers "*.Cu" "*.Mask"))')
    line = '(stroke (width {w}) (type solid)) (fill none) (layer "{l}")'
    return f'''(footprint "W5500_Lite_Module" (version 20241229) (generator "plc_gen") (generator_version "10.0")
  (layer "F.Cu")
  (descr "Module W5500 Lite 23x25mm, 2 hang socket 1x6 P2.54mm cach 20.32mm; RJ45 nho ra mep tren")
  (tags "W5500 Ethernet module")
  (property "Reference" "REF**" (at 10.16 20.3 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "W5500_Lite" (at 10.16 6.35 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (property "Footprint" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))
  (property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))
  (property "Description" "" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1.27 1.27))))
  (attr through_hole)
  (fp_rect (start {X0} {Y0}) (end {X1} {Y1}) {line.format(w=0.12, l="F.SilkS")})
  (fp_rect (start {RJ[0]} {RJ[1]}) (end {RJ[2]} {Y0}) {line.format(w=0.12, l="F.SilkS")})
  (fp_text user "LAN" (at 10.16 -7.6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (fp_line (start -2.4 -0.9) (end -2.4 0.9) (stroke (width 0.2) (type solid)) (layer "F.SilkS"))
  (fp_rect (start {X0} {Y0}) (end {X1} {Y1}) {line.format(w=0.1, l="F.Fab")})
  (fp_rect (start {RJ[0]} {RJ[1]}) (end {RJ[2]} {RJ[3]}) {line.format(w=0.1, l="F.Fab")})
  (fp_text user "W5500 Lite" (at 10.16 15.5 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {X0 - 0.25} {RJ[1] - 0.25}) (end {X1 + 0.25} {Y1 + 0.25}) {line.format(w=0.05, l="F.CrtYd")})
  {" ".join(pads)}
)
'''


def main():
    open(os.path.join(HERE, "PLC.kicad_sym"), "w", encoding="utf8", newline="\n").write(symbol_lib())
    open(os.path.join(KI, "PLC.kicad_sym"), "w", encoding="utf8", newline="\n").write(symbol_lib())
    os.makedirs(os.path.join(KI, "PLC.pretty"), exist_ok=True)
    open(os.path.join(KI, "PLC.pretty", "W5500_Lite_Module.kicad_mod"), "w", encoding="utf8",
         newline="\n").write(footprint())
    open(os.path.join(KI, "sym-lib-table"), "w", encoding="utf8", newline="\n").write(
        '(sym_lib_table\n  (version 7)\n  (lib (name "PLC")(type "KiCad")(uri "${KIPRJMOD}/PLC.kicad_sym")'
        '(options "")(descr "Thu vien rieng cua project"))\n)\n')
    open(os.path.join(KI, "fp-lib-table"), "w", encoding="utf8", newline="\n").write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "PLC")(type "KiCad")(uri "${KIPRJMOD}/PLC.pretty")'
        '(options "")(descr "Thu vien rieng cua project"))\n)\n')
    print("ok")


if __name__ == "__main__":
    main()
