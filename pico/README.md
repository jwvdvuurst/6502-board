# Pico USB terminal bridge

C firmware for the **original RP2040 Raspberry Pi Pico**, using Pico SDK 2.2.0
and its pinned TinyUSB dependency. It implements the
[ROM/Pico protocol](../firmware/PROTOCOL.md) with ordinary GPIO, without PIO,
an RTOS, or a second CPU core.

The Pico exposes one USB CDC port, queues host keyboard/file input, receives
SLIP-framed display records from the 6502, and maintains an 80 by 25 shadow
screen. It renders that screen as ANSI terminal cursor positions and text.
USB processing and bus processing share a nonblocking main loop. A stalled or
disconnected terminal does not stall display reception from the 6502.

## Wiring and startup

| Pico GPIO | Signal | Function |
|---|---|---|
| GP0-GP7 | Data bus | Through U19 transceiver to VIA PB0-PB7 |
| GP8 | BUS_REQ | Input from VIA CA2 |
| GP9 | BUS_ACK | Output to VIA CB1 |
| GP10 | BUS_DIR | Input from VIA PA0; also wired to transceiver DIR |
| GP11 | BUS_OE_N | Output controlling transceiver enable |
| GP25 | Onboard LED | On when firmware initialization is complete |

These match the electrical draft: Pico is on the transceiver A side, VIA on
its B side. DIR=1 selects Pico to VIA; DIR=0 selects VIA to Pico. The Pico
does not drive GP10. Retain the external pull-up on OE and pull-down on REQ.

At startup OE is driven inactive before ACK is driven low; data pins stay
inputs. Start the Pico and wait for its LED before releasing/resetting the
6502. The current harness provides no CPU reset control or main-board power
sense to the Pico. The power sequencing issues documented in DESIGN.md still
apply. No changes to the hardware schematic are made by this firmware.

Use an ANSI-compatible terminal, at least 80 columns by 25 rows, **local echo
off**, and CR or CR/LF line endings. CDC baud-rate selection does not control
this parallel link. The renderer disables terminal autowrap to protect the
bottom-right cell. To restore it after closing the session, send the terminal
sequence `ESC[?7h` or reset the terminal.

The ROM monitor commands work as before. For a binary program, type `L`, send
the generated Intel HEX file as text, then type `G 0400` (or its linked entry
address). In BASIC, send uppercase numbered lines and then `RUN`. CR/LF is
normalized to one CR, including across USB packets. A 4096-byte keyboard queue
and TinyUSB endpoint backpressure preserve input when the 6502 is slower.
Closing the terminal clears queued keys; reopening redraws the shadow screen.
Already acknowledged keys cannot be recalled.

## Build

Requires CMake, Ninja, Python 3, Arm GNU bare-metal tools, Pico SDK 2.2.0 with
`lib/tinyusb` initialized, and picotool. These are present in this workspace's
ignored `firmware/tools` directory; the script uses them without installing
anything system-wide:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File pico/build.ps1
```

Output: `build/board_bridge.uf2`, plus ELF, BIN, HEX, disassembly and map files.
No build step accesses a physical device. To install manually, hold BOOTSEL
while connecting the Pico over USB, then copy the UF2 to its `RPI-RP2` drive.
This replaces the Pico's existing application.

For a fresh environment with tools on PATH and `PICO_SDK_PATH` set:

```text
cmake -S pico -B pico/build -G Ninja -DPICO_BOARD=pico
cmake --build pico/build
```

Use `-Dpicotool_DIR=...` if its CMake package is not discoverable. SDK source:
[raspberrypi/pico-sdk](https://github.com/raspberrypi/pico-sdk), tag `2.2.0`,
commit `a1438dff1d38bd9c65dbd693f0e5db4b9ae91779`.
TinyUSB commit: `86ad6e56c1700e85f1c5678607a762cfe3aa2f47`.
Validated tools: Arm GCC 14.2.Rel1, CMake 3.31.6, Ninja 1.12.1, picotool 2.3.1.
The USB descriptor uses TinyUSB's development VID/PID `CAFE:4001`; it is not
a project-assigned production USB identity.

## Verification

Portable C tests run without Pico hardware or SDK:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File pico/build.ps1 -HostTests
```

For Linux/macOS, configure `-DBRIDGE_HOST_TESTS=ON`, build, then run `ctest`
in that build directory. Tests compile with warnings as errors and assertions
enabled. They check atomic display updates, invalid records/escapes, overflow
recovery, queue saturation, newline handling, both bus directions, held ACK,
cancellation before ACK, direction faults, partial USB output, reconnect
redraw, and sanitization of display control characters.

To test bytes emitted by the actual ROM running in its WDC 65C02 emulator:

```powershell
$env:ROM_PICO_TRACE = "$PWD/pico/build/rom-trace.bin"
node firmware/test.js
Remove-Item Env:ROM_PICO_TRACE
./pico/build-host/bridge_tests.exe pico/build/rom-trace.bin
```

The last ROM scenario loads and runs the hello program; the C test replays its
output bytes through the handshake and decoder and checks the resulting screen.
Cross compilation, UF2 inspection, host tests, and this ROM-stream test pass.
There has been **no flashing or physical USB/GPIO test**. The firmware uses
1 microsecond GPIO settling intervals; electrical setup/hold, asynchronous
GPIO timing, reset during transfers, throughput, and board power sequencing
still require measurement on the assembled hardware. USB enumeration/reconnect
behavior also requires a real Pico and host terminal.

## Layout and license

C source and headers follow AI Hub's C style: `BOARD_` prefixes for project
APIs/types/fields, PascalCase functions/types, and documented contracts in
headers. TinyUSB callback and configuration names follow its required API.
`pico/.clang-format` records the four-space, 88-column formatting settings.
Implementation comments explain handshake sequencing, framing recovery, queue
ownership, and partial-write handling.

- `bridge.c`: portable SLIP decoder, screen, keyboard queue, handshake state.
- `terminal.c`: bounded ANSI row output with partial-write handling.
- `main.c`: Pico GPIO sequencing and TinyUSB service loop.
- `usb_descriptors.c`, `tusb_config.h`: single CDC device configuration.

Project C sources use GPL-3.0-only, with license text in
[firmware/COPYING](../firmware/COPYING). SDK and TinyUSB retain their own
upstream licenses. Downloaded tools and SDK sources are not committed.
