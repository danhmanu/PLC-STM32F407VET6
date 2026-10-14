# PLC STM32F407VET6 – Modbus TCP – 16 DO transistor – 10 AI

Mạch nguyên lý KiCad 10 cho bộ PLC: điều khiển qua LAN bằng **Modbus TCP** (W5500), có thêm **RS485 (Modbus RTU)**, nạp code qua **USB‑C (CH340C)**, 16 ngõ ra transistor cách ly quang, 10 ngõ vào analog **0–10V / 4–20mA**.

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `kicad/PLC_STM32_Modbus.kicad_pro` | Project KiCad (mở file này) |
| `kicad/*.kicad_sch` | 6 trang mạch con (xem bảng dưới) |
| `kicad/PLC_STM32_Modbus.pdf` | Bản in PDF toàn bộ mạch |
| `kicad/BOM.csv` | Danh sách linh kiện (gom theo giá trị + footprint) |
| `kicad/erc.rpt` | Báo cáo ERC |
| `kicad/PLC_STM32_Modbus.kicad_pcb` | Mạch in 2 lớp 100×80mm |
| `kicad/fab/` | File sản xuất: Gerber + khoan (zip), file gắp đặt 2 mặt, PDF từng lớp, ảnh 3D |
| `gen/design.py`, `gen/kisch.py` | Script sinh mạch nguyên lý – sửa ở đây rồi chạy lại `sh gen/run.sh` |
| `gen/pcb.py`, `gen/finish.py`, `gen/fab.sh` | Script đặt linh kiện, nạp kết quả đi dây + đổ đồng, xuất file sản xuất |

> ⚠️ Các file `.kicad_sch` được **sinh tự động**. Nếu bạn sửa trực tiếp trong KiCad thì **đừng** chạy lại `gen/run.sh`, vì script sẽ ghi đè lên các file đó.

## Các trang mạch

| Trang | Nội dung chính |
|---|---|
| **Nguồn 24VDC** | PTC MF‑MSMF050 (0.5A/60V) → diode chống ngược SS110 → TVS SMBJ33CA → cuộn lọc common‑mode TDK ACM7060 → ferrite 3A + 47µF/10µF → **+24V**. Buck **LMR16006Y** (vào tới 60V) → 5V. Diode OR với VBUS của USB → **AMS1117‑3.3** → +3V3. Ferrite tách riêng **+3.3VA** cho ADC |
| **MCU** | STM32F407VET6, thạch anh 8MHz, **REF3030 (3.000V) làm VREF+**, nút RESET/BOOT, cổng SWD 10 chân, LED RUN/ERR |
| **USB nạp code** | USB‑C, USBLC6 chống tĩnh điện, polyfuse 500mA, **CH340C → USART1** (cổng bootloader của STM32), mạch tự vào bootloader bằng DTR/RTS (2×MMBT3904 + MMBT3906), jumper AUTO‑BOOT |
| **Ethernet + RS485** | W5500 + RJ45 HR911105A (có sẵn biến áp), thạch anh 25MHz. SP3485 + TVS + điện trở phân cực + jumper đầu cuối 120Ω |
| **16 ngõ ra transistor** | Mỗi kênh: TLP291 (opto) → **MOSFET DMN6075S (60V/2.5A)**, diode dập SS16, LED báo phía tải. Kiểu ngõ ra **sink (NPN)**: tải đấu giữa V+ và Yn |
| **10 ngõ vào analog** | Mỗi kênh: PTC 50mA, TVS SMF12CA, shunt 499Ω 0.1% (chọn bằng jumper trên header **J702 2×10**), cầu chia 47k/18k 0.1%, lọc RC 1k/100nF. Có cầu đấu nguồn loop 24V (qua PTC 200mA) |

## Gán chân STM32F407VET6

| Chức năng | Chân |
|---|---|
| DO1…DO16 | PE1, PE0, PB9, PB8, PB7, PB6, PB5, PB4, PD7, PD6, PD5, PD4, PD3, PD2, PD1, PD0 (các chân ở cạnh trên của LQFP, hướng về khối ngõ ra để dễ đi dây) |
| AI1…AI10 | PA0, PA1, PA2, PA3, PC0, PC1, PC2, PC3, PC4, PC5 (ADC1, 12‑bit) |
| W5500 (SPI2, tối đa 21MHz) | PB12 = CS, PB13 = SCK, PB14 = MISO, PB15 = MOSI, PD8 = RST, PD9 = INT |
| USB/CH340C (USART1) | PA9 = TX, PA10 = RX |
| RS485 (USART3) | PB10 = TX, PB11 = RX, PE15 = DE/RE |
| SWD | PA13 = SWDIO, PA14 = SWCLK, PB3 = SWO |
| LED | PD12 = RUN, PD13 = ERR |
| Còn trống | PA4–PA8, PA11, PA12, PA15, PB0, PB1, PC6–PC15, PD10, PD11, PD14, PD15, PE2–PE14 (đã đánh dấu NC) |

## Ngõ vào analog – công thức đổi

- Điện áp tại chân ADC: `Vadc = Vin × 18/65` (VREF = 3.000V)
- **0–10V** (không cắm jumper): 10V → 2.77V. Đo được tối đa khoảng 10.8V.
- **4–20mA** (cắm jumper kênh n trên J702, chân 2n‑1 ↔ 2n): shunt 499Ω mắc song song cầu chia 65k, tổng ≈ 495.2Ω. 20mA → 9.9V → 2.74V; 4mA → 0.55V.
  - Sụt áp trên tải ≈ 10V. Cảm biến 2 dây cấp 24V vẫn còn khoảng 14V để hoạt động.
- Firmware: `Vin = raw/4095 × 3.0 × 65/18`, `I(mA) = Vin / 0.4952`. Nên hiệu chuẩn hệ số cho từng kênh và lưu vào Holding Register.

## Ngõ ra transistor

- Phía tải có nguồn riêng: cấp 24V vào **V+ / COM** trên cầu đấu J501/J502 (chân 2 = V+, chân 1 = COM; chân 10…3 = Y1…Y8).
  - Nguồn này **cách ly** với mạch logic qua opto.
  - Nếu không cần cách ly, có thể nối chung với nguồn 24V của board.
- Khi kênh ON, gate MOSFET ≈ ½·V+ (≈ 12V). Dòng tối đa mỗi kênh khoảng 2A (giới hạn bởi tản nhiệt SOT‑23 và độ rộng đường mạch). Nên giới hạn tổng dòng mỗi nhóm 8 kênh ≤ 4A.

## Nạp chương trình qua USB

1. Cắm USB‑C. Không cần cấp 24V: board tự lấy nguồn 5V từ USB.
2. **Tự động** (cắm jumper AUTO‑BOOT JP301): phần mềm nạp điều khiển hai đường DTR/RTS theo trình tự sau (giống esptool):
   - RTS = 1, DTR = 0 → MCU bị reset.
   - RTS = 0, DTR = 1 → nhả reset trong khi BOOT0 = 1 → MCU vào bootloader UART.
   - Thả cả hai.
   - Có thể dùng `stm32flash` với tùy chọn `-i` (chuỗi GPIO DTR/RTS), hoặc script Python + pyserial.
3. **Thủ công**: giữ **BOOT**, bấm rồi nhả **RESET**, sau đó nhả BOOT. Tiếp theo nạp bằng **STM32CubeProgrammer** (UART) hoặc Arduino IDE (STM32duino, upload method “Serial”).
4. Cổng SWD (ST‑Link) để debug.

## Bảng địa chỉ Modbus gợi ý (TCP cổng 502 và RTU)

| Vùng | Địa chỉ | Nội dung |
|---|---|---|
| Coils | 00001–00016 | DO1–DO16 |
| Input Registers | 30001–30010 | AI1–AI10 (raw hoặc ×100 đơn vị kỹ thuật) |
| Holding Registers | 40001+ | IP/mask/gateway, chế độ V/mA từng kênh, hệ số hiệu chuẩn, timeout an toàn cho ngõ ra |

⚠️ Modbus TCP **không có mã hóa hay xác thực**. Nếu muốn điều khiển qua Internet, hãy đi qua VPN (WireGuard/Tailscale). Không mở thẳng port 502 trên router.

## Mạch in (PCB) 2 lớp – 100 × 80 mm

![PCB mặt trên](kicad/fab/render_top.png)

**Bố trí** (nhìn từ mặt trên):
- **Cạnh trên:** cầu đấu ngõ ra J501/J502, bước 3.81mm. Từ trái sang phải: Y1…Y8, V+, COM | Y9…Y16, V+, COM.
- **Cạnh dưới:** J701 (AI1…AI10), J703 (24V loop ×3, GND ×3), J402 (RS485: A, B, GND), J101 (24VDC IN: +, −).
- **Cạnh trái:** USB‑C nạp code. **Cạnh phải:** RJ45.
- 16 kênh ngõ ra xếp thành cột ngay dưới cầu đấu. MCU ở giữa, W5500 bên phải, nguồn ở góc dưới phải, analog ở góc dưới trái.
- 4 lỗ bắt vít M3 ở 4 góc.

**Hai mặt linh kiện:**
- Mặt dưới chỉ có tụ/trở nhỏ: tụ lọc nguồn đặt ngay dưới chân nguồn của STM32/W5500, cầu chia analog, tụ USB, cổng SWD.
- Cần đặt hàng **lắp ráp SMT 2 mặt**. File gắp đặt: `fab/pos_top.csv`, `fab/pos_bottom.csv`.

**Quy tắc thiết kế:**

| Nhóm net | Độ rộng dây | Khoảng cách |
|---|---|---|
| Mặc định (tín hiệu) | 0.2mm | 0.2mm |
| Supply (+3V3, +3.3VA, GND) | 0.3mm | 0.2mm |
| Power (24V, 5V, VBUS, V24_OUT, COM_OUT, Y1…Y16) | 0.8mm | 0.2mm |

- Via 0.6/0.3mm (via công suất 0.8/0.4mm).
- Đổ đồng GND cả hai mặt. Có thêm một vùng đồng +3V3 ở mặt dưới, dưới MCU và W5500.
- Dây và via cách mép board ≥ 0.45mm.

### Trạng thái đi dây – CẦN HOÀN THIỆN TRƯỚC KHI ĐẶT MẠCH

- Freerouting đi được **626/666 kết nối (~94%)**. Các chân nguồn của 2 IC QFP được fan‑out trước bằng script.
- **Còn 40 kết nối chưa đi dây.** Danh sách đầy đủ kèm tọa độ ở `kicad/unrouted.txt`, gồm:
  - +3V3 (8) và GND (4) quanh MCU/W5500.
  - AIx_ADC (8) từ cầu chia analog lên MCU.
  - Một số net analog / USB / SWD / LED.
- **DRC hiện tại:** 0 lỗi điện (khoảng cách, chập, lỗ khoan). Không lệch so với sơ đồ nguyên lý. Chỉ còn cảnh báo silkscreen (chữ chồng lên nhau hoặc lên pad), không ảnh hưởng mạch.
- **Cách hoàn thiện:** mở `PLC_STM32_Modbus.kicad_pcb`, bật ratsnest, dùng Interactive Router (phím **X**) nối từng đường trong `unrouted.txt`. Ưu tiên đi ở mặt dưới hoặc thêm via xuống vùng GND/+3V3. Sau đó chạy lại DRC (Inspect → Design Rules Checker) đến khi **Unconnected = 0**.
- ⚠️ **Không gửi Gerber đi sản xuất khi DRC còn báo "unconnected".**

### Tái tạo / sửa PCB bằng script

```bash
"/c/Program Files/KiCad/10.0/bin/python.exe" gen/pcb.py            # đặt linh kiện + fan-out -> kicad/*.kicad_pcb, gen/placed.kicad_pcb
"/c/Program Files/KiCad/10.0/bin/python.exe" gen/finish.py gen/routing/plc4.ses gen/routing/plc5.ses   # nạp đường đi dây + đổ đồng
sh gen/fab.sh                                                       # Gerber, khoan, pos, PDF, ảnh 3D
```

> ⚠️ Chạy lại `gen/pcb.py` hoặc `gen/finish.py` sẽ **ghi đè** file PCB. Sau khi đã đi dây tay trong KiCad, chỉ dùng `gen/fab.sh`, hoặc xuất trực tiếp trong KiCad.

## Kết quả kiểm tra

- **ERC: còn 1 cảnh báo, là cố ý.** Chân `V3` của CH340C (kiểu power‑output trong thư viện) nối vào +3V3; datasheet yêu cầu như vậy khi VCC = 3.3V.
- Đã kiểm tra netlist: không có net nào chỉ có một chân. Các net DO, AI, SPI, UART, NRST, BOOT0 và mạch trong từng kênh nối đúng.

## Việc cần kiểm tra / làm tiếp trước khi làm PCB

1. **Phần PHY của W5500**: so sánh với `w5500_sch_v110_use_mag.pdf` của WIZnet. Mạch hiện tại:
   - TX: 49.9Ω kéo lên 3V3, TCT nối 3V3.
   - RX: 49.9Ω về điểm giữa, tụ 6.8nF xuống GND; RCT qua 10nF xuống GND.
   - Datasheet W5500 xác nhận các giá trị: EXRES1 = 12.4k 1%, TOCAP = 4.7µF, 1V2O = 10nF, chân 23 nối GND.
2. **Cuộn lọc common‑mode**: TDK ACM7060‑701‑2PL. Kiểm tra lại dòng định mức và thứ tự chân 1‑2 / 3‑4 khớp footprint.
3. **Cuộn cảm buck**: 10µH cho LMR16006Y (2.1MHz). Đối chiếu lại bảng chọn L/C trong datasheet TI.
4. Footprint của các linh kiện dùng ký hiệu chung (R, C, LED, polyfuse…) đã gán sẵn (0603/0805/1206). Kiểm tra lại công suất: shunt 499Ω cần ≥ 0.25W (đã chọn 1206).
5. Chưa có ngõ vào số (DI). Nếu cần, còn trống PE2–PE14 cho 13 DI cách ly quang.
