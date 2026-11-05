# 6502 USB Computer - Initial Architecture

This document records the first design pass for a small, single-board 6502
computer. It is an architecture proposal, not a released schematic: exact part
numbers, timing, power, and footprints must be checked against manufacturer
datasheets before layout.

## Goals

- Run a modern 6502-family CPU and provide substantially more than 64 KiB of
  physical RAM.
- Connect to a modern computer over USB and provide a terminal interface.
- Avoid putting a UART/ACIA in the 6502-to-host data path.
- Keep the first revision understandable and buildable; use KiCad for the
  schematic and PCB when the architecture is settled.

## Agreed baseline

- **CPU:** W65C02S.
- **Logic:** 3.3 V throughout, subject to confirming compatible voltage and
  timing specifications for every selected part.
- **RAM:** 256 KiB SRAM.
- **Expansion:** a 16 KiB bank-switched window.
- **Host interface:** a USB device MCU exposing USB CDC (serial-port behavior
  to a terminal program). The MCU communicates with the 6502 through a
  memory-mapped parallel interface, not a UART.
- **USB MCU implementation:** standard Raspberry Pi Pico (RP2040, micro-USB)
  as an external daughterboard, connected to the main board through a
  detachable harness. Do not mount the Pico on the main PCB because its ICs
  are not DIP packages.
- **IC package and assembly requirement:** every IC mounted on the main PCB
  must be a through-hole DIP package and installed in a socket. No SMD ICs or
  directly soldered ICs are permitted. Select matching socket footprints and
  list the IC sockets explicitly in the assembly BOM; verify the socket,
  package width, and pin count against the selected IC.
- **First milestone:** architecture and schematic, before PCB layout.

The DIP-and-socket rule is a hard requirement, not a preference. It applies
to every main-board IC, including memory, logic, clock, and power-management
devices. If an IC cannot be selected in a suitable DIP package, redesign that
function or keep it on a separate off-board module connected through a
detachable interface; do not silently substitute an SMD package or adapter.

## Proposed CPU memory map

| CPU address | Size | Function |
|---|---:|---|
| `$0000-$77FF` | 30 KiB | General fixed SRAM; includes zero page and stack |
| `$7800-$7FFF` | 2 KiB | Reserved text-screen buffer for 25 rows x 80 columns |
| `$8000-$BFFF` | 16 KiB | SRAM bank window |
| `$C000-$DFFF` | 8 KiB | Memory-mapped I/O decode region |
| `$E000-$FFFF` | 8 KiB | Boot ROM; reset and interrupt vectors reside here |

The text-screen buffer is row-major, with one byte per character cell:
`address = $7800 + row * 80 + column` for rows 0-24 and columns 0-79. The
2 KiB reservation holds 2,048 bytes, so 48 bytes at `$7FD0-$7FFF` remain
unused. This is ordinary SRAM reserved by software, not a separate video RAM
chip or a hardware video generator; no character ROM is needed.

A 4-bit bank register selects one of sixteen 16 KiB regions in the 256 KiB
SRAM. Banks 0 and 1 overlap the physical SRAM used by the fixed 32 KiB area;
this is intentional aliasing and makes all 256 KiB addressable. The remaining
banks provide 224 KiB beyond the fixed area. The bank register is write-only
at `$C000-$C0FF` (mirrored); changing it affects only `$8000-$BFFF`. It resets
to bank 0.

This is bank switching, not a protected or relocatable MMU: software is
responsible for managing the shared window and preserving any data it needs
across bank changes.

Because bank 1 aliases fixed SRAM, its `$B800-$BFFF` window aliases the
screen-buffer area at `$7800-$7FFF`. Software must avoid using that bank-1
range for unrelated data while the screen contents need to be preserved.

The I/O region will be internally decoded rather than assigning separate
components across all 8 KiB. A VIA-style parallel I/O device is proposed at
`$C100-$C1FF` (mirrored on address bits A7-A4), subject to confirming a
suitable 3.3 V part. Its internal register select uses CPU address bits A3-A0.

## Schematic-level bus plan

The CPU address bus is decoded into four non-overlapping regions using the
upper address bits:

| Decode condition | Selected region |
|---|---|
| A15 = 0 | Fixed SRAM, `$0000-$7FFF` |
| A15 = 1, A14 = 0 | Banked SRAM, `$8000-$BFFF` |
| A15 = 1, A14 = 1, A13 = 0 | I/O, `$C000-$DFFF` |
| A15 = 1, A14 = 1, A13 = 1 | Boot ROM, `$E000-$FFFF` |

Using active-high logical selects (before any active-low pin inversion):

```text
RAM_SEL  = !A15 || !A14
BANK_SEL =  A15 && !A14
IO_SEL   =  A15 &&  A14 && !A13
ROM_SEL  =  A15 &&  A14 &&  A13

BANK_REG_SEL = IO_SEL && !A12 && !A11 && !A10 && !A9 && !A8
VIA_SEL      = IO_SEL && !A12 && !A11 && !A10 && !A9 &&  A8
```

`BANK_REG_SEL` writes the bank latch only when the CPU performs a valid write.
The VIA register address uses A3-A0; A7-A4 are intentionally ignored and
mirror its 16 registers throughout `$C100-$C1FF`. Addresses elsewhere in the
I/O region are reserved. Qualify memory and peripheral accesses with the
appropriate CPU phase; for the initial timing model, assert normal bus
accesses only while PHI2 is high.

For the 256 KiB x 8 SRAM, CPU A0-A13 connect to SRAM A0-A13. In the fixed
region, SRAM A14 is CPU A14 and SRAM A15-A17 are low. In the bank window,
SRAM A14-A17 are the four bank-register outputs. The SRAM is enabled only for
accesses in either RAM region. Its active-low output enable is asserted only
for RAM reads; its active-low write enable is asserted only for RAM writes.
Never assert output enable and write enable together, and keep both inactive
for non-RAM cycles.

The bank register is a resettable 4-bit register, written from CPU D0-D3 on a
write to `$C000-$C0FF`. Writes must be qualified as valid CPU write cycles;
the read path is not needed because the register is write-only. The register
and falling-edge clock shown in the draft are provisional and still require
datasheet and timing validation.

The current schematic uses a 74HC273 register with asynchronous reset, a
74HC157 feedback mux to hold the register between writes, and a socketed DIP
74HC04 inverter to clock the register on the falling edge of PHI2O. The SRAM
symbol available in the installed KiCad libraries is an AS6C4008 512 KiB x 8
candidate; its A18 pin is tied low so the design uses only the intended lower
256 KiB. Confirm the exact orderable part, voltage range, access time, package,
and supply current against the manufacturer datasheet before treating these
provisional symbols as BOM selections.

### Captured address decode and SRAM controls

The electrical draft uses two 74HC138 decoders. U4 decodes A15-A13 into
8 KiB pages (Y0 through Y7); U9 decodes A10-A8, enabled only when A12=A11=0,
to qualify the 256-byte bank-register and VIA regions. Decoder outputs are
active low:

```text
BANK_SEL       = !PAGE4_N || !PAGE5_N
BANK_REG_WRITE = !PAGE6_N && !SUBPAGE0_N && !RWB
VIA_CS1        = !PAGE6_N && !SUBPAGE1_N && PHI2O
VIA_CS2_N      = 0

RAM_SEL   = !A15 || !A14
RAM_CE_N  = !(RAM_SEL && PHI2O)
RAM_OE_N  = !(RAM_SEL && PHI2O && RWB)
RAM_WE_N  = !(RAM_SEL && PHI2O && !RWB)
```

`BANK_REG_WRITE` is the select input to the bank-register feedback mux; the
register captures only on its inverted-PHI2O clock edge. `VIA_CS1` is qualified
by PHI2O, while the VIA's active-low CS2 input is held low. SRAM `/CE`, `/OE`,
and `/WE` are inactive outside the CPU's high clock phase, and `/OE` and `/WE`
cannot be asserted together by these equations. Validate setup/hold and access
timing against the selected device datasheets before choosing the CPU clock
rate.

The electrical draft now includes U20, a socketed DIP-28 32 KiB OTP EPROM
candidate, mapped into `$E000-$FFFF`. EPROM A0-A12 connect to CPU A0-A12;
EPROM A13/A14 are tied low, so only one 8 KiB image is visible. `/CE` is
driven by the active-low U4 Y7 decode (`PAGE_7_N`), and `/OE` is asserted
only for a PHI2O-qualified CPU read. VPP is tied to +3V3 for read-only
operation. The boot image must contain the reset vector at `$FFFC/$FFFD`
(low byte first), NMI at `$FFFA/$FFFB`, and IRQ/BRK at `$FFFE/$FFFF`.

U20's symbol/value names the legacy low-voltage OTP EPROM AT27LV256A. The
Microchip AT27BV256 datasheet describes the equivalent 256K-bit OTP device
family with read operation at 2.7-3.6 V and 70 ns access, but its published
package drawing is PLCC only and is not sufficient proof that a genuine
AT27LV256A DIP order code can be sourced. The schematic uses a socketed
DIP-28 footprint to match the required package; confirm the exact orderable
part, package, pinout, datasheet, and programming support before PCB layout.
Do not substitute a 5 V-only EPROM or a surface-mount/adapter package without
revalidating the 3.3 V interface and the DIP/socket requirement.
[AT27BV256 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/doc0601.pdf).

## Proposed VIA/USB-MCU electrical interface

Use VIA Port B as the shared 8-bit data path, with a 3.3 V bus transceiver
between the VIA and USB MCU GPIO. Keep the transceiver disabled during reset
by pulling its active-low output enable inactive. Proposed control signals:

| Signal | Source -> destination | Purpose |
|---|---|---|
| `BUS_DIR` | VIA PA0 -> MCU/transceiver DIR | 0: 6502 to MCU; 1: MCU to 6502 |
| `BUS_REQ` | VIA CA2 -> MCU | Active-high byte request |
| `BUS_ACK` | MCU -> VIA CB1 | Acknowledge edge; may raise VIA interrupt |
| `BUS_D[7:0]` | VIA PB[7:0] <-> transceiver <-> MCU GPIO | Byte data |
| `VIA_IRQ_N` | VIA IRQB -> CPU IRQB | Notify the CPU of acknowledged/received events |

The MCU owns the transceiver output-enable control and keeps it disabled at
reset and idle. The VIA Port B data-direction register (DDRB) determines
whether the 6502 is driving the VIA pins or sampling them. The 6502 must set
DDRB and `BUS_DIR` before asserting `BUS_REQ`; the MCU must set transceiver
direction before enabling its outputs.

Transfers use break-before-make sequencing:

1. For a 6502-to-MCU byte, the 6502 configures DDRB as output, sets
   `BUS_DIR=0`, places the byte on Port B, then asserts `BUS_REQ`. The MCU
   enables the transceiver in the VIA-to-MCU direction, samples the byte,
   pulses `BUS_ACK`, then disables the transceiver. The 6502 deasserts
   `BUS_REQ` after observing the acknowledgement.
2. For an MCU-to-6502 byte, the 6502 first configures DDRB as input, sets
   `BUS_DIR=1`, then asserts `BUS_REQ`. The MCU sets the transceiver direction,
   presents the byte, enables its outputs, and pulses `BUS_ACK`. The 6502
   reads Port B and deasserts `BUS_REQ`; the MCU then disables the transceiver.
3. Reset and idle states leave `BUS_REQ` low, the transceiver disabled, and
   MCU data GPIOs as inputs. Pull `BUS_REQ` low, the transceiver's active-low
   output enable high, and `BUS_DIR` to a defined default while the VIA pins
   are inputs. Firmware must not drive the shared data lines until a receive
   request is granted.

These assignments are a proposed interface, not a verified VIA register
configuration. The VIA control-line modes, transceiver part, polarity, timing,
and exact handshake state machine must be checked against the selected VIA
datasheet and simulated for contention, missed edges, and reset safety before
layout.

### Provisional Pico GPIO allocation

The following allocation assumes the standard Raspberry Pi Pico GPIO names.
It is a planning aid, not a pinout commitment; check the chosen module's pinout
and board-edge USB clearance before creating footprints.

| Pico GPIO | Signal | Direction at module |
|---|---|---|
| GP0-GP7 | `BUS_D0-BUS_D7` | Bidirectional through the bus transceiver |
| GP8 | `BUS_REQ` | Input |
| GP9 | `BUS_ACK` | Output |
| GP10 | `BUS_DIR` | Input |
| GP11 | `BUS_OE_N` | Output; pulled high so the transceiver is disabled at reset |

Mount the Pico so its USB connector is accessible at a board edge. Use the
module's 3.3 V output as the board logic rail only if its documented regulator
budget covers the CPU, SRAM, VIA, and glue logic with margin. Otherwise, add a
separate 3.3 V regulator and ensure the two 3.3 V sources cannot back-feed one
another. Verify the module USB connector's ESD provisions and add protection
if needed.

## Top-level schematic block diagram

```text
                         USB host computer
                                |
                    USB CDC (module connector)
                                |
                        RP2040 module
                     GP0-GP7 + handshake
                                |
                       3.3 V bus transceiver
                                |
                       65C22 VIA Port B
                                |
                 +--------------+---------------+
                 |                              |
           CPU address/data                VIA control
                 |                              |
             W65C02S CPU ------------------------+
              /      |       \
     address bus   data bus   PHI2/RWB
          |           |          |
     decode logic    +-----------+---------------------+
          |          |           |                     |
   SRAM chip select  bank      65C22 select       ROM select
          |        register        |                  |
    256 KiB SRAM    |             VIA             8 KiB ROM
                    +-- SRAM A14-A17

W65C02S A0-A13 -> SRAM A0-A13
W65C02S A14 -> SRAM A14 in fixed-RAM cycles
bank-register Q0-Q3 -> SRAM A14-A17 in bank-window cycles
```

The diagram shows logical connectivity only. Memory and peripheral chip
selects, read/write enables, the CPU data bus, reset, and interrupt wiring
still need explicit schematic nets and timing checks.

## USB terminal path

The Raspberry Pi Pico will enumerate as a USB CDC device. Its firmware will
buffer characters in both directions and exchange them with the 6502 through
the parallel I/O device. The RP2040 provides USB device support and GPIO for
the parallel interface. Its clock, flash, and USB device circuitry are
supplied by the module; the module documentation, connector access, power
budget, and actual Pico pinout still need checking before schematic capture.

The CPU-side software can expose this as a console without implementing USB
protocols. The USB MCU is a peripheral/bridge, not the board's main processor.
The first schematic must settle the exact handshake and reset behavior, and
include a safe way to program/debug the MCU.

For the text display, the 6502 stores one character per cell in the reserved
`$7800-$7FCF` screen buffer. The ROM display routine reads the buffer in
row-major order and sends display records through the VIA/Pico byte handshake.
The Pico reconstructs the screen and renders it over USB CDC to a terminal.
The Pico cannot directly read the SRAM with the current interface, so the ROM
scans and transmits the buffer. The implemented ROM interface uses SLIP-framed
full screens, individual cell updates, and cursor updates; see
[the Pico protocol contract](firmware/PROTOCOL.md).

## ROM firmware

[Firmware source and build instructions](firmware/README.md) now provide an
8 KiB boot image for `$E000-$FFFF`, including all three CPU vectors. Reset
enters a monitor with checked Intel HEX loading into `$0400-$77FF`, memory
inspection, program execution, bank selection, screen refresh, and cold entry
to ROM-resident Tiny BASIC. BASIC uses signed 16-bit integer arithmetic;
floating point and disk storage are not provided. Its workspace is in fixed
RAM, separate from the screen. Loading machine code and BASIC program storage
share the same user RAM.

The implemented handshake holds ACK high until REQ falls, then waits for ACK
to fall before starting another byte. This supersedes the proposed ACK pulses
above. The VIA register modes and software state machine are tested with an
instruction-level WDC 65C02 emulator and a VIA/Pico model. Electrical timing,
reset recovery, and physical hardware remain to be validated. Pico firmware
will be implemented separately against the documented contract.

## Initial hardware blocks

1. W65C02S CPU, clock source, reset, and interrupt connections.
2. 256 KiB x 8 SRAM and bank-select latch/register.
3. 8 KiB boot ROM implemented using a verified 3.3 V parallel nonvolatile
   memory (exact device TBD).
4. Address decode and memory read/write control logic.
5. Parallel I/O/VIA and USB CDC-capable MCU.
6. External Raspberry Pi Pico harness and regulated 3.3 V board-power input;
   verify the module's USB and ESD implementation separately.
7. Reset/debug access and expansion/test points.

## Checks before PCB layout

- Confirm a genuine 3.3 V AT27LV256A-compatible OTP EPROM in socketed DIP-28
  form can be sourced and programmed; otherwise revisit the ROM/package plan.
- Verify the selected W65C02S speed grade and all memory/peripheral timing at
  the intended 3.3 V supply; choose a conservative initial clock.
- Confirm SRAM capacity, address pin mapping, access time, and package.
- Confirm the VIA/peripheral and logic-family VIH/VIL thresholds are compatible
  with the CPU and MCU at 3.3 V.
- Select the regulated 3.3 V source and verify current margin and power-up
  behavior.
- Validate the crystal oscillator values and reset timing against exact device
  datasheets and hardware measurements.
- Define safe Pico/main-board power sequencing; the independently powered Pico
  must not back-power an unpowered main-board transceiver through its GPIOs.
- Confirm Raspberry Pi Pico GPIO availability, harness pinout, USB connector
  clearance, and firmware programming/debug workflow.
- Verify the VIA-to-MCU handshake and reset defaults prevent bus contention.
- Finalize the VIA register map and test/debug access.

## KiCad status and next design step

`6502-board.kicad_sch` remains a conceptual block diagram.
`6502-electrical-draft.kicad_sch` now captures the W65C02S and W65C22S, the
provisional SRAM, two address decoders, bank-address mux, resettable bank
register, and logic generating the SRAM `/CE`, `/OE`, and `/WE` controls,
`BANK_SEL`, `BANK_REG_WRITE`, and the phase-qualified VIA select. The exported
KiCad netlist has been checked for these connections and their decode
equations. The CPU PHI2 input is separate from PHI2O; PHI2O clocks the VIA,
qualifies memory and VIA accesses, and is inverted for the bank-register
falling-edge clock.

The electrical-draft generator replaces the single-gate SOT-23 logic with
socketed DIP 74HC packages, sharing unused gates within each package; unused
gate inputs are tied low and outputs are left unconnected. The expanded draft
now includes a regulated-3.3-V input connector, reset circuit, provisional
1 MHz crystal oscillator, bypass capacitors, a socketed DIP 74HC245, and a
detachable Pico harness. All main-board IC footprints are socketed DIP
footprints. This meets the package rule at the footprint level, but the
assembly BOM still needs explicit socket line items and verified socket part
numbers. The Pico remains an external daughterboard.

### Following connections in the schematic

The electrical schematic uses named net labels for many inter-component
connections instead of drawing each connection as a long wire. In KiCad,
identical labels on the same sheet are electrically the same net. For example,
`A0` through `A13` connect CPU U1 to SRAM U3; `A0` through `A12` also connect
to EPROM U20. `D0` through `D7` connect U1, VIA U2, SRAM U3, and EPROM U20.
The EPROM select and read-enable connections are named `PAGE_7_N` and
`ROM_OE_N`. Click a net label in KiCad to highlight all pins on that net.

This label-based convention is electrically valid, but the exported drawing
does not show long point-to-point wires between those devices. The connection
key has been added to the schematic so the shared-net convention is clear.

The logic-family substitution is a schematic-level package choice, not a
completed timing or voltage-margin verification. Confirm the exact ordered
74HC variants' pinouts, operating range, input thresholds, output drive, and
propagation delays against the CPU, SRAM, and other bus devices before PCB
layout.

The ROM and vector connections are now represented, but its exact low-voltage
DIP orderable part and programming availability are not verified. A software
ROM image can now be built from `firmware/`; it has not been programmed or
tested on hardware. The clock and reset values are provisional, and the
regulated 3.3 V source and power budget are unspecified. The Pico's
independently powered GPIO may back-power an unpowered transceiver; power
sequencing or isolation must be resolved. There is no `.kicad_pcb` board
file. The electrical draft is not PCB- or fabrication-ready.

The CPU address ranges partition the full 64 KiB address space without overlap.
The sixteen 16 KiB bank selections cover all 256 KiB of SRAM; the fixed 32 KiB
is intentionally aliased by banks 0 and 1. The reset vector at `$FFFC-$FFFD`
is inside the ROM window.

KiCad 10.0.8 ERC on the regenerated electrical draft reports zero
violations. The ROM address/data/control mapping, active-low page decode,
qualified read enable, supply, and ground nets are included in the exported
netlist. Unused CPU/VIA pins are explicitly marked no-connect. The project
configuration loads the local symbol library. Netlist inspection confirms
that the Pico harness pins, ground, power, reset, and bus-control nets are
separate. The CLI netlist exporter still prints an annotation warning even
though the exported component references and multi-unit assignments are
unique; resolve that warning in the schematic editor before board release.
ERC cleanliness does not validate circuit behavior, part ratings, timing,
power sequencing, or fabrication readiness.

The analog/mixed-signal scope is limited to the power input and distribution,
reset behavior, and USB interface protection; no analog signal-processing
stage is specified. The draft has local bypassing, reset, and an external
regulated 3.3 V input, but their values and ratings are provisional. Before
layout, verify the supply source and budget, oscillator startup, reset timing,
return paths, and module USB protection from exact device documentation and
hardware tests. Do not infer regulator stability, current capacity, ESD
coverage, or transient performance from an ERC pass.

The next step is to verify the exact low-voltage DIP EPROM orderable and its
programmer support, then resolve Pico/main-board power sequencing. Validate
clock/reset and bus timing against exact datasheets, settle the board outline
and connectors, and create the KiCad PCB with socketed DIP footprints and an
explicit socket BOM. Complete routing and run PCB DRC plus schematic-to-board
parity checks. A board is not ready for fabrication until these checks and a
qualified hardware review are complete.
