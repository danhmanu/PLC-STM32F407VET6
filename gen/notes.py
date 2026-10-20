"""Ghi chu giai thich dat SAT linh kien / khoi tren so do (tac dung, cach tinh gia tri)."""
import textwrap

FAILED = []


def _wrap(items, width_mm, size):
    maxc = max(24, int(width_mm / (size * 0.74)))
    out = []
    for it in items:
        lines = textwrap.wrap(it.strip(), maxc)
        out += lines if lines else [""]
    return out


def near(sh, refs, items, title=None, size=1.05, width=58, at=None):
    """Ghi chu ngan ngay canh cum linh kien refs (at=(x, y): vi tri du phong neu het cho)."""
    lines = _wrap(items, width, size)
    if sh.note_near(refs, title, lines, size=size, width=width) is None:
        if at and title:
            sh.note(at[0], at[1], title, lines, size=size, width=width)
        elif at:
            sh._note_body(at[0], at[1], lines, size, width, (0, 0, 132))
        else:
            FAILED.append((sh.name, refs))


def blk(sh, refs, title, items, width=95, at=None):
    """Tieu de khoi (dam, lon hon) dat canh ca khoi."""
    near(sh, refs, items, title=title, size=1.25, width=width, at=at)


# ----------------------------------------------------------------------------- ROOT
def root(sh):
    lines = _wrap([
        "• Nguồn 24VDC → bảo vệ (PTC, chống ngược, TVS) + lọc nhiễu → buck 5V → LDO 3.3V; +3.3VA riêng cho ADC.",
        "• MCU STM32F407VET6 (168MHz): 16 ngõ ra DO1–DO16, 10 ngõ vào 4–20mA (ADC 12-bit, VREF 3.000V), "
        "SPI2 → W5500.",
        "• Ethernet W5500 + RJ45: Modbus TCP cổng 502, tối đa 8 kết nối. Coil 00001–00016 = DO1–DO16; "
        "Input Register 30001–30010 = AI1–AI10.",
        "• USB-C + CH340C: nạp chương trình qua bootloader UART (tự vào boot bằng DTR/RTS), cổng debug.",
        "• 16 ngõ ra: opto PC817 (cách ly 5kV) + MOSFET 60V/2.5A, kiểu sink, nguồn tải V+/COM riêng 12–30V.",
        "• 10 ngõ vào 4–20mA: TVS + shunt 120Ω + lọc RC; J703 cấp 24V (PTC 0.5A) nuôi cảm biến 2 dây.",
        "• Ghi chú chi tiết (tác dụng, cách tính giá trị) đặt ngay cạnh từng linh kiện ở các trang con.",
    ], 360, 1.6)
    sh.note(30, 125, "TỔNG QUAN HỆ THỐNG – PLC STM32F407 + W5500 (Modbus TCP)", lines, size=1.6, width=360)


# ----------------------------------------------------------------------------- POWER
def power(sh):
    blk(sh, ["J101", "F101", "D101", "D102", "L101", "C101", "C102", "FB101", "C103", "C104"],
        "KHỐI VÀO 24VDC – BẢO VỆ & LỌC NHIỄU",
        ["Cầu chì → chống ngược → TVS → lọc common-mode → lọc LC → +24V cho toàn board."])
    near(sh, ["F101"], ["F101 PTC 0.5A/60V: tự ngắt khi chập/quá tải, tự phục hồi. I_hold > tải ≈ 0.1A (buck) "
                        "+ 0.25A (cảm biến) = 0.35A."])
    near(sh, ["D101"], ["D101 SS110 (Schottky 100V): chống cấp ngược cực. Sụt ≈ 0.5V → P ≈ 0.5V × 0.35A ≈ 0.18W."])
    near(sh, ["D102"], ["D102 TVS SMBJ33CA: kẹp xung sét/ESD. V_standoff 33V > 28.8V (24V+20%); "
                        "V_clamp ≈ 53V < 60V (Vin max U101)."])
    near(sh, ["L101"], ["L101 cuộn lọc common-mode: chặn nhiễu đồng pha trên cả 2 dây nguồn (cáp dài, biến tần)."])
    near(sh, ["C101", "C102"], ["C101 47µF tụ hóa: dự trữ; ESR dập dao động LC khi cắm nóng. "
                                "C102 1µF gốm: lọc cao tần."])
    near(sh, ["FB101", "C103", "C104"], ["FB101 + C103 10µF + C104 100nF: lọc LC thông thấp, chặn nhiễu 2.1MHz "
                                         "của buck dội ngược ra dây nguồn."])
    near(sh, ["R101", "D103"], ["LED nguồn: I = (24V − 2V)/4.7kΩ ≈ 4.7mA; P_R = 22²/4.7k ≈ 0.1W → R 1206."])

    blk(sh, ["C105", "C106", "U101", "C107", "D104", "L102", "C108", "C109"],
        "BUCK 24V → 5V (LMR16006Y, 0.6A, f_sw = 2.1MHz)",
        ["Hạ áp hiệu suất ~85%; D = Vout/Vin = 5/24 ≈ 0.21."])
    near(sh, ["C105", "C106"], ["C105 2.2µF/50V + C106 100nF: tụ ngõ vào cấp dòng xung cho khóa đóng cắt, "
                                "đặt sát VIN–GND."])
    near(sh, ["U101"], ["~SHDN nối VIN → luôn chạy. FB nối thẳng ngõ ra (bản 5V cố định, không cần cầu chia)."])
    near(sh, ["C107"], ["C107 100nF: tụ bootstrap lái MOSFET phía cao (datasheet)."])
    near(sh, ["D104"], ["D104 SS16 (60V/1A): diode thả trôi, dẫn dòng cuộn cảm khi khóa ngắt."])
    near(sh, ["L102"], ["L102 10µH: ΔI = (Vin−Vout)·D/(L·f) = 19V × 0.21/(10µH × 2.1MHz) ≈ 0.19A "
                        "(≈ 30% I_out). I_sat ≥ 0.6 + ΔI/2 ≈ 0.7A."])
    near(sh, ["C108", "C109"], ["C108, C109 22µF: gợn áp ΔV ≈ ΔI/(8·f·C) = 0.19/(8 × 2.1MHz × 44µF) ≈ 0.26mV."])
    near(sh, ["D105", "D106"], ["D105, D106 SS14: OR nguồn – lấy 5V từ buck hoặc USB (nạp code khi chưa có 24V), "
                                "chặn dòng chảy ngược."])

    blk(sh, ["C110", "U102", "C111", "C112"], "LDO 5V → 3.3V (AMS1117-3.3)",
        ["Tải 3.3V ≈ 260–300mA: STM32 ~100mA + W5500 ~130mA + CH340 + LED."])
    near(sh, ["U102"], ["Vin ≈ 4.65V ≥ 3.3V + 1.1V (dropout). P = (4.65 − 3.3) × 0.3A ≈ 0.4W → SOT-223 chịu được."])
    near(sh, ["C110", "C111", "C112"], ["C110 10µF vào; C111 22µF ra (AMS1117 cần ≥ 22µF để ổn định); "
                                        "C112 100nF lọc cao tần."])
    near(sh, ["FB102", "C113", "C114"], ["FB102 (600Ω@100MHz) + C113 + C114: tách +3.3VA sạch cho VDDA, REF3030."])
    near(sh, ["R102", "D107"], ["LED 3.3V: I = (3.3V − 2.0V)/1kΩ ≈ 1.3mA."])


# ----------------------------------------------------------------------------- MCU
def mcu(sh):
    blk(sh, ["U200"], "STM32F407VET6 (168MHz, Flash 512KB, RAM 192KB)",
        ["DO1–16: PE1, PE0, PB9…PB4, PD7…PD0 • AI1–10: PA0–PA3, PC0–PC5 • SPI2 → W5500 • USART1 → CH340."])
    near(sh, ["Y201", "C201", "C202"], ["Y201 8MHz → PLL 168MHz. Tụ tải C = 2·(C_L − C_stray) = 2 × (12 − 2) = 20pF "
                                        "(C_L theo datasheet thạch anh)."])
    near(sh, ["U201", "C214", "C215"], ["REF3030: VREF+ = 3.000V ±0.2% → 1 LSB = 3.0V/4096 ≈ 0.73mV. "
                                        "C214 1µF + C215 100nF giữ ổn định."])
    near(sh, ["C212", "C213"], ["VCAP 2.2µF ESR thấp: bắt buộc cho ổn áp 1.2V của lõi (datasheet)."])
    near(sh, ["C203", "C204", "C205", "C206", "C207", "C208", "C209"],
         ["C203–C208 100nF: một tụ cho mỗi chân VDD, đặt sát chân trên PCB. C209 4.7µF: dự trữ chung "
          "(ST AN4488)."], width=80)
    near(sh, ["C210", "C211"], ["VDDA: C210 1µF + C211 100nF – nguồn sạch cho ADC."])
    near(sh, ["C216", "SW201"], ["NRST: C216 100nF lọc nhiễu + nút RESET (trở kéo lên 40k có sẵn trong chip)."])
    near(sh, ["R201", "SW202"], ["BOOT0: R201 10k kéo xuống → chạy từ Flash. Giữ BOOT khi reset → BOOT0 = 1 → "
                                 "bootloader UART."])
    near(sh, ["R202"], ["BOOT1 (PB2) = 0 qua R202 10k → chọn bootloader hệ thống."])
    near(sh, ["R203", "D201", "R204", "D202"], ["LED RUN/ERR: I = (3.3V − 2.0V)/1kΩ ≈ 1.3mA (GPIO ≤ 25mA)."])
    near(sh, ["J201"], ["SWD (ST-Link): nạp và gỡ lỗi; VTref báo mức 3.3V."])


# ----------------------------------------------------------------------------- USB
def usb(sh):
    near(sh, ["R301", "R302"], ["R301, R302 5.1kΩ = R_d chuẩn Type-C: máy tính/sạc nhận ra thiết bị → cấp 5V "
                                "lên VBUS."])
    near(sh, ["R303", "C301"], ["Vỏ USB → GND qua 1MΩ // 4.7nF: xả tĩnh điện chậm, nhiễu cao tần qua tụ, tránh "
                                "vòng đất."])
    near(sh, ["F301", "C302"], ["F301 PTC 500mA: bảo vệ cổng USB máy tính (USB 2.0 ≤ 500mA). C302 1µF lọc VBUS."])
    near(sh, ["U301"], ["USBLC6-2SC6: chống ESD ±15kV cho D+, D−, VBUS."])
    blk(sh, ["U302", "C303", "C304"], "CH340C – USB ↔ UART (nạp code)",
        ["Dao động nội, không cần thạch anh. Cấp 3.3V nên V3 nối VCC. TXD/RXD → USART1 (PA9/PA10) = cổng "
         "bootloader ROM của STM32. C303 100nF + C304 10µF lọc nguồn."], width=80)
    blk(sh, ["Q301", "Q302", "Q303", "R304", "R305", "R306", "R307"], "TỰ VÀO BOOTLOADER BẰNG DTR/RTS",
        ["(RTS=1, DTR=0) → reset; (RTS=0, DTR=1) → nhả reset với BOOT0 = 1 → MCU vào bootloader. "
         "RTS, DTR cùng mức: không tác động."], width=85)
    near(sh, ["Q301", "R304"], ["Q301: RTS=1, DTR=0 → kéo NRST xuống. I_B = (3.3 − 0.7)/10k ≈ 0.26mA → "
                                "bão hòa (β ≥ 100)."])
    near(sh, ["Q302", "R305", "R306"], ["Q302: RTS=0, DTR=1 → kéo BOOT_N xuống. R306 10k kéo BOOT_N lên khi nghỉ."])
    near(sh, ["Q303", "R307"], ["Q303 (PNP) dẫn khi BOOT_N = 0 → BOOT0 = 3.3V. R307 hạn dòng bazơ."])
    near(sh, ["JP301", "R308"], ["JP301: bật/tắt nạp tự động. R308 1k hạn dòng khi nút BOOT và mạch tự động cùng "
                                 "tác động (≤ 3.3mA)."])


# ----------------------------------------------------------------------------- COMM
def comm(sh):
    blk(sh, ["U400"], "W5500 – ETHERNET 10/100 + TCP/IP PHẦN CỨNG",
        ["8 socket = tối đa 8 kết nối Modbus TCP đồng thời. Giao tiếp MCU qua SPI2 (≤ 21MHz)."], width=85)
    near(sh, ["R401"], ["R401 12.4kΩ 1% (EXRES1): tham chiếu dòng bias PHY – giá trị theo datasheet."])
    near(sh, ["C401", "C402"], ["C401 4.7µF (TOCAP), C402 10nF (1V2O): bắt buộc theo datasheet."])
    near(sh, ["Y401", "C403", "C404"], ["Y401 25MHz ±50ppm (chuẩn Ethernet). Tụ tải C = 2·(C_L − C_stray) = "
                                        "2 × (11 − 2) ≈ 18pF."])
    near(sh, ["R402", "R403"], ["R402, R403 10k kéo lên INT, RST (giữ mức 1 khi MCU chưa khởi động)."])
    near(sh, ["C405", "C406", "C407", "C408", "C409", "C410"],
         ["C405–C409 100nF: một tụ cho mỗi chân AVDD; C410 10µF dự trữ (W5500 hút ~130mA dạng xung khi phát)."],
         width=80)
    near(sh, ["R404", "R405", "C412"], ["TX: R404, R405 49.9Ω kéo lên 3.3V (tầng phát nguồn dòng). Cáp Cat5 "
                                        "Z_vi sai = 100Ω = 2 × 49.9Ω. C412 10nF lọc nguồn."])
    near(sh, ["R406", "R407", "C411"], ["RX: R406, R407 49.9Ω phối hợp 100Ω; C411 6.8nF nối điểm giữa xuống GND "
                                        "(xoay chiều)."])
    near(sh, ["J401", "C413", "C414"], ["RJ45 HR911105A có biến áp cách ly 1500Vrms. TCT → 3.3V (C414 lọc); "
                                        "RCT → C413 10nF xuống GND."])
    near(sh, ["R408", "R409"], ["LED RJ45 (W5500 kéo xuống để sáng): I = (3.3 − 2.0)/330Ω ≈ 4mA."])
    near(sh, ["C415"], ["C415 100nF: lọc chân VDD (pin 28) W5500."])


# ----------------------------------------------------------------------------- OUTPUTS
def outputs(sh):
    blk(sh, ["R501", "U501", "R502", "Q501", "R503", "D501", "R504", "D502"],
        "KÊNH NGÕ RA (16 kênh giống nhau) – SINK, CÁCH LY QUANG",
        ["DOx = 1 → LED opto sáng → MOSFET dẫn → Yn kéo về COM → relay hút."], width=62, at=(20, 252))
    near(sh, ["R501"], ["R_in 470Ω: I_F = (3.3V − 1.2V)/470Ω ≈ 4.5mA (PC817 ~5mA; GPIO ≤ 25mA)."], width=48)
    near(sh, ["U501"], ["PC817: cách ly 5000Vrms; CTR ≥ 50% → I_C ≥ 2.2mA."], width=45)
    near(sh, ["R502", "R503"], ["R_c 10k + R_g 10k: V_GS = V+ × 10k/20k = V+/2 ≈ 12V @24V (V_GS max 20V → V+ ≤ 30V; "
                                "≥ 4.5V → V+ ≥ 10V). I_opto = 24V/20k = 1.2mA < 2.2mA → bão hòa."], width=46)
    near(sh, ["Q501"], ["MOSFET 60V/2.5A, R_on≈0.1Ω: P = 0.5²×0.1 = 25mW (relay 0.5A); tắt τ≈R_g·C_iss≈3µs."],
         width=36, at=(97.0, 30.0))
    near(sh, ["D501"], ["SS16: dập xung ngược L·di/dt của cuộn relay về V+."], width=40)
    near(sh, ["R504", "D502"], ["LED Qn: I = (24V − 2V)/10kΩ ≈ 2.2mA – báo trạng thái ngõ ra thực."], width=45)
    near(sh, ["D533", "C501", "C502"], ["D533 TVS 33V + C501 10µF/50V + C502 100nF: bảo vệ và lọc nguồn tải V+."],
         width=55)
    near(sh, ["J501", "J502"], ["Nguồn relay 12–30V vào V+ (chân 2) / COM (chân 1). Tải nối giữa V+ và Yn. "
                                "KHÔNG nối COM với GND board (mất cách ly). Giới hạn 30V: Vceo PC817 = 35V."],
         width=70)


# ----------------------------------------------------------------------------- ANALOG
def analog(sh):
    blk(sh, ["D701", "R701", "R704", "C701"], "KÊNH 4–20mA (10 kênh giống nhau)",
        ["Firmware: I(mA) = raw/4095 × 3000mV/120Ω. Dải 4–20mA ≈ 2600 mức ADC."], width=80)
    near(sh, ["D701"], ["TVS SMF5.0CA: kẹp xung/quá áp > 5V. Không có cầu chì: đấu nhầm 24V vào AIn → "
                        "200mA, 4.8W → cháy shunt."], width=55)
    near(sh, ["R701"], ["Shunt 120Ω 0.1%: V = I·R; R ≤ 3.0V/24mA = 125Ω → 120Ω. 4mA → 0.48V, 20mA → 2.40V; "
                        "P = 48mW."], width=55)
    near(sh, ["R704", "C701"], ["RC 4.7k/100nF: f_c = 1/(2πRC) ≈ 340Hz; hạn dòng vào ADC ≈ 1mA khi quá áp."],
         width=50)
    near(sh, ["J701"], ["J701: AI1–AI10 nối thẳng vào kênh (đã bỏ cầu chì từng kênh)."], width=50)
    near(sh, ["F711"], ["F711 PTC 0.5A/60V (MF-MSMF050-2): bảo vệ nguồn 24V nuôi cảm biến; "
                        "10 × 24mA = 240mA < 0.5A."], width=55)
    near(sh, ["J703"], ["Cảm biến 2 dây: V24_LOOP → (+) → (−) → AIn. 4 dây: ngõ ra mA → AIn, 0V cảm biến → GND."],
         width=55)


BY_SHEET = {"Root": root, "Nguon 24VDC": power, "MCU STM32F407VET6": mcu, "USB nap code": usb,
            "Ethernet": comm, "16 ngo ra transistor": outputs, "10 ngo vao analog": analog}


def add_all(root_sheet, sheets):
    FAILED.clear()
    for sh in [root_sheet] + sheets:
        f = BY_SHEET.get(sh.name)
        if f:
            f(sh)
    if FAILED:
        print("notes khong dat duoc:", FAILED)
